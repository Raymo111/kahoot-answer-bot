"""Type definitions"""
from typing import List, Union, Callable, Awaitable, Any, Dict
import ssl as ssl_module

import aiohttp

from aiocometd.constants import ConnectionType


#: Coroutine function
CoroFunction = Callable[..., Awaitable[Any]]
#: JSON object value
JsonObject = Dict[str, Any]
#: JSON serializer function
JsonDumper = Callable[[JsonObject], str]
#: JSON deserializer function
JsonLoader = Callable[[str], JsonObject]
#: Message payload (list of messages)
Payload = List[JsonObject]
#: Header values
Headers = Dict[str, str]
#: Connection type specification
ConnectionTypeSpec = Union[ConnectionType, List[ConnectionType]]
#: SSL validation mode
SSLValidationMode = Union[ssl_module.SSLContext, aiohttp.Fingerprint, bool]
