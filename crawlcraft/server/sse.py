"""Server-Sent Events (SSE) formatting helper."""

import json
from typing import Any, Dict, Optional


def format_sse(data: Dict[str, Any] | str, event: Optional[str] = None, event_id: Optional[str] = None) -> str:
    """Formats payload as an SSE chunk complying with W3C Server-Sent Events standard."""
    lines = []
    if event:
        lines.append(f"event: {event}")
    if event_id:
        lines.append(f"id: {event_id}")

    payload_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    for line in payload_str.splitlines():
        lines.append(f"data: {line}")

    return "\n".join(lines) + "\n\n"
