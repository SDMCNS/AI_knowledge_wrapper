"""Background Task Manager for non-blocking document parsing and indexing."""

from __future__ import annotations

import asyncio
import concurrent.futures
import datetime
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from akw.core.models import StagedDocument
from akw.kb import KnowledgeBase

logger = logging.getLogger("akw.tasks")


class TaskRecord(BaseModel):
    id: str
    task_type: str  # "stage" | "ingest"
    filename: str
    file_size_bytes: int
    status: str = "queued"  # "queued" | "processing" | "completed" | "failed"
    progress: int = 0  # 0 to 100
    current_step: str = "Queued..."
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None


class BackgroundTaskManager:
    """Thread-safe manager for asynchronous document parsing and ingestion jobs."""

    def __init__(self, max_workers: int = 3):
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> List[TaskRecord]:
        with self._lock:
            # Return tasks sorted newest first
            return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    def clear_completed(self) -> None:
        with self._lock:
            self._tasks = {
                tid: t for tid, t in self._tasks.items() if t.status not in ("completed", "failed")
            }

    def start_stage_task(
        self, file_bytes: bytes, filename: str, kb: KnowledgeBase
    ) -> TaskRecord:
        """Launch background staging (parse + chunk) without blocking caller."""
        task_id = f"tsk_{uuid.uuid4().hex[:12]}"
        task = TaskRecord(
            id=task_id,
            task_type="stage",
            filename=filename,
            file_size_bytes=len(file_bytes),
            status="queued",
            progress=5,
            current_step="Queued for parsing...",
        )

        with self._lock:
            self._tasks[task_id] = task

        self._executor.submit(self._run_stage_worker, task_id, file_bytes, filename, kb)
        return task

    def _run_stage_worker(
        self, task_id: str, file_bytes: bytes, filename: str, kb: KnowledgeBase
    ) -> None:
        """Worker thread executing document parsing and chunking with progress ticker updates."""
        try:
            self._update_task(task_id, status="processing", progress=15, step="Initializing parser & checking content...")

            # Parse content
            has_vision = bool(
                getattr(kb, "vision_engine", None)
                and getattr(kb.vision_engine.config, "vision_enabled", False)
                and filename.lower().endswith((".pptx", ".ppt", ".pdf"))
            )
            step_msg = (
                "Extracting text, tables, and analyzing figures with Vision LLM..."
                if has_vision
                else "Extracting text, tables, and document layout..."
            )
            self._update_task(task_id, progress=35, step=step_msg)
            staged_doc = kb.stage_document(file_source=file_bytes, filename=filename)

            self._update_task(task_id, progress=75, step="Preserving heading hierarchy & breadcrumbs...")

            self._update_task(task_id, progress=90, step="Synthesizing windowed semantic chunks...")

            # Ready
            self._update_task(
                task_id,
                status="completed",
                progress=100,
                step=f"Ready for review ({len(staged_doc.chunks)} chunks generated)",
                result=staged_doc.model_dump(),
                completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self._update_task(
                task_id,
                status="failed",
                progress=100,
                step="Failed to process document",
                error=str(e),
                completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )

    def _update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        step: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = progress
            if step is not None:
                task.current_step = step
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if completed_at is not None:
                task.completed_at = completed_at


# Global Task Manager singleton
task_manager = BackgroundTaskManager()

