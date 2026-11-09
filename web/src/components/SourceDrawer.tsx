import React from 'react';
import { X, FileText, ChevronRight, Check, Copy, ExternalLink, Bookmark, Eye, Download } from 'lucide-react';
import { ExpandedContextBlock } from '../types';

interface SourceDrawerProps {
  block: ExpandedContextBlock | null;
  onClose: () => void;
}

const extractImageUrl = (content: string, metadata?: Record<string, any>): string | null => {
  if (metadata?.image_url) return metadata.image_url;
  const match = content.match(/!\[.*?\]\((.*?)\)/);
  return match ? match[1] : null;
};

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ block, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  if (!block) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(block.merged_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const breadcrumbSegments = block.breadcrumb ? block.breadcrumb.split(' > ') : [block.document_name];

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col animate-fade-in">
      {/* Drawer Header */}
      <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-sky-500/10 text-sky-400 border border-sky-500/30">
            {block.citation_id}
          </span>
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <FileText className="w-4 h-4 text-slate-400" />
            <span className="truncate max-w-[280px]" title={block.document_name}>
              {block.document_name}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={`/api/kb/documents/${block.document_id}/download`}
            download={block.document_name}
            className="p-1.5 rounded-lg text-slate-400 hover:text-sky-400 hover:bg-slate-800 transition-colors"
            title={`Download original file: ${block.document_name}`}
          >
            <Download className="w-4 h-4" />
          </a>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Copy expanded text"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Breadcrumb & Metadata Banner */}
      <div className="px-6 py-3.5 bg-slate-800/40 border-b border-slate-800 text-xs">
        <div className="text-slate-400 mb-1.5 font-medium flex items-center gap-1.5">
          <Bookmark className="w-3.5 h-3.5 text-indigo-400" />
          Document Breadcrumb Path
        </div>
        <div className="flex flex-wrap items-center gap-1 text-slate-300 font-medium">
          {breadcrumbSegments.map((segment, idx) => (
            <React.Fragment key={idx}>
              <span className={`px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60 ${idx === breadcrumbSegments.length - 1 ? 'text-sky-300 font-semibold' : ''}`}>
                {segment}
              </span>
              {idx < breadcrumbSegments.length - 1 && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>

        <div className="mt-3 flex items-center gap-4 text-slate-400">
          {block.page_start && (
            <span>Page: <strong className="text-slate-200">{block.page_start}{block.page_end && block.page_end !== block.page_start ? ` - ${block.page_end}` : ''}</strong></span>
          )}
          <span>Relevance: <strong className="text-emerald-400">{(block.relevance_score * 100).toFixed(1)}%</strong></span>
          <span>Contiguous Window: <strong className="text-slate-200">{block.chunks.length} chunks</strong></span>
        </div>
      </div>

      {/* Contiguous Chunk Window Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="text-xs uppercase tracking-wider font-bold text-slate-400 flex items-center justify-between">
          <span>Surrounding Context (±2 Chunks)</span>
          <span className="text-[11px] font-normal text-slate-500">Seed matches highlighted</span>
        </div>

        {block.chunks.map((chunk) => {
          const isSeed = block.seed_indices.includes(chunk.chunk_index);
          const imageUrl = extractImageUrl(chunk.content, chunk.metadata);
          const displayText = chunk.content.replace(/!\[.*?\]\(.*?\)\n*/g, '').trim();

          return (
            <div
              key={chunk.id}
              className={`p-4 rounded-xl border transition-all ${
                isSeed
                  ? 'bg-sky-950/20 border-sky-500/50 shadow-sm shadow-sky-500/10'
                  : 'bg-slate-800/40 border-slate-800/80 text-slate-300 opacity-90'
              }`}
            >
              <div className="flex items-center justify-between text-xs mb-2">
                <span className={`font-mono font-medium ${isSeed ? 'text-sky-400 font-bold' : 'text-slate-400'}`}>
                  Chunk #{chunk.chunk_index} {isSeed ? '★ SEED MATCH' : '(Context Neighbor)'}
                </span>
                <span className="text-slate-500">{chunk.token_count} tokens</span>
              </div>

              {/* Render Extracted Figure if attached */}
              {imageUrl && (
                <div className="my-2 p-2.5 rounded-lg bg-slate-950/90 border border-slate-700/80">
                  <div className="relative group overflow-hidden rounded">
                    <img
                      src={imageUrl}
                      alt="Extracted Context Figure"
                      className="max-h-56 w-auto rounded object-contain mx-auto shadow"
                    />
                    <a
                      href={imageUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded transition-opacity text-xs font-semibold text-white gap-1"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> View Full Image
                    </a>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-[11px] text-slate-400 px-1">
                    <span className="flex items-center gap-1 text-indigo-400 font-medium">
                      <Eye className="w-3 h-3" /> Extracted Figure / Diagram
                    </span>
                    <a
                      href={imageUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sky-400 hover:underline flex items-center gap-1"
                    >
                      <ExternalLink className="w-3 h-3" /> Full Asset
                    </a>
                  </div>
                </div>
              )}

              <div className="text-sm font-sans leading-relaxed whitespace-pre-wrap select-text">
                {displayText || chunk.content}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

