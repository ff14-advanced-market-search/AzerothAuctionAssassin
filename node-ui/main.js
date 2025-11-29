/* eslint-env node, es6 */
/* global require, __dirname, process, console, setTimeout, clearTimeout, setInterval, clearInterval */
const { app, BrowserWindow, ipcMain, dialog } = require("electron")
const path = require("path")
const fs = require("fs")

// In production (packaged app), __dirname is inside app.asar (read-only)
// In development, __dirname points to the actual node-ui directory
const ROOT = app.isPackaged
  ? path.dirname(app.getPath("exe")) // Executable location
  : path.resolve(__dirname, "..")

// Config file to store custom data directory path (stored in userData so it persists)
const CONFIG_FILE = path.join(app.getPath("userData"), "app-config.json")

function loadConfig() {
  return readJson(CONFIG_FILE, { customDataDir: null })
}

function saveConfig(config) {
  writeJson(CONFIG_FILE, config)
}

// For data directory:
// - Check for custom data directory setting first
// - In development: use project root (same as before)
// - In production: place data next to the app
//   macOS: Next to .app bundle (go up from MacOS to Contents to .app parent)
//   Windows: Next to exe folder (same level as exe)
function getDataDir() {
  // Check for custom data directory setting first
  const config = loadConfig()
  if (config.customDataDir && fs.existsSync(config.customDataDir)) {
    return config.customDataDir
  }

  if (!app.isPackaged) {
    return path.join(ROOT, "AzerothAuctionAssassinData")
  }

  if (process.platform === "darwin") {
    // macOS: exe is at App.app/Contents/MacOS/exe, go up 4 levels to get parent of .app bundle
    // This places data next to the .app bundle, not inside it
    return path.join(
      path.dirname(
        path.dirname(path.dirname(path.dirname(app.getPath("exe"))))
      ),
      "AzerothAuctionAssassinData"
    )
  } else {
    // Windows: For portable builds, exe is directly in the folder
    // Data directory should be next to the exe (same directory)
    let exePath = app.getPath("exe")
    let exeDir = path.dirname(exePath)

    // Check if we're in a temp directory (portable exe extracts to temp when run)
    const tempPath = process.env.TEMP || process.env.TMP || ""
    const normalizedTempPath = tempPath.toLowerCase().replace(/\\/g, "/")
    const normalizedExeDir = exeDir.toLowerCase().replace(/\\/g, "/")
    const isInTemp = tempPath && normalizedExeDir.includes(normalizedTempPath)

    if (isInTemp) {
      // Portable exe extracts to temp - use current working directory instead
      // This is where the user launched the exe from (where the actual exe file is)
      const cwd = process.cwd()
      if (cwd && !cwd.toLowerCase().includes("temp")) {
        exeDir = cwd
      }
    }

    return path.join(exeDir, "AzerothAuctionAssassinData")
  }
}

// For static data directory:
// - In development: use project root
// - In production: use resources folder (where extraResources are placed)
//   macOS: App.app/Contents/Resources/StaticData
//   Windows: resources/StaticData (next to exe) or StaticData (for portable)
function getStaticDir() {
  if (!app.isPackaged) {
    return path.join(ROOT, "StaticData")
  }

  // Use process.resourcesPath which Electron provides - works on both platforms
  // This points to the resources directory where extraResources are placed
  // Note: process.resourcesPath is available in Electron packaged apps
  const resourcesPath =
    process.resourcesPath ||
    (process.platform === "darwin"
      ? path.join(path.dirname(path.dirname(app.getPath("exe"))), "Resources")
      : path.join(path.dirname(app.getPath("exe")), "resources"))

  return path.join(resourcesPath, "StaticData")
}

const DATA_DIR = getDataDir()
const STATIC_DIR = getStaticDir()

const BACKUP_DIR = path.join(DATA_DIR, "backup")

// Log paths for debugging - always log in packaged mode to help debug data directory location
console.log("App paths:", {
  isPackaged: app.isPackaged,
  exePath: app.getPath("exe"),
  exeDir: path.dirname(app.getPath("exe")),
  processCwd: process.cwd(),
  processExecPath: process.execPath,
  userData: app.getPath("userData"),
  __dirname: __dirname,
  ROOT: ROOT,
  DATA_DIR: DATA_DIR,
  STATIC_DIR: STATIC_DIR,
})

