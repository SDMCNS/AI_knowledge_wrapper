"""Base document parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, List, Union

from akw.core.models import ParsedBlock


class BaseParser(ABC):
    """Abstract base class for all file parsers."""

    @abstractmethod
    def parse(self, file_source: Union[str, Path, BinaryIO, bytes], filename: str) -> List[ParsedBlock]:
        """Parse a document into an ordered list of ParsedBlocks.
        
        Args:
            file_source: Path to file, bytes, or binary file-like object.
            filename: Original file name used for title and breadcrumb derivation.
            
        Returns:
            List of ParsedBlock objects containing content and breadcrumb context.
        """
        pass
