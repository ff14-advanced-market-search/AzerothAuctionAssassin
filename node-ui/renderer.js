// Helper function to escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div")
  div.textContent = text
  return div.innerHTML
}

const DEFAULT_MAX_IN_APP_ALERTS = 120
const MAX_IN_APP_ALERTS_HARD_CAP = 5000
const DEFAULT_ALERT_SOUND_VOLUME = 70
const BUILTIN_ALERT_SOUND_GAIN_MULTIPLIER = 2
const ALERTS_VIEW_STORAGE_KEY = "aaa-alerts-view-mode"

const alertEmbedHistory = []

const ALERT_VIEW_MODES = ["sheet", "discord", "details"]

const SHEET_COL_PAGE_SIZE = 15
const SHEET_COLUMN_ORDER_STORAGE_KEY = "aaa-alerts-sheet-column-order"
let sheetSearchDebounceTimer = null

function loadSheetColumnOrderFromStorage() {
  try {
    const raw = localStorage.getItem(SHEET_COLUMN_ORDER_STORAGE_KEY)
    if (!raw) return null
    const a = JSON.parse(raw)
    return Array.isArray(a) && a.every((x) => typeof x === "string") ? a : null
  } catch {
    return null
  }
}

function saveSheetColumnOrder(order) {
  try {
    localStorage.setItem(SHEET_COLUMN_ORDER_STORAGE_KEY, JSON.stringify(order))
  } catch {
    // ignore quota / private mode
  }
}

function mergeSavedColumnOrder(rawCols, saved) {
  if (!saved || saved.length === 0) return [...rawCols]
  const set = new Set(rawCols)
  const out = []
  for (const c of saved) {
    if (set.has(c)) {
      out.push(c)
      set.delete(c)
    }
  }
  for (const c of rawCols) {
    if (set.has(c)) out.push(c)
  }
  return out
}

const unifiedSheetState = {
  searchRaw: "",
  sortCol: null,
  sortDir: "asc",
  columnVisible: {},
  sheetColumnOrder: loadSheetColumnOrderFromStorage(),
  numericFilters: [],
  nextFilterId: 1,
  colPage: 0,
  colPanelOpen: false,
  filterPanelOpen: false,
}

function getSheetColumnsOrdered(allRows) {
  const rawCols = collectSheetColumns(allRows)
  if (rawCols.length === 0) {
    return []
  }
  const merged = mergeSavedColumnOrder(
    rawCols,
    unifiedSheetState.sheetColumnOrder
  )
  unifiedSheetState.sheetColumnOrder = merged
  return merged
}

function loadStoredAlertsViewMode() {
  const v = localStorage.getItem(ALERTS_VIEW_STORAGE_KEY)
  if (ALERT_VIEW_MODES.includes(v)) {
    return v
  }
  if (v === "table") {
    return "details"
  }
  if (v === "cards") {
    return "discord"
  }
  return "sheet"
}

let alertsViewMode = loadStoredAlertsViewMode()

/**
 * Closing `)` for `[label](url)` when the URL may contain balanced parentheses
 * (regex `[^)\s]+` breaks on the first `)` inside URLs such as item links).
 */
function findMarkdownLinkUrlEnd(str, urlStartIndex) {
  let depth = 0
  for (let i = urlStartIndex; i < str.length; i++) {
    const c = str[i]
    if (c === "(") {
      depth++
    } else if (c === ")") {
      if (depth === 0) {
        return i
      }
      depth--
    }
  }
  return -1
}

