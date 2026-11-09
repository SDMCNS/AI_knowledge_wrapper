"""Tests for SQLite Storage with FTS5 BM25 and Vector Search."""

import os
import tempfile
import numpy as np
import pytest

from akw.core.models import Chunk, Document
from akw.storage.sqlite_db import SQLiteStorage


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    storage = SQLiteStorage(db_path=path)
    yield storage
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def test_document_and_chunk_crud(temp_db):
    doc = Document(
        id="doc_1",
        filename="manual.pdf",
        sha256_hash="abc123hash",
        mime_type="application/pdf",
        file_size_bytes=1024,
        total_chunks=3,
    )
    temp_db.insert_document(doc)

    fetched = temp_db.get_document("doc_1")
    assert fetched is not None
    assert fetched.filename == "manual.pdf"

    chunks = [
        Chunk(
            id=f"chk_{i}",
            document_id="doc_1",
            chunk_index=i,
            content=f"This is chunk {i} describing database configuration and connection parameters.",
            breadcrumb_display="Manual > Database",
            breadcrumb_path=["Manual", "Database"],
            token_count=15,
        )
        for i in range(5)
    ]
    temp_db.insert_chunks(chunks)

    # Test neighbor chunks (+/- 2 chunks)
    neighbors = temp_db.get_neighbor_chunks("doc_1", start_index=1, end_index=3)
    assert len(neighbors) == 3
    assert [c.chunk_index for c in neighbors] == [1, 2, 3]

    # Test batch chunk deletion
    deleted = temp_db.delete_chunks(["chk_1", "chk_2"])
    assert deleted == 2
    remaining = temp_db.get_chunks_for_document("doc_1")
    assert len(remaining) == 3
    assert [c.id for c in remaining] == ["chk_0", "chk_3", "chk_4"]
    # Verify document total_chunks updated
    assert temp_db.get_document("doc_1").total_chunks == 3


def test_fts5_bm25_search(temp_db):
    doc = Document(
        id="doc_search",
        filename="network.md",
        sha256_hash="hash_net",
        mime_type="text/markdown",
        file_size_bytes=500,
    )
    temp_db.insert_document(doc)

    chunks = [
        Chunk(
            id="chk_net_1",
            document_id="doc_search",
            chunk_index=0,
            content="Kubernetes cluster ingress and egress routing instructions.",
            breadcrumb_display="Network > Ingress",
            token_count=10,
        ),
        Chunk(
            id="chk_net_2",
            document_id="doc_search",
            chunk_index=1,
            content="PostgreSQL database replication and failover architecture.",
            breadcrumb_display="Network > Database",
            token_count=10,
        ),
    ]
    temp_db.insert_chunks(chunks)

    results = temp_db.search_bm25("Kubernetes ingress", limit=5)
    assert len(results) >= 1
    hit_chunk, score, rank = results[0]
    assert hit_chunk.id == "chk_net_1"
    assert rank == 1


def test_vector_similarity_search(temp_db):
    # Store dummy 4-dimensional embeddings
    embeddings = {
        "chk_v1": np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        "chk_v2": np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        "chk_v3": np.array([0.8, 0.2, 0.0, 0.0], dtype=np.float32),
    }

    doc = Document(
        id="doc_v",
        filename="vec.txt",
        sha256_hash="hash_vec",
        mime_type="text/plain",
        file_size_bytes=100,
    )
    temp_db.insert_document(doc)

    chunks = [
        Chunk(
            id=cid,
            document_id="doc_v",
            chunk_index=idx,
            content=f"Vector chunk {cid}",
            breadcrumb_display="Vector > Test",
            token_count=5,
        )
        for idx, cid in enumerate(embeddings.keys())
    ]
    temp_db.insert_chunks(chunks)
    temp_db.store_embeddings(embeddings, model_name="test_model")

    # Search with a vector close to chk_v1
    query_vec = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
    hits = temp_db.search_vectors(query_vec, model_name="test_model", limit=2)

    assert len(hits) == 2
    top_chunk, score, rank = hits[0]
    assert top_chunk.id in ("chk_v1", "chk_v3")
    assert score > 0.8

