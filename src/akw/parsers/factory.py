"""Parser Factory resolving document parsers by file extension or MIME type."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Dict, Optional, Type

from akw.core.exceptions import UnsupportedFileTypeError
from akw.parsers.base import BaseParser
from akw.parsers.docx import DocxParser
from akw.parsers.excel import ExcelParser
from akw.parsers.html import HTMLParser
from akw.parsers.markdown import MarkdownParser
from akw.parsers.pdf import PDFParser
from akw.parsers.pptx_parser import PPTXParser
from akw.parsers.text import TextParser
from akw.parsers.vision import VisionEngine
from akw.storage.assets import AssetManager


class ParserFactory:
    """Factory for obtaining the appropriate parser for a given file."""

    _EXTENSION_MAP: Dict[str, Type[BaseParser]] = {
        ".pdf": PDFParser,
        ".pptx": PPTXParser,
        ".ppt": PPTXParser,
        ".docx": DocxParser,
        ".xlsx": ExcelParser,
        ".xls": ExcelParser,
        ".csv": ExcelParser,
        ".html": HTMLParser,
        ".htm": HTMLParser,
        ".md": MarkdownParser,
        ".markdown": MarkdownParser,
        ".txt": TextParser,
        ".json": TextParser,
        ".yaml": TextParser,
        ".yml": TextParser,
        ".xml": TextParser,
        ".py": TextParser,
        ".js": TextParser,
        ".ts": TextParser,
        ".sql": TextParser,
        ".sh": TextParser,
        ".ini": TextParser,
        ".env": TextParser,
    }

    @classmethod
    def get_parser(
        cls,
        filename: str,
        vision_engine: Optional[VisionEngine] = None,
        asset_manager: Optional[AssetManager] = None,
    ) -> BaseParser:
        """Resolve and instantiate a parser based on filename extension."""
        ext = Path(filename).suffix.lower()
        parser_cls = cls._EXTENSION_MAP.get(ext)

        if not parser_cls:
            # Fallback to TextParser if plain text mime type
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type and (mime_type.startswith("text/") or "json" in mime_type or "xml" in mime_type):
                parser_cls = TextParser
            else:
                raise UnsupportedFileTypeError(
                    f"Unsupported file format '{ext}' for file '{filename}'. Supported formats: "
                    + ", ".join(sorted(cls._EXTENSION_MAP.keys()))
                )

        if parser_cls in (PDFParser, PPTXParser, DocxParser):
            return parser_cls(vision_engine=vision_engine, asset_manager=asset_manager)  # type: ignore[call-arg]

        return parser_cls()

