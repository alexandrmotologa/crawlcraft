"""Tests for metadata extraction and tiktoken token calculations."""

import pytest
from crawlcraft.extractor.metadata import TokenEstimator, extract_metadata


def test_token_estimator():
    estimator = TokenEstimator("cl100k_base")
    text = "CrawlCraft is an asynchronous high-throughput web crawler."
    stats = estimator.compute_stats(text)

    assert stats["token_count"] > 0
    assert stats["word_count"] == 7
    assert stats["encoding"] == "cl100k_base"


def test_metadata_opengraph_and_json_ld():
    html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <title>Machine Learning Guide</title>
        <meta name="description" content="A comprehensive tutorial on neural networks.">
        <meta name="author" content="Jane Doe">
        <meta property="og:title" content="OG Machine Learning">
        <meta property="og:description" content="OG description text.">
        <meta property="og:site_name" content="TechBlog">
        <link rel="canonical" href="https://techblog.com/ml-guide">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": "Machine Learning Guide",
          "author": {
            "@type": "Person",
            "name": "Jane Doe"
          },
          "datePublished": "2026-05-01T08:00:00Z"
        }
        </script>
      </head>
      <body>
        <article>
          <h1>Machine Learning Guide</h1>
          <p>Article body discussing neural networks and algorithms.</p>
        </article>
      </body>
    </html>
    """
    meta = extract_metadata(html, url="https://techblog.com/ml-guide")

    assert meta.title == "Machine Learning Guide"
    assert meta.author == "Jane Doe"
    assert meta.description == "A comprehensive tutorial on neural networks."
    assert meta.canonical_url == "https://techblog.com/ml-guide"
    assert meta.site_name == "TechBlog"
    assert meta.published_time == "2026-05-01T08:00:00Z"
    assert len(meta.json_ld) == 1
    assert meta.json_ld[0]["@type"] == "Article"
    assert meta.token_stats["token_count"] > 0
