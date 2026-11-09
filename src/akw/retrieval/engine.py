"""Hybrid Retrieval Engine coordinating HyDE, BM25, Dense Vectors, RRF, Reranker & Window Expansion."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from akw.core.config import AKWConfig
from akw.core.models import Citation, ExpandedContextBlock, RetrievedChunk
from akw.embeddings.engine import EmbeddingEngine
from akw.retrieval.hyde import HyDEGenerator
from akw.retrieval.reranker import LocalReranker
from akw.retrieval.window_expander import ContextWindowExpander
from akw.storage.sqlite_db import SQLiteStorage

logger = logging.getLogger("akw.retrieval")


class HybridRetrievalEngine:
    """End-to-end multi-stage hybrid retrieval engine."""

    def __init__(
        self,
        storage: SQLiteStorage,
        embedder: Optional[EmbeddingEngine] = None,
        config: Optional[AKWConfig] = None,
    ):
        self.storage = storage
        self.config = config or AKWConfig()
        self.embedder = embedder or EmbeddingEngine(config=self.config)
        self.hyde = HyDEGenerator(config=self.config)
        self.reranker = LocalReranker(config=self.config)
        self.expander = ContextWindowExpander(storage=self.storage, window_size=self.config.window_expansion)

    def retrieve(
        self, query: str, top_k: Optional[int] = None, expand_window: Optional[int] = None
    ) -> Tuple[List[ExpandedContextBlock], List[Citation]]:
        """Execute end-to-end multi-stage hybrid retrieval."""
        k = top_k or self.config.top_k_seeds
        w_size = expand_window if expand_window is not None else self.config.window_expansion

        # 1. HyDE Query Expansion
        hyde_doc = None
        if self.config.hyde_enabled:
            hyde_doc = self.hyde.generate_hypothetical_document(query)

        # 2. Vector Embedding
        query_vec = self.embedder.embed_query(query)
        if hyde_doc:
            hyde_vec = self.embedder.embed_query(hyde_doc)
            search_vec = self.hyde.blend_embeddings(query_vec, hyde_vec, alpha=0.7)
        else:
            search_vec = query_vec

        # 3. Dense Vector Search
        dense_hits = self.storage.search_vectors(
            query_vector=search_vec,
            model_name=self.config.embedding_model,
            limit=self.config.dense_candidate_limit,
        )

        # 4. Sparse BM25 Search
        bm25_hits = self.storage.search_bm25(query=query, limit=self.config.bm25_candidate_limit)

        # 5. Reciprocal Rank Fusion (RRF)
        fused_candidates = self._reciprocal_rank_fusion(dense_hits, bm25_hits)

        # Take top candidates for cross-encoder reranking
        top_candidates = fused_candidates[:20]

        # 6. Cross-Encoder Reranking
        top_seeds = self.reranker.rerank(query=query, candidates=top_candidates, top_k=k)

        # 7. Neighbor Context Expansion (+/- 2 Chunks)
        if w_size != self.expander.window_size:
            expander = ContextWindowExpander(storage=self.storage, window_size=w_size)
        else:
            expander = self.expander

        context_blocks, citations = expander.expand_and_assemble(top_seeds)
        return context_blocks, citations

    @staticmethod
    def _reciprocal_rank_fusion(
        dense_hits: List[Tuple[Any, float, int]], bm25_hits: List[Tuple[Any, float, int]], rrf_k: int = 60
    ) -> List[RetrievedChunk]:
        """Combine dense and sparse search rankings using Reciprocal Rank Fusion."""
        candidate_map: Dict[str, RetrievedChunk] = {}

        # Process dense hits
        for chunk, score, rank in dense_hits:
            rrf_score = 1.0 / (rrf_k + rank)
            cand = RetrievedChunk(
                chunk=chunk,
                dense_score=score,
                dense_rank=rank,
                rrf_score=rrf_score,
            )
            candidate_map[chunk.id] = cand

        # Process BM25 hits
        for chunk, score, rank in bm25_hits:
            rrf_contrib = 1.0 / (rrf_k + rank)
            if chunk.id in candidate_map:
                candidate_map[chunk.id].bm25_score = score
                candidate_map[chunk.id].bm25_rank = rank
                candidate_map[chunk.id].rrf_score = (candidate_map[chunk.id].rrf_score or 0.0) + rrf_contrib
            else:
                cand = RetrievedChunk(
                    chunk=chunk,
                    bm25_score=score,
                    bm25_rank=rank,
                    rrf_score=rrf_contrib,
                )
                candidate_map[chunk.id] = cand

        # Sort descending by combined RRF score
        fused = list(candidate_map.values())
        fused.sort(key=lambda c: c.rrf_score or 0.0, reverse=True)
        return fused

