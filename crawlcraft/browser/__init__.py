"""Browser rendering and SPA detection package."""

from crawlcraft.browser.spa_detector import detect_spa_shell
from crawlcraft.browser.headless_pool import HeadlessBrowserPool

__all__ = [
    "detect_spa_shell",
    "HeadlessBrowserPool",
]
