# AI Knowledge Wrapper (`akw`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-FTS5%20%2B%20Vectors-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Google Gemini](https://img.shields.io/badge/Gemini-3.8%20Flash%20%2F%20Pro-8E75C2.svg?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![LM Studio](https://img.shields.io/badge/LM%20Studio-Qwen%203.5%209B-00ADD8.svg?style=flat)](https://lmstudio.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**AI Knowledge Wrapper (`akw`)** is an API-based Python library and dual-view web application for wrapping **Google Gemini 3.8** and local LLM sessions (**LM Studio** / **Ollama**) with grounded local knowledge retrieval.

It provides a zero-external-database, local-first RAG engine featuring unified SQLite storage (relational + FTS5 BM25 + dense vectors), multimodal figure and diagram extraction with local Vision LLMs, hierarchical document breadcrumbs, contiguous $\pm 2$ chunk window expansion, local HyDE query expansions, discrete project workspaces, and interactive pre-commit chunk curation.

---

## 🏗️ System Architecture

```
+----------------------------------------------------------------------------------------------------+
|                                     AI KNOWLEDGE WRAPPER (AKW)                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   [ UPLOAD DROPZONE / CLI ]                                                                        |
|      PDF | DOCX | PPTX | XLSX | HTML | MD | TXT                                                    |
|                   │                                                                                |
|                   ▼                                                                                |
|   [ MULTI-FORMAT PARSERS & VISION EXTRACTOR ]                                                      |
|      • PyMuPDF (PDF)        • python-docx (DOCX)     • python-pptx (PPT/PPTX)                      |
|      • openpyxl (Excel)     • beautifulsoup4 (HTML)  • markdown-it-py (Markdown)                   |
|      • High-Res Image Extraction ──► Local Vision LLM (Qwen / Gemini) ──► Figure Summary           |
|      • Original File Archiver ──► ./workspaces/{id}/files/{doc_id}_{filename}                      |
|                   │                                                                                |
|                   ▼                                                                                |
|   [ CHUNK CURATION & STAGING STUDIO ]                                                              |
|      • Windowed Semantic Chunker (Sentence-aware)                                                  |
|      • Breadcrumb Tracking: Doc.docx > Section 1 > Subsection 2                                    |
|      • Standalone Figure Chunks with Markdown Link & Preview: ![Figure](/api/assets/ast_xxx.png)  |
|      • Non-blocking Ingestion Ticker & Multi-Select Chunk Deletion / Editing                       |
|                   │                                                                                |
|                   ▼                                                                                |
|   [ DISCRETE SQLITE WORKSPACE ENGINE ]                                                             |
|      • Isolated Project DBs: ./workspaces/{id}/knowledge_base.sqlite                               |
|      • FTS5 BM25 Full-Text Virtual Table (Auto-sync triggers)                                      |
|      • Dense Embeddings BLOBs (BAAI/bge-small-en-v1.5 / MiniLM / Ollama)                           |
|                   ▲                                                                                |
|                   │ Hybrid RRF Search (BM25 + Cosine) + ±2 Contiguous Window Merging               |
|                   │                                                                                |
|   [ GROUNDED RAG ORCHESTRATOR ] ◄── Local HyDE Query Expansion (Qwen 3.5 9B / LM Studio)           |
|      • FlashRank Cross-Encoder Local Reranker (<15ms)                                              |
|      • Strict Citation Protocol: [REF-1], [REF-2] with breadcrumb & page citations                |
|                   │                                                                                |
|                   ▼                                                                                |
|   [ DUAL-VIEW INTERFACE (VITE + REACT + TAILWIND) ]                                                |
|      • View 1: Grounded Chat Workspace (Gemini 3.8 / LM Studio streaming, Citation Pills, Drawer) |
|      • View 2: Knowledge Base Management Station (Staging, File Archival, Workspace Switcher)     |
|      • Example Datasets: One-click hydration for Project Apollo & BioNexus Diagnostics             |
+----------------------------------------------------------------------------------------------------+
```

---

## 🌟 Key Capabilities

