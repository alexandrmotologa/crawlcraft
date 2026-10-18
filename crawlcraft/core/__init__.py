"""Core crawling engine components for CrawlCraft."""

from crawlcraft.core.http_client import AsyncHttpClient
from crawlcraft.core.rate_limiter import DomainRateLimiter
from crawlcraft.core.robots import RobotsManager
from crawlcraft.core.deduplicator import ContentDeduplicator, normalize_url
from crawlcraft.core.crawler import AsyncCrawler, CrawlConfig, CrawledPage
from crawlcraft.core.sitemap import (
    fetch_and_parse_sitemaps,
    discover_and_parse_sitemaps,
    parse_sitemap_xml,
    parse_feed_xml,
)

__all__ = [
    "AsyncHttpClient",
    "DomainRateLimiter",
    "RobotsManager",
    "ContentDeduplicator",
    "normalize_url",
    "AsyncCrawler",
    "CrawlConfig",
    "CrawledPage",
    "fetch_and_parse_sitemaps",
    "discover_and_parse_sitemaps",
    "parse_sitemap_xml",
    "parse_feed_xml",
]
