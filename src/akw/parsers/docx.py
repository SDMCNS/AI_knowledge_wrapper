"""DOCX Document Parser using python-docx."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Optional, Union

import docx

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser
from akw.parsers.vision import VisionEngine
from akw.storage.assets import AssetManager


class DocxParser(BaseParser):
    """Parses Microsoft Word (.docx) files preserving native style hierarchies, tables, and figures."""

    def __init__(
        self,
        vision_engine: Optional[VisionEngine] = None,
        asset_manager: Optional[AssetManager] = None,
    ):
        self.vision_engine = vision_engine
        self.asset_manager = asset_manager

    def parse(self, file_source: Union[str, Path, BinaryIO, bytes], filename: str) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        tracker = BreadcrumbTracker(document_title=filename)

        try:
            if isinstance(file_source, bytes):
                doc = docx.Document(io.BytesIO(file_source))
            elif isinstance(file_source, (str, Path)):
                doc = docx.Document(str(file_source))
            else:
                data = file_source.read()
                doc = docx.Document(io.BytesIO(data))
        except Exception as e:
            raise DocumentParseError(f"Failed to open DOCX '{filename}': {e}") from e

        try:
            # We iterate through the body elements to preserve interweaving of paragraphs and tables
            for child in doc.element.body:
                # Check for paragraph
                if child.tag.endswith("p"):
                    p = docx.text.paragraph.Paragraph(child, doc)

                    # Extract embedded figures/diagrams in the paragraph
                    self._extract_paragraph_images(p, doc, tracker, blocks)

                    text = p.text.strip()
                    if not text:
                        continue

                    style_name = p.style.name if p.style else ""
                    style_lower = style_name.lower()

                    if "heading 1" in style_lower or style_lower == "title":
                        tracker.update_heading(level=1, title=text)
                        blocks.append(
                            ParsedBlock(
                                content=text,
                                breadcrumb=tracker.get_path(),
                                heading_level=1,
                                block_type=BlockType.HEADING,
                            )
                        )
                    elif "heading 2" in style_lower or style_lower == "subtitle":
                        tracker.update_heading(level=2, title=text)
                        blocks.append(
                            ParsedBlock(
                                content=text,
                                breadcrumb=tracker.get_path(),
                                heading_level=2,
                                block_type=BlockType.HEADING,
                            )
                        )
                    elif "heading 3" in style_lower:
                        tracker.update_heading(level=3, title=text)
                        blocks.append(
                            ParsedBlock(
                                content=text,
                                breadcrumb=tracker.get_path(),
                                heading_level=3,
                                block_type=BlockType.HEADING,
                            )
                        )
                    elif "list" in style_lower:
                        blocks.append(
                            ParsedBlock(
                                content=f"- {text}",
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.LIST_ITEM,
                            )
                        )
                    else:
                        blocks.append(
                            ParsedBlock(
                                content=text,
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.PARAGRAPH,
                            )
                        )

                # Check for table
                elif child.tag.endswith("tbl"):
                    t = docx.table.Table(child, doc)
                    table_md = self._table_to_markdown(t)
                    if table_md.strip():
                        blocks.append(
                            ParsedBlock(
                                content=table_md,
                                breadcrumb=tracker.get_path(),
                                block_type=BlockType.TABLE,
                            )
                        )
        except Exception as e:
            raise DocumentParseError(f"Error parsing DOCX '{filename}': {e}") from e

        return blocks

    def _extract_paragraph_images(
        self,
        p: docx.text.paragraph.Paragraph,
        doc: docx.Document,
        tracker: BreadcrumbTracker,
        blocks: List[ParsedBlock],
    ) -> None:
        """Extract drawings and images embedded within a docx paragraph."""
        try:
            blips = p._p.xpath(".//a:blip")
            for blip in blips:
                embed_id = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                if not embed_id or embed_id not in doc.part.related_parts:
                    continue
                part = doc.part.related_parts[embed_id]
                image_bytes = getattr(part, "blob", None)
                if not image_bytes or len(image_bytes) < 100:
                    continue
                content_type = getattr(part, "content_type", "image/png") or "image/png"

                # Persist image file copy if asset manager available
                asset_id = None
                image_url = None
                if self.asset_manager:
                    asset_id, image_url = self.asset_manager.save_image(
                        image_bytes=image_bytes, mime_type=content_type
                    )

                desc = None
                if self.vision_engine and getattr(self.vision_engine.config, "vision_enabled", False):
                    desc = self.vision_engine.describe_image(
                        image_bytes=image_bytes,
                        mime_type=content_type,
                        prompt=(
                            "Analyze this document figure, diagram, or chart. "
                            "Transcribe any visible labels, numbers, axis data, and summarize key insights."
                        ),
                    )

                content_lines = []
                if image_url:
                    content_lines.append(f"![Document Figure]({image_url})")
                if desc and desc.strip():
                    content_lines.append(f"**[Document Figure / Diagram Description]:**\n{desc.strip()}")
                elif not image_url:
                    continue

                if content_lines:
                    blocks.append(
                        ParsedBlock(
                            content="\n\n".join(content_lines),
                            breadcrumb=tracker.get_path(),
                            block_type=BlockType.FIGURE,
                            metadata={
                                "image_url": image_url,
                                "asset_id": asset_id,
                                "is_figure": True,
                            },
                        )
                    )
        except Exception:
            pass

    @staticmethod
    def _table_to_markdown(table: docx.table.Table) -> str:
        rows_data = []
        for row in table.rows:
            cell_texts = [cell.text.replace("\n", " ").strip() for cell in row.cells]
            rows_data.append(cell_texts)

        if not rows_data:
            return ""

        header = rows_data[0]
        md = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]
        for row in rows_data[1:]:
            md.append("| " + " | ".join(row) + " |")

        return "\n".join(md)
