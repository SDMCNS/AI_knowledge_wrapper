import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileText,
  Trash2,
  Search,
  Eye,
  CheckCircle,
  X,
  FileSpreadsheet,
  FileCode,
  Layers,
  Database,
  ChevronRight,
  Sparkles,
  Edit3,
  Check,
  Plus,
  Scissors,
  AlertTriangle,
  RotateCcw,
  Presentation,
  ExternalLink,
  Download,
} from 'lucide-react';
import {
  Chunk,
  Document,
  ExpandedContextBlock,
  StagedChunk,
  StagedDocument,
} from '../types';
import {
  fetchDocuments,
  startStageTask,
  commitStagedChunks,
  deleteDocument,
  fetchDocumentDetails,
  updateChunk,
  deleteChunk,
  deleteChunksBatch,
  searchDiagnostic,
  getDocumentDownloadUrl,
} from '../api';

interface KnowledgeViewProps {
  onInspectBlock: (block: ExpandedContextBlock) => void;
  onRefreshStatus: () => void;
  activeStagedDoc?: StagedDocument | null;
  onClearActiveStagedDoc?: () => void;
}

const extractImageUrl = (content: string, metadata?: Record<string, any>): string | null => {
  if (metadata?.image_url) return metadata.image_url;
  const match = content.match(/!\[.*?\]\((.*?)\)/);
  return match ? match[1] : null;
};

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({
  onInspectBlock,
  onRefreshStatus,
  activeStagedDoc,
  onClearActiveStagedDoc,
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Staged Document for Review & Curation
  const [stagedDoc, setStagedDoc] = useState<StagedDocument | null>(null);

  // Sync with prop from toast/ticker
  useEffect(() => {
    if (activeStagedDoc) {
      setStagedDoc(activeStagedDoc);
    }
  }, [activeStagedDoc]);

  // Existing Document Chunks Inspector Modal
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [docChunks, setDocChunks] = useState<Chunk[]>([]);
  const [selectedChunkIds, setSelectedChunkIds] = useState<Set<string>>(new Set());
  const [editingChunkId, setEditingChunkId] = useState<string | null>(null);
  const [editChunkText, setEditChunkText] = useState<string>('');
  const [editChunkBreadcrumb, setEditChunkBreadcrumb] = useState<string>('');
  const [isLoadingChunks, setIsLoadingChunks] = useState<boolean>(false);

  // Diagnostic Sandbox State
  const [sandboxQuery, setSandboxQuery] = useState<string>('');
  const [sandboxResults, setSandboxResults] = useState<ExpandedContextBlock[]>([]);
  const [isSearchingSandbox, setIsSearchingSandbox] = useState<boolean>(false);

  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      onRefreshStatus();
    } catch (e) {
      console.error('Failed to load documents', e);
    }
  };

  // 1. Initial File Stage (Non-blocking background parsing)
  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    setStatusMessage(`Started background parsing for '${file.name}'. Track progress in the header ticker!`);

    try {
      await startStageTask(file);
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (err: any) {
      setStatusMessage(`Error starting task: ${err.message}`);
    }
  };

  // Staging Curation Actions
  const toggleRetainChunk = (index: number) => {
    if (!stagedDoc) return;
    const updated = [...stagedDoc.chunks];
    updated[index].is_retained = !updated[index].is_retained;
    setStagedDoc({ ...stagedDoc, chunks: updated });
  };

  const handleUpdateStagedChunkContent = (index: number, newContent: string) => {
    if (!stagedDoc) return;
    const updated = [...stagedDoc.chunks];
    updated[index].content = newContent;
    updated[index].token_count = Math.max(1, Math.round(newContent.length / 4));
    updated[index].is_modified = true;
    setStagedDoc({ ...stagedDoc, chunks: updated });
  };

  const handleUpdateStagedChunkBreadcrumb = (index: number, newBc: string) => {
    if (!stagedDoc) return;
    const updated = [...stagedDoc.chunks];
    updated[index].breadcrumb_display = newBc;
    updated[index].is_modified = true;
    setStagedDoc({ ...stagedDoc, chunks: updated });
  };

  const handleDeleteStagedChunk = (index: number) => {
    if (!stagedDoc) return;
    const updated = stagedDoc.chunks.filter((_, idx) => idx !== index);
    setStagedDoc({ ...stagedDoc, chunks: updated });
  };

  const handleAddStagedChunk = (afterIndex: number) => {
    if (!stagedDoc) return;
    const prevChunk = stagedDoc.chunks[afterIndex];
    const newChunk: StagedChunk = {
      staging_id: `custom_${Date.now()}`,
      chunk_index: afterIndex + 1,
      content: 'Custom chunk text...',
      breadcrumb_display: prevChunk ? prevChunk.breadcrumb_display : stagedDoc.filename,
      token_count: 5,
      is_retained: true,
      is_modified: true,
    };
    const updated = [...stagedDoc.chunks];
    updated.splice(afterIndex + 1, 0, newChunk);
    setStagedDoc({ ...stagedDoc, chunks: updated });
  };

  // Commit Reviewed Chunks to SQLite
  const handleCommitStaged = async () => {
    if (!stagedDoc) return;
    const retained = stagedDoc.chunks.filter((c) => c.is_retained && c.content.trim());
    if (retained.length === 0) {
      alert('You must retain at least one chunk to commit this document.');
      return;
    }

    setIsProcessing(true);
    setStatusMessage(`Embedding and committing ${retained.length} curated chunk(s)...`);

    try {
      await commitStagedChunks({
        staging_id: stagedDoc.staging_id,
        filename: stagedDoc.filename,
        sha256_hash: stagedDoc.sha256_hash,
        mime_type: stagedDoc.mime_type,
        file_size_bytes: stagedDoc.file_size_bytes,
        chunks: stagedDoc.chunks,
      });
      setStagedDoc(null);
      setStatusMessage('Document successfully added to Knowledge Base!');
      loadDocs();
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: any) {
      setStatusMessage(`Commit error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Document Management
  const handleDeleteDoc = async (docId: string, filename: string) => {
    if (!confirm(`Delete '${filename}' and all associated chunks and vectors?`)) return;
    try {
      await deleteDocument(docId);
      loadDocs();
    } catch (e) {
      console.error('Delete error', e);
    }
  };

  const handleInspectChunks = async (doc: Document) => {
    setSelectedDoc(doc);
    setIsLoadingChunks(true);
    setEditingChunkId(null);
    setSelectedChunkIds(new Set());
    try {
      const res = await fetchDocumentDetails(doc.id);
      setDocChunks(res.chunks);
    } catch (e) {
      console.error('Load chunks error', e);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const toggleSelectChunk = (chunkId: string) => {
    setSelectedChunkIds((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  };

  const toggleSelectAllChunks = () => {
    if (selectedChunkIds.size === docChunks.length) {
      setSelectedChunkIds(new Set());
    } else {
      setSelectedChunkIds(new Set(docChunks.map((c) => c.id)));
    }
  };

  const handleBatchDeleteChunks = async () => {
    if (selectedChunkIds.size === 0) return;
    const count = selectedChunkIds.size;
    if (!confirm(`Are you sure you want to delete ${count} selected chunk(s)?`)) return;

    try {
      await deleteChunksBatch(Array.from(selectedChunkIds));
      setDocChunks((prev) => prev.filter((c) => !selectedChunkIds.has(c.id)));
      setSelectedChunkIds(new Set());
      loadDocs();
    } catch (e) {
      alert('Failed to delete selected chunks');
    }
  };

  const handleSaveChunkEdit = async (chunkId: string) => {
    try {
      const updated = await updateChunk(chunkId, editChunkText, editChunkBreadcrumb);
      setDocChunks((prev) => prev.map((c) => (c.id === chunkId ? updated : c)));
      setEditingChunkId(null);
    } catch (e) {
      alert('Failed to update chunk');
    }
  };

  const handleDeleteExistingChunk = async (chunkId: string) => {
    if (!confirm('Delete this chunk permanently?')) return;
    try {
      await deleteChunk(chunkId);
      setDocChunks((prev) => prev.filter((c) => c.id !== chunkId));
      loadDocs();
    } catch (e) {
      alert('Failed to delete chunk');
    }
  };

  const handleRunSandboxSearch = async () => {
    if (!sandboxQuery.trim()) return;
    setIsSearchingSandbox(true);
    try {
      const res = await searchDiagnostic(sandboxQuery, 3, 2);
      setSandboxResults(res.context_blocks);
    } catch (e) {
      console.error('Diagnostic search failed', e);
    } finally {
      setIsSearchingSandbox(false);
    }
  };

  const getFileBadge = (mime: string) => {
    if (mime.includes('presentation') || mime.includes('ppt')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/20">
          <Presentation className="w-3.5 h-3.5" />
          Slides
        </span>
      );
    }
    if (mime.includes('sheet') || mime.includes('xls') || mime.includes('csv')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <FileSpreadsheet className="w-3.5 h-3.5" />
          Sheet
        </span>
      );
    }
    if (mime.includes('html') || mime.includes('code') || mime.includes('json') || mime.includes('yaml')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <FileCode className="w-3.5 h-3.5" />
          Code/Data
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
        <FileText className="w-3.5 h-3.5" />
        Document
      </span>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-6xl w-full mx-auto space-y-8 animate-fade-in pb-24">
      {/* Status Alert Banner */}
      {statusMessage && (
        <div className="p-4 rounded-xl bg-indigo-950/60 border border-indigo-500/40 text-sm text-indigo-200 flex items-center justify-between shadow-lg shadow-indigo-950/40">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-pulse"></span>
            <span>{statusMessage}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* STAGE REVIEW MODE (When user dropped/uploaded a document) */}
      {stagedDoc ? (
        <section className="bg-slate-900 border border-indigo-500/40 rounded-2xl p-6 shadow-2xl space-y-6 animate-fade-in">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded text-[11px] uppercase font-bold tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Chunk Curation Studio
                </span>
                <h2 className="text-lg font-bold text-slate-100">{stagedDoc.filename}</h2>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Review generated chunks below. Remove useless fragments, edit text for clarity, adjust section breadcrumbs, and commit retained chunks.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  setStagedDoc(null);
                  onClearActiveStagedDoc?.();
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                Discard Draft
              </button>
              <button
                onClick={handleCommitStaged}
                disabled={isProcessing}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition-all"
              >
                <Check className="w-4 h-4" />
                Commit Retained Chunks ({stagedDoc.chunks.filter((c) => c.is_retained).length})
              </button>
            </div>
          </div>

          {/* Staged Chunks Cards */}
          <div className="space-y-4">
            {stagedDoc.chunks.map((chunk, idx) => (
              <div
                key={chunk.staging_id || idx}
                className={`p-5 rounded-xl border transition-all ${
                  chunk.is_retained
                    ? 'bg-slate-950 border-slate-800 shadow-sm'
                    : 'bg-slate-950/40 border-slate-900 opacity-40 line-through-text'
                }`}
              >
                {/* Chunk Header */}
                <div className="flex items-center justify-between text-xs pb-3 border-b border-slate-800/60 mb-3">
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-indigo-400">
                      Chunk #{idx + 1}
                    </span>
                    <span className="text-slate-500">{chunk.token_count} tokens</span>
                    {chunk.is_modified && (
                      <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-400 text-[10px] font-bold">
                        Edited
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleRetainChunk(idx)}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        chunk.is_retained
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20'
                      }`}
                    >
                      {chunk.is_retained ? '✓ Retained' : '✗ Excluded'}
                    </button>
                    <button
                      onClick={() => handleAddStagedChunk(idx)}
                      className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                      title="Insert new chunk after this"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteStagedChunk(idx)}
                      className="p-1 rounded hover:bg-rose-950/40 text-slate-500 hover:text-rose-400"
                      title="Delete chunk completely"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Editable Breadcrumb */}
                <div className="mb-3">
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Breadcrumb Hierarchy:
                  </label>
                  <input
                    type="text"
                    value={chunk.breadcrumb_display}
                    disabled={!chunk.is_retained}
                    onChange={(e) => handleUpdateStagedChunkBreadcrumb(idx, e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-sky-400 font-medium focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Extracted Figure Asset Preview */}
                {(() => {
                  const imageUrl = extractImageUrl(chunk.content, chunk.metadata);
                  if (!imageUrl) return null;
                  return (
                    <div className="mb-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-start gap-4">
                      <div className="relative group shrink-0 overflow-hidden rounded-lg">
                        <img
                          src={imageUrl}
                          alt="Extracted Figure"
                          className="w-36 h-28 object-contain rounded-lg border border-slate-700 bg-slate-950 p-1 shadow"
                        />
                        <a
                          href={imageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded-lg transition-opacity text-xs font-semibold text-white gap-1"
                        >
                          <ExternalLink className="w-3.5 h-3.5" /> Full View
                        </a>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-semibold flex items-center gap-1">
                            <Eye className="w-3 h-3" /> Graphical Figure Asset
                          </span>
                          <span className="text-[11px] text-slate-500 font-mono truncate">{imageUrl}</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed">
                          Extracted graphical schematic/figure saved in asset storage. Linked to chunk for multimodal review and retrieval citations.
                        </p>
                      </div>
                    </div>
                  );
                })()}

                {/* Editable Content */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Chunk Content:
                  </label>
                  <textarea
                    rows={Math.min(10, Math.max(3, chunk.content.split('\n').length))}
                    value={chunk.content}
                    disabled={!chunk.is_retained}
                    onChange={(e) => handleUpdateStagedChunkContent(idx, e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 font-sans leading-relaxed focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : (
        /* STANDARD UPLOAD DROPZONE */
        <section className="bg-slate-900/90 border-2 border-dashed border-slate-800 hover:border-indigo-500/80 rounded-2xl p-10 text-center transition-all shadow-sm">
          <input
            type="file"
            id="fileInput"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
          <label
            htmlFor="fileInput"
            className="cursor-pointer flex flex-col items-center justify-center space-y-4"
          >
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/10">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div>
              <span className="font-semibold text-base text-slate-100 hover:text-indigo-400 transition-colors">
                Upload Document to Review Chunks
              </span>
              <p className="text-xs text-slate-400 mt-1">
                Drag and drop files here to parse, inspect, edit, and curate chunks before indexing into SQLite
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-2 text-[11px] text-slate-500 font-mono">
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">PDF</span>
              <span className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 font-semibold">PPTX / PPT</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">DOCX</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">XLSX</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">CSV</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">HTML</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">Markdown</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60">Code & Text</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-400/90 pt-1">
              <Eye className="w-3.5 h-3.5" />
              <span>Vision analysis automatically extracts slide diagrams & figures</span>
            </div>
          </label>
        </section>
      )}

      {/* DOCUMENT LIBRARY TABLE */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-indigo-400" />
              Document Library
            </h2>
            <p className="text-xs text-slate-400">
              Files committed to local SQLite with breadcrumbs, FTS5 BM25, and dense embeddings
            </p>
          </div>
          <span className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {documents.length} document(s)
          </span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm text-slate-300 border-collapse">
            <thead className="bg-slate-800/60 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800 font-bold">
              <tr>
                <th className="py-3 px-5">Document</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Chunks</th>
                <th className="py-3 px-4">Indexed Date</th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 text-sm">
                    No documents committed yet. Upload a file above to review and add chunks.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-4 px-5 font-medium text-slate-100 flex items-center gap-3">
                      <span className="truncate max-w-sm" title={doc.filename}>
                        {doc.filename}
                      </span>
                    </td>
                    <td className="py-4 px-4">{getFileBadge(doc.mime_type)}</td>
                    <td className="py-4 px-4 text-xs text-slate-400 font-mono">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-4 px-4 text-xs font-mono font-bold text-indigo-400">
                      {doc.total_chunks} chunks
                    </td>
                    <td className="py-4 px-4 text-xs text-slate-400">
                      {new Date(doc.created_at).toLocaleDateString()} {new Date(doc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-4 px-5 text-right space-x-2">
                      <a
                        href={getDocumentDownloadUrl(doc.id)}
                        download={doc.filename}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors inline-flex items-center gap-1.5"
                        title={`Download original file: ${doc.filename}`}
                      >
                        <Download className="w-3.5 h-3.5 text-sky-400" />
                        Download
                      </a>
                      <button
                        onClick={() => handleInspectChunks(doc)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors inline-flex items-center gap-1.5"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect / Edit Chunks
                      </button>
                      <button
                        onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 text-xs font-semibold border border-slate-700 hover:border-rose-800 transition-colors inline-flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* DIAGNOSTIC SANDBOX */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            Retrieval Diagnostic Sandbox
          </h3>
          <p className="text-xs text-slate-400">
            Test how queries trigger HyDE, BM25, vector search, cross-encoder reranking, and ±2 contiguous chunk window expansion
          </p>
        </div>

        <div className="flex gap-3">
          <input
            type="text"
            value={sandboxQuery}
            onChange={(e) => setSandboxQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRunSandboxSearch()}
            placeholder="Type a test query (e.g. 'refund policy timeout values')..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={handleRunSandboxSearch}
            disabled={isSearchingSandbox || !sandboxQuery.trim()}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold flex items-center gap-2 transition-all shadow-md"
          >
            <Search className="w-4 h-4" />
            Test Search
          </button>
        </div>

        {/* Sandbox Results */}
        {sandboxResults.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Retrieved Context Blocks ({sandboxResults.length})
            </div>
            {sandboxResults.map((block) => (
              <div
                key={block.citation_id}
                className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-3"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sky-400 bg-sky-950/40 border border-sky-500/20 px-2.5 py-0.5 rounded-full">
                      {block.citation_id}
                    </span>
                    <strong className="text-slate-200">{block.document_name}</strong>
                    <span className="text-slate-600">|</span>
                    <span className="text-slate-400">{block.breadcrumb}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-emerald-400 font-bold">
                      Relevance: {(block.relevance_score * 100).toFixed(1)}%
                    </span>
                    <button
                      onClick={() => onInspectBlock(block)}
                      className="px-3 py-1 rounded bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-semibold"
                    >
                      Inspect Window ({block.chunks.length} chunks)
                    </button>
                  </div>
                </div>
                <div className="text-xs text-slate-300 font-mono bg-slate-900 p-3 rounded-lg border border-slate-800/80 whitespace-pre-wrap max-h-36 overflow-y-auto">
                  {block.merged_text}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* CHUNK INSPECTOR & INLINE EDITOR MODAL (For Committed Documents) */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-center justify-between shrink-0">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  Chunks: {selectedDoc.filename} ({docChunks.length} chunks)
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  View, select multiple chunks to batch delete, or edit content stored in SQLite
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Batch Actions Bar */}
                {docChunks.length > 0 && (
                  <button
                    onClick={toggleSelectAllChunks}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
                  >
                    {selectedChunkIds.size === docChunks.length ? 'Deselect All' : 'Select All'}
                  </button>
                )}

                {selectedChunkIds.size > 0 && (
                  <button
                    onClick={handleBatchDeleteChunks}
                    className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-rose-600/20 transition-all animate-fade-in"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete Selected ({selectedChunkIds.size})
                  </button>
                )}

                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {isLoadingChunks ? (
                <div className="text-center py-12 text-slate-500 text-sm">Loading chunks...</div>
              ) : (
                docChunks.map((chunk) => {
                  const isEditing = editingChunkId === chunk.id;
                  const isSelected = selectedChunkIds.has(chunk.id);

                  return (
                    <div
                      key={chunk.id}
                      className={`p-5 rounded-xl border transition-all ${
                        isSelected
                          ? 'bg-rose-950/20 border-rose-500/50 shadow-sm'
                          : 'bg-slate-950 border-slate-800'
                      } space-y-3`}
                    >
                      <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-800/60">
                        <div className="flex items-center gap-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectChunk(chunk.id)}
                            className="w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900 cursor-pointer"
                          />
                          <span className="font-mono text-indigo-400 font-bold">
                            Chunk #{chunk.chunk_index} ({chunk.id})
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-slate-500">{chunk.token_count} tokens</span>
                          {!isEditing ? (
                            <>
                              <button
                                onClick={() => {
                                  setEditingChunkId(chunk.id);
                                  setEditChunkText(chunk.content);
                                  setEditChunkBreadcrumb(chunk.breadcrumb_display);
                                }}
                                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteExistingChunk(chunk.id)}
                                className="p-1 text-slate-500 hover:text-rose-400"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleSaveChunkEdit(chunk.id)}
                                className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1"
                              >
                                <Check className="w-3.5 h-3.5" />
                                Save & Re-embed
                              </button>
                              <button
                                onClick={() => setEditingChunkId(null)}
                                className="px-2 py-1 rounded bg-slate-800 text-slate-400 hover:text-slate-200 text-xs"
                              >
                                Cancel
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {isEditing ? (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                              Breadcrumb:
                            </label>
                            <input
                              type="text"
                              value={editChunkBreadcrumb}
                              onChange={(e) => setEditChunkBreadcrumb(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-sky-400 font-medium"
                            />
                          </div>
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                              Content:
                            </label>
                            <textarea
                              rows={6}
                              value={editChunkText}
                              onChange={(e) => setEditChunkText(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 font-sans leading-relaxed"
                            />
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="text-xs font-semibold text-sky-400">
                            Breadcrumb: {chunk.breadcrumb_display || 'Root'}
                          </div>

                          {/* Figure Image Thumbnail */}
                          {(() => {
                            const imgUrl = extractImageUrl(chunk.content, chunk.metadata);
                            if (!imgUrl) return null;
                            return (
                              <div className="my-2 p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-3">
                                <img
                                  src={imgUrl}
                                  alt="Figure preview"
                                  className="w-20 h-16 object-contain rounded bg-slate-950 p-1 border border-slate-700"
                                />
                                <div className="text-xs">
                                  <span className="font-semibold text-indigo-400 flex items-center gap-1">
                                    <Eye className="w-3 h-3" /> Extracted Graphic Figure
                                  </span>
                                  <a
                                    href={imgUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[11px] text-sky-400 hover:underline flex items-center gap-1 mt-0.5"
                                  >
                                    <ExternalLink className="w-3 h-3" /> View Source Image Asset
                                  </a>
                                </div>
                              </div>
                            );
                          })()}

                          <div className="text-xs text-slate-300 font-sans leading-relaxed whitespace-pre-wrap">
                            {chunk.content}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
