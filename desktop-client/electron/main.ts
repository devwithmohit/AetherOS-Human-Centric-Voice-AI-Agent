import { app, BrowserWindow, globalShortcut, ipcMain } from 'electron';
import * as path from 'path';
import { setupTray } from './tray';
import { MicrophoneManager } from './audio/microphone';
import { AudioPlayer } from './audio/player';

let mainWindow: BrowserWindow | null = null;
let microphoneManager: MicrophoneManager | null = null;
let audioPlayer: AudioPlayer | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    frame: true,
    titleBarStyle: 'default',
    backgroundColor: '#0f172a', // slate-950
    show: false, // Don't show until ready
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Setup system tray
  setupTray(mainWindow);
}

// ApInitialize audio managers
  microphoneManager = new MicrophoneManager();
  audioPlayer = new AudioPlayer();

  // p lifecycle
app.whenReady().then(() => {
  createWindow();

  // Register global shortcuts
  globalShortcut.register('CommandOrControl+`', () => {
    if (mainWindow) {
      mainWindow.webContents.send('toggle-recording');
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

  // Cleanup audio managers
  if (microphoneManager) {
    microphoneManager.cleanup();
  }
  if (audioPlayer) {
    audioPlayer.cleanup();
  }

app.on('will-quit', () => {
  // Unregister all shortcuts
  globalShortcut.unregisterAll();
});

// IPC handlers
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('minimize-window', () => {
  mainWindow?.minimize();
});

ipcMain.handle('maximize-window', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

ipcMain.handle('close-window', () => {
  mainWindow?.close();
});
