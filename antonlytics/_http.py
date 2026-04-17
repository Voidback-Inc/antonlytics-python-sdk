"""
Antonlytics SDK — HTTP transport layer.

Provides both synchronous (httpx.Client) and asynchronous (httpx.AsyncClient)
request methods with:
  - automatic retry with exponential backoff on 5xx / network errors
  - timeout enforcement
  - X-Api-Key header injection
  - structured error parsing
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from .exceptions import (
    AntoError, NetworkError, TimeoutError as AntoTimeoutError,
    ServerError, error_from_response,
)

SDK_VERSION = "1.0.0"
RETRY_ON = {429, 500, 502, 503, 504}


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "X-Api-Key": api_key,
        "X-Sdk-Version": SDK_VERSION,
        "X-Sdk-Language": "python",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _parse_error(response: httpx.Response) -> AntoError:
    try:
        body = response.json()
    except Exception:
        body = {}
    return error_from_response(response.status_code, body)


def _should_retry(status: int, attempt: int, max_retries: int) -> bool:
    return status in RETRY_ON and attempt < max_retries


def _backoff(attempt: int) -> float:
    """Exponential backoff: 0.3s, 0.6s, 1.2s …"""
    return 0.3 * (2 ** attempt)


# ── Synchronous client ────────────────────────────────────────────────────────

class HttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float,
        max_retries: int,
        debug: bool,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = _build_headers(api_key)
        self._timeout = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._client = httpx.Client(
            base_url=f"{self._base}/api/v1",
            headers=self._headers,
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        if self._debug:
            print(f"[Antonlytics] → {method} {path}", json or "")

        attempt = 0
        while True:
            try:
                response = self._client.request(method, path, params=params, json=json)
            except httpx.TimeoutException:
                raise AntoTimeoutError(self._timeout)
            except httpx.RequestError as e:
                raise NetworkError(str(e)) from e

            if self._debug:
                print(f"[Antonlytics] ← {response.status_code} {path}")

            if _should_retry(response.status_code, attempt, self._max_retries):
                time.sleep(_backoff(attempt))
                attempt += 1
                continue

            if not response.is_success:
                raise _parse_error(response)

            if response.status_code == 204:
                return None

            return response.json()

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Any = None) -> Any:
        return self.request("POST", path, json=json)

    def patch(self, path: str, json: Any = None) -> Any:
        return self.request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)


# ── Asynchronous client ───────────────────────────────────────────────────────

class AsyncHttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float,
        max_retries: int,
        debug: bool,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = _build_headers(api_key)
        self._timeout = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._client = httpx.AsyncClient(
            base_url=f"{self._base}/api/v1",
            headers=self._headers,
            timeout=timeout,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncHttpClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        import asyncio

        if self._debug:
            print(f"[Antonlytics] → {method} {path}", json or "")

        attempt = 0
        while True:
            try:
                response = await self._client.request(method, path, params=params, json=json)
            except httpx.TimeoutException:
                raise AntoTimeoutError(self._timeout)
            except httpx.RequestError as e:
                raise NetworkError(str(e)) from e

            if self._debug:
                print(f"[Antonlytics] ← {response.status_code} {path}")

            if _should_retry(response.status_code, attempt, self._max_retries):
                await asyncio.sleep(_backoff(attempt))
                attempt += 1
                continue

            if not response.is_success:
                raise _parse_error(response)

            if response.status_code == 204:
                return None

            return response.json()

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self.request("POST", path, json=json)

    async def patch(self, path: str, json: Any = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)
