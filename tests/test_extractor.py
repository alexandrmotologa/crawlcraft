"""Tests for Selectolax HTML cleaner and content isolator."""

import pytest
from selectolax.lexbor import LexborHTMLParser
from crawlcraft.extractor.html_cleaner import clean_html_tree, extract_main_content_node


def test_strip_scripts_styles_and_ads():
    html = """
    <html>
      <head>
        <title>Article</title>
        <style>body { background: red; }</style>
        <script>console.log("analytics");</script>
      </head>
      <body>
        <div class="cookie-consent-banner">Accept cookies</div>
        <div class="advertisement-box">Buy shoes now</div>
        <article>
          <h1>Actual Title</h1>
          <p>Real article content that must be retained.</p>
        </article>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """
    cleaned = clean_html_tree(html)
    text = cleaned.body.text(deep=True) if cleaned.body else ""

    assert "Accept cookies" not in text
    assert "Buy shoes" not in text
    assert "analytics" not in text
    assert "Copyright 2026" not in text
    assert "Real article content" in text


def test_extract_main_content_node():
    html = """
    <html>
      <body>
        <nav><a href="/home">Home</a></nav>
        <article>
          <h2>Main Post</h2>
          <p>This is the primary post containing detailed research and factual engineering data that represents the article body.</p>
        </article>
      </body>
    </html>
    """
    parser = LexborHTMLParser(html)
    main_node = extract_main_content_node(parser)
    assert main_node is not None
    assert main_node.tag == "article"
