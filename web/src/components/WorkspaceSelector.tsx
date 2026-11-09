import React, { useState, useEffect, useRef } from 'react';
import {
  FolderKanban,
  ChevronDown,
  Plus,
  Check,
  Trash2,
  Database,
  Layers,
  Sparkles,
  RotateCcw,
  BookOpen,
  X,
  Loader2,
} from 'lucide-react';
import { WorkspaceInfo, ExampleDatasetInfo } from '../types';
import {
  fetchWorkspaces,
  switchWorkspace,
  createWorkspace,
  deleteWorkspace,
  fetchExampleDatasets,
  loadExampleWorkspace,
  resetAllExamples,
} from '../api';

interface WorkspaceSelectorProps {
  activeWorkspace: WorkspaceInfo | null;
  onWorkspaceChanged: (ws: WorkspaceInfo) => void;
}

export const WorkspaceSelector: React.FC<WorkspaceSelectorProps> = ({
  activeWorkspace,
  onWorkspaceChanged,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [exampleDatasets, setExampleDatasets] = useState<ExampleDatasetInfo[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newWsName, setNewWsName] = useState('');
  const [newWsDesc, setNewWsDesc] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingExamples, setIsLoadingExamples] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadWorkspaces();
    loadExampleList();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const loadWorkspaces = async () => {
    try {
      const list = await fetchWorkspaces();
      setWorkspaces(list);
    } catch (e) {
      console.warn('Failed to load workspaces', e);
    }
  };

  const loadExampleList = async () => {
    try {
      const list = await fetchExampleDatasets();
      setExampleDatasets(list);
    } catch (e) {
      console.warn('Failed to fetch example datasets', e);
    }
  };

  const handleSelectWorkspace = async (wsId: string) => {
    if (activeWorkspace?.id === wsId) {
      setIsOpen(false);
      return;
    }
    try {
      const switched = await switchWorkspace(wsId);
      onWorkspaceChanged(switched);
      await loadWorkspaces();
      setIsOpen(false);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to switch workspace');
    }
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await createWorkspace(newWsName.trim(), newWsDesc.trim());
      onWorkspaceChanged(created);
      setNewWsName('');
      setNewWsDesc('');
      setIsCreating(false);
      await loadWorkspaces();
      setIsOpen(false);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to create workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWorkspace = async (e: React.MouseEvent, wsId: string, name: string) => {
    e.stopPropagation();
    if (!confirm(`Delete project workspace '${name}'? This removes its discrete database.`)) return;

    try {
      await deleteWorkspace(wsId);
      const list = await fetchWorkspaces();
      setWorkspaces(list);
      // If we deleted the active one, refresh active
      const active = list.find((w) => w.is_active) || list[0];
      if (active) onWorkspaceChanged(active);
    } catch (e: any) {
      alert(e.message || 'Failed to delete workspace');
    }
  };

  const handleLoadExamples = async (reset: boolean = false) => {
    setIsLoadingExamples(true);
    setErrorMsg(null);
    try {
      if (reset) {
        if (!confirm('Reset all workspaces to fresh Project Apollo and BioNexus example knowledge bases?')) {
          setIsLoadingExamples(false);
          return;
        }
        const updated = await resetAllExamples();
        setWorkspaces(updated);
        const active = updated.find((w) => w.is_active) || updated[0];
        if (active) onWorkspaceChanged(active);
      } else {
        // Load both examples
        for (const ex of exampleDatasets) {
          await loadExampleWorkspace(ex.id, false);
        }
        const updated = await fetchWorkspaces();
        setWorkspaces(updated);
        const active = updated.find((w) => w.is_active) || updated[0];
        if (active) onWorkspaceChanged(active);
      }
      setIsOpen(false);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed loading examples');
    } finally {
      setIsLoadingExamples(false);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger Button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          loadWorkspaces();
          loadExampleList();
        }}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/80 border border-slate-700/80 text-xs font-semibold text-slate-200 shadow-sm transition-all"
        title="Switch active Knowledge Base workspace"
      >
        <div className="w-5 h-5 rounded-md bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
          <FolderKanban className="w-3.5 h-3.5" />
        </div>
        <span className="max-w-[130px] truncate">
          {activeWorkspace?.name || 'Default Project'}
        </span>
        <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900/80 text-slate-400 font-mono">
          {activeWorkspace?.document_count ?? 0} docs
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-2 w-84 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl z-50 overflow-hidden animate-fade-in flex flex-col">
          {/* Menu Header */}
          <div className="px-4 py-3 bg-slate-950/70 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Project Workspaces
              </h3>
              <p className="text-[11px] text-slate-500">
                Discrete SQLite databases per project
              </p>
            </div>
            {!isCreating && (
              <button
                onClick={() => setIsCreating(true)}
                className="px-2 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold flex items-center gap-1 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                New
              </button>
            )}
          </div>

          {/* Creation Form Popover */}
          {isCreating && (
            <form onSubmit={handleCreateWorkspace} className="p-3 bg-slate-950/90 border-b border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                <span>New Project Workspace</span>
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <input
                type="text"
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                placeholder="Project name (e.g. Apollo Telemetry)"
                autoFocus
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <input
                type="text"
                value={newWsDesc}
                onChange={(e) => setNewWsDesc(e.target.value)}
                placeholder="Optional description"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-2.5 py-1 rounded text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !newWsName.trim()}
                  className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create & Switch'}
                </button>
              </div>
            </form>
          )}

          {errorMsg && (
            <div className="px-4 py-2 bg-rose-500/10 text-rose-400 text-xs border-b border-rose-500/20">
              {errorMsg}
            </div>
          )}

          {/* Workspaces List */}
          <div className="max-h-60 overflow-y-auto divide-y divide-slate-800/60 p-1.5">
            {workspaces.map((ws) => {
              const isActive = activeWorkspace?.id === ws.id || ws.is_active;

              return (
                <div
                  key={ws.id}
                  onClick={() => handleSelectWorkspace(ws.id)}
                  className={`group p-2.5 rounded-xl cursor-pointer flex items-center justify-between transition-colors ${
                    isActive
                      ? 'bg-indigo-600/15 border border-indigo-500/30'
                      : 'hover:bg-slate-800/60'
                  }`}
                >
                  <div className="min-w-0 flex-1 pr-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-semibold truncate ${isActive ? 'text-indigo-400' : 'text-slate-200'}`}>
                        {ws.name}
                      </span>
                      {isActive && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                      )}
                    </div>
                    {ws.description && (
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">
                        {ws.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500 font-mono">
                      <span>{ws.document_count} docs</span>
                      <span>•</span>
                      <span>{ws.total_chunks} chunks</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {isActive ? (
                      <Check className="w-4 h-4 text-emerald-400" />
                    ) : ws.id !== 'default' ? (
                      <button
                        onClick={(e) => handleDeleteWorkspace(e, ws.id, ws.name)}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-950/40 text-slate-500 hover:text-rose-400 transition-all"
                        title="Delete project workspace"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Example Knowledge Bases Section */}
          <div className="p-3 bg-slate-950/80 border-t border-slate-800 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Example Datasets
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                Apollo & BioNexus
              </span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 pt-1">
              <button
                type="button"
                disabled={isLoadingExamples}
                onClick={() => handleLoadExamples(false)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium flex items-center justify-center gap-1.5 border border-slate-700 transition-colors disabled:opacity-50"
                title="Hydrate pre-configured example workspaces with figures"
              >
                {isLoadingExamples ? (
                  <Loader2 className="w-3 h-3 animate-spin text-indigo-400" />
                ) : (
                  <BookOpen className="w-3 h-3 text-indigo-400" />
                )}
                <span>Load Examples</span>
              </button>

              <button
                type="button"
                disabled={isLoadingExamples}
                onClick={() => handleLoadExamples(true)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium flex items-center justify-center gap-1.5 border border-slate-700 hover:border-amber-500/40 transition-colors disabled:opacity-50"
                title="Wipe all data and reload fresh Apollo and BioNexus examples"
              >
                <RotateCcw className="w-3 h-3 text-amber-400" />
                <span>Reset Clean</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