const FILES = {
  megaData: path.join(DATA_DIR, "mega_data.json"),
  desiredItems: path.join(DATA_DIR, "desired_items.json"),
  ilvlList: path.join(DATA_DIR, "desired_ilvl_list.json"),
  petIlvlList: path.join(DATA_DIR, "desired_pet_ilvl_list.json"),
}

const REALM_FILES = {
  EU: path.join(DATA_DIR, "eu-wow-connected-realm-ids.json"),
  NA: path.join(DATA_DIR, "na-wow-connected-realm-ids.json"),
  EUCLASSIC: path.join(DATA_DIR, "euclassic-wow-connected-realm-ids.json"),
  NACLASSIC: path.join(DATA_DIR, "naclassic-wow-connected-realm-ids.json"),
  NASODCLASSIC: path.join(
    DATA_DIR,
    "nasodclassic-wow-connected-realm-ids.json"
  ),
  EUSODCLASSIC: path.join(
    DATA_DIR,
    "eusodclassic-wow-connected-realm-ids.json"
  ),
}

let alertsProcess = null
let mainWindow = null
let logFileStream = null

function readJson(filePath, fallback) {
  try {
    const raw = fs.readFileSync(filePath, "utf8")
    return JSON.parse(raw)
  } catch (err) {
    return fallback
  }
}

function writeJson(filePath, data) {
  try {
    // Ensure directory exists
    const dir = path.dirname(filePath)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2))
    return { success: true }
  } catch (error) {
    console.error(`Failed to write JSON file: ${filePath}`, error)
    return { success: false, error: error.message }
  }
}

function getTimestampInt() {
  const now = new Date()
  return (
    now.getFullYear() * 1_000_000 +
    (now.getMonth() + 1) * 10_000 +
    now.getDate() * 100 +
    now.getHours()
  )
}

function saveBackup(fileType, data) {
  try {
    fs.mkdirSync(BACKUP_DIR, { recursive: true })
    const timestamp = getTimestampInt()
    const backupFilenames = {
      megaData: `${timestamp}_mega_data.json`,
      desiredItems: `${timestamp}_desired_items.json`,
      ilvlList: `${timestamp}_desired_ilvl_list.json`,
      petIlvlList: `${timestamp}_desired_pet_ilvl_list.json`,
    }
    const backupFilename = backupFilenames[fileType]
    if (backupFilename) {
      const backupPath = path.join(BACKUP_DIR, backupFilename)
      writeJson(backupPath, data)
    }
  } catch (err) {
    console.error("Failed to create backup:", err)
  }
}

function ensureDataFiles() {
  fs.mkdirSync(DATA_DIR, { recursive: true })
  fs.mkdirSync(BACKUP_DIR, { recursive: true })

  // Create logs directory
  const LOGS_DIR = path.join(DATA_DIR, "logs")
  fs.mkdirSync(LOGS_DIR, { recursive: true })

  // Create timestamped log file
  if (!logFileStream) {
    const now = new Date()
    const timestamp =
      now.getFullYear().toString() +
      String(now.getMonth() + 1).padStart(2, "0") +
      String(now.getDate()).padStart(2, "0") +
      "_" +
      String(now.getHours()).padStart(2, "0") +
      String(now.getMinutes()).padStart(2, "0") +
      String(now.getSeconds()).padStart(2, "0")
    const logFilePath = path.join(LOGS_DIR, `aaa_log_${timestamp}.txt`)
    logFileStream = fs.createWriteStream(logFilePath, {
      flags: "a",
      encoding: "utf8",
    })
    const startMessage = `=== Log started at ${now.toISOString()} ===\n`
    logFileStream.write(startMessage)
  }

  const defaults = {
    [FILES.megaData]: {
      MEGA_WEBHOOK_URL: "",
      WOW_CLIENT_ID: "",
      WOW_CLIENT_SECRET: "",
      AUTHENTICATION_TOKEN: "",
      WOW_REGION: "EU",
      EXTRA_ALERTS: "[]",
      SHOW_BID_PRICES: false,
      MEGA_THREADS: 10,
      WOWHEAD_LINK: false,
      SCAN_TIME_MIN: -1,
      SCAN_TIME_MAX: 3,
      NO_LINKS: false,
      NO_RUSSIAN_REALMS: false,
      DISCOUNT_PERCENT: 10,
      TOKEN_PRICE: 0,
      REFRESH_ALERTS: false,
      DEBUG: false,
      FACTION: "all",
    },
    [FILES.desiredItems]: {},
    [FILES.ilvlList]: [],
    [FILES.petIlvlList]: [],
  }

  for (const [filePath, fallback] of Object.entries(defaults)) {
    if (!fs.existsSync(filePath)) {
      writeJson(filePath, fallback)
    }
  }

  // Initialize realm list files if they don't exist (empty objects)
  // They will be populated by the reset function using hardcoded data
  for (const filePath of Object.values(REALM_FILES)) {
    if (!fs.existsSync(filePath)) {
      writeJson(filePath, {})
    }
  }
}