function appendInlineFormattedDiscord(container, text) {
  if (!text) return
  const segments = text.split(/(`[^`\n]+`)/g)
  for (const part of segments) {
    if (!part) continue
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      const code = document.createElement("code")
      code.className = "discord-embed-code"
      code.textContent = part.slice(1, -1)
      container.appendChild(code)
      continue
    }
    const boldRe = /\*\*(.+?)\*\*/g
    let last = 0
    let bm
    while ((bm = boldRe.exec(part)) !== null) {
      if (bm.index > last) {
        container.appendChild(
          document.createTextNode(part.slice(last, bm.index))
        )
      }
      const strong = document.createElement("strong")
      strong.textContent = bm[1]
      container.appendChild(strong)
      last = bm.lastIndex
    }
    if (last < part.length) {
      container.appendChild(document.createTextNode(part.slice(last)))
    }
  }
}

function appendRichDiscordText(container, raw) {
  if (raw == null || raw === "") return
  const str = String(raw)
  let i = 0
  while (i < str.length) {
    const openB = str.indexOf("[", i)
    if (openB === -1) {
      appendInlineFormattedDiscord(container, str.slice(i))
      break
    }
    appendInlineFormattedDiscord(container, str.slice(i, openB))
    const closeB = str.indexOf("]", openB + 1)
    if (closeB === -1) {
      appendInlineFormattedDiscord(container, str.slice(openB))
      break
    }
    if (str[closeB + 1] !== "(") {
      appendInlineFormattedDiscord(container, str.slice(openB, closeB + 1))
      i = closeB + 1
      continue
    }
    const urlStart = closeB + 2
    const closeP = findMarkdownLinkUrlEnd(str, urlStart)
    if (closeP === -1) {
      appendInlineFormattedDiscord(container, str.slice(openB))
      break
    }
    const label = str.slice(openB + 1, closeB)
    const url = str.slice(urlStart, closeP).trim()
    if (/^https?:\/\//i.test(url)) {
      const a = document.createElement("a")
      a.href = url
      a.textContent = label
      a.target = "_blank"
      a.rel = "noopener noreferrer"
      a.className = "discord-embed-link"
      container.appendChild(a)
      i = closeP + 1
    } else {
      appendInlineFormattedDiscord(container, str.slice(openB, closeP + 1))
      i = closeP + 1
    }
  }
}

function extractMarkdownLinks(str) {
  const out = []
  const s = String(str)
  let i = 0
  while (i < s.length) {
    const openB = s.indexOf("[", i)
    if (openB === -1) break
    const closeB = s.indexOf("]", openB + 1)
    if (closeB === -1) break
    if (s[closeB + 1] !== "(") {
      i = openB + 1
      continue
    }
    const urlStart = closeB + 2
    const closeP = findMarkdownLinkUrlEnd(s, urlStart)
    if (closeP === -1) {
      i = openB + 1
      continue
    }
    const label = s.slice(openB + 1, closeB)
    const url = s.slice(urlStart, closeP).trim()
    if (/^https?:\/\//i.test(url)) {
      out.push({ label, url })
    }
    i = closeP + 1
  }
  return out
}

function isLineOnlyMarkdownLink(line) {
  const t = line.trim()
  if (!t.startsWith("[") || !t.endsWith(")")) return false
  const closeB = t.indexOf("]", 1)
  if (closeB < 1 || t[closeB + 1] !== "(") return false
  const closeP = findMarkdownLinkUrlEnd(t, closeB + 2)
  return closeP === t.length - 1
}

function fieldDetailBody(value) {
  const lines = String(value).split("\n")
  const kept = []
  for (const line of lines) {
    if (isLineOnlyMarkdownLink(line)) continue
    kept.push(line)
  }
  return kept.join("\n").trim()
}

function parseDescriptionMeta(description) {
  const out = { region: "", realmID: "", realmNames: "" }
  if (!description) return out
  const s = String(description)
  const pick = (re) => {
    const m = s.match(re)
    return m ? m[1].trim() : ""
  }
  out.region =
    pick(/^\s*\*\*region:\*\*\s*(.+)$/im) || pick(/^\s*region:\s*(.+)$/im)
  out.realmID =
    pick(/^\s*\*\*realmID:\*\*\s*(.+)$/im) || pick(/^\s*realmID:\s*(.+)$/im)
  out.realmNames =
    pick(/^\s*\*\*realmNames:\*\*\s*(.+)$/im) ||
    pick(/^\s*realmNames:\s*(.+)$/im)
  return out
}

function isDescriptionMetaLine(line) {
  const t = String(line).trim()
  return (
    /^\*\*region:\*\*/i.test(t) ||
    /^\*\*realmID:\*\*/i.test(t) ||
    /^\*\*realmNames:\*\*/i.test(t) ||
    /^region:/i.test(t) ||
    /^realmID:/i.test(t) ||
    /^realmNames:/i.test(t)
  )
}

/** Drop leading region / realmID / realmNames lines (Discord embed header). */
function removeDescriptionMetaLines(description) {
  if (!description) return ""
  const lines = String(description).split(/\r?\n/)
  const rest = []
  let atHead = true
  for (const line of lines) {
    const empty = line.trim() === ""
    if (atHead) {
      if (empty) continue
      if (isDescriptionMetaLine(line)) continue
      atHead = false
    }
    rest.push(line)
  }
  return rest.join("\n").trim()
}

function descriptionMetaHasValues(meta) {
  return Boolean(
    String(meta?.region || "").trim() ||
      String(meta?.realmID || "").trim() ||
      String(meta?.realmNames || "").trim()
  )
}

/** Structured realm/region lines + remaining description (Discord + Details cards). */
function appendParsedDescriptionMeta(host, rawDescription, descClassName) {
  if (rawDescription == null || rawDescription === "") return
  const metaObj = parseDescriptionMeta(rawDescription)
  const hasMeta = descriptionMetaHasValues(metaObj)
  if (hasMeta) {
    const block = document.createElement("div")
    block.className = "alert-embed-meta-block"
    const defs = [
      ["region", "region"],
      ["realmID", "realmID"],
      ["realmNames", "realmNames"],
    ]
    for (const [key, label] of defs) {
      const v = String(metaObj[key] || "").trim()
      if (!v) continue
      const row = document.createElement("div")
      row.className = "alert-embed-meta-row"
      const kEl = document.createElement("span")
      kEl.className = "alert-embed-meta-key"
      kEl.textContent = `${label}: `
      const vEl = document.createElement("span")
      vEl.className = "alert-embed-meta-val"
      vEl.textContent = v
      row.appendChild(kEl)
      row.appendChild(vEl)
      block.appendChild(row)
    }
    host.appendChild(block)
  }
  const remainder = hasMeta
    ? removeDescriptionMetaLines(rawDescription)
    : String(rawDescription)
  if (remainder.trim()) {
    const desc = document.createElement("div")
    desc.className = descClassName
    appendRichDiscordText(desc, remainder.trim())
    host.appendChild(desc)
  }
}

const LINK_LABEL_TO_COL = {
  "Shopping List": "link_shopping_list",
  "Where to Sell": "link_where_to_sell",
  "Wowhead link": "link_wowhead",
  "Undermine link": "link_undermine",
  "Saddlebag link": "link_saddlebag",
}

function linkLabelToColumnKey(label) {
  if (LINK_LABEL_TO_COL[label]) return LINK_LABEL_TO_COL[label]
  const slug = String(label)
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "")
  return slug ? `link_${slug}` : ""
}

/** Discord-style link column → table header / anchor text (matches in-app alerts). */
const LINK_COLUMN_DISPLAY = {
  link_shopping_list: "Shopping List",
  link_where_to_sell: "Where to Sell",
  link_where_to_search: "Where to Sell",
  link_wowhead: "Wowhead link",
  link_undermine: "Undermine link",
  link_saddlebag: "Saddlebag link",
}

function stripLeadingColonSpace(val) {
  if (val == null) return ""
  let s = String(val).trimStart()
  s = s.replace(/^(?:\s*:\s*)+/, "")
  return s.trimStart()
}

function getSheetColumnHeaderLabel(col) {
  if (col === "time") return "Time"
  if (LINK_COLUMN_DISPLAY[col]) return LINK_COLUMN_DISPLAY[col]
  if (col.startsWith("link_")) {
    const slug = col.slice(5)
    return slug
      .split("_")
      .map((p) =>
        p ? p.charAt(0).toUpperCase() + p.slice(1).toLowerCase() : ""
      )
      .filter(Boolean)
      .join(" ")
  }
  return col
}

function appendSheetTableCell(td, col, rawVal) {
  td.replaceChildren()
  const cleaned = stripLeadingColonSpace(
    rawVal !== undefined && rawVal !== null ? rawVal : ""
  )
  const trimmed = cleaned.trim()
  if (col.startsWith("link_") && /^https?:\/\//i.test(trimmed)) {
    const a = document.createElement("a")
    a.href = trimmed
    a.textContent =
      LINK_COLUMN_DISPLAY[col] || getSheetColumnHeaderLabel(col) || "Link"
    a.target = "_blank"
    a.rel = "noopener noreferrer"
    a.className = "discord-embed-link alert-sheet-cell-link"
    td.appendChild(a)
    return
  }
  if (col === "time") {
    if (!trimmed) {
      delete td.dataset.sheetTimeIso
      td.textContent = ""
      return
    }
    const d = new Date(trimmed)
    if (!Number.isNaN(d.getTime())) {
      td.dataset.sheetTimeIso = d.toISOString()
      td.textContent = d.toLocaleString()
    } else {
      delete td.dataset.sheetTimeIso
      td.textContent = cleaned
    }
    return
  }
  td.textContent = cleaned
}

function parseFieldKeyValues(text) {
  const o = {}
  for (const line of String(text).split("\n")) {
    if (isLineOnlyMarkdownLink(line)) continue
    const t = line.trim()
    if (!t) continue
    const tick = t.match(/^`([^`]+)`\s*(.*)$/)
    if (tick) {
      const k = tick[1].replace(/:\s*$/, "").trim()
      if (k) o[k] = stripLeadingColonSpace(tick[2].trim())
      continue
    }
    const colon = t.indexOf(":")
    if (colon > 0) {
      const k = t
        .slice(0, colon)
        .trim()
        .replace(/^`+|`+$/g, "")
      const v = stripLeadingColonSpace(t.slice(colon + 1).trim())
      if (k) o[k] = v
    }
  }
  return o
}

const SHEET_COL_ORDER = [
  "item",
  "buyout_prices",
  "realmNames",
  "time",
  "region",
  "realmID",
  "itemID",
  "petID",
  "ilvl",
  "tertiary_stats",
  "required_lvl",
  "bonus_ids",
  "target_price",
  "Below_Target",
  "bid_prices",
  "link_shopping_list",
  "link_where_to_sell",
  "link_wowhead",
  "link_undermine",
  "link_saddlebag",
  "title",
  "message",
]

function collectSheetColumns(rows) {
  const set = new Set()
  for (const r of rows) {
    Object.keys(r).forEach((k) => {
      if (!k.startsWith("__")) set.add(k)
    })
  }
  const ordered = []
  for (const c of SHEET_COL_ORDER) {
    if (set.has(c)) ordered.push(c)
  }
  const rest = [...set].filter((c) => !ordered.includes(c)).sort()
  return [...ordered, ...rest]
}

function parseSheetCellNumber(val) {
  if (val == null || val === "") return null
  const s = String(stripLeadingColonSpace(val)).replace(/,/g, "").trim()
  const pct = s.match(/([\d.]+)\s*%/)
  if (pct) {
    const n = parseFloat(pct[1])
    return Number.isFinite(n) ? n : null
  }
  const m = s.match(/-?[\d.]+(?:e[+-]?\d+)?/)
  if (!m) return null
  const n = parseFloat(m[0])
  return Number.isFinite(n) ? n : null
}

/** Min/max for time column filters: ISO-8601, epoch ms/s, or other Date.parse-accepted strings. */
function parseSheetTimeFilterBound(raw) {
  const s = String(raw ?? "").trim()
  if (s === "") return null
  const fromDate = Date.parse(s)
  if (!Number.isNaN(fromDate)) return fromDate
  const n = Number(String(s).replace(/,/g, ""))
  if (!Number.isFinite(n)) return null
  if (n > 1e11 && n < 1e14) return Math.round(n)
  if (n > 1e9 && n < 1e11) return Math.round(n * 1000)
  return null
}

function compareSheetRows(a, b, col, dir) {
  const mul = dir === "desc" ? -1 : 1
  if (col === "time") {
    return ((a.__ts || 0) - (b.__ts || 0)) * mul
  }
  const va = stripLeadingColonSpace(a[col])
  const vb = stripLeadingColonSpace(b[col])
  const na = parseSheetCellNumber(va)
  const nb = parseSheetCellNumber(vb)
  if (na !== null && nb !== null && na !== nb) {
    return (na - nb) * mul
  }
  return (
    String(va ?? "")
      .toLowerCase()
      .localeCompare(String(vb ?? "").toLowerCase()) * mul
  )
}

function rowMatchesSheetSearch(row, q) {
  if (!q) return true
  const ql = q.toLowerCase()
  for (const [k, v] of Object.entries(row)) {
    if (k.startsWith("__")) continue
    const s = stripLeadingColonSpace(v).toLowerCase()
    if (s.includes(ql)) return true
  }
  return false
}

function rowPassesNumericFilters(row, filters) {
  for (const f of filters) {
    if (!f || !f.column) continue
    const minS = f.min
    const maxS = f.max
    const minActive = minS !== "" && minS != null && String(minS).trim() !== ""
    const maxActive = maxS !== "" && maxS != null && String(maxS).trim() !== ""
    if (f.column === "time") {
      if (!minActive && !maxActive) continue
      const ts = row.__ts
      if (!ts || Number.isNaN(ts)) return false
      if (minActive) {
        const minMs = parseSheetTimeFilterBound(minS)
        if (minMs != null && ts < minMs) return false
      }
      if (maxActive) {
        const maxMs = parseSheetTimeFilterBound(maxS)
        if (maxMs != null && ts > maxMs) return false
      }
      continue
    }
    const n = parseSheetCellNumber(row[f.column])
    if (n === null) return false
    if (minActive) {
      const min = parseFloat(String(minS).replace(/,/g, ""))
      if (Number.isFinite(min) && n < min) return false
    }
    if (maxActive) {
      const max = parseFloat(String(maxS).replace(/,/g, ""))
      if (Number.isFinite(max) && n > max) return false
    }
  }
  return true
}

function getNumericColumnCandidates(rows, cols) {
  return cols.filter((col) => {
    if (col === "time") {
      return rows.some(
        (r) =>
          (Number(r.__ts) > 0 && !Number.isNaN(Number(r.__ts))) ||
          (r.time != null && String(r.time).trim() !== "")
      )
    }
    if (col.startsWith("link_")) return false
    let num = 0
    let tot = 0
    for (const r of rows) {
      const v = r[col]
      if (v === undefined || v === null || String(v).trim() === "") continue
      tot++
      if (parseSheetCellNumber(v) !== null) num++
    }
    return tot > 0 && num >= Math.min(2, tot)
  })
}

function ensureSheetColumnVisibility(cols) {
  for (const c of cols) {
    if (unifiedSheetState.columnVisible[c] === undefined) {
      unifiedSheetState.columnVisible[c] = true
    }
  }
}

function visibleSheetColumns(allCols) {
  return allCols.filter((c) => unifiedSheetState.columnVisible[c] !== false)
}

function parseBracketValueList(raw) {
  const s = String(raw ?? "").trim()
  if (!s.startsWith("[") || !s.endsWith("]")) return null
  const inner = s.slice(1, -1).trim()
  if (!inner) return []
  return inner
    .split(",")
    .map((x) => x.trim())
    .filter((x) => x !== "")
}

function expandPriceArrayRows(row) {
  const priceCols = ["buyout_prices", "bid_prices"]
  const parsed = {}
  let maxLen = 0
  for (const col of priceCols) {
    const list = parseBracketValueList(row[col])
    if (!list || list.length === 0) continue
    parsed[col] = list
    maxLen = Math.max(maxLen, list.length)
  }
  if (maxLen <= 1) {
    if (maxLen === 1) {
      const one = { ...row }
      for (const [col, list] of Object.entries(parsed)) one[col] = list[0]
      return [one]
    }
    return [row]
  }
  const out = []
  for (let i = 0; i < maxLen; i++) {
    const next = { ...row }
    for (const [col, list] of Object.entries(parsed)) {
      next[col] = list[i] ?? ""
    }
    out.push(next)
  }
  return out
}

function buildSpreadsheetRowsForEmbed(embed) {
  const fields = Array.isArray(embed.fields) ? embed.fields : []
  const meta = parseDescriptionMeta(embed.description)
  if (!fields.length) {
    const row = { ...meta }
    if (embed.title) row.title = embed.title
    row.message = String(embed.description || "")
      .replace(/\s*\n\s*/g, " ")
      .trim()
    return [row]
  }
  const rows = []
  for (const f of fields) {
    const row = { ...meta, item: f.name || "" }
    Object.assign(row, parseFieldKeyValues(String(f.value || "")))
    for (const { label, url } of extractMarkdownLinks(String(f.value || ""))) {
      const col = linkLabelToColumnKey(label)
      if (col) row[col] = url
    }
    rows.push(...expandPriceArrayRows(row))
  }
  return rows
}

/** ISO string for sheet/CSV data so time filters and exports round-trip reliably. */
function embedTimestampToIso(iso) {
  if (!iso) return ""
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "" : d.toISOString()
}

/** Localized display for Discord-style footers and detail tables (not for sheet cell data). */
function formatEmbedTimestampDisplay(iso) {
  if (!iso) return ""
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString()
}

/** WoW token price embeds (no item fields); keep out of sheet so columns stay auction-focused. */
function isWowTokenAlertEmbed(embed) {
  const t = embed && embed.title != null ? String(embed.title).trim() : ""
  return /^WoW\s+Token\s+Alert\b/i.test(t)
}

function getAllUnifiedSheetRows() {
  const rows = []
  for (const { embed } of alertEmbedHistory) {
    if (isWowTokenAlertEmbed(embed)) continue
    const timeStr = embedTimestampToIso(embed.timestamp)
    const tsNum =
      embed.timestamp && !Number.isNaN(new Date(embed.timestamp).getTime())
        ? new Date(embed.timestamp).getTime()
        : 0
    const per = buildSpreadsheetRowsForEmbed(embed)
    for (const r of per) {
      rows.push({
        ...r,
        time: timeStr,
        __ts: tsNum,
      })
    }
  }
  return rows
}

function getAccentColor(embed) {
  const colorNum = embed.color
  return typeof colorNum === "number" && colorNum >= 0
    ? `#${colorNum.toString(16).padStart(6, "0")}`
    : "#5865f2"
}

function createDiscordFooterLine(iso) {
  const ts = formatEmbedTimestampDisplay(iso)
  if (!ts) return null
  const foot = document.createElement("div")
  foot.className = "discord-embed-footer"
  foot.textContent = ts
  return foot
}

/** One Discord-style card: title, description, field grid (like the Discord client). */
function createDiscordFlatGroup(embed, fields) {
  const wrap = document.createElement("div")
  wrap.className = "alert-embed-group alert-embed-discord-flat"
  const card = document.createElement("article")
  card.className = "discord-embed-card discord-embed-flat"
  card.style.setProperty("--embed-accent", getAccentColor(embed))
  if (embed.title) {
    const t = document.createElement("div")
    t.className = "discord-embed-title"
    appendRichDiscordText(t, embed.title)
    card.appendChild(t)
  }
  if (embed.description) {
    appendParsedDescriptionMeta(card, embed.description, "discord-embed-desc")
  }
  if (fields.length) {
    const grid = document.createElement("div")
    grid.className = "discord-embed-fields"
    for (const f of fields) {
      const fieldWrap = document.createElement("div")
      fieldWrap.className = "discord-embed-field"
      if (f.name) {
        const nameEl = document.createElement("div")
        nameEl.className = "discord-embed-field-name"
        appendRichDiscordText(nameEl, f.name)
        fieldWrap.appendChild(nameEl)
      }
      if (f.value != null && f.value !== "") {
        const valEl = document.createElement("div")
        valEl.className = "discord-embed-field-value"
        appendRichDiscordText(valEl, String(f.value))
        fieldWrap.appendChild(valEl)
      }
      grid.appendChild(fieldWrap)
    }
    card.appendChild(grid)
  }
  const foot = createDiscordFooterLine(embed.timestamp)
  if (foot) card.appendChild(foot)
  wrap.appendChild(card)
  return wrap
}

function createAlertTableGroup(embed, fields) {
  const group = document.createElement("div")
  group.className = "alert-table-group"
  const accent = getAccentColor(embed)
  group.style.setProperty("--embed-accent", accent)

  if (embed.title || embed.description) {
    const meta = document.createElement("div")
    meta.className = "alert-table-meta"
    if (embed.title) {
      const th = document.createElement("div")
      th.className = "alert-table-title"
      appendRichDiscordText(th, embed.title)
      meta.appendChild(th)
    }
    if (embed.description) {
      appendParsedDescriptionMeta(meta, embed.description, "alert-table-desc")
    }
    group.appendChild(meta)
  }

  if (!fields.length) {
    if (!embed.title && !embed.description) {
      const empty = document.createElement("div")
      empty.className = "alert-table-empty"
      empty.textContent = "No item rows in this alert."
      group.appendChild(empty)
    }
  } else {
    const table = document.createElement("table")
    table.className = "alert-items-table"
    const thead = document.createElement("thead")
    const hr = document.createElement("tr")
    for (const label of ["Item", "Details", "Links"]) {
      const th = document.createElement("th")
      th.textContent = label
      hr.appendChild(th)
    }
    thead.appendChild(hr)
    table.appendChild(thead)
    const tbody = document.createElement("tbody")
    for (const f of fields) {
      const tr = document.createElement("tr")
      const tdName = document.createElement("td")
      tdName.className = "col-item"
      if (f.name) appendRichDiscordText(tdName, f.name)
      const tdDet = document.createElement("td")
      tdDet.className = "col-details"
      const det = fieldDetailBody(f.value || "")
      if (det) {
        const div = document.createElement("div")
        div.className = "alert-table-details-text"
        appendRichDiscordText(div, det)
        tdDet.appendChild(div)
      }
      const tdLinks = document.createElement("td")
      tdLinks.className = "col-links"
      const links = extractMarkdownLinks(String(f.value || ""))
      if (links.length) {
        const ul = document.createElement("ul")
        ul.className = "alert-link-list"
        for (const { label, url } of links) {
          const li = document.createElement("li")
          const a = document.createElement("a")
          a.href = url
          a.textContent = label || url
          a.target = "_blank"
          a.rel = "noopener noreferrer"
          a.className = "discord-embed-link"
          li.appendChild(a)
          ul.appendChild(li)
        }
        tdLinks.appendChild(ul)
      }
      tr.appendChild(tdName)
      tr.appendChild(tdDet)
      tr.appendChild(tdLinks)
      tbody.appendChild(tr)
    }
    table.appendChild(tbody)
    group.appendChild(table)
  }

  const ts = formatEmbedTimestampDisplay(embed.timestamp)
  if (ts) {
    const tf = document.createElement("div")
    tf.className = "alert-table-ts"
    tf.textContent = ts
    group.appendChild(tf)
  }
  return group
}

function renderNumericFilterPanel(dash) {
  const box = dash.querySelector(".alert-sheet-filter-list")
  if (!box) return
  box.replaceChildren()
  const allRows = getAllUnifiedSheetRows()
  const allCols = getSheetColumnsOrdered(allRows)
  const numericCols = getNumericColumnCandidates(allRows, allCols)

  for (const f of unifiedSheetState.numericFilters) {
    const row = document.createElement("div")
    row.className = "alert-sheet-filter-row"
    row.dataset.filterId = String(f.id)

    const head = document.createElement("div")
    head.className = "alert-sheet-filter-row-head"
    const summary = document.createElement("span")
    summary.className = "alert-sheet-filter-summary"
    const minL = f.min !== "" && f.min != null ? String(f.min) : "—"
    const maxL = f.max !== "" && f.max != null ? String(f.max) : "—"
    summary.textContent = `${getSheetColumnHeaderLabel(
      f.column || "?"
    )} ∈ [${minL}, ${maxL}]`
    const rm = document.createElement("button")
    rm.type = "button"
    rm.className = "ghost alert-sheet-filter-remove"
    rm.textContent = "Remove"
    rm.addEventListener("click", () => {
      unifiedSheetState.numericFilters =
        unifiedSheetState.numericFilters.filter((x) => x.id !== f.id)
      renderNumericFilterPanel(dash)
      refreshUnifiedSheetTable(dash)
    })
    head.appendChild(summary)
    head.appendChild(rm)
    row.appendChild(head)

    const grid = document.createElement("div")
    grid.className = "alert-sheet-filter-grid"
    const sel = document.createElement("select")
    sel.className = "alert-sheet-select"
    const opt0 = document.createElement("option")
    opt0.value = ""
    opt0.textContent = "Column"
    sel.appendChild(opt0)
    for (const c of numericCols) {
      const opt = document.createElement("option")
      opt.value = c
      opt.textContent = getSheetColumnHeaderLabel(c)
      if (f.column === c) opt.selected = true
      sel.appendChild(opt)
    }
    const minIn = document.createElement("input")
    minIn.type = "text"
    minIn.className = "alert-sheet-filter-input"
    minIn.value = f.min != null ? String(f.min) : ""
    const maxIn = document.createElement("input")
    maxIn.type = "text"
    maxIn.className = "alert-sheet-filter-input"
    maxIn.value = f.max != null ? String(f.max) : ""
    const syncRangeFilterPlaceholders = () => {
      if (f.column === "time") {
        minIn.placeholder = "From (copy Time cell, ISO, or epoch ms)"
        maxIn.placeholder = "To (optional)"
      } else {
        minIn.placeholder = "Min (optional)"
        maxIn.placeholder = "Max (optional)"
      }
    }
    syncRangeFilterPlaceholders()
    sel.addEventListener("change", () => {
      f.column = sel.value
      syncRangeFilterPlaceholders()
      summary.textContent = `${getSheetColumnHeaderLabel(f.column || "?")} ∈ [${
        f.min !== "" && f.min != null ? String(f.min) : "—"
      }, ${f.max !== "" && f.max != null ? String(f.max) : "—"}]`
      refreshUnifiedSheetTable(dash)
    })
    minIn.addEventListener("input", () => {
      f.min = minIn.value
      summary.textContent = `${getSheetColumnHeaderLabel(f.column || "?")} ∈ [${
        f.min !== "" && f.min != null ? String(f.min) : "—"
      }, ${f.max !== "" && f.max != null ? String(f.max) : "—"}]`
      refreshUnifiedSheetTable(dash)
    })
    maxIn.addEventListener("input", () => {
      f.max = maxIn.value
      summary.textContent = `${getSheetColumnHeaderLabel(f.column || "?")} ∈ [${
        f.min !== "" && f.min != null ? String(f.min) : "—"
      }, ${f.max !== "" && f.max != null ? String(f.max) : "—"}]`
      refreshUnifiedSheetTable(dash)
    })
    grid.appendChild(sel)
    grid.appendChild(minIn)
    grid.appendChild(maxIn)
    row.appendChild(grid)
    box.appendChild(row)
  }
}

function renderColumnControlPanel(dash) {
  const box = dash.querySelector(".alert-sheet-col-checkboxes")
  const pageLabel = dash.querySelector(".alert-sheet-col-page-label")
  if (!box || !pageLabel) return
  const allRows = getAllUnifiedSheetRows()
  const allCols = getSheetColumnsOrdered(allRows)
  ensureSheetColumnVisibility(allCols)
  const totalPages = Math.max(
    1,
    Math.ceil(allCols.length / SHEET_COL_PAGE_SIZE)
  )
  if (unifiedSheetState.colPage >= totalPages) {
    unifiedSheetState.colPage = totalPages - 1
  }
  const start = unifiedSheetState.colPage * SHEET_COL_PAGE_SIZE
  const slice = allCols.slice(start, start + SHEET_COL_PAGE_SIZE)
  box.replaceChildren()
  for (const col of slice) {
    const lab = document.createElement("label")
    lab.className = "alert-sheet-col-check"
    const cb = document.createElement("input")
    cb.type = "checkbox"
    cb.checked = unifiedSheetState.columnVisible[col] !== false
    cb.addEventListener("change", () => {
      unifiedSheetState.columnVisible[col] = cb.checked
      refreshUnifiedSheetTable(dash)
    })
    lab.appendChild(cb)
    lab.appendChild(
      document.createTextNode(` ${getSheetColumnHeaderLabel(col)}`)
    )
    box.appendChild(lab)
  }
  pageLabel.textContent = `Page ${
    unifiedSheetState.colPage + 1
  } of ${totalPages}`
}

function computeUnifiedSheetDisplay() {
  const allRows = getAllUnifiedSheetRows()
  const allCols = getSheetColumnsOrdered(allRows)
  ensureSheetColumnVisibility(allCols)
  const q = unifiedSheetState.searchRaw.trim()
  let working = allRows.filter((r) => rowMatchesSheetSearch(r, q))
  working = working.filter((r) =>
    rowPassesNumericFilters(r, unifiedSheetState.numericFilters)
  )
  working = working.filter((row) =>
    Object.keys(row).some((k) => {
      if (k.startsWith("__")) return false
      const v = row[k]
      if (v === undefined || v === null) return false
      return String(v).trim() !== ""
    })
  )
  const sortCol = unifiedSheetState.sortCol
  const sortDir = unifiedSheetState.sortDir
  if (sortCol && allCols.includes(sortCol)) {
    working = [...working].sort((a, b) =>
      compareSheetRows(a, b, sortCol, sortDir)
    )
  }
  const cols = visibleSheetColumns(allCols)
  return { allRows, allCols, working, cols }
}

function csvEscapeField(val) {
  let s = String(val ?? "")
  if (/^[\t\r ]*[=+\-@]/.test(s)) {
    s = `'${s}`
  }
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

function sheetCellPlainExport(col, rawVal) {
  const cleaned = stripLeadingColonSpace(
    rawVal !== undefined && rawVal != null ? rawVal : ""
  )
  const trimmed = cleaned.trim()
  if (col.startsWith("link_") && /^https?:\/\//i.test(trimmed)) return trimmed
  return cleaned
}

function downloadUnifiedSheetAsCsv() {
  const { allRows, working, cols } = computeUnifiedSheetDisplay()
  if (!cols.length) {
    showToast(
      "No columns to export — use Column controls or add alerts first.",
      "error"
    )
    return
  }
  const headerLine = cols
    .map((c) => csvEscapeField(getSheetColumnHeaderLabel(c)))
    .join(",")
  const lines = [headerLine]
  for (const row of working) {
    lines.push(
      cols.map((c) => csvEscapeField(sheetCellPlainExport(c, row[c]))).join(",")
    )
  }
  const blob = new Blob(["\ufeff", lines.join("\r\n")], {
    type: "text/csv;charset=utf-8",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `aaa-alerts-${new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/:/g, "-")}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function getLocalHourRangeMs() {
  const now = new Date()
  const start = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    now.getHours(),
    0,
    0,
    0
  )
  const end = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
    now.getHours(),
    59,
    59,
    999
  )
  return { startMs: start.getTime(), endMs: end.getTime() }
}

function syncSheetFilterPanelFromState(root) {
  const filterPanel = root.querySelector(".alert-sheet-filter-panel")
  const btnFilter = root.querySelector("#aaa-sheet-toggle-filter")
  if (filterPanel) filterPanel.hidden = !unifiedSheetState.filterPanelOpen
  if (btnFilter) {
    btnFilter.textContent = unifiedSheetState.filterPanelOpen
      ? "Hide range filter"
      : "Show range filter"
  }
  if (unifiedSheetState.filterPanelOpen) {
    renderNumericFilterPanel(root)
  }
  refreshUnifiedSheetTable(root)
}

function applyCurrentHourTimeFilter() {
  const { startMs, endMs } = getLocalHourRangeMs()
  unifiedSheetState.numericFilters = unifiedSheetState.numericFilters.filter(
    (f) => f && f.column !== "time"
  )
  unifiedSheetState.numericFilters.push({
    id: unifiedSheetState.nextFilterId++,
    column: "time",
    min: String(startMs),
    max: String(endMs),
  })
  unifiedSheetState.filterPanelOpen = true
  const needRedraw = alertsViewMode !== "sheet"
  if (needRedraw) {
    setAlertsViewMode("sheet")
  }
  const stream = getElement("alerts-stream")
  const root = stream?.querySelector(".alert-sheet-dashboard")
  if (root) syncSheetFilterPanelFromState(root)
}

function refreshUnifiedSheetTable(dash) {
  const table = dash.querySelector(".alert-sheet-table.unified")
  const thead = table?.querySelector("thead")
  const tbody = table?.querySelector("tbody")
  const footer = dash.querySelector(".alert-sheet-unified-footer")
  if (!table || !thead || !tbody || !footer) return

  const { allRows, working, cols } = computeUnifiedSheetDisplay()
  thead.replaceChildren()
  const hr = document.createElement("tr")
  if (cols.length === 0) {
    const th = document.createElement("th")
    th.textContent = "—"
    hr.appendChild(th)
  } else {
    for (const col of cols) {
      const th = document.createElement("th")
      th.dataset.col = col
      th.className = "alert-sheet-th-sortable"
      const grip = document.createElement("span")
      grip.className = "alert-sheet-col-drag"
      grip.textContent = "⋮⋮"
      grip.draggable = true
      grip.title = "Drag to reorder column"
      grip.setAttribute("aria-hidden", "true")
      grip.addEventListener("dragstart", (e) => {
        e.stopPropagation()
        e.dataTransfer.setData("text/plain", col)
        e.dataTransfer.effectAllowed = "move"
        th.classList.add("alert-sheet-th-dragging")
      })
      const label = document.createElement("span")
      label.className = "alert-sheet-col-label"
      label.textContent = getSheetColumnHeaderLabel(col)
      label.title = "Click to sort"
      label.addEventListener("click", (e) => {
        e.stopPropagation()
        if (unifiedSheetState.sortCol === col) {
          unifiedSheetState.sortDir =
            unifiedSheetState.sortDir === "asc" ? "desc" : "asc"
        } else {
          unifiedSheetState.sortCol = col
          unifiedSheetState.sortDir = "asc"
        }
        refreshUnifiedSheetTable(dash)
      })
      th.appendChild(grip)
      th.appendChild(label)
      if (unifiedSheetState.sortCol === col) {
        const ind = document.createElement("span")
        ind.className = "alert-sheet-sort-ind"
        ind.textContent = unifiedSheetState.sortDir === "desc" ? " ▼" : " ▲"
        th.appendChild(ind)
      }
      th.addEventListener("dragover", (e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = "move"
        th.classList.add("alert-sheet-th-drop-target")
      })
      th.addEventListener("dragleave", (e) => {
        if (!th.contains(e.relatedTarget)) {
          th.classList.remove("alert-sheet-th-drop-target")
        }
      })
      th.addEventListener("drop", (e) => {
        e.preventDefault()
        th.classList.remove("alert-sheet-th-drop-target")
        const fromCol = e.dataTransfer.getData("text/plain")
        if (fromCol && fromCol !== col) {
          reorderSheetColumns(dash, fromCol, col)
        }
      })
      hr.appendChild(th)
    }
  }
  thead.appendChild(hr)

  tbody.replaceChildren()
  if (cols.length === 0) {
    const tr = document.createElement("tr")
    const td = document.createElement("td")
    td.className = "alert-sheet-empty-msg"
    td.textContent =
      allRows.length === 0
        ? "No alerts yet."
        : "No columns visible — open Column controls or click Show all."
    tr.appendChild(td)
    tbody.appendChild(tr)
  } else {
    for (const row of working) {
      const tr = document.createElement("tr")
      for (const col of cols) {
        const td = document.createElement("td")
        appendSheetTableCell(td, col, row[col])
        tr.appendChild(td)
      }
      tbody.appendChild(tr)
    }
  }

  footer.textContent = `Showing ${working.length} of ${allRows.length} rows`
}

function reorderSheetColumns(dash, fromCol, toCol) {
  const allRows = getAllUnifiedSheetRows()
  const order = [...getSheetColumnsOrdered(allRows)]
  const fi = order.indexOf(fromCol)
  const ti = order.indexOf(toCol)
  if (fi < 0 || ti < 0 || fromCol === toCol) return
  const [moved] = order.splice(fi, 1)
  order.splice(ti, 0, moved)
  unifiedSheetState.sheetColumnOrder = order
  saveSheetColumnOrder(order)
  refreshUnifiedSheetTable(dash)
  renderColumnControlPanel(dash)
}

function createUnifiedSheetDashboard() {
  const root = document.createElement("div")
  root.className = "alert-sheet-dashboard"

  const toolbar = document.createElement("div")
  toolbar.className = "alert-sheet-toolbar"

  const search = document.createElement("input")
  search.type = "search"
  search.className = "alert-sheet-search"
  search.placeholder = "Search all columns…"
  search.autocomplete = "off"
  search.value = unifiedSheetState.searchRaw
  search.addEventListener("input", () => {
    unifiedSheetState.searchRaw = search.value
    if (sheetSearchDebounceTimer) clearTimeout(sheetSearchDebounceTimer)
    sheetSearchDebounceTimer = setTimeout(() => {
      sheetSearchDebounceTimer = null
      refreshUnifiedSheetTable(root)
    }, 120)
  })

  const btnFilter = document.createElement("button")
  btnFilter.type = "button"
  btnFilter.id = "aaa-sheet-toggle-filter"
  btnFilter.className = "ghost alert-sheet-toggle"
  btnFilter.textContent = unifiedSheetState.filterPanelOpen
    ? "Hide range filter"
    : "Show range filter"

  const btnCol = document.createElement("button")
  btnCol.type = "button"
  btnCol.className = "ghost alert-sheet-toggle"
  btnCol.textContent = unifiedSheetState.colPanelOpen
    ? "Hide column controls"
    : "Show column controls"

  const btnColReset = document.createElement("button")
  btnColReset.type = "button"
  btnColReset.className = "ghost alert-sheet-toggle"
  btnColReset.title =
    "Restore default column order (item, buyout_prices, realmNames, time, …)"
  btnColReset.textContent = "Reset column order"
  btnColReset.addEventListener("click", () => {
    unifiedSheetState.sheetColumnOrder = null
    try {
      localStorage.removeItem(SHEET_COLUMN_ORDER_STORAGE_KEY)
    } catch {
      // ignore
    }
    refreshUnifiedSheetTable(root)
    renderColumnControlPanel(root)
  })

  const toolbarActions = document.createElement("div")
  toolbarActions.className = "alert-sheet-toolbar-actions"
  toolbarActions.appendChild(btnFilter)
  toolbarActions.appendChild(btnCol)
  toolbarActions.appendChild(btnColReset)
  toolbar.appendChild(toolbarActions)
  toolbar.appendChild(search)

  const filterPanel = document.createElement("div")
  filterPanel.className = "alert-sheet-panel alert-sheet-filter-panel"
  filterPanel.hidden = !unifiedSheetState.filterPanelOpen
  const filterTitle = document.createElement("div")
  filterTitle.className = "alert-sheet-panel-title"
  filterTitle.textContent = "Range filter"
  const filterActions = document.createElement("div")
  filterActions.className = "alert-sheet-panel-actions"
  const addF = document.createElement("button")
  addF.type = "button"
  addF.className = "primary"
  addF.textContent = "Add filter"
  addF.addEventListener("click", () => {
    unifiedSheetState.numericFilters.push({
      id: unifiedSheetState.nextFilterId++,
      column: "",
      min: "",
      max: "",
    })
    renderNumericFilterPanel(root)
    refreshUnifiedSheetTable(root)
  })
  const clearF = document.createElement("button")
  clearF.type = "button"
  clearF.className = "danger"
  clearF.textContent = "Clear all"
  clearF.addEventListener("click", () => {
    unifiedSheetState.numericFilters = []
    renderNumericFilterPanel(root)
    refreshUnifiedSheetTable(root)
  })
  filterActions.appendChild(addF)
  filterActions.appendChild(clearF)
  const filterList = document.createElement("div")
  filterList.className = "alert-sheet-filter-list"
  const filterHint = document.createElement("div")
  filterHint.className = "alert-sheet-filter-hint"
  const filterHintNumeric = document.createElement("p")
  filterHintNumeric.textContent =
    "For numeric columns, choose a column and optional min / max. Bounds use the numbers parsed from cells (prices, percentages, etc.); leave min or max empty for an open-ended range."
  const filterHintTime = document.createElement("p")
  filterHintTime.textContent =
    "Time filters use each alert’s embed timestamp. The sheet shows local time; copying a Time cell puts ISO-8601 on the clipboard. You can also paste ISO-8601 or Unix ms."
  filterHint.appendChild(filterHintNumeric)
  filterHint.appendChild(filterHintTime)
  filterPanel.appendChild(filterTitle)
  filterPanel.appendChild(filterHint)
  filterPanel.appendChild(filterActions)
  filterPanel.appendChild(filterList)

  const colPanel = document.createElement("div")
  colPanel.className = "alert-sheet-panel alert-sheet-col-panel"
  colPanel.hidden = !unifiedSheetState.colPanelOpen
  const colTitle = document.createElement("div")
  colTitle.className = "alert-sheet-panel-title"
  colTitle.textContent = "Column controls"
  const colNav = document.createElement("div")
  colNav.className = "alert-sheet-col-nav"
  const colChecks = document.createElement("div")
  colChecks.className = "alert-sheet-col-checkboxes"
  const colPageLabel = document.createElement("span")
  colPageLabel.className = "alert-sheet-col-page-label"
  const prevP = document.createElement("button")
  prevP.type = "button"
  prevP.className = "ghost"
  prevP.textContent = "Previous"
  const nextP = document.createElement("button")
  nextP.type = "button"
  nextP.className = "ghost"
  nextP.textContent = "Next"
  const showAll = document.createElement("button")
  showAll.type = "button"
  showAll.className = "success"
  showAll.textContent = "Show all"
  const hideAll = document.createElement("button")
  hideAll.type = "button"
  hideAll.className = "danger"
  hideAll.textContent = "Hide all"
  colNav.appendChild(prevP)
  colNav.appendChild(colPageLabel)
  colNav.appendChild(nextP)
  const colFoot = document.createElement("div")
  colFoot.className = "alert-sheet-col-foot"
  colFoot.appendChild(showAll)
  colFoot.appendChild(hideAll)
  colPanel.appendChild(colTitle)
  colPanel.appendChild(colChecks)
  colPanel.appendChild(colNav)
  colPanel.appendChild(colFoot)

  prevP.addEventListener("click", () => {
    if (unifiedSheetState.colPage > 0) {
      unifiedSheetState.colPage--
      renderColumnControlPanel(root)
    }
  })
  nextP.addEventListener("click", () => {
    const allRows = getAllUnifiedSheetRows()
    const allCols = getSheetColumnsOrdered(allRows)
    const totalPages = Math.max(
      1,
      Math.ceil(allCols.length / SHEET_COL_PAGE_SIZE)
    )
    if (unifiedSheetState.colPage < totalPages - 1) {
      unifiedSheetState.colPage++
      renderColumnControlPanel(root)
    }
  })
  showAll.addEventListener("click", () => {
    const allRows = getAllUnifiedSheetRows()
    const allCols = getSheetColumnsOrdered(allRows)
    for (const c of allCols) unifiedSheetState.columnVisible[c] = true
    renderColumnControlPanel(root)
    refreshUnifiedSheetTable(root)
  })
  hideAll.addEventListener("click", () => {
    const allRows = getAllUnifiedSheetRows()
    const allCols = getSheetColumnsOrdered(allRows)
    for (const c of allCols) unifiedSheetState.columnVisible[c] = false
    renderColumnControlPanel(root)
    refreshUnifiedSheetTable(root)
  })

  btnFilter.addEventListener("click", () => {
    unifiedSheetState.filterPanelOpen = !unifiedSheetState.filterPanelOpen
    filterPanel.hidden = !unifiedSheetState.filterPanelOpen
    btnFilter.textContent = unifiedSheetState.filterPanelOpen
      ? "Hide range filter"
      : "Show range filter"
    if (unifiedSheetState.filterPanelOpen) {
      renderNumericFilterPanel(root)
    }
  })
  btnCol.addEventListener("click", () => {
    unifiedSheetState.colPanelOpen = !unifiedSheetState.colPanelOpen
    colPanel.hidden = !unifiedSheetState.colPanelOpen
    btnCol.textContent = unifiedSheetState.colPanelOpen
      ? "Hide column controls"
      : "Show column controls"
    if (unifiedSheetState.colPanelOpen) {
      renderColumnControlPanel(root)
    }
  })

  const scroll = document.createElement("div")
  scroll.className = "alert-sheet-scroll unified"
  const table = document.createElement("table")
  table.className = "alert-sheet-table unified"
  table.addEventListener("copy", (e) => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return
    let node = sel.anchorNode
    if (!node) return
    if (node.nodeType === Node.TEXT_NODE) node = node.parentElement
    const td =
      node && typeof node.closest === "function" ? node.closest("td") : null
    if (
      !td ||
      td.dataset.sheetTimeIso == null ||
      td.dataset.sheetTimeIso === ""
    )
      return
    e.preventDefault()
    e.clipboardData.setData("text/plain", td.dataset.sheetTimeIso)
  })
  const thead = document.createElement("thead")
  const tbody = document.createElement("tbody")
  table.appendChild(thead)
  table.appendChild(tbody)
  scroll.appendChild(table)

  table.addEventListener("dragend", () => {
    table.querySelectorAll("th").forEach((th) => {
      th.classList.remove(
        "alert-sheet-th-dragging",
        "alert-sheet-th-drop-target"
      )
    })
  })

  const footer = document.createElement("div")
  footer.className = "alert-sheet-unified-footer"

  root.appendChild(toolbar)
  root.appendChild(filterPanel)
  root.appendChild(colPanel)
  root.appendChild(scroll)
  root.appendChild(footer)

  renderNumericFilterPanel(root)
  renderColumnControlPanel(root)
  refreshUnifiedSheetTable(root)
  return root
}

function redrawAlertsStream() {
  const stream = getElement("alerts-stream")
  if (!stream) return
  stream.replaceChildren()
  if (alertsViewMode === "sheet") {
    stream.appendChild(createUnifiedSheetDashboard())
    return
  }
  const frag = document.createDocumentFragment()
  for (const { embed } of alertEmbedHistory) {
    frag.appendChild(buildAlertElement(embed, alertsViewMode))
  }
  stream.appendChild(frag)
}

function buildAlertElement(embed, mode) {
  const fields = Array.isArray(embed.fields) ? embed.fields : []
  if (mode === "discord") {
    return createDiscordFlatGroup(embed, fields)
  }
  if (mode === "details") {
    return createAlertTableGroup(embed, fields)
  }
  return createDiscordFlatGroup(embed, fields)
}

function refreshAlertsViewToggleButtons() {
  for (const m of ALERT_VIEW_MODES) {
    const btn = document.getElementById(`alerts-view-${m}`)
    if (!btn) continue
    const on = alertsViewMode === m
    btn.classList.toggle("alerts-view-btn-active", on)
    btn.setAttribute("aria-pressed", on ? "true" : "false")
  }
}

function setAlertsViewMode(mode) {
  if (!ALERT_VIEW_MODES.includes(mode)) return
  if (mode === alertsViewMode) return
  alertsViewMode = mode
  localStorage.setItem(ALERTS_VIEW_STORAGE_KEY, mode)
  redrawAlertsStream()
  refreshAlertsViewToggleButtons()
}

function appendAlertEmbed(embed) {
  const stream = getElement("alerts-stream")
  if (!stream || !embed || typeof embed !== "object") return
  const nearBottom =
    stream.scrollHeight - stream.scrollTop - stream.clientHeight < 140

  alertEmbedHistory.push({ embed })

  const cap = getMaxInAppAlerts()
  if (alertsViewMode === "sheet") {
    if (alertEmbedHistory.length > cap) {
      alertEmbedHistory.shift()
    }
    let dash = stream.querySelector(".alert-sheet-dashboard")
    if (!dash) {
      redrawAlertsStream()
      dash = stream.querySelector(".alert-sheet-dashboard")
    }
    if (dash) refreshUnifiedSheetTable(dash)
  } else {
    if (alertEmbedHistory.length > cap) {
      alertEmbedHistory.shift()
      if (stream.firstChild) {
        stream.removeChild(stream.firstChild)
      }
    }
    stream.appendChild(buildAlertElement(embed, alertsViewMode))
  }
  if (nearBottom) {
    stream.scrollTop = stream.scrollHeight
  }
}

// Helper function for fetch with timeout
async function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => {
    controller.abort()
  }, timeoutMs)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    if (error.name === "AbortError") {
      throw new Error(`Request timeout after ${timeoutMs}ms`)
    }
    throw error
  }
}

// Helper function for safe DOM element access
function getElement(id) {
  const element = document.getElementById(id)
  if (!element) {
    console.warn(`Element with id "${id}" not found`)
  }
  return element
}

const WOW_DISCORD_CONSENT =
  "I have gone to discord and asked the devs about this api and i know it only updates once per hour and will not spam the api like an idiot and there is no point in making more than one request per hour and i will not make request for one item at a time i know many apis support calling multiple items at once"

// Keep in sync with root package.json version (avoid IPC on every Saddlebag request — was causing UI jitter)
const SADDLEBAG_USER_AGENT = "AzerothAuctionAssassin/2.1.1"

function saddlebagFetchHeaders(base = {}) {
  return { ...base, "User-Agent": SADDLEBAG_USER_AGENT }
}

const state = {
  megaData: {},
  desiredItems: {},
  ilvlList: [],
  petIlvlList: [],
  realmLists: {},
  processRunning: false,
}

let alertAudioCtx = null
let alertAudioEl = null
let alertAudioSrc = ""
let lastAlertSoundAt = 0

function isAlertSoundEnabled() {
  return Boolean(state.megaData?.ALERT_SOUND_ENABLED)
}

function getAlertSoundVolume() {
  const n = Number(state.megaData?.ALERT_SOUND_VOLUME)
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    return DEFAULT_ALERT_SOUND_VOLUME
  }
  return Math.min(100, Math.max(1, n))
}

function getAlertSoundFile() {
  return String(state.megaData?.ALERT_SOUND_FILE || "").trim()
}

function toLocalFileAudioSrc(soundFile) {
  const raw = String(soundFile || "").trim()
  if (!raw) return ""
  if (/^file:\/\//i.test(raw)) return raw
  const normalized = raw.replace(/\\/g, "/")
  const encoded = encodeURI(normalized).replace(/#/g, "%23")
  if (/^[a-zA-Z]:\//.test(normalized)) {
    return `file:///${encoded}`
  }
  if (normalized.startsWith("/")) {
    return `file://${encoded}`
  }
  return `file:///${encoded}`
}

function playBuiltInAlertSound(volume) {
  try {
    if (!alertAudioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      if (!AudioCtx) return
      alertAudioCtx = new AudioCtx()
    }
    if (alertAudioCtx.state === "suspended") {
      alertAudioCtx.resume().catch(() => {})
    }
    const t0 = alertAudioCtx.currentTime
    const osc = alertAudioCtx.createOscillator()
    const gain = alertAudioCtx.createGain()
    osc.type = "triangle"
    osc.frequency.setValueAtTime(880, t0)
    osc.frequency.exponentialRampToValueAtTime(1320, t0 + 0.08)
    const vol = Math.max(
      0.01,
      Math.min(
        1,
        (Number(volume || 0) / 100) * BUILTIN_ALERT_SOUND_GAIN_MULTIPLIER
      )
    )
    gain.gain.setValueAtTime(0.0001, t0)
    gain.gain.exponentialRampToValueAtTime(0.08 * vol, t0 + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.12)
    osc.connect(gain)
    gain.connect(alertAudioCtx.destination)
    osc.start(t0)
    osc.stop(t0 + 0.13)
  } catch {
    // ignore audio errors so alerts continue normally
  }
}

function playAlertSound() {
  if (!isAlertSoundEnabled()) return
  const now = Date.now()
  if (now - lastAlertSoundAt < 120) return
  lastAlertSoundAt = now
  const vol = getAlertSoundVolume()
  const soundFile = getAlertSoundFile()
  if (!soundFile) {
    playBuiltInAlertSound(vol)
    return
  }
  try {
    const src = toLocalFileAudioSrc(soundFile)
    if (!alertAudioEl || alertAudioSrc !== src) {
      alertAudioEl = new Audio(src)
      alertAudioSrc = src
    }
    alertAudioEl.volume = Math.max(0.01, Math.min(1, vol / 100))
    alertAudioEl.currentTime = 0
    const playPromise = alertAudioEl.play()
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        playBuiltInAlertSound(vol)
      })
    }
  } catch {
    playBuiltInAlertSound(vol)
  }
}

function getMaxInAppAlerts() {
  const raw = state.megaData?.MAX_IN_APP_ALERTS
  const n = Number(raw)
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    return DEFAULT_MAX_IN_APP_ALERTS
  }
  return Math.min(MAX_IN_APP_ALERTS_HARD_CAP, Math.max(1, n))
}

