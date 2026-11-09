"""API endpoints for Chat sessions, real-time SSE streaming, and model discovery."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from akw.core.models import ChatMessage, ChatRole, ChatSession
from akw.kb import KnowledgeBase
from akw.llm.lmstudio_client import LMStudioClient
from akw.llm.local_client import LocalLLMClient
from akw.sessions.rag_session import GeminiRAGSession, LMStudioRAGSession, LocalRAGSession
from server.dependencies import get_config, get_knowledge_base

router = APIRouter(prefix="/api/chat", tags=["Chat & Sessions"])


class SessionCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    model_provider: str = "gemini"  # "gemini" | "lmstudio" | "ollama"
    model_name: Optional[str] = None
    system_instruction: Optional[str] = None


class MessageSendRequest(BaseModel):
    message: str
    top_k: Optional[int] = 3
    expand_window: Optional[int] = 2


class SessionDetailResponse(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]


class ModelOption(BaseModel):
    id: str
    name: str
    provider: str
    is_local: bool


@router.get("/models", response_model=List[ModelOption])
def list_available_models(config=Depends(get_config)):
    """List cloud Gemini models and locally installed LM Studio / Ollama models."""
    models = [
        ModelOption(id="gemini-3.8-flash", name="Gemini 3.8 Flash (Google Cloud)", provider="gemini", is_local=False),
        ModelOption(id="gemini-3.8-pro", name="Gemini 3.8 Pro (Google Cloud)", provider="gemini", is_local=False),
    ]

    # 1. Discover local LM Studio models (OpenAI compatible on port 1234)
    try:
        lm_client = LMStudioClient(config=config)
        lm_models = lm_client.list_models()
        if lm_models:
            for lmm in lm_models:
                models.append(
                    ModelOption(id=lmm, name=f"LM Studio: {lmm}", provider="lmstudio", is_local=True)
                )
        else:
            # Add default fallback model option for LM Studio if service is ready
            models.append(
                ModelOption(
                    id=config.lmstudio_model,
                    name=f"LM Studio: {config.lmstudio_model}",
                    provider="lmstudio",
                    is_local=True,
                )
            )
    except Exception:
        pass

    # 2. Discover local Ollama models (port 11434)
    try:
        local_client = LocalLLMClient(config=config)
        ollama_models = local_client.list_models()
        for om in ollama_models:
            models.append(
                ModelOption(id=om, name=f"Ollama: {om}", provider="ollama", is_local=True)
            )
    except Exception:
        pass

    return models


@router.post("/sessions", response_model=ChatSession)
def create_session(
    req: SessionCreateRequest, kb: KnowledgeBase = Depends(get_knowledge_base)
):
    """Create a new conversational session."""
    import uuid

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    model_name = req.model_name
    if not model_name:
        if req.model_provider == "gemini":
            model_name = kb.config.gemini_model
        elif req.model_provider == "lmstudio":
            model_name = kb.config.lmstudio_model
        else:
            model_name = kb.config.ollama_model

    session = ChatSession(
        id=session_id,
        title=req.title or "New Conversation",
        model_provider=req.model_provider,
        model_name=model_name,
        system_instruction=req.system_instruction,
    )
    kb.storage.create_chat_session(session)
    return session


@router.get("/sessions", response_model=List[ChatSession])
def list_sessions(kb: KnowledgeBase = Depends(get_knowledge_base)):
    """List all chat sessions."""
    return kb.storage.list_chat_sessions()


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Get chat session details and message history."""
    session = kb.storage.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = kb.storage.get_session_messages(session_id)
    return SessionDetailResponse(session=session, messages=messages)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, kb: KnowledgeBase = Depends(get_knowledge_base)):
    """Delete a chat session."""
    success = kb.storage.delete_chat_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "deleted_id": session_id}


@router.post("/sessions/{session_id}/messages")
async def send_message_stream(
    session_id: str,
    req: MessageSendRequest,
    kb: KnowledgeBase = Depends(get_knowledge_base),
):
    """Post message and stream response events via Server-Sent Events (SSE)."""
    session_record = kb.storage.get_chat_session(session_id)
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found")

    # Instantiate the appropriate RAG session
    if session_record.model_provider == "gemini":
        rag_session = GeminiRAGSession(
            knowledge_base=kb,
            model=session_record.model_name,
            session_id=session_id,
            system_instruction=session_record.system_instruction,
        )
    elif session_record.model_provider == "lmstudio":
        rag_session = LMStudioRAGSession(
            knowledge_base=kb,
            model=session_record.model_name,
            session_id=session_id,
            system_instruction=session_record.system_instruction,
        )
    else:
        rag_session = LocalRAGSession(
            knowledge_base=kb,
            model=session_record.model_name,
            session_id=session_id,
            system_instruction=session_record.system_instruction,
        )

    def event_generator():
        try:
            for event in rag_session.ask_stream(
                user_message=req.message,
                top_k=req.top_k or 3,
                expand_window=req.expand_window or 2,
            ):
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event),
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())
