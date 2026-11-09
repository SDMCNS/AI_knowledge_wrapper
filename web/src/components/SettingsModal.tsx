import React, { useState, useEffect } from 'react';
import { X, Cpu, Eye, Sparkles, Check, Server, AlertCircle } from 'lucide-react';
import { ModelOption, SystemSettings } from '../types';
import { fetchModels, fetchSettings, updateSettings } from '../api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsSaved?: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSettingsSaved,
}) => {
  const [settings, setSettings] = useState<SystemSettings>({
    helper_llm_provider: 'lmstudio',
    helper_llm_model: 'qwen/qwen3.5-9b',
    vision_enabled: true,
    vision_llm_provider: 'lmstudio',
    vision_llm_model: 'qwen/qwen3-vl-8b',
    vision_timeout_seconds: 45,
    hyde_enabled: true,
    hyde_model: 'qwen/qwen3.5-9b',
    lmstudio_host: 'http://localhost:1234/v1',
  });

  const [availableModels, setAvailableModels] = useState<ModelOption[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [currentSettings, models] = await Promise.all([
        fetchSettings(),
        fetchModels().catch(() => []),
      ]);
      setSettings(currentSettings);
      setAvailableModels(models);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      const updated = await updateSettings(settings);
      setSettings(updated);
      setSuccessMsg('Settings updated successfully!');
      onSettingsSaved?.();
      setTimeout(() => {
        setSuccessMsg(null);
        onClose();
      }, 1200);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">System & Model Configuration</h2>
              <p className="text-xs text-slate-400">Configure local helper LLM and vision model parameters</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-6 overflow-y-auto flex-1">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Section 1: Local Helper LLM */}
          <div className="space-y-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-slate-200">Local Helper LLM</h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-mono">
                HyDE & Query Expansion
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Used for generating hypothetical document passages (HyDE) and assisting with retrieval tasks.
            </p>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Provider</label>
                <select
                  value={settings.helper_llm_provider}
                  onChange={(e) => setSettings({ ...settings, helper_llm_provider: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="lmstudio">LM Studio (Local)</option>
                  <option value="ollama">Ollama (Local)</option>
                  <option value="gemini">Google Gemini (Cloud)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Model Name / Tag</label>
                <input
                  type="text"
                  value={settings.helper_llm_model}
                  onChange={(e) => setSettings({ ...settings, helper_llm_model: e.target.value })}
                  placeholder="e.g. qwen/qwen3.5-9b"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="hydeToggle"
                checked={settings.hyde_enabled}
                onChange={(e) => setSettings({ ...settings, hyde_enabled: e.target.checked })}
                className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-0 focus:ring-offset-0"
              />
              <label htmlFor="hydeToggle" className="text-xs text-slate-300 cursor-pointer">
                Enable HyDE query expansion during chat retrieval
              </label>
            </div>
          </div>

          {/* Section 2: Vision LLM Model */}
          <div className="space-y-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-200">Vision LLM Model</h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono">
                PPT & Figure Analysis
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts diagrams, charts, and architectural schematics from PowerPoint (.pptx) slides and PDF figures into semantic text descriptions.
            </p>

            <div className="flex items-center gap-2 pt-1 pb-1">
              <input
                type="checkbox"
                id="visionToggle"
                checked={settings.vision_enabled}
                onChange={(e) => setSettings({ ...settings, vision_enabled: e.target.checked })}
                className="rounded border-slate-700 bg-slate-800 text-emerald-600 focus:ring-0 focus:ring-offset-0"
              />
              <label htmlFor="visionToggle" className="text-xs text-slate-300 font-medium cursor-pointer">
                Enable Vision figure & diagram description extraction
              </label>
            </div>

            {settings.vision_enabled && (
              <div className="space-y-3 pt-2 border-t border-slate-800/80">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Vision Provider</label>
                    <select
                      value={settings.vision_llm_provider}
                      onChange={(e) => setSettings({ ...settings, vision_llm_provider: e.target.value })}
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="lmstudio">LM Studio (Local)</option>
                      <option value="gemini">Google Gemini (Cloud)</option>
                      <option value="ollama">Ollama (Local)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Vision Model Tag</label>
                    <input
                      type="text"
                      value={settings.vision_llm_model}
                      onChange={(e) => setSettings({ ...settings, vision_llm_model: e.target.value })}
                      placeholder="e.g. qwen/qwen3-vl-8b"
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Inference Timeout (Seconds)
                  </label>
                  <input
                    type="number"
                    min="10"
                    max="180"
                    value={settings.vision_timeout_seconds}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        vision_timeout_seconds: parseInt(e.target.value, 10) || 45,
                      })
                    }
                    className="w-32 bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[11px] text-slate-500 ml-2">Fails gracefully if local vision model times out</span>
                </div>
              </div>
            )}
          </div>

          {/* Section 3: LM Studio Base URL */}
          <div className="space-y-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-slate-200">Local Endpoint Configuration</h3>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">LM Studio Host API</label>
              <input
                type="text"
                value={settings.lmstudio_host}
                onChange={(e) => setSettings({ ...settings, lmstudio_host: e.target.value })}
                placeholder="http://localhost:1234/v1"
                className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                OpenAI-compatible local server hosted by LM Studio (port 1234).
              </p>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Save Settings
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

