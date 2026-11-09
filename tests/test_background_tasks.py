"""Tests for background document parsing tasks and progress ticker."""

import io
import time
import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.tasks import task_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_background_stage_task(client):
    file_content = b"# Background Parsing Test\n\n## Section 1\nThis document is parsed asynchronously."
    
    # 1. Start background stage task
    response = client.post(
        "/api/kb/tasks/stage",
        files={"file": ("test_async.md", io.BytesIO(file_content), "text/markdown")},
    )
    assert response.status_code == 200
    task_data = response.json()
    task_id = task_data["id"]
    assert task_id.startswith("tsk_")
    assert task_data["filename"] == "test_async.md"

    # 2. Poll until completed (should take <3 seconds)
    max_retries = 30
    completed = False
    for _ in range(max_retries):
        poll_resp = client.get(f"/api/kb/tasks/{task_id}")
        assert poll_resp.status_code == 200
        data = poll_resp.json()
        if data["status"] == "completed":
            completed = True
            assert data["progress"] == 100
            assert "result" in data and data["result"] is not None
            assert len(data["result"]["chunks"]) >= 1
            break
        elif data["status"] == "failed":
            pytest.fail(f"Task failed: {data.get('error')}")
        time.sleep(0.1)

    assert completed, "Background task did not complete in time"

    # 3. Verify task listed in /api/kb/tasks
    list_resp = client.get("/api/kb/tasks")
    assert list_resp.status_code == 200
    all_tasks = list_resp.json()
    assert any(t["id"] == task_id for t in all_tasks)