function normalizeMegaData(input) {
  const boolKeys = new Set([
    "SHOW_BID_PRICES",
    "WOWHEAD_LINK",
    "NO_LINKS",
    "NO_RUSSIAN_REALMS",
    "REFRESH_ALERTS",
    "DEBUG",
  ])
  const intKeys = new Set([
    "MEGA_THREADS",
    "SCAN_TIME_MIN",
    "SCAN_TIME_MAX",
    "TOKEN_PRICE",
  ])

  const output = { ...input }
  for (const key of Object.keys(output)) {
    if (boolKeys.has(key)) {
      output[key] = Boolean(output[key])
    } else if (intKeys.has(key)) {
      const num = Number(output[key])
      output[key] = Number.isFinite(num) ? num : 0
    }
  }
  return output
}

function normalizeKV(input) {
  const out = {}
  Object.entries(input || {}).forEach(([k, v]) => {
    const num = Number(v)
    if (!Number.isNaN(num)) {
      out[String(k)] = num
    }
  })
  return out
}

function normalizeIlvlRules(list) {
  if (!Array.isArray(list)) return []
  return list
    .map((rule) => ({
      ilvl: Number(rule.ilvl) || 0,
      max_ilvl: Number(rule.max_ilvl) || Number(rule.ilvl) || 0,
      buyout: Number(rule.buyout) || 0,
      sockets: Boolean(rule.sockets),
      speed: Boolean(rule.speed),
      leech: Boolean(rule.leech),
      avoidance: Boolean(rule.avoidance),
      item_ids: Array.isArray(rule.item_ids)
        ? rule.item_ids.map((id) => Number(id)).filter((n) => !Number.isNaN(n))
        : [],
      required_min_lvl: Number(rule.required_min_lvl) || 1,
      required_max_lvl: Number(rule.required_max_lvl) || 1000,
      bonus_lists: Array.isArray(rule.bonus_lists)
        ? rule.bonus_lists
            .map((id) => Number(id))
            .filter((n) => !Number.isNaN(n))
        : [],
    }))
    .filter((rule) => rule.buyout > 0)
}

function normalizePetIlvlRules(list) {
  if (!Array.isArray(list)) return []
  return list
    .map((rule) => ({
      petID: Number(rule.petID) || 0,
      price: Number(rule.price) || 0,
      minLevel: Number(rule.minLevel) || 1,
      minQuality:
        rule.minQuality === undefined ? -1 : Number(rule.minQuality) || -1,
      excludeBreeds: Array.isArray(rule.excludeBreeds)
        ? rule.excludeBreeds
            .map((id) => Number(id))
            .filter((n) => !Number.isNaN(n))
        : [],
    }))
    .filter((rule) => rule.petID && rule.price > 0)
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 1000,
    minHeight: 720,
    backgroundColor: "#0c1116",
    show: true, // Show immediately
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  const htmlPath = path.join(__dirname, "index.html")
  console.log("Loading HTML from:", htmlPath)

  mainWindow.loadFile(htmlPath).catch((err) => {
    console.error("Failed to load HTML:", err)
    // Show native error dialog since renderer may not be ready
    dialog.showErrorBox(
      "Failed to Load Application",
      `Failed to load the application window: ${err.message}`
    )
  })

  // Set default zoom to 80%
  mainWindow.webContents.setZoomFactor(0.8)

  // Listen for zoom changes and notify renderer
  mainWindow.webContents.on("zoom-changed", () => {
    const zoomFactor = mainWindow.webContents.getZoomFactor()
    mainWindow.webContents.send("zoom-changed", zoomFactor)
  })

  // Ensure window is visible and focused when ready
  mainWindow.once("ready-to-show", () => {
    console.log("Window ready to show")
    if (!mainWindow.isVisible()) {
      mainWindow.show()
    }
    mainWindow.focus()
    // Send initial zoom level
    const zoomFactor = mainWindow.webContents.getZoomFactor()
    mainWindow.webContents.send("zoom-changed", zoomFactor)
  })

  // Fallback: show window after a short delay if ready-to-show doesn't fire
  setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      console.log("Fallback: showing window")
      mainWindow.show()
      mainWindow.focus()
    }
  }, 1000)

  // Handle page load errors
  mainWindow.webContents.on(
    "did-fail-load",
    (event, errorCode, errorDescription) => {
      console.error("Failed to load page:", errorCode, errorDescription)
    }
  )

  // Open DevTools in development (uncomment for debugging)
  // mainWindow.webContents.openDevTools();
}

