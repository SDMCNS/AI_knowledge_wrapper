"""Settings and model configuration endpoints."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from akw.core.config import AKWConfig
from akw.kb import KnowledgeBase
from akw.llm.lmstudio_client import LMStudioClient
from server.dependencies import get_config, get_knowledge_base

router = APIRouter(prefix="/api/system", tags=["System & Settings"])


class SettingsDTO(BaseModel):
    helper_llm_provider: str
    helper_llm_model: str
    vision_enabled: bool
    vision_llm_provider: str
    vision_llm_model: str
    vision_timeout_seconds: int
    hyde_enabled: bool
    hyde_model: str
    lmstudio_host: str


class SettingsUpdateRequest(BaseModel):
    helper_llm_provider: Optional[str] = None
    helper_llm_model: Optional[str] = None
    vision_enabled: Optional[bool] = None
    vision_llm_provider: Optional[str] = None
    vision_llm_model: Optional[str] = None
    vision_timeout_seconds: Optional[int] = None
    hyde_enabled: Optional[bool] = None
    hyde_model: Optional[str] = None
    lmstudio_host: Optional[str] = None


@router.get("/settings", response_model=SettingsDTO)
def get_settings(config: AKWConfig = Depends(get_config)):
    """Fetch current system configuration including helper LLM and vision settings."""
    return SettingsDTO(
        helper_llm_provider=config.helper_llm_provider,
        helper_llm_model=config.helper_llm_model,
        vision_enabled=config.vision_enabled,
        vision_llm_provider=config.vision_llm_provider,
        vision_llm_model=config.vision_llm_model,
        vision_timeout_seconds=config.vision_timeout_seconds,
        hyde_enabled=config.hyde_enabled,
        hyde_model=config.hyde_model,
        lmstudio_host=config.lmstudio_host,
    )


@router.post("/settings", response_model=SettingsDTO)
def update_settings(
    req: SettingsUpdateRequest,
    config: AKWConfig = Depends(get_config),
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Update system settings dynamically."""
    if req.helper_llm_provider is not None:
        config.helper_llm_provider = req.helper_llm_provider
    if req.helper_llm_model is not None:
        config.helper_llm_model = req.helper_llm_model
        config.hyde_model = req.helper_llm_model
    if req.vision_enabled is not None:
        config.vision_enabled = req.vision_enabled
    if req.vision_llm_provider is not None:
        config.vision_llm_provider = req.vision_llm_provider
    if req.vision_llm_model is not None:
        config.vision_llm_model = req.vision_llm_model
    if req.vision_timeout_seconds is not None:
        config.vision_timeout_seconds = req.vision_timeout_seconds
    if req.hyde_enabled is not None:
        config.hyde_enabled = req.hyde_enabled
    if req.hyde_model is not None:
        config.hyde_model = req.hyde_model
    if req.lmstudio_host is not None:
        config.lmstudio_host = req.lmstudio_host

    # Propagate to knowledge base and sub-engines
    kb.config = config
    if hasattr(kb, "vision_engine"):
        kb.vision_engine.config = config
    if hasattr(kb, "retrieval_engine"):
        kb.retrieval_engine.config = config
        if hasattr(kb.retrieval_engine, "hyde"):
            kb.retrieval_engine.hyde.config = config

    return get_settings(config=config)

