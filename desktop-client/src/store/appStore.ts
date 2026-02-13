import { create } from 'zustand';

export type AppStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  toolStatus?: {
    tool: string;
    status: 'running' | 'complete' | 'error';
    result?: string;
  };
  isMarkdown?: boolean;
}

export interface Memory {
  id: string;
  type: 'fact' | 'preference' | 'context';
  content: string;
  timestamp: Date;
  source?: string;
}

interface AppState {
  // Status
  status: AppStatus;
  setStatus: (status: AppStatus) => void;

  // Audio levels
  micLevel: number;
  setMicLevel: (level: number) => void;

  // Chat
  messages: Message[];
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;
  isTyping: boolean;
  setTyping: (isTyping: boolean) => void;
  inputMode: 'voice' | 'text';
  setInputMode: (mode: 'voice' | 'text') => void;

  // Memory
  memories: Memory[];
  addMemory: (memory: Omit<Memory, 'id' | 'timestamp'>) => void;
  removeMemory: (id: string) => void;

  // Settings
  settings: {
    wakeWord: string;
    pushToTalk: boolean;
    autoStart: boolean;
    theme: 'light' | 'dark' | 'auto';
    voice: string;
    apiGatewayUrl: string;
    // Privacy
    enableLearning: boolean;
    dataRetentionDays: number;
    shareAnalytics: boolean;
    // Shortcuts
    recordingHotkey: string;
    // Models
    llmMode: 'local' | 'cloud' | 'hybrid';
    llmModel: string;
  };
  updateSettings: (settings: Partial<AppState['settings']>) => void;

  // WebSocket connection
  isConnected: boolean;
  setConnected: (connected: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial status
  status: 'idle',
  setStatus: (status) => set({ status }),

  // Audio
  micLevel: 0,
  setMicLevel: (micLevel) => set({ micLevel }),

  // Chat
  messages: [],
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        },
      ],
    })),
  clearMessages: () => set({ messages: [] }),
  isTyping: false,
  setTyping: (isTyping) => set({ isTyping }),
  inputMode: 'voice',
  setInputMode: (inputMode) => set({ inputMode }),

  // Memory
  memories: [],
  addMemory: (memory) =>
    set((state) => ({
      memories: [
        ...state.memories,
        {
          ...memory,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        },
      ],
    })),
  removeMemory: (id) =>
    set((state) => ({
      memories: state.memories.filter((m) => m.id !== id),
    })),

  // Settings
  settings: {
    wakeWord: 'hey jarvis',
    pushToTalk: false,
    autoStart: true,
    theme: 'dark',
    voice: 'en_US-lessac-medium',
    apiGatewayUrl: 'http://localhost:8000',
    // Privacy defaults
    enableLearning: true,
    dataRetentionDays: 30,
    shareAnalytics: false,
    // Shortcuts
    recordingHotkey: 'CommandOrControl+`',
    // Models
    llmMode: 'local',
    llmModel: 'llama3.2:3b',
  },
  updateSettings: (settings) =>
    set((state) => ({
      settings: { ...state.settings, ...settings },
    })),

  // Connection
  isConnected: false,
  setConnected: (isConnected) => set({ isConnected }),
}));
