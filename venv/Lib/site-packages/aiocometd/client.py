"""Client class implementation"""
import asyncio
import reprlib
import logging
from collections import abc
from contextlib import suppress
import json
from typing import Optional, List, Union, Set, AsyncIterator, Type, Any
from types import TracebackType

from aiocometd.transports import create_transport
from aiocometd.transports.abc import Transport
from aiocometd.constants import DEFAULT_CONNECTION_TYPE, ConnectionType, \
    MetaChannel, SERVICE_CHANNEL_PREFIX, TransportState
from aiocometd.exceptions import ServerError, ClientInvalidOperation, \
    TransportTimeoutError, ClientError
from aiocometd.utils import is_server_error_message
from aiocometd.extensions import Extension, AuthExtension
from aiocometd.typing import ConnectionTypeSpec, SSLValidationMode, \
    JsonObject, JsonDumper, JsonLoader


LOGGER = logging.getLogger(__name__)


class Client:  # pylint: disable=too-many-instance-attributes
    """CometD client"""
    #: Predefined server error messages by channel name
    _SERVER_ERROR_MESSAGES = {
        MetaChannel.HANDSHAKE: "Handshake request failed.",
        MetaChannel.CONNECT: "Connect request failed.",
        MetaChannel.DISCONNECT: "Disconnect request failed.",
        MetaChannel.SUBSCRIBE: "Subscribe request failed.",
        MetaChannel.UNSUBSCRIBE: "Unsubscribe request failed."
    }
    #: Defualt connection types list
    _DEFAULT_CONNECTION_TYPES = [ConnectionType.WEBSOCKET,
                                 ConnectionType.LONG_POLLING]

    def __init__(self, url: str,
                 connection_types: Optional[ConnectionTypeSpec] = None, *,
                 connection_timeout: Union[int, float] = 10.0,
                 ssl: Optional[SSLValidationMode] = None,
                 max_pending_count: int = 100,
                 extensions: Optional[List[Extension]] = None,
                 auth: Optional[AuthExtension] = None,
                 json_dumps: JsonDumper = json.dumps,
                 json_loads: JsonLoader = json.loads,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        :param url: CometD service url
        :param connection_types: List of connection types in order of \
        preference, or a single connection type name. If ``None``, \
        [:obj:`~ConnectionType.WEBSOCKET`, \
        :obj:`~ConnectionType.LONG_POLLING`] will be used as a default value.
        :param connection_timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        :param ssl: SSL validation mode. None for default SSL check \
        (:func:`ssl.create_default_context` is used), False for skip SSL \
        certificate validation, \
        `aiohttp.Fingerprint <https://aiohttp.readthedocs.io/en/stable/\
        client_reference.html#aiohttp.Fingerprint>`_ for fingerprint \
        validation, :obj:`ssl.SSLContext` for custom SSL certificate \
        validation.
        :param max_pending_count: The maximum number of messages to \
        prefetch from the server. If the number of prefetched messages reach \
        this size then the connection will be suspended, until messages are \
        consumed. \
        If it is less than or equal to zero, the count is infinite.
        :param extensions: List of protocol extension objects
        :param auth: An auth extension
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :param json_loads: Function for JSON deserialization, the default is \
        :func:`json.loads`
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        #: CometD service url
        self.url = url
        #: List of connection types to use in order of preference
        if isinstance(connection_types, ConnectionType):
            self._connection_types = [connection_types]
        elif isinstance(connection_types, abc.Iterable):
            self._connection_types = list(connection_types)
        else:
            self._connection_types = self._DEFAULT_CONNECTION_TYPES
        self._loop = loop or asyncio.get_event_loop()
        #: queue for consuming incoming event messages
        self._incoming_queue: "Optional[asyncio.Queue[JsonObject]]" = None
        #: transport object
        self._transport: Optional[Transport] = None
        #: marks whether the client is open or closed
        self._closed = True
        #: The maximum amount of time to wait for the transport to re-establish
        #: a connection with the server when the connection fails
        self.connection_timeout = connection_timeout
        #: SSL validation mode
        self.ssl = ssl
        #: the maximum number of messages to prefetch from the server
        self._max_pending_count = max_pending_count
        #: List of protocol extension objects
        self.extensions = extensions
        #: An auth extension
        self.auth = auth
        #: Function for JSON serialization
        self._json_dumps = json_dumps
        #: Function for JSON deserialization
        self._json_loads = json_loads

    def __repr__(self) -> str:
        """Formal string representation"""
        cls_name = type(self).__name__
        fmt_spec = "{}({}, {}, connection_timeout={}, ssl={}, " \
                   "max_pending_count={}, extensions={}, auth={}, loop={})"
        return fmt_spec.format(cls_name,
                               reprlib.repr(self.url),
                               reprlib.repr(self._connection_types),
                               reprlib.repr(self.connection_timeout),
                               reprlib.repr(self.ssl),
                               reprlib.repr(self._max_pending_count),
                               reprlib.repr(self.extensions),
                               reprlib.repr(self.auth),
                               reprlib.repr(self._loop))

    @property
    def closed(self) -> bool:
        """Marks whether the client is open or closed"""
        return self._closed

    @property
    def subscriptions(self) -> Set[str]:
        """Set of subscribed channels"""
        if self._transport:
            return self._transport.subscriptions
        return set()

    @property
    def connection_type(self) -> Optional[ConnectionType]:
        """The current connection type in use if the client is open,
        otherwise ``None``"""
        if self._transport is not None:
            return self._transport.connection_type
        return None

    @property
    def pending_count(self) -> int:
        """The number of pending incoming messages

        Once :obj:`open` is called the client starts listening for messages
        from the server. The incoming messages are retrieved and stored in an
        internal queue until they get consumed by calling :obj:`receive`.
        """
        if self._incoming_queue is None:
            return 0
        return self._incoming_queue.qsize()

    @property
    def has_pending_messages(self) -> bool:
        """Marks whether the client has any pending incoming messages"""
        return self.pending_count > 0

    def _pick_connection_type(self, connection_types: List[str]) \
            -> Optional[ConnectionType]:
        """Pick a connection type based on the  *connection_types*
        supported by the server and on the user's preferences

        :param connection_types: Connection types \
        supported by the server
        :return: The connection type with the highest precedence \
        which is supported by the server
        """
        server_connection_types = []
        for type_string in connection_types:
            with suppress(ValueError):
                server_connection_types.append(ConnectionType(type_string))

        intersection = (set(server_connection_types) &
                        set(self._connection_types))
        if not intersection:
            return None

        result = min(intersection, key=self._connection_types.index)
        return result

    async def _negotiate_transport(self) -> Transport:
        """Negotiate the transport type to use with the server and create the
        transport object

        :return: Transport object
        :raise ClientError: If none of the connection types offered by the \
        server are supported
        """
        self._incoming_queue = asyncio.Queue(maxsize=self._max_pending_count)
        transport = create_transport(DEFAULT_CONNECTION_TYPE,
                                     url=self.url,
                                     incoming_queue=self._incoming_queue,
                                     ssl=self.ssl,
                                     extensions=self.extensions,
                                     auth=self.auth,
                                     json_dumps=self._json_dumps,
                                     json_loads=self._json_loads,
                                     loop=self._loop)

        try:
            response = await transport.handshake(self._connection_types)
            self._verify_response(response)

            LOGGER.info("Connection types supported by the server: %r",
                        response["supportedConnectionTypes"])
            connection_type = self._pick_connection_type(
                response["supportedConnectionTypes"]
            )
            if not connection_type:
                raise ClientError("None of the connection types offered by "
                                  "the server are supported.")

            if transport.connection_type != connection_type:
                # extract and reuse the client_id from the initial transport
                client_id = transport.client_id
                # extract and reuse the reconnect_advice from the initial
                # transport
                advice = transport.reconnect_advice
                # extract and reuse the http_session, to avoid loosing any
                # cookies sent to the initial transport
                session = transport.http_session
                # clear the http_session in the initial transport to avoid
                # the termination of the session when the transport is closed
                transport.http_session = None  # type: ignore
                # close the initial transport
                await transport.close()
                # create the negotiated transport
                transport = create_transport(
                    connection_type,
                    url=self.url,
                    incoming_queue=self._incoming_queue,
                    client_id=client_id,
                    ssl=self.ssl,
                    extensions=self.extensions,
                    auth=self.auth,
                    json_dumps=self._json_dumps,
                    json_loads=self._json_loads,
                    reconnect_advice=advice,
                    http_session=session,
                    loop=self._loop)
            return transport
        except Exception:
            await transport.close()
            raise

    async def open(self) -> None:
        """Establish a connection with the CometD server

        This method works mostly the same way as the `handshake` method of
        CometD clients in the reference implementations.

        :raise ClientError: If none of the connection types offered by the \
        server are supported
        :raise ClientInvalidOperation:  If the client is already open, or in \
        other words if it isn't :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the handshake or the first connect request \
        gets rejected by the server.
        """
        if not self.closed:
            raise ClientInvalidOperation("Client is already open.")

        LOGGER.info("Opening client with connection types %r ...",
                    [t.value for t in self._connection_types])
        self._transport = await self._negotiate_transport()

        response = await self._transport.connect()
        self._verify_response(response)
        self._closed = False

        assert self.connection_type is not None
        LOGGER.info("Client opened with connection_type %r",
                    self.connection_type.value)

    async def close(self) -> None:
        """Disconnect from the CometD server"""
        if not self.closed:
            if self.pending_count == 0:
                LOGGER.info("Closing client...")
            else:
                LOGGER.warning(
                    "Closing client while %s messages are still pending...",
                    self.pending_count)
            try:
                if self._transport:
                    await self._transport.disconnect()
                    await self._transport.close()
            finally:
                self._closed = True
                LOGGER.info("Client closed.")

    async def subscribe(self, channel: str) -> None:
        """Subscribe to *channel*

        :param channel: Name of the channel
        :raise ClientInvalidOperation: If the client is :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the subscribe request gets rejected by the \
        server
        """
        if self.closed:
            raise ClientInvalidOperation("Can't send subscribe request while, "
                                         "the client is closed.")
        await self._check_server_disconnected()

        assert self._transport is not None
        response = await self._transport.subscribe(channel)
        self._verify_response(response)
        LOGGER.info("Subscribed to channel %s", channel)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from *channel*

        :param channel: Name of the channel
        :raise ClientInvalidOperation: If the client is :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the unsubscribe request gets rejected by the \
        server
        """
        if self.closed:
            raise ClientInvalidOperation("Can't send unsubscribe request "
                                         "while, the client is closed.")
        await self._check_server_disconnected()

        assert self._transport is not None
        response = await self._transport.unsubscribe(channel)
        self._verify_response(response)
        LOGGER.info("Unsubscribed from channel %s", channel)

    async def publish(self, channel: str, data: JsonObject) -> JsonObject:
        """Publish *data* to the given *channel*

        :param channel: Name of the channel
        :param data: Data to send to the server
        :return: Publish response
        :raise ClientInvalidOperation: If the client is :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the publish request gets rejected by the server
        """
        if self.closed:
            raise ClientInvalidOperation("Can't publish data while, "
                                         "the client is closed.")
        await self._check_server_disconnected()

        assert self._transport is not None
        response = await self._transport.publish(channel, data)
        self._verify_response(response)
        return response

    def _verify_response(self, response: JsonObject) -> None:
        """Check the ``successful`` status of the *response* and raise \
        the appropriate :obj:`~aiocometd.exceptions.ServerError` if it's False

        If the *response* has no ``successful`` field, it's considered to be
        successful.

        :param response: Response message
        :raise ServerError: If the *response* is not ``successful``
        """
        if is_server_error_message(response):
            self._raise_server_error(response)

    def _raise_server_error(self, response: JsonObject) -> None:
        """Raise the appropriate :obj:`~aiocometd.exceptions.ServerError` for \
        the failed *response*

        :param response: Response message
        :raise ServerError: If the *response* is not ``successful``
        """
        channel = response["channel"]
        message = type(self)._SERVER_ERROR_MESSAGES.get(channel)
        if not message:
            if channel.startswith(SERVICE_CHANNEL_PREFIX):
                message = "Service request failed."
            else:
                message = "Publish request failed."
        raise ServerError(message, response)

    async def receive(self) -> JsonObject:
        """Wait for incoming messages from the server

        :return: Incoming message
        :raise ClientInvalidOperation: If the client is closed, and has no \
        more pending incoming messages
        :raise ServerError: If the client receives a confirmation message \
         which is not ``successful``
        :raise TransportTimeoutError: If the transport can't re-establish \
        connection with the server in :obj:`connection_timeout` time.
        """
        if not self.closed or self.has_pending_messages:
            response = await self._get_message(self.connection_timeout)
            self._verify_response(response)
            return response

        raise ClientInvalidOperation("The client is closed and there are "
                                     "no pending messages.")

    async def __aiter__(self) -> AsyncIterator[JsonObject]:
        """Asynchronous iterator

        :raise ServerError: If the client receives a confirmation message \
         which is not ``successful``
        :raise TransportTimeoutError: If the transport can't re-establish \
        connection with the server in :obj:`connection_timeout` time.
        """
        while True:
            try:
                yield await self.receive()
            except ClientInvalidOperation:
                break

    async def __aenter__(self) -> "Client":
        """Enter the runtime context and call :obj:`open`

        :raise ClientInvalidOperation:  If the client is already open, or in \
        other words if it isn't :obj:`closed`
        :raise TransportError: If a network or transport related error occurs
        :raise ServerError: If the handshake or the first connect request \
        gets rejected by the server.
        :return: The client object itself
        :rtype: Client
        """
        try:
            await self.open()
        except Exception:
            await self.close()
            raise
        return self

    async def __aexit__(self, exc_type: Type[BaseException],
                        exc_val: BaseException,
                        exc_tb: TracebackType) -> None:
        """Exit the runtime context and call :obj:`open`"""
        await self.close()

    async def _get_message(self, connection_timeout: Union[int, float]) \
            -> JsonObject:
        """Get the next incoming message

        :param connection_timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        :return: Incoming message
        :raise TransportTimeoutError: If the transport can't re-establish \
        connection with the server in :obj:`connection_timeout` time.
        :raise ServerError: If the connection gets closed by the server.
        """
        tasks: List[asyncio.Future[Any]] = []
        # task waiting on connection timeout
        if connection_timeout:
            timeout_task = asyncio.ensure_future(
                self._wait_connection_timeout(connection_timeout),
                loop=self._loop
            )
            tasks.append(timeout_task)

        assert self._incoming_queue is not None
        # task waiting on incoming messages
        get_task = asyncio.ensure_future(self._incoming_queue.get(),
                                         loop=self._loop)
        tasks.append(get_task)

        assert self._transport is not None
        # task waiting on server side disconnect
        server_disconnected_task = asyncio.ensure_future(
            self._transport.wait_for_state(
                TransportState.SERVER_DISCONNECTED),
            loop=self._loop
        )
        tasks.append(server_disconnected_task)

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
                loop=self._loop)

            # cancel all pending tasks
            for task in pending:
                task.cancel()

            # handle the completed task
            if get_task in done:
                return get_task.result()

            if server_disconnected_task in done:
                await self.close()
                raise ServerError("Connection closed by the server",
                                  self._transport.last_connect_result)
            raise TransportTimeoutError("Lost connection with the server.")
        except asyncio.CancelledError:
            # cancel all tasks
            for task in tasks:
                task.cancel()
            raise

    async def _wait_connection_timeout(self, timeout: Union[int, float]) \
            -> None:
        """Wait for and return when the transport can't re-establish \
        connection with the server in *timeout* time

        :param timeout: The maximum amount of time to wait for the \
        transport to re-establish a connection with the server when the \
        connection fails.
        """
        assert self._transport is not None
        while True:
            await self._transport.wait_for_state(TransportState.CONNECTING)
            try:
                await asyncio.wait_for(
                    self._transport.wait_for_state(TransportState.CONNECTED),
                    timeout, loop=self._loop
                )
            except asyncio.TimeoutError:
                break

    async def _check_server_disconnected(self) -> None:
        """Checks whether the current transport'state is
        :obj:`TransportState.SERVER_DISCONNECTED` and if it is then closes the
        client and raises an error

        :raise ServerError: If the current transport's state is \
        :obj:`TransportState.SERVER_DISCONNECTED`
        """
        if (self._transport and
                self._transport.state == TransportState.SERVER_DISCONNECTED):
            await self.close()
            raise ServerError("Connection closed by the server",
                              self._transport.last_connect_result)
