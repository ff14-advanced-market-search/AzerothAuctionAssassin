const assert = require("node:assert/strict")
const { readFileSync } = require("node:fs")
const { join } = require("node:path")
const { test } = require("node:test")
const vm = require("node:vm")

const renderer = readFileSync(join(__dirname, "../node-ui/renderer.js"), "utf8")
const auctionatorList =
  "boe^Bound Serpent's Jade Eye^Restored Artifact^Footpad's Shoes^Pauldrons of the Forgotten Sacrifice^Slippers of the Hissing Cult^Ruined Pattern^Temple Delver's Mystic Helm^Cranberry Chutney^Venom Rite Mantle^Design: Revitalizing Shadowspirit Diamond^Slitherscale Girdle^Satchel of Helpful Goods^Crushing Coiler Coif^Recipe: Snapper Extreme^Worn Shortsword^Greaves of the Noxious Depths^Fanged Brute's Greatbelt"

// Representative market data; the remaining six names have no market entry.
const marketItems = [
  [271638, "Bound Serpent's Jade Eye"],
  [47, "Footpad's Shoes"],
  [271444, "Pauldrons of the Forgotten Sacrifice"],
  [271435, "Slippers of the Hissing Cult"],
  [271438, "Temple Delver's Mystic Helm"],
  [271434, "Venom Rite Mantle"],
  [271436, "Slitherscale Girdle"],
  [271441, "Crushing Coiler Coif"],
  [25, "Worn Shortsword"],
  [271440, "Greaves of the Noxious Depths"],
  [271445, "Fanged Brute's Greatbelt"],
].map(([itemID, itemName]) => ({ itemID, itemName, desiredPrice: 1000 }))

function response(data = marketItems, status = 200) {
  return { ok: status === 200, status, json: async () => data }
}

function setup(fetch = async () => response(), saveError = null) {
  const calls = { fetches: 0, saves: [], flashes: [], toasts: [], logs: [] }
  const elements = new Map()
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, { addEventListener() {} })
    return elements.get(id)
  }
  const context = vm.createContext({
    document: { getElementById: element, querySelectorAll: () => [] },
    localStorage: { getItem: () => null },
    window: {
      addEventListener() {},
      aaa: {
        canGoBack: async () => false,
        canGoForward: async () => false,
        onMegaLog() {},
        onMegaAlertEmbed() {},
        onMegaExit() {},
        onZoomChanged() {},
        onReloadState() {},
        saveItems: async (items) => {
          if (saveError) throw saveError
          calls.saves.push({ ...items })
          return items
        },
      },
    },
    AbortController,
    setTimeout,
    clearTimeout,
    console: { error() {} },
    fetch: (...args) => {
      calls.fetches++
      return fetch(...args)
    },
    calls,
  })
  // Load the actual renderer; do not invoke DOMContentLoaded or Electron itself.
  vm.runInContext(renderer, context)
  vm.runInContext(
    `showPasteModal = (title, placeholder, submit) => { globalThis.submit = submit }
     loadState = async () => {}
     updateSuggestions = () => {}
     flashButton = (button, text) => calls.flashes.push(text)
     showToast = (message, type) => calls.toasts.push({ message, type })
     appendLog = (message) => calls.logs.push(message)
     state.desiredItems = { "999": 42 }
     state.megaData = { DISCOUNT_PERCENT: 20 }`,
    context
  )
  return {
    calls,
    loadItems: () => vm.runInContext("fetchItemNames()", context),
    importItems: async (text = auctionatorList) => {
      await vm.runInContext("handlePastePBSItems({})", context)
      await context.submit(text)
    },
  }
}

function assertReportedListImported(calls) {
  assert.equal(calls.saves.length, 1)
  assert.deepEqual(calls.saves[0], {
    999: 42,
    ...Object.fromEntries(marketItems.map((row) => [row.itemID, 200])),
  })
  assert.equal(calls.flashes.length, 1)
}

test("imports the reported Auctionator list into an existing item list", async () => {
  const app = setup()
  await app.importItems()
  assertReportedListImported(app.calls)
  assert.match(app.calls.toasts[0].message, /11.*6/)
})

test("import waits for item names already loading at startup", async () => {
  let finishFetch
  const app = setup(
    () =>
      new Promise((resolve) => {
        finishFetch = resolve
      })
  )
  const initialLoad = app.loadItems()
  const importing = app.importItems()
  await Promise.resolve()
  assert.equal(app.calls.saves.length, 0)
  finishFetch(response())
  await Promise.all([initialLoad, importing])
  assert.equal(app.calls.fetches, 1)
  assertReportedListImported(app.calls)
})

test("preserves PBS prices, quotes, case-insensitive names, and list titles", async () => {
  const app = setup()
  await app.importItems(
    'Bound Serpent\'s Jade Eye^"FOOTPAD\'S SHOES";;0;0;0;0;0;0;0;50000;;#;;^"Worn Shortsword";;0;0;0;0;0;0;0;75000;;#;;'
  )
  assert.deepEqual(app.calls.saves, [{ 999: 42, 47: 50000, 25: 75000 }])
})

test("supports a single item without a list title and reuses loaded names", async () => {
  const app = setup()
  await app.loadItems()
  await app.importItems("Worn Shortsword")
  assert.equal(app.calls.fetches, 1)
  assert.deepEqual(app.calls.saves, [{ 999: 42, 25: 200 }])
})

test("does not save or report success when no item names match", async () => {
  const app = setup()
  await app.importItems("boe^Unknown item")
  assert.equal(app.calls.saves.length, 0)
  assert.equal(app.calls.flashes.length, 0)
  assert.equal(app.calls.toasts[0].type, "error")
})

for (const failure of [
  "network",
  "HTTP",
  "invalid JSON shape",
  "empty data",
  "invalid JSON",
]) {
  test(`failed ${failure} lookup can be retried without restarting`, async () => {
    let fail = true
    const app = setup(async () => {
      if (!fail) return response()
      if (failure === "network") throw new Error("offline")
      if (failure === "HTTP") return response({ detail: "unavailable" }, 503)
      if (failure === "empty data") return response([])
      if (failure === "invalid JSON") {
        return {
          ok: true,
          json: async () => {
            throw new SyntaxError("bad JSON")
          },
        }
      }
      return response({ detail: "unexpected response" })
    })
    await app.importItems()
    assert.equal(app.calls.saves.length, 0)
    assert.equal(app.calls.flashes.length, 0)
    assert.equal(app.calls.toasts[0].type, "error")
    fail = false
    await app.importItems()
    assert.equal(app.calls.fetches, 2)
    assertReportedListImported(app.calls)
  })
}

test("save failures show an error without success feedback", async () => {
  const app = setup(undefined, new Error("disk full"))
  await app.importItems()
  assert.equal(app.calls.flashes.length, 0)
  assert.match(app.calls.toasts[0].message, /disk full/)
})
