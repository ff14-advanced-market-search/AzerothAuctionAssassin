const assert = require("node:assert/strict")
const { test } = require("node:test")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const vm = require("node:vm")
const { createRequire } = require("node:module")
const Forever = require("../node-ui/forever")
const { getRealmListByRegion } = require("../node-ui/realm-data")

function scanner(fetch) {
  const filename = path.resolve(__dirname, "../node-ui/mega-alerts.js")
  const localRequire = createRequire(filename)
  const context = vm.createContext({
    require: (name) => (name === "undici" ? { fetch } : localRequire(name)),
    __dirname: path.dirname(filename),
    module: { exports: {} },
    console: { log() {}, error() {} },
    Buffer,
    URLSearchParams,
    AbortController,
    setTimeout,
    clearTimeout,
  })
  vm.runInContext(fs.readFileSync(filename, "utf8"), context)
  return context.module.exports
}
function response(data, minute = 0) {
  return {
    status: 200,
    ok: true,
    headers: new Headers({
      "last-modified": `Fri, 06 Nov 2026 14:${String(minute).padStart(
        2,
        "0"
      )}:00 GMT`,
    }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  }
}

test("Forever markets expose both feeds, exclude empty houses and filter factions", () => {
  for (const region of ["NAFOREVER", "EUFOREVER"]) {
    const markets = getRealmListByRegion(region)
    assert.equal(Object.keys(markets).length, 24)
    assert.equal(new Set(Object.values(markets)).size, 24)
    for (const faction of ["alliance", "horde", "booty bay"])
      assert.equal(Object.keys(Forever.filter(markets, faction)).length, 8)
    assert.equal(Object.keys(Forever.filter(markets, "all")).length, 24)
    for (const id of Object.values(markets)) {
      assert.ok(![112, 115, 118].includes(Math.abs(id)))
      assert.ok(
        Forever.url(region, id).includes(
          `dynamic-forever-${region === "NAFOREVER" ? "us" : "eu"}`
        )
      )
      assert.equal(Forever.url(region, id).includes("/commodities?"), id < 0)
    }
  }
})

test("stack prices become unit prices; commodity prices are already per unit", () => {
  assert.equal(
    Forever.unitPrice({ buyout: 200000, quantity: 2 }, "buyout"),
    100000
  )
  assert.equal(
    Forever.unitPrice({ unit_price: 110000, quantity: 20 }, "unit_price"),
    110000
  )
  for (const quantity of [undefined, 0, -1, 1.5])
    assert.equal(Forever.unitPrice({ buyout: 100, quantity }, "buyout"), null)
  assert.equal(Forever.unitPrice({ buyout: 0, quantity: 1 }, "buyout"), null)
})

test("full Forever scan emits item alerts without pets, Raidbots, Retail names or external Discord posts", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-forever-test-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({
      WOW_REGION: "NAFOREVER",
      FACTION: "alliance",
      DEBUG: true,
      DISCORD_ALERTS_ENABLED: false,
      IN_APP_ALERTS_ENABLED: true,
      TOKEN_PRICE: 100000,
      USE_POST_MIDNIGHT_ILVL: true,
    })
  )
  fs.writeFileSync(
    path.join(dir, "desired_items.json"),
    JSON.stringify({ 3048: 12 })
  )
  fs.writeFileSync(
    path.join(dir, "desired_ilvl_list.json"),
    JSON.stringify([{ item_ids: [3048], ilvl: 1 }])
  )
  fs.writeFileSync(
    path.join(dir, "desired_pet_ilvl_list.json"),
    JSON.stringify([{ petID: 1, price: 100 }])
  )
  fs.writeFileSync(
    path.join(dir, "naforever-wow-connected-realm-ids.json"),
    JSON.stringify({
      "Alliance Auction House 110 — Items": 110,
      "Alliance Auction House 110 — Commodities": -110,
      Horde: 113,
    })
  )
  const urls = [],
    embeds = []
  const api = scanner(async (url) => {
    urls.push(url)
    if (url.endsWith("/forever/itemnames"))
      return response({ 3048: "Lambent Scale Legguards" })
    if (url.includes("oauth.battle.net"))
      return response({ access_token: "test-token" })
    if (url.includes("/ruleset/1/auctions/110"))
      return response({
        auctions: [
          {
            id: 1,
            item: { id: 3048 },
            quantity: 2,
            ...(url.includes("/commodities?")
              ? { unit_price: 110000 }
              : { buyout: 200000 }),
          },
        ],
      })
    throw new Error(`Unexpected request: ${url}`)
  })
  api.setPaths(dir, dir)
  api.setAlertEmbedCallback((embed) => embeds.push(embed))
  await api.main()
  assert.equal(urls.filter((u) => u.includes("/ruleset/1/auctions/")).length, 2)
  assert.equal(embeds.length, 2)
  const text = JSON.stringify(embeds)
  assert.match(text, /Lambent Scale Legguards/)
  assert.match(text, /PvP Alliance — Items/)
  assert.doesNotMatch(text, /Alliance Auction House 110/)
  assert.match(text, /wowhead.com\/forever\/item=3048/)
  assert.doesNotMatch(text, /saddlebagexchange.com\/wow\//)
  assert.match(text, /undermine.exchange\/#usf-pvp-alliance\/3048/)
  assert.match(text, /\[10\]/)
  assert.match(text, /\[11\]/)
})

test("individual and commodity update timers are independent even with equal Last-Modified", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-forever-timers-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "EUFOREVER" })
  )
  const urls = []
  const api = scanner(async (url) => {
    urls.push(url)
    return response({ auctions: [{ id: 1 }] })
  })
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  data.upload_timers = {}
  data.fetchAccessToken = async () => "test"
  assert.equal((await data.get_listings_single(110)).length, 1)
  assert.equal((await data.get_listings_single(-110)).length, 1)
  assert.equal(await data.get_listings_single(110), null)
  assert.equal(await data.get_listings_single(-110), null)
  assert.equal(Object.keys(data.upload_timers).length, 2)
  assert.match(urls[0], /eu.api.blizzard.com/)
  assert.match(
    data.upload_timers[-110].tableName,
    /EU_forever_110_commodityListings/
  )
})

