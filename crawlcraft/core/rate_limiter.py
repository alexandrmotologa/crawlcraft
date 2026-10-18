"""Per-domain token-bucket rate limiter for polite web crawling."""

import asyncio
import time
from typing import Dict
from urllib.parse import urlparse


class TokenBucket:
    """Token bucket implementation for a single domain."""

    def __init__(self, rate: float, capacity: float) -> None:
        self.rate = rate  # Tokens added per second
        self.capacity = capacity  # Maximum bucket capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Asynchronously wait until enough tokens are available, then consume them."""
        while True:
            async with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now

                # Add generated tokens
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate sleep duration needed for required tokens
                missing_tokens = tokens - self.tokens
                sleep_duration = missing_tokens / self.rate

            # Sleep outside the lock so other tasks don't block
            await asyncio.sleep(max(0.001, sleep_duration))


class DomainRateLimiter:
    """Manages independent token-bucket rate limiters across different network hosts."""

    def __init__(
        self,
        default_requests_per_second: float = 5.0,
        burst_capacity: float = 5.0,
    ) -> None:
        self.default_rate = default_requests_per_second
        self.burst_capacity = burst_capacity
        self.buckets: Dict[str, TokenBucket] = {}
        self._manager_lock = asyncio.Lock()

    @staticmethod
    def extract_domain(url_or_domain: str) -> str:
        """Extracts the network location (host) from a URL or raw domain string."""
        if "://" in url_or_domain:
            parsed = urlparse(url_or_domain)
            return parsed.netloc.lower()
        return url_or_domain.split("/")[0].lower()

    async def _get_or_create_bucket(self, domain: str) -> TokenBucket:
        async with self._manager_lock:
            if domain not in self.buckets:
                self.buckets[domain] = TokenBucket(
                    rate=self.default_rate,
                    capacity=self.burst_capacity,
                )
            return self.buckets[domain]

    async def acquire(self, url_or_domain: str) -> None:
        """Wait until a request to the target domain is permitted under politeness limits."""
        domain = self.extract_domain(url_or_domain)
        bucket = await self._get_or_create_bucket(domain)
        await bucket.acquire(1.0)

    def set_domain_rate(self, domain: str, requests_per_second: float) -> None:
        """Override rate limit for a specific domain."""
        clean_domain = self.extract_domain(domain)
        self.buckets[clean_domain] = TokenBucket(
            rate=requests_per_second,
            capacity=max(1.0, requests_per_second),
        )
