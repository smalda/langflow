import asyncio
import logging
import time
from typing import Any, Dict, Optional, Union

import httpx
from httpx import URL, Cookies, Headers, QueryParams, Response

logger = logging.getLogger(__name__)


class AsyncRetryingClient(httpx.AsyncClient):
    def __init__(
        self,
        *args,
        max_retries: int = 5,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 32.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        logger.info(
            f"Initialized AsyncRetryingClient with base_url: {kwargs.get('base_url')}"
        )

    async def _request_with_retry(
        self,
        method: str,
        url: Union[str, URL],
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> Response:
        retry_delay = self.initial_retry_delay
        full_url = str(self.base_url) + str(url) if self.base_url else str(url)

        if max_retries is None:
            max_retries = self.max_retries

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Attempting {method} request to {full_url} (attempt {attempt + 1}/{self.max_retries})"
                )
                response = await super().request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.ConnectError as e:
                logger.warning(f"Connection error to {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error from {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise

            logger.info(f"Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, self.max_retry_delay)

    async def request(self, *args, **kwargs) -> Response:
        return await self._request_with_retry(*args, **kwargs)

    async def get(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("GET", *args, **kwargs)

    async def post(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("POST", *args, **kwargs)

    async def put(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("PUT", *args, **kwargs)

    async def patch(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("PATCH", *args, **kwargs)

    async def delete(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("DELETE", *args, **kwargs)

    async def head(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("HEAD", *args, **kwargs)

    async def options(self, *args, **kwargs) -> Response:
        return await self._request_with_retry("OPTIONS", *args, **kwargs)


class RetryingClient(httpx.Client):
    def __init__(
        self,
        *args,
        max_retries: int = 5,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 32.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        logger.info(
            f"Initialized RetryingClient with base_url: {kwargs.get('base_url')}"
        )

    def _request_with_retry(
        self,
        method: str,
        url: Union[str, URL],
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> Response:
        retry_delay = self.initial_retry_delay
        full_url = str(self.base_url) + str(url) if self.base_url else str(url)

        if max_retries is None:
            max_retries = self.max_retries

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Attempting {method} request to {full_url} (attempt {attempt + 1}/{self.max_retries})"
                )
                response = super().request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.ConnectError as e:
                logger.warning(f"Connection error to {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error from {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to {full_url}: {e}")
                if attempt == max_retries - 1:
                    raise

            logger.info(f"Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, self.max_retry_delay)

    def request(self, *args, **kwargs) -> Response:
        return self._request_with_retry(*args, **kwargs)

    def get(self, *args, **kwargs) -> Response:
        return self._request_with_retry("GET", *args, **kwargs)

    def post(self, *args, **kwargs) -> Response:
        return self._request_with_retry("POST", *args, **kwargs)

    def put(self, *args, **kwargs) -> Response:
        return self._request_with_retry("PUT", *args, **kwargs)

    def patch(self, *args, **kwargs) -> Response:
        return self._request_with_retry("PATCH", *args, **kwargs)

    def delete(self, *args, **kwargs) -> Response:
        return self._request_with_retry("DELETE", *args, **kwargs)

    def head(self, *args, **kwargs) -> Response:
        return self._request_with_retry("HEAD", *args, **kwargs)

    def options(self, *args, **kwargs) -> Response:
        return self._request_with_retry("OPTIONS", *args, **kwargs)
