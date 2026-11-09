"""Tests for Grounded Prompts and RAG Sessions."""

from typing import Generator
import pytest

from akw.core.config import AKWConfig
from akw.core.models import Citation, ExpandedContextBlock
from akw.kb import KnowledgeBase
from akw.sessions.prompt_builder import PromptBuilder
from akw.sessions.rag_session import BaseRAGSession


def test_prompt_builder():
    blocks = [
        ExpandedContextBlock(
            citation_id="REF-1",
            document_id="doc_1",
            document_name="server_config.md",
            breadcrumb="Server > Ports",
            page_start=1,
            merged_text="The API server listens on port 8000 by default.",
            relevance_score=0.95,
        )
    ]
    citations = [
        Citation(
            id="REF-1",
            document_name="server_config.md",
            breadcrumb="Server > Ports",
            page_start=1,
            score=0.95,
            excerpt="The API server listens on port 8000...",
        )
    ]

    prompt = PromptBuilder.build_user_prompt("What port does the server use?", blocks)
    assert "--- BEGIN REF-1 ---" in prompt
    assert "server_config.md" in prompt
    assert "The API server listens on port 8000" in prompt

    model_answer = "The server listens on port 8000 [REF-1]."
    used = PromptBuilder.extract_cited_references(model_answer, citations)
    assert len(used) == 1
    assert used[0].id == "REF-1"


class MockRAGSession(BaseRAGSession):
    def get_provider_name(self) -> str:
        return "mock"

    def get_model_name(self) -> str:
        return "mock-model"

    def _call_llm_sync(self, prompt: str) -> str:
        return "This is a mock answer based on [REF-1]."

    def _call_llm_stream(self, prompt: str) -> Generator[str, None, None]:
        tokens = ["This ", "is ", "a ", "mock ", "stream [REF-1]."]
        for t in tokens:
            yield t


def test_mock_rag_session(tmp_path):
    db_path = str(tmp_path / "test_session.sqlite")
    config = AKWConfig(
        db_path=db_path,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        target_chunk_size=50,
        hyde_enabled=False,
        reranker_provider="none",
    )
    kb = KnowledgeBase(config=config)
    kb.add_document(
        file_source=b"# Guidelines\n\nAlways use port 8000.",
        filename="ports.md",
    )

    session = MockRAGSession(knowledge_base=kb)
    events = list(session.ask_stream("What port?"))

    event_types = [e["type"] for e in events]
    assert "status" in event_types
    assert "sources" in event_types
    assert "token" in event_types
    assert "done" in event_types

    history = session.get_history()
    assert len(history) == 2
    assert history[0].role.value == "user"
    assert history[1].role.value == "model"

