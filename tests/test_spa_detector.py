"""Tests for SPA detection heuristics."""

import pytest
from crawlcraft.browser.spa_detector import detect_spa_shell


def test_detect_empty_root_div():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>React App</title></head>
      <body>
        <div id="root"></div>
        <script src="/static/js/bundle.js"></script>
      </body>
    </html>
    """
    is_spa, reason = detect_spa_shell(html)
    assert is_spa is True
    assert "root" in reason.lower()


def test_detect_noscript_warning():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>App</title></head>
      <body>
        <noscript>You need to enable JavaScript to run this app.</noscript>
        <div id="app"></div>
      </body>
    </html>
    """
    is_spa, reason = detect_spa_shell(html)
    assert is_spa is True
    assert "noscript" in reason.lower()


def test_detect_static_content_is_not_spa():
    paragraphs = "<p>This is a high quality article discussing web scraping algorithms and efficiency in modern data pipelines.</p>" * 10
    html = f"""
    <!DOCTYPE html>
    <html>
      <head><title>Blog Post</title></head>
      <body>
        <main>
          <h1>Understanding Crawlers</h1>
          {paragraphs}
        </main>
      </body>
    </html>
    """
    is_spa, reason = detect_spa_shell(html)
    assert is_spa is False
    assert "sufficient" in reason.lower()
