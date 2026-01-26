/* eslint-env node, es6 */
/* global require, __dirname, console, Buffer, URLSearchParams, module, AbortController, setTimeout, clearTimeout */
const fs = require("fs")
const path = require("path")
const { setTimeout: delay } = require("timers/promises")
const { fetch } = require("undici")

// Directory paths - will be set by setPaths() in packaged apps
let ROOT = path.resolve(__dirname, "..")
let DATA_DIR = path.join(ROOT, "AzerothAuctionAssassinData")
// eslint-disable-next-line no-unused-vars
let STATIC_DIR // Set by setPaths() for API compatibility, no longer used for reading files
const SADDLEBAG_URL = "https://api.saddlebagexchange.com"
const RAIDBOTS_BASE = "https://www.raidbots.com/static/data/live"
const RAW_GITHUB_BACKUP_PATH =
  "https://raw.githubusercontent.com/ff14-advanced-market-search/AzerothAuctionAssassin/refs/heads/main/StaticData"

/**
 * Build equippable-items lookup { id: { baseItemLevel } } from Raidbots array or dict.
 */
function normalizeEquippableItems(data) {
  if (!data || typeof data !== "object") return {}
  if (Array.isArray(data)) {
    const out = {}
    for (const e of data) {
      if (e && typeof e === "object" && "id" in e) {
        out[String(e.id)] = { baseItemLevel: e.itemLevel }
      }
    }
    return out
  }
  return data
}

// Stop flag and callbacks for Electron integration
let STOP_REQUESTED = false
let logCallback = null
let stopCallback = null

/**
 * Set directory paths (used by Electron main process in packaged apps)
 * @param {string} dataDir - Path to AzerothAuctionAssassinData directory
 * @param {string} staticDir - Path to StaticData directory
 */
function setPaths(dataDir, staticDir) {
  DATA_DIR = dataDir
  STATIC_DIR = staticDir
  ROOT = path.dirname(dataDir)
}

/**
 * Set callback function for logging messages
 * Used by Electron main process to send logs to renderer
 */
function setLogCallback(callback) {
  logCallback = callback
}

/**
 * Set callback function for when alerts are stopped
 * Used by Electron main process to notify renderer
 */
function setStopCallback(callback) {
  stopCallback = callback
}

/**
 * Request that the alert loop stop
 * Sets STOP_REQUESTED flag and calls stop callback if set
 */
function requestStop() {
  STOP_REQUESTED = true
  if (stopCallback) {
    stopCallback()
  }
}

/**
 * Reset module-level state
 * Clears STOP_REQUESTED flag and callbacks to ensure fresh state on each run
 * This is preferred over deleting from require.cache as it's more explicit and testable
 */
function reset() {
  STOP_REQUESTED = false
  logCallback = null
  stopCallback = null
}

// Local logging functions that use callback if set (for Electron integration)
const originalLog = console.log
const originalError = console.error

function log(...args) {
  originalLog(...args)
  if (logCallback) {
    logCallback(args.join(" ") + "\n")
  }
}

function logError(...args) {
  originalError(...args)
  if (logCallback) {
    // Format error messages properly, including stack traces for Error objects
    // Safely handle errors to prevent circular reference issues
    const errorMsg = args
      .map((arg) => {
        if (arg instanceof Error) {
          try {
            // Safely extract message and stack, limiting stack trace length
            const message = arg.message || String(arg)
            let stack = ""
            try {
              stack = arg.stack || ""
              // Limit stack trace to prevent excessive recursion
              if (stack.length > 2000) {
                stack = stack.substring(0, 2000) + "... (truncated)"
              }
            } catch {
              // If accessing stack causes issues, skip it
              stack = ""
            }
            return `${message}${stack ? "\n" + stack : ""}`
          } catch {
            // Fallback if error formatting fails
            return String(arg)
          }
        }
        try {
          return String(arg)
        } catch {
          return "[Unable to stringify argument]"
        }
      })
      .join(" ")
    logCallback(`[ERROR] ${errorMsg}\n`)
  }
}

/**
 * Read JSON file with fallback value
 */
function readJson(p, fallback) {
  try {
    const raw = fs.readFileSync(p, "utf8")
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

/**
 * Get list of Russian realm IDs to exclude if NO_RUSSIAN_REALMS is enabled
 * Returns retail, classic, and SoD (Season of Discovery) Russian realm IDs
 */
function getRussianRealmIds() {
  const retail = [
    1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922,
  ]
  const classic = [4452, 4474]
  const sod = [5280, 5285, 5829, 5830]
  return [...retail, ...classic, ...sod]
}

/**
 * Create a Discord embed with specified title, description, and fields
 * Uses blurple color code (0x7289da) and adds current users time as footer
 */
function createEmbed(title, description, fields) {
  return {
    title,
    description,
    color: 0x7289da, // Blurple color code
    fields,
    timestamp: new Date().toISOString(), // Discord's native timestamp field (ISO 8601)
  }
}

/**
 * Split a list into chunks of maximum size
 */
function splitList(lst, maxSize) {
  const res = []
  for (let i = 0; i < lst.length; i += maxSize)
    res.push(lst.slice(i, i + maxSize))
  return res
}

/**
 * Format target price information for Discord message
 * @param {Object} auction - Auction object with targetPrice and buyout_prices
 * @returns {string} Formatted target price string, or empty string if no target price
 */
function formatTargetPrice(auction) {
  if (auction.targetPrice === null || auction.targetPrice === undefined) {
    return ""
  }

  const target = Number(auction.targetPrice)
  if (isNaN(target) || target <= 0) {
    return `\`target_price\`: ${auction.targetPrice}\n`
  }

  // Parse buyout_prices - it can be a JSON string, array, or number (for ilvl/pets)
  let actual = null
  if (auction.buyout_prices !== undefined) {
    if (typeof auction.buyout_prices === "number") {
      // For ilvl and pet alerts, buyout_prices is a single number (already in gold)
      actual = auction.buyout_prices
    } else if (typeof auction.buyout_prices === "string") {
      // For regular items, it's a JSON stringified array
      try {
        const buyoutPrices = JSON.parse(auction.buyout_prices)
        if (Array.isArray(buyoutPrices) && buyoutPrices.length > 0) {
          actual = Math.min(
            ...buyoutPrices
              .map((p) => Number(p))
              .filter((n) => !isNaN(n) && n > 0)
          )
        }
      } catch {
        // If parsing fails, try to extract numbers from the string
        const match = auction.buyout_prices.match(/\[(.*?)\]/)
        if (match) {
          const buyoutPrices = match[1]
            .split(",")
            .map((s) => Number(s.trim()))
            .filter((n) => !isNaN(n) && n > 0)
          if (buyoutPrices.length > 0) {
            actual = Math.min(...buyoutPrices)
          }
        }
      }
    } else if (Array.isArray(auction.buyout_prices)) {
      // Already an array
      const validPrices = auction.buyout_prices
        .map((p) => Number(p))
        .filter((n) => !isNaN(n) && n > 0)
      if (validPrices.length > 0) {
        actual = Math.min(...validPrices)
      }
    }
  }

  // If we couldn't parse a valid price, just show target price
  if (actual === null || isNaN(actual) || actual <= 0) {
    return `\`target_price\`: ${auction.targetPrice}\n`
  }

  // Only show savings if actual price is below target
  if (actual >= target) {
    return `\`target_price\`: ${auction.targetPrice}\n`
  }

  const percentBelow = Math.round(((target - actual) / target) * 100)
  const goldBelow = Math.round(target - actual)
  return `\`target_price\`: ${
    auction.targetPrice
  }\n\`Below_Target\`: ${percentBelow}% / ${goldBelow.toLocaleString()}g\n`
}

/**
 * HTTP request helper with retry logic
 * Retries up to 3 times with 500ms delay between attempts
 */
async function httpJson(url, opts = {}, retries = 3, timeoutMs = 5000) {
  let lastErr
  for (let i = 0; i < retries; i++) {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, timeoutMs)

    try {
      const res = await fetch(url, {
        ...opts,
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (!res.ok) {
        lastErr = new Error(`${res.status} ${res.statusText}`)
        await delay(500)
        continue
      }
      return await res.json()
    } catch (err) {
      clearTimeout(timeoutId)
      if (err.name === "AbortError") {
        lastErr = new Error(`Request timeout after ${timeoutMs}ms`)
      } else {
        lastErr = err
      }
      await delay(500)
    }
  }
  throw lastErr
}

/**
 * Send a Discord embed message to the webhook
 */
async function sendDiscordEmbed(webhook, embed) {
  try {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ embeds: [embed] }),
    })
    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error")
      logError(
        `Discord webhook failed: ${response.status} ${response.statusText}`,
        errorText
      )
    }
  } catch (error) {
    logError("Failed to send Discord embed:", error)
  }
}

/**
 * Send a plain text Discord message to the webhook
 */
async function sendDiscordMessage(webhook, message) {
  try {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: message }),
    })
    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error")
      logError(
        `Discord webhook failed: ${response.status} ${response.statusText}`,
        errorText
      )
    }
  } catch (error) {
    logError("Failed to send Discord message:", error)
  }
}

/**
 * Main data class for managing auction house sniper configuration and state
 * Handles loading configuration, desired items, ilvl rules, and pet rules
 */
