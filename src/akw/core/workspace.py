"""Workspace management for discrete, isolated SQLite knowledge bases and project assets."""

from __future__ import annotations

import datetime
import json
import logging
import re
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from akw.core.config import AKWConfig

logger = logging.getLogger("akw.workspaces")


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    db_path: str
    assets_dir: str
    files_dir: str
    is_active: bool = False
    document_count: int = 0
    total_chunks: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class WorkspaceManager:
    """Manages creation, switching, and isolation of multiple project workspaces."""

    def __init__(self, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        self.workspaces_dir = Path(self.config.workspaces_dir).resolve()
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.workspaces_dir / "workspaces_registry.json"
        self._lock = threading.Lock()
        self._init_registry()

    def _init_registry(self) -> None:
        """Initialize or load workspace registry."""
        with self._lock:
            if not self.registry_file.exists():
                # Check if an existing database is at config.db_path
                existing_db = Path(self.config.db_path).resolve()
                default_assets = Path(self.config.assets_dir).resolve()
                default_files = Path(self.config.files_dir).resolve()

                registry_data = {
                    "active_id": "default",
                    "workspaces": {
                        "default": {
                            "id": "default",
                            "name": "Default Project",
                            "description": "Primary default knowledge base workspace",
                            "db_path": str(existing_db),
                            "assets_dir": str(default_assets),
                            "files_dir": str(default_files),
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                    },
                }
                self.registry_file.write_text(json.dumps(registry_data, indent=2), encoding="utf-8")

    def _read_registry_data(self) -> dict:
        try:
            return json.loads(self.registry_file.read_text(encoding="utf-8"))
        except Exception:
            return {"active_id": "default", "workspaces": {}}

    def _write_registry_data(self, data: dict) -> None:
        self.registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _slugify(name: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", name.lower()).strip()
        slug = re.sub(r"[-\s]+", "_", slug)
        return slug or "ws"

    def _get_workspace_metrics(self, db_path: str) -> tuple[int, int]:
        """Fetch document count and total chunk count from a workspace SQLite DB."""
        if not Path(db_path).exists():
            return 0, 0
        try:
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]
            conn.close()
            return doc_count, chunk_count
        except Exception:
            return 0, 0

    def list_workspaces(self) -> List[WorkspaceInfo]:
        """List all registered workspaces with real-time document metrics."""
        with self._lock:
            data = self._read_registry_data()
            active_id = data.get("active_id", "default")
            workspaces_map = data.get("workspaces", {})

            result = []
            for ws_id, ws_data in workspaces_map.items():
                docs, chunks = self._get_workspace_metrics(ws_data["db_path"])
                result.append(
                    WorkspaceInfo(
                        id=ws_id,
                        name=ws_data["name"],
                        description=ws_data.get("description", ""),
                        db_path=ws_data["db_path"],
                        assets_dir=ws_data["assets_dir"],
                        files_dir=ws_data["files_dir"],
                        is_active=(ws_id == active_id),
                        document_count=docs,
                        total_chunks=chunks,
                        created_at=ws_data.get("created_at", ""),
                    )
                )

            # Sort default first, then alphabetical by name
            return sorted(result, key=lambda w: (w.id != "default", w.name.lower()))

    def get_active_workspace(self) -> WorkspaceInfo:
        """Get the currently active workspace."""
        with self._lock:
            data = self._read_registry_data()
            active_id = data.get("active_id", "default")
            ws_data = data.get("workspaces", {}).get(active_id)

            if not ws_data:
                # Fallback to default
                active_id = "default"
                ws_data = data.get("workspaces", {}).get("default")

            docs, chunks = self._get_workspace_metrics(ws_data["db_path"])
            return WorkspaceInfo(
                id=active_id,
                name=ws_data["name"],
                description=ws_data.get("description", ""),
                db_path=ws_data["db_path"],
                assets_dir=ws_data["assets_dir"],
                files_dir=ws_data["files_dir"],
                is_active=True,
                document_count=docs,
                total_chunks=chunks,
                created_at=ws_data.get("created_at", ""),
            )

    def create_workspace(self, name: str, description: str = "") -> WorkspaceInfo:
        """Create a new project workspace with discrete SQLite DB and asset directories."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Workspace name cannot be empty")

        slug = self._slugify(clean_name)
        with self._lock:
            data = self._read_registry_data()
            workspaces = data.setdefault("workspaces", {})

            # Ensure unique id
            candidate_id = slug
            counter = 1
            while candidate_id in workspaces:
                candidate_id = f"{slug}_{counter}"
                counter += 1

            ws_folder = self.workspaces_dir / candidate_id
            ws_folder.mkdir(parents=True, exist_ok=True)
            assets_folder = ws_folder / "assets"
            assets_folder.mkdir(parents=True, exist_ok=True)
            files_folder = ws_folder / "files"
            files_folder.mkdir(parents=True, exist_ok=True)
            db_path = ws_folder / "knowledge_base.sqlite"

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            ws_entry = {
                "id": candidate_id,
                "name": clean_name,
                "description": description.strip() if description else "",
                "db_path": str(db_path),
                "assets_dir": str(assets_folder),
                "files_dir": str(files_folder),
                "created_at": now_iso,
            }

            workspaces[candidate_id] = ws_entry
            # Automatically activate newly created workspace
            data["active_id"] = candidate_id
            self._write_registry_data(data)

            return WorkspaceInfo(
                id=candidate_id,
                name=clean_name,
                description=description.strip() if description else "",
                db_path=str(db_path),
                assets_dir=str(assets_folder),
                files_dir=str(files_folder),
                is_active=True,
                document_count=0,
                total_chunks=0,
                created_at=now_iso,
            )

    def switch_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """Switch active workspace."""
        with self._lock:
            data = self._read_registry_data()
            workspaces = data.get("workspaces", {})
            if workspace_id not in workspaces:
                raise KeyError(f"Workspace '{workspace_id}' does not exist")

            data["active_id"] = workspace_id
            self._write_registry_data(data)

            ws_data = workspaces[workspace_id]
            docs, chunks = self._get_workspace_metrics(ws_data["db_path"])
            return WorkspaceInfo(
                id=workspace_id,
                name=ws_data["name"],
                description=ws_data.get("description", ""),
                db_path=ws_data["db_path"],
                assets_dir=ws_data["assets_dir"],
                files_dir=ws_data["files_dir"],
                is_active=True,
                document_count=docs,
                total_chunks=chunks,
                created_at=ws_data.get("created_at", ""),
            )

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace. Default workspace cannot be deleted."""
        if workspace_id == "default":
            raise ValueError("The 'default' workspace cannot be deleted.")

        with self._lock:
            data = self._read_registry_data()
            workspaces = data.get("workspaces", {})
            if workspace_id not in workspaces:
                return False

            del workspaces[workspace_id]
            if data.get("active_id") == workspace_id:
                data["active_id"] = "default"

            self._write_registry_data(data)
            return True

