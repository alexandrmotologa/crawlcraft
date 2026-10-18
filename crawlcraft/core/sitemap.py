"""Asynchronous sitemap and RSS/Atom feed parser and discovery engine."""

import gzip
import re
from typing import List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import httpx
from selectolax.lexbor import LexborHTMLParser

from crawlcraft.core.deduplicator import normalize_url


class SitemapUrl:
    """Represents a discovered URL from an XML sitemap or feed."""

    def __init__(
        self,
        url: str,
        lastmod: Optional[str] = None,
        changefreq: Optional[str] = None,
        priority: Optional[float] = None,
    ) -> None:
        self.url = url
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority

    def to_dict(self):
        return {
            "url": self.url,
            "lastmod": self.lastmod,
            "changefreq": self.changefreq,
            "priority": self.priority,
        }


def _strip_ns(tag: str) -> str:
    """Strips XML namespace from tag name."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_sitemap_xml(xml_content: str | bytes) -> Tuple[List[SitemapUrl], List[str]]:
    """Parses a sitemap XML string or bytes.

    Returns:
        Tuple[List[SitemapUrl], List[str]]: (discovered_urls, child_sitemap_index_urls)
    """
    urls: List[SitemapUrl] = []
    child_sitemaps: List[str] = []

    if isinstance(xml_content, bytes):
        # Attempt transparent gzip decompression if gzipped sitemap (.xml.gz)
        if xml_content.startswith(b"\x1f\x8b"):
            try:
                xml_content = gzip.decompress(xml_content).decode("utf-8", errors="replace")
            except Exception:
                xml_content = xml_content.decode("utf-8", errors="replace")
        else:
            xml_content = xml_content.decode("utf-8", errors="replace")

    xml_text = xml_content.strip()
    if not xml_text:
        return urls, child_sitemaps

    try:
        root = ET.fromstring(xml_text)
    except Exception:
        # Fallback to regex extraction if XML is slightly malformed
        locs = re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", xml_text, re.IGNORECASE)
        for loc in locs:
            if loc.endswith(".xml") or loc.endswith(".xml.gz") or "sitemap" in loc.lower():
                child_sitemaps.append(loc)
            else:
                urls.append(SitemapUrl(url=normalize_url(loc)))
        return urls, child_sitemaps

    root_tag = _strip_ns(root.tag).lower()

    # Case 1: Sitemap Index containing child sitemaps (<sitemapindex>)
    if root_tag == "sitemapindex":
        for sitemap_node in root:
            for child in sitemap_node:
                if _strip_ns(child.tag).lower() == "loc" and child.text:
                    child_sitemaps.append(child.text.strip())
        return urls, child_sitemaps

    # Case 2: Standard URL set (<urlset>)
    if root_tag == "urlset":
        for url_node in root:
            loc = None
            lastmod = None
            changefreq = None
            priority = None

            for child in url_node:
                tag = _strip_ns(child.tag).lower()
                text = child.text.strip() if child.text else None
                if tag == "loc" and text:
                    loc = text
                elif tag == "lastmod" and text:
                    lastmod = text
                elif tag == "changefreq" and text:
                    changefreq = text
                elif tag == "priority" and text:
                    try:
                        priority = float(text)
                    except ValueError:
                        pass

            if loc:
                urls.append(
                    SitemapUrl(
                        url=normalize_url(loc),
                        lastmod=lastmod,
                        changefreq=changefreq,
                        priority=priority,
                    )
                )
        return urls, child_sitemaps

    # Case 3: RSS / Atom Feed fallback
    if root_tag in ("rss", "feed"):
        for elem in root.iter():
            tag = _strip_ns(elem.tag).lower()
            if tag in ("item", "entry"):
                link_text = None
                date_text = None
                for child in elem:
                    c_tag = _strip_ns(child.tag).lower()
                    if c_tag == "link":
                        link_text = child.attrib.get("href") or (child.text.strip() if child.text else None)
                    elif c_tag in ("pubdate", "updated", "published"):
                        date_text = child.text.strip() if child.text else None

                if link_text:
                    urls.append(SitemapUrl(url=normalize_url(link_text), lastmod=date_text))

    return urls, child_sitemaps


def parse_feed_xml(xml_content: str | bytes) -> List[SitemapUrl]:
    """Parses RSS/Atom feed content and returns extracted URLs."""
    urls, _ = parse_sitemap_xml(xml_content)
    return urls


async def fetch_and_parse_sitemaps(
    start_url_or_domain: str,
    max_urls: int = 1000,
    client: Optional[httpx.AsyncClient] = None,
) -> List[SitemapUrl]:
    """Discovers and parses sitemaps recursively up to max_urls."""
    parsed = urlparse(start_url_or_domain)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or start_url_or_domain.split("/")[0]
    base_url = f"{scheme}://{netloc}"

    candidate_sitemaps: List[str] = []
    if parsed.path.endswith((".xml", ".xml.gz")):
        candidate_sitemaps.append(start_url_or_domain)
    else:
        candidate_sitemaps.extend([
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemap-index.xml",
            f"{base_url}/sitemap/sitemap.xml",
        ])

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        close_client = True

    discovered: List[SitemapUrl] = []
    visited_sitemaps: Set[str] = set()
    queue = list(candidate_sitemaps)

    try:
        while queue and len(discovered) < max_urls:
            sitemap_url = queue.pop(0)
            if sitemap_url in visited_sitemaps:
                continue
            visited_sitemaps.add(sitemap_url)

            try:
                resp = await client.get(sitemap_url)
                if resp.status_code != 200:
                    continue

                urls, child_sitemaps = parse_sitemap_xml(resp.content)
                for u in urls:
                    if len(discovered) >= max_urls:
                        break
                    discovered.append(u)

                for child in child_sitemaps:
                    full_child = urljoin(sitemap_url, child)
                    if full_child not in visited_sitemaps:
                        queue.append(full_child)
            except Exception:
                continue
    finally:
        if close_client:
            await client.aclose()

    return discovered


discover_and_parse_sitemaps = fetch_and_parse_sitemaps
