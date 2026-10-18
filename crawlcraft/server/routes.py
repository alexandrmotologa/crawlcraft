"""FastAPI route handlers for synchronous extraction, crawl jobs, and SSE streaming."""

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from crawlcraft.browser.headless_pool import HeadlessBrowserPool
from crawlcraft.browser.spa_detector import detect_spa_shell
from crawlcraft.core.crawler import AsyncCrawler, CrawlConfig, CrawledPage
from crawlcraft.core.http_client import AsyncHttpClient
from crawlcraft.extractor.markdown import html_to_markdown
from crawlcraft.extractor.metadata import extract_metadata
from crawlcraft.server.models import (
    CrawlJobResponse,
    CrawlJobStatus,
    CrawlRequest,
    ExtractRequest,
    ExtractResponse,
)
from crawlcraft.server.sse import format_sse

router = APIRouter(prefix="/v1", tags=["CrawlCraft"])


class JobRecord:
    """In-memory tracking record for a crawl job."""

    def __init__(self, job_id: str, request: CrawlRequest) -> None:
        self.job_id = job_id
        self.request = request
        self.status = "queued"  # queued, running, completed, failed, cancelled
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.start_time = time.monotonic()
        self.end_time: Optional[float] = None
        self.crawled_count = 0
        self.failed_count = 0
        self.total_tokens = 0
        self.pages: List[CrawledPage] = []
        self.event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.crawler: Optional[AsyncCrawler] = None


# In-memory storage for active and completed crawl jobs
JOBS: Dict[str, JobRecord] = {}


@router.post("/extract", response_model=ExtractResponse)
async def extract_content(req: ExtractRequest) -> ExtractResponse:
    """Extracts clean Markdown and structured metadata from a URL or raw HTML string."""
    if not req.url and not req.html:
        raise HTTPException(status_code=400, detail="Must provide either 'url' or 'html' in request")

    start_time = time.perf_counter()
    html_content = req.html or ""
    rendered_with = "raw_html"
    target_url = req.url or "http://localhost/raw"

    if req.url and not req.html:
        async with AsyncHttpClient() as client:
            resp = await client.get(req.url)
            if not resp.is_success:
                raise HTTPException(status_code=502, detail=f"Failed to fetch {req.url}: {resp.error_message}")
            html_content = resp.text
            rendered_with = resp.http_version

            # Check if SPA fallback is warranted
            if req.allow_spa_fallback:
                is_spa, _ = detect_spa_shell(html_content)
                if is_spa:
                    pool = HeadlessBrowserPool()
                    try:
                        rendered = await pool.render_url(req.url)
                        if rendered:
                            html_content = rendered
                            rendered_with = "playwright_chromium"
                    finally:
                        await pool.close()

    markdown = html_to_markdown(html_content, base_url=target_url, extract_main_only=req.extract_main_only)
    meta = extract_metadata(html_content, url=target_url, text_content=markdown)
    elapsed = (time.perf_counter() - start_time) * 1000.0

    return ExtractResponse(
        url=target_url,
        markdown=markdown,
        metadata=meta.to_dict(),
        rendered_with=rendered_with,
        elapsed_ms=round(elapsed, 2),
    )


async def _run_crawl_job(job: JobRecord) -> None:
    job.status = "running"
    config = CrawlConfig(
        start_urls=job.request.urls,
        max_depth=job.request.max_depth,
        max_pages=job.request.max_pages,
        concurrency=job.request.concurrency,
        requests_per_second=job.request.requests_per_second,
        same_domain_only=job.request.same_domain_only,
        allowed_domains=job.request.allowed_domains,
        respect_robots_txt=job.request.respect_robots_txt,
        allow_spa_fallback=job.request.allow_spa_fallback,
        extract_main_only=job.request.extract_main_only,
    )

    async def on_page_scraped(page: CrawledPage) -> None:
        job.crawled_count += 1
        page_tokens = page.metadata.token_stats.get("token_count", 0)
        job.total_tokens += page_tokens
        job.pages.append(page)
        await job.event_queue.put({
            "type": "page",
            "data": page.to_dict(),
            "crawled_count": job.crawled_count,
            "total_tokens": job.total_tokens,
        })

    crawler = AsyncCrawler(config=config, on_page=on_page_scraped)
    job.crawler = crawler

    try:
        await crawler.run()
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        await job.event_queue.put({"type": "error", "message": str(exc)})
    finally:
        job.end_time = time.monotonic()
        await job.event_queue.put({"type": "done", "status": job.status, "crawled_count": job.crawled_count})


@router.post("/crawl", response_model=CrawlJobResponse)
async def start_crawl(req: CrawlRequest) -> CrawlJobResponse:
    """Launches an asynchronous bounded BFS crawl job."""
    if not req.urls:
        raise HTTPException(status_code=400, detail="Must supply at least one seed URL")

    job_id = uuid.uuid4().hex[:12]
    job_record = JobRecord(job_id=job_id, request=req)
    JOBS[job_id] = job_record

    asyncio.create_task(_run_crawl_job(job_record))

    return CrawlJobResponse(
        job_id=job_id,
        status="queued",
        created_at=job_record.created_at,
    )


@router.get("/crawl/{job_id}/status", response_model=CrawlJobStatus)
async def get_crawl_status(job_id: str) -> CrawlJobStatus:
    """Queries telemetry and summary status for a specific crawl job."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    end = job.end_time or time.monotonic()
    elapsed = round(end - job.start_time, 2)

    return CrawlJobStatus(
        job_id=job.job_id,
        status=job.status,
        crawled_count=job.crawled_count,
        failed_count=job.failed_count,
        total_tokens=job.total_tokens,
        elapsed_seconds=elapsed,
        pages=[p.to_dict() for p in job.pages],
    )


@router.get("/crawl/{job_id}/stream")
async def stream_crawl_events(job_id: str) -> StreamingResponse:
    """Real-time Server-Sent Events (SSE) feed of pages crawled in this job."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Yield already completed pages first if reconnecting
        for page in job.pages:
            yield format_sse({"type": "page", "data": page.to_dict()}, event="page")

        if job.status in ("completed", "failed", "cancelled"):
            yield format_sse({"type": "done", "status": job.status}, event="done")
            return

        while True:
            try:
                event = await asyncio.wait_for(job.event_queue.get(), timeout=2.0)
                event_type = event.get("type", "update")
                yield format_sse(event, event=event_type)
                if event_type == "done":
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat comment
                yield ": ping\n\n"
                if job.status in ("completed", "failed", "cancelled"):
                    yield format_sse({"type": "done", "status": job.status}, event="done")
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/crawl/{job_id}/export")
async def export_crawl(job_id: str, format: str = Query("jsonl", pattern="^(jsonl|markdown)$")) -> Response:
    """Downloads the crawled dataset formatted as JSONL or a consolidated Markdown document."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if format == "jsonl":
        lines = [json.dumps(p.to_dict()) for p in job.pages]
        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="crawlcraft_{job_id}.jsonl"'},
        )
    else:
        # Markdown export
        sections = []
        for p in job.pages:
            title = p.metadata.title or p.url
            sections.append(f"# {title}\n\n**Source:** {p.url}\n\n{p.markdown}\n\n---\n")
        content = "\n".join(sections)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="crawlcraft_{job_id}.md"'},
        )
