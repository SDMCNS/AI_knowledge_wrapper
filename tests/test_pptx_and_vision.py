"""Tests for PPTX parsing, vision-assisted diagram extraction, and system settings."""

from __future__ import annotations

import io
from pptx import Presentation
from pptx.util import Inches, Pt
from PIL import Image

from akw.core.config import AKWConfig
from akw.parsers.factory import ParserFactory
from akw.parsers.pptx_parser import PPTXParser
from akw.parsers.vision import VisionEngine
from server.app import app
from fastapi.testclient import TestClient


def create_sample_pptx() -> bytes:
    """Generate a realistic test PPTX in-memory with text, table, notes, and an image."""
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Title, bullets, and presenter notes
    slide1 = prs.slides.add_slide(blank_layout)
    tx_box = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2))
    tf = tx_box.text_frame
    p0 = tf.paragraphs[0]
    p0.text = "Quantum Storage Engine Architecture"
    p0.font.size = Pt(24)

    p1 = tf.add_paragraph()
    p1.text = "High-performance hybrid vector and BM25 index."
    p1.level = 1

    p2 = tf.add_paragraph()
    p2.text = "Guarantees contiguous +/- 2 neighbor expansion."
    p2.level = 1

    # Notes for slide 1
    notes_slide = slide1.notes_slide
    notes_slide.notes_text_frame.text = "Review this slide with senior infrastructure architects."

    # Slide 2: Table
    slide2 = prs.slides.add_slide(blank_layout)
    title_box = slide2.shapes.add_textbox(Inches(1), Inches(0.5), Inches(6), Inches(1))
    title_box.text_frame.text = "Benchmark Results"

    table_shape = slide2.shapes.add_table(rows=3, cols=2, left=Inches(1), top=Inches(2), width=Inches(6), height=Inches(2))
    table = table_shape.table
    table.cell(0, 0).text = "Benchmark"
    table.cell(0, 1).text = "Latency"
    table.cell(1, 0).text = "Dense Vector Search"
    table.cell(1, 1).text = "4.2 ms"
    table.cell(2, 0).text = "BM25 FTS5 Match"
    table.cell(2, 1).text = "1.1 ms"

    # Slide 3: Image with figure
    slide3 = prs.slides.add_slide(blank_layout)
    s3_title = slide3.shapes.add_textbox(Inches(1), Inches(0.5), Inches(6), Inches(1))
    s3_title.text_frame.text = "System Topology"

    # Create a 200x200 test PNG image
    img = Image.new("RGB", (200, 200), color=(73, 109, 137))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    slide3.shapes.add_picture(io.BytesIO(img_bytes), Inches(1), Inches(2), width=Inches(4), height=Inches(4))

    out_stream = io.BytesIO()
    prs.save(out_stream)
    return out_stream.getvalue()


class MockVisionEngine(VisionEngine):
    """Mock Vision Engine returning predictable descriptions."""
    def describe_image(self, image_bytes: bytes, mime_type: str = "image/png", prompt: str = None):
        return "Schematic topology showing React frontend communicating with FastAPI and SQLite storage."


def test_pptx_parser_extraction_and_vision():
    """Verify PPTX parsing extracts slides, titles, tables, notes, and visual descriptions."""
    pptx_bytes = create_sample_pptx()
    mock_vision = MockVisionEngine(config=AKWConfig(vision_enabled=True))

    parser = ParserFactory.get_parser("presentation.pptx", vision_engine=mock_vision)
    assert isinstance(parser, PPTXParser)

    blocks = parser.parse(pptx_bytes, filename="presentation.pptx")
    assert len(blocks) >= 4

    content_dump = "\n".join(b.content for b in blocks)
    assert "Quantum Storage Engine Architecture" in content_dump
    assert "High-performance hybrid vector and BM25 index." in content_dump
    assert "Review this slide with senior infrastructure architects." in content_dump
    assert "| Benchmark | Latency |" in content_dump
    assert "Dense Vector Search" in content_dump
    assert "Schematic topology showing React frontend" in content_dump


def test_system_settings_api():
    """Test GET and POST /api/system/settings endpoints."""
    client = TestClient(app)

    # 1. Fetch current settings
    resp = client.get("/api/system/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "helper_llm_model" in data
    assert "vision_llm_model" in data
    assert data["vision_enabled"] is True

    # 2. Update settings dynamically
    update_payload = {
        "helper_llm_model": "qwen/qwen3.5-9b",
        "vision_llm_model": "qwen/qwen3-vl-8b",
        "vision_timeout_seconds": 30,
    }
    resp_update = client.post("/api/system/settings", json=update_payload)
    assert resp_update.status_code == 200
    updated_data = resp_update.json()
    assert updated_data["helper_llm_model"] == "qwen/qwen3.5-9b"
    assert updated_data["vision_llm_model"] == "qwen/qwen3-vl-8b"
    assert updated_data["vision_timeout_seconds"] == 30

