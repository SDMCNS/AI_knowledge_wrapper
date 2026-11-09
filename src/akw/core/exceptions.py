"""Exceptions for AI Knowledge Wrapper (akw)."""

class AKWError(Exception):
    """Base exception for all akw errors."""
    pass


class DocumentParseError(AKWError):
    """Raised when parsing a document fails."""
    pass


class UnsupportedFileTypeError(AKWError):
    """Raised when an unsupported file type is provided."""
    pass


class StorageError(AKWError):
    """Raised when SQLite storage operations encounter an error."""
    pass


class EmbeddingError(AKWError):
    """Raised when embedding generation fails."""
    pass


class RetrievalError(AKWError):
    """Raised when search or retrieval operations fail."""
    pass


class LLMError(AKWError):
    """Raised when Gemini or local LLM generation encounters an error."""
    pass

