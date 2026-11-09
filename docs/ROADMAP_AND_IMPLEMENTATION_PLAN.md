# Implementation Plan & Technical Roadmap

## 1. Technology Stack Breakdown

```
+--------------------------------------------------------------------------------------------------+
|                                    TECHNOLOGY SELECTION MATRIX                                   |
+----------------------+------------------------------------+--------------------------------------+
| Layer                | Selected Technology                | Rationale                            |
+----------------------+------------------------------------+--------------------------------------+
| Language / Runtime   | Python 3.10+                       | Standard for AI/ML and data pipelines|
| PDF Parsing          | `pymupdf` (PyMuPDF / fitz)         | 10x faster than pypdf; font metrics  |
| DOCX Parsing         | `python-docx`                      | Native style hierarchy & table parser|
| Spreadsheet Parsing  | `openpyxl`, `pandas`               | Complete Excel & CSV serialization   |
| HTML Parsing         | `beautifulsoup4`, `html5lib`       | Robust HTML DOM tree & heading walk  |
| Markdown Parsing     | `markdown-it-py`                   | CommonMark compliant AST navigation  |
| Tokenization         | `tiktoken` / `regex`               | Accurate token counts for LLMs       |
| Primary Database     | SQLite (`sqlite3` stdlib)          | Zero-server, single file, ACID       |
| BM25 Full-Text       | SQLite FTS5 Extension              | Built-in C implementation, no daemon |
| Dense Vector Storage | SQLite BLOB / `sqlite-vec`         | Direct embedding storage in SQLite   |
| Local Embeddings     | `sentence-transformers` / Ollama   | Run BGE/MiniLM on CPU without GPU    |
| Local HyDE Expander  | Ollama / Local HTTP LLM API        | Fast, offline query expansion        |
| Local Reranking      | `flashrank` (ONNX)                 | Fast (<15ms), zero GPU dependency    |
| Cloud LLM            | `google-genai` (Official SDK)      | Native Gemini 2.5 streaming & safety |
| Web Backend          | `fastapi`, `uvicorn`, `pydantic`   | Async SSE streaming, OpenAPI docs    |
| Web Frontend         | React 18, Vite, Tailwind, Lucide   | Modern, responsive, decoupled SPA    |
+----------------------+------------------------------------+--------------------------------------+
```

---

## 2. Phased Execution Roadmap

### Phase 1: Ingestion & Breadcrumbing Foundation
- [ ] Define core data contracts (`Document`, `Chunk`, `ParsedBlock`, `BreadcrumbPath`) in `akw.core.models`.
- [ ] Implement `PDFParser`, `DocxParser`, `ExcelParser`, `HTMLParser`, and `MarkdownParser`.
- [ ] Implement `BreadcrumbTracker` maintaining heading stacks across block streams.
- [ ] Implement `WindowedChunker` slicing text on sentence boundaries with sequential indices (`chunk_index`).
- [ ] Unit tests for parsers verifying breadcrumb fidelity across file formats.

### Phase 2: SQLite Storage Engine (FTS5 + Vectors)
- [ ] Implement SQLite schema manager creating `documents`, `chunks`, `chunks_fts`, and `chunk_embeddings`.
- [ ] Implement FTS5 sync triggers and BM25 query methods with parameter sanitization.
- [ ] Implement vector serialization/deserialization with pure-Python/NumPy cosine similarity fallback and `sqlite-vec` acceleration.
- [ ] Build idempotent file ingestion with SHA-256 deduplication.

### Phase 3: Hybrid Retrieval, HyDE & $\pm 2$ Window Merging
- [ ] Implement `LocalEmbeddingEngine` supporting HuggingFace `sentence-transformers` and Ollama endpoints.
- [ ] Implement `HyDEGenerator` querying a local LLM to draft hypothetical passages.
- [ ] Implement `HybridSearchEngine` calculating Reciprocal Rank Fusion (RRF) between BM25 and vector scores.
- [ ] Integrate `LocalReranker` using `flashrank` to re-score candidates.
- [ ] Implement `ContextWindowExpander` fetching $\pm 2$ chunks and merging overlapping intervals.

### Phase 4: Gemini Session & Grounded RAG Orchestration
- [ ] Integrate official `google-genai` SDK for Gemini 2.5 Flash and Pro.
- [ ] Implement `LocalLLMClient` (Ollama streaming compatible).
- [ ] Design grounded prompt builder with strict `[REF-X]` citation contracts.
- [ ] Implement `GeminiRAGSession` and `LocalRAGSession` supporting stateful chat, streaming responses, and citation metadata extraction.

### Phase 5: FastAPI REST & SSE Service
- [ ] Create `/api/kb/upload` (multipart file processing with progress).
- [ ] Create `/api/kb/documents` (CRUD, document metadata, chunk exploration).
- [ ] Create `/api/kb/search` (search sandbox for diagnostics).
- [ ] Create `/api/chat/sessions` and `/api/chat/sessions/{id}/messages` with Server-Sent Events (SSE).
- [ ] Package CLI command: `akw serve --port 8000 --db ./kb.sqlite`.

### Phase 6: Dual-View Web Interface
- [ ] Initialize Vite + React + Tailwind frontend application in `web/`.
- [ ] Implement **View 1: Chat Workspace**:
  - Live SSE message streaming.
  - Interactive `[REF-X]` citation pills.
  - Slide-over Context Inspector drawer showing breadcrumb, scores, and $\pm 2$ chunk windows.
  - Model selector (Gemini vs Local Ollama).
- [ ] Implement **View 2: Knowledge Base Management Station**:
  - Drag-and-drop document upload with format validation.
  - Document inventory table with chunk counts and delete options.
  - Chunk inspector modal.
  - Retrieval diagnostic sandbox.

### Phase 7: Verification & End-to-End Validation
- [ ] End-to-end ingestion test of a sample PDF, Word document, Excel sheet, and Markdown file.
- [ ] Retrieval quality benchmark: verify that HyDE + hybrid search retrieves correct chunks.
- [ ] Verify that context expansion retrieves preceding and succeeding neighbor chunks correctly.
- [ ] Validate citation compliance and streaming stability with Gemini.