function setupIpc() {
  ipcMain.handle("load-state", () => {
    ensureDataFiles()
    return {
      megaData: readJson(FILES.megaData, {}),
      desiredItems: readJson(FILES.desiredItems, {}),
      ilvlList: readJson(FILES.ilvlList, []),
      petIlvlList: readJson(FILES.petIlvlList, []),
      processRunning: Boolean(alertsProcess),
    }
  })

  // Helper function to send log messages to renderer
  const sendToLogPanel = (message) => {
    BrowserWindow.getAllWindows().forEach((win) =>
      win.webContents.send("mega-log", message)
    )
    if (logFileStream) {
      logFileStream.write(message)
    }
  }

  ipcMain.handle("save-mega-data", (_event, payload) => {
    const normalized = normalizeMegaData(payload || {})
    const logMsg = `[SAVE] Saving mega_data.json to: ${FILES.megaData}\n`
    console.log(logMsg.trim())
    sendToLogPanel(logMsg)
    writeJson(FILES.megaData, normalized)
    saveBackup("megaData", normalized)
    const successMsg = `[SAVE] Successfully saved mega_data.json\n`
    console.log(successMsg.trim())
    sendToLogPanel(successMsg)
    return normalized
  })

  ipcMain.handle("save-items", (_event, payload) => {
    const normalized = normalizeKV(payload || {})
    const logMsg = `[SAVE] Saving desired_items.json to: ${FILES.desiredItems}\n`
    console.log(logMsg.trim())
    sendToLogPanel(logMsg)
    writeJson(FILES.desiredItems, normalized)
    saveBackup("desiredItems", normalized)
    const successMsg = `[SAVE] Successfully saved desired_items.json\n`
    console.log(successMsg.trim())
    sendToLogPanel(successMsg)
    return normalized
  })

  ipcMain.handle("save-ilvl", (_event, payload) => {
    const normalized = normalizeIlvlRules(payload || [])
    const logMsg = `[SAVE] Saving desired_ilvl_list.json to: ${FILES.ilvlList}\n`
    console.log(logMsg.trim())
    sendToLogPanel(logMsg)
    writeJson(FILES.ilvlList, normalized)
    saveBackup("ilvlList", normalized)
    const successMsg = `[SAVE] Successfully saved desired_ilvl_list.json\n`
    console.log(successMsg.trim())
    sendToLogPanel(successMsg)
    return normalized
  })

  ipcMain.handle("save-pet-ilvl", (_event, payload) => {
    const normalized = normalizePetIlvlRules(payload || [])
    const logMsg = `[SAVE] Saving desired_pet_ilvl_list.json to: ${FILES.petIlvlList}\n`
    console.log(logMsg.trim())
    sendToLogPanel(logMsg)
    writeJson(FILES.petIlvlList, normalized)
    saveBackup("petIlvlList", normalized)
    const successMsg = `[SAVE] Successfully saved desired_pet_ilvl_list.json\n`
    console.log(successMsg.trim())
    sendToLogPanel(successMsg)
    return normalized
  })

  // Reset handlers - clear data for each page
  ipcMain.handle("reset-mega-data", () => {
    const defaultData = readJson(
      path.join(DATA_DIR, "example_mega_data.json"),
      {
        MEGA_WEBHOOK_URL: "",
        WOW_CLIENT_ID: "",
        WOW_CLIENT_SECRET: "",
        AUTHENTICATION_TOKEN: "",
        WOW_REGION: "EU",
        EXTRA_ALERTS: "[]",
        SHOW_BID_PRICES: false,
        MEGA_THREADS: 10,
        WOWHEAD_LINK: false,
        SCAN_TIME_MIN: -1,
        SCAN_TIME_MAX: 3,
        NO_LINKS: false,
        NO_RUSSIAN_REALMS: false,
        DISCOUNT_PERCENT: 10,
        TOKEN_PRICE: 0,
        REFRESH_ALERTS: false,
        DEBUG: false,
        FACTION: "all",
      }
    )
    const normalized = normalizeMegaData(defaultData)
    writeJson(FILES.megaData, normalized)
    saveBackup("megaData", normalized)
    return normalized
  })

  ipcMain.handle("reset-items", () => {
    const normalized = normalizeKV({})
    writeJson(FILES.desiredItems, normalized)
    saveBackup("desiredItems", normalized)
    return normalized
  })

  ipcMain.handle("reset-ilvl", () => {
    const normalized = normalizeIlvlRules([])
    writeJson(FILES.ilvlList, normalized)
    saveBackup("ilvlList", normalized)
    return normalized
  })

  ipcMain.handle("reset-pet-ilvl", () => {
    const normalized = normalizePetIlvlRules([])
    writeJson(FILES.petIlvlList, normalized)
    saveBackup("petIlvlList", normalized)
    return normalized
  })

  // Navigation handlers
  ipcMain.handle("can-go-back", () => {
    return mainWindow?.webContents.canGoBack() || false
  })

  ipcMain.handle("can-go-forward", () => {
    return mainWindow?.webContents.canGoForward() || false
  })

  ipcMain.handle("go-back", () => {
    if (mainWindow?.webContents.canGoBack()) {
      mainWindow.webContents.goBack()
    }
    return mainWindow?.webContents.canGoBack() || false
  })

  ipcMain.handle("go-forward", () => {
    if (mainWindow?.webContents.canGoForward()) {
      mainWindow.webContents.goForward()
    }
    return mainWindow?.webContents.canGoForward() || false
  })

  // Write log to file (for renderer logs)
  ipcMain.handle("write-log", (_event, line) => {
    if (logFileStream) {
      logFileStream.write(line)
    }
    return { success: true }
  })

  ipcMain.handle("import-json", async (_event, { target }) => {
    const targetPath = FILES[target]
    if (!targetPath) return { error: "Unknown target" }
    const res = await dialog.showOpenDialog({
      properties: ["openFile"],
      filters: [{ name: "JSON", extensions: ["json"] }],
    })
    if (res.canceled || !res.filePaths.length) return { canceled: true }
    const src = res.filePaths[0]
    let data = readJson(src, null)
    if (data === null) return { error: "Failed to read JSON" }

    // Validate pet ilvl format before importing
    if (target === "petIlvlList") {
      // Check if it's the legacy format (object with numeric keys) and convert it
      if (data && typeof data === "object" && !Array.isArray(data)) {
        const keys = Object.keys(data)
        if (keys.length > 0 && keys.every((k) => !Number.isNaN(Number(k)))) {
          // Convert legacy format to new format with validation
          const converted = keys
            .map((key) => {
              const petID = Number(key)
              const price = Number(data[key])
              // Validate pet ID range (1-10000)
              if (
                Number.isNaN(petID) ||
                petID < 1 ||
                petID > 10000 ||
                Number.isNaN(price) ||
                price <= 0
              ) {
                return null
              }
              return {
                petID,
                price,
                minLevel: 1,
                minQuality: -1,
                excludeBreeds: [],
              }
            })
            .filter((rule) => rule !== null)
          data = converted
        }
      }

      // Must be an array
      if (!Array.isArray(data)) {
        return {
          error:
            'Invalid format. Expected an array of pet rules: [{"petID": 183, "price": 100000, ...}]',
        }
      }

      // Validate and filter rules, collecting invalid ones
      const validRules = []
      const invalidCount = { count: 0 }

      for (let i = 0; i < data.length; i++) {
        const rule = data[i]
        if (!rule || typeof rule !== "object") {
          invalidCount.count++
          continue
        }

        // Check required fields
        if (rule.petID === undefined || rule.petID === null) {
          invalidCount.count++
          continue
        }

        if (rule.price === undefined || rule.price === null) {
          invalidCount.count++
          continue
        }

        // Validate types and ranges
        const petID = Number(rule.petID)
        const price = Number(rule.price)
        const minLevel = Number(rule.minLevel ?? 1)
        const minQuality = Number(rule.minQuality ?? -1)
        const excludeBreeds = Array.isArray(rule.excludeBreeds)
          ? rule.excludeBreeds
              .map((b) => Number(b))
              .filter((b) => !Number.isNaN(b))
          : []

        // Validate pet ID range (1-10000)
        if (Number.isNaN(petID) || petID < 1 || petID > 10000) {
          invalidCount.count++
          continue
        }

        // Validate price
        if (Number.isNaN(price) || price <= 0) {
          invalidCount.count++
          continue
        }

        // Validate minLevel (1-25)
        if (Number.isNaN(minLevel) || minLevel < 1 || minLevel > 25) {
          invalidCount.count++
          continue
        }

        // Validate minQuality (-1 to 3)
        if (Number.isNaN(minQuality) || minQuality < -1 || minQuality > 3) {
          invalidCount.count++
          continue
        }

        // All validations passed, add to valid rules
        validRules.push({
          petID,
          price,
          minLevel,
          minQuality,
          excludeBreeds,
        })
      }

      // If no valid rules found, return error
      if (validRules.length === 0) {
        return {
          error: "No valid pet rules found. All rules were invalid.",
        }
      }

      // Use filtered valid rules
      data = validRules

      // Log warning if some rules were filtered
      if (invalidCount.count > 0) {
        const logMsg = `[IMPORT] Filtered out ${invalidCount.count} invalid pet rule(s), imported ${validRules.length} valid rule(s)\n`
        console.log(logMsg.trim())
        sendToLogPanel(logMsg)
      }
    }

    writeJson(targetPath, data)
    saveBackup(target, data)
    return { data }
  })

  ipcMain.handle("export-json", async (_event, { target }) => {
    const targetPath = FILES[target]
    if (!targetPath) return { error: "Unknown target" }
    const res = await dialog.showSaveDialog({
      defaultPath: path.basename(targetPath),
      filters: [{ name: "JSON", extensions: ["json"] }],
    })
    if (res.canceled || !res.filePath) return { canceled: true }
    const data = readJson(targetPath, null)
    if (data === null) return { error: "Failed to read source JSON" }
    writeJson(res.filePath, data)
    return { exported: res.filePath }
  })

  ipcMain.handle("list-backups", (_event, { target }) => {
    try {
      if (!fs.existsSync(BACKUP_DIR)) {
        return { backups: [] }
      }
      const files = fs.readdirSync(BACKUP_DIR)
      const backupPatterns = {
        megaData: /^(\d+)_mega_data\.json$/,
        desiredItems: /^(\d+)_desired_items\.json$/,
        ilvlList: /^(\d+)_desired_ilvl_list\.json$/,
        petIlvlList: /^(\d+)_desired_pet_ilvl_list\.json$/,
      }
      const pattern = backupPatterns[target]
      if (!pattern) {
        return { error: "Unknown target", backups: [] }
      }
      const backupFiles = files
        .filter((file) => pattern.test(file))
        .map((file) => {
          const match = file.match(pattern)
          if (!match) return null
          const timestamp = parseInt(match[1], 10)
          // Parse timestamp: YYYYMMDDHH
          const year = Math.floor(timestamp / 1_000_000)
          const month = Math.floor((timestamp % 1_000_000) / 10_000)
          const day = Math.floor((timestamp % 10_000) / 100)
          const hour = timestamp % 100
          const date = new Date(year, month - 1, day, hour)
          return {
            filename: file,
            timestamp,
            date: date.toISOString(),
            displayDate: date.toLocaleString(),
          }
        })
        .filter((item) => item !== null)
        .sort((a, b) => b.timestamp - a.timestamp) // Most recent first

      return { backups: backupFiles }
    } catch (err) {
      console.error("Failed to list backups:", err)
      return { error: err.message, backups: [] }
    }
  })

  ipcMain.handle("restore-backup", (_event, { target, filename }) => {
    try {
      // Sanitize filename to prevent path traversal
      if (
        !filename ||
        filename.includes("..") ||
        filename.includes("/") ||
        filename.includes("\\") ||
        filename.includes("\0")
      ) {
        return { error: "Invalid filename" }
      }
      // Normalize and validate path
      const normalizedFilename = path.basename(filename)
      const backupPath = path.join(BACKUP_DIR, normalizedFilename)
      const resolvedPath = path.resolve(backupPath)
      const resolvedBackupDir = path.resolve(BACKUP_DIR)
      if (!resolvedPath.startsWith(resolvedBackupDir)) {
        return { error: "Invalid backup path" }
      }
      if (!fs.existsSync(backupPath)) {
        return { error: "Backup file not found" }
      }
      const data = readJson(backupPath, null)
      if (data === null) {
        return { error: "Failed to read backup file" }
      }
      const targetPath = FILES[target]
      if (!targetPath) {
        return { error: "Unknown target" }
      }
      writeJson(targetPath, data)
      const logMsg = `[RESTORE] Restored ${filename} to ${path.basename(
        targetPath
      )}\n`
      console.log(logMsg.trim())
      sendToLogPanel(logMsg)
      return { success: true, data }
    } catch (err) {
      console.error("Failed to restore backup:", err)
      return { error: err.message }
    }
  })

  ipcMain.handle("run-mega", () => {
    if (alertsProcess) {
      return { alreadyRunning: true }
    }

    // Set up log callback to send to renderer and write to file
    const sendLog = (line) => {
      // Write to log file
      if (logFileStream) {
        logFileStream.write(line)
      }
      // Send to renderer for UI display
      BrowserWindow.getAllWindows().forEach((win) =>
        win.webContents.send("mega-log", line)
      )
    }

    const sendExit = (code) => {
      BrowserWindow.getAllWindows().forEach((win) =>
        win.webContents.send("mega-exit", code)
      )
      alertsProcess = null
    }

    try {
      // Load and run mega-alerts directly in this process
      const megaAlertsPath = path.join(__dirname, "mega-alerts.js")
      const resolvedPath = require.resolve(megaAlertsPath)

      // Clear module cache to ensure fresh state on each run
      // This prevents STOP_REQUESTED flag from persisting across runs
      delete require.cache[resolvedPath]

      const megaAlerts = require(megaAlertsPath)

      // Set paths first (important for packaged apps)
      if (megaAlerts.setPaths) {
        megaAlerts.setPaths(DATA_DIR, STATIC_DIR)
      }

      // Set up callbacks
      if (megaAlerts.setLogCallback) {
        megaAlerts.setLogCallback(sendLog)
      }
      if (megaAlerts.setStopCallback) {
        megaAlerts.setStopCallback(() => sendExit(0))
      }

      // Run in background (don't await - it runs continuously)
      megaAlerts.main().catch((err) => {
        sendLog(`Error in mega alerts: ${err.message || err}`)
        if (err.stack) {
          sendLog(err.stack)
        }
        sendExit(1)
      })

      alertsProcess = true // Mark as running
      return { started: true }
    } catch (err) {
      alertsProcess = null
      sendLog(`Error launching alerts: ${err.message || err}`)
      if (err.stack) {
        sendLog(err.stack)
      }
      sendExit(1)
      return { error: err.message || String(err) }
    }
  })

  ipcMain.handle("stop-mega", async () => {
    if (alertsProcess) {
      try {
        const megaAlertsPath = path.join(__dirname, "mega-alerts.js")
        const megaAlerts = require(megaAlertsPath)
        if (megaAlerts.requestStop) {
          megaAlerts.requestStop()
        }

        // Wait for stop to complete with timeout fallback
        // The stopCallback (sendExit) will set alertsProcess = null when stop completes
        await new Promise((resolve) => {
          // Check if already stopped (callback may have fired synchronously)
          if (!alertsProcess) {
            resolve()
            return
          }

          let intervalId
          let timeoutId

          const cleanup = () => {
            if (intervalId) clearInterval(intervalId)
            if (timeoutId) clearTimeout(timeoutId)
          }

          // Poll to see if state was cleared by callback
          intervalId = setInterval(() => {
            if (!alertsProcess) {
              cleanup()
              resolve()
            }
          }, 50) // Check every 50ms

          // Timeout fallback: clear state after 1 second even if callback didn't fire
          timeoutId = setTimeout(() => {
            cleanup()
            if (alertsProcess) {
              alertsProcess = null
            }
            resolve()
          }, 1000)
        })
      } catch (err) {
        console.error("Error stopping alerts:", err)
        alertsProcess = null
      }
    }
    return { stopped: true }
  })

  // Realm list handlers
  ipcMain.handle("load-realm-lists", () => {
    const lists = {}
    for (const [region, filePath] of Object.entries(REALM_FILES)) {
      lists[region] = readJson(filePath, {})
    }
    return lists
  })

  ipcMain.handle("save-realm-list", (_event, region, realms) => {
    const filePath = REALM_FILES[region]
    if (!filePath) return { error: "Unknown region" }
    const logMsg = `[SAVE] Saving realm list for ${region} to: ${filePath}\n`
    console.log(logMsg.trim())
    sendToLogPanel(logMsg)
    const normalized = {}
    Object.entries(realms || {}).forEach(([k, v]) => {
      const id = Number(v)
      if (!Number.isNaN(id)) {
        normalized[String(k)] = id
      }
    })
    writeJson(filePath, normalized)
    const successMsg = `[SAVE] Successfully saved realm list for ${region}\n`
    console.log(successMsg.trim())
    sendToLogPanel(successMsg)
    return normalized
  })

  // Data directory selection handlers
  ipcMain.handle("get-data-dir", () => {
    return DATA_DIR
  })

  ipcMain.handle("get-custom-data-dir", () => {
    const config = loadConfig()
    return config.customDataDir || null
  })

  ipcMain.handle("set-custom-data-dir", async (_event, dirPath) => {
    if (!dirPath) {
      // Clear custom directory - use default
      const config = loadConfig()
      config.customDataDir = null
      saveConfig(config)
      return { success: true, dataDir: getDataDir() }
    }

    // Validate directory exists and is writable
    try {
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true })
      }
      // Test write permissions
      const testFile = path.join(dirPath, ".test-write")
      fs.writeFileSync(testFile, "test")
      fs.unlinkSync(testFile)

      const config = loadConfig()
      config.customDataDir = dirPath
      saveConfig(config)

      const logMsg = `[CONFIG] Custom data directory set to: ${dirPath}\n`
      console.log(logMsg.trim())
      sendToLogPanel(logMsg)

      return { success: true, dataDir: dirPath }
    } catch (err) {
      const errorMsg = `[CONFIG] Failed to set data directory: ${err.message}\n`
      console.error(errorMsg.trim())
      sendToLogPanel(errorMsg)
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle("select-data-dir", async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openDirectory", "createDirectory"],
      title: "Select Data Directory",
    })

    if (result.canceled || !result.filePaths.length) {
      return { canceled: true }
    }

    const selectedDir = result.filePaths[0]

    // Validate directory exists and is writable
    try {
      if (!fs.existsSync(selectedDir)) {
        fs.mkdirSync(selectedDir, { recursive: true })
      }
      // Test write permissions
      const testFile = path.join(selectedDir, ".test-write")
      fs.writeFileSync(testFile, "test")
      fs.unlinkSync(testFile)

      const config = loadConfig()
      config.customDataDir = selectedDir
      saveConfig(config)

      const logMsg = `[CONFIG] Custom data directory set to: ${selectedDir}\n`
      console.log(logMsg.trim())
      sendToLogPanel(logMsg)

      return { success: true, dataDir: selectedDir }
    } catch (err) {
      const errorMsg = `[CONFIG] Failed to set data directory: ${err.message}\n`
      console.error(errorMsg.trim())
      sendToLogPanel(errorMsg)
      return { success: false, error: err.message }
    }
  })

  // Zoom level handlers
  ipcMain.handle("get-zoom-level", () => {
    if (!mainWindow) return { zoom: 1.0 }
    const zoomFactor = mainWindow.webContents.getZoomFactor()
    return { zoom: zoomFactor }
  })

  ipcMain.handle("set-zoom-level", (_event, zoomFactor) => {
    if (!mainWindow) return { success: false }
    try {
      mainWindow.webContents.setZoomFactor(zoomFactor)
      return { success: true, zoom: zoomFactor }
    } catch (err) {
      return { success: false, error: err.message }
    }
  })
}

