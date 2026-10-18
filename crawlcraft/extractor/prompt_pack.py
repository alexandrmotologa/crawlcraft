"""Formats crawled documents into standardized context packets for LLM prompts."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from crawlcraft.core.crawler import CrawledPage


def _get_page_attr(page: Any, attr: str, default: Any = None) -> Any:
    if isinstance(page, dict):
        return page.get(attr, default)
    return getattr(page, attr, default)


def pack_pages_for_llm(
    pages: List[Any],
    format_type: str = "xml",
    system_directive: Optional[str] = None,
) -> str:
    """Consolidates crawled pages into a structured prompt context block."""
    total_tokens = 0
    clean_pages = []

    for p in pages:
        meta = _get_page_attr(p, "metadata", {})
        if hasattr(meta, "to_dict"):
            meta_dict = meta.to_dict()
            title = meta.title
            desc = meta.description
            stats = meta.token_stats
        elif isinstance(meta, dict):
            meta_dict = meta
            title = meta.get("title")
            desc = meta.get("description")
            stats = meta.get("token_stats", {})
        else:
            meta_dict = {}
            title = None
            desc = None
            stats = {}

        t_count = stats.get("token_count", 0) if isinstance(stats, dict) else 0
        total_tokens += t_count
        clean_pages.append({
            "url": _get_page_attr(p, "url", ""),
            "title": title or _get_page_attr(p, "url", "Untitled"),
            "description": desc or "",
            "tokens": t_count,
            "markdown": _get_page_attr(p, "markdown", ""),
        })

    total_docs = len(clean_pages)

    if format_type.lower() == "xml":
        lines = []
        if system_directive:
            lines.append(f"<system_context>\n{system_directive.strip()}\n</system_context>\n")

        lines.append(f'<knowledge_base total_documents="{total_docs}" total_tokens="{total_tokens}">')

        # Index manifest
        lines.append("  <manifest>")
        for idx, p in enumerate(clean_pages, 1):
            title = p["title"].replace('"', '&quot;')
            lines.append(f'    <entry id="{idx}" url="{p["url"]}" title="{title}" tokens="{p["tokens"]}" />')
        lines.append("  </manifest>\n")

        # Documents
        for idx, p in enumerate(clean_pages, 1):
            title = p["title"]
            lines.append(f'  <document id="{idx}" url="{p["url"]}" tokens="{p["tokens"]}">')
            lines.append(f"    <title>{title}</title>")
            if p["description"]:
                lines.append(f"    <description>{p['description']}</description>")
            lines.append("    <content><![CDATA[")
            lines.append(p["markdown"].strip())
            lines.append("    ]]></content>")
            lines.append("  </document>\n")

        lines.append("</knowledge_base>")
        return "\n".join(lines)

    # Markdown format
    lines = []
    if system_directive:
        lines.append(f"> **System Instructions:** {system_directive}\n\n---\n")

    lines.append(f"# Knowledge Base ({total_docs} Documents | {total_tokens:,} Tokens)\n")
    lines.append("| ID | Document Title | Source URL | Tokens |")
    lines.append("|:---|:---|:---|:---:|")
    for idx, p in enumerate(clean_pages, 1):
        lines.append(f"| {idx} | {p['title']} | {p['url']} | {p['tokens']:,} |")

    lines.append("\n---\n")

    for idx, p in enumerate(clean_pages, 1):
        lines.append(f"## Document {idx}: {p['title']}")
        lines.append(f"**URL:** {p['url']} | **Tokens:** {p['tokens']:,}\n")
        if p["description"]:
            lines.append(f"*{p['description']}*\n")
        lines.append(p["markdown"].strip())
        lines.append("\n\n---\n")

    return "\n".join(lines)
