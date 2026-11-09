import React from 'react';
import { MessageSquare, Database, Layers, Sparkles, Settings } from 'lucide-react';
import { StagedDocument, SystemStatus, TaskRecord, WorkspaceInfo } from '../types';
import { TaskTicker } from './TaskTicker';
import { WorkspaceSelector } from './WorkspaceSelector';

interface HeaderProps {
  currentView: 'chat' | 'knowledge';
  onViewChange: (view: 'chat' | 'knowledge') => void;
  status: SystemStatus | null;
  tasks: TaskRecord[];
  activeWorkspace: WorkspaceInfo | null;
  onWorkspaceChanged: (ws: WorkspaceInfo) => void;
  onOpenStagedDoc: (doc: StagedDocument) => void;
  onClearCompletedTasks: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onViewChange,
  status,
  tasks,
  activeWorkspace,
  onWorkspaceChanged,
  onOpenStagedDoc,
  onClearCompletedTasks,
  onOpenSettings,
}) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between z-20 shrink-0">
      {/* Brand & Workspace Selector */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-base text-slate-100 flex items-center gap-2">
              AI Knowledge Wrapper
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Local RAG
              </span>
            </h1>
            <p className="text-xs text-slate-400">Grounded local knowledge with Gemini & local LLMs</p>
          </div>
        </div>

        {/* Project Knowledge Base Workspace Selector */}
        <WorkspaceSelector
          activeWorkspace={activeWorkspace}
          onWorkspaceChanged={onWorkspaceChanged}
        />
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
        <button
          onClick={() => onViewChange('chat')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
            currentView === 'chat'
              ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat Workspace
        </button>

        <button
          onClick={() => onViewChange('knowledge')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
            currentView === 'knowledge'
              ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
          }`}
        >
          <Database className="w-4 h-4" />
          Knowledge Base
          {status && (
            <span className="ml-1 text-xs px-1.5 py-0.2 rounded-full bg-slate-900/60 text-slate-300">
              {status.total_documents}
            </span>
          )}
        </button>
      </nav>

      {/* Right Area: Task Progress Ticker & System Metrics */}
      <div className="flex items-center gap-4">
        {/* Background Task Ticker */}
        <TaskTicker
          tasks={tasks}
          onOpenStagedDoc={onOpenStagedDoc}
          onClearCompleted={onClearCompletedTasks}
        />

        {/* System Metrics Pill */}
        {status && (
          <div className="hidden lg:flex items-center gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-1.5 bg-slate-800/50 border border-slate-800 px-3 py-1.5 rounded-lg">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>SQLite: <strong className="text-slate-300">{status.db_size_mb} MB</strong></span>
              <span className="text-slate-600">|</span>
              <span>Chunks: <strong className="text-slate-300">{status.total_chunks}</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-500">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span className="truncate max-w-[140px]" title={status.embedding_model}>
                {status.embedding_model.split('/').pop()}
              </span>
            </div>
          </div>
        )}
        {/* Settings Cog */}
        <button
          onClick={onOpenSettings}
          className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/60 text-slate-400 hover:text-slate-100 hover:bg-slate-700/80 transition-colors"
          title="System & Model Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
