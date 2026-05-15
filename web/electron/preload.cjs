const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('otimizerPC', {
  getSnapshot: () => ipcRenderer.invoke('system:snapshot'),
  getProcesses: (limit = 8) => ipcRenderer.invoke('system:processes', limit),
  getNetworkAudit: (limit = 40) => ipcRenderer.invoke('system:network', limit),
  cleanup: (confirm = false) => ipcRenderer.invoke('system:cleanup', confirm),
  openExternal: (url) => ipcRenderer.invoke('app:openExternal', url),
});
