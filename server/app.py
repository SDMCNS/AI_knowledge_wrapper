"""FastAPI application entrypoint for AI Knowledge Wrapper."""

from __future__ import annotations

import os
import mimetypes
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.dependencies import get_config, get_knowledge_base
from server.routers import chat, documents, settings, workspaces

app = FastAPI(
    title="AI Knowledge Wrapper (akw) API",
    description="API for local grounded knowledge base management and Gemini/Local LLM chat sessions",
    version="0.1.0",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(settings.router)
app.include_router(workspaces.router)


@app.get("/api/assets/{filename}")
def get_extracted_asset(filename: str):
    """Serve an extracted graphical figure or slide image."""
    kb = get_knowledge_base()
    asset_path = kb.asset_manager.get_asset_path(filename)
    if not asset_path or not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset figure not found")
    media_type, _ = mimetypes.guess_type(asset_path.name)
    return FileResponse(
        str(asset_path),
        media_type=media_type or "image/png",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "akw-backend"}


@app.get("/api/system/status")
def system_status():
    """Return backend runtime diagnostics."""
    config = get_config()
    kb = get_knowledge_base()
    docs = kb.list_documents()
    total_chunks = sum(d.total_chunks for d in docs)

    db_size_bytes = 0
    if os.path.exists(config.db_path):
        db_size_bytes = os.path.getsize(config.db_path)

    return {
        "db_path": config.db_path,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "total_documents": len(docs),
        "total_chunks": total_chunks,
        "embedding_model": config.embedding_model,
        "reranker_model": config.reranker_model,
        "hyde_enabled": config.hyde_enabled,
        "window_expansion": config.window_expansion,
        "gemini_configured": bool(config.gemini_api_key),
    }


# Mount frontend static files if built
frontend_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

