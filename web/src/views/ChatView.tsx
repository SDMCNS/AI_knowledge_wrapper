import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Bot,
  User,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Sliders,
  AlertCircle,
  FileText,
  Cpu,
  Cloud,
} from 'lucide-react';
import {
  ChatMessage,
  ChatSession,
  Citation,
  ExpandedContextBlock,
  ModelOption,
} from '../types';
import {
  fetchModels,
  fetchSessions,
  createSession,
  fetchSessionDetails,
  deleteSession,
  streamChatMessage,
} from '../api';

interface ChatViewProps {
  onInspectBlock: (block: ExpandedContextBlock) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({ onInspectBlock }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gemini-3.8-flash');
  const [inputPrompt, setInputPrompt] = useState<string>('');

  // Streaming & Pipeline States
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamStatus, setStreamStatus] = useState<{ step: string; message: string } | null>(null);
  const [activeStreamingMessage, setActiveStreamingMessage] = useState<string>('');
  const [activeContextBlocks, setActiveContextBlocks] = useState<ExpandedContextBlock[]>([]);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  // Search Controls
  const [topK, setTopK] = useState<number>(3);
  const [expandWindow, setExpandWindow] = useState<number>(2);
  const [showSettings, setShowSettings] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load models and sessions on mount
  useEffect(() => {
    loadModelsAndSessions();
  }, []);

  const loadModelsAndSessions = async () => {
    try {
      const [fetchedModels, fetchedSessions] = await Promise.all([
        fetchModels(),
        fetchSessions(),
      ]);
      setModels(fetchedModels);
      setSessions(fetchedSessions);

      // Default to gemini-3.8-flash or qwen/qwen3.5-9b if available
      const preferred = fetchedModels.find(
        (m) => m.id === 'gemini-3.8-flash' || m.id === 'qwen/qwen3.5-9b'
      );
      const defaultModelId = preferred ? preferred.id : fetchedModels[0]?.id || 'gemini-3.8-flash';
      setSelectedModel(defaultModelId);

      if (fetchedSessions.length > 0) {
        selectSession(fetchedSessions[0].id);
      } else {
        handleNewSession(defaultModelId);
      }
    } catch (e) {
      console.error('Failed to load initial data', e);
    }
  };

  const selectSession = async (sessionId: string) => {
    try {
      const details = await fetchSessionDetails(sessionId);
      setActiveSession(details.session);
      setMessages(details.messages);
      setSelectedModel(details.session.model_name);
    } catch (e) {
      console.error('Failed to load session details', e);
    }
  };

  const handleNewSession = async (modelId?: string) => {
    const targetModel = modelId || selectedModel;
    const modelObj = models.find((m) => m.id === targetModel);
    const provider = modelObj ? modelObj.provider : 'gemini';

    try {
      const newSess = await createSession({
        title: 'New Conversation',
        model_provider: provider,
        model_name: targetModel,
      });
      setSessions((prev) => [newSess, ...prev]);
      setActiveSession(newSess);
      setMessages([]);
    } catch (e) {
      console.error('Failed to create new session', e);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (activeSession?.id === sessionId) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeStreamingMessage, streamStatus]);

