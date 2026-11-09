# AI Knowledge Wrapper (`akw`) Documentation

Welcome to the architectural and technical specification suite for **AI Knowledge Wrapper (`akw`)**, an API-based Python library and dual-view application for wrapping Google Gemini and local LLM sessions with grounded local knowledge retrieval.

---

## Specification Suite

1. [Architecture Overview](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/ARCHITECTURE.md)
   - High-level system topology, components, and data flow.
   - Dual-view UI architecture: Grounded Chat Workspace & Knowledge Management Station.
   - Core design principles (single-file SQLite, breadcrumbing, neighbor expansion).
   - Discrete project workspaces and hot-swappable SQLite databases.

2. [Ingestion, Chunking & Storage Specification](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/INGESTION_AND_STORAGE_SPEC.md)
   - Supported document formats (`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.md`, `.txt`) and chosen Python parser libraries.
   - Graphical figure extraction from Word, PDF, and PowerPoint with local Vision LLM analysis.
   - Dedicated figure chunk emission with inline Markdown embeds (`/api/assets/{id}.png`).
   - Original source file byte-for-byte archival and download streaming (`/api/kb/documents/{id}/download`).
   - Hierarchical breadcrumb extraction strategy (`Doc > Section > Subheading`).
   - Semantic sliding window chunking with sequential `chunk_index`.
   - SQLite unified schema (FTS5 BM25 virtual table, vector embeddings, document records).
   - Contiguous neighbor context expansion ($\pm 2$ chunks) and interval merging.

3. [Retrieval, HyDE & RAG Pipeline Specification](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/RETRIEVAL_AND_RAG_SPEC.md)
   - Hypothetical Document Embeddings (HyDE) with local LLMs (e.g. `qwen/qwen3.5-9b` in LM Studio).
   - Local dense embedding models (HuggingFace `BAAI/bge-small-en-v1.5` and Ollama).
   - Sparse BM25 retrieval via SQLite FTS5.
   - Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking (`flashrank`).
   - Grounded LLM prompt engineering and strict citation contracts (`[REF-X]`).

4. [Python API & Session Specification](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/API_AND_SESSION_SPEC.md)
   - Programmatic Python library API (`KnowledgeBase`, `GeminiRAGSession`, `LMStudioRAGSession`, `LocalRAGSession`).
   - Streaming execution and real-time citation emission.
   - FastAPI REST and Server-Sent Events (SSE) endpoints.
   - Workspace management endpoints (`/api/workspaces`) and discrete SQLite architecture.
   - Bundled example dataset hydration and reset endpoints (`/api/workspaces/examples`).

5. [Frontend User Interface Specification](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/FRONTEND_SPEC.md)
   - **View 1: Chat Workspace**: Model switcher (Gemini 3.8 / LM Studio Qwen 3.5 9B), streaming chat, citation pills, slide-over Context Inspector drawer with diagram previews and file downloads.
   - **View 2: Knowledge Base Management Station**: File dropzone, background parsing ticker, interactive chunk curation studio (multi-select delete, inline edits), document inventory table, and retrieval diagnostic sandbox.
   - **Workspace Selector**: Dropdown switcher for discrete project databases and one-click example hydration.

6. [Roadmap & Technical Roadmap](file:///c:/Projects/libraries/AI_knowledge_wrapper/docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md)
   - Complete technology selection matrix.
   - Phased execution steps from core ingestion to UI delivery, multimodal figure extraction, and workspace swapping.

---

## Bundled Example Knowledge Bases

For quick testing and demonstrations, `akw` bundles two fully articulated example projects:
- **Project Apollo: Autonomous Avionics** (`examples/datasets/project_apollo`): Mission avionics, sensor fusion topologies, EKF state estimation rate, failsafe trigger envelopes, and high-res architecture diagrams.
- **BioNexus: Clinical Diagnostics** (`examples/datasets/bionexus_diagnostics`): Secondary NGS bioinformatics pipelines, QC gates, ACMG 5-tier variant classification guidelines, and clinical workflow schemas.

See [`examples/README.md`](file:///c:/Projects/libraries/AI_knowledge_wrapper/examples/README.md) for usage details.