/** Drop oldest alerts when history exceeds settings cap; refresh Alerts UI. */
function trimAlertEmbedHistoryToLimit() {
  const max = getMaxInAppAlerts()
  let changed = false
  while (alertEmbedHistory.length > max) {
    alertEmbedHistory.shift()
    changed = true
  }
  if (!changed) return
  const stream = getElement("alerts-stream")
  if (!stream) return
  if (alertsViewMode === "sheet") {
    const dash = stream.querySelector(".alert-sheet-dashboard")
    if (dash) refreshUnifiedSheetTable(dash)
  } else {
    redrawAlertsStream()
  }
}

const megaForm = getElement("mega-form")
const itemList = getElement("item-list")
const ilvlTable = getElement("ilvl-table")
const petIlvlTable = getElement("pet-ilvl-table")
const logPanel = getElement("log-panel")
const processState = getElement("process-state")
const saveSettingsBtn = getElement("save-settings-btn")
const reloadBtn = getElement("reload-btn")
const startBtn = getElement("start-btn")
const stopBtn = getElement("stop-btn")
const backBtn = getElement("back-btn")
const forwardBtn = getElement("forward-btn")
const navButtons = Array.from(document.querySelectorAll(".nav-btn"))
const itemSearchInput = getElement("item-search-input")
const itemSearchBtn = getElement("item-search-btn")
const itemSearchResults = getElement("item-search-results")
const itemSearchStatus = getElement("item-search-status")
const itemFilterInput = getElement("item-filter-input")
const ilvlFilterInput = getElement("ilvl-filter-input")
const petIlvlFilterInput = getElement("pet-ilvl-filter-input")
const petIlvlSearchInput = getElement("pet-ilvl-search-input")
const realmList = getElement("realm-list")
const realmForm = getElement("realm-form")
const realmRegionSelect = getElement("realm-region-select")
const realmNameInput = getElement("realm-name-input")
const realmIdInput = getElement("realm-id-input")
const realmFilterInput = getElement("realm-filter-input")
const resetRealmBtn = getElement("reset-realm-btn")
const removeRealmBtn = getElement("remove-realm-btn")
const removeAllRealmsBtn = getElement("remove-all-realms-btn")
const restoreBackupBtn = getElement("restore-backup-btn")
const restoreBackupItemsBtn = getElement("restore-backup-items-btn")
const restoreBackupIlvlBtn = getElement("restore-backup-ilvl-btn")
const restoreBackupPetsBtn = getElement("restore-backup-pets-btn")
const resetSettingsBtn = getElement("reset-settings-btn")
const resetItemsBtn = getElement("reset-items-btn")
const resetIlvlBtn = getElement("reset-ilvl-btn")
const resetPetsBtn = getElement("reset-pets-btn")
const petIlvlSearchBtn = getElement("pet-ilvl-search-btn")
const petIlvlSearchResults = getElement("pet-ilvl-search-results")
const petIlvlSearchStatus = getElement("pet-ilvl-search-status")
const ilvlSearchInput = getElement("ilvl-search-input")
const ilvlSearchBtn = getElement("ilvl-search-btn")
const ilvlSearchResults = getElement("ilvl-search-results")
const ilvlSearchStatus = getElement("ilvl-search-status")
const itemSearchSuggest = getElement("item-search-suggest")
const petIlvlSearchSuggest = getElement("pet-ilvl-search-suggest")
const ilvlSearchSuggest = getElement("ilvl-search-suggest")
const importConfigBtn = getElement("import-config-btn")
const exportConfigBtn = getElement("export-config-btn")
const importItemsBtn = getElement("import-items-btn")
const exportItemsBtn = getElement("export-items-btn")
const importIlvlBtn = getElement("import-ilvl-btn")
const exportIlvlBtn = getElement("export-ilvl-btn")
const importPetIlvlBtn = getElement("import-pet-ilvl-btn")
const exportPetIlvlBtn = getElement("export-pet-ilvl-btn")
const pasteConfigBtn = getElement("paste-config-btn")
const copyConfigBtn = getElement("copy-config-btn")
const pasteItemsBtn = getElement("paste-items-btn")
const copyItemsBtn = getElement("copy-items-btn")
const pastePBSItemsBtn = getElement("paste-pbs-items-btn")
const copyPBSItemsBtn = getElement("copy-pbs-items-btn")
const pasteIlvlBtn = getElement("paste-ilvl-btn")
const copyIlvlBtn = getElement("copy-ilvl-btn")
const pastePBSIlvlBtn = getElement("paste-pbs-ilvl-btn")
const copyPBSIlvlBtn = getElement("copy-pbs-ilvl-btn")
const pastePetIlvlBtn = getElement("paste-pet-ilvl-btn")
const copyPetIlvlBtn = getElement("copy-pet-ilvl-btn")
const pastePBSPetIlvlBtn = getElement("paste-pbs-pet-ilvl-btn")
const copyPBSPetIlvlBtn = getElement("copy-pbs-pet-ilvl-btn")
const alertSoundVolumeSlider = getElement("alert-sound-volume-slider")
const alertSoundVolumeInput = getElement("alert-sound-volume-input")
const alertSoundFileInput = getElement("alert-sound-file-input")
const alertSoundBrowseBtn = getElement("alert-sound-browse-btn")
const alertSoundClearBtn = getElement("alert-sound-clear-btn")
let itemNameMap = {}
let petNameMap = {}

