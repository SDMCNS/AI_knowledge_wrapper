"""Tests for FastAPI backend routes."""

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_system_status(client):
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "embedding_model" in data


def test_list_models(client):
    resp = client.get("/api/chat/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 2
    model_ids = [m["id"] for m in models]
    assert "gemini-3.8-flash" in model_ids


def test_session_lifecycle(client):
    # 1. Create session
    create_resp = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat", "model_provider": "gemini", "model_name": "gemini-3.8-flash"},
    )
    assert create_resp.status_code == 200
    sess = create_resp.json()
    sess_id = sess["id"]
    assert sess_id.startswith("sess_")

    # 2. Get session
    get_resp = client.get(f"/api/chat/sessions/{sess_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["session"]["id"] == sess_id
    assert isinstance(detail["messages"], list)

    # 3. Delete session
    del_resp = client.delete(f"/api/chat/sessions/{sess_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_document_download(client):
    """Verify uploaded documents can be downloaded with identical content."""
    sample_content = b"# Architecture Plan\n\nOriginal file content for user download verification."
    upload_resp = client.post(
        "/api/kb/upload",
        files=[("files", ("system_plan.md", sample_content, "text/markdown"))],
    )
    assert upload_resp.status_code == 200
    docs = upload_resp.json()
    assert len(docs) == 1
    doc_id = docs[0]["id"]

    download_resp = client.get(f"/api/kb/documents/{doc_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content == sample_content
    assert "system_plan.md" in download_resp.headers.get("content-disposition", "")

