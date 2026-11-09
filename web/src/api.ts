import {
  ChatSession,
  ChatMessage,
  Citation,
  Document,
  ExpandedContextBlock,
  ModelOption,
  SystemStatus,
  Chunk,
  StagedDocument,
  CommitChunksRequest,
  TaskRecord,
  SystemSettings,
  WorkspaceInfo,
} from './types';

const API_BASE = '/api';

export async function startStageTask(file: File): Promise<TaskRecord> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/kb/tasks/stage`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Task initiation failed' }));
    throw new Error(err.detail || 'Failed to start background parsing task');
  }
  return res.json();
}

export async function fetchTasks(): Promise<TaskRecord[]> {
  const res = await fetch(`${API_BASE}/kb/tasks`);
  if (!res.ok) throw new Error('Failed to fetch tasks');
  return res.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskRecord> {
  const res = await fetch(`${API_BASE}/kb/tasks/${taskId}`);
  if (!res.ok) throw new Error('Failed to fetch task status');
  return res.json();
}

export async function clearCompletedTasks(): Promise<void> {
  await fetch(`${API_BASE}/kb/tasks/completed`, { method: 'DELETE' });
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/system/status`);
  if (!res.ok) throw new Error('Failed to fetch system status');
  return res.json();
}

export async function fetchSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/system/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(settings: Partial<SystemSettings>): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/system/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update settings' }));
    throw new Error(err.detail || 'Failed to update settings');
  }
  return res.json();
}

export async function fetchWorkspaces(): Promise<WorkspaceInfo[]> {
  const res = await fetch(`${API_BASE}/workspaces`);
  if (!res.ok) throw new Error('Failed to fetch workspaces');
  return res.json();
}

export async function fetchActiveWorkspace(): Promise<WorkspaceInfo> {
  const res = await fetch(`${API_BASE}/workspaces/active`);
  if (!res.ok) throw new Error('Failed to fetch active workspace');
  return res.json();
}

export async function switchWorkspace(workspaceId: string): Promise<WorkspaceInfo> {
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/switch`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to switch workspace' }));
    throw new Error(err.detail || 'Failed to switch workspace');
  }
  return res.json();
}

export async function createWorkspace(name: string, description?: string): Promise<WorkspaceInfo> {
  const res = await fetch(`${API_BASE}/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create workspace' }));
    throw new Error(err.detail || 'Failed to create workspace');
  }
  return res.json();
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete workspace' }));
    throw new Error(err.detail || 'Failed to delete workspace');
  }
}

export async function fetchExampleDatasets(): Promise<import('./types').ExampleDatasetInfo[]> {
  const res = await fetch(`${API_BASE}/workspaces/examples/list`);
  if (!res.ok) throw new Error('Failed to fetch example datasets');
  return res.json();
}

export async function loadExampleWorkspace(
  exampleId: string,
  reset: boolean = false
): Promise<WorkspaceInfo> {
  const res = await fetch(`${API_BASE}/workspaces/examples/${exampleId}/load?reset=${reset}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to load example workspace' }));
    throw new Error(err.detail || 'Failed to load example workspace');
  }
  return res.json();
}

export async function resetAllExamples(): Promise<WorkspaceInfo[]> {
  const res = await fetch(`${API_BASE}/workspaces/examples/reset-all`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to reset examples' }));
    throw new Error(err.detail || 'Failed to reset examples');
  }
  return res.json();
}

export async function fetchDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/kb/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export function getDocumentDownloadUrl(documentId: string): string {
  return `${API_BASE}/kb/documents/${documentId}/download`;
}

export async function fetchDocumentDetails(
  id: string
): Promise<{ document: Document; chunks: Chunk[] }> {
  const res = await fetch(`${API_BASE}/kb/documents/${id}`);
  if (!res.ok) throw new Error('Failed to fetch document details');
  return res.json();
}

export async function stageDocument(file: File): Promise<StagedDocument> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/kb/stage`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Staging failed' }));
    throw new Error(err.detail || 'Failed to parse and stage document');
  }
  return res.json();
}

export async function commitStagedChunks(
  payload: CommitChunksRequest
): Promise<Document> {
  const res = await fetch(`${API_BASE}/kb/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Commit failed' }));
    throw new Error(err.detail || 'Failed to commit chunks to knowledge base');
  }
  return res.json();
}

export async function uploadDocuments(files: File[]): Promise<Document[]> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));

  const res = await fetch(`${API_BASE}/kb/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/kb/documents/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function updateChunk(
  chunkId: string,
  content: string,
  breadcrumb_display?: string
): Promise<Chunk> {
  const res = await fetch(`${API_BASE}/kb/chunks/${chunkId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, breadcrumb_display }),
  });
  if (!res.ok) throw new Error('Failed to update chunk');
  return res.json();
}

export async function deleteChunk(chunkId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/kb/chunks/${chunkId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete chunk');
}

export async function deleteChunksBatch(chunkIds: string[]): Promise<void> {
  const res = await fetch(`${API_BASE}/kb/chunks/batch-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chunk_ids: chunkIds }),
  });
  if (!res.ok) throw new Error('Failed to batch delete chunks');
}

export async function searchDiagnostic(
  query: string,
  top_k = 3,
  expand_window = 2
): Promise<{ query: string; context_blocks: ExpandedContextBlock[]; citations: Citation[] }> {
  const res = await fetch(`${API_BASE}/kb/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k, expand_window }),
  });
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function fetchModels(): Promise<ModelOption[]> {
  const res = await fetch(`${API_BASE}/chat/models`);
  if (!res.ok) throw new Error('Failed to fetch models');
  return res.json();
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/chat/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function createSession(data: {
  title?: string;
  model_provider: string;
  model_name?: string;
}): Promise<ChatSession> {
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function fetchSessionDetails(
  id: string
): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const res = await fetch(`${API_BASE}/chat/sessions/${id}`);
  if (!res.ok) throw new Error('Failed to fetch session messages');
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/sessions/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete session');
}

export function streamChatMessage(
  sessionId: string,
  message: string,
  top_k: number,
  expand_window: number,
  callbacks: {
    onStatus?: (step: string, message: string) => void;
    onSources?: (citations: Citation[], contextBlocks: ExpandedContextBlock[]) => void;
    onToken?: (token: string) => void;
    onDone?: (messageId: string, citations: Citation[]) => void;
    onError?: (error: string) => void;
  }
) {
  const controller = new AbortController();

  fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ message, top_k, expand_window }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error('ReadableStream not supported');

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            currentEvent = 'message';
            continue;
          }
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.slice(5).trim();
            try {
              const payload = JSON.parse(jsonStr);

              if (currentEvent === 'status' || payload.type === 'status') {
                const s = payload.data || {};
                callbacks.onStatus?.(s.step || '', s.message || '');
              } else if (currentEvent === 'sources' || payload.type === 'sources') {
                callbacks.onSources?.(payload.data || [], payload.context_blocks || []);
              } else if (currentEvent === 'token' || payload.type === 'token') {
                callbacks.onToken?.(payload.data || '');
              } else if (currentEvent === 'done' || payload.type === 'done') {
                callbacks.onDone?.(payload.data?.message_id || '', payload.data?.citations || []);
              } else if (currentEvent === 'error') {
                callbacks.onError?.(payload.error || 'Stream error');
              }
            } catch (e) {
              console.warn('Failed to parse SSE payload', jsonStr);
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError?.(err.message || 'Stream connection error');
      }
    });

  return () => controller.abort();
}