test("Forever market labels and Undermine links use the verified ruleset and faction", () => {
  const expected = {
    110: "pvp-alliance",
    111: "pve-alliance",
    113: "pvp-horde",
    114: "pve-horde",
    116: "pvp-neutral",
    117: "pve-neutral",
    119: "rp-alliance",
    120: "rp-horde",
    121: "rp-neutral",
    123: "rppvp-alliance",
    124: "rppvp-horde",
    125: "rppvp-neutral",
  }
  for (const [id, slug] of Object.entries(expected)) {
    for (const sign of [1, -1]) {
      assert.equal(
        Forever.undermine("EUFOREVER", Number(id) * sign, 2912),
        `https://undermine.exchange/#euf-${slug}/2912`
      )
      assert.equal(
        Forever.undermine("NAFOREVER", Number(id) * sign, 2912),
        `https://undermine.exchange/#usf-${slug}/2912`
      )
    }
  }
  assert.equal(Forever.name(111), "Normal Alliance — Items")
  assert.equal(Forever.name(-111), "Normal Alliance — Commodities")
  assert.deepEqual(
    Forever.rename({
      "Alliance Auction House 111 — Items": 111,
      "Blackwater Auction House 125 — Commodities": -125,
    }),
    {
      "Normal Alliance — Items": 111,
      "Roleplay PvP Neutral — Commodities": -125,
    }
  )
  assert.deepEqual(Forever.rename({ "My selected market": 111 }), {
    "My selected market": 111,
  })
})

test("Forever scanner uses public GitHub names when Saddlebag is down", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-forever-backup-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "NAFOREVER" })
  )
  fs.writeFileSync(
    path.join(dir, "desired_items.json"),
    JSON.stringify({ 3048: 10 })
  )
  const urls = []
  const api = scanner(async (url) => {
    urls.push(url)
    if (url.includes("api.saddlebagexchange.com"))
      return { ok: false, status: 503 }
    assert.match(
      url,
      /raw.githubusercontent.com\/.*\/main\/StaticData\/forever_item_names.json$/
    )
    return response({ 3048: "Lambent Scale Legguards", 720: "Brawler Gloves" })
  })
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  await data.initialize()
  assert.equal(data.ITEM_NAMES[3048], "Lambent Scale Legguards")
  assert.equal(data.ITEM_NAMES[720], undefined)
  assert.equal(urls.length, 2)
})

test("null and array market files cannot break all-region loading", () => {
  assert.equal(Object.keys(Forever.rename(null)).length, 24)
  assert.equal(Object.keys(Forever.rename([])).length, 24)
})

