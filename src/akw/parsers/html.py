"""HTML Document Parser using BeautifulSoup4."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Union

from bs4 import BeautifulSoup, NavigableString, Tag

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser


class HTMLParser(BaseParser):
    """Parses HTML documents with DOM heading hierarchy and semantic element extraction."""

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

            soup = BeautifulSoup(content, "html.parser")
        except Exception as e:
            raise DocumentParseError(f"Failed to read HTML '{filename}': {e}") from e

        try:
            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
                tag.decompose()

            # Find body or main element
            container = soup.body or soup

            for element in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "pre", "li"]):
                tag_name = element.name.lower()

                if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    level = int(tag_name[1])
                    heading_text = element.get_text(" ", strip=True)
                    if heading_text:
                        tracker.update_heading(level=level, title=heading_text)
                        blocks.append(
                            ParsedBlock(
                                content=heading_text,
                                breadcrumb=tracker.get_path(),
                                heading_level=level,
                                block_type=BlockType.HEADING,
                            )
                        )

                elif tag_name == "p":
                    text = element.get_text(" ", strip=True)
                    if text:
                        blocks.append(
                            ParsedBlock(
                                content=text,
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.PARAGRAPH,
                            )
                        )

                elif tag_name == "pre":
                    code_text = element.get_text("\n", strip=True)
                    if code_text:
                        blocks.append(
                            ParsedBlock(
                                content=f"```\n{code_text}\n```",
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.CODE,
                            )
                        )

                elif tag_name == "table":
                    table_md = self._table_to_markdown(element)
                    if table_md.strip():
                        blocks.append(
                            ParsedBlock(
                                content=table_md,
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.TABLE,
                            )
                        )

                elif tag_name == "li":
                    item_text = element.get_text(" ", strip=True)
                    if item_text:
                        blocks.append(
                            ParsedBlock(
                                content=f"- {item_text}",
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.LIST_ITEM,
                            )
                        )
        except Exception as e:
            raise DocumentParseError(f"Error parsing HTML '{filename}': {e}") from e

        return blocks

    @staticmethod
    def _table_to_markdown(table_tag: Tag) -> str:
        rows_data = []
        for tr in table_tag.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            cell_texts = [cell.get_text(" ", strip=True).replace("\n", " ") for cell in cells]
            if cell_texts:
                rows_data.append(cell_texts)

        if not rows_data:
            return ""

        header = rows_data[0]
        md = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]
        for row in rows_data[1:]:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            md.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n".join(md)
