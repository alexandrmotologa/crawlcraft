"""URL normalization and 64-bit SimHash content deduplication."""

import hashlib
import re
from typing import List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "msclkid",
    "mc_eid",
    "_ga",
    "ref",
    "ref_src",
    "source",
    "campaign",
    "sessionid",
    "phpsessid",
    "jsessionid",
}


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalizes a URL by resolving relative links, stripping tracking parameters,

    sorting query arguments, and standardizing hostnames.
    """
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Strip fragments
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path
    path = parsed.path
    if not path:
        path = "/"
    elif len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    # Filter tracking query parameters and sort alphabetically
    cleaned_query: List[Tuple[str, str]] = []
    if parsed.query:
        for key, val in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() not in TRACKING_PARAMS:
                cleaned_query.append((key, val))
        cleaned_query.sort(key=lambda item: item[0])

    new_query = urlencode(cleaned_query) if cleaned_query else ""

    return urlunparse((scheme, netloc, path, "", new_query, ""))


def compute_simhash(text: str) -> int:
    """Computes a 64-bit SimHash fingerprint for document text similarity."""
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return 0

    # Build 3-word shingles or single token weights
    features: List[str] = []
    if len(tokens) >= 3:
        for i in range(len(tokens) - 2):
            features.append(f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}")
    else:
        features = tokens

    v = [0] * 64
    for feature in features:
        # Generate 64-bit hash
        digest = hashlib.md5(feature.encode("utf-8")).digest()
        h = int.from_bytes(digest[:8], byteorder="big")
        for i in range(64):
            bitmask = 1 << i
            if h & bitmask:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculates the number of differing bits between two 64-bit integers."""
    x = (hash1 ^ hash2) & 0xFFFFFFFFFFFFFFFF
    return bin(x).count("1")


class ContentDeduplicator:
    """Tracks crawled URLs and flags duplicate and near-duplicate text content."""

    def __init__(self, hamming_threshold: int = 3) -> None:
        self.seen_urls: Set[str] = set()
        self.seen_hashes: List[Tuple[int, str]] = []
        self.threshold = hamming_threshold

    def is_url_seen(self, url: str) -> bool:
        normalized = normalize_url(url)
        return normalized in self.seen_urls

    def mark_url_seen(self, url: str) -> None:
        self.seen_urls.add(normalize_url(url))

    def is_content_duplicate(self, text: str) -> Tuple[bool, Optional[str]]:
        """Checks if text content has already been seen using SimHash.

        Returns (is_duplicate, original_matching_url).
        """
        if not text.strip():
            return False, None

        doc_hash = compute_simhash(text)
        if doc_hash == 0:
            return False, None

        for existing_hash, original_url in self.seen_hashes:
            if hamming_distance(doc_hash, existing_hash) <= self.threshold:
                return True, original_url

        return False, None

    def record_content(self, url: str, text: str) -> None:
        """Records the content fingerprint for future duplicate comparisons."""
        doc_hash = compute_simhash(text)
        if doc_hash != 0:
            self.seen_hashes.append((doc_hash, url))
