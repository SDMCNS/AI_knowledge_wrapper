"""RAG Session implementations for Gemini and Local LLMs."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional

from akw.core.config import AKWConfig
from akw.core.models import (
    ChatMessage,
    ChatRole,
    ChatSession,
    Citation,
    ExpandedContextBlock,
)
from akw.kb import KnowledgeBase
from akw.llm.gemini_client import GeminiClient
from akw.llm.lmstudio_client import LMStudioClient
from akw.llm.local_client import LocalLLMClient
from akw.sessions.prompt_builder import PromptBuilder

logger = logging.getLogger("akw.sessions")


class BaseRAGSession(ABC):
    """Abstract base session managing stateful conversation and grounded knowledge retrieval."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.kb = knowledge_base
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.title = title or "New Conversation"
        self.system_instruction = system_instruction or PromptBuilder.SYSTEM_INSTRUCTION_TEMPLATE
        self.temperature = temperature

        # Ensure session exists in SQLite
        existing = self.kb.storage.get_chat_session(self.session_id)
        if not existing:
            session_record = ChatSession(
                id=self.session_id,
                title=self.title,
                model_provider=self.get_provider_name(),
                model_name=self.get_model_name(),
                system_instruction=self.system_instruction,
            )
            self.kb.storage.create_chat_session(session_record)

    @abstractmethod
    def get_provider_name(self) -> str:
        """Name of provider (e.g. 'gemini', 'ollama')."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Name of active model."""
        pass

    @abstractmethod
    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        """Stream tokens from underlying LLM."""
        pass

    @abstractmethod
    def _call_llm_sync(self, prompt: str) -> str:
        """Synchronously generate response from underlying LLM."""
        pass

    def ask(self, user_message: str, top_k: int = 3, expand_window: int = 2) -> ChatMessage:
        """Synchronously send user message, retrieve context, generate response, and persist."""
        # 1. Retrieve knowledge
        context_blocks, citations = self.kb.search(
            query=user_message, top_k=top_k, expand_window=expand_window
        )

        # 2. Build grounded prompt
        prompt = PromptBuilder.build_user_prompt(user_message, context_blocks)

        # 3. Store user message in DB
        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=self.session_id,
            role=ChatRole.USER,
            content=user_message,
        )
        self.kb.storage.insert_chat_message(user_msg)

        # 4. Generate response
        response_text = self._call_llm_sync(prompt)

        # 5. Extract cited references
        used_citations = PromptBuilder.extract_cited_references(response_text, citations)

        # 6. Store assistant message in DB
        assistant_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=self.session_id,
            role=ChatRole.MODEL,
            content=response_text,
            context_blocks=context_blocks,
            citations=used_citations if used_citations else citations,
        )
        self.kb.storage.insert_chat_message(assistant_msg)

        return assistant_msg

    def ask_stream(
        self, user_message: str, top_k: int = 3, expand_window: int = 2
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream conversational interaction yielding status, citations, tokens, and completion."""
        # 1. Status: Searching
        yield {"type": "status", "data": {"step": "retrieval", "message": "Searching knowledge base..."}}

        context_blocks, citations = self.kb.search(
            query=user_message, top_k=top_k, expand_window=expand_window
        )

        # 2. Send citations / sources metadata event
        yield {
            "type": "sources",
            "data": [
                {
                    "id": c.id,
                    "document_name": c.document_name,
                    "breadcrumb": c.breadcrumb,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "score": round(c.score, 3),
                    "excerpt": c.excerpt,
                }
                for c in citations
            ],
            "context_blocks": [b.model_dump() for b in context_blocks],
        }

        # 3. Store user message
        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=self.session_id,
            role=ChatRole.USER,
            content=user_message,
        )
        self.kb.storage.insert_chat_message(user_msg)

        # 4. Build prompt and stream tokens
        prompt = PromptBuilder.build_user_prompt(user_message, context_blocks)
        yield {"type": "status", "data": {"step": "generation", "message": "Generating answer..."}}

        accumulated_tokens: List[str] = []
        for token in self._call_llm_stream(prompt):
            accumulated_tokens.append(token)
            yield {"type": "token", "data": token}

        full_response = "".join(accumulated_tokens)

        # 5. Extract citations actually used
        used_citations = PromptBuilder.extract_cited_references(full_response, citations)

        # 6. Save assistant message
        assistant_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=self.session_id,
            role=ChatRole.MODEL,
            content=full_response,
            context_blocks=context_blocks,
            citations=used_citations if used_citations else citations,
        )
        self.kb.storage.insert_chat_message(assistant_msg)

        yield {
            "type": "done",
            "data": {
                "message_id": assistant_msg.id,
                "citations": [c.model_dump() for c in assistant_msg.citations or []],
            },
        }

    def get_history(self) -> List[ChatMessage]:
        """Fetch all messages for this session from SQLite."""
        return self.kb.storage.get_session_messages(self.session_id)


class GeminiRAGSession(BaseRAGSession):
    """Grounded RAG session powered by Google Gemini."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.model = model or knowledge_base.config.gemini_model
        self.client = GeminiClient(api_key=api_key, config=knowledge_base.config)
        super().__init__(
            knowledge_base=knowledge_base,
            session_id=session_id,
            title=title,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def get_provider_name(self) -> str:
        return "gemini"

    def get_model_name(self) -> str:
        return self.model

    def _call_llm_sync(self, prompt: str) -> str:
        return self.client.generate(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )

    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        return self.client.generate_stream(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )


class LMStudioRAGSession(BaseRAGSession):
    """Grounded RAG session powered by local LM Studio (OpenAI-compatible /v1)."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        model: Optional[str] = None,
        host: Optional[str] = None,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.model = model or knowledge_base.config.lmstudio_model
        self.client = LMStudioClient(host=host, config=knowledge_base.config)
        super().__init__(
            knowledge_base=knowledge_base,
            session_id=session_id,
            title=title,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def get_provider_name(self) -> str:
        return "lmstudio"

    def get_model_name(self) -> str:
        return self.model

    def _call_llm_sync(self, prompt: str) -> str:
        return self.client.generate(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )

    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        return self.client.generate_stream(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )


class LocalRAGSession(BaseRAGSession):
    """Grounded RAG session powered by local Ollama / local LLM."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        model: Optional[str] = None,
        host: Optional[str] = None,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.model = model or knowledge_base.config.ollama_model
        self.client = LocalLLMClient(host=host, config=knowledge_base.config)
        super().__init__(
            knowledge_base=knowledge_base,
            session_id=session_id,
            title=title,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def get_provider_name(self) -> str:
        return "ollama"

    def get_model_name(self) -> str:
        return self.model

    def _call_llm_sync(self, prompt: str) -> str:
        return self.client.generate(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )

    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        return self.client.generate_stream(
            prompt=prompt,
            model=self.model,
            system_instruction=self.system_instruction,
            temperature=self.temperature,
        )

