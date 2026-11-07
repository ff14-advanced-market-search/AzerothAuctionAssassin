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
    run: (code) => vm.runInContext(code, context),
    calls,
    setRegion: (region) =>
      vm.runInContext(
        `state.megaData.WOW_REGION = ${JSON.stringify(region)}`,
        context
      ),
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

test("imports every reported item with a question-mark list separator", async () => {
  const app = setup()
  await app.importItems(auctionatorList.replace("boe^", "boe?"))
  assertReportedListImported(app.calls)
  assert.match(app.calls.toasts[0].message, /11.*6/)
})

for (const separator of ["^", "?"]) {
  test(`preserves PBS prices and ignores the list title with ${separator}`, async () => {
    const app = setup()
    await app.importItems(
      `Bound Serpent's Jade Eye${separator}"FOOTPAD'S SHOES";;0;0;0;0;0;0;0;50000;;#;;^"Worn Shortsword";;0;0;0;0;0;0;0;75000;;#;;`
    )
    assert.deepEqual(app.calls.saves, [{ 999: 42, 47: 50000, 25: 75000 }])
    assert.match(app.calls.toasts[0].message, /2 item\(s\).*0 name\(s\)/)
  })
}

test("imports a single PBS item after a question-mark list separator", async () => {
  const app = setup()
  await app.importItems('boe?"Worn Shortsword";;0;0;0;0;0;0;0;75000;;#;;')
  assert.deepEqual(app.calls.saves, [{ 999: 42, 25: 75000 }])
  assert.match(app.calls.toasts[0].message, /1 item\(s\).*0 name\(s\)/)
})

for (const price of ["Infinity", "-Infinity", "1e309", "-1", "NaN", " "]) {
  test(`uses the discounted default for invalid PBS price ${JSON.stringify(
    price
  )}`, async () => {
    const app = setup()
    await app.importItems(`boe?"Worn Shortsword";;0;0;0;0;0;0;0;${price};;#;;`)
    assert.deepEqual(app.calls.saves, [{ 999: 42, 25: 200 }])
  })
}

test("preserves an explicit zero PBS price", async () => {
  const app = setup()
  await app.importItems('boe?"Worn Shortsword";;0;0;0;0;0;0;0;0;;#;;')
  assert.deepEqual(app.calls.saves, [{ 999: 42, 25: 0 }])
})

const invalidMarketItems = [
  null,
  {},
  { itemID: 101 },
  { itemID: 102, itemName: 123 },
  { itemID: 103, itemName: "" },
  { itemID: 104, itemName: " " },
  { itemName: "Missing ID" },
]

