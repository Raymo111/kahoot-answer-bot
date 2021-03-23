"""Transport related constants"""
from enum import Enum, unique, auto


@unique
class ConnectionType(Enum):
    """CometD Connection types"""
    #: Long polling connection type
    LONG_POLLING = "long-polling"
    #: Websocket connection type
    WEBSOCKET = "websocket"


#: Connection type that all CometD server implementaions should support
DEFAULT_CONNECTION_TYPE = ConnectionType.LONG_POLLING
#: CometD meta channel prefix
META_CHANNEL_PREFIX = "/meta/"
#: CometD service channel prefix
SERVICE_CHANNEL_PREFIX = "/service/"


@unique
class MetaChannel(str, Enum):
    """CometD meta channel names"""
    #: Handshake meta channel
    HANDSHAKE = META_CHANNEL_PREFIX + "handshake"
    #: Connect meta channel
    CONNECT = META_CHANNEL_PREFIX + "connect"
    #: Disconnect meta channel
    DISCONNECT = META_CHANNEL_PREFIX + "disconnect"
    #: Subscribe meta channel
    SUBSCRIBE = META_CHANNEL_PREFIX + "subscribe"
    #: Unsubscribe meta channel
    UNSUBSCRIBE = META_CHANNEL_PREFIX + "unsubscribe"


@unique
class TransportState(Enum):
    """Describes a transport object's state"""
    #: Transport is disconnected
    DISCONNECTED = auto()
    #: Connection terminated by the server
    SERVER_DISCONNECTED = auto()
    #: Transport is trying to establish a connection
    CONNECTING = auto()
    #: Transport is connected to the server
    CONNECTED = auto()
    #: Transport is disconnecting from the server
    DISCONNECTING = auto()


#: Handshake message template
HANDSHAKE_MESSAGE = {
    # mandatory
    "channel": MetaChannel.HANDSHAKE,
    "version": "1.0",
    "supportedConnectionTypes": None,
    # optional
    "minimumVersion": "1.0",
    "id": None
}

#: Connect message template
CONNECT_MESSAGE = {
    # mandatory
    "channel": MetaChannel.CONNECT,
    "clientId": None,
    "connectionType": None,
    # optional
    "id": None
}

#: Disconnect message template
DISCONNECT_MESSAGE = {
    # mandatory
    "channel": MetaChannel.DISCONNECT,
    "clientId": None,
    # optional
    "id": None
}

#: Subscribe message template
SUBSCRIBE_MESSAGE = {
    # mandatory
    "channel": MetaChannel.SUBSCRIBE,
    "clientId": None,
    "subscription": None,
    # optional
    "id": None
}

#: Unsubscribe message template
UNSUBSCRIBE_MESSAGE = {
    # mandatory
    "channel": MetaChannel.UNSUBSCRIBE,
    "clientId": None,
    "subscription": None,
    # optional
    "id": None
}

#: Publish message template
PUBLISH_MESSAGE = {
    # mandatory
    "channel": None,
    "clientId": None,
    "data": None,
    # optional
    "id": None
}
