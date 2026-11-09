"""Contiguous Context Window Expander (+/- 2 chunks) with interval merging."""

from __future__ import annotations

from typing import Dict, List, Tuple

from akw.core.models import Chunk, Citation, ExpandedContextBlock, RetrievedChunk
from akw.storage.sqlite_db import SQLiteStorage


class ContextWindowExpander:
    """Expands retrieved seed chunks with contiguous neighbor chunks (+/- 2) and merges overlaps."""

    def __init__(self, storage: SQLiteStorage, window_size: int = 2):
        self.storage = storage
        self.window_size = window_size

    def expand_and_assemble(
        self, seed_candidates: List[RetrievedChunk]
    ) -> Tuple[List[ExpandedContextBlock], List[Citation]]:
        """Expand seeds into merged contiguous context blocks and generate citation objects.
        
        Returns:
            Tuple of (ExpandedContextBlocks, Citations)
        """
        if not seed_candidates:
            return [], []

        # 1. Group seed chunks by document_id
        doc_seeds: Dict[str, List[RetrievedChunk]] = {}
        for cand in seed_candidates:
            doc_id = cand.chunk.document_id
            doc_seeds.setdefault(doc_id, []).append(cand)

        context_blocks: List[ExpandedContextBlock] = []
        citations: List[Citation] = []
        citation_counter = 1

        for doc_id, seeds in doc_seeds.items():
            doc = self.storage.get_document(doc_id)
            doc_name = doc.filename if doc else f"Document_{doc_id[:8]}"

            # Sort seeds by chunk_index
            seeds.sort(key=lambda s: s.chunk.chunk_index)

            # Compute intervals [idx - window_size, idx + window_size]
            intervals: List[Tuple[int, int, List[RetrievedChunk]]] = []
            for s in seeds:
                idx = s.chunk.chunk_index
                start_idx = max(0, idx - self.window_size)
                end_idx = idx + self.window_size
                intervals.append((start_idx, end_idx, [s]))

            # Merge overlapping or contiguous intervals
            merged_intervals = self._merge_intervals(intervals)

            # For each merged interval, fetch all contiguous chunks
            for start_idx, end_idx, int_seeds in merged_intervals:
                contiguous_chunks = self.storage.get_neighbor_chunks(doc_id, start_idx, end_idx)
                if not contiguous_chunks:
                    continue

                ref_id = f"REF-{citation_counter}"
                citation_counter += 1

                seed_indices = [s.chunk.chunk_index for s in int_seeds]
                max_score = max((s.rerank_score or s.rrf_score or 0.0) for s in int_seeds)
                primary_breadcrumb = int_seeds[0].chunk.breadcrumb_display

                # Determine overall page bounds
                pages = [c.page_start for c in contiguous_chunks if c.page_start is not None]
                page_start = min(pages) if pages else None
                pages_end = [c.page_end for c in contiguous_chunks if c.page_end is not None]
                page_end = max(pages_end) if pages_end else None

                # Assemble merged text with clear chunk delimitation
                text_segments = []
                for c in contiguous_chunks:
                    is_seed = c.chunk_index in seed_indices
                    if is_seed:
                        text_segments.append(f"[Matched Content - Chunk #{c.chunk_index}]\n{c.content}")
                    else:
                        text_segments.append(f"[Context - Chunk #{c.chunk_index}]\n{c.content}")

                merged_text = "\n\n".join(text_segments)

                block = ExpandedContextBlock(
                    citation_id=ref_id,
                    document_id=doc_id,
                    document_name=doc_name,
                    breadcrumb=primary_breadcrumb,
                    page_start=page_start,
                    page_end=page_end,
                    seed_indices=seed_indices,
                    chunks=contiguous_chunks,
                    merged_text=merged_text,
                    relevance_score=max_score,
                )
                context_blocks.append(block)

                # Build citation summary
                seed_chunk = int_seeds[0].chunk
                excerpt = seed_chunk.content[:200] + "..." if len(seed_chunk.content) > 200 else seed_chunk.content
                citations.append(
                    Citation(
                        id=ref_id,
                        document_name=doc_name,
                        breadcrumb=primary_breadcrumb,
                        page_start=page_start,
                        page_end=page_end,
                        score=max_score,
                        excerpt=excerpt,
                    )
                )

        # Sort context blocks descending by relevance score
        context_blocks.sort(key=lambda b: b.relevance_score, reverse=True)
        return context_blocks, citations

    @staticmethod
    def _merge_intervals(
        intervals: List[Tuple[int, int, List[RetrievedChunk]]]
    ) -> List[Tuple[int, int, List[RetrievedChunk]]]:
        """Merge intervals that overlap or touch."""
        if not intervals:
            return []

        # Sort by start_idx
        intervals.sort(key=lambda x: x[0])
        merged = [intervals[0]]

        for current in intervals[1:]:
            prev_start, prev_end, prev_seeds = merged[-1]
            curr_start, curr_end, curr_seeds = current

            if curr_start <= prev_end + 1:
                # Merge
                new_end = max(prev_end, curr_end)
                merged[-1] = (prev_start, new_end, prev_seeds + curr_seeds)
            else:
                merged.append(current)

        return merged

