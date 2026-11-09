import React from 'react';
import { Sparkles, X, ChevronRight, CheckCircle2 } from 'lucide-react';
import { StagedDocument } from '../types';

interface ToastNotificationProps {
  notification: {
    id: string;
    filename: string;
    chunkCount: number;
    stagedDoc: StagedDocument;
  } | null;
  onReview: (doc: StagedDocument) => void;
  onDismiss: () => void;
}

export const ToastNotification: React.FC<ToastNotificationProps> = ({
  notification,
  onReview,
  onDismiss,
}) => {
  if (!notification) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md w-full bg-slate-900 border border-emerald-500/40 rounded-2xl shadow-2xl p-4 animate-fade-in flex items-start gap-3.5 backdrop-blur-md">
      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
        <CheckCircle2 className="w-5 h-5" />
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
            Document Ready for Review
          </h4>
          <button
            onClick={onDismiss}
            className="p-1 rounded text-slate-400 hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300">
          <strong className="text-emerald-400">{notification.filename}</strong> has finished parsing (
          {notification.chunkCount} chunks generated).
        </p>

        <div className="pt-2 flex items-center gap-2">
          <button
            onClick={() => onReview(notification.stagedDoc)}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Review Chunks
          </button>
          <button
            onClick={onDismiss}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

