"""Transport abstract base class definition"""
from abc import ABC, abstractmethod
from typing import Set, Optional, List

import aiohttp

from aiocometd.constants import ConnectionType, TransportState
from aiocometd.typing import JsonObject


class Transport(ABC):
    """Defines the operations that all transport classes should support"""
    @property
    @abstractmethod
    def connection_type(self) -> ConnectionType:
        """The transport's connection type"""

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """CometD service url"""

    @property
    @abstractmethod
    def client_id(self) -> Optional[str]:
        """Clinet id value assigned by the server"""

    @property
    @abstractmethod
    def state(self) -> TransportState:
        """Current state of the transport"""

    @property
    @abstractmethod
    def subscriptions(self) -> Set[str]:
        """Set of subscribed channels"""

    @property
    @abstractmethod
    def last_connect_result(self) -> Optional[JsonObject]:
        """Result of the last connect request"""

    @property
    @abstractmethod
    def reconnect_advice(self) -> JsonObject:
        """Reconnection advice parameters returned by the server"""

    @property  # type: ignore
    @abstractmethod
    def http_session(self) -> Optional[aiohttp.ClientSession]:
        """HTTP client session"""

    @http_session.setter  # type: ignore
    @abstractmethod
    def http_session(self, http_session: Optional[aiohttp.ClientSession]) \
            -> None:
        """HTTP client session"""

    @abstractmethod
    async def handshake(self, connection_types: List[ConnectionType]) \
            -> JsonObject:
        """Executes the handshake operation

        :param connection_types: list of connection types
        :return: Handshake response
        :raises TransportError: When the network request fails.
        """

    @abstractmethod
    async def connect(self) -> JsonObject:
        """Connect to the server

        The transport will try to start and maintain a continuous connection
        with the server, but it'll return with the response of the first
        successful connection as soon as possible.

        :return: The response of the first successful connection.
        :raise TransportInvalidOperation: If the transport doesn't has a \
        client id yet, or if it's not in a :obj:`~TransportState.DISCONNECTED`\
        :obj:`state`.
        :raises TransportError: When the network request fails.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from server

        The disconnect message is only sent to the server if the transport is
        actually connected.
        """

    @abstractmethod
    async def close(self) -> None:
        """Close transport and release resources"""

    @abstractmethod
    async def subscribe(self, channel: str) -> JsonObject:
        """Subscribe to *channel*

        :param channel: Name of the channel
        :return: Subscribe response
        :raise TransportInvalidOperation: If the transport is not in the \
        :obj:`~TransportState.CONNECTED` or :obj:`~TransportState.CONNECTING` \
        :obj:`state`
        :raises TransportError: When the network request fails.
        """

    @abstractmethod
    async def unsubscribe(self, channel: str) -> JsonObject:
        """Unsubscribe from *channel*

        :param channel: Name of the channel
        :return: Unsubscribe response
        :raise TransportInvalidOperation: If the transport is not in the \
        :obj:`~TransportState.CONNECTED` or :obj:`~TransportState.CONNECTING` \
        :obj:`state`
        :raises TransportError: When the network request fails.
        """

    @abstractmethod
    async def publish(self, channel: str, data: JsonObject) -> JsonObject:
        """Publish *data* to the given *channel*

        :param channel: Name of the channel
        :param data: Data to send to the server
        :return: Publish response
        :raise TransportInvalidOperation: If the transport is not in the \
        :obj:`~TransportState.CONNECTED` or :obj:`~TransportState.CONNECTING` \
        :obj:`state`
        :raises TransportError: When the network request fails.
        """

    @abstractmethod
    async def wait_for_state(self, state: TransportState) -> None:
        """Waits for and returns when the transport enters the given *state*

        :param state: A state value
        """
