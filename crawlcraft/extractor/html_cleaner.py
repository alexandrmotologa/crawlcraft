"""High-performance Selectolax HTML cleaner and boilerplate remover."""

import re
from typing import List, Optional, Set
from selectolax.lexbor import LexborHTMLParser, LexborNode as Node

# Tags that contain no relevant text content for RAG or Markdown
DISCARD_TAGS: Set[str] = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "iframe",
    "frame",
    "frameset",
    "object",
    "embed",
    "applet",
    "template",
    "audio",
    "video",
    "source",
    "track",
}

# Structural boilerplate elements to prune
STRUCTURAL_BOILERPLATE_TAGS: Set[str] = {
    "nav",
    "footer",
    "aside",
}

# CSS selector patterns for ads, cookie notices, and popups
NOISE_SELECTORS: List[str] = [
    "[class*='cookie' i]",
    "[id*='cookie' i]",
    "[class*='consent' i]",
    "[id*='consent' i]",
    "[class*='privacy-banner' i]",
    "[class*='newsletter' i]",
    "[id*='newsletter' i]",
    "[class*='subscribe' i]",
    "[class*='social-share' i]",
    "[class*='share-buttons' i]",
    "[class*='advertisement' i]",
    "[id*='advertisement' i]",
    "[class*='ad-container' i]",
    "[class*='taboola' i]",
    "[class*='outbrain' i]",
    "[role='dialog']",
    "[aria-modal='true']",
]

# Primary content container candidates
CONTENT_SELECTORS: List[str] = [
    "article",
    "main",
    "[role='main']",
    "#main-content",
    "#content",
    ".post-content",
    ".entry-content",
    ".article-body",
    ".main-content",
]


def clean_html_tree(
    html_or_parser: str | LexborHTMLParser,
    exclude_selectors: Optional[List[str]] = None,
) -> LexborHTMLParser:
    """Parses and strips scripts, styles, boilerplate, and ads from an HTML document."""
    parser = LexborHTMLParser(html_or_parser) if isinstance(html_or_parser, str) else html_or_parser

    # 1. Decompose unusable technical tags
    for tag_name in DISCARD_TAGS:
        for node in parser.css(tag_name):
            node.decompose()

    # 2. Decompose structural boilerplate tags
    for tag_name in STRUCTURAL_BOILERPLATE_TAGS:
        for node in parser.css(tag_name):
            node.decompose()

    # 3. Decompose noise and ad elements
    for selector in NOISE_SELECTORS:
        try:
            for node in parser.css(selector):
                # Don't prune if it happens to be the primary main container
                tag = node.tag.lower()
                if tag in ("main", "article", "body", "html"):
                    continue
                node.decompose()
        except Exception:
            continue

    # 4. Decompose custom user-specified exclude selectors
    if exclude_selectors:
        for selector in exclude_selectors:
            try:
                for node in parser.css(selector):
                    tag = node.tag.lower()
                    if tag not in ("body", "html"):
                        node.decompose()
            except Exception:
                continue

    return parser


def extract_main_content_node(
    parser: LexborHTMLParser,
    include_selectors: Optional[List[str]] = None,
) -> Node:
    """Finds the most text-dense semantic container (article, main, or highest text-density node)."""
    # 0. Check custom user include selectors first
    if include_selectors:
        for selector in include_selectors:
            try:
                candidates = parser.css(selector)
                if candidates:
                    return max(candidates, key=lambda n: len(n.text(deep=True).strip()))
            except Exception:
                continue

    # 1. Check well-known semantic selectors
    for selector in CONTENT_SELECTORS:
        try:
            candidates = parser.css(selector)
            if candidates:
                # Pick candidate with greatest text length
                best_candidate = max(candidates, key=lambda n: len(n.text(deep=True).strip()))
                text_len = len(best_candidate.text(deep=True).strip())
                min_len = 30 if selector in ("article", "main", "[role='main']") else 80
                if text_len >= min_len:
                    return best_candidate
        except Exception:
            continue

    # Fallback to body or html root
    body = parser.css_first("body")
    if body:
        return body

    return parser.root if parser.root else parser.body
