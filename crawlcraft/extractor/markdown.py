"""AST and node-based GitHub Flavored Markdown (GFM) synthesizer."""

import re
from typing import Generator, List, Optional
from urllib.parse import urljoin
from selectolax.lexbor import LexborHTMLParser, LexborNode as Node

from crawlcraft.extractor.html_cleaner import clean_html_tree, extract_main_content_node
from crawlcraft.extractor.tables import html_table_to_gfm


class MarkdownConverter:
    """Converts a Selectolax HTML tree into clean GitHub Flavored Markdown."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url

    def _resolve_url(self, link: str) -> str:
        if not link:
            return ""
        if self.base_url and not link.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            return urljoin(self.base_url, link)
        return link

    @staticmethod
    def _iter_children(node: Node) -> Generator[Node, None, None]:
        """Iterates through all child nodes (both elements and text nodes) in Lexbor."""
        curr = node.child
        while curr is not None:
            yield curr
            curr = curr.next

    def _extract_code_language(self, node: Node) -> str:
        """Extracts programming language identifier from class names."""
        classes = node.attributes.get("class", "")
        if isinstance(classes, str):
            for cls in classes.split():
                if cls.startswith("language-"):
                    return cls.replace("language-", "").strip()
                if cls.startswith("lang-"):
                    return cls.replace("lang-", "").strip()
        return ""

    def _handle_code_block(self, pre_node: Node) -> str:
        """Processes pre and code elements preserving exact syntax and language."""
        code_node = pre_node.css_first("code")
        lang = ""
        if code_node:
            lang = self._extract_code_language(code_node)
            raw_code = code_node.text(deep=True)
        else:
            lang = self._extract_code_language(pre_node)
            raw_code = pre_node.text(deep=True)

        return f"\n```{lang}\n{raw_code.strip()}\n```\n"

    def _convert_node(self, node: Node, list_depth: int = 0, is_ordered: bool = False, item_index: int = 1) -> str:
        if node.tag == "-text":
            return node.text()

        tag = node.tag.lower()

        # Handle math formulas
        if "katex" in node.attributes.get("class", "").lower() or tag == "math":
            math_text = node.text(deep=True).strip()
            if not math_text.startswith("$"):
                return f" ${math_text}$ "
            return f" {math_text} "

        # Headings
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            heading_text = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            if heading_text:
                return f"\n\n{'#' * level} {heading_text}\n\n"
            return ""

        # Paragraphs and divs
        if tag == "p":
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            return f"\n\n{inner}\n\n" if inner else ""

        if tag == "br":
            return "\n"

        if tag == "hr":
            return "\n\n---\n\n"

        # Code block
        if tag == "pre":
            return self._handle_code_block(node)

        # Inline code
        if tag == "code":
            code_text = node.text(deep=True)
            return f"`{code_text}`"

        # Text formatting
        if tag in ("strong", "b"):
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            return f"**{inner}**" if inner else ""

        if tag in ("em", "i"):
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            return f"*{inner}*" if inner else ""

        if tag in ("del", "s", "strike"):
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            return f"~~{inner}~~" if inner else ""

        # Blockquote
        if tag == "blockquote":
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            if not inner:
                return ""
            quoted_lines = [f"> {line}" for line in inner.splitlines()]
            return "\n\n" + "\n".join(quoted_lines) + "\n\n"

        # Tables
        if tag == "table":
            return html_table_to_gfm(node)

        # Links
        if tag == "a":
            href = node.attributes.get("href", "").strip()
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            if not href or href.startswith("javascript:"):
                return inner
            resolved_href = self._resolve_url(href)
            if not inner:
                return f"<{resolved_href}>"
            return f"[{inner}]({resolved_href})"

        # Images
        if tag == "img":
            src = node.attributes.get("src", "").strip()
            alt = node.attributes.get("alt", "").strip()
            if not src:
                return ""
            resolved_src = self._resolve_url(src)
            return f"![{alt}]({resolved_src})"

        # Lists
        if tag == "ul":
            items: List[str] = []
            for child in self._iter_children(node):
                if child.tag.lower() == "li":
                    items.append(self._convert_node(child, list_depth + 1, is_ordered=False))
            return "\n" + "".join(items) + "\n"

        if tag == "ol":
            items = []
            idx = 1
            for child in self._iter_children(node):
                if child.tag.lower() == "li":
                    items.append(self._convert_node(child, list_depth + 1, is_ordered=True, item_index=idx))
                    idx += 1
            return "\n" + "".join(items) + "\n"

        if tag == "li":
            indent = "  " * max(0, list_depth - 1)
            bullet = f"{item_index}. " if is_ordered else "- "
            inner = "".join(self._convert_node(child, list_depth) for child in self._iter_children(node)).strip()
            return f"{indent}{bullet}{inner}\n"

        # Default recursive traversal for other tags (div, span, section, main, article, etc.)
        results: List[str] = []
        for child in self._iter_children(node):
            results.append(self._convert_node(child, list_depth))

        return "".join(results)

    def convert(self, html: str, extract_main_only: bool = True) -> str:
        """Parses raw HTML, cleans noise, and outputs synthesized GFM Markdown."""
        parser = clean_html_tree(html)
        target_node = extract_main_content_node(parser) if extract_main_only else parser.body or parser.root

        if not target_node:
            return ""

        raw_md = self._convert_node(target_node)

        # Post-process whitespace: collapse excessive empty lines
        cleaned_md = re.sub(r"\n{3,}", "\n\n", raw_md)
        return cleaned_md.strip()


def html_to_markdown(html: str, base_url: Optional[str] = None, extract_main_only: bool = True) -> str:
    """Convenience function to convert raw HTML string into clean GFM Markdown."""
    converter = MarkdownConverter(base_url=base_url)
    return converter.convert(html, extract_main_only=extract_main_only)
