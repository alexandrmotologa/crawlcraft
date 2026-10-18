"""Automated screenshot and demo GIF capture script using Playwright and FFmpeg."""

import asyncio
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(".").resolve()))

from playwright.async_api import async_playwright
import uvicorn
from crawlcraft.server.app import app


class ServerThread(threading.Thread):
    def __init__(self, port: int = 8889):
        super().__init__(daemon=True)
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


async def main():
    port = 8889
    server_thread = ServerThread(port=port)
    server_thread.start()
    time.sleep(1.5)

    images_dir = Path("docs/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path("docs/images/_frames")
    frames_dir.mkdir(parents=True, exist_ok=True)

    print("Launching Playwright Chromium...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Experience (1440x900)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print(f"Navigating to http://127.0.0.1:{port}...")
        await page.goto(f"http://127.0.0.1:{port}")
        await page.wait_for_selector("input[type='url']")
        await asyncio.sleep(0.5)

        # Frame 1: Initial load
        await page.screenshot(path=str(frames_dir / "frame_01.png"))

        # Click Single Extract
        extract_button = page.locator("button:has-text('Single Extract')")
        if await extract_button.count() > 0:
            await extract_button.click()
            await asyncio.sleep(0.3)

        # Click Extract Document
        launch_button = page.locator("button:has-text('Extract Document')")
        if await launch_button.count() > 0:
            await launch_button.click()
            print("Extraction triggered...")

        # Wait for results to populate
        await page.wait_for_selector("text=cl100k Tokens", timeout=10000)
        await asyncio.sleep(0.8)

        # Capture high-res desktop dashboard screenshot
        dashboard_png = images_dir / "crawlcraft_dashboard.png"
        await page.screenshot(path=str(dashboard_png))
        print(f"Saved desktop dashboard screenshot to {dashboard_png}")

        # Capture animation frames for GIF
        frame_idx = 2
        for i in range(1, 16):
            if i == 3:
                # Open Filters & Selectors
                advanced_btn = page.locator("button:has-text('Filters & Selectors')")
                if await advanced_btn.count() > 0:
                    await advanced_btn.click()
            elif i == 6:
                # Switch to RAG Chunks tab
                chunks_tab = page.locator("button:has-text('RAG Chunks')")
                if await chunks_tab.count() > 0:
                    await chunks_tab.click()
            elif i == 9:
                # Open Pack for LLM modal
                pack_btn = page.locator("button:has-text('Pack for LLM')")
                if await pack_btn.count() > 0:
                    await pack_btn.click()
            elif i == 12:
                # Close modal
                close_btn = page.locator("button:has(svg.lucide-x)")
                if await close_btn.count() > 0:
                    await close_btn.click()
            elif i == 14:
                # Switch to Metadata tab
                meta_tab = page.locator("button:has-text('Metadata')")
                if await meta_tab.count() > 0:
                    await meta_tab.click()

            await asyncio.sleep(0.3)
            await page.screenshot(path=str(frames_dir / f"frame_{frame_idx:02d}.png"))
            frame_idx += 1

        await context.close()

        # 2. Mobile Responsive Experience (390x844 - iPhone Viewport)
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto(f"http://127.0.0.1:{port}")
        await mobile_page.wait_for_selector("input[type='url']")

        # Trigger single extract on mobile
        m_extract_btn = mobile_page.locator("button:has-text('Single Extract')")
        if await m_extract_btn.count() > 0:
            await m_extract_btn.click()
            await asyncio.sleep(0.2)

        m_launch_btn = mobile_page.locator("button:has-text('Extract Document')")
        if await m_launch_btn.count() > 0:
            await m_launch_btn.click()

        await mobile_page.wait_for_selector("text=cl100k Tokens", timeout=10000)
        await asyncio.sleep(0.5)

        # Capture mobile responsive screenshot
        mobile_png = images_dir / "crawlcraft_mobile.png"
        await mobile_page.screenshot(path=str(mobile_png))
        print(f"Saved mobile screenshot to {mobile_png}")

        await mobile_context.close()
        await browser.close()

    server_thread.stop()

    # Generate animated GIF using ffmpeg
    demo_gif = images_dir / "crawlcraft_demo.gif"
    print("Generating animated demo GIF with FFmpeg...")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", "3",
        "-i", str(frames_dir / "frame_%02d.png"),
        "-vf", "split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
        str(demo_gif)
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated demo GIF: {demo_gif}")

    # Clean up frames
    for f in frames_dir.glob("*.png"):
        f.unlink()
    frames_dir.rmdir()


if __name__ == "__main__":
    asyncio.run(main())
