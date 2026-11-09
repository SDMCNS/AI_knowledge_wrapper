"""FastAPI dependency injection for KnowledgeBase and configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional

from akw.core.config import AKWConfig
from akw.core.workspace import WorkspaceManager
from akw.kb import KnowledgeBase

_CONFIG_INSTANCE: Optional[AKWConfig] = None
_WORKSPACE_MANAGER_INSTANCE: Optional[WorkspaceManager] = None
_KB_CACHE: Dict[str, KnowledgeBase] = {}


def get_config() -> AKWConfig:
    """Get active configuration singleton."""
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = AKWConfig()
    return _CONFIG_INSTANCE


def get_workspace_manager() -> WorkspaceManager:
    """Get or create singleton WorkspaceManager."""
    global _WORKSPACE_MANAGER_INSTANCE
    if _WORKSPACE_MANAGER_INSTANCE is None:
        cfg = get_config()
        _WORKSPACE_MANAGER_INSTANCE = WorkspaceManager(config=cfg)
    return _WORKSPACE_MANAGER_INSTANCE


def get_knowledge_base() -> KnowledgeBase:
    """Get or create the KnowledgeBase instance for the currently active workspace."""
    wm = get_workspace_manager()
    active_ws = wm.get_active_workspace()

    global _KB_CACHE
    if active_ws.id not in _KB_CACHE:
        cfg = get_config().model_copy()
        cfg.db_path = active_ws.db_path
        cfg.assets_dir = active_ws.assets_dir
        cfg.files_dir = active_ws.files_dir
        _KB_CACHE[active_ws.id] = KnowledgeBase(config=cfg)

    return _KB_CACHE[active_ws.id]


def clear_knowledge_base_cache(workspace_id: Optional[str] = None) -> None:
    """Evict cached KnowledgeBase instances on configuration or workspace updates."""
    global _KB_CACHE
    if workspace_id:
        _KB_CACHE.pop(workspace_id, None)
    else:
        _KB_CACHE.clear()

