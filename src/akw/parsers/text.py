"""Plain text, source code, and configuration parser."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Union

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser


class TextParser(BaseParser):
    """Parses plain text (.txt), source code (.py, .ts, etc.), JSON, and YAML."""

    def __init__(self, paragraph_split_lines: int = 50):
        self.paragraph_split_lines = paragraph_split_lines

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes], filename: str) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        tracker = BreadcrumbTracker(document_title=filename)

        try:
            if isinstance(file_source, bytes):
                content = file_source.decode("utf-8", errors="replace")
            elif isinstance(file_source, (str, Path)):
                with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            else:
                data = file_source.read()
                content = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        except Exception as e:
            raise DocumentParseError(f"Failed to read text file '{filename}': {e}") from e

        # Determine if it's code/structured or prose
        ext = Path(filename).suffix.lower()
        is_code = ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".sql", ".sh")
        is_json_yaml = ext in (".json", ".yaml", ".yml", ".toml", ".xml")

        # Split into double-newline sections or line chunks
        raw_sections = content.split("\n\n")

        for sec in raw_sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            block_type = BlockType.CODE if (is_code or is_json_yaml) else BlockType.PARAGRAPH
            blocks.append(
                ParsedBlock(
                    content=sec_clean,
                    breadcrumb=tracker.get_path(),
                    block_type=block_type,
                )
            )

        if not blocks and content.strip():
            blocks.append(
                ParsedBlock(
                    content=content.strip(),
                    breadcrumb=tracker.get_path(),
                    block_type=BlockType.CODE if is_code else BlockType.PARAGRAPH,
                )
            )

        return blocks
