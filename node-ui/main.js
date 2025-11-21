const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "AzerothAuctionAssassinData");
const BACKUP_DIR = path.join(DATA_DIR, "backup");

const FILES = {
  megaData: path.join(DATA_DIR, "mega_data.json"),
  desiredItems: path.join(DATA_DIR, "desired_items.json"),
  desiredPets: path.join(DATA_DIR, "desired_pets.json"),
  ilvlList: path.join(DATA_DIR, "desired_ilvl_list.json"),
  petIlvlList: path.join(DATA_DIR, "desired_pet_ilvl_list.json"),
};

const REALM_FILES = {
  EU: path.join(DATA_DIR, "eu-wow-connected-realm-ids.json"),
  NA: path.join(DATA_DIR, "na-wow-connected-realm-ids.json"),
  EUCLASSIC: path.join(DATA_DIR, "euclassic-wow-connected-realm-ids.json"),
  NACLASSIC: path.join(DATA_DIR, "naclassic-wow-connected-realm-ids.json"),
  NASODCLASSIC: path.join(DATA_DIR, "nasodclassic-wow-connected-realm-ids.json"),
  EUSODCLASSIC: path.join(DATA_DIR, "eusodclassic-wow-connected-realm-ids.json"),
};

let alertsProcess = null;

function readJson(filePath, fallback) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch (err) {
    return fallback;
  }
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

function getTimestampInt() {
  const now = new Date();
  return (
    now.getFullYear() * 1_000_000 +
    (now.getMonth() + 1) * 10_000 +
    now.getDate() * 100 +
    now.getHours()
  );
}

function saveBackup(fileType, data) {
  try {
    fs.mkdirSync(BACKUP_DIR, { recursive: true });
    const timestamp = getTimestampInt();
    const backupFilenames = {
      megaData: `${timestamp}_mega_data.json`,
      desiredItems: `${timestamp}_desired_items.json`,
      desiredPets: `${timestamp}_desired_pets.json`,
      ilvlList: `${timestamp}_desired_ilvl_list.json`,
      petIlvlList: `${timestamp}_desired_pet_ilvl_list.json`,
    };
    const backupFilename = backupFilenames[fileType];
    if (backupFilename) {
      const backupPath = path.join(BACKUP_DIR, backupFilename);
      writeJson(backupPath, data);
    }
  } catch (err) {
    console.error("Failed to create backup:", err);
  }
}

function ensureDataFiles() {
  fs.mkdirSync(DATA_DIR, { recursive: true });

  const defaults = {
    [FILES.megaData]: readJson(
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
        SCAN_TIME_MIN: 1,
        SCAN_TIME_MAX: 3,
        NO_LINKS: false,
        NO_RUSSIAN_REALMS: false,
        DISCOUNT_PERCENT: 10,
        TOKEN_PRICE: 0,
        REFRESH_ALERTS: false,
        DEBUG: false,
        FACTION: "all",
      }
    ),
    [FILES.desiredItems]: {},
    [FILES.desiredPets]: {},
    [FILES.ilvlList]: [],
    [FILES.petIlvlList]: [],
  };

  for (const [filePath, fallback] of Object.entries(defaults)) {
    if (!fs.existsSync(filePath)) {
      writeJson(filePath, fallback);
    }
  }

  // Initialize realm list files if they don't exist (empty objects)
  // They will be populated by the reset function using hardcoded data
  for (const [region, filePath] of Object.entries(REALM_FILES)) {
    if (!fs.existsSync(filePath)) {
      writeJson(filePath, {});
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
  ]);
  const intKeys = new Set([
    "MEGA_THREADS",
    "SCAN_TIME_MIN",
    "SCAN_TIME_MAX",
    "TOKEN_PRICE",
  ]);

  const output = { ...input };
  for (const key of Object.keys(output)) {
    if (boolKeys.has(key)) {
      output[key] = Boolean(output[key]);
    } else if (intKeys.has(key)) {
      const num = Number(output[key]);
      output[key] = Number.isFinite(num) ? num : 0;
    }
  }
  return output;
}

