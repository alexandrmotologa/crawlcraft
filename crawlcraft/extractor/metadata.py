"""Metadata extraction (JSON-LD, OpenGraph, Dublin Core) and RAG token estimation."""

import json
import re
from typing import Any, Dict, List, Optional
from selectolax.lexbor import LexborHTMLParser
import tiktoken


class TokenEstimator:
    """Computes exact token counts with tiktoken and text density metrics."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding_name = encoding_name
        self._encoder = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoder.encode(text, disallowed_special=()))

    def compute_stats(self, text: str) -> Dict[str, Any]:
        """Calculates token count, word count, character count, and estimated reading time."""
        tokens = self.count_tokens(text)
        words = len(text.split())
        chars = len(text)
        reading_time_min = round(words / 200.0, 2) if words > 0 else 0.0

        return {
            "token_count": tokens,
            "word_count": words,
            "character_count": chars,
            "reading_time_minutes": reading_time_min,
            "encoding": self.encoding_name,
        }


# Global estimator singleton
_DEFAULT_ESTIMATOR = TokenEstimator()


class PageMetadata:
    """Structured container for document metadata extracted from web pages."""

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        canonical_url: Optional[str] = None,
        author: Optional[str] = None,
        published_time: Optional[str] = None,
        modified_time: Optional[str] = None,
        language: Optional[str] = None,
        site_name: Optional[str] = None,
        image_url: Optional[str] = None,
        open_graph: Optional[Dict[str, str]] = None,
        json_ld: Optional[List[Dict[str, Any]]] = None,
        token_stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.title = title
        self.description = description
        self.canonical_url = canonical_url
        self.author = author
        self.published_time = published_time
        self.modified_time = modified_time
        self.language = language
        self.site_name = site_name
        self.image_url = image_url
        self.open_graph = open_graph or {}
        self.json_ld = json_ld or []
        self.token_stats = token_stats or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "canonical_url": self.canonical_url,
            "author": self.author,
            "published_time": self.published_time,
            "modified_time": self.modified_time,
            "language": self.language,
            "site_name": self.site_name,
            "image_url": self.image_url,
            "open_graph": self.open_graph,
            "json_ld": self.json_ld,
            "token_stats": self.token_stats,
        }


def extract_metadata(html: str, url: str = "", text_content: str = "") -> PageMetadata:
    """Extracts title, meta tags, OpenGraph, JSON-LD schemas, and token metrics from HTML."""
    parser = LexborHTMLParser(html)

    # 1. Title extraction
    title = None
    title_node = parser.css_first("title")
    if title_node:
        title = title_node.text(deep=True).strip()

    # 2. OpenGraph and standard meta tags
    open_graph: Dict[str, str] = {}
    description = None
    author = None
    published_time = None
    modified_time = None
    site_name = None
    image_url = None

    for meta in parser.css("meta"):
        prop = meta.attributes.get("property", "").lower()
        name = meta.attributes.get("name", "").lower()
        content = meta.attributes.get("content", "").strip()

        if not content:
            continue

        if prop.startswith("og:"):
            key = prop[3:]
            open_graph[key] = content
            if key == "title" and not title:
                title = content
            elif key == "description" and not description:
                description = content
            elif key == "site_name":
                site_name = content
            elif key == "image" and not image_url:
                image_url = content

        if name == "description" and not description:
            description = content
        elif name == "author" and not author:
            author = content
        elif name in ("pubdate", "publishdate", "date") and not published_time:
            published_time = content
        elif prop in ("article:published_time", "og:published_time") and not published_time:
            published_time = content
        elif prop in ("article:modified_time", "og:updated_time") and not modified_time:
            modified_time = content

    # 3. Canonical URL
    canonical_url = None
    canonical_node = parser.css_first("link[rel='canonical']")
    if canonical_node:
        canonical_url = canonical_node.attributes.get("href", "").strip()
    if not canonical_url and "url" in open_graph:
        canonical_url = open_graph["url"]

    # 4. Language
    language = None
    html_node = parser.css_first("html")
    if html_node:
        language = html_node.attributes.get("lang")

    # 5. Schema.org JSON-LD extraction
    json_ld_schemas: List[Dict[str, Any]] = []
    for script in parser.css('script[type="application/ld+json"]'):
        raw_json = script.text(deep=True).strip()
        if not raw_json:
            continue
        try:
            data = json.loads(raw_json)
            if isinstance(data, list):
                json_ld_schemas.extend(data)
            elif isinstance(data, dict):
                if "@graph" in data and isinstance(data["@graph"], list):
                    json_ld_schemas.extend(data["@graph"])
                else:
                    json_ld_schemas.append(data)
        except Exception:
            # Skip invalid JSON scripts without crashing
            continue

    # Attempt to extract author/dates from JSON-LD if missing
    for schema in json_ld_schemas:
        if not author and "author" in schema:
            author_val = schema["author"]
            if isinstance(author_val, dict) and "name" in author_val:
                author = author_val["name"]
            elif isinstance(author_val, str):
                author = author_val
            elif isinstance(author_val, list) and author_val and isinstance(author_val[0], dict):
                author = author_val[0].get("name")

        if not published_time and "datePublished" in schema:
            published_time = str(schema["datePublished"])
        if not modified_time and "dateModified" in schema:
            modified_time = str(schema["dateModified"])

    # 6. Token statistics
    eval_text = text_content if text_content else (parser.body.text(deep=True) if parser.body else "")
    token_stats = _DEFAULT_ESTIMATOR.compute_stats(eval_text)

    return PageMetadata(
        title=title,
        description=description,
        canonical_url=canonical_url or url,
        author=author,
        published_time=published_time,
        modified_time=modified_time,
        language=language,
        site_name=site_name,
        image_url=image_url,
        open_graph=open_graph,
        json_ld=json_ld_schemas,
        token_stats=token_stats,
    )