function normalizeAlertSoundVolumeInput(raw) {
  const n = Number(raw)
  if (!Number.isFinite(n)) return DEFAULT_ALERT_SOUND_VOLUME
  return Math.min(100, Math.max(1, Math.trunc(n)))
}

function syncAlertSoundControlsFromData(data) {
  const v = normalizeAlertSoundVolumeInput(data?.ALERT_SOUND_VOLUME)
  if (alertSoundVolumeSlider) alertSoundVolumeSlider.value = String(v)
  if (alertSoundVolumeInput) alertSoundVolumeInput.value = String(v)
  if (alertSoundFileInput) {
    alertSoundFileInput.value = String(data?.ALERT_SOUND_FILE || "")
  }
}

let itemSearchCache = null
let itemSearchLoading = false
let petSearchCache = null
let petSearchLoading = false

let editingIlvlIndex = null
let editingPetIlvlIndex = null

/**
 * Clear ilvl form and reset to "add new" mode
 */
function clearIlvlForm() {
  editingIlvlIndex = null
  const form = document.getElementById("ilvl-form")
  if (form) {
    form.reset()
    form.ilvl.value = 150
    form.max_ilvl.value = 10000
    form.buyout.value = 100000
    form.required_min_lvl.value = 1
    form.required_max_lvl.value = 999
    const submitBtn = form.querySelector('button[type="submit"]')
    if (submitBtn) submitBtn.textContent = "Add rule"
    form.ilvl.focus()
  }
}

/**
 * Convert pet quality integer to human-readable label
 * @param {number} quality - Quality value (-1, 0, 1, 2, or 3)
 * @returns {string} Human-readable quality label
 */
function getQualityLabel(quality) {
  const qualityMap = {
    "-1": "All",
    0: "Poor",
    1: "Common",
    2: "Uncommon",
    3: "Rare",
  }
  return qualityMap[String(quality)] || "All"
}

/**
 * Clear pet ilvl form and reset to "add new" mode
 */
function clearPetIlvlForm() {
  editingPetIlvlIndex = null
  const form = document.getElementById("pet-ilvl-form")
  if (form) {
    form.reset()
    form.minLevel.value = 1
    form.minQuality.value = "-1" // Set dropdown to "All"
    renderExcludeBreeds("")
    const submitBtn = form.querySelector('button[type="submit"]')
    if (submitBtn) submitBtn.textContent = "Add pet rule"
    form.petID.focus()
  }
}

/**
 * Get item name with fallback to "Unknown item name" if not found
 * @param {string|number} id - Item ID
 * @returns {string} Item name or "Unknown item name"
 */
function getItemName(id) {
  const key = String(id)
  return itemNameMap[key] || "Unknown item name"
}

function ensureItemName(id, name) {
  const key = String(id)
  if (name) {
    itemNameMap[key] = name
    return
  }
  if (itemNameMap[key]) return
  if (itemSearchCache) {
    const match = itemSearchCache.find((row) => String(row.itemID) === key)
    if (match?.itemName) {
      itemNameMap[key] = match.itemName
      return
    }
  }
  fetchItemNames().then(() => {
    const match = itemSearchCache?.find((row) => String(row.itemID) === key)
    if (match?.itemName) itemNameMap[key] = match.itemName
    renderItemList()
  })
}

/**
 * Get pet name with fallback to "Unknown pet name" if not found
 * @param {string|number} id - Pet ID
 * @returns {string} Pet name or "Unknown pet name"
 */
function getPetName(id) {
  const key = String(id)
  return petNameMap[key] || "Unknown pet name"
}

function ensurePetName(id, name) {
  const key = String(id)
  if (name) {
    petNameMap[key] = name
    return
  }
  if (petNameMap[key]) return
  if (petSearchCache) {
    const match = petSearchCache.find((row) => String(row.itemID) === key)
    if (match?.itemName) {
      petNameMap[key] = match.itemName
      return
    }
  }
  fetchPetNames().then(() => {
    const match = petSearchCache?.find((row) => String(row.itemID) === key)
    if (match?.itemName) petNameMap[key] = match.itemName
    renderPetIlvlRules()
  })
}

function setRunning(running) {
  state.processRunning = running
  processState.textContent = running ? "AH Scan Running" : "Not Running"
  processState.style.background = running
    ? "rgba(74,210,149,0.18)"
    : "rgba(128,255,234,0.1)"
  startBtn.disabled = running
  stopBtn.disabled = !running
}

function showView(view) {
  document
    .querySelectorAll(".view")
    .forEach((node) =>
      node.classList.toggle("active", node.dataset.view === view)
    )
  navButtons.forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.viewTarget === view)
  )
  if (view === "alerts") {
    redrawAlertsStream()
    refreshAlertsViewToggleButtons()
  }
  // Initialize exclude breeds dropdown when pet-ilvl view is shown
  if (view === "pet-ilvl") {
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
      const list = document.getElementById("exclude-breeds-list")
      const display = document.getElementById("exclude-breeds-display")
      if (list && display) {
        // Always re-render to ensure checkboxes are created
        const currentValue =
          display.textContent === "Select breed IDs..."
            ? ""
            : display.textContent
        renderExcludeBreeds(currentValue)
      }
    }, 50)
  }
}

function parseNums(text) {
  if (!text) return []
  const values = []
  const invalid = []
  text
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .forEach((t) => {
      const n = Number(t)
      if (Number.isNaN(n)) {
        invalid.push(t)
      } else {
        values.push(n)
      }
    })
  if (invalid.length > 0) {
    throw new Error(
      `Invalid number tokens: ${invalid.join(
        ", "
      )}. All values must be numbers.`
    )
  }
  return values
}

function updateSuggestions(inputEl, suggestEl, cache) {
  const term = (inputEl.value || "").toLowerCase().trim()
  if (!cache || !cache.length) return
  const matches = cache
    .filter((row) => row.itemName && row.itemName.toLowerCase().includes(term))
    .slice(0, 12)
  suggestEl.innerHTML = matches
    .map((row) => `<option value="${escapeHtml(row.itemName)}"></option>`)
    .join("")
}

async function handleImport(target, btn) {
  const res = await window.aaa.importJson(target)
  if (res?.error) {
    appendLog(`Import error: ${res.error}\n`)
    return
  }
  await loadState()
  flashButton(btn, "Imported!")
}

async function handleExport(target, btn) {
  const res = await window.aaa.exportJson(target)
  if (res?.error) {
    appendLog(`Export error: ${res.error}\n`)
  } else {
    flashButton(btn, "Exported!")
  }
}

function flashButton(btn, label = "Done") {
  if (!btn) return
  const original = btn.textContent
  btn.textContent = label
  btn.disabled = true
  setTimeout(() => {
    btn.textContent = original
    btn.disabled = false
  }, 900)
}

/**
 * Show a toast notification message
 * @param {string} message - The message to display
 * @param {string} type - 'error' or 'success' (default: 'error')
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = "error", duration = 3000) {
  // Remove any existing toast
  const existing = document.querySelector(".toast")
  if (existing) existing.remove()

  const toast = document.createElement("div")
  toast.className = `toast ${type === "success" ? "success" : ""}`
  toast.textContent = message
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.style.animation = "toastSlideIn 0.3s ease-out reverse"
    setTimeout(() => toast.remove(), 300)
  }, duration)
}

function showPasteModal(title, placeholder, onSubmit) {
  const overlay = document.createElement("div")
  overlay.className = "modal-overlay"
  const modal = document.createElement("div")
  modal.className = "modal"
  const heading = document.createElement("div")
  heading.style.fontWeight = "700"
  heading.textContent = title
  const ta = document.createElement("textarea")
  ta.placeholder = placeholder
  const actions = document.createElement("div")
  actions.className = "modal-actions"
  const cancel = document.createElement("button")
  cancel.className = "ghost"
  cancel.textContent = "Cancel"
  const apply = document.createElement("button")
  apply.className = "primary"
  apply.textContent = "Import"
  actions.appendChild(cancel)
  actions.appendChild(apply)
  modal.appendChild(heading)
  modal.appendChild(ta)
  modal.appendChild(actions)
  overlay.appendChild(modal)
  document.body.appendChild(overlay)
  ta.focus()

  const cleanup = () => overlay.remove()
  cancel.onclick = cleanup
  overlay.onclick = (e) => {
    if (e.target === overlay) cleanup()
  }
  apply.onclick = async () => {
    const text = ta.value
    if (!text.trim()) return cleanup()
    // Close modal first, then run onSubmit (which may show toast)
    cleanup()
    await onSubmit(text)
  }
}

function showBackupModal(title, backups, onSelect) {
  const overlay = document.createElement("div")
  overlay.className = "modal-overlay"
  const modal = document.createElement("div")
  modal.className = "modal"
  modal.style.maxWidth = "500px"
  const heading = document.createElement("div")
  heading.style.fontWeight = "700"
  heading.style.marginBottom = "16px"
  heading.textContent = title
  const list = document.createElement("div")
  list.style.display = "flex"
  list.style.flexDirection = "column"
  list.style.gap = "8px"
  list.style.maxHeight = "400px"
  list.style.overflowY = "auto"
  list.style.marginBottom = "16px"

  if (backups.length === 0) {
    const emptyMsg = document.createElement("div")
    emptyMsg.className = "muted"
    emptyMsg.textContent = "No backups found"
    list.appendChild(emptyMsg)
  } else {
    backups.forEach((backup) => {
      const item = document.createElement("button")
      item.className = "ghost"
      item.style.textAlign = "left"
      item.style.padding = "12px"
      item.style.cursor = "pointer"
      item.textContent = backup.displayDate
      item.onclick = () => {
        cleanup()
        onSelect(backup)
      }
      list.appendChild(item)
    })
  }

  const actions = document.createElement("div")
  actions.className = "modal-actions"
  const cancel = document.createElement("button")
  cancel.className = "ghost"
  cancel.textContent = "Cancel"
  actions.appendChild(cancel)
  modal.appendChild(heading)
  modal.appendChild(list)
  modal.appendChild(actions)
  overlay.appendChild(modal)
  document.body.appendChild(overlay)

  const cleanup = () => overlay.remove()
  cancel.onclick = cleanup
  overlay.onclick = (e) => {
    if (e.target === overlay) cleanup()
  }
}

function validatePetIlvlFormat(data) {
  // Check if it's the legacy format (object with numeric keys) and convert it
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const keys = Object.keys(data)
    if (keys.length > 0 && keys.every((k) => !Number.isNaN(Number(k)))) {
      // Convert legacy format to new format
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

      return { valid: true, converted }
    }
  }

  // Must be an array
  if (!Array.isArray(data)) {
    return {
      valid: false,
      error:
        'Invalid format. Expected an array of pet rules: [{"petID": 183, "price": 100000, ...}]',
    }
  }

  // Validate and filter rules, collecting invalid ones
  const validRules = []
  const invalidRules = []

  for (let i = 0; i < data.length; i++) {
    const rule = data[i]
    if (!rule || typeof rule !== "object") {
      invalidRules.push({ index: i, reason: "must be an object" })
      continue
    }

    // Check required fields
    if (rule.petID === undefined || rule.petID === null) {
      invalidRules.push({ index: i, reason: 'missing required field "petID"' })
      continue
    }

    if (rule.price === undefined || rule.price === null) {
      invalidRules.push({ index: i, reason: 'missing required field "price"' })
      continue
    }

    // Validate types and ranges
    const petID = Number(rule.petID)
    const price = Number(rule.price)
    const minLevel = Number(rule.minLevel ?? 1)
    const minQuality = Number(rule.minQuality ?? -1)
    const excludeBreeds = Array.isArray(rule.excludeBreeds)
      ? rule.excludeBreeds.map((b) => Number(b)).filter((b) => !Number.isNaN(b))
      : []

    // Validate pet ID range (1-10000)
    if (Number.isNaN(petID) || petID < 1 || petID > 10000) {
      invalidRules.push({
        index: i,
        reason: `petID must be between 1 and 10000, got ${rule.petID}`,
      })
      continue
    }

    // Validate price
    if (Number.isNaN(price) || price <= 0) {
      invalidRules.push({
        index: i,
        reason: `price must be greater than 0, got ${rule.price}`,
      })
      continue
    }

    // Validate minLevel (1-25)
    if (Number.isNaN(minLevel) || minLevel < 1 || minLevel > 25) {
      invalidRules.push({
        index: i,
        reason: `minLevel must be between 1 and 25, got ${
          rule.minLevel ?? "undefined"
        }`,
      })
      continue
    }

    // Validate minQuality (-1 to 3)
    if (Number.isNaN(minQuality) || minQuality < -1 || minQuality > 3) {
      invalidRules.push({
        index: i,
        reason: `minQuality must be between -1 and 3, got ${
          rule.minQuality ?? "undefined"
        }`,
      })
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
      valid: false,
      error: "No valid pet rules found. All rules were invalid.",
    }
  }

  // Return valid rules and info about invalid ones
  return {
    valid: true,
    validRules,
    invalidCount: invalidRules.length,
    invalidRules: invalidRules.slice(0, 5), // Show first 5 invalid rules for feedback
  }
}

async function handlePasteAAA(target, btn) {
  showPasteModal("Import AAA JSON", "{...}", async (raw) => {
    try {
      let parsed = JSON.parse(raw)

      // Validate pet ilvl format before importing
      if (target === "petIlvlList") {
        const validation = validatePetIlvlFormat(parsed)
        if (!validation.valid) {
          appendLog(`Import error: ${validation.error}\n`)
          showToast(validation.error, "error", 5000)
          return
        }
        // Legacy object format
        if (validation.converted) {
          parsed = validation.converted
          appendLog(
            `Converted legacy format: ${validation.converted.length} pet rules imported\n`
          )
          // New array format
        } else if (validation.validRules) {
          parsed = validation.validRules
          if (validation.invalidCount) {
            appendLog(
              `Skipped ${validation.invalidCount} invalid pet rules during import\n`
            )
          }
        }
      }

      if (target === "megaData") {
        state.megaData = await window.aaa.saveMegaData(parsed)
      } else if (target === "desiredItems") {
        state.desiredItems = await window.aaa.saveItems(parsed)
      } else if (target === "ilvlList") {
        state.ilvlList = await window.aaa.saveIlvl(parsed)
      } else if (target === "petIlvlList") {
        state.petIlvlList = await window.aaa.savePetIlvl(parsed)
      }
      await loadState()
      flashButton(btn, "Imported!")
    } catch (err) {
      const errorMsg =
        err instanceof SyntaxError
          ? `Invalid JSON: ${err.message}`
          : `Paste error: ${err.message || err}`
      appendLog(`${errorMsg}\n`)
      showToast(errorMsg, "error", 5000)
    }
  })
}

async function handleCopyAAA(target, btn) {
  let data
  if (target === "megaData") data = state.megaData
  else if (target === "desiredItems") data = state.desiredItems
  else if (target === "ilvlList") data = state.ilvlList
  else if (target === "petIlvlList") data = state.petIlvlList
  if (data === undefined) return
  await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
  appendLog("Copied JSON to clipboard\n")
  flashButton(btn, "Copied!")
}

function discountPercent() {
  const val = Number(
    state.megaData?.DISCOUNT_PERCENT || state.megaData?.discount_percent || 10
  )
  if (!Number.isFinite(val)) return 10
  return val
}

async function handlePastePBSItems(btn) {
  showPasteModal(
    "Import PBS items",
    'Example: Snipe?"Item";;0;0;0;0;0;0;0;50000;;#;;',
    async (text) => {
      await fetchItemNames()
      const pbs_data = text.replace(/\r|\n/g, "").split("^")
      const pbs_prices = {}
      for (const entry of pbs_data) {
        const parts = entry.split(";;")
        if (!parts[0]) continue
        let item_name = parts[0].trim()
        if (item_name.startsWith('"') && item_name.endsWith('"')) {
          item_name = item_name.slice(1, -1)
        }
        const price_parts = (parts[1] || "").split(";")
        const last = price_parts[price_parts.length - 1]
        const price = last && !Number.isNaN(Number(last)) ? Number(last) : null
        pbs_prices[item_name.toLowerCase()] = price
      }
      const tempItems = { ...state.desiredItems }
      for (const row of itemSearchCache || []) {
        const lower = row.itemName.toLowerCase()
        if (Object.hasOwn(pbs_prices, lower)) {
          const price = pbs_prices[lower]
          if (price !== null) {
            tempItems[String(row.itemID)] = price
          } else {
            const pct = discountPercent() / 100
            tempItems[String(row.itemID)] = Math.round(
              Number(row.desiredPrice || 0) * pct
            )
          }
        }
      }
      state.desiredItems = await window.aaa.saveItems(tempItems)
      await loadState()
      flashButton(btn, "Imported!")
    }
  )
}

async function handleCopyPBSItems(btn) {
  await fetchItemNames()
  const entries = []
  for (const [id, price] of Object.entries(state.desiredItems)) {
    const name = getItemName(id)
    entries.push(`"${name}";;0;0;0;0;0;0;0;${Math.trunc(Number(price))};;#;;`)
  }
  const timestamp = Date.now()
  const out = `AAA PBS List ${timestamp}^${entries.join("^")}`
  await navigator.clipboard.writeText(out)
  appendLog("Copied PBS items string to clipboard\n")
  flashButton(btn, "Copied!")
}

async function handlePastePBSIlvl(btn) {
  showPasteModal(
    "Import PBS ilvl string",
    'Example: Snipe?"Item";;430;470;1;80;0;0;0;50000;;#;;',
    async (text) => {
      await fetchItemNames()
      const pbs_data = text.replace(/\r|\n/g, "").split("^")
      const rules = [...state.ilvlList]
      for (const entry of pbs_data) {
        const parts = entry.split(";;")
        if (parts.length < 2) continue
        let item_name = parts[0].trim()
        if (item_name.startsWith('"') && item_name.endsWith('"')) {
          item_name = item_name.slice(1, -1)
        }
        const values = parts[1].split(";")
        if (values.length < 8) continue
        if (
          values[0] === "0" &&
          values[1] === "0" &&
          values[2] === "0" &&
          values[3] === "0"
        ) {
          continue
        }
        const min_ilvl = Number(values[0]) || 1
        const max_ilvl = Number(values[1]) || 10000
        const min_level = Number(values[2]) || 1
        const max_level = Number(values[3]) || 999
        const price = Number(values[7]) || 0
        const match = (itemSearchCache || []).find(
          (row) =>
            row.itemName &&
            row.itemName.toLowerCase() === item_name.toLowerCase()
        )
        const item_ids = match ? [Number(match.itemID)] : []
        const rule = {
          ilvl: min_ilvl,
          max_ilvl: max_ilvl,
          buyout: price,
          sockets: false,
          speed: false,
          leech: false,
          avoidance: false,
          item_ids,
          required_min_lvl: min_level,
          required_max_lvl: max_level,
          bonus_lists: [],
          item_names: {},
          base_ilvls: {},
          base_required_levels: {},
        }
        rules.push(rule)
      }
      state.ilvlList = await window.aaa.saveIlvl(rules)
      await loadState()
      flashButton(btn, "Imported!")
    }
  )
}

async function handleCopyPBSIlvl(btn) {
  await fetchItemNames()
  const entries = []
  for (const rule of state.ilvlList) {
    const ids = rule.item_ids && rule.item_ids.length ? rule.item_ids : [0]
    for (const id of ids) {
      const name = getItemName(id)
      entries.push(
        `"${name}";;${rule.ilvl};${rule.max_ilvl};${
          rule.required_min_lvl || 0
        };${rule.required_max_lvl || 0};0;0;0;${Math.trunc(
          Number(rule.buyout) || 0
        )};;#;;`
      )
    }
  }
  const timestamp = Date.now()
  const out = `AAA PBS Ilvl List ${timestamp}^${entries.join("^")}`
  await navigator.clipboard.writeText(out)
  appendLog("Copied PBS ilvl string to clipboard\n")
  flashButton(btn, "Copied!")
}

async function handlePastePBSPetIlvl(btn) {
  showPasteModal(
    "Import PBS pets",
    'Example: Snipe?"Pet";;0;0;0;0;0;0;0;50000;;#;;',
    async (text) => {
      await fetchPetNames()
      const pbs_data = text.replace(/\r|\n/g, "").split("^")
      const rules = [...state.petIlvlList]
      for (const pet of pbs_data) {
        const parts = pet.split(";;")
        if (!parts[0]) continue
        let pet_name = parts[0].trim()
        if (pet_name.startsWith('"') && pet_name.endsWith('"')) {
          pet_name = pet_name.slice(1, -1)
        }
        const price_parts = (parts[1] || "").split(";")
        const last = price_parts[price_parts.length - 1]
        const price = last && !Number.isNaN(Number(last)) ? Number(last) : null
        const match = (petSearchCache || []).find(
          (row) =>
            row.itemName &&
            row.itemName.toLowerCase() === pet_name.toLowerCase()
        )
        if (!match) continue
        rules.push({
          petID: Number(match.itemID),
          price: price !== null ? price : Number(match.desiredPrice || 0),
          minLevel: 1,
          minQuality: -1,
          excludeBreeds: [],
        })
      }
      state.petIlvlList = await window.aaa.savePetIlvl(rules)
      await loadState()
      flashButton(btn, "Imported!")
    }
  )
}

async function handleCopyPBSPetIlvl(btn) {
  await fetchPetNames()
  const entries = []
  for (const rule of state.petIlvlList) {
    const name = getPetName(rule.petID)
    entries.push(
      `"${name}";;0;0;0;0;0;0;0;${Math.trunc(Number(rule.price) || 0)};;#;;`
    )
  }
  const timestamp = Date.now()
  const out = `AAA PBS Pet Ilvl List ${timestamp}^${entries.join("^")}`
  await navigator.clipboard.writeText(out)
  appendLog("Copied PBS pet string to clipboard\n")
  flashButton(btn, "Copied!")
}

function renderMegaForm(data) {
  // Iterate over all form elements, not just FormData entries
  // This ensures all checkboxes are set, even if they're unchecked
  for (const el of megaForm.elements) {
    if (!el.name) continue
    if (el.type === "checkbox") {
      if (el.name === "USE_POST_MIDNIGHT_ILVL") {
        el.checked = Boolean(data[el.name] ?? true)
      } else if (el.name === "DISCORD_ALERTS_ENABLED") {
        el.checked = Boolean(data[el.name] ?? true)
      } else if (el.name === "IN_APP_ALERTS_ENABLED") {
        el.checked = Boolean(data[el.name] ?? false)
      } else {
        el.checked = Boolean(data[el.name])
      }
    } else if (el.type !== "submit" && el.type !== "button") {
      if (el.name === "MAX_IN_APP_ALERTS") {
        const v = data[el.name]
        el.value = String(
          v === undefined || v === null || v === ""
            ? DEFAULT_MAX_IN_APP_ALERTS
            : v
        )
      } else if (el.name === "ALERT_SOUND_VOLUME") {
        el.value = String(normalizeAlertSoundVolumeInput(data[el.name]))
      } else {
        el.value = data[el.name] ?? ""
      }
    }
  }
  // Handle extra alerts checkboxes separately
  renderExtraAlerts(data.EXTRA_ALERTS || "")
  syncAlertSoundControlsFromData(data)
}

function readMegaForm() {
  const out = {}
  // Iterate over all form elements, not just FormData entries
  // This ensures all checkboxes are saved, even if they're unchecked
  for (const el of megaForm.elements) {
    if (!el.name) continue
    if (el.type === "checkbox") {
      out[el.name] = el.checked
    } else if (el.type === "number") {
      const num = Number(el.value)
      out[el.name] = Number.isNaN(num) ? "" : num
    } else if (el.type !== "submit" && el.type !== "button") {
      out[el.name] = el.value
    }
  }
  // Handle extra alerts checkboxes separately
  out.EXTRA_ALERTS = readExtraAlerts()
  return out
}

/**
 * Render extra alerts checkboxes (1-59) in dropdown
 */
