"""Functions for transport class registration and instantiation"""
from typing import Type, Callable, Any

from aiocometd.exceptions import TransportInvalidOperation
from aiocometd.constants import ConnectionType
from aiocometd.transports.abc import Transport


TRANSPORT_CLASSES = {}


def register_transport(conn_type: ConnectionType) \
        -> Callable[[Type[Transport]], Type[Transport]]:
    """Class decorator for registering transport classes

    The class' connection_type property will be also defined to return the
    given *connection_type*
    :param conn_type: A connection type
    :return: The updated class
    """
    # pylint: disable=unused-argument, missing-docstring
    def decorator(cls: Type[Transport]) -> Type[Transport]:
        TRANSPORT_CLASSES[conn_type] = cls

        @property  # type: ignore
        def connection_type(self: Transport) -> ConnectionType:
            return conn_type

        cls.connection_type = connection_type  # type: ignore
        return cls
    return decorator


def create_transport(connection_type: ConnectionType, *args: Any,
                     **kwargs: Any) -> Transport:
    """Create a transport object that can be used for the given
    *connection_type*

    :param connection_type: A connection type
    :param kwargs: Keyword arguments to pass to the transport
    :return: A transport object
    """
    if connection_type not in TRANSPORT_CLASSES:
        raise TransportInvalidOperation("There is no transport for connection "
                                        "type {!r}".format(connection_type))

    return TRANSPORT_CLASSES[connection_type](*args, **kwargs)  # type: ignore
