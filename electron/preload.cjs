const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('luma', {
  onBackend: (callback) => ipcRenderer.on('backend:event', (_event, payload) => callback(payload)),
  send: (command, payload = {}) => ipcRenderer.send('backend:command', { command, ...payload }),
  chooseFolder: (kind) => ipcRenderer.invoke('dialog:folder', kind),
  chooseFile: () => ipcRenderer.invoke('dialog:file'),
  reveal: (path) => ipcRenderer.invoke('shell:reveal', path),
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:is-maximized')
});
