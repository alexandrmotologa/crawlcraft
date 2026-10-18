"""Hierarchical Markdown chunking engine for RAG pipelines and vector stores."""

import re
from typing import Any, Dict, List, Optional
import tiktoken


class MarkdownChunk:
    """Represents a coherent token-bounded chunk of a Markdown document with hierarchical context."""

    def __init__(
        self,
        chunk_id: str,
        content: str,
        breadcrumbs: List[str],
        token_count: int,
        char_count: int,
        word_count: int,
        index: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.chunk_id = chunk_id
        self.content = content
        self.breadcrumbs = breadcrumbs
        self.token_count = token_count
        self.char_count = char_count
        self.word_count = word_count
        self.index = index
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "breadcrumbs": self.breadcrumbs,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "index": self.index,
            "metadata": self.metadata,
        }


class MarkdownChunker:
    """Splits Markdown text into semantically coherent chunks preserving header hierarchies and code blocks."""

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = min(overlap_tokens, max_tokens // 4)
        self.encoding_name = encoding_name
        self.encoder = tiktoken.get_encoding(encoding_name)

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.encoder.encode(text, disallowed_special=()))

    def chunk_document(
        self,
        markdown: str,
        doc_id: str = "doc",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MarkdownChunk]:
        """Splits markdown into hierarchical chunks."""
        if not markdown or not markdown.strip():
            return []

        # Split into structural blocks (preserving headers, code blocks, tables, and paragraphs)
        blocks = self._split_into_blocks(markdown)
        chunks: List[MarkdownChunk] = []

        current_breadcrumbs: List[str] = []
        current_block_texts: List[str] = []
        current_token_count = 0
        chunk_idx = 0

        for block, block_type, heading_info in blocks:
            if block_type == "heading" and heading_info:
                level, title = heading_info
                # Update breadcrumb stack
                while len(current_breadcrumbs) >= level:
                    current_breadcrumbs.pop()
                current_breadcrumbs.append(title)

            block_tokens = self._count_tokens(block)

            # If a single block is larger than max_tokens, flush current and slice it
            if block_tokens > self.max_tokens:
                if current_block_texts:
                    chunk_text = "\n\n".join(current_block_texts).strip()
                    c_tokens = self._count_tokens(chunk_text)
                    chunks.append(
                        MarkdownChunk(
                            chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                            content=chunk_text,
                            breadcrumbs=list(current_breadcrumbs),
                            token_count=c_tokens,
                            char_count=len(chunk_text),
                            word_count=len(chunk_text.split()),
                            index=chunk_idx,
                            metadata=extra_metadata or {},
                        )
                    )
                    chunk_idx += 1
                    current_block_texts = []
                    current_token_count = 0

                # Slice large block into token-sized windows
                sub_chunks = self._slice_oversized_block(block, doc_id, chunk_idx, current_breadcrumbs, extra_metadata)
                chunks.extend(sub_chunks)
                chunk_idx += len(sub_chunks)
                continue

            # Check if adding this block exceeds max_tokens
            if (current_token_count + block_tokens) > self.max_tokens and current_block_texts:
                chunk_text = "\n\n".join(current_block_texts).strip()
                c_tokens = self._count_tokens(chunk_text)
                chunks.append(
                    MarkdownChunk(
                        chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                        content=chunk_text,
                        breadcrumbs=list(current_breadcrumbs),
                        token_count=c_tokens,
                        char_count=len(chunk_text),
                        word_count=len(chunk_text.split()),
                        index=chunk_idx,
                        metadata=extra_metadata or {},
                    )
                )
                chunk_idx += 1

                # Overlap: keep the last block if it fits within overlap_tokens
                if self.overlap_tokens > 0 and current_block_texts:
                    last_block = current_block_texts[-1]
                    last_block_tokens = self._count_tokens(last_block)
                    if last_block_tokens <= self.overlap_tokens:
                        current_block_texts = [last_block]
                        current_token_count = last_block_tokens
                    else:
                        current_block_texts = []
                        current_token_count = 0
                else:
                    current_block_texts = []
                    current_token_count = 0

            current_block_texts.append(block)
            current_token_count += block_tokens

        # Flush any remaining blocks
        if current_block_texts:
            chunk_text = "\n\n".join(current_block_texts).strip()
            c_tokens = self._count_tokens(chunk_text)
            chunks.append(
                MarkdownChunk(
                    chunk_id=f"{doc_id}_chunk_{chunk_idx}",
                    content=chunk_text,
                    breadcrumbs=list(current_breadcrumbs),
                    token_count=c_tokens,
                    char_count=len(chunk_text),
                    word_count=len(chunk_text.split()),
                    index=chunk_idx,
                    metadata=extra_metadata or {},
                )
            )

        return chunks

    def _split_into_blocks(self, text: str) -> List[tuple[str, str, Optional[tuple[int, str]]]]:
        """Splits markdown into blocks, classifying headings, code fences, and paragraphs."""
        raw_lines = text.splitlines()
        blocks = []
        current_lines: List[str] = []
        in_code_fence = False

        for line in raw_lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                in_code_fence = not in_code_fence
                current_lines.append(line)
                if not in_code_fence:
                    # Closing code fence ends the block
                    blocks.append(("\n".join(current_lines), "code", None))
                    current_lines = []
                continue

            if in_code_fence:
                current_lines.append(line)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                if current_lines:
                    blocks.append(("\n".join(current_lines), "text", None))
                    current_lines = []
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                blocks.append((line, "heading", (level, title)))
                continue

            if not stripped:
                if current_lines:
                    blocks.append(("\n".join(current_lines), "text", None))
                    current_lines = []
                continue

            current_lines.append(line)

        if current_lines:
            blocks.append(("\n".join(current_lines), "text", None))

        return blocks

    def _slice_oversized_block(
        self,
        block: str,
        doc_id: str,
        start_idx: int,
        breadcrumbs: List[str],
        metadata: Optional[Dict[str, Any]],
    ) -> List[MarkdownChunk]:
        """Slices a single block exceeding max_tokens into smaller token windows."""
        tokens = self.encoder.encode(block, disallowed_special=())
        chunks: List[MarkdownChunk] = []
        idx = start_idx
        step = self.max_tokens - self.overlap_tokens

        for i in range(0, len(tokens), step):
            sub_tokens = tokens[i : i + self.max_tokens]
            sub_text = self.encoder.decode(sub_tokens)
            chunks.append(
                MarkdownChunk(
                    chunk_id=f"{doc_id}_chunk_{idx}",
                    content=sub_text.strip(),
                    breadcrumbs=list(breadcrumbs),
                    token_count=len(sub_tokens),
                    char_count=len(sub_text),
                    word_count=len(sub_text.split()),
                    index=idx,
                    metadata=metadata or {},
                )
            )
            idx += 1

        return chunks


def chunk_markdown(
    markdown: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    doc_id: str = "doc",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[MarkdownChunk]:
    """Convenience helper to hierarchically chunk Markdown for vector embeddings."""
    chunker = MarkdownChunker(max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    return chunker.chunk_document(markdown, doc_id=doc_id, extra_metadata=metadata)
