"""AI Knowledge Wrapper (akw) - Grounded LLM Knowledge Retrieval Library."""

from akw.core.config import AKWConfig
from akw.core.models import (
    ChatMessage,
    ChatRole,
    ChatSession,
    Chunk,
    Citation,
    Document,
    ExpandedContextBlock,
    ParsedBlock,
)
from akw.kb import KnowledgeBase
from akw.sessions.rag_session import GeminiRAGSession, LMStudioRAGSession, LocalRAGSession

__version__ = "0.1.0"

__all__ = [
    "AKWConfig",
    "KnowledgeBase",
    "GeminiRAGSession",
    "LMStudioRAGSession",
    "LocalRAGSession",
    "Document",
    "Chunk",
    "Citation",
    "ExpandedContextBlock",
    "ChatMessage",
    "ChatSession",
]

