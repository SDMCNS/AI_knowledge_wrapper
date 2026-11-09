import React, { useState } from 'react';
import { Loader2, CheckCircle2, AlertCircle, ChevronDown, Sparkles, X } from 'lucide-react';
import { StagedDocument, TaskRecord } from '../types';

interface TaskTickerProps {
  tasks: TaskRecord[];
  onOpenStagedDoc: (doc: StagedDocument) => void;
  onClearCompleted: () => void;
}

export const TaskTicker: React.FC<TaskTickerProps> = ({
  tasks,
  onOpenStagedDoc,
  onClearCompleted,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const activeTasks = tasks.filter((t) => t.status === 'processing' || t.status === 'queued');
  const completedUnopenedTasks = tasks.filter((t) => t.status === 'completed' && t.result);
  const failedTasks = tasks.filter((t) => t.status === 'failed');

  if (tasks.length === 0) return null;

  const currentActive = activeTasks[0];

  return (
    <div className="relative">
      {/* Ticker Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-800/90 border border-slate-700/80 hover:bg-slate-800 text-xs transition-all shadow-sm"
      >
        {activeTasks.length > 0 ? (
          <>
            <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />
            <div className="flex items-center gap-2 text-slate-200">
              <span className="font-semibold truncate max-w-[150px]">{currentActive.filename}</span>
              <span className="text-sky-400 font-mono font-bold">{currentActive.progress}%</span>
            </div>
            {/* Tiny progress bar */}
            <div className="w-12 h-1.5 rounded-full bg-slate-700 overflow-hidden">
              <div
                className="h-full bg-sky-400 transition-all duration-300"
                style={{ width: `${currentActive.progress}%` }}
              />
            </div>
          </>
        ) : completedUnopenedTasks.length > 0 ? (
          <>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-emerald-300 font-medium">
              {completedUnopenedTasks.length} document(s) ready
            </span>
          </>
        ) : failedTasks.length > 0 ? (
          <>
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-rose-300 font-medium">Task error</span>
          </>
        ) : (
          <span className="text-slate-400">Background Tasks</span>
        )}

        <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
      </button>

      {/* Dropdown Task List */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-3 z-50 animate-fade-in space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            <span>Background Tasks ({tasks.length})</span>
            {tasks.some((t) => t.status === 'completed' || t.status === 'failed') && (
              <button
                onClick={onClearCompleted}
                className="text-[10px] text-slate-400 hover:text-slate-200 underline"
              >
                Clear finished
              </button>
            )}
          </div>

          <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 truncate max-w-[170px]" title={task.filename}>
                    {task.filename}
                  </span>
                  {task.status === 'processing' && (
                    <span className="font-mono text-sky-400 font-bold">{task.progress}%</span>
                  )}
                  {task.status === 'completed' && (
                    <span className="text-emerald-400 font-semibold text-[11px] flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  )}
                  {task.status === 'failed' && (
                    <span className="text-rose-400 font-semibold text-[11px]">Failed</span>
                  )}
                </div>

                <div className="text-[11px] text-slate-400 truncate">{task.current_step}</div>

                {task.status === 'processing' && (
                  <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-sky-400 transition-all duration-300"
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>
                )}

                {task.status === 'completed' && task.result && (
                  <button
                    onClick={() => {
                      onOpenStagedDoc(task.result as StagedDocument);
                      setIsOpen(false);
                    }}
                    className="w-full mt-1 py-1 px-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Sparkles className="w-3 h-3" />
                    Review Chunks ({task.result.chunks?.length || 0})
                  </button>
                )}

                {task.error && (
                  <div className="text-[10px] text-rose-400 mt-1">{task.error}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

