"""Unit tests for sitemap and feed discovery parser."""

import gzip
import pytest
from crawlcraft.core.sitemap import parse_sitemap_xml, parse_feed_xml


STANDARD_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2026-10-18T10:00:00Z</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/docs</loc>
    <lastmod>2026-10-17T12:00:00Z</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
    <lastmod>2026-10-18</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>
"""

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>CrawlCraft Blog</title>
    <link>https://example.com/blog</link>
    <description>Updates and releases</description>
    <item>
      <title>CrawlCraft 1.0 Released</title>
      <link>https://example.com/blog/v1-released</link>
      <pubDate>Sun, 18 Oct 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Benchmarking C-based Parsers</title>
      <link>https://example.com/blog/c-parser-benchmarks</link>
    </item>
  </channel>
</rss>
"""

ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>CrawlCraft News</title>
  <link href="https://example.com/feed.atom" rel="self"/>
  <entry>
    <title>RAG Context Packing</title>
    <link href="https://example.com/news/rag-packing"/>
    <updated>2026-10-18T14:00:00Z</updated>
  </entry>
</feed>
"""


def test_parse_standard_sitemap():
    urls, child_sitemaps = parse_sitemap_xml(STANDARD_SITEMAP)
    assert len(urls) == 2
    assert len(child_sitemaps) == 0

    assert urls[0].url == "https://example.com/"
    assert urls[0].priority == 1.0
    assert urls[0].changefreq == "daily"
    assert urls[0].lastmod == "2026-10-18T10:00:00Z"

    assert urls[1].url == "https://example.com/docs"
    assert urls[1].priority == 0.8


def test_parse_sitemap_index():
    urls, child_sitemaps = parse_sitemap_xml(SITEMAP_INDEX)
    assert len(urls) == 0
    assert len(child_sitemaps) == 2
    assert "https://example.com/sitemap-posts.xml" in child_sitemaps
    assert "https://example.com/sitemap-pages.xml" in child_sitemaps


def test_parse_gzipped_sitemap():
    compressed_bytes = gzip.compress(STANDARD_SITEMAP.encode("utf-8"))
    urls, child_sitemaps = parse_sitemap_xml(compressed_bytes)
    assert len(urls) == 2
    assert urls[0].url == "https://example.com/"


def test_parse_rss_feed():
    urls = parse_feed_xml(RSS_FEED)
    assert len(urls) == 2
    url_strings = [u.url for u in urls]
    assert "https://example.com/blog/v1-released" in url_strings
    assert "https://example.com/blog/c-parser-benchmarks" in url_strings


def test_parse_atom_feed():
    urls = parse_feed_xml(ATOM_FEED)
    assert len(urls) == 1
    assert urls[0].url == "https://example.com/news/rag-packing"