function renderExtraAlerts(extraAlertsJson) {
  const list = document.getElementById("extra-alerts-list")
  const display = document.getElementById("extra-alerts-display")
  if (!list || !display) return

  // Parse the JSON array, default to empty array if invalid
  let selectedMinutes = []
  if (extraAlertsJson) {
    try {
      selectedMinutes = JSON.parse(extraAlertsJson)
      if (!Array.isArray(selectedMinutes)) {
        selectedMinutes = []
      }
    } catch {
      selectedMinutes = []
    }
  }

  // Update display text
  if (selectedMinutes.length === 0) {
    display.textContent = "Select minutes..."
  } else {
    const sorted = [...selectedMinutes].sort((a, b) => a - b)
    if (sorted.length <= 5) {
      display.textContent = sorted.join(", ")
    } else {
      display.textContent = `${sorted.length} minutes selected`
    }
  }

  // Clear list
  list.innerHTML = ""

  // Create checkboxes for minutes 1-59
  for (let i = 1; i <= 59; i++) {
    const label = document.createElement("label")
    label.className = "extra-alert-checkbox"

    const checkbox = document.createElement("input")
    checkbox.type = "checkbox"
    checkbox.value = i
    checkbox.name = `extra_alert_${i}`
    checkbox.checked = selectedMinutes.includes(i)
    checkbox.addEventListener("change", () => {
      updateExtraAlertsDisplay()
    })

    const span = document.createElement("span")
    span.textContent = i

    label.appendChild(checkbox)
    label.appendChild(span)
    list.appendChild(label)
  }
}

/**
 * Update the display text for extra alerts dropdown
 */
function updateExtraAlertsDisplay() {
  const display = document.getElementById("extra-alerts-display")
  if (!display) return

  const selectedMinutes = readExtraAlertsArray()
  if (selectedMinutes.length === 0) {
    display.textContent = "Select minutes..."
  } else {
    const sorted = [...selectedMinutes].sort((a, b) => a - b)
    if (sorted.length <= 5) {
      display.textContent = sorted.join(", ")
    } else {
      display.textContent = `${sorted.length} minutes selected`
    }
  }
}

/**
 * Read extra alerts checkboxes and return as array of numbers
 */
function readExtraAlertsArray() {
  const list = document.getElementById("extra-alerts-list")
  if (!list) return []

  const selectedMinutes = []
  const checkboxes = list.querySelectorAll('input[type="checkbox"]:checked')
  for (const checkbox of checkboxes) {
    const value = Number(checkbox.value)
    if (!isNaN(value) && value >= 1 && value <= 59) {
      selectedMinutes.push(value)
    }
  }

  return selectedMinutes
}

/**
 * Read extra alerts checkboxes and return as JSON array string
 */
function readExtraAlerts() {
  const selectedMinutes = readExtraAlertsArray()
  // Sort the array for consistency
  selectedMinutes.sort((a, b) => a - b)
  return JSON.stringify(selectedMinutes)
}

/**
 * Render a key-value list with optional label function
 * @param {HTMLElement} target - Target element to render into
 * @param {Object} data - Key-value data object
 * @param {Function} onRemove - Callback for remove button
 * @param {Function} labelFn - Optional function that receives raw (id, price) and returns HTML string. Must escape HTML internally.
 * @param {Function} onClick - Optional click handler
 */
/**
 * Render a key-value list with optional label function
 * @param {HTMLElement} target - Target element to render into
 * @param {Object} data - Key-value data object
 * @param {Function} onRemove - Callback for remove button
 * @param {(labelEl: HTMLElement, id: string, price: string) => void} labelFn
 *   Optional function that receives the label container and raw (id, price)
 *   and is responsible for safely populating the DOM (using textContent, etc.).
 * @param {Function} onClick - Optional click handler
 */
function renderKVList(target, data, onRemove, labelFn, onClick) {
  target.innerHTML = ""
  const entries = Object.entries(data)
  if (entries.length === 0) {
    const li = document.createElement("li")
    li.textContent = "No entries yet."
    li.style.color = "#90a4b8"
    target.appendChild(li)
    return
  }
  entries.forEach(([id, price]) => {
    const li = document.createElement("li")
    const labelDiv = document.createElement("div")
    if (labelFn) {
      // labelFn populates labelDiv using safe DOM APIs
      labelFn(labelDiv, String(id), String(price))
    } else {
      // Default: use safe DOM APIs
      const strong = document.createElement("strong")
      strong.textContent = String(id)
      labelDiv.appendChild(strong)
      labelDiv.appendChild(document.createTextNode(` → ${price}`))
    }
    if (onClick) {
      labelDiv.style.cursor = "pointer"
      labelDiv.onclick = (e) => {
        e.stopPropagation()
        onClick(id, price)
      }
    }
    li.appendChild(labelDiv)
    const btn = document.createElement("button")
    btn.textContent = "Remove"
    btn.className = "ghost"
    btn.onclick = (e) => {
      e.stopPropagation()
      onRemove(id)
    }
    li.appendChild(btn)
    target.appendChild(li)
  })
}

function renderItemList() {
  const filterTerm = itemFilterInput
    ? itemFilterInput.value.toLowerCase().trim()
    : ""
  let filteredData = { ...state.desiredItems }

  if (filterTerm) {
    filteredData = {}
    Object.entries(state.desiredItems).forEach(([id, price]) => {
      const name = getItemName(id)
      const searchText = `${id} ${name}`.toLowerCase()
      if (searchText.includes(filterTerm)) {
        filteredData[id] = price
      }
    })
  }

  const itemForm = document.getElementById("item-form")
  const handleItemClick = (itemId, price) => {
    if (itemForm) {
      itemForm.id.value = itemId
      itemForm.price.value = price
      itemForm.id.focus()
    }
  }

  renderKVList(
    itemList,
    filteredData,
    removeItem,
    (labelEl, itemId, p) => {
      const name = getItemName(itemId) || "Unknown item name"
      const idNum = Number.parseInt(itemId, 10)

      const strong = document.createElement("strong")
      const link = document.createElement("a")

      // Guard against unexpected non-numeric IDs
      const safeId = Number.isFinite(idNum) ? String(idNum) : String(itemId)

      link.href = `https://www.wowhead.com/item=${safeId}`
      link.target = "_blank"
      link.rel = "noopener noreferrer"
      link.setAttribute("data-wowhead", `item=${safeId}`)
      link.textContent = safeId

      strong.appendChild(link)
      strong.appendChild(document.createTextNode(` • ${name}`))

      labelEl.appendChild(strong)
      labelEl.appendChild(document.createTextNode(` → ${String(p)}`))
    },
    handleItemClick
  )
}

function renderIlvlRules() {
  ilvlTable.innerHTML = ""
  if (!state.ilvlList.length) {
    const div = document.createElement("div")
    div.className = "table-row"
    div.textContent = "No ilvl rules yet."
    div.style.color = "#90a4b8"
    ilvlTable.appendChild(div)
    return
  }

  const filterTerm = ilvlFilterInput
    ? ilvlFilterInput.value.toLowerCase().trim()
    : ""
  let filteredRules = state.ilvlList

  if (filterTerm) {
    filteredRules = state.ilvlList.filter((rule) => {
      const itemIds = (rule.item_ids || []).map(String)
      const itemNames = itemIds.map((id) => getItemName(id))
      const searchText = `${itemIds.join(" ")} ${itemNames.join(" ")} ${
        rule.bonus_lists?.join(" ") || ""
      }`.toLowerCase()
      return searchText.includes(filterTerm)
    })
  }

  if (!filteredRules.length) {
    const div = document.createElement("div")
    div.className = "table-row"
    div.textContent = filterTerm
      ? "No rules match your filter."
      : "No ilvl rules yet."
    div.style.color = "#90a4b8"
    ilvlTable.appendChild(div)
    return
  }

  filteredRules.forEach((rule, filteredIdx) => {
    const idx = state.ilvlList.indexOf(rule)
    const row = document.createElement("div")
    row.className = "table-row"
    row.style.cursor = "pointer"

    const pill = document.createElement("div")
    pill.className = "pill"
    pill.textContent = `#${filteredIdx + 1}`
    row.appendChild(pill)

    const ilvlDiv = document.createElement("div")
    ilvlDiv.textContent = `ilvl ${rule.ilvl}-${rule.max_ilvl}`
    row.appendChild(ilvlDiv)

    const buyoutDiv = document.createElement("div")
    buyoutDiv.textContent = `${rule.buyout} gold`
    row.appendChild(buyoutDiv)

    const detailsDiv = document.createElement("div")
    if (rule.item_ids?.length) {
      const itemsLabel = document.createTextNode("Items: ")
      detailsDiv.appendChild(itemsLabel)
      const itemIds = rule.item_ids.slice(0, 5)
      itemIds.forEach((id, i) => {
        if (i > 0) {
          detailsDiv.appendChild(document.createTextNode(", "))
        }
        const nm = getItemName(id)
        const itemNameSpan = document.createElement("span")
        itemNameSpan.textContent = nm
        detailsDiv.appendChild(itemNameSpan)
        detailsDiv.appendChild(document.createTextNode(" ("))
        const itemLink = document.createElement("a")
        itemLink.href = `https://www.wowhead.com/item=${id}`
        itemLink.target = "_blank"
        itemLink.rel = "noopener noreferrer"
        itemLink.setAttribute("data-wowhead", `item=${id}`)
        itemLink.textContent = String(id)
        detailsDiv.appendChild(itemLink)
        detailsDiv.appendChild(document.createTextNode(")"))
      })
      if (rule.item_ids.length > 5) {
        detailsDiv.appendChild(document.createTextNode("…"))
      }
    } else {
      detailsDiv.textContent = "Any items"
    }

    const bonusesDiv1 = document.createElement("div")
    bonusesDiv1.className = "bonuses"
    bonusesDiv1.textContent = `Bonus IDs: ${
      rule.bonus_lists?.map(String).map(escapeHtml).join(", ") || "Any"
    }`
    detailsDiv.appendChild(bonusesDiv1)

    const bonusesDiv2 = document.createElement("div")
    bonusesDiv2.className = "bonuses"
    bonusesDiv2.textContent = `Player lvl: ${rule.required_min_lvl}-${rule.required_max_lvl}`
    detailsDiv.appendChild(bonusesDiv2)

    const bonusesDiv3 = document.createElement("div")
    bonusesDiv3.className = "bonuses"
    bonusesDiv3.textContent = `Sockets:${rule.sockets ? "Y" : "N"} Speed:${
      rule.speed ? "Y" : "N"
    } Leech:${rule.leech ? "Y" : "N"} Avoid:${rule.avoidance ? "Y" : "N"}`
    detailsDiv.appendChild(bonusesDiv3)

    row.appendChild(detailsDiv)
    const button = document.createElement("button")
    button.textContent = "Remove"
    button.className = "ghost"
    button.onclick = (e) => {
      e.stopPropagation()
      removeIlvlRule(idx)
    }
    row.appendChild(button)

    // Make row clickable to populate form
    row.onclick = (e) => {
      if (e.target === button || e.target.closest("button")) return
      const form = document.getElementById("ilvl-form")
      if (form) {
        editingIlvlIndex = idx
        form.ilvl.value = rule.ilvl || 150
        form.max_ilvl.value = rule.max_ilvl || 10000
        form.buyout.value = rule.buyout || 100000
        form.item_ids.value = (rule.item_ids || []).join(", ")
        form.bonus_lists.value = (rule.bonus_lists || []).join(", ")
        form.required_min_lvl.value = rule.required_min_lvl || 1
        form.required_max_lvl.value = rule.required_max_lvl || 1000
        form.sockets.checked = rule.sockets || false
        form.speed.checked = rule.speed || false
        form.leech.checked = rule.leech || false
        form.avoidance.checked = rule.avoidance || false
        const submitBtn = form.querySelector('button[type="submit"]')
        if (submitBtn) submitBtn.textContent = "Update rule"
        form.ilvl.focus()
      }
    }

    ilvlTable.appendChild(row)
  })
}