function normalizeKV(input) {
  const out = {};
  Object.entries(input || {}).forEach(([k, v]) => {
    const num = Number(v);
    if (!Number.isNaN(num)) {
      out[String(k)] = num;
    }
  });
  return out;
}

function normalizeIlvlRules(list) {
  if (!Array.isArray(list)) return [];
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
        ? rule.bonus_lists.map((id) => Number(id)).filter((n) => !Number.isNaN(n))
        : [],
    }))
    .filter((rule) => rule.buyout > 0);
}

function normalizePetIlvlRules(list) {
  if (!Array.isArray(list)) return [];
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
    .filter((rule) => rule.petID && rule.price > 0);
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 1000,
    minHeight: 720,
    backgroundColor: "#0c1116",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));
}

function setupIpc() {
  ipcMain.handle("load-state", () => {
    ensureDataFiles();
    return {
      megaData: readJson(FILES.megaData, {}),
      desiredItems: readJson(FILES.desiredItems, {}),
      desiredPets: readJson(FILES.desiredPets, {}),
      ilvlList: readJson(FILES.ilvlList, []),
      petIlvlList: readJson(FILES.petIlvlList, []),
      processRunning: Boolean(alertsProcess),
    };
  });

  ipcMain.handle("save-mega-data", (_event, payload) => {
    const normalized = normalizeMegaData(payload || {});
    writeJson(FILES.megaData, normalized);
    saveBackup("megaData", normalized);
    return normalized;
  });

  ipcMain.handle("save-items", (_event, payload) => {
    const normalized = normalizeKV(payload || {});
    writeJson(FILES.desiredItems, normalized);
    saveBackup("desiredItems", normalized);
    return normalized;
  });

  ipcMain.handle("save-pets", (_event, payload) => {
    const normalized = normalizeKV(payload || {});
    writeJson(FILES.desiredPets, normalized);
    saveBackup("desiredPets", normalized);
    return normalized;
  });

  ipcMain.handle("save-ilvl", (_event, payload) => {
    const normalized = normalizeIlvlRules(payload || []);
    writeJson(FILES.ilvlList, normalized);
    saveBackup("ilvlList", normalized);
    return normalized;
  });

  ipcMain.handle("save-pet-ilvl", (_event, payload) => {
    const normalized = normalizePetIlvlRules(payload || []);
    writeJson(FILES.petIlvlList, normalized);
    saveBackup("petIlvlList", normalized);
    return normalized;
  });

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
        SCAN_TIME_MIN: 1,
        SCAN_TIME_MAX: 3,
        NO_LINKS: false,
        NO_RUSSIAN_REALMS: false,
        DISCOUNT_PERCENT: 10,
        TOKEN_PRICE: 0,
        REFRESH_ALERTS: false,
        DEBUG: false,
        FACTION: "all",
      }
    );
    const normalized = normalizeMegaData(defaultData);
    writeJson(FILES.megaData, normalized);
    saveBackup("megaData", normalized);
    return normalized;
  });

  ipcMain.handle("reset-items", () => {
    const normalized = normalizeKV({});
    writeJson(FILES.desiredItems, normalized);
    saveBackup("desiredItems", normalized);
    return normalized;
  });

  ipcMain.handle("reset-ilvl", () => {
    const normalized = normalizeIlvlRules([]);
    writeJson(FILES.ilvlList, normalized);
    saveBackup("ilvlList", normalized);
    return normalized;
  });

  ipcMain.handle("reset-pet-ilvl", () => {
    const normalized = normalizePetIlvlRules([]);
    writeJson(FILES.petIlvlList, normalized);
    saveBackup("petIlvlList", normalized);
    return normalized;
  });

  ipcMain.handle("import-json", async (_event, { target }) => {
    const targetPath = FILES[target];
    if (!targetPath) return { error: "Unknown target" };
    const res = await dialog.showOpenDialog({
      properties: ["openFile"],
      filters: [{ name: "JSON", extensions: ["json"] }],
    });
    if (res.canceled || !res.filePaths.length) return { canceled: true };
    const src = res.filePaths[0];
    const data = readJson(src, null);
    if (data === null) return { error: "Failed to read JSON" };
    writeJson(targetPath, data);
    saveBackup(target, data);
    return { data };
  });

  ipcMain.handle("export-json", async (_event, { target }) => {
    const targetPath = FILES[target];
    if (!targetPath) return { error: "Unknown target" };
    const res = await dialog.showSaveDialog({
      defaultPath: path.basename(targetPath),
      filters: [{ name: "JSON", extensions: ["json"] }],
    });
    if (res.canceled || !res.filePath) return { canceled: true };
    const data = readJson(targetPath, null);
    if (data === null) return { error: "Failed to read source JSON" };
    writeJson(res.filePath, data);
    return { exported: res.filePath };
  });

  ipcMain.handle("run-mega", () => {
    if (alertsProcess) {
      return { alreadyRunning: true };
    }

    // Set up log callback to send to renderer
    const sendLog = (line) => {
      BrowserWindow.getAllWindows().forEach((win) =>
        win.webContents.send("mega-log", line)
      );
    };

    const sendExit = (code) => {
      BrowserWindow.getAllWindows().forEach((win) =>
        win.webContents.send("mega-exit", code)
      );
      alertsProcess = null;
    };

    try {
      // Load and run mega-alerts directly in this process
      const megaAlertsPath = path.join(__dirname, "mega-alerts.js");
      const megaAlerts = require(megaAlertsPath);
      
      // Set up callbacks
      if (megaAlerts.setLogCallback) {
        megaAlerts.setLogCallback(sendLog);
      }
      if (megaAlerts.setStopCallback) {
        megaAlerts.setStopCallback(() => sendExit(0));
      }

      // Run in background (don't await - it runs continuously)
      megaAlerts.main().catch((err) => {
        sendLog(`Error in mega alerts: ${err.message || err}`);
        if (err.stack) {
          sendLog(err.stack);
        }
        sendExit(1);
      });

      alertsProcess = true; // Mark as running
      return { started: true };
    } catch (err) {
      alertsProcess = null;
      sendLog(`Error launching alerts: ${err.message || err}`);
      if (err.stack) {
        sendLog(err.stack);
      }
      sendExit(1);
      return { error: err.message || String(err) };
    }
  });

  ipcMain.handle("stop-mega", () => {
    if (alertsProcess) {
      try {
        const megaAlertsPath = path.join(__dirname, "mega-alerts.js");
        const megaAlerts = require(megaAlertsPath);
        if (megaAlerts.requestStop) {
          megaAlerts.requestStop();
        }
      } catch (err) {
        console.error("Error stopping alerts:", err);
      }
      alertsProcess = null;
    }
    return { stopped: true };
  });

  // Realm list handlers
  ipcMain.handle("load-realm-lists", () => {
    const lists = {};
    for (const [region, filePath] of Object.entries(REALM_FILES)) {
      lists[region] = readJson(filePath, {});
    }
    return lists;
  });

  ipcMain.handle("save-realm-list", (_event, region, realms) => {
    const filePath = REALM_FILES[region];
    if (!filePath) return { error: "Unknown region" };
    const normalized = {};
    Object.entries(realms || {}).forEach(([k, v]) => {
      const id = Number(v);
      if (!Number.isNaN(id)) {
        normalized[String(k)] = id;
      }
    });
    writeJson(filePath, normalized);
    return normalized;
  });
}

app.whenReady().then(() => {
  ensureDataFiles();
  createWindow();
  setupIpc();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