class MegaData {
  constructor() {
    // Load the raw configuration file (the raw file users can write their input into)
    this.cfg = readJson(path.join(DATA_DIR, "mega_data.json"), {})
    this.WEBHOOK_URL = this.cfg.MEGA_WEBHOOK_URL
    this.REGION = this.cfg.WOW_REGION

    // Set optional configuration variables with defaults
    this.THREADS = Math.max(1, this.normalizeInt(this.cfg.MEGA_THREADS, 48)) // Default to 48 threads, min 1
    this.SCAN_TIME_MIN = this.normalizeInt(this.cfg.SCAN_TIME_MIN, 1) // Minutes before data update to start scans
    this.SCAN_TIME_MAX = this.normalizeInt(this.cfg.SCAN_TIME_MAX, 3) // Minutes after data update to stop scans
    this.REFRESH_ALERTS = Boolean(this.cfg.REFRESH_ALERTS) // Refresh alerts every 1 hour
    this.SHOW_BIDPRICES = Boolean(this.cfg.SHOW_BID_PRICES ?? false) // Show items with bid prices
    this.EXTRA_ALERTS = this.cfg.EXTRA_ALERTS // JSON array of extra alert minutes
    this.NO_RUSSIAN_REALMS = Boolean(this.cfg.NO_RUSSIAN_REALMS) // Removes alerts from Russian Realms
    this.USE_POST_MIDNIGHT_ILVL = Boolean(
      this.cfg.USE_POST_MIDNIGHT_ILVL ?? true
    ) // Post-midnight ilvl (Raidbots era-based); false = legacy Saddlebag
    this.DEBUG = Boolean(this.cfg.DEBUG) // Trigger a scan on all realms once for testing
    this.NO_LINKS = Boolean(this.cfg.NO_LINKS) // Disable all Wowhead, undermine and saddlebag links
    this.TOKEN_PRICE =
      typeof this.cfg.TOKEN_PRICE === "number"
        ? this.cfg.TOKEN_PRICE
        : undefined

    // Classic regions don't have undermine exchange, so use wowhead links
    // Classic also needs faction selection (all, horde, alliance, booty bay)
    if (String(this.REGION).includes("CLASSIC")) {
      this.WOWHEAD_LINK = true
      this.FACTION = this.cfg.FACTION ?? "all"
    } else {
      this.WOWHEAD_LINK = Boolean(this.cfg.WOWHEAD_LINK)
      this.FACTION = "all" // Retail uses cross-faction AH by default
    }

    // Setup items to snipe (synchronous parts)
    this.desiredItems = this.loadDesiredItems()
    this.desiredPetIlvlList = this.loadDesiredPetIlvlList()
    // desiredIlvlList will be loaded in initialize() since it needs async getIlvlItems()
    this.desiredIlvlList = []

    // Load realm names (filtered by NO_RUSSIAN_REALMS if enabled)
    this.WOW_SERVER_NAMES = this.loadRealmNames()

    // Initialize empty sets/objects - will be populated by async initialization
    this.socket_ids = new Set()
    this.speed_ids = new Set()
    this.leech_ids = new Set()
    this.avoidance_ids = new Set()
    this.ilvl_addition = {}
    this.bonuses_by_id = {}
    this.equippable_items = {}
    this.item_curves = {}
    this.item_squish_era = {}
    this.ITEM_NAMES = {}
    this.PET_NAMES = {}
    this.DESIRED_ILVL_NAMES = {}
  }

  /**
   * Async initialization - fetches data from APIs
   * Must be called after construction before using the instance
   */
  async initialize() {
    // Get static lists of ALL bonus id values from raidbots
    // This is the index for all ilvl gear (sockets, leech, avoidance, speed, ilvl additions)
    await this.setBonusIds()

    // Get name dictionaries - only get names of desired items to limit data
    this.ITEM_NAMES = await this.loadItemNames()
    // PET_NAMES from saddlebags (or backup)
    this.PET_NAMES = await this.loadPetNamesBackup()

    // Load desired ilvl list (must be after setBonusIds and getIlvlItems is available)
    this.desiredIlvlList = await this.loadDesiredIlvlList()

    // Get item names from desired ilvl entries
    this.buildIlvlNames()

    // Get upload times - initially empty, will be populated dynamically from each scan
    this.upload_timers = this.loadUploadTimers()

    // OAuth token management
    this.access_token = ""
    this.access_token_creation_unix_time = 0
    this._tokenRefreshPromise = null // Track in-flight token refresh to prevent race conditions
  }

  /**
   * Normalize integer value with fallback
   * Converts string numbers to integers, returns fallback if invalid
   */
  normalizeInt(val, fallback) {
    if (typeof val === "number" && Number.isFinite(val)) return val
    const n = Number(val)
    return Number.isFinite(n) ? n : fallback
  }

  /**
   * Load desired items from JSON file
   * Converts string keys to integer keys and float values
   */
  loadDesiredItems() {
    const raw = readJson(path.join(DATA_DIR, "desired_items.json"), {})
    const out = {}
    Object.entries(raw).forEach(([k, v]) => {
      const id = Number(k)
      if (!Number.isNaN(id)) out[id] = Number(v)
    })
    return out
  }

  /**
   * Load desired ilvl list from JSON file
   * Groups items by ilvl and handles both specific item_ids and broad groups
   * Broad groups don't care about ilvl or item_ids - same generic info for all
   * NOTE: This must be called after initialize() since it uses async getIlvlItems()
   */
  async loadDesiredIlvlList() {
    const file = path.join(DATA_DIR, "desired_ilvl_list.json")
    const list = readJson(file, [])
    if (!Array.isArray(list) || list.length === 0) return []

    const grouped = {}
    const broad = []
    for (const entry of list) {
      if (!entry.item_ids || entry.item_ids.length === 0) {
        broad.push(entry)
      } else {
        grouped[entry.ilvl] = grouped[entry.ilvl] || []
        grouped[entry.ilvl].push(entry.item_ids)
      }
    }

    const rules = []
    const addRules = (
      ilvl,
      entries,
      itemIds,
      itemNames,
      baseIlvls,
      baseReq
    ) => {
      // Process all entries passed (already filtered for grouped entries, all entries for broad)
      for (const entry of entries) {
        const rule = {
          ilvl: entry.ilvl,
          max_ilvl: entry.max_ilvl ?? 10000,
          buyout: Number(entry.buyout),
          sockets: Boolean(entry.sockets),
          speed: Boolean(entry.speed),
          leech: Boolean(entry.leech),
          avoidance: Boolean(entry.avoidance),
          item_ids:
            entry.item_ids && entry.item_ids.length ? entry.item_ids : itemIds,
          required_min_lvl: entry.required_min_lvl ?? 1,
          required_max_lvl: entry.required_max_lvl ?? 1000,
          bonus_lists: entry.bonus_lists ?? [],
          item_names: {},
          base_ilvls: {},
          base_required_levels: {},
        }
        rule.item_ids.forEach((id) => {
          rule.item_names[id] = itemNames[id] ?? "foobar"
          if (!this.USE_POST_MIDNIGHT_ILVL) {
            rule.base_ilvls[id] = baseIlvls[id] ?? 1
          }
          rule.base_required_levels[id] = baseReq[id] ?? 1
        })
        rules.push(rule)
      }
    }

    for (const [ilvlStr, groups] of Object.entries(grouped)) {
      const ilvl = Number(ilvlStr)
      const allIds = groups.flat()
      // Python: get_ilvl_items(ilvl, all_item_ids) - passes ilvl and item_ids
      const { itemNames, itemIds, baseIlvls, baseReq } =
        await this.getIlvlItems(ilvl, allIds)
      // Filter to only include entries with matching ilvl and non-empty item_ids
      // This prevents broad entries (without item_ids) from being processed here
      const matchingEntries = list.filter(
        (entry) =>
          entry.ilvl === ilvl && entry.item_ids && entry.item_ids.length > 0
      )
      addRules(
        ilvl,
        matchingEntries,
        Array.from(itemIds),
        itemNames,
        baseIlvls,
        baseReq
      )
    }

    if (broad.length) {
      // Python: get_ilvl_items() - no params, uses default ilvl=201
      const { itemNames, itemIds, baseIlvls, baseReq } =
        await this.getIlvlItems()
      addRules(0, broad, Array.from(itemIds), itemNames, baseIlvls, baseReq)
    }

    return rules
  }

  /**
   * Load desired pet ilvl list from JSON file
   * Converts pet rules to proper format with numeric values
   */
  loadDesiredPetIlvlList() {
    const file = path.join(DATA_DIR, "desired_pet_ilvl_list.json")
    const list = readJson(file, [])
    const out = []
    for (const pet of list) {
      out.push({
        petID: Number(pet.petID),
        price: Number(pet.price),
        minLevel: Number(pet.minLevel),
        minQuality: Number(pet.minQuality ?? -1),
        excludeBreeds: (pet.excludeBreeds || []).map((b) => Number(b)),
      })
    }
    return out
  }

  /**
   * Load realm names from JSON file
   * Filters out Russian realms if NO_RUSSIAN_REALMS is enabled
   */
  loadRealmNames() {
    const file = path.join(
      DATA_DIR,
      `${String(this.REGION).toLowerCase()}-wow-connected-realm-ids.json`
    )
    let realmNames = readJson(file, {})
    if (this.NO_RUSSIAN_REALMS) {
      const russian = new Set(getRussianRealmIds())
      realmNames = Object.fromEntries(
        Object.entries(realmNames).filter(([, id]) => !russian.has(id))
      )
    }
    return realmNames
  }

