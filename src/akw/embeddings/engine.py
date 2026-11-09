"""Local Dense Embedding Engine supporting SentenceTransformers and Ollama."""

from __future__ import annotations

from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

import requests

from akw.core.config import AKWConfig
from akw.core.exceptions import EmbeddingError


class EmbeddingEngine:
    """Generates dense vector embeddings using local models."""

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        self.provider = self.config.embedding_provider.lower()
        self.model_name = self.config.embedding_model
        self._st_model = None

    def _get_st_model(self) -> SentenceTransformer:
        """Lazy-load the SentenceTransformer model on first usage."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise EmbeddingError("sentence-transformers is not installed.")

        if self._st_model is None:
            try:
                # Load on CPU or CUDA if available
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._st_model = SentenceTransformer(self.model_name, device=device)
            except Exception as e:
                raise EmbeddingError(f"Failed to load embedding model '{self.model_name}': {e}") from e

        return self._st_model

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for a list of text passages."""
        if not texts:
            return np.empty((0, self.config.embedding_dim), dtype=np.float32)

        if self.provider == "ollama":
            return self._embed_ollama(texts)

        # Default: SentenceTransformers
        model = self._get_st_model()
        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return np.asarray(embeddings, dtype=np.float32)
        except Exception as e:
            raise EmbeddingError(f"Error encoding embeddings: {e}") from e

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single user query."""
        results = self.embed_texts([query])
        return results[0]

    def _embed_ollama(self, texts: List[str]) -> np.ndarray:
        """Embed texts using local Ollama endpoint."""
        url = f"{self.config.ollama_host.rstrip('/')}/api/embeddings"
        embeddings: List[List[float]] = []

        for text in texts:
            try:
                response = requests.post(
                    url,
                    json={"model": self.model_name, "prompt": text},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embedding", []))
            except Exception as e:
                raise EmbeddingError(f"Ollama embedding request failed: {e}") from e

        arr = np.array(embeddings, dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

