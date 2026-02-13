import React, { useEffect } from 'react';
import { VoiceVisualizer } from '@components/VoiceVisualizer';
import { ChatWindow } from '@components/ChatWindow';
import { StatusIndicator } from '@components/StatusIndicator';
import { useAppStore } from '@store/appStore';
import { useVoiceRecording } from '@hooks/useVoiceRecording';
import { useWebSocket } from '@hooks/useWebSocket';

function App() {
  const status = useAppStore((state) => state.status);
  const micLevel = useAppStore((state) => state.micLevel);
  const settings = useAppStore((state) => state.settings);

  // Initialize voice recording hook
  const { startRecording, stopRecording, isRecording } = useVoiceRecording();

  // Initialize WebSocket connection
  const { isConnected } = useWebSocket(settings.apiGatewayUrl);

  useEffect(() => {
    // Listen for keyboard shortcuts from Electron
    const handleKeyPress = (event: KeyboardEvent) => {
      // Ctrl + ` for wake
      if (event.ctrlKey && event.key === '`') {
        if (isRecording) {
          stopRecording();
        } else {
          startRecording();
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isRecording, startRecording, stopRecording]);

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden">
      {/* Main container */}
      <div className="h-full flex flex-col p-6 gap-4">
        {/* Header with status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-2xl">A</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-400 to-accent-400 bg-clip-text text-transparent">
                Aether
              </h1>
              <p className="text-sm text-slate-500">AI Voice Assistant</p>
            </div>
          </div>

          <StatusIndicator />
        </div>

        {/* Voice visualizer */}
        <VoiceVisualizer
          isRecording={status === 'listening'}
          audioLevel={micLevel}
          onWakeWordDetected={() => startRecording()}
        />

        {/* Chat window (takes remaining space) */}
        <div className="flex-1 min-h-0">
          <ChatWindow />
        </div>

        {/* Quick actions footer */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => {
              if (isRecording) {
                stopRecording();
              } else {
                startRecording();
              }
            }}
            className={`px-6 py-3 rounded-xl font-semibold transition-all shadow-lg ${
              isRecording
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700'
            }`}
          >
            {isRecording ? 'Stop Listening' : 'Start Listening'}
          </button>

          <div className="text-xs text-slate-500">
            Press <kbd className="px-2 py-1 bg-slate-700 rounded text-xs">Ctrl + `</kbd> to toggle
          </div>
        </div>
      </div>

      {/* Connection status overlay */}
      {!isConnected && (
        <div className="absolute top-4 right-4 px-4 py-2 bg-red-600/90 backdrop-blur rounded-lg shadow-lg flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
          <span className="text-sm font-medium">Disconnected from backend</span>
        </div>
      )}
    </div>
  );
}

export default App;