function renderPetIlvlRules() {
  petIlvlTable.innerHTML = ""
  if (!state.petIlvlList.length) {
    const div = document.createElement("div")
    div.className = "table-row"
    div.textContent = "No pet rules yet."
    div.style.color = "#90a4b8"
    petIlvlTable.appendChild(div)
    return
  }

  const filterTerm = petIlvlFilterInput
    ? petIlvlFilterInput.value.toLowerCase().trim()
    : ""
  let filteredRules = state.petIlvlList

  if (filterTerm) {
    filteredRules = state.petIlvlList.filter((rule) => {
      const name = getPetName(rule.petID)
      const searchText = `${rule.petID} ${name}`.toLowerCase()
      return searchText.includes(filterTerm)
    })
  }

  if (!filteredRules.length) {
    const div = document.createElement("div")
    div.className = "table-row"
    div.textContent = filterTerm
      ? "No rules match your filter."
      : "No pet rules yet."
    div.style.color = "#90a4b8"
    petIlvlTable.appendChild(div)
    return
  }

  filteredRules.forEach((rule, filteredIdx) => {
    const idx = state.petIlvlList.indexOf(rule)
    const name = getPetName(rule.petID)
    const row = document.createElement("div")
    row.className = "table-row"
    row.style.cursor = "pointer"

    const pill = document.createElement("div")
    pill.className = "pill"
    pill.textContent = `#${filteredIdx + 1}`
    row.appendChild(pill)

    const petIdDiv = document.createElement("div")
    petIdDiv.textContent = `Pet ${rule.petID}`
    row.appendChild(petIdDiv)

    const priceDiv = document.createElement("div")
    priceDiv.textContent = `${rule.price} gold`
    row.appendChild(priceDiv)

    const detailsDiv = document.createElement("div")
    const nameSpan = document.createElement("span")
    nameSpan.textContent = name
    detailsDiv.appendChild(nameSpan)

    const bonusesDiv = document.createElement("div")
    bonusesDiv.className = "bonuses"
    bonusesDiv.textContent = `Min lvl ${
      rule.minLevel
    }, quality ${getQualityLabel(rule.minQuality)}, exclude breeds: ${
      rule.excludeBreeds?.map(String).map(escapeHtml).join(",") || "none"
    }`
    detailsDiv.appendChild(bonusesDiv)

    row.appendChild(detailsDiv)
    const button = document.createElement("button")
    button.textContent = "Remove"
    button.className = "ghost"
    button.onclick = (e) => {
      e.stopPropagation()
      removePetIlvlRule(idx)
    }
    row.appendChild(button)

    // Make row clickable to populate form
    row.onclick = (e) => {
      if (e.target === button || e.target.closest("button")) return
      const form = document.getElementById("pet-ilvl-form")
      if (form) {
        editingPetIlvlIndex = idx
        form.petID.value = rule.petID || ""
        form.price.value = rule.price || ""
        form.minLevel.value = rule.minLevel || 1
        form.minQuality.value =
          rule.minQuality !== undefined ? String(rule.minQuality) : "-1"
        renderExcludeBreeds((rule.excludeBreeds || []).join(", "))
        const submitBtn = form.querySelector('button[type="submit"]')
        if (submitBtn) submitBtn.textContent = "Update pet rule"
        form.petID.focus()
      }
    }

    petIlvlTable.appendChild(row)
  })
}

function appendLog(line) {
  logPanel.textContent += line
  logPanel.scrollTop = logPanel.scrollHeight
  // Also write to log file
  if (window.aaa?.writeLog) {
    window.aaa.writeLog(line).catch(() => {
      // Silently fail if log file isn't available
    })
  }
}

async function loadState() {
  const payload = await window.aaa.loadState()
  state.megaData = payload.megaData || {}
  state.desiredItems = payload.desiredItems || {}
  state.ilvlList = payload.ilvlList || []
  state.petIlvlList = payload.petIlvlList || []
  setRunning(Boolean(payload.processRunning))
  renderMegaForm(state.megaData)
  renderItemList()
  renderIlvlRules()
  renderPetIlvlRules()
  await loadRealmLists()
  await loadDataDir()
  await loadZoomLevel()

  // Initialize extra alerts grid if not already rendered
  const container = document.getElementById("extra-alerts-container")
  if (container && container.children.length === 0) {
    renderExtraAlerts(state.megaData.EXTRA_ALERTS || "")
  }

  // attempt to hydrate name maps so existing lists show names once fetched
  fetchItemNames().then(() => {
    renderItemList()
    renderIlvlRules()
  })
  fetchPetNames().then(() => {
    renderPetIlvlRules()
  })

  trimAlertEmbedHistoryToLimit()
}

async function loadDataDir() {
  const dataDirInput = document.getElementById("data-dir-input")
  if (dataDirInput) {
    const currentDir = await window.aaa.getDataDir()
    dataDirInput.value = currentDir
  }
}

function updateZoomDisplay(zoomFactor) {
  const zoomDisplay = document.getElementById("zoom-level-display")
  if (zoomDisplay) {
    const zoomPercent = Math.round((zoomFactor || 1.0) * 100)
    zoomDisplay.textContent = `${zoomPercent}%`
  }
}

async function loadZoomLevel() {
  try {
    const result = await window.aaa.getZoomLevel()
    updateZoomDisplay(result.zoom || 1.0)
  } catch (err) {
    console.error("Failed to load zoom level:", err)
    const zoomDisplay = document.getElementById("zoom-level-display")
    if (zoomDisplay) {
      zoomDisplay.textContent = "Unknown"
    }
  }
}

async function fetchItemNames() {
  if (itemSearchLoading) return itemSearchCache
  if (itemSearchCache) return itemSearchCache

  itemSearchLoading = true
  itemSearchStatus.textContent = "Loading item names…"
  const region = state.megaData?.WOW_REGION || "EU"
  try {
    const resp = await fetchWithTimeout(
      "https://api.saddlebagexchange.com/api/wow/megaitemnames",
      {
        method: "POST",
        headers: saddlebagFetchHeaders({
          "Content-Type": "application/json",
          Accept: "application/json",
        }),
        body: JSON.stringify({
          discord_consent: WOW_DISCORD_CONSENT,
          region,
          discount: 1,
        }),
      },
      30000
    )
    const data = await resp.json()
    itemSearchCache = Array.isArray(data) ? data : []
    itemNameMap = {}
    itemSearchCache.forEach((row) => {
      if (row?.itemID && row?.itemName) {
        itemNameMap[String(row.itemID)] = row.itemName
      }
    })
    itemSearchStatus.textContent = `Loaded ${itemSearchCache.length} entries for ${region}`
    updateSuggestions(itemSearchInput, itemSearchSuggest, itemSearchCache)
    updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, itemSearchCache)
  } catch (err) {
    console.error("Item search fetch failed", err)
    itemSearchStatus.textContent = "Failed to load items (check connection)"
    itemSearchCache = []
  } finally {
    itemSearchLoading = false
  }
  return itemSearchCache
}

function renderItemSearchResults(results) {
  itemSearchResults.innerHTML = ""
  if (!results.length) {
    const div = document.createElement("div")
    div.className = "muted tiny"
    div.textContent = "No matches."
    itemSearchResults.appendChild(div)
    return
  }
  results.forEach((row) => {
    const div = document.createElement("div")
    div.className = "search-result"

    // Apply discount percentage to the average price
    const pct = discountPercent() / 100
    const recommendedPrice = Math.round(Number(row.desiredPrice || 0) * pct)

    const innerDiv = document.createElement("div")
    const nameDiv = document.createElement("div")
    const strong = document.createElement("strong")
    strong.textContent = row.itemName
    nameDiv.appendChild(strong)
    innerDiv.appendChild(nameDiv)

    const metaDiv = document.createElement("div")
    metaDiv.className = "meta"
    metaDiv.textContent = `ID: ${row.itemID} • Recommended: ${recommendedPrice}`
    innerDiv.appendChild(metaDiv)

    div.appendChild(innerDiv)
    const btn = document.createElement("button")
    btn.textContent = "Use"
    btn.className = "primary"
    btn.onclick = () => {
      const form = document.getElementById("item-form")
      form.id.value = row.itemID
      form.price.value = recommendedPrice
      ensureItemName(String(row.itemID), row.itemName)
      showView("items")
    }
    div.appendChild(btn)
    itemSearchResults.appendChild(div)
  })
}

async function handleItemSearch() {
  const term = (itemSearchInput.value || "").toLowerCase().trim()
  if (!term) {
    itemSearchStatus.textContent = "Enter a search term."
    return
  }
  const items = await fetchItemNames()
  if (!items.length) return
  updateSuggestions(itemSearchInput, itemSearchSuggest, items)
  const matches = items
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30)
  itemSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`
  renderItemSearchResults(matches)
}

function renderIlvlSearchResults(results) {
  ilvlSearchResults.innerHTML = ""
  if (!results.length) {
    const div = document.createElement("div")
    div.className = "muted tiny"
    div.textContent = "No matches."
    ilvlSearchResults.appendChild(div)
    return
  }
  results.forEach((row) => {
    const div = document.createElement("div")
    div.className = "search-result"

    // Apply discount percentage to the average price
    const pct = discountPercent() / 100
    const recommendedPrice = Math.round(Number(row.desiredPrice || 0) * pct)

    const innerDiv = document.createElement("div")
    const nameDiv = document.createElement("div")
    const strong = document.createElement("strong")
    strong.textContent = row.itemName
    nameDiv.appendChild(strong)
    innerDiv.appendChild(nameDiv)

    const metaDiv = document.createElement("div")
    metaDiv.className = "meta"
    metaDiv.textContent = `ID: ${row.itemID} • Recommended: ${recommendedPrice}`
    innerDiv.appendChild(metaDiv)

    div.appendChild(innerDiv)
    const btn = document.createElement("button")
    btn.textContent = "Use"
    btn.className = "primary"
    btn.onclick = () => {
      const form = document.getElementById("ilvl-form")
      let current = []
      try {
        current = parseNums(form.item_ids.value)
      } catch (err) {
        // If form has invalid data, show error and clear it, then add the new item
        showToast(
          "Form contains invalid item IDs. Clearing and adding new item.",
          "error"
        )
        form.item_ids.value = ""
      }
      if (!current.includes(Number(row.itemID))) {
        current.push(Number(row.itemID))
      }
      form.item_ids.value = current.join(", ")
      if (!form.buyout.value || Number(form.buyout.value) === 0) {
        form.buyout.value = recommendedPrice
      }
      ensureItemName(String(row.itemID), row.itemName)
      showView("ilvl")
    }
    div.appendChild(btn)
    ilvlSearchResults.appendChild(div)
  })
}

async function handleIlvlSearch() {
  const term = (ilvlSearchInput.value || "").toLowerCase().trim()
  if (!term) {
    ilvlSearchStatus.textContent = "Enter a search term."
    return
  }
  const items = await fetchItemNames()
  if (!items.length) return
  updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, items)
  const matches = items
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30)
  ilvlSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`
  renderIlvlSearchResults(matches)
}

async function fetchPetNames() {
  if (petSearchLoading) return petSearchCache
  if (petSearchCache) return petSearchCache

  petSearchLoading = true
  petIlvlSearchStatus.textContent = "Loading pets…"
  const region = state.megaData?.WOW_REGION || "EU"
  try {
    const resp = await fetchWithTimeout(
      "https://api.saddlebagexchange.com/api/wow/megaitemnames",
      {
        method: "POST",
        headers: saddlebagFetchHeaders({
          "Content-Type": "application/json",
          Accept: "application/json",
        }),
        body: JSON.stringify({
          discord_consent: WOW_DISCORD_CONSENT,
          region,
          discount: 1,
          pets: true,
        }),
      },
      30000
    )
    const data = await resp.json()
    petSearchCache = Array.isArray(data) ? data : []
    petNameMap = {}
    petSearchCache.forEach((row) => {
      if (row?.itemID && row?.itemName) {
        petNameMap[String(row.itemID)] = row.itemName
      }
    })
    petIlvlSearchStatus.textContent = `Loaded ${petSearchCache.length} pet entries for ${region}`
  } catch (err) {
    console.error("Pet search fetch failed", err)
    petIlvlSearchStatus.textContent = "Failed to load pets (check connection)"
    petSearchCache = []
  } finally {
    petSearchLoading = false
  }
  return petSearchCache
}

function renderPetSearchResults(results) {
  petIlvlSearchResults.innerHTML = ""
  if (!results.length) {
    const div = document.createElement("div")
    div.className = "muted tiny"
    div.textContent = "No matches."
    petIlvlSearchResults.appendChild(div)
    return
  }
  results.forEach((row) => {
    const div = document.createElement("div")
    div.className = "search-result"

    // Apply discount percentage to the average price
    const pct = discountPercent() / 100
    const recommendedPrice = Math.round(Number(row.desiredPrice || 0) * pct)

    const innerDiv = document.createElement("div")
    const nameDiv = document.createElement("div")
    const strong = document.createElement("strong")
    strong.textContent = row.itemName
    nameDiv.appendChild(strong)
    innerDiv.appendChild(nameDiv)

    const metaDiv = document.createElement("div")
    metaDiv.className = "meta"
    metaDiv.textContent = `ID: ${row.itemID} • Recommended: ${recommendedPrice}`
    innerDiv.appendChild(metaDiv)

    div.appendChild(innerDiv)
    const btn = document.createElement("button")
    btn.textContent = "Use"
    btn.className = "primary"
    btn.onclick = () => {
      const form = document.getElementById("pet-ilvl-form")
      form.petID.value = row.itemID
      form.price.value = recommendedPrice
      ensurePetName(String(row.itemID), row.itemName)
      showView("pet-ilvl")
    }
    div.appendChild(btn)
    petIlvlSearchResults.appendChild(div)
  })
}

