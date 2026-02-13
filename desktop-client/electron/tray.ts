import { Tray, Menu, nativeImage, BrowserWindow } from 'electron';
import * as path from 'path';

let tray: Tray | null = null;

export function setupTray(mainWindow: BrowserWindow) {
  // Create a simple icon (you'll want to replace this with actual icons)
  const icon = nativeImage.createEmpty();

  // TODO: Use actual tray icons from public/assets/icons/
  // const iconPath = path.join(__dirname, '../../public/assets/icons/tray-icon.png');
  // const icon = nativeImage.createFromPath(iconPath);

  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Aether',
      click: () => {
        mainWindow.show();
      },
    },
    {
      label: 'Start Listening',
      click: () => {
        mainWindow.webContents.send('toggle-recording');
      },
    },
    { type: 'separator' },
    {
      label: 'Settings',
      click: () => {
        mainWindow.show();
        mainWindow.webContents.send('open-settings');
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        mainWindow.destroy();
      },
    },
  ]);

  tray.setToolTip('Aether AI Assistant');
  tray.setContextMenu(contextMenu);

  // Show window on tray icon click
  tray.on('click', () => {
    mainWindow.show();
  });

  return tray;
}

export function updateTrayIcon(status: 'idle' | 'listening' | 'speaking') {
  if (!tray) return;

  // TODO: Update tray icon based on status
  // const iconPath = path.join(__dirname, `../../public/assets/icons/tray-${status}.png`);
  // const icon = nativeImage.createFromPath(iconPath);
  // tray.setImage(icon);
}
