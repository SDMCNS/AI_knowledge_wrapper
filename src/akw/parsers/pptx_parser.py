"""PowerPoint Presentation (.pptx) parser with slide tracking, tables, notes, and vision diagram extraction."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Optional, Union

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser
from akw.parsers.vision import VisionEngine
from akw.storage.assets import AssetManager


class PPTXParser(BaseParser):
    """Parses Microsoft PowerPoint (.pptx) presentations into structured semantic blocks."""

    def __init__(
        self,
        vision_engine: Optional[VisionEngine] = None,
        asset_manager: Optional[AssetManager] = None,
    ):
        self.vision_engine = vision_engine
        self.asset_manager = asset_manager

    def parse(
        self, file_source: Union[str, Path, BinaryIO, bytes], filename: str
    ) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        tracker = BreadcrumbTracker(document_title=filename)

        try:
            if isinstance(file_source, bytes):
                stream = io.BytesIO(file_source)
            elif isinstance(file_source, (str, Path)):
                with open(file_source, "rb") as f:
                    stream = io.BytesIO(f.read())
            else:
                data = file_source.read()
                stream = io.BytesIO(data)

            prs = Presentation(stream)
        except Exception as e:
            raise DocumentParseError(f"Failed to open PPTX presentation '{filename}': {e}") from e

        try:
            for slide_idx, slide in enumerate(prs.slides, start=1):
                # 1. Slide Title & Breadcrumb
                slide_title = self._extract_slide_title(slide, slide_idx)
                tracker.update_heading(level=1, title=f"Slide {slide_idx}: {slide_title}")

                blocks.append(
                    ParsedBlock(
                        content=f"Slide {slide_idx}: {slide_title}",
                        breadcrumb=tracker.get_path(),
                        page_number=slide_idx,
                        heading_level=1,
                        block_type=BlockType.HEADING,
                    )
                )

                # 2. Extract slide shapes (text, tables, images/diagrams)
                self._process_shapes(slide.shapes, slide_idx, tracker, blocks)

                # 3. Extract presenter notes if available
                if slide.has_notes_slide and slide.notes_slide:
                    notes_frame = slide.notes_slide.notes_text_frame
                    if notes_frame and notes_frame.text.strip():
                        clean_notes = notes_frame.text.strip()
                        blocks.append(
                            ParsedBlock(
                                content=f"**Presenter Notes (Slide {slide_idx}):**\n{clean_notes}",
                                breadcrumb=tracker.get_path(),
                                page_number=slide_idx,
                                block_type=BlockType.PARAGRAPH,
                            )
                        )

        except Exception as e:
            raise DocumentParseError(f"Error parsing PPTX presentation '{filename}': {e}") from e

        return blocks

    def _extract_slide_title(self, slide, slide_idx: int) -> str:
        """Extract title shape text if present, else fallback to Slide N."""
        if slide.shapes.title and slide.shapes.title.text.strip():
            return slide.shapes.title.text.strip()
        # Scan for first non-empty text shape
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                first_line = shape.text_frame.text.strip().split("\n")[0]
                if len(first_line) < 80:
                    return first_line
        return f"Slide {slide_idx}"

    def _process_shapes(
        self, shapes, slide_idx: int, tracker: BreadcrumbTracker, blocks: List[ParsedBlock]
    ) -> None:
        """Recursively process shapes on a slide."""
        for shape in shapes:
            # Handle Group Shapes
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                if hasattr(shape, "shapes"):
                    self._process_shapes(shape.shapes, slide_idx, tracker, blocks)
                continue

            # Handle Tables
            if shape.has_table:
                table_md = self._table_to_markdown(shape.table)
                if table_md.strip():
                    blocks.append(
                        ParsedBlock(
                            content=table_md,
                            breadcrumb=tracker.get_path(),
                            page_number=slide_idx,
                            block_type=BlockType.TABLE,
                        )
                    )
                continue

            # Handle Pictures / Figures with Vision
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(shape, "image"):
                self._process_image_shape(shape, slide_idx, tracker, blocks)
                continue

            # Handle Text Frames
            if shape.has_text_frame:
                # If this shape is already the title, don't duplicate it if identical
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                if shape == shapes.title:
                    continue

                formatted_lines = []
                for p in shape.text_frame.paragraphs:
                    p_text = p.text.strip()
                    if not p_text:
                        continue
                    indent = "  " * (p.level if p.level else 0)
                    if p.level and p.level > 0:
                        formatted_lines.append(f"{indent}- {p_text}")
                    else:
                        formatted_lines.append(p_text)

                if formatted_lines:
                    blocks.append(
                        ParsedBlock(
                            content="\n".join(formatted_lines),
                            breadcrumb=tracker.get_path(),
                            page_number=slide_idx,
                            block_type=BlockType.PARAGRAPH,
                        )
                    )

    def _process_image_shape(
        self, shape, slide_idx: int, tracker: BreadcrumbTracker, blocks: List[ParsedBlock]
    ) -> None:
        """Extract image bytes and optionally describe via VisionEngine."""
        try:
            image = getattr(shape, "image", None)
            if not image:
                return

            image_bytes = image.blob
            content_type = getattr(image, "content_type", "image/png") or "image/png"

            # Check dimensions if available (ignore tiny icons < 64x64 or raw bytes < 100)
            if hasattr(image, "size") and image.size:
                w, h = image.size
                if w < 64 or h < 64:
                    return
            elif len(image_bytes) < 100:
                return

            # Persist image file copy if asset manager is available
            asset_id = None
            image_url = None
            if self.asset_manager:
                asset_id, image_url = self.asset_manager.save_image(
                    image_bytes=image_bytes, mime_type=content_type
                )

            desc = None
            if self.vision_engine:
                desc = self.vision_engine.describe_image(
                    image_bytes=image_bytes,
                    mime_type=content_type,
                    prompt=(
                        f"Describe the diagrams, charts, architectural schematics, or visual figures "
                        f"on this PowerPoint slide (Slide {slide_idx}). Transcribe any visible metrics, text, "
                        f"and structure."
                    ),
                )

            content_lines = []
            if image_url:
                content_lines.append(f"![Slide {slide_idx} Figure]({image_url})")
            if desc and desc.strip():
                content_lines.append(
                    f"**[Slide {slide_idx} Visual Figure / Diagram Description]:**\n{desc.strip()}"
                )
            elif not image_url:
                return

            if content_lines:
                blocks.append(
                    ParsedBlock(
                        content="\n\n".join(content_lines),
                        breadcrumb=tracker.get_path(),
                        page_number=slide_idx,
                        block_type=BlockType.FIGURE,
                        metadata={
                            "image_url": image_url,
                            "asset_id": asset_id,
                            "slide_number": slide_idx,
                            "is_figure": True,
                        },
                    )
                )
        except Exception:
            # Gracefully handle corrupted image streams without halting document parsing
            pass

    @staticmethod
    def _table_to_markdown(table) -> str:
        """Convert a pptx Table shape to a markdown table."""
        rows_data: List[List[str]] = []
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                text = cell.text.strip().replace("\n", " ")
                row_cells.append(text)
            rows_data.append(row_cells)

        if not rows_data or not any(any(c for c in row) for row in rows_data):
            return ""

        header = rows_data[0]
        # Ensure header cells are non-empty
        header_labels = [c if c else f"Col {i+1}" for i, c in enumerate(header)]
        separator = ["---"] * len(header_labels)

        lines = [
            "| " + " | ".join(header_labels) + " |",
            "| " + " | ".join(separator) + " |",
        ]

        for row in rows_data[1:]:
            # Pad if needed
            if len(row) < len(header_labels):
                row = row + [""] * (len(header_labels) - len(row))
            lines.append("| " + " | ".join(row[:len(header_labels)]) + " |")

        return "\n".join(lines)
