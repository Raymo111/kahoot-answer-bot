"""Utility functions"""
import re
import asyncio
from functools import wraps
from http import HTTPStatus
from typing import Union, Optional, List, Any

from aiocometd.constants import META_CHANNEL_PREFIX, SERVICE_CHANNEL_PREFIX
from aiocometd.typing import CoroFunction, JsonObject


def defer(coro_func: CoroFunction, delay: Union[int, float, None] = None, *,
          loop: Optional[asyncio.AbstractEventLoop] = None) -> CoroFunction:
    """Returns a coroutine function that will defer the call to the given
    *coro_func* by *delay* seconds

    :param coro_func: A coroutine function
    :param delay: Delay in seconds
    :param loop: An event loop
    :return: Coroutine function wrapper
    """
    @wraps(coro_func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:  \
            # pylint: disable=missing-docstring
        if delay:
            await asyncio.sleep(delay, loop=loop)  # type: ignore
        return await coro_func(*args, **kwargs)

    return wrapper


def get_error_code(error_field: Union[str, None]) -> Optional[int]:
    """Get the error code part of the `error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field

    :param error_field: `Error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field
    :return: The error code as an int if 3 digits can be matched at the \
    beginning of the error field, for all other cases (``None`` or invalid \
    error field) return ``None``
    """
    result = None
    if error_field is not None:
        match = re.search(r"^\d{3}", error_field)
        if match:
            result = int(match[0])
    return result


def get_error_message(error_field: Union[str, None]) -> Optional[str]:
    """Get the description part of the `error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field

    :param error_field: `Error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field
    :return: The third part of the error field as a string if it can be \
    matched otherwise return ``None``
    """
    result = None
    if error_field is not None:
        match = re.search(r"(?<=:)[^:]*$", error_field)
        if match:
            result = match[0]
    return result


def get_error_args(error_field: Union[str, None]) -> Optional[List[str]]:
    """Get the arguments part of the `error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field

    :param error_field: `Error\
    <https://docs.cometd.org/current/reference/#_code_error_code>`_, message \
    field
    :return: The second part of the error field as a list of strings if it \
    can be matched otherwise return ``None``
    """
    result = None
    if error_field is not None:
        match = re.search(r"(?<=:).*(?=:)", error_field)
        if match:
            if match[0]:
                result = match[0].split(",")
            else:
                result = []
    return result


def is_matching_response(response_message: JsonObject,
                         message: Optional[JsonObject]) -> bool:
    """Check whether the *response_message* is a response for the
    given *message*.

    :param message: A sent message
    :param response_message: A response message
    :return: True if the *response_message* is a match for *message*
             otherwise False.
    """
    if message is None or response_message is None:
        return False
    # to consider a response message as a pair of the sent message
    # their channel should match, if they contain an id field it should
    # also match (according to the specs an id is always optional),
    # and the response message should contain the successful field
    return (message["channel"] == response_message["channel"] and
            message.get("id") == response_message.get("id") and
            "successful" in response_message)


def is_server_error_message(response_message: JsonObject) -> bool:
    """Check whether the *response_message* is a server side error message

    :param response_message: A response message
    :return: True if the *response_message* is a server side error message
             otherwise False.
    """
    return not response_message.get("successful", True)


def is_event_message(response_message: JsonObject) -> bool:
    """Check whether the *response_message* is an event message

    :param response_message: A response message
    :return: True if the *response_message* is an event message
             otherwise False.
    """
    channel = response_message["channel"]
    # every message is a response message if it's not on a meta channel
    # and if it's either not on a service channel, or it's on a service channel
    # but doesn't has an id (which means that it's not a response for an
    # outgoing message) and it has a data field
    return (not channel.startswith(META_CHANNEL_PREFIX) and
            (not channel.startswith(SERVICE_CHANNEL_PREFIX) or
             "id" not in response_message) and
            "data" in response_message)


def is_auth_error_message(response_message: JsonObject) -> bool:
    """Check whether the *response_message* is an authentication error
    message

    :param response_message: A response message
    :return: True if the *response_message* is an authentication error \
    message, otherwise False.
    """
    error_code = get_error_code(response_message.get("error"))
    # Strictly speaking, only UNAUTHORIZED should be considered as an auth
    # error, but some channels can also react with FORBIDDEN for auth
    # failures. This is certainly true for /meta/handshake, and since this
    # might happen for other channels as well, it's better to stay safe
    # and treat FORBIDDEN also as a potential auth error
    return error_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)
