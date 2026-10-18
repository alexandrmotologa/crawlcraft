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


def test_custom_exclude_selectors():
    html = """
    <html>
      <body>
        <div class="sidebar">Sidebar info</div>
        <div class="promo-box">Sign up for special discount!</div>
        <main>
          <h1>Doc Title</h1>
          <p>Main content of documentation.</p>
          <div class="rating-widget">Rate this page: 5 stars</div>
        </main>
      </body>
    </html>
    """
    cleaned = clean_html_tree(html, exclude_selectors=[".promo-box", ".rating-widget"])
    text = cleaned.body.text(deep=True) if cleaned.body else ""

    assert "Sign up for special discount" not in text
    assert "Rate this page" not in text
    assert "Main content of documentation" in text


def test_custom_include_selectors():
    html = """
    <html>
      <body>
        <div id="general-wrapper">Some generic wrapper text</div>
        <div class="custom-target-container">
          <h2>Isolated Target</h2>
          <p>This is the only section we care to extract.</p>
        </div>
      </body>
    </html>
    """
    parser = LexborHTMLParser(html)
    node = extract_main_content_node(parser, include_selectors=[".custom-target-container"])
    assert node is not None
    assert "Isolated Target" in node.text(deep=True)
    assert "generic wrapper" not in node.text(deep=True)
