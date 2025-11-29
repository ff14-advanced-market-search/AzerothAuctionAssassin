const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("aaa", {
  loadState: () => ipcRenderer.invoke("load-state"),
  saveMegaData: (data) => ipcRenderer.invoke("save-mega-data", data),
  saveItems: (data) => ipcRenderer.invoke("save-items", data),
  saveIlvl: (data) => ipcRenderer.invoke("save-ilvl", data),
  savePetIlvl: (data) => ipcRenderer.invoke("save-pet-ilvl", data),
  importJson: (target) => ipcRenderer.invoke("import-json", { target }),
  exportJson: (target) => ipcRenderer.invoke("export-json", { target }),
  runMega: () => ipcRenderer.invoke("run-mega"),
  stopMega: () => ipcRenderer.invoke("stop-mega"),
  onMegaLog: (callback) => {
    const handler = (_event, line) => callback(line)
    ipcRenderer.on("mega-log", handler)
    return () => ipcRenderer.removeListener("mega-log", handler)
  },
  onMegaExit: (callback) => {
    const handler = (_event, code) => callback(code)
    ipcRenderer.on("mega-exit", handler)
    return () => ipcRenderer.removeListener("mega-exit", handler)
  },
  loadRealmLists: () => ipcRenderer.invoke("load-realm-lists"),
  saveRealmList: (region, realms) =>
    ipcRenderer.invoke("save-realm-list", region, realms),
  resetMegaData: () => ipcRenderer.invoke("reset-mega-data"),
  resetItems: () => ipcRenderer.invoke("reset-items"),
  resetIlvl: () => ipcRenderer.invoke("reset-ilvl"),
  resetPetIlvl: () => ipcRenderer.invoke("reset-pet-ilvl"),
  canGoBack: () => ipcRenderer.invoke("can-go-back"),
  canGoForward: () => ipcRenderer.invoke("can-go-forward"),
  goBack: () => ipcRenderer.invoke("go-back"),
  goForward: () => ipcRenderer.invoke("go-forward"),
  writeLog: (line) => ipcRenderer.invoke("write-log", line),
  getDataDir: () => ipcRenderer.invoke("get-data-dir"),
  getCustomDataDir: () => ipcRenderer.invoke("get-custom-data-dir"),
  selectDataDir: () => ipcRenderer.invoke("select-data-dir"),
  setCustomDataDir: (dirPath) =>
    ipcRenderer.invoke("set-custom-data-dir", dirPath),
  getZoomLevel: () => ipcRenderer.invoke("get-zoom-level"),
  setZoomLevel: (zoomFactor) =>
    ipcRenderer.invoke("set-zoom-level", zoomFactor),
  onZoomChanged: (callback) => {
    const handler = (_event, zoomFactor) => callback(zoomFactor)
    ipcRenderer.on("zoom-changed", handler)
    return () => ipcRenderer.removeListener("zoom-changed", handler)
  },
  listBackups: (target) => ipcRenderer.invoke("list-backups", { target }),
  restoreBackup: (target, filename) =>
    ipcRenderer.invoke("restore-backup", { target, filename }),
})
