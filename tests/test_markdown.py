"""Tests for GFM Markdown synthesizer and tables."""

import pytest
from crawlcraft.extractor.markdown import html_to_markdown


def test_markdown_headings_and_paragraphs():
    html = """
    <html>
      <body>
        <main>
          <h1>Heading 1</h1>
          <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
          <h2>Subheading</h2>
          <p>Another paragraph.</p>
        </main>
      </body>
    </html>
    """
    md = html_to_markdown(html)
    assert "# Heading 1" in md
    assert "## Subheading" in md
    assert "**bold**" in md
    assert "*italic*" in md


def test_markdown_code_blocks():
    html = """
    <html>
      <body>
        <main>
          <pre><code class="language-python">def add(a, b):
    return a + b</code></pre>
        </main>
      </body>
    </html>
    """
    md = html_to_markdown(html)
    assert "```python" in md
    assert "def add(a, b):" in md
    assert "return a + b" in md
    assert "```" in md


def test_markdown_tables():
    html = """
    <html>
      <body>
        <main>
          <table>
            <thead>
              <tr><th>Header 1</th><th>Header 2</th></tr>
            </thead>
            <tbody>
              <tr><td>Row 1 Cell 1</td><td>Row 1 Cell 2</td></tr>
              <tr><td>Row 2 Cell 1</td><td>Row 2 Cell 2</td></tr>
            </tbody>
          </table>
        </main>
      </body>
    </html>
    """
    md = html_to_markdown(html)
    assert "| Header 1 | Header 2 |" in md
    assert "| --- | --- |" in md
    assert "| Row 1 Cell 1 | Row 1 Cell 2 |" in md


def test_markdown_links_resolution():
    html = """
    <html>
      <body>
        <main>
          <p>Check the <a href="/docs/guide">Documentation</a> or <a href="https://google.com">Search</a>.</p>
        </main>
      </body>
    </html>
    """
    md = html_to_markdown(html, base_url="https://crawlcraft.dev")
    assert "[Documentation](https://crawlcraft.dev/docs/guide)" in md
    assert "[Search](https://google.com)" in md


def test_markdown_math_formula():
    html = """
    <html>
      <body>
        <main>
          <p>The equation is <span class="katex">E = mc^2</span> according to physics.</p>
        </main>
      </body>
    </html>
    """
    md = html_to_markdown(html)
    assert "$E = mc^2$" in md
