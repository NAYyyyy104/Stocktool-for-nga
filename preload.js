const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  readRowsSync: () => ipcRenderer.sendSync("rows:read-sync"),
  writeRowsSync: (rows) => ipcRenderer.sendSync("rows:write-sync", rows),
  clearRowsSync: () => ipcRenderer.sendSync("rows:clear-sync"),
  getStorageInfoSync: () => ipcRenderer.sendSync("rows:storage-info-sync")
});
