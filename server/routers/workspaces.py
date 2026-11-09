"""API endpoints for Workspace management and knowledge base swapping."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from akw.core.workspace import WorkspaceCreateRequest, WorkspaceInfo, WorkspaceManager
from akw.examples.manager import ExampleDatasetInfo, ExampleManager
from server.dependencies import (
    clear_knowledge_base_cache,
    get_workspace_manager,
)

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


@router.get("", response_model=List[WorkspaceInfo])
def list_workspaces(wm: WorkspaceManager = Depends(get_workspace_manager)):
    """List all registered project workspaces with document and chunk metrics."""
    return wm.list_workspaces()


@router.get("/active", response_model=WorkspaceInfo)
def get_active_workspace(wm: WorkspaceManager = Depends(get_workspace_manager)):
    """Retrieve the currently active workspace."""
    return wm.get_active_workspace()


@router.post("", response_model=WorkspaceInfo)
def create_workspace(
    req: WorkspaceCreateRequest,
    wm: WorkspaceManager = Depends(get_workspace_manager),
):
    """Create a new project workspace with discrete SQLite DB and asset directories."""
    try:
        new_ws = wm.create_workspace(name=req.name, description=req.description or "")
        clear_knowledge_base_cache()
        return new_ws
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {str(e)}")


@router.post("/{workspace_id}/switch", response_model=WorkspaceInfo)
def switch_active_workspace(
    workspace_id: str,
    wm: WorkspaceManager = Depends(get_workspace_manager),
):
    """Switch active knowledge base workspace."""
    try:
        active_ws = wm.switch_workspace(workspace_id)
        clear_knowledge_base_cache()
        return active_ws
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch workspace: {str(e)}")


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    wm: WorkspaceManager = Depends(get_workspace_manager),
):
    """Delete a workspace. Note that 'default' cannot be deleted."""
    try:
        success = wm.delete_workspace(workspace_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")
        clear_knowledge_base_cache(workspace_id)
        return {"success": True, "deleted_id": workspace_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Example Knowledge Bases Endpoints ---


@router.get("/examples/list", response_model=List[ExampleDatasetInfo])
def list_example_datasets():
    """List all available pre-packaged example knowledge bases."""
    mgr = ExampleManager()
    return mgr.list_available_examples()


@router.post("/examples/{example_id}/load", response_model=WorkspaceInfo)
def load_example_workspace(
    example_id: str,
    reset: bool = Query(False, description="Whether to overwrite if already exists"),
):
    """Load or reset a specific example knowledge base into workspaces."""
    mgr = ExampleManager()
    try:
        ws = mgr.load_example(example_id, reset=reset)
        clear_knowledge_base_cache()
        return ws
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed loading example: {str(e)}")


@router.post("/examples/reset-all", response_model=List[WorkspaceInfo])
def reset_all_examples():
    """Wipe all workspaces and reload fresh example datasets."""
    mgr = ExampleManager()
    try:
        workspaces = mgr.reset_all()
        clear_knowledge_base_cache()
        return workspaces
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed resetting examples: {str(e)}")
