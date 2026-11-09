"""Integration tests for KnowledgeBase facade."""

import os
import tempfile
import pytest

from akw.core.config import AKWConfig
from akw.kb import KnowledgeBase


@pytest.fixture
def temp_kb():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    # Configure lightweight settings for fast tests (disable HyDE and external calls)
    config = AKWConfig(
        db_path=path,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        target_chunk_size=50,
        chunk_overlap=10,
        hyde_enabled=False,
        reranker_provider="none",  # Fast RRF ranking for unit tests
        window_expansion=2,
    )
    kb = KnowledgeBase(config=config)
    yield kb
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


def test_kb_add_document_and_search(temp_kb):
    doc_content = """# Company Guidelines

## Section 1: Security Practices

All developers must enable two-factor authentication (2FA) across all administrative accounts.
Passkeys or hardware security keys are strongly recommended for root infrastructure access.

## Section 2: Data Retention

Customer logs must be retained for at least 90 days in cold storage before secure purging.
Audit logs related to financial records must be archived for 7 years to comply with regulatory standards.

## Section 3: Incident Response

If a suspected security breach occurs, notify the incident commander within 15 minutes.
Do not modify firewall rules without senior engineering approval.
"""
    doc = temp_kb.add_document(
        file_source=doc_content.encode("utf-8"),
        filename="Security_Guidelines.md",
        metadata={"category": "Policy"},
    )

    assert doc.id.startswith("doc_")
    assert doc.total_chunks >= 3

    # Test duplicate detection
    doc_dup = temp_kb.add_document(
        file_source=doc_content.encode("utf-8"),
        filename="Security_Guidelines.md",
    )
    assert doc_dup.id == doc.id

    # Test search
    blocks, citations = temp_kb.search("two-factor authentication 2FA", top_k=1, expand_window=2)
    assert len(blocks) >= 1
    assert len(citations) >= 1

    top_block = blocks[0]
    assert top_block.citation_id == "REF-1"
    assert "Security_Guidelines.md" in top_block.document_name
    assert "2FA" in top_block.merged_text
    assert top_block.relevance_score > 0
