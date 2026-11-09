# Python API & Session Specification

## 1. Overview

`ai_knowledge_wrapper` (`akw`) provides a two-tiered interface:
1. **Python Developer SDK**: An importable library for programmatic scripts, data pipelines, and CLI utilities.
2. **REST / SSE API**: A high-performance FastAPI service powering web frontends, desktop electron apps, and headless integrations.

---

## 2. Python Developer SDK (`akw`)

### 2.1. Knowledge Base Initialization & Ingestion

```python
from akw import KnowledgeBase, AKWConfig

# 1. Initialize with explicit configuration or environment defaults
config = AKWConfig(
    db_path="./knowledge_base.sqlite",
    embedding_model="BAAI/bge-small-en-v1.5", # Local HuggingFace or Ollama model
    reranker_model="flashrank::ms-marco-TinyBERT-L-2-v2",
    hyde_enabled=True,
    hyde_model="ollama::gemma2:2b",           # Local LLM for HyDE
    context_window_expansion=2                 # Contiguous +/- 2 chunk window
)

kb = KnowledgeBase(config=config)

# 2. Ingest single files with metadata
doc = kb.add_document(
    file_path="./quarterly_report.pdf",
    tags=["finance", "q3_2026"],
    metadata={"department": "Auditing"}
)
print(f"Ingested {doc.filename}: {doc.total_chunks} chunks indexed.")

# 3. Batch ingest an entire directory
docs = kb.add_directory(
    directory_path="./company_docs",
    recursive=True,
    extensions=[".pdf", ".docx", ".xlsx", ".md", ".html"]
)

# 4. Search and inspect retrieval directly
results = kb.search(
    query="What were the capital expenditure projections?",
    top_k=3,
    expand_window=2
)
for hit in results:
    print(f"[{hit.score:.3f}] {hit.breadcrumb}")
    print(f"Contiguous text preview ({len(hit.chunks)} chunks merged):")
    print(hit.expanded_text[:200] + "...\n")
```

---

### 2.2. Gemini RAG Session

```python
from akw.sessions import GeminiRAGSession

session = GeminiRAGSession(
    knowledge_base=kb,
    model="gemini-2.5-flash",        # or 'gemini-2.5-pro'
    api_key="AIzaSy...",             # or read automatically from GEMINI_API_KEY
    temperature=0.2,
    system_instruction="You are a senior compliance auditor answering strictly from files."
)

# Streaming execution with real-time citation pills
response_stream = session.ask_stream("What are the breach reporting requirements?")

for event in response_stream:
    if event.type == "token":
        print(event.text, end="", flush=True)
    elif event.type == "sources":
        print("\n\nReferenced Citations:")
        for ref in event.sources:
            print(f"- [{ref.id}] {ref.document_name} > {ref.breadcrumb} (Page {ref.page})")
```

---

### 2.3. Local LLM RAG Session (Ollama / Local Engine)

The same API pattern works with local models when zero cloud egress is desired:

```python
from akw.sessions import LocalRAGSession

local_session = LocalRAGSession(
    knowledge_base=kb,
    model="llama3.2:3b",
    host="http://localhost:11434",
    temperature=0.3
)

response = local_session.ask("Summarize the vacation rollover policy.")
print(response.content)
print(response.citations)
```

---

## 3. REST & Server-Sent Events (SSE) API Specification

The FastAPI server wraps the SDK and provides unified endpoints:

### 3.1. Knowledge Base Management Endpoints

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/kb/upload` | Upload & stage file in background | `multipart/form-data` | `StagedUploadResponse` |
| `GET` | `/api/kb/staging/tasks/{task_id}` | Poll background parsing progress | None | `TaskProgressResponse` |
| `GET` | `/api/kb/staging/{doc_id}` | Get staged chunks for review | None | `StagedDocumentResponse` |
| `POST` | `/api/kb/staging/{doc_id}/commit` | Commit curated chunks to SQLite | `CommitChunksRequest` | `DocumentResponse` |
| `DELETE` | `/api/kb/staging/{doc_id}` | Discard staged document | None | `{"success": true}` |
| `GET` | `/api/kb/documents` | List all ingested documents | Query: `limit`, `offset`, `search` | `PaginatedDocuments` |
| `GET` | `/api/kb/documents/{id}` | Get document metadata & chunks | None | `DocumentDetailResponse` |
| `GET` | `/api/kb/documents/{id}/download` | Download original archived file | None | Binary file attachment |
| `DELETE` | `/api/kb/documents/{id}` | Delete document & cascade chunks | None | `{"success": true}` |
| `POST` | `/api/kb/search` | Test search & debug scoring | `{"query": str, "top_k": int}` | `SearchDebugResult` |
| `GET` | `/api/assets/{filename}` | Serve extracted graphical figures | None | Image binary stream |

### 3.2. Workspaces & Discrete Knowledge Bases

Manage isolated SQLite databases and asset repositories per project:

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/workspaces` | List all workspaces with stats | None | `List[WorkspaceInfo]` |
| `GET` | `/api/workspaces/active` | Get active workspace details | None | `WorkspaceInfo` |
| `POST` | `/api/workspaces` | Create a new project workspace | `{"name": str, "description": str}` | `WorkspaceInfo` |
| `POST` | `/api/workspaces/{id}/switch` | Switch active workspace database | None | `WorkspaceInfo` |
| `DELETE` | `/api/workspaces/{id}` | Delete workspace & sqlite database | None | `{"success": true}` |

### 3.3. Chat & Session Endpoints

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/chat/sessions` | Create a new chat session | `SessionCreateRequest` | `SessionResponse` |
| `GET` | `/api/chat/sessions` | List existing chat sessions | None | `List[SessionResponse]` |
| `GET` | `/api/chat/sessions/{id}` | Get session details & messages | None | `SessionHistoryResponse` |
| `DELETE` | `/api/chat/sessions/{id}` | Delete a chat session | None | `{"success": true}` |
| `POST` | `/api/chat/sessions/{id}/messages` | Post user query & stream answer | `{"message": str}` | SSE Event Stream |

### 3.4. Server-Sent Events (SSE) Protocol

When querying `/api/chat/sessions/{id}/messages`, the backend streams events in real time:

```
event: status
data: {"step": "hyde", "message": "Drafting hypothetical query expansion with local LLM..."}

event: status
data: {"step": "retrieval", "message": "Executing hybrid BM25 + dense vector search..."}

event: sources
data: [{"ref_id": "REF-1", "doc_name": "policy.pdf", "breadcrumb": "Policy > Section 2", "score": 0.94, "chunks": [3, 4, 5]}]

event: token
data: {"text": "According"}

event: token
data: {"text": " to the breach policy [REF-1],"}

event: done
data: {"finish_reason": "stop", "token_usage": {"prompt": 1240, "completion": 85}}
```