app.whenReady().then(async () => {
  const startupMsg1 = `[STARTUP] Data directory: ${DATA_DIR}\n`
  const startupMsg2 = `[STARTUP] Static directory: ${STATIC_DIR}\n`
  console.log(startupMsg1.trim())
  console.log(startupMsg2.trim())
  // Ensure data files exist before setting up IPC handlers
  // This prevents race conditions where renderer calls IPC before files exist
  ensureDataFiles()

  // Send startup messages to log panel after window is created
  setTimeout(() => {
    BrowserWindow.getAllWindows().forEach((win) => {
      win.webContents.send("mega-log", startupMsg1)
      win.webContents.send("mega-log", startupMsg2)
    })
    if (logFileStream) {
      logFileStream.write(startupMsg1)
      logFileStream.write(startupMsg2)
    }
  }, 500) // Small delay to ensure window is ready

  // Create window and set up IPC after files are ready
  createWindow()
  setupIpc()

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on("window-all-closed", () => {
  // Quit the app when all windows are closed (including on macOS)
  app.quit()
})

app.on("before-quit", () => {
  // Close log file stream on app quit
  if (logFileStream) {
    const endMessage = `=== Log ended at ${new Date().toISOString()} ===\n`
    logFileStream.write(endMessage)
    logFileStream.end()
    logFileStream = null
  }
})
