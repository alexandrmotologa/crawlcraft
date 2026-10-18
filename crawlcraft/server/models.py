"""Pydantic schemas and models for CrawlCraft REST and SSE endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """Request model for immediate extraction on a single URL or raw HTML."""

    url: Optional[str] = Field(None, description="Target URL to fetch and synthesize")
    html: Optional[str] = Field(None, description="Raw HTML string if already fetched")
    extract_main_only: bool = Field(True, description="Prune header, footer, and navigation boilerplate")
    allow_spa_fallback: bool = Field(True, description="Delegate to headless Chromium if empty SPA detected")
    include_selectors: Optional[List[str]] = Field(None, description="CSS selectors to whitelist and extract")
    exclude_selectors: Optional[List[str]] = Field(None, description="CSS selectors to blacklist and decompose")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers like Authorization")
    cookies: Optional[Dict[str, str]] = Field(None, description="Custom cookies for authentication")


class ExtractResponse(BaseModel):
    """Response model containing synthesized Markdown and metadata."""

    url: str
    markdown: str
    metadata: Dict[str, Any]
    rendered_with: str
    elapsed_ms: float
    cleaned_html: Optional[str] = Field(None, description="Pruned HTML DOM before markdown conversion")


class CrawlRequest(BaseModel):
    """Request model for starting an asynchronous multi-page crawl."""

    urls: List[str] = Field(..., description="One or more seed URLs to initiate the crawl")
    max_depth: int = Field(2, ge=0, le=10, description="Maximum BFS crawl depth")
    max_pages: int = Field(50, ge=1, le=1000, description="Maximum pages to crawl")
    concurrency: int = Field(8, ge=1, le=50, description="Simultaneous request concurrency")
    requests_per_second: float = Field(5.0, ge=0.1, le=50.0, description="Politeness rate limit per domain")
    same_domain_only: bool = Field(True, description="Confine crawl to the initial domain")
    allowed_domains: Optional[List[str]] = Field(None, description="Optional whitelist of domains")
    respect_robots_txt: bool = Field(True, description="Strict compliance with robots.txt")
    allow_spa_fallback: bool = Field(True, description="Headless Chromium fallback for dynamic SPAs")
    extract_main_only: bool = Field(True, description="Extract main article body")
    include_selectors: Optional[List[str]] = Field(None, description="CSS selectors to extract")
    exclude_selectors: Optional[List[str]] = Field(None, description="CSS selectors to drop")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    cookies: Optional[Dict[str, str]] = Field(None, description="Session cookies")
    from_sitemap: bool = Field(False, description="Seed the crawl queue from XML sitemaps")
    seed_from_sitemaps: Optional[bool] = Field(None, description="Alias for from_sitemap")
    webhook_url: Optional[str] = Field(None, description="Callback URL for job completion notification")

    def get_from_sitemap(self) -> bool:
        if self.seed_from_sitemaps is not None:
            return self.seed_from_sitemaps
        return self.from_sitemap


class CrawlJobResponse(BaseModel):
    """Confirmation payload returned upon job launch."""

    job_id: str
    status: str
    created_at: str


class CrawlJobStatus(BaseModel):
    """Detailed telemetry and status for an ongoing or completed crawl job."""

    job_id: str
    status: str
    crawled_count: int
    failed_count: int
    total_tokens: int
    elapsed_seconds: float
    pages: List[Dict[str, Any]]


class SitemapRequest(BaseModel):
    """Request model for discovering sitemap URLs."""

    url: str = Field(..., description="Root domain or sitemap XML URL")
    max_urls: int = Field(500, ge=1, le=5000, description="Max sitemap entries to retrieve")


class SitemapResponse(BaseModel):
    """Response containing discovered URLs from sitemap."""

    urls: List[Dict[str, Any]]
    count: int
