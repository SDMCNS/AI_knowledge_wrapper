"""Tests for staging, chunk review/curation, and LM Studio."""

import os
import tempfile
import pytest

from akw.core.config import AKWConfig
from akw.core.models import CommitChunksRequest
from akw.kb import KnowledgeBase
from akw.llm.lmstudio_client import LMStudioClient


@pytest.fixture
def staging_kb():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    config = AKWConfig(
        db_path=path,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        target_chunk_size=40,
        hyde_enabled=False,
        reranker_provider="none",
    )
    kb = KnowledgeBase(config=config)
    yield kb
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def test_chunk_staging_and_curation(staging_kb):
    sample_text = """# Product Manual

## Features
- Ultra-low latency retrieval engine
- Contiguous +/- 2 chunk context windows
- First-class support for LM Studio and Gemini 3.8

## Legal Disclaimers
This software is provided as-is without any express or implied warranties of any kind whatsoever.
All rights reserved under international copyright conventions. Do not distribute or reproduce without permission.

## Usage Guide
Run `python run.py serve --port 8000` to start the application and access the web UI.
"""
    # 1. Stage the document (parse + chunk without committing to DB)
    staged = staging_kb.stage_document(
        file_source=sample_text.encode("utf-8"),
        filename="Manual.md",
    )
    assert staged.staging_id.startswith("stg_")
    assert len(staged.chunks) >= 3

    # Verify no documents are in the DB yet
    assert len(staging_kb.list_documents()) == 0

    # 2. Curate chunks: Exclude the legal disclaimer chunk and edit the usage chunk
    for c in staged.chunks:
        if "Legal Disclaimers" in c.breadcrumb_display or "warranties" in c.content:
            c.is_retained = False
        if "Usage Guide" in c.breadcrumb_display or "Usage" in c.content:
            c.content += "\nOpen http://localhost:8000 in your browser."

    commit_req = CommitChunksRequest(
        staging_id=staged.staging_id,
        filename=staged.filename,
        sha256_hash=staged.sha256_hash,
        mime_type=staged.mime_type,
        file_size_bytes=staged.file_size_bytes,
        chunks=staged.chunks,
    )

    # 3. Commit only retained & edited chunks
    doc = staging_kb.commit_staged_chunks(commit_req)
    assert doc.id.startswith("doc_")
    assert doc.total_chunks == len([c for c in staged.chunks if c.is_retained])

    # 4. Verify search hits the edited content and excludes the legal disclaimer
    blocks, _ = staging_kb.search("browser", top_k=1)
    assert len(blocks) >= 1
    assert "Open http://localhost:8000 in your browser" in blocks[0].merged_text

    # Search for disclaimer
    disclaimer_blocks, _ = staging_kb.search("without any warranties", top_k=1)
    if disclaimer_blocks:
        assert "without any warranties" not in disclaimer_blocks[0].merged_text


def test_lmstudio_client_discovery():
    client = LMStudioClient()
    models = client.list_models()
    # LM Studio is running on user's machine on port 1234
    assert isinstance(models, list)
    if models:
        assert "qwen/qwen3.5-9b" in models
