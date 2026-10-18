"""High-performance asynchronous HTTP client with HTTP/2 and header rotation."""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional
import httpx


USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class HttpResponse:
    """Encapsulates the response from an HTTP fetch."""

    def __init__(
        self,
        url: str,
        status_code: int,
        text: str,
        headers: Dict[str, str],
        elapsed_ms: float,
        http_version: str = "HTTP/1.1",
        is_success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.text = text
        self.headers = headers
        self.elapsed_ms = elapsed_ms
        self.http_version = http_version
        self.is_success = is_success
        self.error_message = error_message

    @property
    def content_type(self) -> str:
        for k, v in self.headers.items():
            if k.lower() == "content-type":
                return v.split(";")[0].strip().lower()
        return ""

    @property
    def is_html(self) -> bool:
        ct = self.content_type
        return "text/html" in ct or "application/xhtml+xml" in ct or ct == ""


class AsyncHttpClient:
    """Asynchronous HTTP/2 client with connection pooling, retries, and headers."""

    def __init__(
        self,
        timeout: float = 15.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        retries: int = 2,
        backoff_factor: float = 0.5,
    ) -> None:
        self.timeout = timeout
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.retries = retries
        self.backoff_factor = backoff_factor
        self._client: Optional[httpx.AsyncClient] = None

    def _get_browser_headers(self) -> Dict[str, str]:
        ua = random.choice(USER_AGENTS)
        is_firefox = "Firefox" in ua
        is_safari = "Safari" in ua and "Chrome" not in ua

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }

        if not is_firefox and not is_safari:
            headers.update({
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"' if "Windows" in ua else ('"macOS"' if "Macintosh" in ua else '"Linux"'),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })

        return headers

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
            )
            self._client = httpx.AsyncClient(
                http2=True,
                limits=limits,
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                verify=self.verify_ssl,
                proxy=self.proxy,
                follow_redirects=True,
            )
        return self._client

    async def get(
        self,
        url: str,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> HttpResponse:
        """Fetch a URL with HTTP/2, realistic headers, and exponential backoff retries."""
        client = await self._ensure_client()
        headers = self._get_browser_headers()
        if custom_headers:
            headers.update(custom_headers)

        last_error = None
        for attempt in range(self.retries + 1):
            start_time = time.perf_counter()
            try:
                resp = await client.get(url, headers=headers)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                if resp.status_code == 429 and attempt < self.retries:
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else (self.backoff_factor * (2 ** attempt))
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code >= 500 and attempt < self.retries:
                    await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                    continue

                headers_dict = {k: v for k, v in resp.headers.items()}
                http_ver = getattr(resp, "http_version", "HTTP/1.1")
                is_success = resp.status_code < 400

                return HttpResponse(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    text=resp.text,
                    headers=headers_dict,
                    elapsed_ms=elapsed_ms,
                    http_version=str(http_ver),
                    is_success=is_success,
                )

            except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as exc:
                last_error = str(exc)
                if attempt < self.retries:
                    await asyncio.sleep(self.backoff_factor * (2 ** attempt))
                else:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return HttpResponse(
                        url=url,
                        status_code=0,
                        text="",
                        headers={},
                        elapsed_ms=elapsed_ms,
                        is_success=False,
                        error_message=last_error,
                    )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return HttpResponse(
                    url=url,
                    status_code=0,
                    text="",
                    headers={},
                    elapsed_ms=elapsed_ms,
                    is_success=False,
                    error_message=str(exc),
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return HttpResponse(
            url=url,
            status_code=0,
            text="",
            headers={},
            elapsed_ms=elapsed_ms,
            is_success=False,
            error_message=last_error or "Exceeded retry budget",
        )

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncHttpClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
