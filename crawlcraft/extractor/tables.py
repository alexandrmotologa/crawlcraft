"""HTML table to GitHub Flavored Markdown (GFM) converter."""

from typing import List, Optional
from selectolax.lexbor import LexborNode as Node


def _clean_cell_text(text: str) -> str:
    """Removes line breaks, tabs, and unescaped pipes from table cell text."""
    # Replace linebreaks with single spaces
    cleaned = " ".join(text.split())
    # Escape pipe characters
    return cleaned.replace("|", r"\|")


def html_table_to_gfm(table_node: Node) -> str:
    """Converts a Selectolax table Node into a formatted GitHub Flavored Markdown table."""
    rows: List[List[str]] = []
    alignments: List[str] = []

    # Check for thead or tr
    thead = table_node.css_first("thead")
    header_cells: List[str] = []

    if thead:
        header_tr = thead.css_first("tr")
        if header_tr:
            for cell in header_tr.css("th, td"):
                header_cells.append(_clean_cell_text(cell.text(deep=True)))
                align = cell.attributes.get("align", "").lower()
                if "center" in align:
                    alignments.append(":---:")
                elif "right" in align:
                    alignments.append("---:")
                else:
                    alignments.append("---")

    # If no thead, inspect the first tr
    all_trs = table_node.css("tr")
    start_row_idx = 0

    if not header_cells and all_trs:
        first_tr = all_trs[0]
        cells = first_tr.css("th, td")
        if cells:
            for cell in cells:
                header_cells.append(_clean_cell_text(cell.text(deep=True)))
                align = cell.attributes.get("align", "").lower()
                if "center" in align:
                    alignments.append(":---:")
                elif "right" in align:
                    alignments.append("---:")
                else:
                    alignments.append("---")
            start_row_idx = 1

    # Process remaining body rows
    body_trs = all_trs[start_row_idx:] if not thead else (table_node.css("tbody tr") or table_node.css("tr")[1:])
    for tr in body_trs:
        # Avoid duplicate inclusion of header
        if thead and tr.parent and tr.parent.tag == "thead":
            continue
        row_cells = [_clean_cell_text(cell.text(deep=True)) for cell in tr.css("th, td")]
        if row_cells:
            rows.append(row_cells)

    if not header_cells and not rows:
        return ""

    # Determine maximum number of columns across all rows
    num_cols = len(header_cells)
    for row in rows:
        num_cols = max(num_cols, len(row))

    if num_cols == 0:
        return ""

    # Pad header cells if needed
    while len(header_cells) < num_cols:
        header_cells.append("")
    while len(alignments) < num_cols:
        alignments.append("---")

    # Pad data rows
    for row in rows:
        while len(row) < num_cols:
            row.append("")

    # Construct GFM table lines
    lines: List[str] = []
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(alignments) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n" + "\n".join(lines) + "\n"
