import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  // App info
  getVersion: () => ipcRenderer.invoke('get-app-version'),

  // Window controls
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),

  // Audio recording events
  onToggleRecording: (callback: () => void) => {
    ipcRenderer.on('toggle-recording', callback);
  },

  // Microphone
  microphoneStart: () => ipcRenderer.invoke('microphone:start'),
  microphoneStop: () => ipcRenderer.invoke('microphone:stop'),
  microphoneGetState: () => ipcRenderer.invoke('microphone:get-state'),
  microphoneGetDevices: () => ipcRenderer.invoke('microphone:get-devices'),

  // Audio player
  audioPlay: (path: string) => ipcRenderer.invoke('audio:play', path),
  audioPause: () => ipcRenderer.invoke('audio:pause'),
  audioStop: () => ipcRenderer.invoke('audio:stop'),
  audioGetState: () => ipcRenderer.invoke('audio:get-state'),
  audioSetVolume: (volume: number) => ipcRenderer.invoke('audio:set-volume', volume),

  // Remove listeners
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
});

// TypeScript declaration for window.electron
declare global {
  interface Window {
    electron: {
      getVersion: () => Promise<string>;
      minimizeWindow: () => Promise<void>;
      maximizeWindow: () => Promise<void>;
      closeWindow: () => Promise<void>;
      onToggleRecording: (callback: () => void) => void;
      microphoneStart: () => Promise<{ success: boolean; error?: string }>;
      microphoneStop: () => Promise<{ success: boolean; error?: string }>;
      microphoneGetState: () => Promise<{ isRecording: boolean }>;
      microphoneGetDevices: () => Promise<{ success: boolean; devices: any[]; error?: string }>;
      audioPlay: (path: string) => Promise<{ success: boolean; method?: string; path?: string; error?: string }>;
      audioPause: () => Promise<{ success: boolean; error?: string }>;
      audioStop: () => Promise<{ success: boolean; error?: string }>;
      audioGetState: () => Promise<{ isPlaying: boolean; currentAudio: string | null }>;
      audioSetVolume: (volume: number) => Promise<{ success: boolean; volume?: number; error?: string }>;
      removeAllListeners: (channel: string) => void;
    };
  }
}
