"""API endpoints for Document ingestion, chunk review/staging, and KB management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from akw.core.models import (
    Chunk,
    Citation,
    CommitChunksRequest,
    Document,
    ExpandedContextBlock,
    StagedChunk,
    StagedDocument,
)
from akw.kb import KnowledgeBase
from server.dependencies import get_knowledge_base
from server.tasks import TaskRecord, task_manager

router = APIRouter(prefix="/api/kb", tags=["Knowledge Base"])


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3
    expand_window: Optional[int] = 2


class SearchResponse(BaseModel):
    query: str
    context_blocks: List[ExpandedContextBlock]
    citations: List[Citation]


class DocumentDetailResponse(BaseModel):
    document: Document
    chunks: List[Chunk]


class ChunkUpdateRequest(BaseModel):
    content: str
    breadcrumb_display: Optional[str] = None


@router.post("/tasks/stage", response_model=TaskRecord)
async def start_background_stage_task(
    file: UploadFile = File(...),
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Launch asynchronous background parsing and chunking job, returning immediately."""
    try:
        content = await file.read()
        task = task_manager.start_stage_task(
            file_bytes=content,
            filename=file.filename or "uploaded_file",
            kb=kb,
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start task: {str(e)}")


@router.get("/tasks", response_model=List[TaskRecord])
def list_tasks():
    """List all background document processing tasks."""
    return task_manager.list_tasks()


@router.get("/tasks/{task_id}", response_model=TaskRecord)
def get_task_status(task_id: str):
    """Get real-time progress and status of a specific background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/completed")
def clear_completed_tasks():
    """Clear finished tasks from the tracker."""
    task_manager.clear_completed()
    return {"success": True}


@router.post("/stage", response_model=StagedDocument)
async def stage_document_for_review(
    file: UploadFile = File(...),
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Parse and chunk a file without committing, returning draft chunks for user review & editing."""
    try:
        content = await file.read()
        staged = kb.stage_document(
            file_source=content,
            filename=file.filename or "uploaded_file",
        )
        return staged
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse and stage '{file.filename}': {str(e)}")


@router.post("/commit", response_model=Document)
def commit_reviewed_chunks(
    req: CommitChunksRequest,
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Commit user-curated and reviewed chunks to the SQLite knowledge base."""
    try:
        doc = kb.commit_staged_chunks(req)
        return doc
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to commit chunks: {str(e)}")


@router.post("/upload", response_model=List[Document])
async def upload_documents_direct(
    files: List[UploadFile] = File(...),
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Directly upload and auto-commit one or more documents without manual review."""
    ingested = []
    for file in files:
        try:
            content = await file.read()
            doc = kb.add_document(
                file_source=content,
                filename=file.filename or "uploaded_file",
            )
            ingested.append(doc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to ingest '{file.filename}': {str(e)}")

    return ingested


@router.get("/documents", response_model=List[Document])
def list_documents(kb: KnowledgeBase = Depends(get_knowledge_base)):
    """List all documents in the knowledge base."""
    return kb.list_documents()


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Fetch document metadata and all its indexed chunks."""
    doc = kb.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = kb.get_chunks(document_id)
    return DocumentDetailResponse(document=doc, chunks=chunks)


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Download the original uploaded document file."""
    doc = kb.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = kb.get_document_file_path(document_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Original document file not found on disk")

    media_type, _ = mimetypes.guess_type(doc.filename)
    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type=media_type or "application/octet-stream",
    )


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Delete document and all associated chunks, vectors, and FTS indexes."""
    success = kb.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True, "deleted_id": document_id}


@router.put("/chunks/{chunk_id}", response_model=Chunk)
def update_chunk(
    chunk_id: str,
    req: ChunkUpdateRequest,
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Update an existing chunk's text and refresh its dense vector embedding."""
    updated = kb.update_chunk(
        chunk_id=chunk_id,
        new_content=req.content,
        new_breadcrumb=req.breadcrumb_display,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return updated


class BatchDeleteChunksRequest(BaseModel):
    chunk_ids: List[str]


@router.post("/chunks/batch-delete")
def batch_delete_chunks(
    req: BatchDeleteChunksRequest, kb: KnowledgeBase = Depends(get_knowledge_base)
):
    """Delete multiple chunks in a single batch request."""
    count = kb.delete_chunks(req.chunk_ids)
    return {"success": True, "deleted_count": count}


@router.delete("/chunks/{chunk_id}")
def delete_chunk(chunk_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Delete an individual chunk from the knowledge base."""
    success = kb.delete_chunk(chunk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {"success": True, "deleted_id": chunk_id}


@router.post("/search", response_model=SearchResponse)
def search_knowledge_base(
    req: SearchRequest, kb: KnowledgeBase = Depends(get_knowledge_base)
):
    """Diagnostic search endpoint testing HyDE, BM25, vectors, and +/- 2 neighbor expansion."""
    blocks, citations = kb.search(
        query=req.query, top_k=req.top_k, expand_window=req.expand_window
    )
    return SearchResponse(query=req.query, context_blocks=blocks, citations=citations)
