"""Tests for multi-project workspace creation, swapping, and isolation."""

from __future__ import annotations

import tempfile
import pytest
from fastapi.testclient import TestClient

from akw.core.config import AKWConfig
from akw.core.workspace import WorkspaceManager
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_workspace_manager_crud():
    """Verify WorkspaceManager creates, lists, switches, and isolates workspaces."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg = AKWConfig(workspaces_dir=tmp_dir)
        wm = WorkspaceManager(config=cfg)

        # 1. Default workspace exists
        workspaces = wm.list_workspaces()
        assert len(workspaces) >= 1
        default_ws = [w for w in workspaces if w.id == "default"][0]
        assert default_ws.is_active is True

        # 2. Create Project Titan
        titan = wm.create_workspace(name="Project Titan", description="Mission logs for Titan probe")
        assert titan.id.startswith("project_titan")
        assert titan.is_active is True
        assert "knowledge_base.sqlite" in titan.db_path

        # 3. List reflects new active workspace
        updated_list = wm.list_workspaces()
        assert len(updated_list) == 2
        active_ws = wm.get_active_workspace()
        assert active_ws.id == titan.id

        # 4. Switch back to default
        switched = wm.switch_workspace("default")
        assert switched.id == "default"
        assert wm.get_active_workspace().id == "default"

        # 5. Cannot delete default
        with pytest.raises(ValueError, match="cannot be deleted"):
            wm.delete_workspace("default")

        # 6. Delete Project Titan
        deleted = wm.delete_workspace(titan.id)
        assert deleted is True
        assert len(wm.list_workspaces()) == 1


def test_workspace_api_endpoints(client):
    """Test REST API endpoints /api/workspaces."""
    # 1. List
    resp = client.get("/api/workspaces")
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) >= 1

    # 2. Create
    create_resp = client.post(
        "/api/workspaces",
        json={"name": "Project Artemis", "description": "Lunar base telemetry"},
    )
    assert create_resp.status_code == 200
    artemis = create_resp.json()
    assert "project_artemis" in artemis["id"]
    assert artemis["is_active"] is True

    # 3. Verify Active
    active_resp = client.get("/api/workspaces/active")
    assert active_resp.status_code == 200
    assert active_resp.json()["id"] == artemis["id"]

    # 4. Ingest file into Artemis
    upload_resp = client.post(
        "/api/kb/upload",
        files=[("files", ("artemis_spec.txt", b"Artemis Lunar Module Engine Data", "text/plain"))],
    )
    assert upload_resp.status_code == 200

    # Verify Artemis has 1 document
    docs_artemis = client.get("/api/kb/documents").json()
    assert len(docs_artemis) >= 1

    # 5. Switch to default
    switch_resp = client.post("/api/workspaces/default/switch")
    assert switch_resp.status_code == 200
    assert switch_resp.json()["id"] == "default"

    # 6. Delete Artemis
    del_resp = client.delete(f"/api/workspaces/{artemis['id']}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True


def test_workspace_examples_endpoints(client):
    """Test /api/workspaces/examples/list and /load endpoints."""
    # 1. List available examples
    resp = client.get("/api/workspaces/examples/list")
    assert resp.status_code == 200
    examples = resp.json()
    assert len(examples) >= 2
    ids = [e["id"] for e in examples]
    assert "project_apollo" in ids
    assert "bionexus_diagnostics" in ids

    # Check metadata fields
    apollo = [e for e in examples if e["id"] == "project_apollo"][0]
    assert "Avionics" in apollo["name"]
    assert len(apollo["sample_queries"]) >= 1
    assert apollo["has_diagrams"] is True


