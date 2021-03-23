"""Websocket transport class definition"""
import asyncio
import logging
from contextlib import suppress
from typing import Callable, Optional, AsyncContextManager, Any, Awaitable, \
    cast, Dict

import aiohttp
import aiohttp.client_ws

from aiocometd.constants import ConnectionType
from aiocometd.exceptions import TransportError, TransportConnectionClosed
from aiocometd.typing import JsonObject
from aiocometd.transports.registry import register_transport
from aiocometd.transports.base import TransportBase, Payload, Headers


LOGGER = logging.getLogger(__name__)
#: Asynchronous factory function of ClientSessions
AsyncSessionFactory = Callable[[], Awaitable[aiohttp.ClientSession]]
#: Web socket type
WebSocket = aiohttp.client_ws.ClientWebSocketResponse
#: Context manager type managing a WebSocket
WebSocketContextManager = AsyncContextManager[WebSocket]


class WebSocketFactory:  # pylint: disable=too-few-public-methods
    """Helper class to create asynchronous callable objects, that return
    WebSocket objects

    This class allows the usage of WebSocket objects without context blocks
    """
    def __init__(self, session_factory: AsyncSessionFactory):
        """
        :param session_factory: Coroutine factory function \
        which returns an HTTP session
        """
        self._session_factory = session_factory
        self._context: Optional[WebSocketContextManager] = None
        self._socket: Optional[WebSocket] = None

    async def close(self) -> None:
        """Close the WebSocket"""
        with suppress(Exception):
            await self._exit()

    async def __call__(self, *args: Any, **kwargs: Any) -> WebSocket:
        """Create a new WebSocket object or return a previously created one
        if it's not closed

        :param args: positional arguments for the ws_connect function
        :param kwargs: keyword arguments for the ws_connect function
        :return: Websocket object
        """
        # if a the factory object already exists and if it's in closed state
        # exit the context manager and clear the references
        if self._socket is not None and self._socket.closed:
            await self._exit()

        # if there is no factory object, then create it and enter the \
        # context manager to initialize it
        if self._socket is None:
            self._socket = await self._enter(*args, **kwargs)

        return self._socket

    async def _enter(self, *args: Any, **kwargs: Any) -> WebSocket:
        """Enter WebSocket context

        :param args: positional arguments for the ws_connect function
        :param kwargs: keyword arguments for the ws_connect function
        :return: Websocket object
        """
        session = await self._session_factory()
        self._context = session.ws_connect(*args, **kwargs)
        return await self._context.__aenter__()

    async def _exit(self) -> None:
        """Exit WebSocket context"""
        if self._context:
            await self._context.__aexit__(None, None, None)
            self._socket = self._context = None


