# Frontend User Interface Specification (Dual View)

## 1. Overview

The UI is structured around two dedicated views designed for clarity, transparency, and high workflow efficiency:
- **View 1: Chat Workspace** (Conversational querying with Gemini or Local LLMs, real-time streaming, and interactive source citations).
- **View 2: Knowledge Base Management Station** (Document uploading, chunk inspection, embedding status, and a retrieval sandbox).

---

## 2. View 1: Chat Workspace

```
+--------------------------------------------------------------------------------------------------+
|  [Logo] AI Knowledge Wrapper     [Model: Gemini 2.5 Flash v] [Temp: 0.2]     [Knowledge: 14 docs]|
+---------------------------------------------------+----------------------------------------------+
|                                                   |  [x] Source Context Drawer                   |
|  User:                                            |                                              |
|  What are our SLA response times for Tier 1?      |  Citation: [REF-1]                           |
|                                                   |  File: Support_Contracts_2026.docx           |
|  Assistant:                                       |  Breadcrumb: Support Contracts > SLA > Tier1 |
|  For Tier 1 critical incidents, our guaranteed    |  Relevance Score: 0.962 (Cross-Encoder)      |
|  response time is within 15 minutes [REF-1].      |                                              |
|  For standard business hours inquiries, Tier 1    |  Contiguous Chunk Window (+/-2 Chunks):      |
|  requests are handled within 2 hours [REF-2].     |  +----------------------------------------+  |
|                                                   |  | [Chunk 12 - Preceding Context]         |  |
|  -- References --                                 |  | Support tiers are categorized by...    |  |
|  [REF-1] Support_Contracts_2026.docx > SLA        |  +----------------------------------------+  |
|  [REF-2] Customer_Handbook.pdf > Page 8           |  | [Chunk 13 - SEED MATCH]                |  |
|                                                   |  | >> Tier 1 response time: 15 minutes... |  |
|  +---------------------------------------------+  |  +----------------------------------------+  |
|  | Message Gemini or search knowledge base... |  |  | [Chunk 14 - Following Context]         |  |
|  +---------------------------------------------+  |  | Escalation procedures for Tier 1...    |  |
+---------------------------------------------------+----------------------------------------------+
```

### 2.1. Key Features
1. **Model Switcher**: Single-click toggle between:
   - **Google Gemini**: Gemini 2.5 Flash (default, fast & grounded), Gemini 2.5 Pro (complex reasoning).
   - **Local Models**: Auto-discovered models from local Ollama instances (`llama3.2`, `gemma2`, `mistral`, `qwen2.5`).
2. **Retrieval Pipeline Stepper**: When a query is submitted, a subtle status badge shows live execution stages:
   - `[1/4] HyDE`: Local LLM drafting hypothetical passage.
   - `[2/4] Hybrid Search`: BM25 + Vector candidate retrieval.
   - `[3/4] Reranking`: Cross-encoder scoring top matches.
   - `[4/4] Generating`: Streaming answer from Gemini.
3. **Interactive Citation Pills (`[REF-X]`)**:
   - Hovering displays a tooltip summary (document title, section, score).
   - Clicking slides open the **Source Context Drawer**.
4. **Source Context Drawer**:
   - Full document breadcrumb trail.
   - Page, sheet, or section number.
   - Exact text of the seed chunk highlighted with surrounding contiguous chunks ($\pm 2$) visibly bordered, providing total visibility into what the LLM was given.

---

## 3. View 2: Knowledge Base Management Station

```
+--------------------------------------------------------------------------------------------------+
|  [View: Knowledge Base Management]     [Stats: 18 Documents | 1,420 Chunks | SQLite: 42 MB]       |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   +------------------------------------------------------------------------------------------+   |
|   |                     DRAG & DROP FILES HERE OR CLICK TO BROWSE                            |   |
|   |         Supported: PDF, DOCX, XLSX, XLS, CSV, HTML, MD, TXT, JSON, YAML (Max: 100MB)       |   |
|   +------------------------------------------------------------------------------------------+   |
|                                                                                                  |
|  Document Library                                                    [Search documents: ________]|
|  +--------------------------------------------------------------------------------------------+  |
|  | Filename            | Type  | Size    | Chunks | Ingested Date       | Status    | Actions     |  |
|  |---------------------|-------|---------|--------|---------------------|-----------|-------------|  |
|  | Architecture.pdf    | PDF   | 2.4 MB  | 142    | 2026-11-09 16:30    | Indexed   | [Inspect] [x|  |
|  | Q3_Financials.xlsx  | XLSX  | 840 KB  | 48     | 2026-11-09 17:15    | Indexed   | [Inspect] [x|  |
|  | API_Spec.md         | MD    | 120 KB  | 18     | 2026-11-09 17:22    | Indexed   | [Inspect] [x|  |
|  +--------------------------------------------------------------------------------------------+  |
|                                                                                                  |
|  Retrieval Diagnostic Sandbox                                                                    |
|  +--------------------------------------------------------------------------------------------+  |
|  | Test Query: [ "database connection pooling settings"             ]  [Test Search]          |  |
|  | Results:                                                                                   |  |
|  | 1. API_Spec.md > Database > Pooling (Rerank: 0.941 | BM25: #2 | Dense: #1) [Preview Window]   |  |
|  | 2. Architecture.pdf > Storage > SQLite (Rerank: 0.812 | BM25: #1 | Dense: #6) [Preview Window] |  |
|  +--------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

### 3.1. Key Features
1. **Dropzone Ingestion**:
   - Multi-file drag and drop.
   - Real-time progress bar showing parsing, chunking, and vector embedding progress.
2. **Chunk Inspector Modal**:
   - Allows users to click **Inspect** on any document to browse all indexed chunks.
   - Displays the exact extracted breadcrumb, token count, and raw text for every chunk.
3. **Retrieval Diagnostic Sandbox**:
   - Allows power users to test queries without running an LLM.
   - Compares raw BM25 ranks against Dense Vector ranks and shows how the Cross-Encoder reorders results.
   - Displays how the $\pm 2$ neighbor window merges overlapping intervals.
4. **Document Controls**:
   - Re-index document (e.g., after changing embedding model).
   - Delete document (cascades automatically to chunks, FTS5 virtual tables, and vector tables).