### 1. Zero-Daemon SQLite Engine & Multi-Project Workspaces
- **Discrete Databases per Project**: Each workspace manages its own isolated `knowledge_base.sqlite`, `assets/` folder, and archived `files/`. Project managers can swap projects on the fly without server restarts.
- **Unified SQLite Persistence**: Relational metadata, FTS5 BM25 text indices, and dense vector embeddings reside in standard SQLite files—zero Docker or external database services required.
- **Original Source File Archiving**: Preserves byte-for-byte copies of uploaded files. Users can download original documents directly from the UI or via `GET /api/kb/documents/{id}/download`.

### 2. Graphical Asset Extraction & Local Vision LLMs
- **Automated Figure Extraction**: Detects, extracts, and deduplicates drawings, charts, and slide figures from `.docx`, `.pdf`, and `.pptx` documents into `knowledge_assets/`.
- **Vision Summaries**: Dispatches figures to your configured vision model (**LM Studio** `qwen/qwen3.5-9b` / `qwen3-vl-8b` or **Gemini Vision**) to synthesize detailed functional descriptions.
- **Dedicated Figure Chunks**: Generates standalone, searchable figure chunks containing inline Markdown previews: `![Figure](/api/assets/ast_xxx.png)` with full metadata preservation.

### 3. Non-Blocking Ingestion & Interactive Chunk Curation
- **Asynchronous Task Processing**: Uploading large multi-hundred page documents will never freeze your browser. A live header progress ticker displays parsing percentage and triggers notifications when ready.
- **Staging Review Studio**: Review parsed chunks before committing them to the permanent knowledge base. Edit content and breadcrumbs in-place, or select multiple useless chunks and delete them in bulk.

### 4. Hierarchical Breadcrumbs & $\pm 2$ Contiguous Chunk Expansion
- **Hierarchical Paths**: Embeds deep document paths (`Handbook.pdf > Chapter 4: Avionics > Section 4.2: Failsafe Protocols`) directly into chunk metadata and search results.
- **$\pm 2$ Window Expansion**: When a seed chunk matches a user's query, the retrieval engine retrieves its preceding (-2) and succeeding (+2) neighbor chunks, merging contiguous intervals into cohesive, unified context blocks.

### 5. Grounded Citations & Dual-View Web UI
- **Strict Verification Protocol**: Models answer strictly from retrieved knowledge, embedding interactive `[REF-X]` citation pills.
- **Slide-Over Context Inspector**: Clicking any citation pill opens an inspector drawer displaying exact relevance scores, breadcrumbs, page ranges, neighboring chunks, and original figure previews.

---

## 📦 Bundled Example Knowledge Bases

`akw` ships with pre-configured, production-grade example datasets located in [`examples/datasets/`](examples/datasets/):

| Example Dataset | Domain | Included Files | Graphical Figures |
| :--- | :--- | :--- | :--- |
| **Project Apollo: Autonomous Avionics** (`project_apollo`) | Aerospace & Guidance | `01_apollo_avionics_architecture.docx`<br>`02_flight_safety_specifications.md`<br>`03_sensor_telemetry_flow.pptx` | High-res telemetry flowchart (`apollo_telemetry_flowchart.png`), EKF3 fusion schema, CAN bus table |
| **BioNexus: Clinical Diagnostics** (`bionexus_diagnostics`) | Genomics & Bioinformatics | `01_clinical_genomics_pipeline.docx`<br>`02_acmg_variant_classification.md`<br>`03_sequencing_quality_standards.pptx` | High-res secondary pipeline flowchart (`bionexus_pipeline_diagram.png`), ACMG 5-tier classification rules |

### Loading Examples:
- **In the Web UI**: Open the **Workspace Selector** in the header and click **"🚀 Load Examples"** or **"🔄 Reset Clean"**.
- **Via CLI**:
  ```bash
  # List bundled examples
  akw examples list

  # Hydrate all examples into discrete SQLite workspaces
  akw examples load

  # Reset all data and hydrate fresh examples
  akw examples load --reset
  ```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/your-username/AI_knowledge_wrapper.git
cd AI_knowledge_wrapper

# Install dependencies and package in editable mode
pip install -e .
```

### 2. Configure Environment (Optional)

```bash
# For Google Gemini 3.8
export GEMINI_API_KEY="AIzaSy..."

