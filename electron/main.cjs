const { app, BrowserWindow, ipcMain, dialog, shell, Notification } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const readline = require('node:readline');

let win;
let backend;
let backendReady = false;
let initialSnapshot = null;
const pending = [];

function emit(payload) {
  if (payload.event === 'snapshot') initialSnapshot = payload;
  if (payload.event === 'completed' && Notification.isSupported()) {
    new Notification({ title: 'Luma Downloader', body: `${payload.title} foi baixado.` }).show();
  }
  if (win && !win.isDestroyed()) win.webContents.send('backend:event', payload);
}

function startBackend() {
  const executable = app.isPackaged
    ? path.join(process.resourcesPath, 'backend', 'LumaBackend.exe')
    : path.join(__dirname, '..', 'backend-dist', 'LumaBackend.exe');
  backend = spawn(executable, [path.join(app.getPath('userData'), 'settings.json')], {
    windowsHide: true, stdio: ['pipe', 'pipe', 'pipe']
  });
  const lines = readline.createInterface({ input: backend.stdout });
  lines.on('line', (line) => {
    try {
      const payload = JSON.parse(line);
      if (!backendReady && payload.event === 'snapshot') {
        backendReady = true;
        for (const command of pending.splice(0)) backend.stdin.write(`${JSON.stringify(command)}\n`);
      }
      emit(payload);
    } catch { /* Ignore malformed stdout; diagnostics go to stderr. */ }
  });
  backend.stderr.on('data', (chunk) => console.error('[Luma backend]', chunk.toString()));
  backend.on('error', (error) => emit({ event: 'error', kind: 'backend', message: `Não foi possível iniciar o mecanismo de downloads: ${error.message}` }));
  backend.on('exit', (code) => {
    backendReady = false;
    if (code && !app.isQuitting) emit({ event: 'error', kind: 'backend', message: `O mecanismo de downloads foi encerrado (código ${code}).` });
  });
}

function createWindow() {
  const iconPath = app.isPackaged ? path.join(process.resourcesPath, 'luma.ico') : path.join(__dirname, '..', 'assets', 'luma.ico');
  win = new BrowserWindow({
    width: 1500, height: 970, minWidth: 1100, minHeight: 720,
    backgroundColor: '#07111b', frame: false, show: false,
    icon: iconPath,
    title: 'Luma Downloader',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true }
  });
  win.loadFile(path.join(__dirname, '..', 'ui', 'index.html'));
  win.once('ready-to-show', () => { win.show(); if (initialSnapshot) win.webContents.send('backend:event', initialSnapshot); });
}

app.whenReady().then(() => { startBackend(); createWindow(); });
app.on('before-quit', () => { app.isQuitting = true; if (backend && !backend.killed) backend.kill(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

ipcMain.on('backend:command', (_event, message) => {
  if (!backend || !backend.stdin.writable) return;
  if (!backendReady) pending.push(message);
  else backend.stdin.write(`${JSON.stringify(message)}\n`);
});
ipcMain.handle('dialog:folder', async (_event, kind) => {
  const result = await dialog.showOpenDialog(win, { title: kind === 'audio' ? 'Pasta para áudios' : 'Pasta para vídeos', properties: ['openDirectory', 'createDirectory'] });
  return result.canceled ? null : result.filePaths[0];
});
ipcMain.handle('dialog:file', async () => {
  const result = await dialog.showOpenDialog(win, { title: 'Localizar ffmpeg.exe', properties: ['openFile'], filters: [{ name: 'FFmpeg', extensions: ['exe'] }] });
  return result.canceled ? null : result.filePaths[0];
});
ipcMain.handle('shell:reveal', async (_event, target) => {
  if (!target) return;
  const normalized = path.resolve(target);
  const fs = require('node:fs');
  if (fs.existsSync(normalized) && fs.statSync(normalized).isFile()) shell.showItemInFolder(normalized);
  else await shell.openPath(fs.existsSync(normalized) ? normalized : path.dirname(normalized));
});
ipcMain.on('window:minimize', () => win?.minimize());
ipcMain.on('window:maximize', () => win && (win.isMaximized() ? win.unmaximize() : win.maximize()));
ipcMain.handle('window:is-maximized', () => win?.isMaximized() ?? false);
ipcMain.on('window:close', () => win?.close());
