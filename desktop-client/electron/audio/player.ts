import { ipcMain } from 'electron';
import * as path from 'path';
import * as fs from 'fs';

export class AudioPlayer {
  private isPlaying = false;
  private currentAudio: string | null = null;

  constructor() {
    this.setupIpcHandlers();
  }

  private setupIpcHandlers() {
    ipcMain.handle('audio:play', async (event, audioPath: string) => {
      try {
        this.isPlaying = true;
        this.currentAudio = audioPath;

        // Check if file exists
        if (audioPath.startsWith('http://') || audioPath.startsWith('https://')) {
          // URL - let renderer handle it via HTML5 Audio
          return { success: true, method: 'url' };
        } else if (fs.existsSync(audioPath)) {
          // Local file
          return { success: true, method: 'file', path: audioPath };
        } else {
          throw new Error('Audio file not found');
        }
      } catch (error) {
        console.error('Failed to play audio:', error);
        return { success: false, error: String(error) };
      }
    });

    ipcMain.handle('audio:pause', async () => {
      try {
        this.isPlaying = false;
        return { success: true };
      } catch (error) {
        console.error('Failed to pause audio:', error);
        return { success: false, error: String(error) };
      }
    });

    ipcMain.handle('audio:stop', async () => {
      try {
        this.isPlaying = false;
        this.currentAudio = null;
        return { success: true };
      } catch (error) {
        console.error('Failed to stop audio:', error);
        return { success: false, error: String(error) };
      }
    });

    ipcMain.handle('audio:get-state', async () => {
      return {
        isPlaying: this.isPlaying,
        currentAudio: this.currentAudio,
      };
    });

    // Set system volume (Windows/macOS specific)
    ipcMain.handle('audio:set-volume', async (event, volume: number) => {
      try {
        // Volume control would require platform-specific implementations
        // For now, delegate to renderer's Audio element
        return { success: true, volume };
      } catch (error) {
        console.error('Failed to set volume:', error);
        return { success: false, error: String(error) };
      }
    });
  }

  public cleanup() {
    this.isPlaying = false;
    this.currentAudio = null;
  }
}
