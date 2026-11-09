import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { SourceDrawer } from './components/SourceDrawer';
import { ToastNotification } from './components/ToastNotification';
import { SettingsModal } from './components/SettingsModal';
import { ChatView } from './views/ChatView';
import { KnowledgeView } from './views/KnowledgeView';
import { ExpandedContextBlock, StagedDocument, SystemStatus, TaskRecord, WorkspaceInfo } from './types';
import { fetchSystemStatus, fetchTasks, clearCompletedTasks, fetchActiveWorkspace } from './api';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'chat' | 'knowledge'>('chat');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceInfo | null>(null);
  const [inspectedBlock, setInspectedBlock] = useState<ExpandedContextBlock | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  // Background Task Ticker & Notification States
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [activeNotification, setActiveNotification] = useState<{
    id: string;
    filename: string;
    chunkCount: number;
    stagedDoc: StagedDocument;
  } | null>(null);
  const [stagedDocToReview, setStagedDocToReview] = useState<StagedDocument | null>(null);

  // Set of task IDs for which notifications have already been triggered
  const notifiedTaskIds = useRef<Set<string>>(new Set());

  const refreshStatus = async () => {
    try {
      const [statusData, wsData] = await Promise.all([
        fetchSystemStatus(),
        fetchActiveWorkspace().catch(() => null),
      ]);
      setStatus(statusData);
      if (wsData) setActiveWorkspace(wsData);
    } catch (e) {
      console.warn('System status check failed', e);
    }
  };

  const handleWorkspaceChanged = (ws: WorkspaceInfo) => {
    setActiveWorkspace(ws);
    refreshStatus();
  };

  const pollTasks = async () => {
    try {
      const taskList = await fetchTasks();
      setTasks(taskList);

      // Check for newly completed tasks that haven't been notified yet
      for (const t of taskList) {
        if (t.status === 'completed' && t.result && !notifiedTaskIds.current.has(t.id)) {
          notifiedTaskIds.current.add(t.id);
          const staged = t.result as StagedDocument;
          setActiveNotification({
            id: t.id,
            filename: t.filename,
            chunkCount: staged.chunks?.length || 0,
            stagedDoc: staged,
          });
          // Refresh document counts in case documents were committed
          refreshStatus();
        }
      }
    } catch (e) {
      // Ignore background poll errors
    }
  };

  useEffect(() => {
    refreshStatus();
    pollTasks();

    const statusInterval = setInterval(refreshStatus, 15000);
    // Poll tasks faster (every 1.5s) to provide smooth ticker animation
    const tasksInterval = setInterval(pollTasks, 1500);

    return () => {
      clearInterval(statusInterval);
      clearInterval(tasksInterval);
    };
  }, []);

  const handleOpenStagedDoc = (doc: StagedDocument) => {
    setStagedDocToReview(doc);
    setCurrentView('knowledge');
    setActiveNotification(null);
  };

  const handleClearCompleted = async () => {
    try {
      await clearCompletedTasks();
      pollTasks();
    } catch (e) {
      console.error('Failed to clear completed tasks', e);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden select-none">
      {/* Top Header with Brand, Workspace Selector, Navigation Tabs, and Task Ticker */}
      <Header
        currentView={currentView}
        onViewChange={(view) => setCurrentView(view)}
        status={status}
        tasks={tasks}
        activeWorkspace={activeWorkspace}
        onWorkspaceChanged={handleWorkspaceChanged}
        onOpenStagedDoc={handleOpenStagedDoc}
        onClearCompletedTasks={handleClearCompleted}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Dual Views - keyed by activeWorkspace so views cleanly refresh on workspace swap */}
      <div className="flex-1 flex overflow-hidden">
        {currentView === 'chat' ? (
          <ChatView
            key={`chat_${activeWorkspace?.id || 'default'}`}
            onInspectBlock={(block) => setInspectedBlock(block)}
          />
        ) : (
          <KnowledgeView
            key={`kb_${activeWorkspace?.id || 'default'}`}
            onInspectBlock={(block) => setInspectedBlock(block)}
            onRefreshStatus={refreshStatus}
            activeStagedDoc={stagedDocToReview}
            onClearActiveStagedDoc={() => setStagedDocToReview(null)}
          />
        )}
      </div>

      {/* Slide-over Context Inspector Drawer */}
      <SourceDrawer
        block={inspectedBlock}
        onClose={() => setInspectedBlock(null)}
      />

      {/* System & Model Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSettingsSaved={refreshStatus}
      />

      {/* Non-blocking Floating Notification Toast when background parse finishes */}
      <ToastNotification
        notification={activeNotification}
        onReview={handleOpenStagedDoc}
        onDismiss={() => setActiveNotification(null)}
      />
    </div>
  );
};
export default App;
