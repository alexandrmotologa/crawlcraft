"""Tests for core crawler logic: rate limiter, robots.txt, normalization, and deduplication."""

import asyncio
import pytest
from crawlcraft.core.deduplicator import ContentDeduplicator, compute_simhash, hamming_distance, normalize_url
from crawlcraft.core.rate_limiter import DomainRateLimiter, TokenBucket
from crawlcraft.core.robots import RobotsPolicy


def test_url_normalization():
    raw_url = "HTTPS://Example.COM:443/docs/intro/?utm_source=twitter&b=2&a=1&fbclid=xyz#section"
    normalized = normalize_url(raw_url)
    assert normalized == "https://example.com/docs/intro?a=1&b=2"


def test_url_normalization_with_base():
    rel = "../api/v1"
    base = "https://example.com/docs/intro/"
    normalized = normalize_url(rel, base_url=base)
    assert normalized == "https://example.com/docs/api/v1"


def test_simhash_deduplication():
    text1 = "CrawlCraft provides fast asynchronous web scraping for machine learning and retrieval pipelines."
    text2 = "CrawlCraft provides fast asynchronous web scraping for machine learning and retrieval pipelines!"
    text3 = "Completely distinct content about culinary recipes and baking bread."

    h1 = compute_simhash(text1)
    h2 = compute_simhash(text2)
    h3 = compute_simhash(text3)

    assert hamming_distance(h1, h2) <= 3
    assert hamming_distance(h1, h3) > 10

    dedup = ContentDeduplicator(hamming_threshold=3)
    dedup.record_content("https://example.com/p1", text1)

    is_dup, orig_url = dedup.is_content_duplicate(text2)
    assert is_dup is True
    assert orig_url == "https://example.com/p1"

    is_dup3, _ = dedup.is_content_duplicate(text3)
    assert is_dup3 is False


def test_robots_txt_matching():
    robots_content = """
    User-agent: *
    Disallow: /admin/
    Disallow: /private/*
    Allow: /private/public-doc
    Crawl-delay: 2
    """
    policy = RobotsPolicy(robots_content)

    assert policy.is_allowed("/blog/post-1") is True
    assert policy.is_allowed("/admin/settings") is False
    assert policy.is_allowed("/private/secret") is False
    assert policy.is_allowed("/private/public-doc") is True
    assert policy.crawl_delay == 2.0


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    bucket = TokenBucket(rate=100.0, capacity=2.0)
    # Immediate acquires from burst capacity
    await bucket.acquire(1.0)
    await bucket.acquire(1.0)
    # Bucket depleted, acquiring should be handled smoothly
    t0 = asyncio.get_event_loop().time()
    await bucket.acquire(1.0)
    t1 = asyncio.get_event_loop().time()
    assert (t1 - t0) >= 0.005