# For Windows PowerShell
$env:GEMINI_API_KEY="AIzaSy..."
```
*(If using local models exclusively with LM Studio or Ollama, no API key is required).*

### 3. Launch the Application

```bash
akw serve --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser to start exploring!

---

## 💻 Python Library SDK

Import and use `akw` programmatically inside Python applications, Jupyter notebooks, or automation scripts:

```python
from akw import KnowledgeBase, AKWConfig
from akw.sessions import GeminiRAGSession, LMStudioRAGSession

# 1. Initialize Knowledge Base with custom SQLite database and local embeddings
config = AKWConfig(
    db_path="./my_project.sqlite",
    embedding_model="BAAI/bge-small-en-v1.5",
    context_window_expansion=2, # Contiguous +/- 2 chunk window
)
kb = KnowledgeBase(config=config)

# 2. Ingest document (automatically extracts figures and archives file)
doc = kb.add_document("./specs/apollo_avionics.docx")
print(f"Ingested '{doc.filename}': {doc.total_chunks} chunks indexed.")

# 3. Hybrid Search with +/- 2 neighbor expansion
context_blocks, citations = kb.search("What is the EKF state estimation rate?", top_k=3, expand_window=2)
for block in context_blocks:
    print(f"[{block.citation_id}] {block.document_name} > {block.breadcrumb}")
    print(block.merged_text[:300] + "...\n")

# 4. Interactive Chat Session with Gemini 3.8 (Streaming)
session = GeminiRAGSession(knowledge_base=kb, model="gemini-3.8-flash")
for event in session.ask_stream("Explain the emergency recovery triggers."):
    if event["type"] == "token":
        print(event["data"], end="", flush=True)
    elif event["type"] == "sources":
        print("\n\nCitations:", [s["document_name"] for s in event["data"]])

# 5. Interactive Chat Session with Local LM Studio (Qwen 3.5 9B)
local_session = LMStudioRAGSession(
    knowledge_base=kb,
    model="qwen/qwen3.5-9b",
    host="http://localhost:1234/v1"
)
response = local_session.ask("Summarize the CAN bus message IDs.")
print(response.content)
```

---

## 🛠️ CLI Reference

The unified `akw` CLI provides instant terminal control:

| Command | Description | Example |
| :--- | :--- | :--- |
| `akw serve` | Launch the FastAPI backend and React web UI | `akw serve --port 8000` |
| `akw ingest` | Ingest a single file or directory into SQLite | `akw ingest ./my_docs/ --db ./kb.sqlite` |
| `akw search` | Test hybrid search and $\pm 2$ window expansion | `akw search "failsafe timeout" --top-k 3 --window 2` |
| `akw examples list` | List available bundled example datasets | `akw examples list` |
| `akw examples load` | Hydrate example knowledge bases into workspaces | `akw examples load --reset` |
| `akw reset` | Wipe all databases, files, and workspaces | `akw reset --force` |

---

## 🌐 REST & SSE API Reference

The FastAPI service powers both the web frontend and headless integrations:

### Workspace Endpoints
- `GET /api/workspaces`: List all project workspaces with live document and chunk counts.
- `GET /api/workspaces/active`: Retrieve the currently active workspace.
- `POST /api/workspaces`: Create a new discrete workspace.
- `POST /api/workspaces/{id}/switch`: Seamlessly hot-swap the active database.
- `DELETE /api/workspaces/{id}`: Delete a workspace and its SQLite database.
- `GET /api/workspaces/examples/list`: List available example datasets.
- `POST /api/workspaces/examples/{id}/load`: Hydrate an example dataset.
- `POST /api/workspaces/examples/reset-all`: Reset all workspaces to fresh example sets.

### Knowledge Base & Staging Endpoints
- `POST /api/kb/tasks/stage`: Upload file and trigger background parsing.
- `GET /api/kb/tasks`: List active and completed background parsing tasks.
- `GET /api/kb/staging/{doc_id}`: Fetch staged chunks for curation.
- `POST /api/kb/staging/{doc_id}/commit`: Commit curated chunks to the active SQLite DB.
- `GET /api/kb/documents`: List all ingested documents in the active workspace.
- `GET /api/kb/documents/{id}/download`: Download the original source file.
- `DELETE /api/kb/documents/{id}`: Delete document and cascade chunks.
- `GET /api/assets/{filename}`: Serve extracted diagrams and figures.

