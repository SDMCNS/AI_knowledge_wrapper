"""Example Knowledge Base manager for loading, resetting, and exploring pre-configured datasets."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from akw.core.config import AKWConfig
from akw.core.workspace import WorkspaceInfo, WorkspaceManager
from akw.kb import KnowledgeBase

logger = logging.getLogger("akw.examples")


class ExampleDatasetInfo(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    sample_queries: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    has_diagrams: bool = True


class ExampleManager:
    """Manages discoverable example knowledge bases and automated hydration into workspaces."""

    def __init__(self, examples_dir: Optional[Path] = None, config: Optional[AKWConfig] = None):
        self.config = config or AKWConfig()
        if examples_dir:
            self.examples_dir = Path(examples_dir).resolve()
        else:
            # Default to examples/datasets relative to project root or akw package
            root_candidate = Path("examples/datasets").resolve()
            if root_candidate.exists():
                self.examples_dir = root_candidate
            else:
                pkg_candidate = Path(__file__).parent.parent.parent.parent / "examples" / "datasets"
                self.examples_dir = pkg_candidate.resolve()

        self.workspace_manager = WorkspaceManager(config=self.config)

    def list_available_examples(self) -> List[ExampleDatasetInfo]:
        """List metadata for all available bundled example knowledge bases."""
        if not self.examples_dir.exists():
            return []

        results: List[ExampleDatasetInfo] = []
        for d in self.examples_dir.iterdir():
            if d.is_dir() and (d / "metadata.json").exists():
                try:
                    data = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
                    docs_dir = d / "documents"
                    doc_files = [f.name for f in docs_dir.iterdir() if f.is_file()] if docs_dir.exists() else []
                    results.append(
                        ExampleDatasetInfo(
                            id=data.get("id", d.name),
                            name=data.get("name", d.name),
                            description=data.get("description", ""),
                            tags=data.get("tags", []),
                            sample_queries=data.get("sample_queries", []),
                            documents=doc_files,
                            has_diagrams=(d / "assets").exists(),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not read metadata for example {d.name}: {e}")

        return sorted(results, key=lambda x: x.name)

    def load_example(self, example_id: str, reset: bool = False) -> WorkspaceInfo:
        """Hydrate an example dataset into a discrete SQLite workspace."""
        pkg_dir = self.examples_dir / example_id
        if not pkg_dir.exists() or not (pkg_dir / "metadata.json").exists():
            raise FileNotFoundError(f"Example dataset '{example_id}' not found at {pkg_dir}")

        meta = json.loads((pkg_dir / "metadata.json").read_text(encoding="utf-8"))
        ws_name = meta.get("name", example_id)
        ws_desc = meta.get("description", "")

        # Check existing workspaces
        existing = {w.id: w for w in self.workspace_manager.list_workspaces()}
        candidate_slug = self.workspace_manager._slugify(ws_name)

        target_ws_id = None
        for eid, w in existing.items():
            if eid == candidate_slug or w.name.lower() == ws_name.lower():
                target_ws_id = eid
                break

        if target_ws_id and reset:
            # Delete existing workspace to ensure fresh hydration
            try:
                self.workspace_manager.delete_workspace(target_ws_id)
                target_ws_id = None
            except Exception as e:
                logger.warning(f"Failed deleting existing workspace for reset: {e}")

        if not target_ws_id:
            ws_info = self.workspace_manager.create_workspace(name=ws_name, description=ws_desc)
        else:
            ws_info = self.workspace_manager.switch_workspace(target_ws_id)

        # Ingest documents if workspace has no documents or if reset
        docs_dir = pkg_dir / "documents"
        if docs_dir.exists() and (reset or ws_info.document_count == 0):
            ws_config = AKWConfig(
                db_path=ws_info.db_path,
                assets_dir=ws_info.assets_dir,
                files_dir=ws_info.files_dir,
                workspaces_dir=str(self.workspace_manager.workspaces_dir),
                embedding_model=self.config.embedding_model,
            )
            kb = KnowledgeBase(config=ws_config)

            for doc_file in sorted(docs_dir.iterdir()):
                if doc_file.is_file():
                    try:
                        kb.add_document(file_source=doc_file, filename=doc_file.name)
                        logger.info(f"Ingested example doc: {doc_file.name} into workspace {ws_info.id}")
                    except Exception as e:
                        logger.error(f"Failed ingesting example doc {doc_file.name}: {e}")

            # Refresh metrics
            ws_info = self.workspace_manager.switch_workspace(ws_info.id)

        return ws_info

    def load_all_examples(self, reset: bool = False) -> List[WorkspaceInfo]:
        """Hydrate all bundled examples and set the primary one active."""
        available = self.list_available_examples()
        loaded: List[WorkspaceInfo] = []

        for ex in available:
            try:
                ws = self.load_example(ex.id, reset=reset)
                loaded.append(ws)
            except Exception as e:
                logger.error(f"Failed loading example {ex.id}: {e}")

        # Set first example active
        if loaded:
            self.workspace_manager.switch_workspace(loaded[0].id)
            loaded[0].is_active = True

        return loaded

    def reset_all(self) -> List[WorkspaceInfo]:
        """Wipe all workspaces and recreate fresh examples."""
        # Clean workspaces directory
        ws_dir = self.workspace_manager.workspaces_dir
        if ws_dir.exists():
            for item in ws_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logger.warning(f"Could not delete {item}: {e}")

        # Re-initialize registry with default
        self.workspace_manager._init_registry()
        # Hydrate all examples fresh
        return self.load_all_examples(reset=True)
