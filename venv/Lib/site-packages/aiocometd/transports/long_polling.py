"""Long polling transport class definition"""
import asyncio
import logging
from typing import Any

import aiohttp

from aiocometd.constants import ConnectionType
from aiocometd.exceptions import TransportError
from aiocometd.typing import JsonObject
from aiocometd.transports.registry import register_transport
from aiocometd.transports.base import TransportBase, Payload, Headers


LOGGER = logging.getLogger(__name__)


@register_transport(ConnectionType.LONG_POLLING)
class LongPollingTransport(TransportBase):
    """Long-polling type transport"""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        #: semaphore to limit the number of concurrent HTTP connections to 2
        self._http_semaphore = asyncio.Semaphore(2, loop=self._loop)

    async def _send_final_payload(self, payload: Payload, *,
                                  headers: Headers) -> JsonObject:
        try:
            session = await self._get_http_session()
            async with self._http_semaphore:
                response = await session.post(self._url, json=payload,
                                              ssl=self.ssl, headers=headers,
                                              timeout=self.request_timeout)
            response_payload = await response.json(loads=self._json_loads)
            headers = response.headers
        except aiohttp.client_exceptions.ClientError as error:
            LOGGER.warning("Failed to send payload, %s", error)
            raise TransportError(str(error)) from error
        response_message = await self._consume_payload(
            response_payload,
            headers=headers,
            find_response_for=payload[0]
        )

        if response_message is None:
            error_message = "No response message received for the " \
                            "first message in the payload"
            LOGGER.warning(error_message)
            raise TransportError(error_message)
        return response_message
