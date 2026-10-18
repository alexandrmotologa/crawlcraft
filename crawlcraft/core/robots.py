"""Asynchronous robots.txt parser and policy manager (RFC 9309 compliant)."""

import asyncio
import fnmatch
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import httpx


class RobotsRule:
    """Represents an Allow or Disallow rule in robots.txt."""

    def __init__(self, path_pattern: str, is_allowed: bool) -> None:
        self.raw_pattern = path_pattern.strip()
        self.is_allowed = is_allowed

        # Compile pattern to regex according to RFC 9309
        # In robots.txt, '*' matches any sequence, '$' matches end of URL
        escaped = re.escape(self.raw_pattern).replace(r"\*", ".*")
        if escaped.endswith(r"\$"):
            escaped = escaped[:-2] + "$"
        else:
            escaped = escaped + ".*"
        self._regex = re.compile("^" + escaped)

    def matches(self, path: str) -> bool:
        if not self.raw_pattern:
            return False
        return bool(self._regex.match(path))


class RobotsPolicy:
    """Robots.txt rules and crawl-delay for a specific domain."""

    def __init__(self, content: str, user_agent: str = "*") -> None:
        self.rules: List[RobotsRule] = []
        self.crawl_delay: Optional[float] = None
        self.sitemaps: List[str] = []
        self.timestamp = time.monotonic()
        self._parse(content, user_agent)

    def _parse(self, content: str, target_ua: str) -> None:
        current_uas: List[str] = []
        in_matching_group = False
        target_ua_lower = target_ua.lower()

        lines = content.splitlines()
        for raw_line in lines:
            line = raw_line.split("#")[0].strip()
            if not line:
                current_uas = []
                in_matching_group = False
                continue

            if ":" not in line:
                continue

            field, value = line.split(":", 1)
            field = field.strip().lower()
            val = value.strip()

            if field == "user-agent":
                ua = val.lower()
                current_uas.append(ua)
                if ua == "*" or ua == target_ua_lower or target_ua_lower.startswith(ua):
                    in_matching_group = True
            elif field == "sitemap":
                if val:
                    self.sitemaps.append(val)
            elif in_matching_group:
                if field == "disallow":
                    if val:
                        self.rules.append(RobotsRule(val, is_allowed=False))
                    else:
                        # Empty Disallow means allow all
                        self.rules.append(RobotsRule("/", is_allowed=True))
                elif field == "allow":
                    if val:
                        self.rules.append(RobotsRule(val, is_allowed=True))
                elif field == "crawl-delay":
                    try:
                        self.crawl_delay = float(val)
                    except ValueError:
                        pass

        # Sort rules so most specific (longest pattern) takes precedence, then Allow over Disallow
        self.rules.sort(key=lambda r: (len(r.raw_pattern), 1 if r.is_allowed else 0), reverse=True)

    def is_allowed(self, path: str) -> bool:
        if not path.startswith("/"):
            path = "/" + path

        for rule in self.rules:
            if rule.matches(path):
                return rule.is_allowed

        # Default is allowed if no rule matches
        return True


class RobotsManager:
    """Manages asynchronous fetching, parsing, and caching of robots.txt files."""

    def __init__(self, cache_ttl_seconds: float = 3600.0, user_agent: str = "*") -> None:
        self.cache_ttl = cache_ttl_seconds
        self.user_agent = user_agent
        self.policies: Dict[str, Tuple[RobotsPolicy, float]] = {}
        self.lock = asyncio.Lock()

    async def can_fetch(self, url: str, client: Optional[httpx.AsyncClient] = None) -> bool:
        """Determines if the given URL is permissible to crawl according to robots.txt."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True

        domain = parsed.netloc.lower()
        policy = await self._get_policy(parsed.scheme, domain, client)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        return policy.is_allowed(path)

    async def _get_policy(
        self,
        scheme: str,
        domain: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> RobotsPolicy:
        now = time.monotonic()
        async with self.lock:
            if domain in self.policies:
                cached_policy, cached_time = self.policies[domain]
                if (now - cached_time) < self.cache_ttl:
                    return cached_policy

        # Fetch robots.txt
        robots_url = f"{scheme}://{domain}/robots.txt"
        content = ""
        try:
            if client is not None and not client.is_closed:
                resp = await client.get(robots_url, timeout=5.0)
                if resp.status_code == 200:
                    content = resp.text
            else:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as temp_client:
                    resp = await temp_client.get(robots_url)
                    if resp.status_code == 200:
                        content = resp.text
        except Exception:
            # If robots.txt cannot be retrieved or server fails, assume allowed
            content = ""

        policy = RobotsPolicy(content, self.user_agent)
        async with self.lock:
            self.policies[domain] = (policy, now)

        return policy
