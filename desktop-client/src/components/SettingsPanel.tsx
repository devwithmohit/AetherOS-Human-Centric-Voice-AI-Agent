import React, { useState } from 'react';
import { useAppStore } from '@store/appStore';

interface SettingsPanelProps {
  onConsentChange?: (type: string, granted: boolean) => void;
  onVoiceChange?: (voiceId: string) => void;
  onModelChange?: (model: string) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  onConsentChange,
  onVoiceChange,
  onModelChange,
}) => {
  const settings = useAppStore((state) => state.settings);
  const updateSettings = useAppStore((state) => state.updateSettings);

  const [localSettings, setLocalSettings] = useState(settings);
  const [recordingHotkey, setRecordingHotkey] = useState(false);

  const handleSave = () => {
    updateSettings(localSettings);

    // Trigger callbacks
    if (onVoiceChange && localSettings.voice !== settings.voice) {
      onVoiceChange(localSettings.voice);
    }
    if (onModelChange && localSettings.llmModel !== settings.llmModel) {
      onModelChange(localSettings.llmModel);
    }
  };

  const handleReset = () => {
    setLocalSettings(settings);
  };

  const handleConsentToggle = (type: string, value: boolean) => {
    setLocalSettings({ ...localSettings, [type]: value });
    if (onConsentChange) {
      onConsentChange(type, value);
    }
  };

  const handleHotkeyRecord = (e: React.KeyboardEvent) => {
    e.preventDefault();
    const keys = [];
    if (e.ctrlKey || e.metaKey) keys.push('CommandOrControl');
    if (e.shiftKey) keys.push('Shift');
    if (e.altKey) keys.push('Alt');
    if (e.key && !['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) {
      keys.push(e.key);
    }
    const hotkey = keys.join('+');
    setLocalSettings({ ...localSettings, recordingHotkey: hotkey });
    setRecordingHotkey(false);
  };

  // Voice options categorized by gender and accent
  const voiceOptions = [
    {
      category: 'US English - Male',
      voices: [
        { id: 'en_US-lessac-medium', name: 'Lessac (Medium Quality)' },
        { id: 'en_US-joe-medium', name: 'Joe (Medium Quality)' },
        { id: 'en_US-ryan-high', name: 'Ryan (High Quality)' },
      ],
    },
    {
      category: 'US English - Female',
      voices: [
        { id: 'en_US-amy-medium', name: 'Amy (Medium Quality)' },
        { id: 'en_US-kathleen-low', name: 'Kathleen (Low Quality)' },
      ],
    },
    {
      category: 'British English - Male',
      voices: [
        { id: 'en_GB-alan-medium', name: 'Alan (Medium Quality)' },
        { id: 'en_GB-southern_english_male-medium', name: 'Southern (Medium Quality)' },
      ],
    },
    {
      category: 'British English - Female',
      voices: [
        { id: 'en_GB-alba-medium', name: 'Alba (Medium Quality)' },
        { id: 'en_GB-jenny_dioco-medium', name: 'Jenny (Medium Quality)' },
      ],
    },
  ];

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-slate-800 to-slate-700 border-b border-slate-600">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <svg className="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
        </h2>
        <p className="text-xs text-slate-400">Privacy controls, models, and preferences</p>
      </div>

      {/* Settings form */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-800">

        {/* Privacy & Data Section */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Privacy & Learning
          </h3>

          <div className="space-y-4">
            {/* Enable Learning */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm text-slate-300">Enable AI Learning</label>
                <p className="text-xs text-slate-500">Allow Aether to learn from conversations</p>
              </div>
              <button
                onClick={() => handleConsentToggle('enableLearning', !localSettings.enableLearning)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  localSettings.enableLearning ? 'bg-primary-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    localSettings.enableLearning ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Data Retention */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">Data Retention Period</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="7"
                  max="365"
                  step="7"
                  value={localSettings.dataRetentionDays}
                  onChange={(e) => setLocalSettings({ ...localSettings, dataRetentionDays: parseInt(e.target.value) })}
                  className="flex-1 accent-primary-600"
                />
                <span className="text-sm text-slate-300 min-w-[80px] text-right">
                  {localSettings.dataRetentionDays} days
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Automatically delete conversations older than this period
              </p>
            </div>

            {/* Share Analytics */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm text-slate-300">Share Anonymous Analytics</label>
                <p className="text-xs text-slate-500">Help improve Aether (no personal data)</p>
              </div>
              <button
                onClick={() => handleConsentToggle('shareAnalytics', !localSettings.shareAnalytics)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  localSettings.shareAnalytics ? 'bg-primary-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    localSettings.shareAnalytics ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Privacy Notice */}
            <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="flex-1">
                  <p className="text-xs text-slate-300">
                    All data stored locally. No cloud sync unless explicitly enabled.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Voice Preferences Section */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
            Voice & TTS
          </h3>

          <div className="space-y-4">
            {/* Voice Selection with Categories */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">TTS Voice</label>
              <select
                value={localSettings.voice}
                onChange={(e) => {
                  setLocalSettings({ ...localSettings, voice: e.target.value });
                  if (onVoiceChange) {
                    onVoiceChange(e.target.value);
                  }
                }}
                className="w-full px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              >
                {voiceOptions.map((group) => (
                  <optgroup key={group.category} label={group.category}>
                    {group.voices.map((voice) => (
                      <option key={voice.id} value={voice.id}>
                        {voice.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Preview voices at{' '}
                <a href="https://rhasspy.github.io/piper-samples/" className="text-primary-400 hover:text-primary-300">
                  Piper Samples
                </a>
              </p>
            </div>

            {/* Voice Preview Button */}
            <button className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors text-sm flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              Test Voice
            </button>
          </div>
        </section>

        {/* Shortcuts Section */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            Keyboard Shortcuts
          </h3>

          <div className="space-y-4">
            {/* Wake Word */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">Wake Word</label>
              <input
                type="text"
                value={localSettings.wakeWord}
                onChange={(e) => setLocalSettings({ ...localSettings, wakeWord: e.target.value })}
                className="w-full px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                placeholder="hey jarvis"
              />
              <p className="text-xs text-slate-500 mt-1">Phrase to activate voice listening</p>
            </div>

            {/* Recording Hotkey */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">Recording Hotkey</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={localSettings.recordingHotkey}
                  readOnly
                  onKeyDown={recordingHotkey ? handleHotkeyRecord : undefined}
                  className="flex-1 px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                  placeholder="Press keys..."
                />
                <button
                  onClick={() => setRecordingHotkey(!recordingHotkey)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    recordingHotkey
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                >
                  {recordingHotkey ? 'Recording...' : 'Change'}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Global hotkey to start/stop voice recording
              </p>
            </div>

            {/* Push to Talk */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm text-slate-300">Push-to-Talk Mode</label>
                <p className="text-xs text-slate-500">Hold key to speak (no wake word)</p>
              </div>
              <button
                onClick={() => setLocalSettings({ ...localSettings, pushToTalk: !localSettings.pushToTalk })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  localSettings.pushToTalk ? 'bg-primary-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    localSettings.pushToTalk ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Models Section */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Language Models
          </h3>

          <div className="space-y-4">
            {/* LLM Mode */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">Inference Mode</label>
              <div className="grid grid-cols-3 gap-2">
                {(['local', 'cloud', 'hybrid'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setLocalSettings({ ...localSettings, llmMode: mode })}
                    className={`px-3 py-2 rounded-lg text-sm capitalize transition-colors ${
                      localSettings.llmMode === mode
                        ? 'bg-primary-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {localSettings.llmMode === 'local' && 'All processing on your device (private)'}
                {localSettings.llmMode === 'cloud' && 'Use cloud APIs (faster, requires internet)'}
                {localSettings.llmMode === 'hybrid' && 'Local first, cloud fallback'}
              </p>
            </div>

            {/* Model Selection */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                {localSettings.llmMode === 'local' ? 'Local Model' : 'Cloud Model'}
              </label>
              <select
                value={localSettings.llmModel}
                onChange={(e) => {
                  setLocalSettings({ ...localSettings, llmModel: e.target.value });
                  if (onModelChange) {
                    onModelChange(e.target.value);
                  }
                }}
                className="w-full px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              >
                {localSettings.llmMode === 'local' ? (
                  <>
                    <option value="llama3.2:3b">Llama 3.2 3B (Fast, 2GB RAM)</option>
                    <option value="llama3.2:1b">Llama 3.2 1B (Ultra Fast, 1GB RAM)</option>
                    <option value="phi3:mini">Phi-3 Mini (Balanced, 2.3GB RAM)</option>
                    <option value="mistral:7b">Mistral 7B (High Quality, 4.1GB RAM)</option>
                  </>
                ) : (
                  <>
                    <option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
                    <option value="gpt-4">GPT-4 (OpenAI)</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet (Anthropic)</option>
                    <option value="claude-3-opus">Claude 3 Opus (Anthropic)</option>
                  </>
                )}
              </select>
            </div>

            {/* Model Info */}
            <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="flex-1">
                  <p className="text-xs text-slate-300">
                    Current: <span className="text-primary-400">{localSettings.llmModel}</span>
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {localSettings.llmMode === 'local'
                      ? 'Ensure Ollama is running with the selected model pulled'
                      : 'API key required in backend configuration'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* General Section */}
        <section>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">General</h3>

          <div className="space-y-4">
            {/* Theme */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">Theme</label>
              <div className="grid grid-cols-3 gap-2">
                {(['light', 'dark', 'auto'] as const).map((theme) => (
                  <button
                    key={theme}
                    onClick={() => setLocalSettings({ ...localSettings, theme })}
                    className={`px-4 py-2 rounded-lg text-sm capitalize transition-colors ${
                      localSettings.theme === theme
                        ? 'bg-primary-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'
                    }`}
                  >
                    {theme}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-start */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm text-slate-300">Start on System Boot</label>
                <p className="text-xs text-slate-500">Launch with operating system</p>
              </div>
              <button
                onClick={() => setLocalSettings({ ...localSettings, autoStart: !localSettings.autoStart })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  localSettings.autoStart ? 'bg-primary-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    localSettings.autoStart ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* API Gateway URL */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">API Gateway URL</label>
              <input
                type="text"
                value={localSettings.apiGatewayUrl}
                onChange={(e) => setLocalSettings({ ...localSettings, apiGatewayUrl: e.target.value })}
                className="w-full px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                placeholder="http://localhost:8000"
              />
              <p className="text-xs text-slate-500 mt-1">Backend Module 11 endpoint</p>
            </div>
          </div>
        </section>

        {/* Danger Zone */}
        <section>
          <h3 className="text-sm font-semibold text-red-400 mb-3">Danger Zone</h3>
          <div className="space-y-2">
            <button className="w-full px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg border border-red-600/30 transition-colors text-sm font-medium">
              Clear All Memories
            </button>
            <button className="w-full px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg border border-red-600/30 transition-colors text-sm font-medium">
              Reset All Settings
            </button>
          </div>
        </section>
      </div>

      {/* Actions footer */}
      <div className="px-6 py-4 bg-slate-800 border-t border-slate-700 flex gap-3">
        <button
          onClick={handleReset}
          className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg font-medium transition-colors"
        >
          Reset
        </button>
        <button
          onClick={handleSave}
          className="flex-1 px-4 py-2 bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white rounded-lg font-medium transition-all shadow-lg"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
};
