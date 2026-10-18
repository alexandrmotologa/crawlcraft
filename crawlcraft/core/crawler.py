"""Asynchronous bounded BFS web crawler orchestrator with SPA fallback."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse
from selectolax.lexbor import LexborHTMLParser

from crawlcraft.browser.headless_pool import HeadlessBrowserPool
from crawlcraft.browser.spa_detector import detect_spa_shell
from crawlcraft.core.deduplicator import ContentDeduplicator, normalize_url
from crawlcraft.core.http_client import AsyncHttpClient
from crawlcraft.core.rate_limiter import DomainRateLimiter
from crawlcraft.core.robots import RobotsManager
from crawlcraft.core.sitemap import fetch_and_parse_sitemaps
from crawlcraft.extractor.markdown import MarkdownConverter
from crawlcraft.extractor.metadata import PageMetadata, extract_metadata

logger = logging.getLogger(__name__)


class CrawlConfig:
    """Configuration options for crawl execution."""

    def __init__(
        self,
        start_urls: List[str],
        max_depth: int = 2,
        max_pages: int = 50,
        concurrency: int = 8,
        requests_per_second: float = 5.0,
        same_domain_only: bool = True,
        allowed_domains: Optional[List[str]] = None,
        respect_robots_txt: bool = True,
        allow_spa_fallback: bool = True,
        extract_main_only: bool = True,
        timeout_seconds: float = 15.0,
        include_selectors: Optional[List[str]] = None,
        exclude_selectors: Optional[List[str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        from_sitemap: bool = False,
        webhook_url: Optional[str] = None,
    ) -> None:
        self.start_urls = start_urls
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.requests_per_second = requests_per_second
        self.same_domain_only = same_domain_only
        self.allowed_domains = [d.lower() for d in allowed_domains] if allowed_domains else []
        self.respect_robots_txt = respect_robots_txt
        self.allow_spa_fallback = allow_spa_fallback
        self.extract_main_only = extract_main_only
        self.timeout_seconds = timeout_seconds
        self.include_selectors = include_selectors
        self.exclude_selectors = exclude_selectors
        self.custom_headers = custom_headers
        self.cookies = cookies
        self.from_sitemap = from_sitemap
        self.webhook_url = webhook_url


class CrawledPage:
    """Represents a successfully extracted and synthesized web page."""

    def __init__(
        self,
        url: str,
        status_code: int,
        depth: int,
        markdown: str,
        metadata: PageMetadata,
        rendered_with: str = "http2",
        elapsed_ms: float = 0.0,
        links: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.depth = depth
        self.markdown = markdown
        self.metadata = metadata
        self.rendered_with = rendered_with
        self.elapsed_ms = elapsed_ms
        self.links = links or []
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "depth": self.depth,
            "markdown": self.markdown,
            "metadata": self.metadata.to_dict(),
            "rendered_with": self.rendered_with,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "links_count": len(self.links),
            "error": self.error,
        }


class AsyncCrawler:
    """High-throughput asynchronous web crawler with semantic markdown synthesis."""

    def __init__(
        self,
        config: CrawlConfig,
        on_page: Optional[Callable[[CrawledPage], Any]] = None,
    ) -> None:
        self.config = config
        self.on_page = on_page

        self.http_client = AsyncHttpClient(
            timeout=config.timeout_seconds,
            max_connections=config.concurrency * 2,
        )
        self.rate_limiter = DomainRateLimiter(
            default_requests_per_second=config.requests_per_second,
        )
        self.robots_manager = RobotsManager()
        self.deduplicator = ContentDeduplicator()
        self.browser_pool = HeadlessBrowserPool(max_concurrent_pages=3)

        self.queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self.crawled_count = 0
        self.failed_count = 0
        self.results: List[CrawledPage] = []
        self.is_running = False
        self._semaphore = asyncio.Semaphore(config.concurrency)
        self._initial_domains: Set[str] = set()

    def _is_domain_allowed(self, target_url: str) -> bool:
        parsed = urlparse(target_url)
        domain = parsed.netloc.lower()

        if self.config.allowed_domains:
            return any(domain == d or domain.endswith("." + d) for d in self.config.allowed_domains)

        if self.config.same_domain_only:
            return any(domain == d or domain.endswith("." + d) for d in self._initial_domains)

        return True

    def _extract_page_links(self, html: str, base_url: str) -> List[str]:
        parser = LexborHTMLParser(html)
        links: List[str] = []

        for a_node in parser.css("a"):
            href = a_node.attributes.get("href", "").strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            normalized = normalize_url(href, base_url=base_url)
            parsed = urlparse(normalized)
            if parsed.scheme in ("http", "https") and self._is_domain_allowed(normalized):
                links.append(normalized)

        return links

    async def _process_url(self, url: str, depth: int) -> Optional[CrawledPage]:
        async with self._semaphore:
            if self.crawled_count >= self.config.max_pages:
                return None

            # Robots.txt compliance check
            if self.config.respect_robots_txt:
                can_crawl = await self.robots_manager.can_fetch(url)
                if not can_crawl:
                    logger.info("URL blocked by robots.txt: %s", url)
                    return None

            # Domain rate limit wait
            await self.rate_limiter.acquire(url)

            # Step 1: Attempt ultra-fast HTTP/2 fetch
            response = await self.http_client.get(
                url,
                custom_headers=self.config.custom_headers,
                cookies=self.config.cookies,
            )

            if not response.is_success:
                self.failed_count += 1
                return CrawledPage(
                    url=url,
                    status_code=response.status_code,
                    depth=depth,
                    markdown="",
                    metadata=PageMetadata(),
                    elapsed_ms=response.elapsed_ms,
                    error=response.error_message or f"HTTP {response.status_code}",
                )

            html_content = response.text
            rendered_with = response.http_version

            # Step 2: Check for empty SPA shells demanding JavaScript execution
            if self.config.allow_spa_fallback:
                is_spa, reason = detect_spa_shell(html_content)
                if is_spa:
                    logger.info("SPA shell detected for %s (%s). Falling back to headless Chromium...", url, reason)
                    rendered_html = await self.browser_pool.render_url(url)
                    if rendered_html and len(rendered_html.strip()) > len(html_content.strip()):
                        html_content = rendered_html
                        rendered_with = "playwright_chromium"

            # Step 3: Markdown conversion & content synthesis with selectors
            converter = MarkdownConverter(base_url=url)
            markdown = converter.convert(
                html_content,
                extract_main_only=self.config.extract_main_only,
                include_selectors=self.config.include_selectors,
                exclude_selectors=self.config.exclude_selectors,
            )

            # Step 4: Near-duplicate content check using SimHash
            is_dup, orig_url = self.deduplicator.is_content_duplicate(markdown)
            if is_dup:
                logger.info("Skipping near-duplicate content for %s (matches %s)", url, orig_url)
                return None
            self.deduplicator.record_content(url, markdown)

            # Step 5: Metadata extraction and token estimation
            metadata = extract_metadata(html_content, url=url, text_content=markdown)

            # Step 6: Extract links if depth permits
            discovered_links: List[str] = []
            if depth < self.config.max_depth:
                discovered_links = self._extract_page_links(html_content, base_url=url)
                for link in discovered_links:
                    if not self.deduplicator.is_url_seen(link):
                        self.deduplicator.mark_url_seen(link)
                        await self.queue.put((link, depth + 1))

            crawled_page = CrawledPage(
                url=url,
                status_code=response.status_code,
                depth=depth,
                markdown=markdown,
                metadata=metadata,
                rendered_with=rendered_with,
                elapsed_ms=response.elapsed_ms,
                links=discovered_links,
            )

            self.crawled_count += 1
            self.results.append(crawled_page)

            if self.on_page:
                try:
                    res = self.on_page(crawled_page)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as exc:
                    logger.error("Error in on_page callback: %s", exc)

            return crawled_page

    async def _worker(self) -> None:
        while self.is_running and self.crawled_count < self.config.max_pages:
            try:
                url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if self.queue.empty():
                    break
                continue

            try:
                await self._process_url(url, depth)
            except Exception as exc:
                logger.error("Unexpected error processing %s: %s", url, exc)
                self.failed_count += 1
            finally:
                self.queue.task_done()

    async def run(self) -> List[CrawledPage]:
        """Runs the bounded crawl process until complete or capped by max_pages."""
        self.is_running = True
        self.results.clear()
        self.crawled_count = 0
        self.failed_count = 0

        # Initialize seed domains
        for url in self.config.start_urls:
            domain = urlparse(url).netloc.lower()
            if domain:
                self._initial_domains.add(domain)

            if not self.config.from_sitemap:
                normalized = normalize_url(url)
                self.deduplicator.mark_url_seen(normalized)
                await self.queue.put((normalized, 0))

        # If from_sitemap is enabled, discover and seed queue from XML sitemaps
        if self.config.from_sitemap:
            for seed_url in self.config.start_urls:
                try:
                    sitemap_entries = await fetch_and_parse_sitemaps(seed_url, max_urls=self.config.max_pages)
                    for entry in sitemap_entries:
                        if not self.deduplicator.is_url_seen(entry.url):
                            self.deduplicator.mark_url_seen(entry.url)
                            await self.queue.put((entry.url, 0))
                except Exception as exc:
                    logger.warning("Failed to fetch sitemap for %s: %s", seed_url, exc)

        # Launch worker tasks up to concurrency limit
        workers = [asyncio.create_task(self._worker()) for _ in range(self.config.concurrency)]

        await self.queue.join()
        self.is_running = False

        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        # Trigger webhook notification if configured
        if self.config.webhook_url:
            try:
                import httpx
                summary = {
                    "event": "crawl_completed",
                    "crawled_count": self.crawled_count,
                    "failed_count": self.failed_count,
                    "total_tokens": sum(p.metadata.token_stats.get("token_count", 0) for p in self.results),
                    "urls": [p.url for p in self.results],
                }
                async with httpx.AsyncClient(timeout=5.0) as hook_client:
                    await hook_client.post(self.config.webhook_url, json=summary)
            except Exception as exc:
                logger.warning("Webhook POST to %s failed: %s", self.config.webhook_url, exc)

        # Cleanup resources
        await self.http_client.close()
        await self.browser_pool.close()

        return self.results

    async def stop(self) -> None:
        """Stops the crawl and releases all client and browser pools."""
        self.is_running = False
        await self.http_client.close()
        await self.browser_pool.close()
