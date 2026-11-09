"""Tests for graphical asset extraction, linking, and storage across PDF, DOCX, and PPTX."""

from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import docx
from pptx import Presentation
from pptx.util import Inches
from fastapi.testclient import TestClient

from akw.chunking.chunker import WindowedSemanticChunker
from akw.core.config import AKWConfig
from akw.core.models import BlockType
from akw.parsers.docx import DocxParser
from akw.parsers.pdf import PDFParser
from akw.parsers.pptx_parser import PPTXParser
from akw.parsers.vision import VisionEngine
from akw.storage.assets import AssetManager
from server.app import app


class DummyVisionEngine(VisionEngine):
    def describe_image(self, image_bytes: bytes, mime_type: str = "image/png", prompt: str = None):
        return "Neural architecture schematic showing input, hidden layers, and attention matrix."


def create_test_image_bytes(color=(120, 180, 220), size=(180, 180)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_docx_image_extraction_and_linking():
    """Verify DOCX parser extracts images, saves them to AssetManager, and links them."""
    tmp_dir = tempfile.mkdtemp()
    try:
        asset_mgr = AssetManager(assets_dir=tmp_dir)
        vision_engine = DummyVisionEngine(config=AKWConfig(vision_enabled=True))
        parser = DocxParser(vision_engine=vision_engine, asset_manager=asset_mgr)

        # Build in-memory DOCX with an image
        doc = docx.Document()
        doc.add_heading("Deep Learning Overview", level=1)
        doc.add_paragraph("Here is the model topology diagram:")
        img_bytes = create_test_image_bytes(color=(200, 50, 50))
        doc.add_picture(io.BytesIO(img_bytes))
        doc.add_paragraph("This concludes the architecture section.")

        doc_buf = io.BytesIO()
        doc.save(doc_buf)
        docx_bytes = doc_buf.getvalue()

        blocks = parser.parse(docx_bytes, filename="model_spec.docx")
        figure_blocks = [b for b in blocks if b.block_type == BlockType.FIGURE]
        assert len(figure_blocks) >= 1

        fig = figure_blocks[0]
        assert "image_url" in fig.metadata
        assert fig.metadata["image_url"].startswith("/api/assets/")
        assert "![Document Figure]" in fig.content
        assert "Neural architecture schematic" in fig.content

        # Verify asset file exists on disk
        asset_id = fig.metadata["asset_id"]
        saved_file = asset_mgr.get_asset_path(asset_id)
        assert saved_file is not None and saved_file.exists()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_pdf_image_extraction_and_linking():
    """Verify PDF parser extracts images, saves them to AssetManager, and links them."""
    tmp_dir = tempfile.mkdtemp()
    try:
        asset_mgr = AssetManager(assets_dir=tmp_dir)
        vision_engine = DummyVisionEngine(config=AKWConfig(vision_enabled=True))
        parser = PDFParser(vision_engine=vision_engine, asset_manager=asset_mgr)

        # Build in-memory PDF with an embedded image
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        page.insert_text((50, 50), "PDF Figure Test Section", fontsize=16)

        img_bytes = create_test_image_bytes(color=(50, 150, 50), size=(200, 200))
        rect = fitz.Rect(50, 100, 250, 300)
        page.insert_image(rect, stream=img_bytes)

        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        blocks = parser.parse(pdf_bytes, filename="report.pdf")
        figure_blocks = [b for b in blocks if b.block_type == BlockType.FIGURE]
        assert len(figure_blocks) >= 1

        fig = figure_blocks[0]
        assert "image_url" in fig.metadata
        assert fig.metadata["image_url"].startswith("/api/assets/")
        assert "![Page 1 Figure]" in fig.content
        assert "Neural architecture schematic" in fig.content
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_pptx_image_extraction_and_linking():
    """Verify PPTX parser extracts slide pictures, saves them, and links them."""
    tmp_dir = tempfile.mkdtemp()
    try:
        asset_mgr = AssetManager(assets_dir=tmp_dir)
        vision_engine = DummyVisionEngine(config=AKWConfig(vision_enabled=True))
        parser = PPTXParser(vision_engine=vision_engine, asset_manager=asset_mgr)

        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        img_bytes = create_test_image_bytes(color=(100, 50, 200), size=(220, 220))
        slide.shapes.add_picture(io.BytesIO(img_bytes), Inches(1), Inches(1), width=Inches(3), height=Inches(3))

        pptx_buf = io.BytesIO()
        prs.save(pptx_buf)
        pptx_bytes = pptx_buf.getvalue()

        blocks = parser.parse(pptx_bytes, filename="slides.pptx")
        figure_blocks = [b for b in blocks if b.block_type == BlockType.FIGURE]
        assert len(figure_blocks) >= 1

        fig = figure_blocks[0]
        assert "image_url" in fig.metadata
        assert "![Slide 1 Figure]" in fig.content
        assert "Neural architecture schematic" in fig.content
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_figure_chunking_preserves_metadata():
    """Verify WindowedSemanticChunker isolates figure blocks and carries metadata into Chunk."""
    chunker = WindowedSemanticChunker(target_chunk_size=100)
    fig_block = BlockType.FIGURE
    from akw.core.models import ParsedBlock
    blocks = [
        ParsedBlock(content="Paragraph before the diagram.", breadcrumb=["Doc", "Sec 1"]),
        ParsedBlock(
            content="![Slide 2 Figure](/api/assets/ast_123.png)\n\n**[Slide 2 Diagram]:** High level arch",
            breadcrumb=["Doc", "Sec 1"],
            block_type=BlockType.FIGURE,
            metadata={"image_url": "/api/assets/ast_123.png", "asset_id": "ast_123", "is_figure": True},
        ),
        ParsedBlock(content="Paragraph after the diagram.", breadcrumb=["Doc", "Sec 1"]),
    ]

    chunks = chunker.chunk_blocks(blocks, document_id="doc_test")
    assert len(chunks) == 3
    fig_chunk = chunks[1]
    assert fig_chunk.metadata.get("is_figure") is True
    assert fig_chunk.metadata.get("image_url") == "/api/assets/ast_123.png"
    assert "/api/assets/ast_123.png" in fig_chunk.content


def test_asset_serving_endpoint():
    """Test FastAPI asset endpoint /api/assets/{filename}."""
    client = TestClient(app)
    # Save a test asset using the app's knowledge base asset manager
    from server.dependencies import get_knowledge_base
    kb = get_knowledge_base()
    img_bytes = create_test_image_bytes(color=(40, 80, 160))
    asset_id, url = kb.asset_manager.save_image(img_bytes, mime_type="image/png")

    filename = url.replace("/api/assets/", "")
    resp = client.get(f"/api/assets/{filename}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) == len(img_bytes)

