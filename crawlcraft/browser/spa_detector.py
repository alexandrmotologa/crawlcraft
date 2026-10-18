"""Heuristic detector for client-side rendered Single Page Application (SPA) shells."""

import re
from typing import Tuple
from selectolax.lexbor import LexborHTMLParser

SPA_ROOT_SELECTORS = [
    "#root",
    "#__next",
    "#__nuxt",
    "#app",
    "#mount",
    "app-root",
    "[data-reactroot]",
    "[ng-version]",
]

SPA_NOSCRIPT_PATTERNS = [
    re.compile(r"enable javaScript", re.IGNORECASE),
    re.compile(r"javascript is required", re.IGNORECASE),
    re.compile(r"need to enable javascript", re.IGNORECASE),
    re.compile(r"requires javascript", re.IGNORECASE),
]


def detect_spa_shell(html: str, min_text_length: int = 250) -> Tuple[bool, str]:
    """Detects whether an HTML page is an empty or unhydrated SPA shell requiring JS execution.

    Returns:
        Tuple[bool, str]: (is_spa_shell, reason)
    """
    if not html or not html.strip():
        return False, "Empty HTML content"

    parser = LexborHTMLParser(html)
    body = parser.body
    if not body:
        return False, "No body tag detected"

    # Extract raw text from body
    body_text = body.text(deep=True).strip()
    clean_text = " ".join(body_text.split())

    # Check noscript warnings first
    for noscript in parser.css("noscript"):
        noscript_content = noscript.text(deep=True)
        for pattern in SPA_NOSCRIPT_PATTERNS:
            if pattern.search(noscript_content):
                return True, f"Found noscript JavaScript requirement: '{pattern.pattern}'"

    # If body text is already rich and extensive, it is not an empty shell
    if len(clean_text) >= min_text_length:
        return False, f"Sufficient body text length ({len(clean_text)} chars)"

    # Check for known SPA container roots
    for selector in SPA_ROOT_SELECTORS:
        root_node = parser.css_first(selector)
        if root_node is not None:
            # Check if root node is empty or nearly empty
            root_text = root_node.text(deep=True).strip()
            if len(root_text) < 100:
                return True, f"Detected empty SPA root element '{selector}'"

    # Check for client-side bundle script tags when text is scarce
    scripts = parser.css("script")
    for script in scripts:
        src = script.attributes.get("src", "").lower()
        script_type = script.attributes.get("type", "").lower()
        if script_type == "module" or any(bundle_term in src for bundle_term in ("main.", "app.", "chunk.", "bundle.", "index.")):
            if len(clean_text) < 150:
                return True, f"Found client bundle '{src or script_type}' with sparse body text ({len(clean_text)} chars)"

    return False, "Standard server-rendered HTML or static document"