  /**
   * Validate that at least one snipe list has data
   * Throws error if all lists are empty
   */
  validateSnipeLists() {
    if (
      Object.keys(this.desiredItems).length === 0 &&
      this.desiredIlvlList.length === 0 &&
      this.desiredPetIlvlList.length === 0
    ) {
      throw new Error(
        "No snipe data found in desired_items, desired_ilvl_list, desired_pet_ilvl_list"
      )
    }
  }

  /**
   * Fetch or return cached Blizzard OAuth access token
   * Tokens are valid for 24 hours, but we refresh after 20 hours to be safe
   * If over 20 hours, make a new token and reset the creation time
   * Uses a shared promise to prevent concurrent refresh requests (race condition)
   */
  async fetchAccessToken(timeoutMs = 30000) {
    // Return cached token if still valid
    if (
      this.access_token &&
      Date.now() / 1000 - this.access_token_creation_unix_time < 20 * 60 * 60
    ) {
      return this.access_token
    }

    // If a refresh is already in progress, return the existing promise
    if (this._tokenRefreshPromise) {
      return this._tokenRefreshPromise
    }

    // Start a new refresh and track it
    this._tokenRefreshPromise = this._doFetchAccessToken(timeoutMs).finally(
      () => {
        // Clear the promise when done (success or failure) so subsequent calls can start a new refresh
        this._tokenRefreshPromise = null
      }
    )

    return this._tokenRefreshPromise
  }

  /**
   * Internal helper to perform the actual token fetch
   * Separated from fetchAccessToken to enable promise sharing for concurrent calls
   */
  async _doFetchAccessToken(timeoutMs = 30000) {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, timeoutMs)

