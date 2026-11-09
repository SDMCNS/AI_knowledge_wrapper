"""Markdown Document Parser preserving heading hierarchies and code blocks."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, List, Union

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser


class MarkdownParser(BaseParser):
    """Parses Markdown (.md, .markdown) files, tracking heading depths and preserving code."""

    HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$")

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes], filename: str) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        tracker = BreadcrumbTracker(document_title=filename)

        try:
            if isinstance(file_source, bytes):
                text = file_source.decode("utf-8", errors="replace")
                lines = text.splitlines(keepends=True)
            elif isinstance(file_source, (str, Path)):
                with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            else:
                data = file_source.read()
                text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
                lines = text.splitlines(keepends=True)
        except Exception as e:
            raise DocumentParseError(f"Failed to read Markdown '{filename}': {e}") from e

        try:
            in_code_block = False
            code_buffer: List[str] = []
            para_buffer: List[str] = []

            def flush_para():
                nonlocal para_buffer
                if para_buffer:
                    content = "".join(para_buffer).strip()
                    if content:
                        blocks.append(
                            ParsedBlock(
                                content=content,
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.PARAGRAPH,
                            )
                        )
                    para_buffer = []

            for line in lines:
                stripped = line.strip()

                # Check code block fences
                if stripped.startswith("```"):
                    if in_code_block:
                        code_buffer.append(line)
                        blocks.append(
                            ParsedBlock(
                                content="".join(code_buffer).strip(),
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.CODE,
                            )
                        )
                        code_buffer = []
                        in_code_block = False
                    else:
                        flush_para()
                        in_code_block = True
                        code_buffer.append(line)
                    continue

                if in_code_block:
                    code_buffer.append(line)
                    continue

                # Check headings
                heading_match = self.HEADING_REGEX.match(stripped)
                if heading_match:
                    flush_para()
                    level = len(heading_match.group(1))
                    title = heading_match.group(2).strip()
                    tracker.update_heading(level=level, title=title)
                    blocks.append(
                        ParsedBlock(
                            content=title,
                            breadcrumb=tracker.get_path(),
                            heading_level=level,
                            block_type=BlockType.HEADING,
                        )
                    )
                    continue

                # Blank line flushes paragraph
                if not stripped:
                    flush_para()
                    continue

                para_buffer.append(line)

            # Flush any remaining buffers
            flush_para()
            if code_buffer:
                blocks.append(
                    ParsedBlock(
                        content="".join(code_buffer).strip(),
                        breadcrumb=tracker.get_path(),
                        block_type=BlockType.CODE,
                    )
                )

        except Exception as e:
            raise DocumentParseError(f"Error parsing Markdown '{filename}': {e}") from e

        return blocks