  const handleSendMessage = () => {
    if (!inputPrompt.trim() || !activeSession || isStreaming) return;

    const query = inputPrompt.trim();
    setInputPrompt('');

    // Append user message to UI immediately
    const userMsg: ChatMessage = {
      id: `temp_user_${Date.now()}`,
      session_id: activeSession.id,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    setIsStreaming(true);
    setStreamStatus({ step: 'init', message: 'Starting pipeline...' });
    setActiveStreamingMessage('');
    setActiveContextBlocks([]);
    setActiveCitations([]);

    streamChatMessage(activeSession.id, query, topK, expandWindow, {
      onStatus: (step, msg) => {
        setStreamStatus({ step, message: msg });
      },
      onSources: (citations, contextBlocks) => {
        setActiveCitations(citations);
        setActiveContextBlocks(contextBlocks);
      },
      onToken: (token) => {
        setActiveStreamingMessage((prev) => prev + token);
      },
      onDone: (messageId, finalCitations) => {
        setIsStreaming(false);
        setStreamStatus(null);
        selectSession(activeSession.id);
      },
      onError: (err) => {
        setIsStreaming(false);
        setStreamStatus(null);
        alert(`Generation error: ${err}`);
      },
    });
  };

  // Render text with clickable [REF-X] citation badges
  const renderMessageContent = (
    text: string,
    contextBlocks?: ExpandedContextBlock[]
  ) => {
    // Split on citation tags [REF-X] and Markdown images ![alt](url)
    const tokens = text.split(/(\[REF-\d+\]|!\[.*?\]\(.*?\))/g);

    return (
      <div className="leading-relaxed whitespace-pre-wrap font-sans text-sm space-y-1">
        {tokens.map((token, idx) => {
          // Check for citation pill
          const refMatch = token.match(/^\[(REF-\d+)\]$/);
          if (refMatch) {
            const refId = refMatch[1];
            const targetBlock = contextBlocks?.find((b) => b.citation_id === refId);

            return (
              <button
                key={idx}
                onClick={() => {
                  if (targetBlock) onInspectBlock(targetBlock);
                }}
                className="citation-pill inline-flex"
                title={
                  targetBlock
                    ? `${targetBlock.document_name} > ${targetBlock.breadcrumb}`
                    : refId
                }
              >
                <span>{refId}</span>
              </button>
            );
          }

          // Check for Markdown Image
          const imgMatch = token.match(/^!\[(.*?)\]\((.*?)\)$/);
          if (imgMatch) {
            const alt = imgMatch[1] || 'Document Figure';
            const src = imgMatch[2];
            return (
              <div key={idx} className="my-2.5 p-2 rounded-xl bg-slate-950 border border-slate-800">
                <a href={src} target="_blank" rel="noopener noreferrer">
                  <img
                    src={src}
                    alt={alt}
                    className="max-h-72 w-auto object-contain rounded-lg mx-auto shadow-md hover:scale-[1.01] transition-transform"
                  />
                </a>
                <div className="mt-1 text-center text-[11px] text-slate-400 font-medium">
                  {alt}
                </div>
              </div>
            );
          }

          return <span key={idx}>{token}</span>;
        })}
      </div>
    );
  };

  const getProviderIcon = (provider: string) => {
    if (provider === 'gemini') {
      return <Cloud className="w-3.5 h-3.5 text-sky-400" />;
    }
    return <Cpu className="w-3.5 h-3.5 text-emerald-400" />;
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar - Sessions & Model Switcher */}
      <aside className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-800 space-y-4">
          <button
            onClick={() => handleNewSession()}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>

          {/* Model Switcher Dropdown */}
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
              Active LLM Model
            </label>
            <div className="relative">
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  handleNewSession(e.target.value);
                }}
                className="w-full bg-slate-950 border border-slate-700/80 rounded-xl text-xs py-2.5 px-3 text-slate-100 font-medium focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <optgroup label="Google Gemini 3.8 (Cloud)">
                  {models
                    .filter((m) => m.provider === 'gemini')
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                </optgroup>
                <optgroup label="LM Studio (Local / OpenAI-Compatible)">
                  {models
                    .filter((m) => m.provider === 'lmstudio')
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                </optgroup>
                <optgroup label="Ollama (Local)">
                  {models
                    .filter((m) => m.provider === 'ollama')
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                </optgroup>
              </select>
            </div>
          </div>
        </div>

        {/* Sessions History List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-3 py-1.5">
            Conversations
          </div>
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => selectSession(s.id)}
              className={`group flex items-center justify-between px-3.5 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                activeSession?.id === s.id
                  ? 'bg-slate-800 text-slate-100 font-semibold shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2 truncate pr-2">
                {getProviderIcon(s.model_provider)}
                <span className="truncate">{s.title}</span>
              </div>
              <button
                onClick={(e) => handleDeleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-500 transition-opacity"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Workspace */}
      <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
        {/* Chat Header Status */}
        {activeSession && (
          <div className="h-12 border-b border-slate-800/80 px-6 flex items-center justify-between text-xs text-slate-400 bg-slate-900/40">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-200">{activeSession.title}</span>
              <span className="text-slate-600">•</span>
              <span className="inline-flex items-center gap-1 text-slate-400">
                {getProviderIcon(activeSession.model_provider)}
                <strong className="text-slate-300 font-mono">{activeSession.model_name}</strong>
              </span>
            </div>

            <div className="flex items-center gap-4 text-[11px]">
              <span>Contiguous Window: <strong className="text-slate-200">±{expandWindow} Chunks</strong></span>
              <span>Top-K Seeds: <strong className="text-slate-200">{topK}</strong></span>
            </div>
          </div>
        )}

        {/* Chat Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6 max-w-4xl w-full mx-auto">
          {messages.length === 0 && !isStreaming && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 shadow-xl shadow-indigo-500/10">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-slate-200 mb-1">
                Grounded Local Knowledge Assistant
              </h3>
              <p className="text-sm max-w-md text-slate-400">
                Ask questions about your uploaded documents. Answers cite verified local sources with surrounding ±2 chunk context windows.
              </p>
            </div>
          )}

          {/* Messages Stream */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 animate-fade-in ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'model' && (
                <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shrink-0 shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl px-5 py-4 ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none shadow-md'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none shadow-sm'
                }`}
              >
                {/* Content */}
                {renderMessageContent(msg.content, msg.context_blocks)}

                {/* Grounded References Section */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-sky-400" />
                      Grounded References (±2 Chunks)
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((c) => {
                        const targetBlock = msg.context_blocks?.find(
                          (b) => b.citation_id === c.id
                        );
                        return (
                          <div
                            key={c.id}
                            onClick={() => {
                              if (targetBlock) onInspectBlock(targetBlock);
                            }}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-800 border border-slate-700/60 cursor-pointer text-xs transition-colors shadow-sm"
                          >
                            <span className="font-bold text-sky-400">{c.id}</span>
                            <span className="truncate max-w-[160px] text-slate-300">
                              {c.document_name}
                            </span>
                            <ExternalLink className="w-3 h-3 text-slate-500" />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-slate-700 flex items-center justify-center text-slate-200 shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {/* Active Streaming Message */}
          {isStreaming && (
            <div className="flex gap-4 justify-start animate-fade-in">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shrink-0">
                <Bot className="w-4 h-4" />
              </div>

              <div className="max-w-2xl rounded-2xl px-5 py-4 bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none space-y-3">
                {/* Status Stepper */}
                {streamStatus && (
                  <div className="flex items-center gap-2 text-xs text-sky-400 font-medium bg-sky-950/40 border border-sky-500/20 px-3 py-1.5 rounded-lg">
                    <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span>
                    <span>{streamStatus.message}</span>
                  </div>
                )}

                {/* Tokens */}
                {activeStreamingMessage ? (
                  renderMessageContent(activeStreamingMessage, activeContextBlocks)
                ) : (
                  <div className="text-xs text-slate-500 italic">
                    Retrieving context and preparing grounded response...
                  </div>
                )}

                {/* Live Citations during streaming */}
                {activeCitations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                      Retrieved References
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {activeCitations.map((c) => {
                        const targetBlock = activeContextBlocks.find(
                          (b) => b.citation_id === c.id
                        );
                        return (
                          <div
                            key={c.id}
                            onClick={() => {
                              if (targetBlock) onInspectBlock(targetBlock);
                            }}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 cursor-pointer text-xs"
                          >
                            <span className="font-bold text-sky-400">{c.id}</span>
                            <span className="truncate max-w-[160px] text-slate-300">
                              {c.document_name}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar & Controls */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur shrink-0">
          <div className="max-w-4xl mx-auto space-y-2">
            {/* Context Expansion Config Bar (Collapsible) */}
            {showSettings && (
              <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between text-xs text-slate-300 animate-fade-in shadow-lg">
                <div className="flex items-center gap-8">
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">
                      Top-K Seed Hits: <strong className="text-slate-100">{topK}</strong>
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={8}
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value))}
                      className="accent-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">
                      Window Expansion: <strong className="text-slate-100">±{expandWindow} Chunks</strong>
                    </label>
                    <input
                      type="range"
                      min={0}
                      max={4}
                      value={expandWindow}
                      onChange={(e) => setExpandWindow(Number(e.target.value))}
                      className="accent-indigo-500"
                    />
                  </div>
                </div>
                <div className="text-[11px] text-slate-400 max-w-xs text-right">
                  Seed chunks pull {expandWindow * 2 + 1} contiguous chunks from SQLite and merge overlapping intervals.
                </div>
              </div>
            )}

            {/* Main Prompt Input */}
            <div className="relative flex items-center">
              <textarea
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask anything about your local knowledge base..."
                rows={2}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-4 pr-24 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none shadow-sm"
              />

              <div className="absolute right-3 flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setShowSettings((prev) => !prev)}
                  className={`p-2 rounded-lg text-slate-400 hover:text-slate-200 transition-colors ${
                    showSettings ? 'bg-slate-800 text-indigo-400' : ''
                  }`}
                  title="Retrieval Settings"
                >
                  <Sliders className="w-4 h-4" />
                </button>

                <button
                  type="button"
                  onClick={handleSendMessage}
                  disabled={!inputPrompt.trim() || isStreaming}
                  className="p-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white shadow-md shadow-indigo-600/20 transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