    try {
      const res = await fetch("https://oauth.battle.net/token", {
        method: "POST",
        body: new URLSearchParams({ grant_type: "client_credentials" }),
        headers: {
          Authorization:
            "Basic " +
            Buffer.from(
              `${this.cfg.WOW_CLIENT_ID}:${this.cfg.WOW_CLIENT_SECRET}`
            ).toString("base64"),
        },
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (!res.ok) {
        throw new Error(
          `Failed to get access token: ${res.status} ${await res.text()}`
        )
      }
      const json = await res.json()
      if (!json.access_token) {
        throw new Error(`No access_token in response: ${JSON.stringify(json)}`)
      }
      this.access_token = json.access_token
      this.access_token_creation_unix_time = Math.floor(Date.now() / 1000)
      return this.access_token
    } catch (error) {
      clearTimeout(timeoutId)
      if (error.name === "AbortError") {
        throw new Error(`Access token request timeout after ${timeoutMs}ms`)
      }
      throw error
    }
  }

  /**
   * Get upload timers (collected from realm scans, not from API)
   * Returns the existing upload_timers map which is populated automatically
   * from last-modified headers when scanning realms
   */
  async getUploadTimers() {
    // Upload timers are collected automatically from realm scans via update_local_timers()
    // No need to hit the API endpoint - just return existing timers
    return this.upload_timers
  }

  /**
   * Load upload timers (initially empty)
   * Will be populated dynamically from each scan
   */
  loadUploadTimers() {
    return {}
  }

  /**
   * Send a Discord message using the configured webhook
   */
  send_discord_message(message) {
    return sendDiscordMessage(this.WEBHOOK_URL, message)
  }

  /**
   * Send a Discord embed using the configured webhook
   */
  send_discord_embed(embed) {
    return sendDiscordEmbed(this.WEBHOOK_URL, embed)
  }

  /**
   * Get list of all upload timer objects
   */
  get_upload_time_list() {
    return Object.values(this.upload_timers)
  }

  /**
   * Get set of all upload time minutes (when data updates occur)
   */
  get_upload_time_minutes() {
    return new Set(this.get_upload_time_list().map((r) => r.lastUploadMinute))
  }

  /**
   * Get realm names for a given connected realm ID
   */
  get_realm_names(connectedRealmId) {
    return Object.entries(this.WOW_SERVER_NAMES)
      .filter(([, id]) => id === connectedRealmId)
      .map(([name]) => name)
      .sort((a, b) => a.localeCompare(b))
  }

  /**
   * Make auction house API request for a specific connected realm
   * Updates local timers with last-modified header if available
   * Retries on 429 rate limit errors with 2 second delay
   */
  async makeAhRequest(
    url,
    connectedRealmId,
    timeoutMs = 30000,
    retryCount = 0
  ) {
    const maxRetries = 5
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, timeoutMs)

    try {
      const headers = {
        Authorization: `Bearer ${await this.fetchAccessToken()}`,
      }
      const res = await fetch(url, { headers, signal: controller.signal })
      clearTimeout(timeoutId)
      if (res.status === 429) {
        if (retryCount < maxRetries) {
          log(
            `Rate limited (429) on ${url}, waiting 2 seconds before retry ${
              retryCount + 1
            }/${maxRetries}...`
          )
          await delay(2000)
          return this.makeAhRequest(
            url,
            connectedRealmId,
            timeoutMs,
            retryCount + 1
          )
        }
        throw new Error("429")
      }
      if (res.status !== 200) throw new Error(`${res.status}`)
      const data = await res.json()

      const lastMod = res.headers.get("last-modified")
      if (lastMod) {
        this.update_local_timers(connectedRealmId, lastMod)
      }
      return data
    } catch (error) {
      clearTimeout(timeoutId)
      if (error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeoutMs}ms`)
      }
      // Retry on 429 errors if we haven't exceeded max retries
      if (error.message === "429" && retryCount < maxRetries) {
        log(
          `Rate limited (429) on ${url}, waiting 2 seconds before retry ${
            retryCount + 1
          }/${maxRetries}...`
        )
        await delay(2000)
        return this.makeAhRequest(
          url,
          connectedRealmId,
          timeoutMs,
          retryCount + 1
        )
      }
      throw error
    }
  }

  /**
   * Make commodity auction house API request
   * Commodities use connected realm IDs -1 (NA) or -2 (EU)
   * Retries on 429 rate limit errors with 2 second delay
   */
  async makeCommodityRequest(timeoutMs = 30000, retryCount = 0) {
    const maxRetries = 5
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, timeoutMs)

    try {
      const region = this.REGION
      const endpoint =
        region === "NA"
          ? "https://us.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-us&locale=en_US"
          : "https://eu.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-eu&locale=en_EU"
      const connectedId = region === "NA" ? -1 : -2
      const headers = {
        Authorization: `Bearer ${await this.fetchAccessToken()}`,
      }
      const res = await fetch(endpoint, { headers, signal: controller.signal })
      clearTimeout(timeoutId)
      if (res.status === 429) {
        if (retryCount < maxRetries) {
          log(
            `Rate limited (429) on (${
              this.REGION
            }) commodities, waiting 2 seconds before retry ${
              retryCount + 1
            }/${maxRetries}...`
          )
          await delay(2000)
          return this.makeCommodityRequest(timeoutMs, retryCount + 1)
        }
        throw new Error("429")
      }
      if (res.status !== 200) throw new Error(`${res.status}`)
      const data = await res.json()
      const lastMod = res.headers.get("last-modified")
      if (lastMod) this.update_local_timers(connectedId, lastMod)
      return data
    } catch (error) {
      clearTimeout(timeoutId)
      if (error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeoutMs}ms`)
      }
      // Retry on 429 errors if we haven't exceeded max retries
      if (error.message === "429" && retryCount < maxRetries) {
        log(
          `Rate limited (429) on ${
            this.REGION
          } commodities, waiting 2 seconds before retry ${
            retryCount + 1
          }/${maxRetries}...`
        )
        await delay(2000)
        return this.makeCommodityRequest(timeoutMs, retryCount + 1)
      }
      throw error
    }
  }

  /**
   * Update local upload timers with data from API response
   * Parses last-modified header to determine when data was last updated
   */
  update_local_timers(dataSetID, lastUploadTimeRaw) {
    let tableName
    let dataSetName
    if (dataSetID === -1 || dataSetID === -2) {
      tableName = `${this.REGION}_retail_commodityListings`
      dataSetName = [`${this.REGION} Commodities`]
    } else {
      tableName = `${dataSetID}_singleMinPrices`
      dataSetName = this.get_realm_names(dataSetID)
    }
    const lastUploadMinute = Number(lastUploadTimeRaw.split(":")[1])
    const lastUploadUnix = Math.floor(
      new Date(lastUploadTimeRaw).getTime() / 1000
    )
    this.upload_timers[dataSetID] = {
      dataSetID,
      dataSetName,
      lastUploadMinute,
      lastUploadTimeRaw,
      lastUploadUnix,
      region: this.REGION,
      tableName,
    }
  }

  /**
   * Construct Blizzard API URL for auction house data
   * Handles different regions (NA/EU) and game types (Retail/Classic/SoD)
   */
  construct_api_url(connectedRealmId, endpoint) {
    const base_url = this.REGION.includes("NA")
      ? "https://us.api.blizzard.com"
      : "https://eu.api.blizzard.com"
    let namespace = this.REGION.includes("NA") ? "dynamic-us" : "dynamic-eu"
    const locale = this.REGION.includes("NA") ? "en_US" : "en_EU"
    if (this.REGION.includes("SOD")) {
      namespace = `dynamic-classic1x-${namespace.split("-").pop()}`
    } else if (this.REGION.includes("CLASSIC")) {
      namespace = `dynamic-classic-${namespace.split("-").pop()}`
    }
    return `${base_url}/data/wow/connected-realm/${connectedRealmId}/auctions${endpoint}?namespace=${namespace}&locale=${locale}`
  }

  /**
   * Get auction listings for a single connected realm
   * Handles both regular realms and commodities (-1 for NA, -2 for EU)
   * For Classic realms, handles faction-specific endpoints
   */
  async get_listings_single(connectedRealmId) {
    if (connectedRealmId === -1 || connectedRealmId === -2) {
      try {
        const commodity = await this.makeCommodityRequest()
        return commodity?.auctions || []
      } catch (error) {
        logError("Commodity AH request failed", error)
        return []
      }
    }
    const endpoints = []
    if (this.REGION.includes("CLASSIC")) {
      if (this.FACTION === "alliance") endpoints.push("/2")
      else if (this.FACTION === "horde") endpoints.push("/6")
      else if (this.FACTION === "booty bay") endpoints.push("/7")
      else endpoints.push("/2", "/6", "/7")
    } else {
      endpoints.push("")
    }
    const all = []
    for (const ep of endpoints) {
      try {
        const url = this.construct_api_url(connectedRealmId, ep)
        const data = await this.makeAhRequest(url, connectedRealmId)
        if (data?.auctions && Array.isArray(data.auctions)) {
          // Always use a loop to avoid stack overflow with large arrays
          // Spread operator (all.push(...data.auctions)) can cause "Maximum call stack size exceeded"
          // Performance difference is negligible compared to network latency
          for (const auction of data.auctions) {
            all.push(auction)
          }
        }
      } catch (err) {
        logError("AH request failed", err)
      }
    }
    return all
  }

  /**
   * Get current WoW token price from Blizzard API
   * Returns price in gold (converted from copper)
   * Only works for retail regions (NA/EU)
   */
  async get_wow_token_price() {
    let url
    if (this.REGION === "NA") {
      url =
        "https://us.api.blizzard.com/data/wow/token/index?namespace=dynamic-us&locale=en_US"
    } else if (this.REGION === "EU") {
      url =
        "https://eu.api.blizzard.com/data/wow/token/index?namespace=dynamic-eu&locale=en_EU"
    } else return null

    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      controller.abort()
    }, 5000)

    try {
      const headers = {
        Authorization: `Bearer ${await this.fetchAccessToken()}`,
      }
      const res = await fetch(url, { headers, signal: controller.signal })
      clearTimeout(timeoutId)
      if (!res.ok) return null
      const json = await res.json()
      if (!("price" in json)) return null
      return json.price / 10000
    } catch (error) {
      clearTimeout(timeoutId)
      if (error.name === "AbortError") {
        logError("WoW token price request timeout", error)
      } else {
        logError("Failed to get WoW token price", error)
      }
      return null
    }
  }

  /**
   * Load item names from Saddlebag API or GitHub backup
   * Only loads names for items in desiredItems list to limit data
   */
  async loadItemNames() {
    try {
      const response = await fetch(`${SADDLEBAG_URL}/api/wow/itemnames`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ return_all: true }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const itemNames = await response.json()
      const filtered = {}
      Object.entries(itemNames).forEach(([k, v]) => {
        const id = Number(k)
        if (this.desiredItems[id] !== undefined) filtered[id] = v
      })
      return filtered
    } catch (err) {
      logError("Failed to get item names getting backup from github:", err)
      try {
        const response = await fetch(
          `${RAW_GITHUB_BACKUP_PATH}/item_names.json`
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const itemNames = await response.json()
        const filtered = {}
        Object.entries(itemNames).forEach(([k, v]) => {
          const id = Number(k)
          if (this.desiredItems[id] !== undefined) filtered[id] = v
        })
        return filtered
      } catch (backupErr) {
        logError("Failed to get item names from GitHub backup:", backupErr)
        return {}
      }
    }
  }

  /**
   * Load pet names from Saddlebag API or GitHub backup
   */
  async loadPetNamesBackup() {
    try {
      const response = await fetch(`${SADDLEBAG_URL}/api/wow/itemnames`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pets: true }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const petInfo = await response.json()
      const res = {}
      Object.entries(petInfo).forEach(([k, v]) => {
        const id = Number(k)
        if (!Number.isNaN(id)) res[id] = v
      })
      return res
    } catch (err) {
      logError("Failed to get pet names getting backup from github:", err)
      try {
        const response = await fetch(`${RAW_GITHUB_BACKUP_PATH}/pet_names.json`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const petInfo = await response.json()
        const res = {}
        Object.entries(petInfo).forEach(([k, v]) => {
          const id = Number(k)
          if (!Number.isNaN(id)) res[id] = v
        })
        return res
      } catch (backupErr) {
        logError("Failed to get pet names from GitHub backup:", backupErr)
        return {}
      }
    }
  }

  /**
   * Load bonus IDs from Raidbots API or GitHub backup
   * Gets static lists of ALL bonus id values from raidbots
   * This is the index for all ilvl gear (sockets, leech, avoidance, speed, ilvl additions)
   * Processes the data similar to Python's bonus_ids.py
   */
  async setBonusIds() {
    let bonus = {}
    try {
      // thanks so much to Seriallos (Raidbots) and BinaryHabitat (GoblinStockAlerts) for organizing this data!
      const response = await fetch(`${RAIDBOTS_BASE}/bonuses.json`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const bonusData = await response.json()
      bonus = bonusData
    } catch (err) {
      logError(
        "Failed to get raidbots bonus ids getting backup from github:",
        err
      )
      try {
        const response = await fetch(`${RAW_GITHUB_BACKUP_PATH}/bonuses.json`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        bonus = await response.json()
      } catch (backupErr) {
        logError("Failed to get bonus ids from GitHub backup:", backupErr)
        // Initialize empty sets to prevent undefined errors
        this.socket_ids = new Set()
        this.speed_ids = new Set()
        this.leech_ids = new Set()
        this.avoidance_ids = new Set()
        this.ilvl_addition = {}
        this.bonuses_by_id = {}
        return
      }
    }

    const bonusesById = {}
    for (const [k, v] of Object.entries(bonus)) {
      const id = Number(k)
      if (!Number.isNaN(id)) bonusesById[id] = v
    }
    this.bonuses_by_id = bonusesById

    if (this.USE_POST_MIDNIGHT_ILVL) {
      try {
        const [eq, curves, eras] = await Promise.all([
          fetch(`${RAIDBOTS_BASE}/equippable-items.json`)
            .then((r) => (r.ok ? r.json() : {}))
            .catch(() => {}),
          fetch(`${RAIDBOTS_BASE}/item-curves.json`)
            .then((r) => (r.ok ? r.json() : {}))
            .catch(() => {}),
          fetch(`${RAIDBOTS_BASE}/item-squish-era.json`)
            .then((r) => (r.ok ? r.json() : {}))
            .catch(() => {}),
        ])
        this.equippable_items = normalizeEquippableItems(eq)
        this.item_curves = curves && typeof curves === "object" ? curves : {}
        this.item_squish_era = eras && typeof eras === "object" ? eras : {}
      } catch (e) {
        logError("Failed to fetch post-midnight ilvl data:", e)
      }
    }

    // Process bonus data similar to Python's bonus_ids.py
    const socket = []
    const speed = []
    const leech = []
    const avoidance = []
    const ilvlAdd = {}

    // Debug: capture sample rawStats structure
    let sampleWithRawStats = null

    for (const [idStr, data] of Object.entries(bonus)) {
      const id = Number(idStr)
      if (isNaN(id)) continue

      // Sockets are simple - check if "socket" key exists
      if (data.socket) {
        socket.push(id)
      }

      // Ilvl addition - items with only "id" and "level" keys
      if (typeof data.level === "number") {
        const keys = Object.keys(data)
        if (
          keys.length === 2 &&
          keys.includes("id") &&
          keys.includes("level")
        ) {
          ilvlAdd[id] = data.level
        }
      }

      // Leech, avoidance, speed are in rawStats
      if (data.rawStats && Array.isArray(data.rawStats)) {
        // Capture first sample for debugging
        if (!sampleWithRawStats && data.rawStats.length > 0) {
          sampleWithRawStats = { id, rawStats: data.rawStats }
        }

        for (const stat of data.rawStats) {
          if (typeof stat === "object" && stat !== null) {
            const statValues = Object.values(stat)
            if (statValues.includes("Leech")) {
              leech.push(id)
            }
            if (statValues.includes("Avoidance")) {
              avoidance.push(id)
            }
            if (statValues.includes("RunSpeed")) {
              speed.push(id)
            }
          }
        }
      }
    }

    this.socket_ids = new Set(socket)
    this.speed_ids = new Set(speed)
    this.leech_ids = new Set(leech)
    this.avoidance_ids = new Set(avoidance)
    this.ilvl_addition = ilvlAdd

    // Log what we found (only in debug mode)
    if (this.DEBUG) {
      log(`[BONUS IDS] Loaded ${Object.keys(bonus).length} total bonus entries`)
      log(`[BONUS IDS] Socket IDs: ${socket.length} (${socket.join(", ")})`)
      log(`[BONUS IDS] Speed IDs: ${speed.length} (${speed.join(", ")})`)
      log(`[BONUS IDS] Leech IDs: ${leech.length} (${leech.join(", ")})`)
      log(
        `[BONUS IDS] Avoidance IDs: ${avoidance.length} (${avoidance.join(
          ", "
        )})`
      )
      log(`[BONUS IDS] Ilvl addition entries: ${Object.keys(ilvlAdd).length}`)
    }
  }

  /**
   * Get ilvl items from Saddlebag API or GitHub backup
   * Filters by ilvl and optional item_ids list
   * Returns item names, IDs, base ilvls, and base required levels
   * Matches Python behavior: if item_ids is empty, filter by ilvl (default 201)
   * If item_ids is provided, filter by item_ids and ignore ilvl
   */
  async getIlvlItems(ilvl = 201, item_ids = []) {
    let results = {}
    try {
      // Python behavior: if no item_ids given, reset ilvl to 201
      let actualIlvl = ilvl
      if (!item_ids || item_ids.length === 0) {
        actualIlvl = 201
      }

      const jsonData = {
        ilvl: actualIlvl,
        itemQuality: -1,
        required_level: -1,
        item_class: [2, 4],
        item_subclass: [-1],
        item_ids: item_ids || [],
      }

      const response = await fetch(`${SADDLEBAG_URL}/api/wow/itemdata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jsonData),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      results = await response.json()
    } catch (err) {
      logError("Failed to get ilvl items getting backup from github:", err)
      try {
        const response = await fetch(
          `${RAW_GITHUB_BACKUP_PATH}/ilvl_items.json`
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        results = await response.json()
      } catch (backupErr) {
        logError("Failed to get ilvl items from GitHub backup:", backupErr)
        return {
          itemNames: {},
          itemIds: new Set(),
          baseIlvls: {},
          baseReq: {},
        }
      }
    }

    // Python behavior: if item_ids are given, filter by item_ids and ignore ilvl
    if (item_ids && item_ids.length > 0) {
      const filtered = {}
      for (const [key, value] of Object.entries(results)) {
        if (item_ids.includes(Number(key))) {
          filtered[key] = value
        }
      }
      results = filtered
    }

    const itemNames = {}
    const baseIlvls = {}
    const baseReq = {}
    for (const [k, v] of Object.entries(results)) {
      const id = Number(k)
      itemNames[id] = v.itemName
      baseIlvls[id] = v.ilvl
      baseReq[id] = v.required_level
    }
    return {
      itemNames,
      itemIds: new Set(Object.keys(itemNames).map(Number)),
      baseIlvls,
      baseReq,
    }
  }

  /**
   * Build dictionary of item names for desired ilvl entries
   * Used for displaying item names in alerts
   */
  buildIlvlNames() {
    this.DESIRED_ILVL_NAMES = {}
    for (const rule of this.desiredIlvlList) {
      for (const [idStr, name] of Object.entries(rule.item_names)) {
        this.DESIRED_ILVL_NAMES[Number(idStr)] = name
      }
    }
  }
}

/**
 * Create Undermine Exchange link for a pet
 * All caged battle pets use item ID 82800
 */
function create_oribos_exchange_pet_link(realm_name, pet_id, region) {
  const fixed_realm_name = realm_name
    .toLowerCase()
    .replace(/'/g, "")
    .replace(/ /g, "-")
  const url_region = region === "NA" ? "us" : "eu"
  return `https://undermine.exchange/#${url_region}-${fixed_realm_name}/82800-${pet_id}`
}

/**
 * Create Undermine Exchange link for an item
 */
function create_oribos_exchange_item_link(realm_name, item_id, region) {
  const fixed_realm_name = realm_name
    .toLowerCase()
    .replace(/'/g, "")
    .replace(/ /g, "-")
  const url_region = region === "NA" ? "us" : "eu"
  return `https://undermine.exchange/#${url_region}-${fixed_realm_name}/${item_id}`
}

/**
 * Run tasks in parallel with concurrency limit
 * Uses a pool pattern to limit concurrent executions
 */
async function runPool(tasks, concurrency) {
  // Ensure concurrency is at least 1 to prevent Promise.race([]) hang
  const limit = Math.max(1, Number.isFinite(concurrency) ? concurrency : 1)

  const results = []
  const executing = []
  for (const task of tasks) {
    const p = task()
    results.push(p)
    if (limit <= tasks.length) {
      const e = p.then(() => {
        executing.splice(executing.indexOf(e), 1)
      })
      executing.push(e)
      if (executing.length >= limit) {
        await Promise.race(executing)
      }
    }
  }
  return Promise.all(results)
}

/**
 * Main alert processing function
 * Runs continuously (unless runOnce=true) checking auction house data
 * Blizzard API data only updates 1 time per hour
 * The updates will come on minute X of each hour
 *
 * @param {MegaData} state - MegaData instance with configuration and snipe lists
 * @param {Function} progress - Callback function for progress updates
 * @param {boolean} runOnce - If true, run once and exit (for DEBUG mode)
 */
async function runAlerts(state, progress, runOnce = false) {
  // Reset stop flag at the start of each run
  STOP_REQUESTED = false
  const alert_record = new Set() // Use Set for O(1) lookup
  let last_token_price = null // Track last token price to only alert on changes
  // Upload timers are collected automatically from realm scans via update_local_timers()
  // No need to fetch from API - they'll be populated as we scan realms

  // Helper to create a stable key for an auction
  function getAuctionKey(auction, connected_id) {
    const parts = [connected_id]
    if ("itemID" in auction) {
      parts.push(`item:${auction.itemID}`)
      if ("ilvl" in auction) parts.push(`ilvl:${auction.ilvl}`)
      if ("bonus_ids" in auction && auction.bonus_ids) {
        parts.push(
          `bonus:${Array.from(auction.bonus_ids)
            .sort((a, b) => a - b)
            .join(",")}`
        )
      }
    } else if ("petID" in auction) {
      parts.push(`pet:${auction.petID}`)
      if ("pet_level" in auction) parts.push(`level:${auction.pet_level}`)
      if ("quality" in auction) parts.push(`quality:${auction.quality}`)
      if ("breed" in auction) parts.push(`breed:${auction.breed}`)
    }
    const price_type = "bid_prices" in auction ? "bid_prices" : "buyout_prices"
    if (price_type in auction) {
      parts.push(`${price_type}:${auction[price_type]}`)
    }
    return parts.join("|")
  }

  /**
   * Pull auction data for a single connected realm
   * Processes auctions, checks for matches, and sends Discord alerts
   */
  const pull_single_realm_data = async (connected_id) => {
    const auctions = await state.get_listings_single(connected_id)
    const clean = clean_listing_data(auctions, connected_id)

    if (connected_id === -1 || connected_id === -2) {
      await check_token_price()
    }
    if (!clean || clean.length === 0) return

    const russian = new Set(getRussianRealmIds())
    const suffix =
      clean[0].realmID && russian.has(clean[0].realmID) ? " **(RU)**\n" : "\n"
    const is_russian_realm =
      clean[0].realmID && russian.has(clean[0].realmID)
        ? "**(Russian Realm)**"
        : ""

    const embed_fields = []
    for (const auction of clean) {
      if (STOP_REQUESTED) break
      let id_msg = ""
      let embed_name = ""
      let saddlebag_link_id
      if ("itemID" in auction) {
        saddlebag_link_id = auction.itemID
        if ("tertiary_stats" in auction) {
          const item_name = state.DESIRED_ILVL_NAMES[auction.itemID]
          embed_name = item_name ?? "Unknown Item"
          id_msg += "`itemID:` " + auction.itemID + "\n"
          id_msg += "`ilvl:` " + auction.ilvl + "\n"
          if (auction.tertiary_stats) {
            id_msg += "`tertiary_stats:` " + auction.tertiary_stats + "\n"
          }
          if ("required_lvl" in auction && auction.required_lvl !== null) {
            id_msg += "`required_lvl:` " + auction.required_lvl + "\n"
          }
          if ("bonus_ids" in auction) {
            id_msg +=
              "`bonus_ids:` " +
              JSON.stringify(Array.from(auction.bonus_ids)) +
              "\n"
          }
        } else if (state.ITEM_NAMES[auction.itemID]) {
          embed_name = state.ITEM_NAMES[auction.itemID]
          id_msg += "`itemID:` " + auction.itemID + "\n"
        } else {
          embed_name = "Unknown Item"
          id_msg += "`itemID:` " + auction.itemID + "\n"
        }
      } else {
        saddlebag_link_id = auction.petID
        embed_name =
          state.PET_NAMES[auction.petID] !== undefined
            ? state.PET_NAMES[auction.petID]
            : "Unknown Pet"
        id_msg += "`petID:` " + auction.petID + "\n"
        if ("pet_level" in auction)
          id_msg += "`pet_level:` " + auction.pet_level + "\n"
        if ("quality" in auction)
          id_msg += "`quality:` " + auction.quality + "\n"
        if ("breed" in auction) id_msg += "`breed:` " + auction.breed + "\n"
      }

      let message = id_msg
      const link_label =
        state.WOWHEAD_LINK && "itemID" in auction
          ? "Wowhead link"
          : "Undermine link"
      const link_url =
        state.WOWHEAD_LINK && "itemID" in auction
          ? `https://www.wowhead.com/item=${auction.itemID}`
          : auction.itemlink
      if (!state.NO_LINKS) {
        // Uses ilvl searches for ilvl items, regular searches for others
        // use saddlebag_link_id for non ilvl items, as that corrects for pet ids
        const shoppingListLink =
          "ilvl" in auction && auction.ilvl
            ? `https://saddlebagexchange.com/wow/ilvl-shopping-list?itemId=${saddlebag_link_id}&desiredMinIlvl=${auction.ilvl}`
            : `https://saddlebagexchange.com/wow/shopping-list?itemId=${saddlebag_link_id}`
        message += `[Shopping List](${shoppingListLink})\n`
        const whereToSellUrl =
          "ilvl" in auction && auction.ilvl
            ? `https://saddlebagexchange.com/wow/ilvl-export-search?itemId=${saddlebag_link_id}&ilvl=${auction.ilvl}`
            : `https://saddlebagexchange.com/wow/export-search?itemId=${saddlebag_link_id}`
        message += `[Where to Sell](${whereToSellUrl})\n`
        // normal item links
        message += `[${link_label}](${link_url})\n`
        message += `[Saddlebag link](https://saddlebagexchange.com/wow/item-data/${saddlebag_link_id})\n`
      }
      // Show target price if available (for regular items)
      const targetPriceText = formatTargetPrice(auction)
      if (targetPriceText) {
        message += targetPriceText
      }
      const price_type =
        "bid_prices" in auction ? "bid_prices" : "buyout_prices"
      message += "`" + price_type + "`: " + auction[price_type] + "\n"

      const auctionKey = getAuctionKey(auction, connected_id)
      if (!alert_record.has(auctionKey)) {
        embed_fields.push({ name: embed_name, value: message, inline: true })
        alert_record.add(auctionKey)
      } else {
        // JSON to avoid [object Object]
        log("Already sent this alert", JSON.stringify(auction))
      }
    }

    if (embed_fields.length) {
      let desc = `**region:** ${state.REGION}\n`
      desc += `**realmID:** ${clean[0].realmID ?? ""} ${is_russian_realm}\n`
      desc += `**realmNames:** ${clean[0].realmNames}${suffix}`
      for (const chunk of splitList(embed_fields, 10)) {
        const item_embed = createEmbed(
          `${state.REGION} SNIPE FOUND!`,
          desc,
          chunk
        )
        await state.send_discord_embed(item_embed)
      }
    }
  }

  /**
   * Check WoW token price and send alert if below threshold and price has changed
   * Only alerts when the price changes to avoid duplicate alerts for the same price
   */
  async function check_token_price() {
    try {
      if (state.TOKEN_PRICE) {
        const token_price = await state.get_wow_token_price()
        if (token_price && token_price < state.TOKEN_PRICE) {
          // Only alert if the price has changed from the last known price
          if (last_token_price === null || last_token_price !== token_price) {
            const token_embed = createEmbed(
              `WoW Token Alert - ${state.REGION}`,
              `**Token Price:** ${token_price.toLocaleString()} gold\n**Threshold:** ${state.TOKEN_PRICE.toLocaleString()} gold\n**Region:** ${
                state.REGION
              }`,
              []
            )
            await state.send_discord_embed(token_embed)
            last_token_price = token_price // Store the price after sending alert
          }
        } else {
          // Reset last_token_price if price is now above threshold
          last_token_price = null
        }
      }
    } catch (err) {
      logError("Error checking token price", err)
    }
  }

  function results_dict(
    auction,
    itemlink,
    connected_id,
    realm_names,
    id,
    idType,
    priceType,
    targetPrice = null
  ) {
    const sorted = [...auction].sort((a, b) => a - b)
    const minPrice = sorted[0]
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice,
      targetPrice,
      [`${priceType}_prices`]: JSON.stringify(auction),
    }
  }

  function ilvl_results_dict(
    auction,
    itemlink,
    connected_id,
    realm_names,
    id,
    idType,
    priceType,
    targetPrice = null
  ) {
    const tertiary_stats = Object.entries(auction.tertiary_stats)
      .filter(([, present]) => present)
      .map(([stat]) => stat)
    // Convert price from copper to gold for consistency with other item types
    const priceInGold = auction[priceType] / 10000
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice: priceInGold,
      targetPrice,
      [`${priceType}_prices`]: priceInGold,
      tertiary_stats,
      bonus_ids: auction.bonus_ids,
      ilvl: auction.ilvl,
      required_lvl: auction.required_lvl,
    }
  }

  function pet_ilvl_results_dict(
    auction,
    itemlink,
    connected_id,
    realm_names,
    id,
    idType,
    priceType,
    targetPrice = null
  ) {
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice: auction.buyout,
      targetPrice,
      [`${priceType}_prices`]: auction.buyout,
      pet_level: auction.current_level,
      quality: auction.quality,
      breed: auction.breed,
    }
  }

  /**
   * Resolve post-midnight ilvl from bonus_lists and optional drop_level.
   * Returns number or null if base level missing / unresolvable.
   */
  function resolvePostMidnightIlvl(
    itemId,
    bonusLists,
    dropLevel,
    bonusesById,
    equippableItems,
    itemCurves,
    itemSquishEra
  ) {
    function getBase(itemId, eq) {
      if (!eq || typeof eq !== "object") return null
      const keys = [String(itemId)]
      const n = Number(itemId)
      if (!Number.isNaN(n)) keys.push(n)
      for (const key of keys) {
        if (!(key in eq)) continue
        const e = eq[key]
        if (e && typeof e === "object") {
          const v = e.baseItemLevel ?? e.base_level ?? e.ilvl
          if (v != null) return v
        }
      }
      return null
    }

    function applyCurve(value, curveId, curves) {
      if (!curves || curveId == null) return value
      const c = curves[String(curveId)]
      if (!c) return value
      const points = c.points ?? c.curve ?? []
      if (!Array.isArray(points) || points.length < 2) return value
      try {
        const xs = []
        const ys = []
        for (const p of points) {
          if (Array.isArray(p)) {
            xs.push(p[0])
            ys.push(p[1])
          } else if (p && typeof p === "object") {
            const x = p.playerLevel ?? p.x
            const y = p.itemLevel ?? p.y
            if (x != null && y != null) {
              xs.push(x)
              ys.push(y)
            }
          }
        }
        if (xs.length < 2 || ys.length < 2) return value
        const minX = Math.min(...xs)
        const maxX = Math.max(...xs)
        if (value < minX || value > maxX) return value
        for (let i = 0; i < xs.length; i++) {
          if (value <= xs[i]) {
            if (i === 0) return ys[0]
            const t =
              xs[i] !== xs[i - 1]
                ? (value - xs[i - 1]) / (xs[i] - xs[i - 1])
                : 1
            return Math.floor(ys[i - 1] + t * (ys[i] - ys[i - 1]))
          }
        }
        return ys[ys.length - 1]
      } catch {
        return value
      }
    }

    const base = getBase(itemId, equippableItems)
    // Post-midnight: rely entirely on bonus IDs. Use 0 when no DBC base; itemLevel ops set it.
    let itemLevel = base != null ? Number(base) : 0
    let legacyOffset = 0
    const setLevelOps = {}
    const levelOffsetOps = {}
    const levelOffsetSecondary = []
    const dropLevelOps = {}

    for (const bid of bonusLists || []) {
      const b = bonusesById?.[Number(bid)]
      if (!b || typeof b !== "object") continue

      const il = b.itemLevel
      if (il != null) {
        const era = (il && il.squishEra) ?? 0
        const pr = (il && il.priority) ?? 9999
        const amt = il && typeof il === "object" ? il.amount : il
        if (amt != null) {
          if (!setLevelOps[era]) setLevelOps[era] = []
          setLevelOps[era].push([pr, amt])
        }
      }

      const lo = b.levelOffset
      if (lo != null) {
        const era = (lo && lo.squishEra) ?? 0
        const amt = lo && typeof lo === "object" ? lo.amount : lo
        if (amt != null) {
          if (!levelOffsetOps[era]) levelOffsetOps[era] = []
          levelOffsetOps[era].push(amt)
        }
      }

      const los = b.levelOffsetSecondary
      if (los != null) {
        const amt = los && typeof los === "object" ? los.amount : los
        if (amt != null) levelOffsetSecondary.push(amt)
      }

      const dlc = b.dropLevelCurve
      if (dlc && typeof dlc === "object") {
        const era = dlc.squishEra ?? 0
        const cid = dlc.curveId
        const off = dlc.offset ?? 0
        const pr = dlc.priority ?? 9999
        if (!dropLevelOps[era]) dropLevelOps[era] = []
        dropLevelOps[era].push([pr, cid, off])
      }

      if (typeof b.level === "number") legacyOffset += b.level
    }

    const hasOps =
      Object.keys(setLevelOps).length > 0 ||
      Object.keys(levelOffsetOps).length > 0 ||
      levelOffsetSecondary.length > 0 ||
      Object.keys(dropLevelOps).length > 0

    if (!hasOps) itemLevel += legacyOffset

    let eras = Array.isArray(itemSquishEra) ? itemSquishEra : []
    if (
      eras.length === 0 &&
      itemSquishEra &&
      typeof itemSquishEra === "object"
    ) {
      eras = itemSquishEra.eras ?? itemSquishEra.data ?? []
    }
    if (eras.length === 0) return itemLevel

    for (const eraDef of eras) {
      const curveId =
        eraDef && typeof eraDef === "object"
          ? eraDef.curveId ?? eraDef.curve_id
          : null
      if (curveId != null)
        itemLevel = applyCurve(itemLevel, curveId, itemCurves)

      const eraId =
        eraDef && typeof eraDef === "object"
          ? eraDef.id ?? eraDef.eraId ?? 0
          : 0

      const sl = setLevelOps[eraId] ?? setLevelOps[0]
      if (sl && sl.length) {
        const best = sl.slice().sort((a, b) => a[0] - b[0])[0]
        itemLevel = Number(best[1])
      }

      const dl = dropLevelOps[eraId] ?? dropLevelOps[0]
      if (dl && dl.length && dropLevel != null) {
        const best = dl.slice().sort((a, b) => a[0] - b[0])[0]
        const [, cid, off] = best
        const lookup = cid ? dropLevel : 0
        const scaled = cid ? applyCurve(lookup, cid, itemCurves) : lookup
        itemLevel = Math.floor(Number(scaled)) + Number(off)
      }

      const losEra = levelOffsetOps[eraId] ?? levelOffsetOps[0]
      if (losEra) for (const amt of losEra) itemLevel += Number(amt)
    }

    for (const amt of levelOffsetSecondary) itemLevel += Number(amt)
    return itemLevel
  }

  /**
   * Check if an auction matches the ilvl rule criteria
   * Validates tertiary stats (sockets, leech, avoidance, speed), ilvl, required level, bonus lists, and price
   *
   * Check for a modifier with type 9 and get its value (modifier 9 value equals required playerLevel)
   * If no modifier["type"] == 9 found, use the base required level for report
   */
  function check_tertiary_stats_generic(auction, rule, min_ilvl) {
    if (!auction.item?.bonus_lists) return false
    const item_bonus_ids = new Set(auction.item.bonus_lists)

    const required_lvl =
      auction.item.modifiers?.find((m) => m.type === 9)?.value ??
      rule.base_required_levels[auction.item.id]

    // Check for intersection of bonus_ids with socket/speed/leech/avoidance IDs
    // Python: len(item_bonus_ids & socket_ids) != 0
    // This returns true if any bonus ID matches the stat's bonus IDs
    const tertiary_stats = {
      sockets: intersection(item_bonus_ids, state.socket_ids),
      leech: intersection(item_bonus_ids, state.leech_ids),
      avoidance: intersection(item_bonus_ids, state.avoidance_ids),
      speed: intersection(item_bonus_ids, state.speed_ids),
    }
    const desired = {
      sockets: rule.sockets,
      leech: rule.leech,
      avoidance: rule.avoidance,
      speed: rule.speed,
    }

    // Python: if any(desired_tertiary_stats):
    //         for stat, desired in desired_tertiary_stats.items():
    //             if desired and not tertiary_stats.get(stat, False):
    //                 return False
    // This checks that ALL desired stats are present in the item
    if (Object.values(desired).some(Boolean)) {
      for (const [stat, want] of Object.entries(desired)) {
        if (want && !tertiary_stats[stat]) return false
      }
    }

    let ilvl
    if (state.USE_POST_MIDNIGHT_ILVL) {
      ilvl = resolvePostMidnightIlvl(
        auction.item.id,
        auction.item.bonus_lists,
        required_lvl,
        state.bonuses_by_id,
        state.equippable_items,
        state.item_curves,
        state.item_squish_era
      )
      // Resolver always returns a number (0 when no base); no longer null
    } else {
      const base_ilvl = rule.base_ilvls[auction.item.id]
      const ilvl_add = [...item_bonus_ids]
        .map((b) => state.ilvl_addition[b] || 0)
        .reduce((a, b) => a + b, 0)
      ilvl = base_ilvl + ilvl_add
    }

    if (ilvl < min_ilvl) return false
    if (ilvl > rule.max_ilvl) return false

    if (required_lvl < rule.required_min_lvl) return false
    if (required_lvl > rule.required_max_lvl) return false

    if (rule.bonus_lists.length && rule.bonus_lists[0] !== -1) {
      // Python: set(DESIRED_ILVL_ITEMS["bonus_lists"]) != set(item_bonus_ids)
      // Require exact match: sets must be equal (same size and same elements)
      const requiredBonusIds = new Set(rule.bonus_lists)
      if (requiredBonusIds.size !== item_bonus_ids.size) {
        return false
      }
      // Check that every element in requiredBonusIds exists in item_bonus_ids
      // Since sizes are equal, this also ensures item_bonus_ids has no extra elements
      for (const requiredId of requiredBonusIds) {
        if (!item_bonus_ids.has(requiredId)) {
          return false
        }
      }
    }

    if (rule.bonus_lists.length === 1 && rule.bonus_lists[0] === -1) {
      const temp = new Set(item_bonus_ids)
      for (const bid of state.socket_ids) temp.delete(bid)
      for (const bid of state.leech_ids) temp.delete(bid)
      for (const bid of state.avoidance_ids) temp.delete(bid)
      for (const bid of state.speed_ids) temp.delete(bid)
      if (temp.size > 3) return false
      const bad_ids = [224637]
      if (bad_ids.includes(auction.item.id)) return false
    }

    const buyout = auction.buyout ?? auction.bid
    if (!buyout) return false
    const buyoutValue = Math.round((buyout / 10000) * 100) / 100
    if (buyoutValue > rule.buyout) return false

    return {
      item_id: auction.item.id,
      buyout,
      tertiary_stats,
      bonus_ids: item_bonus_ids,
      ilvl,
      required_lvl,
    }
  }

  /**
   * Check if a pet auction meets the desired level and price criteria
   *
   * Args:
   *   item: Auction house item data from Blizzard API
   *   desired_pet_list: List of pet ilvl rules containing desired pet criteria
   *
   * Returns:
   *   Pet info if it matches criteria, null if it doesn't match
   *
   * Breed IDs can be found on warcraftpets.com
   * 4, 14 are the best power
   * 5, 15 are the best speed
   * 6, 16 are the best health
   */
  function check_pet_ilvl_stats(item, desired_pet_list) {
    const pet_species_id = item.item.pet_species_id
    const desired = desired_pet_list.find((p) => p.petID === pet_species_id)
    if (!desired) return null

    const pet_level = item.item.pet_level
    if (pet_level == null || pet_level < desired.minLevel) return null

    if (item.item.pet_quality_id < desired.minQuality) return null

    if (desired.excludeBreeds.includes(item.item.pet_breed_id)) return null

    const buyout = item.buyout
    if (buyout == null || buyout / 10000 > desired.price) return null

    return {
      pet_species_id,
      current_level: pet_level,
      buyout: buyout / 10000,
      quality: item.item.pet_quality_id,
      breed: item.item.pet_breed_id,
    }
  }

  /**
   * Clean and process auction listing data
   * Separates auctions into different categories: regular items, pets, ilvl items, pet ilvl items
   * All caged battle pets have item id 82800
   */
  function clean_listing_data(auctions, connected_id) {
    const all_ah_buyouts = {}
    const all_ah_bids = {}
    const ilvl_ah_buyouts = []
    const pet_ilvl_ah_buyouts = []

    if (!auctions || auctions.length === 0) {
      log(`no listings found on ${connected_id} of ${state.REGION}`)
      return
    }

    /**
     * Add price to dictionary, converting from copper to gold
     * Only adds unique prices to avoid duplicates
     * Filters out prices that exceed maxPrice if provided
     */
    const add_price_to_dict = (price, item_id, price_dict, maxPrice = null) => {
      const gold = price / 10000
      // Filter out prices that exceed the maximum desired price
      if (maxPrice !== null && gold > maxPrice) {
        return
      }
      if (price_dict[item_id]) {
        if (!price_dict[item_id].includes(gold)) price_dict[item_id].push(gold)
      } else {
        price_dict[item_id] = [gold]
      }
    }

    for (const item of auctions) {
      const item_id = item.item?.id
      if (!item_id) continue

      if (item_id in state.desiredItems && item_id !== 82800) {
        const maxPrice = state.desiredItems[item_id]
        if ("bid" in item && state.SHOW_BIDPRICES) {
          add_price_to_dict(item.bid, item_id, all_ah_bids, maxPrice)
        }
        if ("buyout" in item)
          add_price_to_dict(item.buyout, item_id, all_ah_buyouts, maxPrice)
        if ("unit_price" in item)
          add_price_to_dict(item.unit_price, item_id, all_ah_buyouts, maxPrice)
      } else if (item_id === 82800) {
        if (state.desiredPetIlvlList.length) {
          const info = check_pet_ilvl_stats(item, state.desiredPetIlvlList)
          if (info) pet_ilvl_ah_buyouts.push(info)
        }
      }

      for (const desired_ilvl_item of state.desiredIlvlList) {
        if (desired_ilvl_item.item_ids.includes(item_id)) {
          const info = check_tertiary_stats_generic(
            item,
            desired_ilvl_item,
            desired_ilvl_item.ilvl
          )
          if (info) ilvl_ah_buyouts.push(info)
        }
      }
    }

    if (
      !(
        Object.keys(all_ah_buyouts).length ||
        Object.keys(all_ah_bids).length ||
        ilvl_ah_buyouts.length ||
        pet_ilvl_ah_buyouts.length
      )
    ) {
      log(
        `no listings found matching desires on ${connected_id} of ${state.REGION}`
      )
      return
    }
    log(`Found matches on ${connected_id} of ${state.REGION}!!!`)
    return format_alert_messages(
      all_ah_buyouts,
      all_ah_bids,
      connected_id,
      ilvl_ah_buyouts,
      pet_ilvl_ah_buyouts
    )
  }

  function format_alert_messages(
    all_ah_buyouts,
    all_ah_bids,
    connected_id,
    ilvl_ah_buyouts,
    pet_ilvl_ah_buyouts
  ) {
    const results = []
    const realm_names = state.get_realm_names(connected_id)
    const defaultRealm =
      realm_names && realm_names.length > 0 ? realm_names[0] : null

    // Build lookup maps for O(1) target price lookups (performance optimization)
    const ilvlTargetPriceMap = new Map()
    for (const rule of state.desiredIlvlList) {
      for (const itemID of rule.item_ids) {
        ilvlTargetPriceMap.set(itemID, rule.buyout)
      }
    }

    const petTargetPriceMap = new Map()
    for (const rule of state.desiredPetIlvlList) {
      petTargetPriceMap.set(rule.petID, rule.price)
    }
    for (const [itemIDStr, auction] of Object.entries(all_ah_buyouts)) {
      const itemID = Number(itemIDStr)
      const itemlink = defaultRealm
        ? create_oribos_exchange_item_link(defaultRealm, itemID, state.REGION)
        : null
      const targetPrice =
        itemID in state.desiredItems ? state.desiredItems[itemID] : null
      results.push(
        results_dict(
          auction,
          itemlink,
          connected_id,
          realm_names,
          itemID,
          "itemID",
          "buyout",
          targetPrice
        )
      )
    }
    for (const auction of ilvl_ah_buyouts) {
      const itemID = Number(auction.item_id)
      const itemlink = defaultRealm
        ? create_oribos_exchange_item_link(defaultRealm, itemID, state.REGION)
        : null
      // Fast O(1) lookup instead of O(n) search
      const targetPrice = ilvlTargetPriceMap.get(itemID) || null
      results.push(
        ilvl_results_dict(
          auction,
          itemlink,
          connected_id,
          realm_names,
          itemID,
          "itemID",
          "buyout",
          targetPrice
        )
      )
    }
    if (state.SHOW_BIDPRICES) {
      for (const [itemIDStr, auction] of Object.entries(all_ah_bids)) {
        const itemID = Number(itemIDStr)
        const itemlink = defaultRealm
          ? create_oribos_exchange_item_link(defaultRealm, itemID, state.REGION)
          : null
        const targetPrice =
          itemID in state.desiredItems ? state.desiredItems[itemID] : null
        results.push(
          results_dict(
            auction,
            itemlink,
            connected_id,
            realm_names,
            itemID,
            "itemID",
            "bid",
            targetPrice
          )
        )
      }
    }
    for (const auction of pet_ilvl_ah_buyouts) {
      const petID = auction.pet_species_id
      const itemlink = defaultRealm
        ? create_oribos_exchange_pet_link(defaultRealm, petID, state.REGION)
        : null
      // Fast O(1) lookup instead of O(n) search
      const targetPrice = petTargetPriceMap.get(petID) || null
      results.push(
        pet_ilvl_results_dict(
          auction,
          itemlink,
          connected_id,
          realm_names,
          petID,
          "petID",
          "buyout",
          targetPrice
        )
      )
    }
    return results
  }

  /**
   * Check if two sets have any common elements (intersection)
   * Returns true if any element in setA exists in setB, false otherwise
   * This matches Python's: len(item_bonus_ids & socket_ids) != 0
   */
  function intersection(setA, setB) {
    if (!setA || !setB) return false
    for (const v of setA) {
      if (setB.has(v)) return true
    }
    return false
  }

  // Initial fast run across all realms
  // Run once to get the current data so no one asks about the waiting time
  // After the first run we will trigger once per hour when the new data updates
  const initialRealms = Array.from(
    new Set(Object.values(state.WOW_SERVER_NAMES))
  )
  // Include commodity endpoint for current region if TOKEN_PRICE is configured
  // -1 for NA, -2 for EU (only scan the one for current region)
  // Only add if not already in the list to avoid duplicate scans
  if (state.TOKEN_PRICE) {
    const commodityId = state.REGION === "EU" ? -2 : -1
    if (!initialRealms.includes(commodityId)) {
      initialRealms.push(commodityId)
    }
  }
  if (initialRealms.length) {
    log(
      `Starting mega-alerts-js for region=${state.REGION}, items=${
        Object.keys(state.desiredItems).length
      }, ilvl rules=${state.desiredIlvlList.length}, pet ilvl rules=${
        state.desiredPetIlvlList.length
      }`
    )
    log(`[Desired items]: ${JSON.stringify(state.desiredItems)}`)
    log(`[Desired ilvl rules]: ${JSON.stringify(state.desiredIlvlList)}`)
    log(`[Desired pet ilvl rules]: ${JSON.stringify(state.desiredPetIlvlList)}`)
    progress("Sending alerts!")
    await runPool(
      initialRealms.map((id) => () => pull_single_realm_data(id)),
      state.THREADS
    )
  }

  if (runOnce) return

  // Main loop - runs continuously checking for new auction house data
  while (!STOP_REQUESTED) {
    const current_min = new Date().getMinutes()

    // Refresh alerts 1 time per hour (at minute 1)
    if (current_min === 1 && state.REFRESH_ALERTS) {
      alert_record.clear()
    }

    // Find realms that match the scan time window
    // Scan starts at lastUploadMinute + SCAN_TIME_MIN
    // Scan ends at lastUploadMinute + SCAN_TIME_MAX
    // Commodities are included automatically if they're in upload_timers and match the time window

    /**
     * Check if current_min is within the scan window, handling minute wraparound (0-59).
     * @param {number} current_min - Current minute (0-59)
     * @param {number} last_upload_min - Last upload minute (0-59)
     * @param {number} scan_time_min - Minutes before upload to start scanning (can be negative)
     * @param {number} scan_time_max - Minutes after upload to stop scanning
     * @returns {boolean} True if current_min is within the scan window
     */
    const isInScanWindow = (
      current_min,
      last_upload_min,
      scan_time_min,
      scan_time_max
    ) => {
      // Calculate the start and end of the scan window, wrapping around 0-59
      // JavaScript's modulo operator handles negative numbers differently than Python,
      // so we need to ensure positive values first
      const start_min = (((last_upload_min + scan_time_min) % 60) + 60) % 60
      const end_min = (((last_upload_min + scan_time_max) % 60) + 60) % 60

      // Handle wraparound: if start > end, the range crosses the hour boundary
      if (start_min <= end_min) {
        // Normal range (no wraparound): e.g., 5 to 10
        return start_min <= current_min && current_min <= end_min
      } else {
        // Wraparound range: e.g., 59 to 2 means [59, 0, 1, 2]
        return current_min >= start_min || current_min <= end_min
      }
    }

    let matching_realms = state
      .get_upload_time_list()
      .filter((realm) =>
        isInScanWindow(
          current_min,
          realm.lastUploadMinute,
          state.SCAN_TIME_MIN,
          state.SCAN_TIME_MAX
        )
      )
      .map((r) => r.dataSetID)

    // Check for extra alerts (JSON array of minutes to trigger on)
    if (state.EXTRA_ALERTS) {
      try {
        const extra = JSON.parse(state.EXTRA_ALERTS)
        if (extra.includes(current_min)) {
          // Include all realms from upload_timers (commodities included if they've been scanned)
          matching_realms = state.get_upload_time_list().map((r) => r.dataSetID)
        }
      } catch {
        // Ignore errors when checking extra alert times
      }
    }

    if (matching_realms.length) {
      log(
        `Starting mega-alerts-js for region=${state.REGION}, items=${
          Object.keys(state.desiredItems).length
        }, ilvl rules=${state.desiredIlvlList.length}, pet ilvl rules=${
          state.desiredPetIlvlList.length
        }`
      )
      progress("Sending alerts!")
      await runPool(
        matching_realms.map((id) => () => pull_single_realm_data(id)),
        state.THREADS
      )
    } else {
      progress(
        `The updates will come\non min ${Array.from(
          state.get_upload_time_minutes()
        ).join(",")}\nof each hour.`
      )
      log(
        `Blizzard API data only updates 1 time per hour. The updates will come on minute ${Array.from(
          state.get_upload_time_minutes()
        )} of each hour. ${new Date().toISOString()} is not the update time.`
      )
      await delay(20000) // Wait 20 seconds before checking again
    }
  }
}

/**
 * Main entry point
 * Initializes MegaData and starts alert processing
 */
async function main() {
  // Reset stop flag at the start of each run to handle module caching
  STOP_REQUESTED = false

  const state = new MegaData()
  // Initialize async data (bonus IDs, item names, pet names, ilvl items)
  await state.initialize()
  console.log(
    `Starting mega-alerts-js for region=${state.REGION}, items=${
      Object.keys(state.desiredItems).length
    }, ilvl rules=${state.desiredIlvlList.length}, pet ilvl rules=${
      state.desiredPetIlvlList.length
    }`
  )
  if (state.DEBUG) {
    await sendDiscordMessage(
      state.WEBHOOK_URL,
      "DEBUG MODE: starting mega alerts to run once and then exit operations"
    )
    await runAlerts(state, () => {}, true)
  } else {
    await sendDiscordMessage(
      state.WEBHOOK_URL,
      "🟢Starting mega alerts and scan all AH data instantly.🟢\n" +
        "🟢These first few messages might be old.🟢\n" +
        "🟢All future messages will release seconds after the new data is available.🟢"
    )
    await delay(1000)
    await runAlerts(state, (msg) => log("[progress]", msg))
  }
}

// Export functions for Electron main process integration
module.exports = {
  main,
  setLogCallback,
  setStopCallback,
  setPaths,
  requestStop,
  reset,
  MegaData,
}
