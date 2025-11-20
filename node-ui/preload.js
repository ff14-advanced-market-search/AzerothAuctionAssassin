const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("aaa", {
  loadState: () => ipcRenderer.invoke("load-state"),
  saveMegaData: (data) => ipcRenderer.invoke("save-mega-data", data),
  saveItems: (data) => ipcRenderer.invoke("save-items", data),
  savePets: (data) => ipcRenderer.invoke("save-pets", data),
  saveIlvl: (data) => ipcRenderer.invoke("save-ilvl", data),
  savePetIlvl: (data) => ipcRenderer.invoke("save-pet-ilvl", data),
  importJson: (target) => ipcRenderer.invoke("import-json", { target }),
  exportJson: (target) => ipcRenderer.invoke("export-json", { target }),
  runMega: () => ipcRenderer.invoke("run-mega"),
  stopMega: () => ipcRenderer.invoke("stop-mega"),
  onMegaLog: (callback) =>
    ipcRenderer.on("mega-log", (_event, line) => callback(line)),
  onMegaExit: (callback) =>
    ipcRenderer.on("mega-exit", (_event, code) => callback(code)),
});
