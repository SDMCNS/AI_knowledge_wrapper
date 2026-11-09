"""Tests for document parsers, breadcrumbs, and windowed chunker."""

import pytest
from akw.chunking.breadcrumb import BreadcrumbTracker
from akw.chunking.chunker import WindowedSemanticChunker
from akw.core.models import BlockType
from akw.parsers.factory import ParserFactory
from akw.parsers.html import HTMLParser
from akw.parsers.markdown import MarkdownParser
from akw.parsers.text import TextParser


def test_breadcrumb_tracker():
    tracker = BreadcrumbTracker("System_Architecture.pdf")
    assert tracker.get_display() == "System_Architecture.pdf"

    tracker.update_heading(1, "Section 1: Overview")
    assert tracker.get_display() == "System_Architecture.pdf > Section 1: Overview"

    tracker.update_heading(2, "Storage Layer")
    assert tracker.get_display() == "System_Architecture.pdf > Section 1: Overview > Storage Layer"

    # Sibling update at level 2
    tracker.update_heading(2, "Caching Layer")
    assert tracker.get_display() == "System_Architecture.pdf > Section 1: Overview > Caching Layer"

    # Higher level update replaces level 1 and 2
    tracker.update_heading(1, "Section 2: Security")
    assert tracker.get_display() == "System_Architecture.pdf > Section 2: Security"


def test_markdown_parser():
    md_content = """# Title of Doc

This is an introduction paragraph.

## Subheading A

Details about feature A.

```python
def hello():
    return "world"
```

## Subheading B

More details about feature B.
"""
    parser = MarkdownParser()
    blocks = parser.parse(md_content.encode("utf-8"), "test_doc.md")

    assert len(blocks) >= 5
    headings = [b for b in blocks if b.block_type == BlockType.HEADING]
    assert len(headings) == 3
    assert headings[0].content == "Title of Doc"
    assert headings[1].content == "Subheading A"

    code_blocks = [b for b in blocks if b.block_type == BlockType.CODE]
    assert len(code_blocks) == 1
    assert "def hello():" in code_blocks[0].content
    assert code_blocks[0].breadcrumb == ["test_doc.md", "Title of Doc", "Subheading A"]


def test_html_parser():
    html_content = """
    <html>
      <body>
        <h1>Knowledge Base API</h1>
        <p>This is a guide to the local RAG system.</p>
        <h2>Endpoints</h2>
        <table>
          <tr><th>Method</th><th>Path</th></tr>
          <tr><td>POST</td><td>/api/search</td></tr>
        </table>
      </body>
    </html>
    """
    parser = HTMLParser()
    blocks = parser.parse(html_content.encode("utf-8"), "api_guide.html")

    assert any(b.block_type == BlockType.HEADING and "Knowledge Base API" in b.content for b in blocks)
    assert any(b.block_type == BlockType.TABLE for b in blocks)


def test_windowed_chunker():
    parser = MarkdownParser()
    md_sample = """# Database Operations

## Configuration

To configure connection pooling, specify pool_size=10 and max_overflow=20 in the database settings file.
Ensure that timeouts are set to 30 seconds to prevent thread starvation under heavy load.

## Transactions

Transactions must be wrapped in atomic blocks. If an unhandled exception occurs, the transaction automatically rolls back.
"""
    blocks = parser.parse(md_sample.encode("utf-8"), "db.md")
    chunker = WindowedSemanticChunker(target_chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk_blocks(blocks, document_id="doc_123")

    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.document_id == "doc_123"
        assert len(c.breadcrumb_display) > 0

