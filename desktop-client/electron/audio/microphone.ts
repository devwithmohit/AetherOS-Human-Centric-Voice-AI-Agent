import { ipcMain, desktopCapturer } from 'electron';

export class MicrophoneManager {
  private isRecording = false;

  constructor() {
    this.setupIpcHandlers();
  }

  private setupIpcHandlers() {
    ipcMain.handle('microphone:start', async () => {
      try {
        this.isRecording = true;
        return { success: true };
      } catch (error) {
        console.error('Failed to start microphone:', error);
        return { success: false, error: String(error) };
      }
    });

    ipcMain.handle('microphone:stop', async () => {
      try {
        this.isRecording = false;
        return { success: true };
      } catch (error) {
        console.error('Failed to stop microphone:', error);
        return { success: false, error: String(error) };
      }
    });

    ipcMain.handle('microphone:get-state', async () => {
      return { isRecording: this.isRecording };
    });

    // Get available audio input devices
    ipcMain.handle('microphone:get-devices', async () => {
      try {
        const sources = await desktopCapturer.getSources({
          types: ['screen'],
        });

        // Note: Actual microphone enumeration happens in renderer via Web Audio API
        // This is for future Electron-side audio processing
        return { success: true, devices: [] };
      } catch (error) {
        console.error('Failed to get devices:', error);
        return { success: false, error: String(error) };
      }
    });
  }

  public cleanup() {
    this.isRecording = false;
  }
}