async function handlePetSearch() {
  const term = (petIlvlSearchInput.value || "").toLowerCase().trim()
  if (!term) {
    petIlvlSearchStatus.textContent = "Enter a search term."
    return
  }
  const pets = await fetchPetNames()
  if (!pets.length) return
  updateSuggestions(petIlvlSearchInput, petIlvlSearchSuggest, pets)
  const matches = pets
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30)
  petIlvlSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`
  renderPetSearchResults(matches)
}

/**
 * Validate authentication token by calling the checkmegatoken API
 * @param {string} token - The authentication token to validate
 * @returns {Promise<{valid: boolean, error?: string}>}
 */
async function validateToken(token) {
  if (!token || !token.trim()) {
    return {
      valid: false,
      error: "Please provide a valid Auction Assassin token to save data!",
    }
  }

  try {
    const response = await fetchWithTimeout(
      "https://api.saddlebagexchange.com/api/wow/checkmegatoken",
      {
        method: "POST",
        headers: saddlebagFetchHeaders({
          "Content-Type": "application/json",
          Accept: "application/json",
        }),
        body: JSON.stringify({
          discord_consent: WOW_DISCORD_CONSENT,
          token: token.trim(),
        }),
      },
      30000
    )

    if (!response.ok) {
      return {
        valid: false,
        error: `Could not reach server, status code: ${response.status}`,
      }
    }

    const responseData = await response.json()

    if (!responseData || Object.keys(responseData).length === 0) {
      return {
        valid: false,
        error: "Please provide a valid Auction Assassin token to save data!",
      }
    }

    if (!("succeeded" in responseData)) {
      return {
        valid: false,
        error: "Please provide a valid Auction Assassin token to save data!",
      }
    }

    if (!responseData.succeeded) {
      return {
        valid: false,
        error:
          "Your Auction Assassin token is incorrect or expired!\n\nYou must run the bot command once every 14 days to get a new token.",
      }
    }

    return { valid: true }
  } catch (err) {
    return {
      valid: false,
      error: `Request error: ${err.message || String(err)}`,
    }
  }
}

async function saveMegaData(skipValidation = false) {
  const data = readMegaForm()

  if (!skipValidation) {
    const discordOn = Boolean(data.DISCORD_ALERTS_ENABLED)
    const inAppOn = Boolean(data.IN_APP_ALERTS_ENABLED)
    if (!discordOn && !inAppOn) {
      showToast(
        "Enable at least one: Send alerts to Discord, or Show alerts in the app.",
        "error"
      )
      return false
    }

    const requiredApiFields = {
      WOW_CLIENT_ID: {
        value: (data.WOW_CLIENT_ID || "").trim(),
        field: megaForm.WOW_CLIENT_ID,
        label: "WoW Client ID",
      },
      WOW_CLIENT_SECRET: {
        value: (data.WOW_CLIENT_SECRET || "").trim(),
        field: megaForm.WOW_CLIENT_SECRET,
        label: "WoW Client Secret",
      },
    }

    for (const { value, field, label } of Object.values(requiredApiFields)) {
      if (!value) {
        const errorMsg = `${label} cannot be empty.`
        showToast(errorMsg, "error")
        field?.focus()
        return false
      }
      if (value.length < 20) {
        const errorMsg = `${label} value is invalid. Contact the devs on discord.`
        showToast(errorMsg, "error")
        field?.focus()
        return false
      }
    }

    if (discordOn) {
      const wh = (data.MEGA_WEBHOOK_URL || "").trim()
      if (!wh) {
        showToast(
          "Discord Webhook URL cannot be empty when Discord alerts are enabled.",
          "error"
        )
        megaForm.MEGA_WEBHOOK_URL?.focus()
        return false
      }
      if (wh.length < 20) {
        const errorMsg =
          "Discord Webhook URL value is invalid. Contact the devs on discord."
        showToast(errorMsg, "error")
        megaForm.MEGA_WEBHOOK_URL?.focus()
        return false
      }
    }

    // Validate that Client ID and Secret are not the same
    if (
      requiredApiFields.WOW_CLIENT_ID.value ===
      requiredApiFields.WOW_CLIENT_SECRET.value
    ) {
      const errorMsg =
        "Client ID and Secret cannot be the same value. Read the wiki:\n\nhttps://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Installation-Guide#4-go-to-httpsdevelopbattlenetaccessclients-and-create-a-client-get-the-blizzard-oauth-client-and-secret-ids--you-will-use-these-values-for-the-wow_client_id-and-wow_client_secret-later-on"
      showToast(errorMsg, "error")
      megaForm.WOW_CLIENT_SECRET.focus()
      return false
    }

    // Validate WOW_REGION
    const validRegions = [
      "EU",
      "NA",
      "EUCLASSIC",
      "NACLASSIC",
      "NASODCLASSIC",
      "EUSODCLASSIC",
    ]
    const region = (data.WOW_REGION || "").trim()
    if (!validRegions.includes(region)) {
      const errorMsg = `WOW region must be either 'NA', 'EU', 'NACLASSIC', 'EUCLASSIC', 'EUSODCLASSIC' or 'NASODCLASSIC'.`
      showToast(errorMsg, "error")
      megaForm.WOW_REGION.focus()
      return false
    }

    // Validate all integer fields
    const integerFields = {
      MEGA_THREADS: {
        value: data.MEGA_THREADS,
        field: megaForm.MEGA_THREADS,
        label: "Threads",
      },
      SCAN_TIME_MIN: {
        value: data.SCAN_TIME_MIN,
        field: megaForm.SCAN_TIME_MIN,
        label: "Scan start offset",
      },
      SCAN_TIME_MAX: {
        value: data.SCAN_TIME_MAX,
        field: megaForm.SCAN_TIME_MAX,
        label: "Scan end offset",
      },
      DISCOUNT_PERCENT: {
        value: data.DISCOUNT_PERCENT,
        field: megaForm.DISCOUNT_PERCENT,
        label: "Discount vs Average",
      },
      TOKEN_PRICE: {
        value: data.TOKEN_PRICE,
        field: megaForm.TOKEN_PRICE,
        label: "Token alert min price",
      },
      MAX_IN_APP_ALERTS: {
        value: data.MAX_IN_APP_ALERTS,
        field: megaForm.MAX_IN_APP_ALERTS,
        label: "Max in-app alerts",
      },
      ALERT_SOUND_VOLUME: {
        value: data.ALERT_SOUND_VOLUME,
        field: megaForm.ALERT_SOUND_VOLUME,
        label: "Alert sound volume",
      },
    }

    for (const [key, { value, field, label }] of Object.entries(
      integerFields
    )) {
      if (value === "" || value === null || value === undefined) {
        const errorMsg = `${label} is required and must be an integer.`
        showToast(errorMsg, "error")
        field?.focus()
        return false
      }

      const numValue = Number(value)
      if (Number.isNaN(numValue) || !Number.isInteger(numValue)) {
        const errorMsg = `${label} should be an integer.`
        showToast(errorMsg, "error")
        field?.focus()
        return false
      }
    }

    // Validate discount percent range (1-99)
    const discount = Number(data.DISCOUNT_PERCENT)
    if (!(1 <= discount && discount <= 99)) {
      const errorMsg = "Discount vs Average must be between 1 and 99."
      showToast(errorMsg, "error")
      megaForm.DISCOUNT_PERCENT.focus()
      return false
    }

    const maxInApp = Number(data.MAX_IN_APP_ALERTS)
    if (maxInApp < 1 || maxInApp > MAX_IN_APP_ALERTS_HARD_CAP) {
      showToast(
        `Max in-app alerts must be an integer from 1 to ${MAX_IN_APP_ALERTS_HARD_CAP}.`,
        "error"
      )
      megaForm.MAX_IN_APP_ALERTS?.focus()
      return false
    }

    const soundVolume = Number(data.ALERT_SOUND_VOLUME)
    if (soundVolume < 1 || soundVolume > 100) {
      showToast("Alert sound volume must be an integer from 1 to 100.", "error")
      megaForm.ALERT_SOUND_VOLUME?.focus()
      return false
    }

    // Validate authentication token
    const token = data.AUTHENTICATION_TOKEN || ""
    const tokenValidation = await validateToken(token)
    if (!tokenValidation.valid) {
      showToast(tokenValidation.error || "Invalid token", "error")
      megaForm.AUTHENTICATION_TOKEN.focus()
      return false
    }
  }

  state.megaData = await window.aaa.saveMegaData(data)
  renderMegaForm(state.megaData)
  trimAlertEmbedHistoryToLimit()
  if (!skipValidation) {
    showToast("Settings saved successfully!", "success", 2000)
  }
  return true
}

async function removeItem(id) {
  delete state.desiredItems[id]
  state.desiredItems = await window.aaa.saveItems(state.desiredItems)
  renderItemList()
}

async function removeIlvlRule(idx) {
  state.ilvlList.splice(idx, 1)
  state.ilvlList = await window.aaa.saveIlvl(state.ilvlList)
  renderIlvlRules()
}

async function removePetIlvlRule(idx) {
  state.petIlvlList.splice(idx, 1)
  state.petIlvlList = await window.aaa.savePetIlvl(state.petIlvlList)
  renderPetIlvlRules()
}

// Event wiring
document.getElementById("item-form").addEventListener("submit", async (e) => {
  e.preventDefault()
  const form = e.target
  const id = form.id.value.trim()
  const price = Number(form.price.value)

  // Validation
  if (!id || form.price.value === "") {
    const errorMsg = "All fields are required."
    showToast(errorMsg, "error")
    form.id.focus()
    return
  }

  if (Number.isNaN(price)) {
    const errorMsg = "Item ID and Price should be numbers."
    showToast(errorMsg, "error")
    form.price.focus()
    return
  }

  const itemIdInt = Number(id)
  if (!(1 <= itemIdInt && itemIdInt <= 500000)) {
    const errorMsg = "Item ID must be between 1 and 500000."
    showToast(errorMsg, "error")
    form.id.focus()
    return
  }

  if (!(0 <= price && price <= 10000000)) {
    const errorMsg = "Price must be between 0 and 10 million."
    showToast(errorMsg, "error")
    form.price.focus()
    return
  }

  state.desiredItems[id] = price
  // try to keep name map
  ensureItemName(id)
  state.desiredItems = await window.aaa.saveItems(state.desiredItems)
  renderItemList()
  form.reset()
  showToast("Item saved successfully!", "success", 2000)
})

document.getElementById("ilvl-form").addEventListener("submit", async (e) => {
  e.preventDefault()
  const form = e.target

  // Validation
  const ilvlStr = form.ilvl.value.trim()
  const maxIlvlStr = form.max_ilvl.value.trim()
  const buyoutStr = form.buyout.value.trim()

  if (!ilvlStr || !buyoutStr) {
    const errorMsg = "Both ilvl and buyout fields are required."
    showToast(errorMsg, "error")
    form.ilvl.focus()
    return
  }

  const ilvl = Number(ilvlStr)
  const maxIlvl = Number(maxIlvlStr) || 10000
  const buyout = Number(buyoutStr)

  if (Number.isNaN(ilvl) || Number.isNaN(maxIlvl) || Number.isNaN(buyout)) {
    const errorMsg =
      "Min Ilvl, Max Ilvl, and price should be numbers. No decimals."
    showToast(errorMsg, "error")
    form.ilvl.focus()
    return
  }

  if (!(1 <= ilvl && ilvl <= 999)) {
    const errorMsg = "Ilvl must be between 1 and 999."
    showToast(errorMsg, "error")
    form.ilvl.focus()
    return
  }

  if (!(ilvl <= maxIlvl && maxIlvl <= 10000)) {
    const errorMsg = "Max Ilvl must be between Ilvl and a max of 10000."
    showToast(errorMsg, "error")
    form.max_ilvl.focus()
    return
  }

  if (!(1 <= buyout && buyout <= 10000000)) {
    const errorMsg = "Price must be between 1 and 10 million."
    showToast(errorMsg, "error")
    form.buyout.focus()
    return
  }

  // Validate item IDs if provided
  const itemIdsText = form.item_ids.value.trim()
  let itemIds = []
  if (itemIdsText) {
    try {
      itemIds = parseNums(itemIdsText)
      if (!itemIds.every((id) => 1 <= id && id <= 500000)) {
        const errorMsg = "All item IDs should be between 1 and 500,000."
        showToast(errorMsg, "error")
        form.item_ids.focus()
        return
      }
    } catch (err) {
      // parseNums now throws with a descriptive error message
      showToast(err.message || "Item IDs should be numbers.", "error")
      form.item_ids.focus()
      return
    }
  }

  // Validate player levels
  const minLevel = Number(form.required_min_lvl.value) || 1
  const maxLevel = Number(form.required_max_lvl.value) || 1000

  if (!(1 <= minLevel && minLevel <= 999)) {
    const errorMsg = "Min level must be between 1 and 999."
    showToast(errorMsg, "error")
    form.required_min_lvl.focus()
    return
  }

  if (!(1 <= maxLevel && maxLevel <= 999)) {
    const errorMsg = "Max level must be between 1 and 999."
    showToast(errorMsg, "error")
    form.required_max_lvl.focus()
    return
  }

  if (maxLevel < minLevel) {
    const errorMsg = "Max level must be greater than or equal to Min level."
    showToast(errorMsg, "error")
    form.required_max_lvl.focus()
    return
  }

  // Validate bonus_lists if provided
  let bonusLists = []
  const bonusListsText = form.bonus_lists.value.trim()
  if (bonusListsText) {
    try {
      bonusLists = parseNums(bonusListsText)
    } catch (err) {
      const errorMsg = "Bonus lists should be comma-separated numbers."
      showToast(errorMsg, "error")
      form.bonus_lists.focus()
      return
    }
  }

  const rule = {
    ilvl: ilvl,
    max_ilvl: maxIlvl,
    buyout: buyout,
    sockets: form.sockets.checked,
    speed: form.speed.checked,
    leech: form.leech.checked,
    avoidance: form.avoidance.checked,
    item_ids: itemIds,
    bonus_lists: bonusLists,
    required_min_lvl: minLevel,
    required_max_lvl: maxLevel,
  }

  if (
    editingIlvlIndex !== null &&
    editingIlvlIndex >= 0 &&
    editingIlvlIndex < state.ilvlList.length
  ) {
    state.ilvlList[editingIlvlIndex] = rule
    editingIlvlIndex = null
  } else {
    state.ilvlList.push(rule)
  }
  state.ilvlList = await window.aaa.saveIlvl(state.ilvlList)
  renderIlvlRules()
  clearIlvlForm()
  appendLog("Ilvl rule saved successfully\n")
  showToast("Rule saved successfully!", "success", 2000)
})

document
  .getElementById("pet-ilvl-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault()
    const form = e.target

    // Validation
    const petIdStr = form.petID.value.trim()
    const priceStr = form.price.value.trim()
    const minLevelStr = form.minLevel.value.trim()

    if (!petIdStr || !priceStr || !minLevelStr) {
      const errorMsg = "Please set a pet level (1-25)"
      showToast(errorMsg, "error")
      form.minLevel.focus()
      return
    }

    const petID = Number(petIdStr)
    const price = Number(priceStr)
    const minLevel = Number(minLevelStr)
    // Get minQuality from dropdown (already an integer string)
    const minQuality =
      form.minQuality.value === "" ? -1 : Number(form.minQuality.value)

    if (
      Number.isNaN(petID) ||
      Number.isNaN(price) ||
      Number.isNaN(minLevel) ||
      Number.isNaN(minQuality)
    ) {
      const errorMsg = "Pet ID, Price, and Min Level should be numbers."
      showToast(errorMsg, "error")
      form.petID.focus()
      return
    }

    if (!(1 <= petID && petID <= 10000)) {
      const errorMsg = "Pet ID must be between 1 and 10000"
      showToast(errorMsg, "error")
      form.petID.focus()
      return
    }

    if (price <= 0) {
      const errorMsg = "Price must be greater than 0"
      showToast(errorMsg, "error")
      form.price.focus()
      return
    }

    if (!(1 <= minLevel && minLevel <= 25)) {
      const errorMsg = "Minimum level must be between 1 and 25"
      showToast(errorMsg, "error")
      form.minLevel.focus()
      return
    }

    if (!(-1 <= minQuality && minQuality <= 3)) {
      const errorMsg = "Minimum quality must be between -1 and 3"
      showToast(errorMsg, "error")
      form.minQuality.focus()
      return
    }

    // Get excluded breeds from checkboxes
    const excludeBreeds = readExcludeBreedsArray()

    const rule = {
      petID: petID,
      price: price,
      minLevel: minLevel,
      minQuality: minQuality,
      excludeBreeds: excludeBreeds,
    }
    if (
      editingPetIlvlIndex !== null &&
      editingPetIlvlIndex >= 0 &&
      editingPetIlvlIndex < state.petIlvlList.length
    ) {
      state.petIlvlList[editingPetIlvlIndex] = rule
      editingPetIlvlIndex = null
    } else {
      state.petIlvlList.push(rule)
    }
    ensurePetName(rule.petID)
    state.petIlvlList = await window.aaa.savePetIlvl(state.petIlvlList)
    renderPetIlvlRules()
    clearPetIlvlForm()
    showToast("Pet rule saved successfully!", "success", 2000)
  })

// Add event listeners for "New Item" buttons
document.getElementById("new-ilvl-btn")?.addEventListener("click", () => {
  clearIlvlForm()
})

document.getElementById("new-pet-ilvl-btn")?.addEventListener("click", () => {
  clearPetIlvlForm()
})

// Restore backup button handlers
restoreBackupBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.listBackups("megaData")
    if (result.error) {
      appendLog(`Failed to list backups: ${result.error}\n`)
      showToast(`Failed to list backups: ${result.error}`, "error", 5000)
      return
    }
    const backups = result.backups || []
    showBackupModal("Select Backup to Restore", backups, async (backup) => {
      if (
        confirm(
          `Restore backup from ${backup.displayDate}? This will replace your current settings.`
        )
      ) {
        try {
          const restoreResult = await window.aaa.restoreBackup(
            "megaData",
            backup.filename
          )
          if (restoreResult.error) {
            appendLog(`Failed to restore backup: ${restoreResult.error}\n`)
            showToast(
              `Failed to restore backup: ${restoreResult.error}`,
              "error",
              5000
            )
          } else {
            await loadState()
            flashButton(restoreBackupBtn, "Restored!")
            showToast("Backup restored successfully", "success", 3000)
          }
        } catch (err) {
          appendLog(`Restore error: ${err}\n`)
          showToast(`Restore error: ${err.message}`, "error", 5000)
        }
      }
    })
  } catch (err) {
    appendLog(`Failed to load backups: ${err}\n`)
    showToast(`Failed to load backups: ${err.message}`, "error", 5000)
  }
})

restoreBackupItemsBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.listBackups("desiredItems")
    if (result.error) {
      appendLog(`Failed to list backups: ${result.error}\n`)
      showToast(`Failed to list backups: ${result.error}`, "error", 5000)
      return
    }
    const backups = result.backups || []
    showBackupModal("Select Backup to Restore", backups, async (backup) => {
      if (
        confirm(
          `Restore backup from ${backup.displayDate}? This will replace your current items.`
        )
      ) {
        try {
          const restoreResult = await window.aaa.restoreBackup(
            "desiredItems",
            backup.filename
          )
          if (restoreResult.error) {
            appendLog(`Failed to restore backup: ${restoreResult.error}\n`)
            showToast(
              `Failed to restore backup: ${restoreResult.error}`,
              "error",
              5000
            )
          } else {
            await loadState()
            flashButton(restoreBackupItemsBtn, "Restored!")
            showToast("Backup restored successfully", "success", 3000)
          }
        } catch (err) {
          appendLog(`Restore error: ${err}\n`)
          showToast(`Restore error: ${err.message}`, "error", 5000)
        }
      }
    })
  } catch (err) {
    appendLog(`Failed to load backups: ${err}\n`)
    showToast(`Failed to load backups: ${err.message}`, "error", 5000)
  }
})

restoreBackupIlvlBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.listBackups("ilvlList")
    if (result.error) {
      appendLog(`Failed to list backups: ${result.error}\n`)
      showToast(`Failed to list backups: ${result.error}`, "error", 5000)
      return
    }
    const backups = result.backups || []
    showBackupModal("Select Backup to Restore", backups, async (backup) => {
      if (
        confirm(
          `Restore backup from ${backup.displayDate}? This will replace your current ilvl rules.`
        )
      ) {
        try {
          const restoreResult = await window.aaa.restoreBackup(
            "ilvlList",
            backup.filename
          )
          if (restoreResult.error) {
            appendLog(`Failed to restore backup: ${restoreResult.error}\n`)
            showToast(
              `Failed to restore backup: ${restoreResult.error}`,
              "error",
              5000
            )
          } else {
            await loadState()
            flashButton(restoreBackupIlvlBtn, "Restored!")
            showToast("Backup restored successfully", "success", 3000)
          }
        } catch (err) {
          appendLog(`Restore error: ${err}\n`)
          showToast(`Restore error: ${err.message}`, "error", 5000)
        }
      }
    })
  } catch (err) {
    appendLog(`Failed to load backups: ${err}\n`)
    showToast(`Failed to load backups: ${err.message}`, "error", 5000)
  }
})

restoreBackupPetsBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.listBackups("petIlvlList")
    if (result.error) {
      appendLog(`Failed to list backups: ${result.error}\n`)
      showToast(`Failed to list backups: ${result.error}`, "error", 5000)
      return
    }
    const backups = result.backups || []
    showBackupModal("Select Backup to Restore", backups, async (backup) => {
      if (
        confirm(
          `Restore backup from ${backup.displayDate}? This will replace your current pet rules.`
        )
      ) {
        try {
          const restoreResult = await window.aaa.restoreBackup(
            "petIlvlList",
            backup.filename
          )
          if (restoreResult.error) {
            appendLog(`Failed to restore backup: ${restoreResult.error}\n`)
            showToast(
              `Failed to restore backup: ${restoreResult.error}`,
              "error",
              5000
            )
          } else {
            await loadState()
            flashButton(restoreBackupPetsBtn, "Restored!")
            showToast("Backup restored successfully", "success", 3000)
          }
        } catch (err) {
          appendLog(`Restore error: ${err}\n`)
          showToast(`Restore error: ${err.message}`, "error", 5000)
        }
      }
    })
  } catch (err) {
    appendLog(`Failed to load backups: ${err}\n`)
    showToast(`Failed to load backups: ${err.message}`, "error", 5000)
  }
})

// Reset button handlers
resetSettingsBtn?.addEventListener("click", async () => {
  if (
    confirm(
      "Reset all settings to defaults? This will clear all your current settings."
    )
  ) {
    await window.aaa.resetMegaData()
    await loadState()
    flashButton(resetSettingsBtn, "Reset!")
  }
})

resetItemsBtn?.addEventListener("click", async () => {
  if (
    confirm("Clear all items? This will remove all items from your snipe list.")
  ) {
    await window.aaa.resetItems()
    await loadState()
    flashButton(resetItemsBtn, "Reset!")
  }
})

resetIlvlBtn?.addEventListener("click", async () => {
  if (
    confirm("Clear all ilvl rules? This will remove all ilvl sniping rules.")
  ) {
    await window.aaa.resetIlvl()
    await loadState()
    flashButton(resetIlvlBtn, "Reset!")
  }
})

resetPetsBtn?.addEventListener("click", async () => {
  if (confirm("Clear all pet rules? This will remove all pet sniping rules.")) {
    await window.aaa.resetPetIlvl()
    await loadState()
    flashButton(resetPetsBtn, "Reset!")
  }
})

saveSettingsBtn.addEventListener("click", async () => {
  const saved = await saveMegaData()
  if (saved) {
    flashButton(saveSettingsBtn, "Saved ✓")
  }
})

reloadBtn.addEventListener("click", async () => {
  await loadState()
  flashButton(reloadBtn, "Reloaded ✓")
})

// Navigation history management
function updateNavigationButtons() {
  window.aaa.canGoBack().then((canBack) => {
    if (backBtn) backBtn.disabled = !canBack
  })
  window.aaa.canGoForward().then((canForward) => {
    if (forwardBtn) forwardBtn.disabled = !canForward
  })
}

backBtn?.addEventListener("click", async () => {
  await window.aaa.goBack()
  updateNavigationButtons()
})

forwardBtn?.addEventListener("click", async () => {
  await window.aaa.goForward()
  updateNavigationButtons()
})

// Update navigation buttons on navigation events
window.addEventListener("popstate", updateNavigationButtons)
// Initialize navigation buttons on startup
updateNavigationButtons()

startBtn.addEventListener("click", async () => {
  // Validate and save before starting
  const saved = await saveMegaData()
  if (!saved) {
    return // Validation failed, don't start
  }

  // Check if realm list is empty and reset it if needed
  const region = state.megaData?.WOW_REGION || "EU"
  const realms = state.realmLists[region] || {}
  const realmCount = Object.keys(realms).length

  if (realmCount === 0) {
    // Realm list is empty, reset it to default before starting
    if (!window.REALM_DATA) {
      console.error("Realm data not loaded")
      return
    }
    const defaultList = window.REALM_DATA.getRealmListByRegion(region)
    if (!defaultList) {
      console.error(`No default list for region: ${region}`)
      return
    }
    state.realmLists[region] = { ...defaultList }
    await saveRealmList(region)
    renderRealmList()
  }

  await window.aaa.runMega()
  setRunning(true)
})

stopBtn.addEventListener("click", async () => {
  await window.aaa.stopMega()
  setRunning(false)
})

itemSearchBtn.addEventListener("click", handleItemSearch)
itemSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault()
    handleItemSearch()
  }
})

ilvlSearchBtn.addEventListener("click", handleIlvlSearch)
ilvlSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault()
    handleIlvlSearch()
  }
})

petIlvlSearchBtn.addEventListener("click", handlePetSearch)
petIlvlSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault()
    handlePetSearch()
  }
})

itemSearchInput.addEventListener("input", async () => {
  if (!itemSearchCache) await fetchItemNames()
  updateSuggestions(itemSearchInput, itemSearchSuggest, itemSearchCache || [])
})
ilvlSearchInput.addEventListener("input", async () => {
  if (!itemSearchCache) await fetchItemNames()
  updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, itemSearchCache || [])
})
petIlvlSearchInput.addEventListener("input", async () => {
  if (!petSearchCache) await fetchPetNames()
  updateSuggestions(
    petIlvlSearchInput,
    petIlvlSearchSuggest,
    petSearchCache || []
  )
})

itemSearchInput.addEventListener("focus", () => fetchItemNames())
ilvlSearchInput.addEventListener("focus", () => fetchItemNames())
petIlvlSearchInput.addEventListener("focus", () => fetchPetNames())

// Realm list functions
function renderRealmList() {
  if (!realmList) return
  const region = realmRegionSelect?.value || "EU"
  const realms = state.realmLists[region] || {}
  const filter = realmFilterInput?.value?.toLowerCase() || ""

  realmList.innerHTML = ""

  const entries = Object.entries(realms)
    .filter(([name, id]) => {
      if (!filter) return true
      return name.toLowerCase().includes(filter) || String(id).includes(filter)
    })
    .sort(([a], [b]) => a.localeCompare(b))

  for (const [name, id] of entries) {
    const li = document.createElement("li")
    const nameDiv = document.createElement("div")
    nameDiv.textContent = `Name: ${escapeHtml(name)}; ID: ${id};`
    li.appendChild(nameDiv)

    const removeBtn = document.createElement("button")
    removeBtn.className = "remove-btn"
    removeBtn.setAttribute("data-name", escapeHtml(name))
    removeBtn.setAttribute("data-id", String(id))
    removeBtn.textContent = "Remove"
    li.appendChild(removeBtn)

    li.onclick = (e) => {
      if (e.target.classList.contains("remove-btn")) return
      realmNameInput.value = name
      realmIdInput.value = id
    }
    removeBtn.onclick = (e) => {
      e.stopPropagation()
      removeRealm(name, id)
    }
    realmList.appendChild(li)
  }
}

async function loadRealmLists() {
  try {
    const lists = await window.aaa.loadRealmLists()
    state.realmLists = lists || {}
    renderRealmList()
  } catch (err) {
    console.error("Failed to load realm lists:", err)
  }
}

async function saveRealmList(region) {
  try {
    const realms = state.realmLists[region] || {}
    await window.aaa.saveRealmList(region, realms)
  } catch (err) {
    console.error("Failed to save realm list:", err)
  }
}

async function addRealm(region, name, id) {
  if (!name || !id) return
  if (!state.realmLists[region]) {
    state.realmLists[region] = {}
  }
  state.realmLists[region][name] = Number(id)
  await saveRealmList(region)
  renderRealmList()
  realmNameInput.value = ""
  realmIdInput.value = ""
}

async function removeRealm(name, id) {
  const region = realmRegionSelect?.value || "EU"
  if (!state.realmLists[region]) return
  delete state.realmLists[region][name]
  await saveRealmList(region)
  renderRealmList()
}

async function removeAllRealms() {
  const region = realmRegionSelect?.value || "EU"
  state.realmLists[region] = {}
  await saveRealmList(region)
  renderRealmList()
}

async function resetRealmList() {
  const region = realmRegionSelect?.value || "EU"
  if (!window.REALM_DATA) {
    console.error("Realm data not loaded")
    return
  }
  const defaultList = window.REALM_DATA.getRealmListByRegion(region)
  if (!defaultList) {
    console.error(`No default list for region: ${region}`)
    return
  }
  state.realmLists[region] = { ...defaultList }
  await saveRealmList(region)
  renderRealmList()
}

realmForm?.addEventListener("submit", async (e) => {
  e.preventDefault()
  const formData = new FormData(e.target)
  const region = formData.get("region") || "EU"
  const name = formData.get("realmName")?.trim()
  const id = formData.get("realmId")
  if (name && id) {
    await addRealm(region, name, Number(id))
  }
})

realmRegionSelect?.addEventListener("change", () => {
  renderRealmList()
})

realmFilterInput?.addEventListener("input", () => {
  renderRealmList()
})

resetRealmBtn?.addEventListener("click", () => {
  if (confirm(`Reset realm list for ${realmRegionSelect?.value || "EU"}?`)) {
    resetRealmList()
  }
})

removeRealmBtn?.addEventListener("click", () => {
  const name = realmNameInput.value.trim()
  const id = realmIdInput.value
  if (name && id) {
    removeRealm(name, Number(id))
  }
})

removeAllRealmsBtn?.addEventListener("click", () => {
  const region = realmRegionSelect?.value || "EU"
  if (
    confirm(
      `Remove all realms from ${region}? This will empty the entire realm list.`
    )
  ) {
    removeAllRealms()
  }
})

importConfigBtn?.addEventListener("click", () =>
  handleImport("megaData", importConfigBtn)
)
exportConfigBtn?.addEventListener("click", () =>
  handleExport("megaData", exportConfigBtn)
)
pasteConfigBtn?.addEventListener("click", () => handlePasteAAA("megaData"))
copyConfigBtn?.addEventListener("click", () =>
  handleCopyAAA("megaData", copyConfigBtn)
)
importItemsBtn?.addEventListener("click", () =>
  handleImport("desiredItems", importItemsBtn)
)
exportItemsBtn?.addEventListener("click", () =>
  handleExport("desiredItems", exportItemsBtn)
)
pasteItemsBtn?.addEventListener("click", () =>
  handlePasteAAA("desiredItems", pasteItemsBtn)
)
copyItemsBtn?.addEventListener("click", () =>
  handleCopyAAA("desiredItems", copyItemsBtn)
)
pastePBSItemsBtn?.addEventListener("click", () =>
  handlePastePBSItems(pastePBSItemsBtn)
)
copyPBSItemsBtn?.addEventListener("click", () =>
  handleCopyPBSItems(copyPBSItemsBtn)
)
itemFilterInput?.addEventListener("input", () => renderItemList())
ilvlFilterInput?.addEventListener("input", () => renderIlvlRules())
petIlvlFilterInput?.addEventListener("input", () => renderPetIlvlRules())
importIlvlBtn?.addEventListener("click", () =>
  handleImport("ilvlList", importIlvlBtn)
)
exportIlvlBtn?.addEventListener("click", () =>
  handleExport("ilvlList", exportIlvlBtn)
)
pasteIlvlBtn?.addEventListener("click", () =>
  handlePasteAAA("ilvlList", pasteIlvlBtn)
)
copyIlvlBtn?.addEventListener("click", () =>
  handleCopyAAA("ilvlList", copyIlvlBtn)
)
pastePBSIlvlBtn?.addEventListener("click", () =>
  handlePastePBSIlvl(pastePBSIlvlBtn)
)
copyPBSIlvlBtn?.addEventListener("click", () =>
  handleCopyPBSIlvl(copyPBSIlvlBtn)
)
importPetIlvlBtn?.addEventListener("click", () =>
  handleImport("petIlvlList", importPetIlvlBtn)
)
exportPetIlvlBtn?.addEventListener("click", () =>
  handleExport("petIlvlList", exportPetIlvlBtn)
)
pastePetIlvlBtn?.addEventListener("click", () =>
  handlePasteAAA("petIlvlList", pastePetIlvlBtn)
)
const selectDataDirBtn = getElement("select-data-dir-btn")
const resetDataDirBtn = getElement("reset-data-dir-btn")

selectDataDirBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.selectDataDir()
    if (result.canceled) return

    if (result.success) {
      await loadDataDir()
      showToast(
        `Data directory set to: ${result.dataDir}\nPlease restart the app for changes to take effect.`,
        "success",
        5000
      )
    } else {
      showToast(`Failed to set data directory: ${result.error}`, "error")
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error")
  }
})

resetDataDirBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.setCustomDataDir(null)
    if (result.success) {
      await loadDataDir()
      showToast(
        `Data directory reset to default.\nPlease restart the app for changes to take effect.`,
        "success",
        5000
      )
    } else {
      showToast(`Failed to reset data directory: ${result.error}`, "error")
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error")
  }
})

alertSoundVolumeSlider?.addEventListener("input", () => {
  if (!alertSoundVolumeInput || !alertSoundVolumeSlider) return
  alertSoundVolumeInput.value = alertSoundVolumeSlider.value
})

alertSoundVolumeInput?.addEventListener("input", () => {
  if (!alertSoundVolumeSlider || !alertSoundVolumeInput) return
  const v = normalizeAlertSoundVolumeInput(alertSoundVolumeInput.value)
  alertSoundVolumeInput.value = String(v)
  alertSoundVolumeSlider.value = String(v)
})

alertSoundBrowseBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.selectAlertSoundFile()
    if (result?.canceled || !result?.filePath) return
    if (alertSoundFileInput) {
      alertSoundFileInput.value = result.filePath
    }
  } catch (err) {
    showToast(`Error selecting sound file: ${err.message}`, "error")
  }
})

alertSoundClearBtn?.addEventListener("click", () => {
  if (alertSoundFileInput) {
    alertSoundFileInput.value = ""
  }
})

copyPetIlvlBtn?.addEventListener("click", () =>
  handleCopyAAA("petIlvlList", copyPetIlvlBtn)
)
pastePBSPetIlvlBtn?.addEventListener("click", () =>
  handlePastePBSPetIlvl(pastePBSPetIlvlBtn)
)
copyPBSPetIlvlBtn?.addEventListener("click", () =>
  handleCopyPBSPetIlvl(copyPBSPetIlvlBtn)
)

window.aaa.onMegaLog((line) => appendLog(line))
window.aaa.onMegaAlertEmbed((embed) => {
  if (embed && typeof embed === "object") {
    if (Boolean(state.megaData?.IN_APP_ALERTS_ENABLED)) {
      appendAlertEmbed(embed)
    }
    playAlertSound()
  }
})
window.aaa.onMegaExit((code) => {
  appendLog(`\nProcess exited with code ${code}\n`)
  setRunning(false)
})

// Listen for zoom changes
window.aaa.onZoomChanged((zoomFactor) => {
  updateZoomDisplay(zoomFactor)
})

// Listen for reload state requests (e.g., after data directory changes)
window.aaa.onReloadState(async () => {
  await loadState()
})

// Zoom button handlers
const zoomInBtn = getElement("zoom-in-btn")
const zoomOutBtn = getElement("zoom-out-btn")

zoomInBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.getZoomLevel()
    const currentZoom = result.zoom || 1.0
    const newZoom = Math.min(currentZoom + 0.1, 3.0) // Max 300%
    await window.aaa.setZoomLevel(newZoom)
    updateZoomDisplay(newZoom)
  } catch (err) {
    console.error("Failed to zoom in:", err)
  }
})

zoomOutBtn?.addEventListener("click", async () => {
  try {
    const result = await window.aaa.getZoomLevel()
    const currentZoom = result.zoom || 1.0
    const newZoom = Math.max(currentZoom - 0.1, 0.25) // Min 25%
    await window.aaa.setZoomLevel(newZoom)
    updateZoomDisplay(newZoom)
  } catch (err) {
    console.error("Failed to zoom out:", err)
  }
})

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => showView(btn.dataset.viewTarget))
})

const clearAlertsBtn = getElement("clear-alerts-btn")
clearAlertsBtn?.addEventListener("click", () => {
  alertEmbedHistory.length = 0
  redrawAlertsStream()
})

getElement("alerts-download-csv-btn")?.addEventListener("click", () => {
  downloadUnifiedSheetAsCsv()
})

getElement("alerts-filter-hour-btn")?.addEventListener("click", () => {
  applyCurrentHourTimeFilter()
})

for (const m of ALERT_VIEW_MODES) {
  document.getElementById(`alerts-view-${m}`)?.addEventListener("click", () => {
    setAlertsViewMode(m)
  })
}

window.addEventListener("DOMContentLoaded", async () => {
  refreshAlertsViewToggleButtons()
  await loadState()
  showView("home")
  updateNavigationButtons()
  checkForUpdates()
  setupSensitiveFieldToggles()
  setupExtraAlertsDropdown()
  setupExcludeBreedsDropdown()
})

/**
 * Setup click handlers for extra alerts dropdown
 */
function setupExtraAlertsDropdown() {
  const trigger = document.getElementById("extra-alerts-trigger")
  const dropdown = document.getElementById("extra-alerts-dropdown")
  if (!trigger || !dropdown) return

  // Toggle dropdown on button click
  trigger.addEventListener("click", (e) => {
    e.stopPropagation()
    const isOpen = dropdown.style.display !== "none"
    dropdown.style.display = isOpen ? "none" : "block"
  })

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = "none"
    }
  })
}

/**
 * Render exclude breeds checkboxes (only the recommended breed IDs)
 */
function renderExcludeBreeds(excludeBreedsValue) {
  const list = document.getElementById("exclude-breeds-list")
  const display = document.getElementById("exclude-breeds-display")
  if (!list || !display) return

  // Only these breed IDs are available (from tooltip recommendation)
  const availableBreedIds = [2, 3, 7, 8, 9, 10, 11, 13, 17, 18, 19, 20, 21, 22]

  // Parse the comma-separated string, default to empty array if invalid
  let selectedBreeds = []
  if (excludeBreedsValue && excludeBreedsValue.trim()) {
    try {
      selectedBreeds = excludeBreedsValue
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !isNaN(n) && availableBreedIds.includes(n))
    } catch {
      selectedBreeds = []
    }
  }

  // Update display text
  if (selectedBreeds.length === 0) {
    display.textContent = "Select breed IDs..."
  } else {
    const sorted = [...selectedBreeds].sort((a, b) => a - b)
    if (sorted.length <= 5) {
      display.textContent = sorted.join(", ")
    } else {
      display.textContent = `${sorted.length} breeds selected`
    }
  }

  // Clear list
  list.innerHTML = ""

  // Create checkboxes only for available breed IDs
  for (const breedId of availableBreedIds) {
    const label = document.createElement("label")
    label.className = "exclude-breed-checkbox"

    const checkbox = document.createElement("input")
    checkbox.type = "checkbox"
    checkbox.value = breedId
    checkbox.name = `exclude_breed_${breedId}`
    checkbox.checked = selectedBreeds.includes(breedId)
    checkbox.addEventListener("change", () => {
      updateExcludeBreedsDisplay()
    })

    const span = document.createElement("span")
    span.textContent = breedId

    label.appendChild(checkbox)
    label.appendChild(span)
    list.appendChild(label)
  }
}

/**
 * Update the display text for exclude breeds dropdown
 */
function updateExcludeBreedsDisplay() {
  const display = document.getElementById("exclude-breeds-display")
  if (!display) return

  const selectedBreeds = readExcludeBreedsArray()
  if (selectedBreeds.length === 0) {
    display.textContent = "Select breed IDs..."
  } else {
    const sorted = [...selectedBreeds].sort((a, b) => a - b)
    if (sorted.length <= 5) {
      display.textContent = sorted.join(", ")
    } else {
      display.textContent = `${sorted.length} breeds selected`
    }
  }
}

/**
 * Read exclude breeds checkboxes and return as array of numbers
 */
function readExcludeBreedsArray() {
  const list = document.getElementById("exclude-breeds-list")
  if (!list) return []

  // Only these breed IDs are available (from tooltip recommendation)
  const availableBreedIds = [2, 3, 7, 8, 9, 10, 11, 13, 17, 18, 19, 20, 21, 22]

  const selectedBreeds = []
  const checkboxes = list.querySelectorAll('input[type="checkbox"]:checked')
  for (const checkbox of checkboxes) {
    const value = Number(checkbox.value)
    if (!isNaN(value) && availableBreedIds.includes(value)) {
      selectedBreeds.push(value)
    }
  }

  return selectedBreeds
}

/**
 * Setup click handlers for exclude breeds dropdown
 */
function setupExcludeBreedsDropdown() {
  const trigger = document.getElementById("exclude-breeds-trigger")
  const dropdown = document.getElementById("exclude-breeds-dropdown")
  if (!trigger || !dropdown) return

  // Toggle dropdown on button click
  trigger.addEventListener("click", (e) => {
    e.stopPropagation()
    const isOpen = dropdown.style.display !== "none"
    dropdown.style.display = isOpen ? "none" : "block"
  })

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = "none"
    }
  })
}

/**
 * Setup show/hide toggles for sensitive input fields
 */
function setupSensitiveFieldToggles() {
  const showButtons = document.querySelectorAll(".show-sensitive-btn")
  showButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const fieldName = btn.getAttribute("data-field")
      const input = document.querySelector(`input[name="${fieldName}"]`)
      if (!input) return

      const isPassword = input.type === "password"
      input.type = isPassword ? "text" : "password"
      btn.textContent = isPassword ? "Hide" : "Show"
      btn.title = isPassword ? "Hide value" : "Show value"
    })
  })
}

/**
 * Check for app updates and display notification
 */
async function checkForUpdates() {
  try {
    const result = await window.aaa.checkForUpdates()
    const updateNotification = document.getElementById("update-notification")
    const updateContent = document.getElementById("update-content")

    if (!updateNotification || !updateContent) return

    // Clear existing content
    updateContent.textContent = ""

    if (result.hasUpdate && result.latestVersion) {
      // Show new version available message
      const link = document.createElement("a")
      link.href =
        "https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases/latest"
      link.target = "_blank"
      link.rel = "noopener noreferrer"
      link.className = "update-link"

      const icon = document.createElement("span")
      icon.className = "update-icon"
      icon.textContent = "🆕"

      const text = document.createElement("span")
      text.className = "update-text"
      text.textContent = "New version available: "

      const version = document.createElement("span")
      version.className = "update-version"
      version.textContent = result.latestVersion

      text.appendChild(version)
      link.appendChild(icon)
      link.appendChild(text)
      updateContent.appendChild(link)

      updateNotification.style.display = "block"
      updateNotification.className = "update-notification update-available"
    } else if (!result.error) {
      // Show up to date message
      const div = document.createElement("div")
      div.className = "update-link"

      const icon = document.createElement("span")
      icon.className = "update-icon"
      icon.textContent = "✓"

      const text = document.createElement("span")
      text.className = "update-text"
      text.textContent = `You are up to date (version ${result.currentVersion})`

      div.appendChild(icon)
      div.appendChild(text)
      updateContent.appendChild(div)

      updateNotification.style.display = "block"
      updateNotification.className = "update-notification update-current"
    }
  } catch (err) {
    // Silently fail - don't show errors for update checks
    console.error("Failed to check for updates:", err)
  }
}