@register_transport(ConnectionType.WEBSOCKET)
class WebSocketTransport(TransportBase):
    """WebSocket type transport"""

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        #: factory for creating websockets
        self._socket_factory = WebSocketFactory(self._get_http_session)
        #: pending message exchanges between the client and server,
        #: the request message's id is used as a key
        self._pending_exhanges: Dict[int, "asyncio.Future[JsonObject]"] \
            = dict()
        #: task for receiving incoming messages
        self._receive_task: Optional["asyncio.Task[None]"] = None

    async def _reset_socket(self) -> None:
        """Close the socket factory and recreate it"""
        await self._socket_factory.close()
        self._socket_factory = WebSocketFactory(self._get_http_session)

    async def _get_socket(self, headers: Headers) -> WebSocket:
        """Factory function for creating a websocket object

        :param headers: Headers to send
        :return: Websocket object
        """
        return await self._socket_factory(
            self.endpoint,
            ssl=self.ssl,
            headers=headers,
            receive_timeout=self.request_timeout,
            autoping=True)

    def _create_exhange_future(self, payload: Payload) \
            -> "asyncio.Future[JsonObject]":
        """Create a future which represents an exchange of messages between
        the server and client

        The created future will be associated with the id of the first message
        in the payload.
        :param payload: The payload sent by the client
        :return: A future which will yield the server's response message to the
        outgoing *payload*
        """
        future: "asyncio.Future[JsonObject]" = asyncio.Future(loop=self._loop)
        self._pending_exhanges[payload[0]["id"]] = future
        return future

    def _set_exchange_results(self, response_payload: Payload) -> None:
        """Set the result of all the pending message exchange futures for which
        we can find a response in the payload

        :param response_payload: Response payload
        """
        # iterate over all incoming messages
        for response_message in response_payload:
            # if the incoming message has an id (otherwise it's not a response)
            if "id" in response_message:
                message_id = response_message["id"]
                # if the message id is associated with any pending exchange
                if message_id in self._pending_exhanges:
                    # remove the exchange from the pending exchanges
                    exchange = self._pending_exhanges.pop(message_id)
                    # if the future is not completed yet then set its result
                    if not exchange.done():
                        exchange.set_result(response_message)

    def _set_exchange_errors(self, error: Exception) -> None:
        """Set the *error* as the exception for all pending exchanges

        :param error: An exception
        """
        # set the exception for all the exchanges
        for exchange in self._pending_exhanges.values():
            if not exchange.done():
                exchange.set_exception(error)
        # clear the pending exchanges
        self._pending_exhanges.clear()

    async def _send_final_payload(self, payload: Payload, *,
                                  headers: Headers) -> JsonObject:
        try:
            try:
                # try to send the payload on the socket which might have
                # been closed since the last time it was used
                socket = await self._get_socket(headers)
                return await self._send_socket_payload(socket, payload)
            except asyncio.TimeoutError:
                # reset the socket factory since after a timeout error
                # it becomes invalid
                await self._reset_socket()
                raise
            except TransportConnectionClosed:
                # if the socket was indeed closed, try to reopen the socket
                # and send the payload, since the connection could've
                # normalised since the last network problem
                socket = await self._get_socket(headers)
                return await self._send_socket_payload(socket, payload)
        except aiohttp.client_exceptions.ClientError as error:
            LOGGER.warning("Failed to send payload, %s", error)
            raise TransportError(str(error)) from error

    async def _send_socket_payload(self, socket: WebSocket,
                                   payload: Payload) -> JsonObject:
        """Send *payload* to the server on the given *socket*

        :param socket: WebSocket object
        :param payload: A message or a list of messages
        :return: Response payload
        :raises TransportError: When the request fails.
        :raises TransportConnectionClosed: When the *socket* receives a CLOSE \
        message instead of the expected response
        """
        # create a future for the exchange of messages
        future = self._create_exhange_future(payload)
        try:
            # send the outgoing payload
            await socket.send_json(payload, dumps=self._json_dumps)
        except Exception as error:
            # set the error as the result for all pending exchanges
            self._set_exchange_errors(error)
            raise

        # make sure the receive task is running
        self._start_receive_task(socket)
        # await and return the response of the server
        return await future

    def _start_receive_task(self, socket: WebSocket) -> None:
        """Start the task which receives messages from the *socket* if it's
        not already running

        :param socket: A Websocket object
        """
        # if the receive task is not running then start it
        if self._receive_task is None:
            self._receive_task = self._loop.create_task(self._receive(socket))
            self._receive_task.add_done_callback(self._receive_done)

    async def _receive(self, socket: WebSocket) -> None:
        """Consume the incomming messages on the given *socket*

        :param socket: A Websocket object
        """
        # receive responses from the server and consume them
        try:
            while True:
                response = await socket.receive()
                if response.type == aiohttp.WSMsgType.CLOSE:
                    raise TransportConnectionClosed("Received CLOSE message "
                                                    "on the factory.")
                # parse the response payload
                try:
                    response_payload \
                        = cast(Payload, response.json(loads=self._json_loads))
                except TypeError:
                    raise TransportError("Received invalid response from the "
                                         "server.")

                # consume all event messages in the payload
                await self._consume_payload(response_payload)

                # set results of matching exchanges
                self._set_exchange_results(response_payload)
        except Exception as error:
            # set the error as the result for all pending exchanges
            self._set_exchange_errors(error)
            raise

    def _receive_done(self, future: "asyncio.Task[None]") -> None:
        """Consume the results of the *future*

        :param future: A :obj:`_receive` future
        """
        # extract the result of the future
        try:
            result = future.result()
        except Exception as error:  # pylint: disable=broad-except
            result = error
        # clear the receive task
        self._receive_task = None
        LOGGER.debug("Recevie task finished with: %r", result)

    async def close(self) -> None:
        # cancel the receive task if it exists and wait for its completeion
        if self._receive_task is not None and not self._receive_task.done():
            self._receive_task.cancel()
            await asyncio.wait([self._receive_task])
        await self._socket_factory.close()
        await super().close()
