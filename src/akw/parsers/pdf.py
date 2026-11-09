"""PDF Document Parser using PyMuPDF (fitz)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO, List, Optional, Union

import fitz  # PyMuPDF

from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.core.exceptions import DocumentParseError
from akw.core.models import BlockType, ParsedBlock
from akw.parsers.base import BaseParser
from akw.parsers.vision import VisionEngine
from akw.storage.assets import AssetManager


class PDFParser(BaseParser):
    """Parses PDF documents with page tracking, heading detection, and breadcrumbing."""

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
                doc = fitz.open(stream=file_source, filetype="pdf")
            elif isinstance(file_source, (str, Path)):
                doc = fitz.open(str(file_source))
            else:
                data = file_source.read()
                doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:
            raise DocumentParseError(f"Failed to open PDF '{filename}': {e}") from e

        try:
            # 1. Analyze document font sizes across all pages to establish baseline body text size
            font_sizes: List[float] = []
            for page in doc:
                text_page = page.get_text("dict")
                for b in text_page.get("blocks", []):
                    if "lines" in b:
                        for line in b["lines"]:
                            for span in line.get("spans", []):
                                if span.get("text", "").strip():
                                    font_sizes.append(span.get("size", 10.0))

            body_font_size = 10.0
            if font_sizes:
                # Median font size represents standard body text
                font_sizes.sort()
                body_font_size = font_sizes[len(font_sizes) // 2]

            # Heading thresholds
            h1_threshold = body_font_size * 1.35
            h2_threshold = body_font_size * 1.15

            # 2. Iterate pages and extract blocks
            for page_idx, page in enumerate(doc):
                page_number = page_idx + 1

                # Check if tables can be extracted
                table_rects = []
                try:
                    tabs = page.find_tables()
                    for tab in tabs:
                        tab_df = tab.extract()
                        if tab_df:
                            # Format table as Markdown
                            table_md = self._table_to_markdown(tab_df)
                            if table_md.strip():
                                blocks.append(
                                    ParsedBlock(
                                        content=table_md,
                                        breadcrumb=tracker.get_path(),
                                        page_number=page_number,
                                        block_type=BlockType.TABLE,
                                    )
                                )
                                table_rects.append(fitz.Rect(tab.bbox))
                except Exception:
                    pass  # Non-fatal if table finder isn't available

                # Extract text blocks
                text_page = page.get_text("dict")
                for b in text_page.get("blocks", []):
                    if "lines" not in b:
                        continue

                    # Skip text inside extracted tables
                    block_rect = fitz.Rect(b["bbox"])
                    if any(block_rect.intersects(tr) for tr in table_rects):
                        continue

                    block_text_lines = []
                    max_span_size = 0.0

                    for line in b["lines"]:
                        line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                        for span in line.get("spans", []):
                            max_span_size = max(max_span_size, span.get("size", 0.0))
                        block_text_lines.append(line_text)

                    block_content = " ".join(block_text_lines).strip()
                    if not block_content:
                        continue

                    # Detect headings
                    if max_span_size >= h1_threshold and len(block_content) < 120:
                        tracker.update_heading(level=1, title=block_content)
                        blocks.append(
                            ParsedBlock(
                                content=block_content,
                                breadcrumb=tracker.get_path(),
                                page_number=page_number,
                                heading_level=1,
                                block_type=BlockType.HEADING,
                            )
                        )
                    elif max_span_size >= h2_threshold and len(block_content) < 160:
                        tracker.update_heading(level=2, title=block_content)
                        blocks.append(
                            ParsedBlock(
                                content=block_content,
                                breadcrumb=tracker.get_path(),
                                page_number=page_number,
                                heading_level=2,
                                block_type=BlockType.HEADING,
                            )
                        )
                    else:
                        blocks.append(
                            ParsedBlock(
                                content=block_content,
                                breadcrumb=tracker.get_path(),
                                page_number=page_number,
                                block_type=BlockType.PARAGRAPH,
                            )
                        )

                # Extract embedded figures/diagrams via VisionEngine and AssetManager
                if (self.vision_engine and getattr(self.vision_engine.config, "vision_enabled", False)) or self.asset_manager:
                    try:
                        image_list = page.get_images(full=True)
                        for img_info in image_list:
                            xref = img_info[0]
                            base_img = doc.extract_image(xref)
                            if not base_img:
                                continue
                            w = base_img.get("width", 0)
                            h = base_img.get("height", 0)
                            if w < 100 or h < 100:
                                continue
                            raw_img = base_img.get("image")
                            if not raw_img or len(raw_img) < 500:
                                continue
                            ext = base_img.get("ext", "png").lower()
                            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

                            # Persist image file copy if asset manager available
                            asset_id = None
                            image_url = None
                            if self.asset_manager:
                                asset_id, image_url = self.asset_manager.save_image(
                                    image_bytes=raw_img, mime_type=mime
                                )

                            desc = None
                            if self.vision_engine and getattr(self.vision_engine.config, "vision_enabled", False):
                                desc = self.vision_engine.describe_image(
                                    image_bytes=raw_img,
                                    mime_type=mime,
                                    prompt=(
                                        f"Analyze this figure/diagram from page {page_number} of the document. "
                                        f"Transcribe any visible labels, numbers, axis data, and explain the key findings."
                                    ),
                                )

                            content_lines = []
                            if image_url:
                                content_lines.append(f"![Page {page_number} Figure]({image_url})")
                            if desc and desc.strip():
                                content_lines.append(
                                    f"**[Page {page_number} Figure / Diagram Description]:**\n{desc.strip()}"
                                )
                            elif not image_url:
                                continue

                            if content_lines:
                                blocks.append(
                                    ParsedBlock(
                                        content="\n\n".join(content_lines),
                                        breadcrumb=tracker.get_path(),
                                        page_number=page_number,
                                        block_type=BlockType.FIGURE,
                                        metadata={
                                            "image_url": image_url,
                                            "asset_id": asset_id,
                                            "page_number": page_number,
                                            "is_figure": True,
                                        },
                                    )
                                )
                    except Exception:
                        pass

            doc.close()
        except Exception as e:
            raise DocumentParseError(f"Error parsing PDF content for '{filename}': {e}") from e

        return blocks

    @staticmethod
    def _table_to_markdown(grid: List[List[Union[str, None]]]) -> str:
        """Convert a 2D table grid to a markdown table."""
        if not grid:
            return ""
        # Clean cell text
        cleaned = [[(str(c or "").replace("\n", " ").strip()) for c in row] for row in grid]
        if not cleaned:
            return ""

        header = cleaned[0]
        rows = cleaned[1:] if len(cleaned) > 1 else []

        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]
        for row in rows:
            # Pad row if needed
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n".join(md_lines)
