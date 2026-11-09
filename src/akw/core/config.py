"""Configuration models for AI Knowledge Wrapper (akw)."""

from __future__ import annotations

import os
from typing import Optional
from pydantic import BaseModel, Field


class AKWConfig(BaseModel):
    """Central configuration for akw library and services."""

    # Storage
    db_path: str = Field(
        default_factory=lambda: os.getenv("AKW_DB_PATH", "./knowledge_base.sqlite"),
        description="Path to SQLite database file"
    )
    assets_dir: str = Field(
        default_factory=lambda: os.getenv("AKW_ASSETS_DIR", "./knowledge_assets"),
        description="Directory to store extracted image and figure assets"
    )
    files_dir: str = Field(
        default_factory=lambda: os.getenv("AKW_FILES_DIR", "./knowledge_files"),
        description="Directory to store retained copies of original uploaded documents"
    )
    workspaces_dir: str = Field(
        default_factory=lambda: os.getenv("AKW_WORKSPACES_DIR", "./workspaces"),
        description="Directory managing discrete project workspaces and SQLite databases"
    )

    # Embedding Settings
    embedding_provider: str = Field(
        default_factory=lambda: os.getenv("AKW_EMBEDDING_PROVIDER", "sentence_transformers"),
        description="Provider for dense embeddings: 'sentence_transformers' or 'ollama'"
    )
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("AKW_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        description="Model identifier for embeddings (HuggingFace repo or Ollama tag)"
    )
    embedding_dim: int = Field(
        default=384,
        description="Dimension size of embeddings"
    )

    # Reranking Settings
    reranker_provider: str = Field(
        default_factory=lambda: os.getenv("AKW_RERANKER_PROVIDER", "flashrank"),
        description="Reranker provider: 'flashrank' or 'none'"
    )
    reranker_model: str = Field(
        default_factory=lambda: os.getenv("AKW_RERANKER_MODEL", "ms-marco-TinyBERT-L-2-v2"),
        description="FlashRank model name"
    )

    # HyDE (Hypothetical Document Embeddings)
    hyde_enabled: bool = Field(
        default_factory=lambda: os.getenv("AKW_HYDE_ENABLED", "true").lower() in ("true", "1", "yes"),
        description="Whether to use local HyDE query expansion"
    )
    hyde_provider: str = Field(
        default_factory=lambda: os.getenv("AKW_HYDE_PROVIDER", "lmstudio"),
        description="LLM provider for HyDE: 'lmstudio', 'ollama', or 'gemini'"
    )
    hyde_model: str = Field(
        default_factory=lambda: os.getenv("AKW_HYDE_MODEL", "qwen/qwen3.5-9b"),
        description="Model used to draft hypothetical passages"
    )
    hyde_host: str = Field(
        default_factory=lambda: os.getenv("AKW_HYDE_HOST", "http://localhost:1234/v1"),
        description="LM Studio or Ollama API base URL"
    )

    # Chunking & Retrieval Parameters
    target_chunk_size: int = Field(
        default=500,
        description="Target chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=100,
        description="Token overlap between consecutive chunks"
    )
    window_expansion: int = Field(
        default=2,
        description="Number of neighboring chunks (+/-) retrieved around seed hits"
    )
    top_k_seeds: int = Field(
        default=3,
        description="Number of top seed chunks to select for context assembly"
    )
    bm25_candidate_limit: int = Field(
        default=50,
        description="Number of BM25 sparse candidates to pull before RRF"
    )
    dense_candidate_limit: int = Field(
        default=50,
        description="Number of dense vector candidates to pull before RRF"
    )

    # Cloud LLM Settings (Google Gemini)
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY"),
        description="Google Gemini API key"
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("AKW_GEMINI_MODEL", "gemini-3.8-flash"),
        description="Default Gemini model"
    )

    # Local LLM Settings (LM Studio & Ollama)
    lmstudio_host: str = Field(
        default_factory=lambda: os.getenv("LMSTUDIO_HOST", "http://localhost:1234/v1"),
        description="LM Studio API base URL (OpenAI-compatible)"
    )
    lmstudio_model: str = Field(
        default_factory=lambda: os.getenv("AKW_LMSTUDIO_MODEL", "qwen/qwen3.5-9b"),
        description="Default LM Studio model"
    )

    # Local Helper & Vision LLM Settings
    helper_llm_provider: str = Field(
        default_factory=lambda: os.getenv("AKW_HELPER_PROVIDER", "lmstudio"),
        description="Provider for local helper LLM tasks: 'lmstudio', 'ollama', 'gemini'"
    )
    helper_llm_model: str = Field(
        default_factory=lambda: os.getenv("AKW_HELPER_MODEL", "qwen/qwen3.5-9b"),
        description="Model identifier for local helper LLM tasks"
    )
    vision_enabled: bool = Field(
        default_factory=lambda: os.getenv("AKW_VISION_ENABLED", "true").lower() in ("true", "1", "yes"),
        description="Whether to analyze figures and presentation slides using a Vision LLM"
    )
    vision_llm_provider: str = Field(
        default_factory=lambda: os.getenv("AKW_VISION_PROVIDER", "lmstudio"),
        description="Provider for Vision LLM: 'lmstudio', 'gemini', 'ollama'"
    )
    vision_llm_model: str = Field(
        default_factory=lambda: os.getenv("AKW_VISION_MODEL", "qwen/qwen3-vl-8b"),
        description="Model identifier for Vision LLM (e.g. 'qwen/qwen3-vl-8b' or 'gemini-3.8-flash')"
    )
    vision_timeout_seconds: int = Field(
        default=45,
        description="Timeout in seconds for vision model inference"
    )
    ollama_host: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        description="Ollama host endpoint"
    )
    ollama_model: str = Field(
        default_factory=lambda: os.getenv("AKW_OLLAMA_MODEL", "qwen/qwen3.5-9b"),
        description="Default local Ollama model for chat"
    )

