"""HTTP client for the Pi-Star dashboard."""
from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=4, sock_read=7)
MAX_ATTEMPTS = 2


class PiStarError(Exception):
    """Base exception for Pi-Star communication errors."""


class PiStarAuthenticationError(PiStarError):
    """Pi-Star rejected the supplied credentials."""


class PiStarNotFoundError(PiStarError):
    """A Pi-Star endpoint does not exist."""


class PiStarConnectionError(PiStarError):
    """Pi-Star could not be reached."""


class PiStarResponseError(PiStarError):
    """Pi-Star returned an unusable response."""


def normalize_base_url(host: str) -> str:
    """Return a normalized Pi-Star base URL from a host or URL."""
    value = host.strip()
    if not value:
        raise ValueError("Pi-Star host cannot be empty")

    if "://" not in value:
        value = f"http://{value}"

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Pi-Star host must be an HTTP(S) hostname, IP, or URL")

    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


class PiStarClient:
    """Small resilient HTTP client for Pi-Star dashboard endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self.base_url = normalize_base_url(host)
        self._auth = (
            aiohttp.BasicAuth(username, password)
            if username or password
            else None
        )

    def _url(self, path: str) -> str:
        """Build an endpoint URL."""
        return f"{self.base_url}/{path.lstrip('/')}"

    async def async_get_text(self, path: str) -> str:
        """Fetch a text endpoint."""
        response = await self._async_request(path, as_json=False)
        if not isinstance(response, str):
            raise PiStarResponseError(f"Pi-Star {path} did not return text")
        return response

    async def async_get_json(self, path: str) -> Any:
        """Fetch and decode a JSON endpoint."""
        return await self._async_request(path, as_json=True)

    async def _async_request(self, path: str, *, as_json: bool) -> Any:
        """Fetch one endpoint, retrying transient failures once."""
        url = self._url(path)
        last_error: Exception | None = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                async with self._session.get(
                    url,
                    auth=self._auth,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                ) as response:
                    if response.status in {401, 403}:
                        raise PiStarAuthenticationError(
                            f"Pi-Star rejected authentication for {path}"
                        )
                    if response.status == 404:
                        raise PiStarNotFoundError(
                            f"Pi-Star endpoint {path} was not found"
                        )

                    if response.status in RETRYABLE_STATUS_CODES:
                        last_error = PiStarResponseError(
                            f"Pi-Star {path} returned HTTP {response.status}"
                        )
                        if attempt + 1 < MAX_ATTEMPTS:
                            await asyncio.sleep(0.4 * (attempt + 1))
                            continue
                        raise last_error

                    if response.status != 200:
                        raise PiStarResponseError(
                            f"Pi-Star {path} returned HTTP {response.status}"
                        )

                    if as_json:
                        try:
                            return await response.json(content_type=None)
                        except (ValueError, aiohttp.ContentTypeError) as err:
                            raise PiStarResponseError(
                                f"Pi-Star {path} returned invalid JSON"
                            ) from err

                    return await response.text(errors="replace")

            except (PiStarAuthenticationError, PiStarNotFoundError, PiStarResponseError):
                raise
            except (aiohttp.ClientError, TimeoutError) as err:
                last_error = err
                if attempt + 1 < MAX_ATTEMPTS:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                raise PiStarConnectionError(
                    f"Could not connect to Pi-Star endpoint {path}: {err}"
                ) from err

        raise PiStarConnectionError(
            f"Could not connect to Pi-Star endpoint {path}: {last_error}"
        )