### Chat & Streaming Endpoints
- `POST /api/chat/sessions`: Create a new grounded conversation session.
- `GET /api/chat/sessions`: List conversation sessions.
- `POST /api/chat/sessions/{id}/messages`: Query session and stream tokens via Server-Sent Events (SSE).

---

## ⚙️ Configuration Reference

Configure `akw` via environment variables or runtime parameters in `AKWConfig`:

| Environment Variable | Default | Description |
| :--- | :--- | :--- |
| `AKW_DB_PATH` | `./knowledge_base.sqlite` | Active SQLite database path |
| `AKW_ASSETS_DIR` | `./knowledge_assets` | Directory storing extracted figures and diagrams |
| `AKW_FILES_DIR` | `./knowledge_files` | Directory storing archived original uploaded files |
| `AKW_WORKSPACES_DIR` | `./workspaces` | Directory managing discrete project workspaces |
| `AKW_EMBEDDING_PROVIDER` | `sentence_transformers` | Dense embedding provider (`sentence_transformers` or `ollama`) |
| `AKW_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Dense embedding model repository or tag |
| `AKW_RERANKER_PROVIDER` | `flashrank` | Local reranker engine (`flashrank` or `none`) |
| `AKW_HYDE_ENABLED` | `true` | Enable hypothetical document query expansions |
| `AKW_HELPER_LLM_PROVIDER` | `lmstudio` | Helper model provider for HyDE (`lmstudio` or `gemini`) |
| `AKW_HELPER_LLM_MODEL` | `qwen/qwen3.5-9b` | Helper model identifier |
| `AKW_LMSTUDIO_HOST` | `http://localhost:1234/v1` | LM Studio OpenAI-compatible endpoint |
| `AKW_VISION_ENABLED` | `true` | Extract and describe figures with Vision LLM |
| `GEMINI_API_KEY` | *(None)* | Google Gemini API key |

---

## 📁 Repository Structure

```
AI_knowledge_wrapper/
├── docs/                       # Comprehensive engineering & architectural specs
│   ├── ARCHITECTURE.md
│   ├── INGESTION_AND_STORAGE_SPEC.md
│   ├── RETRIEVAL_AND_RAG_SPEC.md
│   ├── API_AND_SESSION_SPEC.md
│   ├── FRONTEND_SPEC.md
│   └── ROADMAP_AND_IMPLEMENTATION_PLAN.md
├── examples/                   # Pre-configured example knowledge bases & scripts
│   ├── datasets/
│   │   ├── project_apollo/     # Aerospace avionics example (docx, pptx, md, diagram)
│   │   └── bionexus_diagnostics/ # Clinical genomics example (docx, pptx, md, diagram)
│   ├── generate_sample_datasets.py
│   └── load_examples.py
├── server/                     # FastAPI backend application
│   ├── app.py
│   ├── dependencies.py
│   └── routers/
│       ├── chat.py
│       ├── documents.py
│       ├── system.py
│       ├── tasks.py
│       └── workspaces.py
├── src/akw/                    # Core Python library
│   ├── chunking/               # Breadcrumb tracking & semantic window chunker
│   ├── core/                   # Configuration, models, and workspace manager
│   ├── embeddings/             # SentenceTransformers & Ollama embeddings
│   ├── examples/               # Example dataset hydration manager
│   ├── parsers/                # PDF, DOCX, PPTX, Excel, HTML, Markdown parsers
│   ├── retrieval/              # Hybrid BM25 + dense search & FlashRank reranker
│   ├── sessions/               # Grounded Gemini & Local LLM RAG sessions
│   ├── storage/                # SQLite FTS5 database and asset manager
│   ├── cli.py                  # CLI command entry point
│   └── kb.py                   # High-level KnowledgeBase orchestrator
├── web/                        # Vite + React + Tailwind dual-view web app
│   ├── src/
│   │   ├── components/         # WorkspaceSelector, SourceDrawer, ProgressTicker, etc.
│   │   ├── views/              # ChatView and KnowledgeView
│   │   └── api.ts
└── tests/                      # Pytest test suite (27 unit & integration tests)
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
