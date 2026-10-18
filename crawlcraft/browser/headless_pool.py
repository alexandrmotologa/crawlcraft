"""Lazy Playwright Chromium browser pool for rendering dynamic SPA pages."""

import asyncio
import logging
from typing import Optional
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

logger = logging.getLogger(__name__)


class HeadlessBrowserPool:
    """Manages an on-demand Playwright Chromium browser instance with bounded concurrency."""

    def __init__(
        self,
        max_concurrent_pages: int = 3,
        headless: bool = True,
        block_media: bool = True,
    ) -> None:
        self.max_concurrent_pages = max_concurrent_pages
        self.headless = headless
        self.block_media = block_media
        self._semaphore = asyncio.Semaphore(max_concurrent_pages)
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()

            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                        "--no-zygote",
                    ],
                )
            return self._browser

    async def render_url(
        self,
        url: str,
        timeout_ms: int = 15000,
        wait_until: str = "domcontentloaded",
    ) -> Optional[str]:
        """Renders a dynamic URL in headless Chromium and returns fully hydrated HTML."""
        async with self._semaphore:
            browser = await self._ensure_browser()
            context: Optional[BrowserContext] = None
            page = None
            try:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                )

                page = await context.new_page()

                # Speed up rendering by aborting images, fonts, and stylesheets if media blocking enabled
                if self.block_media:
                    await page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type in ("image", "media", "font")
                        else route.continue_(),
                    )

                await page.goto(url, wait_until=wait_until, timeout=timeout_ms)

                # Small settle time for reactive DOM frameworks (React, Vue, Angular)
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    # Ignore timeout on networkidle if page continues streaming background analytics
                    pass

                content = await page.content()
                return content

            except Exception as exc:
                logger.warning("Headless browser rendering failed for %s: %s", url, exc)
                return None
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

    async def close(self) -> None:
        """Closes the browser pool and releases Playwright resources."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