test("Forever skips unchanged bodies and uses each signed feed's conditional header", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-conditional-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "EUFOREVER" })
  )
  const stamp = "Fri, 06 Nov 2026 14:00:00 GMT"
  const calls = []
  let bodyReads = 0,
    cancelled = 0
  const api = scanner(async (url, options) => {
    calls.push({ url, options })
    return {
      status: calls.length === 3 ? 304 : 200,
      headers: new Headers({ "Last-Modified": stamp }),
      body: {
        cancel: async () => {
          cancelled++
        },
      },
      text: async () => {
        bodyReads++
        return JSON.stringify({ auctions: [{ id: 1 }] })
      },
    }
  })
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  data.upload_timers = {}
  data.fetchAccessToken = async () => "test"
  await data.get_listings_single(110)
  await data.get_listings_single(-110)
  assert.equal(await data.get_listings_single(110), null)
  assert.equal(await data.get_listings_single(-110), null)
  assert.equal(bodyReads, 2)
  assert.equal(cancelled, 2)
  assert.equal(calls[0].options.headers["If-Modified-Since"], undefined)
  assert.equal(calls[1].options.headers["If-Modified-Since"], undefined)
  assert.equal(calls[2].options.headers["If-Modified-Since"], stamp)
  assert.equal(calls[3].options.headers["If-Modified-Since"], stamp)
})

test("one failed feed does not reject scanning and remains eligible until recovery", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-retry-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "NAFOREVER" })
  )
  fs.writeFileSync(
    path.join(dir, "naforever-wow-connected-realm-ids.json"),
    JSON.stringify({ Items: 110, Commodities: -110 })
  )
  let offline = true
  const api = scanner(async (url) => {
    if (offline && !url.includes("commodities")) throw new Error("offline")
    return response({ auctions: [{ id: 1 }] })
  })
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  data.upload_timers = {}
  data.fetchAccessToken = async () => "test"
  assert.equal((await data.get_listings_single(110)).length, 0)
  assert.equal((await data.get_listings_single(-110)).length, 1)
  assert.equal(data.getUntrackedForeverFeeds().length, 0)
  assert.equal(await data.get_listings_single(110), null)
  data.feedFailures[110].nextRetryAt = 0
  data.feedLastAttempt[110] = Date.now() - 60001
  assert.deepEqual(Array.from(data.getUntrackedForeverFeeds()), [110])
  offline = false
  assert.equal((await data.get_listings_single(110)).length, 1)
  assert.equal(data.getUntrackedForeverFeeds().length, 0)
})

test("Forever feed failures back off to five minutes and reset after success", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-backoff-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "NAFOREVER" })
  )
  let offline = true,
    requests = 0
  const api = scanner(async () => {
    requests++
    if (offline) throw new Error("403")
    return response({ auctions: [] })
  })
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  data.upload_timers = {}
  data.fetchAccessToken = async () => "test"
  for (let attempt = 0; attempt < 10; attempt++) {
    if (data.feedFailures[110]) data.feedFailures[110].nextRetryAt = 0
    await data.get_listings_single(110)
  }
  const remaining = data.feedFailures[110].nextRetryAt - Date.now()
  assert.ok(remaining > 299000 && remaining <= 300000)
  await data.get_listings_single(110)
  assert.equal(requests, 10)
  data.feedFailures[110].nextRetryAt = 0
  offline = false
  await data.get_listings_single(110)
  assert.equal(data.feedFailures[110], undefined)
})

test("Forever feeds without Last-Modified wait a minute before recovery polling", async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aaa-no-header-"))
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }))
  fs.writeFileSync(
    path.join(dir, "mega_data.json"),
    JSON.stringify({ WOW_REGION: "NAFOREVER" })
  )
  fs.writeFileSync(
    path.join(dir, "naforever-wow-connected-realm-ids.json"),
    JSON.stringify({ Items: 110 })
  )
  const api = scanner(async () => ({
    ...response({ auctions: [] }),
    headers: new Headers(),
  }))
  api.setPaths(dir, dir)
  const data = new api.MegaData()
  data.upload_timers = {}
  data.fetchAccessToken = async () => "test"
  await data.get_listings_single(110)
  assert.equal(data.getUntrackedForeverFeeds().length, 0)
  data.feedLastAttempt[110] = Date.now() - 60001
  assert.deepEqual(Array.from(data.getUntrackedForeverFeeds()), [110])
})
