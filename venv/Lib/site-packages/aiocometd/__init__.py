"""CometD client for asyncio"""
import logging

from aiocometd._metadata import VERSION as __version__  # noqa: F401
from aiocometd.client import Client  # noqa: F401
from aiocometd.constants import ConnectionType  # noqa: F401
from aiocometd.extensions import Extension, AuthExtension  # noqa: F401
from aiocometd import transports  # noqa: F401

# Create a default handler to avoid warnings in applications without logging
# configuration
logging.getLogger(__name__).addHandler(logging.NullHandler())
