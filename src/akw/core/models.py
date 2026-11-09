"""Core data models for AI Knowledge Wrapper (akw)."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    CODE = "code"
    LIST_ITEM = "list_item"
    FIGURE = "figure"


class ParsedBlock(BaseModel):
    """An intermediate block of extracted content from a document parser."""
    content: str
    breadcrumb: List[str] = Field(default_factory=list)
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    heading_level: Optional[int] = None
    block_type: BlockType = BlockType.PARAGRAPH
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """A record representing an ingested document stored in SQLite."""
    id: str
    filename: str
    file_path: Optional[str] = None
    sha256_hash: str
    mime_type: str
    file_size_bytes: int
    total_chunks: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """An individual indexed chunk of text within a document."""
    id: str
    document_id: str
    chunk_index: int  # Sequential 0-based index within parent document
    content: str
    breadcrumb_display: str
    breadcrumb_path: List[str] = Field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    token_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StagedChunk(BaseModel):
    """A draft chunk presented to user for review/editing before commit."""
    staging_id: str
    chunk_index: int
    content: str
    breadcrumb_display: str
    breadcrumb_path: List[str] = Field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    token_count: int = 0
    is_retained: bool = True
    is_modified: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StagedDocument(BaseModel):
    """A parsed and chunked document awaiting user review and approval."""
    staging_id: str
    filename: str
    sha256_hash: str
    mime_type: str
    file_size_bytes: int
    chunks: List[StagedChunk]
    file_path: Optional[str] = None


class CommitChunksRequest(BaseModel):
    """Payload sent by the user to commit reviewed/edited chunks to SQLite."""
    staging_id: str
    filename: str
    sha256_hash: str
    mime_type: Optional[str] = None
    file_size_bytes: int = 0
    chunks: List[StagedChunk]
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """A retrieved chunk candidate scored during search."""
    chunk: Chunk
    dense_score: Optional[float] = None
    dense_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    is_seed: bool = False


class ExpandedContextBlock(BaseModel):
    """A contiguous context block assembled around a seed chunk (+/- 2 neighbors)."""
    citation_id: str  # e.g., "REF-1"
    document_id: str
    document_name: str
    breadcrumb: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    seed_indices: List[int] = Field(default_factory=list)
    chunks: List[Chunk] = Field(default_factory=list)
    merged_text: str
    relevance_score: float = 0.0


class Citation(BaseModel):
    """Grounded reference citation for LLM generation."""
    id: str  # e.g., "REF-1"
    document_name: str
    breadcrumb: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    score: float = 0.0
    excerpt: str = ""


class ChatRole(str, Enum):
    USER = "user"
    MODEL = "model"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A message in a chat session."""
    id: str
    session_id: str
    role: ChatRole
    content: str
    context_blocks: Optional[List[ExpandedContextBlock]] = None
    citations: Optional[List[Citation]] = None
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class ChatSession(BaseModel):
    """A chat session."""
    id: str
    title: str
    model_provider: str  # "gemini" | "ollama" | "local"
    model_name: str
    system_instruction: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

