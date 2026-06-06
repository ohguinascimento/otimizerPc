const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('otimizerPC', {
  getSnapshot: () => ipcRenderer.invoke('system:snapshot'),
  getProcesses: (limit = 8) => ipcRenderer.invoke('system:processes', limit),
  getNetworkAudit: (limit = 40) => ipcRenderer.invoke('system:network', limit),
  getFileAudit: (limit = 40, recentDays = 7, source = null) =>
    ipcRenderer.invoke('system:files', { limit, recentDays, source }),
  getPowerSnapshot: () => ipcRenderer.invoke('system:power'),
  cleanup: (confirm = false) => ipcRenderer.invoke('system:cleanup', confirm),
  openExternal: (url) => ipcRenderer.invoke('app:openExternal', url),
});
