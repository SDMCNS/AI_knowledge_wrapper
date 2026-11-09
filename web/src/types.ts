export interface TaskRecord {
  id: string;
  task_type: string;
  filename: string;
  file_size_bytes: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  result?: StagedDocument;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface Document {
  id: string;
  filename: string;
  file_path?: string;
  sha256_hash: string;
  mime_type: string;
  file_size_bytes: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface Chunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  breadcrumb_display: string;
  breadcrumb_path: string[];
  page_start?: number;
  page_end?: number;
  token_count: number;
  metadata?: Record<string, any>;
}

export interface StagedChunk {
  staging_id: string;
  chunk_index: number;
  content: string;
  breadcrumb_display: string;
  breadcrumb_path?: string[];
  page_start?: number;
  page_end?: number;
  token_count: number;
  is_retained: boolean;
  is_modified?: boolean;
  metadata?: Record<string, any>;
}

export interface StagedDocument {
  staging_id: string;
  filename: string;
  sha256_hash: string;
  mime_type: string;
  file_size_bytes: number;
  chunks: StagedChunk[];
}

export interface CommitChunksRequest {
  staging_id: string;
  filename: string;
  sha256_hash: string;
  mime_type?: string;
  file_size_bytes: number;
  chunks: StagedChunk[];
  metadata?: Record<string, any>;
}

export interface Citation {
  id: string; // e.g. "REF-1"
  document_name: string;
  breadcrumb: string;
  page_start?: number;
  page_end?: number;
  score: number;
  excerpt: string;
}

export interface ExpandedContextBlock {
  citation_id: string;
  document_id: string;
  document_name: string;
  breadcrumb: string;
  page_start?: number;
  page_end?: number;
  seed_indices: number[];
  chunks: Chunk[];
  merged_text: string;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'model' | 'system';
  content: string;
  context_blocks?: ExpandedContextBlock[];
  citations?: Citation[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  system_instruction?: string;
  created_at: string;
  updated_at: string;
}

export interface ModelOption {
  id: string;
  name: string;
  provider: 'gemini' | 'lmstudio' | 'ollama';
  is_local: boolean;
}

export interface SystemStatus {
  db_path: string;
  db_size_mb: number;
  total_documents: number;
  total_chunks: number;
  embedding_model: string;
  reranker_model: string;
  hyde_enabled: boolean;
  window_expansion: number;
  gemini_configured: boolean;
}

export interface SystemSettings {
  helper_llm_provider: string;
  helper_llm_model: string;
  vision_enabled: boolean;
  vision_llm_provider: string;
  vision_llm_model: string;
  vision_timeout_seconds: number;
  hyde_enabled: boolean;
  hyde_model: string;
  lmstudio_host: string;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  description?: string;
  db_path: string;
  assets_dir: string;
  files_dir: string;
  is_active: boolean;
  document_count: number;
  total_chunks: number;
  created_at: string;
}

export interface ExampleDatasetInfo {
  id: string;
  name: string;
  description: string;
  tags: string[];
  sample_queries: string[];
  documents: string[];
  has_diagrams: boolean;
}