test("filters malformed item rows and reuses only valid cached rows", async () => {
  const app = setup(async () =>
    response([...invalidMarketItems, ...marketItems])
  )
  const rows = await app.loadItems()
  assert.deepEqual(rows, marketItems)
  await app.importItems()
  assertReportedListImported(app.calls)
  assert.equal(app.calls.fetches, 1)
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
  "invalid item rows",
  "invalid JSON",
]) {
  test(`failed ${failure} lookup can be retried without restarting`, async () => {
    let fail = true
    const app = setup(async () => {
      if (!fail) return response()
      if (failure === "network") throw new Error("offline")
      if (failure === "HTTP") return response({ detail: "unavailable" }, 503)
      if (failure === "empty data") return response([])
      if (failure === "invalid item rows") return response(invalidMarketItems)
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

test("switches item catalogs between Retail and Forever without reusing cached names", async () => {
  const requests = []
  const ui = setup(async (url, options) => {
    requests.push({ url, payload: JSON.parse(options.body) })
    return response([
      {
        itemID: 3048,
        itemName: url.includes("/forever/") ? "Forever name" : "Retail name",
        desiredPrice: 1,
        salesPerDay: 0,
      },
    ])
  })
  ui.setRegion("NA")
  assert.equal((await ui.loadItems())[0].itemName, "Retail name")
  ui.setRegion("EUFOREVER")
  assert.equal((await ui.loadItems())[0].itemName, "Forever name")
  assert.match(requests[1].url, /\/wow\/forever\/megaitemnames$/)
  assert.equal(requests[1].payload.region, "EU")
  ui.setRegion("NA")
  assert.equal((await ui.loadItems())[0].itemName, "Retail name")
  assert.equal(requests.length, 3)
})

test("a stale Retail response cannot replace a newer Forever catalog", async () => {
  let finishOld
  let count = 0
  const ui = setup(async () => {
    count++
    if (count === 1)
      return new Promise((resolve) => {
        finishOld = resolve
      })
    return response([
      {
        itemID: 3048,
        itemName: "Forever name",
        desiredPrice: 1,
        salesPerDay: 0,
      },
    ])
  })
  ui.setRegion("NA")
  const old = ui.loadItems()
  ui.setRegion("NAFOREVER")
  await ui.loadItems()
  finishOld(
    response([{ itemID: 3048, itemName: "Retail name", desiredPrice: 1 }])
  )
  await old
  assert.equal((await ui.loadItems())[0].itemName, "Forever name")
  assert.equal(count, 2)
})

for (const region of ["NAFOREVER", "EUFOREVER"]) {
  test(`keeps ${region} names with zero suggestions during a price API outage`, async () => {
    const urls = []
    const ui = setup(async (url) => {
      urls.push(url)
      if (url.includes("api.saddlebagexchange.com")) return response({}, 503)
      assert.ok(url.endsWith("/StaticData/forever_item_names.json"))
      return response({ 3048: "Backup Forever name" })
    })
    ui.setRegion(region)
    const items = await ui.loadItems()
    assert.equal(items[0].itemName, "Backup Forever name")
    assert.equal(items[0].desiredPrice, 0)
    assert.equal(items[0].salesPerDay, 0)
    assert.equal(urls.length, 3)
  })
}

test("names-only PBS import skips missing prices and preserves supplied and saved targets", async () => {
  const ui = setup(async () =>
    response([
      {
        itemID: 3048,
        itemName: "Unpriced",
        desiredPrice: 0,
        salesPerDay: 0,
        priceAvailable: false,
      },
      {
        itemID: 720,
        itemName: "Explicit",
        desiredPrice: 0,
        salesPerDay: 0,
        priceAvailable: false,
      },
      {
        itemID: 999,
        itemName: "Saved",
        desiredPrice: 0,
        salesPerDay: 0,
        priceAvailable: false,
      },
    ])
  )
  await ui.importItems("List^Unpriced^Explicit;;0^Saved")
  assert.deepEqual(ui.calls.saves[0], { 999: 42, 720: 0 })
  assert.ok(
    ui.calls.toasts.some((toast) => toast.message.includes("1 item(s) skipped"))
  )
  assert.ok(ui.calls.logs.some((line) => line.includes("Unpriced")))
  assert.equal(ui.calls.toasts.at(-1).type, "warning")
  assert.match(ui.calls.toasts.at(-1).message, /1 item\(s\) skipped/)
})

test(
  "settings save finishes while the item lookup remains pending",
  { timeout: 1000 },
  async () => {
    const ui = setup()
    ui.run(`readMegaForm = () => ({ WOW_REGION: "NAFOREVER" })
    window.aaa.saveMegaData = async (data) => data
    renderMegaForm = () => {}
    applyForeverMode = () => {}
    trimAlertEmbedHistoryToLimit = () => {}
    renderItemList = () => {}
    renderIlvlRules = () => {}
    renderPetIlvlRules = () => {}
    fetchItemNames = () => new Promise((resolve) => { globalThis.finishLookup = resolve })`)
    assert.equal(await ui.run("saveMegaData(true)"), true)
    ui.run("finishLookup([])")
  }
)

test("saving Forever switches away from an active pet or ilvl view", () => {
  const ui = setup()
  ui.run(`state.megaData.WOW_REGION = "NAFOREVER"
    document.querySelector = () => ({})
    showView = (view) => { globalThis.selectedView = view }
    applyForeverMode()`)
  assert.equal(ui.run("selectedView"), "items")
})

test("a names-only result requests manual pricing instead of suggesting zero", () => {
  const ui = setup()
  ui.run(`globalThis.cards = []
    document.createElement = () => ({children: [], appendChild(child) { this.children.push(child) }})
    itemSearchResults.appendChild = (card) => cards.push(card)
    globalThis.form = { id: {value: ""}, price: {value: ""} }
    document.getElementById = () => form
    showView = () => {}
    ensureItemName = () => {}
    renderItemSearchResults([{ itemID: 3048, itemName: "Item", desiredPrice: 0, salesPerDay: 0, priceAvailable: false }])
    cards[0].children[1].onclick()`)
  assert.equal(ui.run("form.price.value"), "")
  assert.match(
    ui.run("cards[0].children[0].children[1].textContent"),
    /unavailable/
  )
})

test("a zero-price API row is unavailable and names-only cache retries after expiry", async () => {
  let recovered = false
  const ui = setup(async () =>
    response([
      {
        itemID: 3048,
        itemName: "Item",
        desiredPrice: recovered ? 100 : 0,
        salesPerDay: 0,
      },
    ])
  )
  ui.setRegion("NAFOREVER")
  assert.equal((await ui.loadItems())[0].priceAvailable, false)
  const firstCalls = ui.calls.fetches
  await ui.loadItems()
  assert.equal(ui.calls.fetches, firstCalls)
  ui.run("itemSearchRetryAt = Date.now() - 1")
  recovered = true
  const rows = await ui.loadItems()
  assert.equal(rows[0].desiredPrice, 100)
  assert.equal(rows[0].priceAvailable, true)
  assert.equal(ui.calls.fetches, firstCalls + 1)
})

test("an expired names cache stays usable if all refresh sources fail", async () => {
  let offline = false
  const ui = setup(async (url) => {
    if (offline || url.includes("megaitemnames")) return response({}, 503)
    return response({ 3048: "Retained name" })
  })
  ui.setRegion("NAFOREVER")
  await ui.loadItems()
  offline = true
  ui.run("itemSearchRetryAt = Date.now() - 1")
  assert.equal((await ui.loadItems())[0].itemName, "Retained name")
})

test("Use applies a real recommendation instead of an old saved target", () => {
  const ui = setup()
  ui.run(`globalThis.cards = []
    document.createElement = () => ({children: [], appendChild(child) { this.children.push(child) }})
    itemSearchResults.appendChild = (card) => cards.push(card)
    globalThis.form = { id: {value: ""}, price: {value: ""} }
    document.getElementById = () => form
    showView = () => {}
    ensureItemName = () => {}
    renderItemSearchResults([{ itemID: 999, itemName: "Item", desiredPrice: 100, salesPerDay: 2 }])
    cards[0].children[1].onclick()`)
  assert.equal(ui.run("form.price.value"), 20)
})

test("Forever Use keeps a sub-gold recommendation", () => {
  const ui = setup()
  ui.setRegion("NAFOREVER")
  ui.run(`globalThis.cards = []
    document.createElement = () => ({children: [], appendChild(child) { this.children.push(child) }})
    itemSearchResults.appendChild = (card) => cards.push(card)
    globalThis.form = { id: {value: ""}, price: {value: ""} }
    document.getElementById = () => form
    showView = () => {}
    ensureItemName = () => {}
    renderItemSearchResults([{ itemID: 999, itemName: "Item", desiredPrice: 2, salesPerDay: 1 }])
    cards[0].children[1].onclick()`)
  assert.equal(ui.run("form.price.value"), 0.4)
  assert.match(ui.run("cards[0].children[0].children[1].textContent"), /0\.4/)
})

test("Save refreshes pet and ilvl rule names after leaving Forever", async () => {
  const ui = setup()
  ui.run(`globalThis.draws = []
    readMegaForm = () => ({ WOW_REGION: "EU" })
    window.aaa.saveMegaData = async (data) => data
    renderMegaForm = () => {}
    applyForeverMode = () => {}
    trimAlertEmbedHistoryToLimit = () => {}
    renderItemList = () => draws.push("items")
    renderIlvlRules = () => draws.push("ilvl")
    renderPetIlvlRules = () => draws.push("pets")
    fetchItemNames = async () => []
    fetchPetNames = async () => []`)
  await ui.run("saveMegaData(true)")
  await Promise.resolve()
  assert.deepEqual(Array.from(ui.run("draws")).sort(), [
    "ilvl",
    "items",
    "pets",
  ])
})
