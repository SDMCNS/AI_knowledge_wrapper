"""Local Cross-Encoder Reranker using FlashRank."""

from __future__ import annotations

import logging
from typing import List, Optional

try:
    from flashrank import Ranker, RerankRequest
    _FLASHRANK_AVAILABLE = True
except Exception:
    _FLASHRANK_AVAILABLE = False

from akw.core.config import AKWConfig
from akw.core.models import RetrievedChunk

logger = logging.getLogger("akw.reranker")


class LocalReranker:
    """Lightweight CPU-optimized cross-encoder reranker."""

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        self.enabled = self.config.reranker_provider.lower() == "flashrank" and _FLASHRANK_AVAILABLE
        self._ranker = None

    def _get_ranker(self) -> Optional[Ranker]:
        if not self.enabled:
            return None
        if self._ranker is None:
            try:
                self._ranker = Ranker(model_name=self.config.reranker_model, cache_dir="./.cache/flashrank")
            except Exception as e:
                logger.warning("Failed to initialize FlashRank: %s. Falling back to RRF ordering.", e)
                self.enabled = False
        return self._ranker

    def rerank(self, query: str, candidates: List[RetrievedChunk], top_k: int = 5) -> List[RetrievedChunk]:
        """Rerank candidates using cross-encoder scoring."""
        if not candidates:
            return []

        ranker = self._get_ranker()
        if not ranker:
            # Fallback to sorting by RRF score
            sorted_candidates = sorted(candidates, key=lambda c: c.rrf_score or 0.0, reverse=True)
            for idx, c in enumerate(sorted_candidates[:top_k]):
                c.is_seed = True
                c.rerank_score = c.rrf_score
            return sorted_candidates[:top_k]

        try:
            # Prepare passages
            passages = []
            for c in candidates:
                text = f"{c.chunk.breadcrumb_display}\n{c.chunk.content}"
                passages.append({"id": c.chunk.id, "text": text})

            rerank_request = RerankRequest(query=query, passages=passages)
            results = ranker.rerank(rerank_request)

            score_map = {res["id"]: float(res["score"]) for res in results}

            # Assign rerank scores
            for c in candidates:
                c.rerank_score = score_map.get(c.chunk.id, 0.0)

            # Sort descending by rerank score
            sorted_candidates = sorted(candidates, key=lambda c: c.rerank_score or 0.0, reverse=True)
            for c in sorted_candidates[:top_k]:
                c.is_seed = True

            return sorted_candidates[:top_k]
        except Exception as e:
            logger.warning("Reranking failed: %s. Using RRF order.", e)
            sorted_candidates = sorted(candidates, key=lambda c: c.rrf_score or 0.0, reverse=True)
            for c in sorted_candidates[:top_k]:
                c.is_seed = True
            return sorted_candidates[:top_k]

