"""Pydantic schemas and models for CrawlCraft REST and SSE endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """Request model for immediate extraction on a single URL or raw HTML."""

    url: Optional[str] = Field(None, description="Target URL to fetch and synthesize")
    html: Optional[str] = Field(None, description="Raw HTML string if already fetched")
    extract_main_only: bool = Field(True, description="Prune header, footer, and navigation boilerplate")
    allow_spa_fallback: bool = Field(True, description="Delegate to headless Chromium if empty SPA detected")


class ExtractResponse(BaseModel):
    """Response model containing synthesized Markdown and metadata."""

    url: str
    markdown: str
    metadata: Dict[str, Any]
    rendered_with: str
    elapsed_ms: float


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
