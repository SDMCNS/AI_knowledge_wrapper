"""Windowed Semantic Chunker for generating consistent, breadcrumb-annotated chunks."""

from __future__ import annotations

import re
import uuid
from typing import List, Optional

try:
    import tiktoken
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None

from akw.core.models import BlockType, Chunk, ParsedBlock


class WindowedSemanticChunker:
    """Chunks structured blocks into sequential, breadcrumb-annotated chunks."""

    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.?!])\s+(?=[A-Z0-9])")

    def __init__(self, target_chunk_size: int = 500, chunk_overlap: int = 100):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken cl100k_base, with character-based fallback."""
        if _TIKTOKEN_ENCODER:
            try:
                return len(_TIKTOKEN_ENCODER.encode(text))
            except Exception:
                pass
        # Fallback: roughly 4 chars per token
        return max(1, len(text) // 4)

    def chunk_blocks(self, blocks: List[ParsedBlock], document_id: str) -> List[Chunk]:
        """Convert a sequence of parsed blocks into ordered, sequential chunks."""
        if not blocks:
            return []

        chunks: List[Chunk] = []
        chunk_index = 0

        current_text_segments: List[str] = []
        current_breadcrumb_path: List[str] = []
        current_page_start: Optional[int] = None
        current_page_end: Optional[int] = None
        current_tokens = 0

        def flush_current_chunk(custom_metadata: Optional[dict] = None):
            nonlocal chunk_index, current_text_segments, current_tokens, current_breadcrumb_path
            nonlocal current_page_start, current_page_end

            if not current_text_segments:
                return

            full_text = "\n\n".join(current_text_segments).strip()
            if not full_text:
                current_text_segments = []
                current_tokens = 0
                return

            breadcrumb_display = " > ".join(current_breadcrumb_path) if current_breadcrumb_path else ""

            chunk_obj = Chunk(
                id=f"chk_{uuid.uuid4().hex[:12]}",
                document_id=document_id,
                chunk_index=chunk_index,
                content=full_text,
                breadcrumb_display=breadcrumb_display,
                breadcrumb_path=list(current_breadcrumb_path),
                page_start=current_page_start,
                page_end=current_page_end,
                token_count=current_tokens,
                metadata=dict(custom_metadata) if custom_metadata else {},
            )
            chunks.append(chunk_obj)
            chunk_index += 1

            # Handle overlap: carry over trailing segment if substantial (and not a figure)
            if self.chunk_overlap > 0 and len(current_text_segments) > 1 and not custom_metadata:
                last_segment = current_text_segments[-1]
                last_tokens = self.count_tokens(last_segment)
                if last_tokens <= self.chunk_overlap:
                    current_text_segments = [last_segment]
                    current_tokens = last_tokens
                else:
                    current_text_segments = []
                    current_tokens = 0
            else:
                current_text_segments = []
                current_tokens = 0

            current_page_start = current_page_end

        for block in blocks:
            block_content = block.content.strip()
            if not block_content:
                continue

            block_tokens = self.count_tokens(block_content)
            block_breadcrumb = block.breadcrumb

            # If block is a dedicated figure, flush previous text and emit figure as isolated chunk
            if block.block_type == BlockType.FIGURE or block.metadata.get("is_figure"):
                if current_text_segments:
                    flush_current_chunk()
                current_breadcrumb_path = block_breadcrumb
                current_page_start = block.page_number
                current_page_end = block.page_number
                current_text_segments = [block_content]
                current_tokens = block_tokens
                flush_current_chunk(custom_metadata=block.metadata)
                continue

            # If breadcrumb path changed, flush previous chunk if we have content
            if current_breadcrumb_path and block_breadcrumb and current_breadcrumb_path != block_breadcrumb and current_tokens >= 30:
                flush_current_chunk()
                current_breadcrumb_path = block_breadcrumb
                current_page_start = block.page_number

            if not current_breadcrumb_path and block_breadcrumb:
                current_breadcrumb_path = block_breadcrumb

            # Track pages
            if block.page_number is not None:
                if current_page_start is None:
                    current_page_start = block.page_number
                current_page_end = block.page_number

            # If single block is huge, split on sentences
            if block_tokens > self.target_chunk_size:
                sentences = self.SENTENCE_SPLIT_REGEX.split(block_content)
                for sentence in sentences:
                    stext = sentence.strip()
                    if not stext:
                        continue
                    stokens = self.count_tokens(stext)

                    if current_tokens + stokens > self.target_chunk_size and current_text_segments:
                        flush_current_chunk()
                        current_breadcrumb_path = block_breadcrumb
                        current_page_start = block.page_number
                        current_page_end = block.page_number

                    current_text_segments.append(stext)
                    current_tokens += stokens
            else:
                # Check if adding this block exceeds target chunk size
                if current_tokens + block_tokens > self.target_chunk_size and current_text_segments:
                    flush_current_chunk()
                    current_breadcrumb_path = block_breadcrumb
                    current_page_start = block.page_number
                    current_page_end = block.page_number

                current_text_segments.append(block_content)
                current_tokens += block_tokens

        # Flush any remaining content
        flush_current_chunk()

        return chunks
