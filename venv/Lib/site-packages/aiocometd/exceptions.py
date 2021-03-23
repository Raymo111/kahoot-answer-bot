"""Exception types

Exception hierarchy::

    AiocometdException
        ClientError
            ClientInvalidOperation
        TransportError
            TransportInvalidOperation
            TransportTimeoutError
            TransportConnectionClosed
        ServerError
"""
from typing import Optional, List, cast

from aiocometd import utils


class AiocometdException(Exception):
    """Base exception type.

    All exceptions of the package inherit from this class.
    """


class TransportError(AiocometdException):
    """Error during the transportation of messages"""


class TransportInvalidOperation(TransportError):
    """The requested operation can't be executed on the current state of the
    transport"""


class TransportTimeoutError(TransportError):
    """Transport timeout"""


class TransportConnectionClosed(TransportError):
    """The connection unexpectedly closed"""


class ServerError(AiocometdException):
    """CometD server side error"""
    # pylint: disable=useless-super-delegation
    def __init__(self, message: str, response: Optional[utils.JsonObject]) \
            -> None:
        """If the *response* contains an error field it gets parsed
        according to the \
        `specs <https://docs.cometd.org/current/reference/#_code_error_code>`_

        :param message: Error description
        :param response: Server response message
        """
        super().__init__(message, response)

    # pylint: enable=useless-super-delegation

    @property
    def message(self) -> str:
        """Error description"""
        # pylint: disable=unsubscriptable-object
        return cast(str, self.args[0])
        # pylint: enable=unsubscriptable-object

    @property
    def response(self) -> Optional[utils.JsonObject]:
        """Server response message"""
        return cast(Optional[utils.JsonObject],
                    self.args[1])  # pylint: disable=unsubscriptable-object

    @property
    def error(self) -> Optional[str]:
        """Error field in the :obj:`response`"""
        if self.response is None:
            return None
        return self.response.get("error")

    @property
    def error_code(self) -> Optional[int]:
        """Error code part of the error code part of the `error\
        <https://docs.cometd.org/current/reference/#_code_error_code>`_, \
        message field"""
        return utils.get_error_code(self.error)

    @property
    def error_message(self) -> Optional[str]:
        """Description part of the `error\
        <https://docs.cometd.org/current/reference/#_code_error_code>`_, \
        message field"""
        return utils.get_error_message(self.error)

    @property
    def error_args(self) -> Optional[List[str]]:
        """Arguments part of the `error\
        <https://docs.cometd.org/current/reference/#_code_error_code>`_, \
        message field"""
        return utils.get_error_args(self.error)


class ClientError(AiocometdException):
    """ComtedD client side error"""


class ClientInvalidOperation(ClientError):
    """The requested operation can't be executed on the current state of the
    client"""
