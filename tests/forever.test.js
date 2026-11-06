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
    JSON.stringify({ Items: 110, Commodities: -110, Horde: 113 })
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
  assert.match(text, /wowhead.com\/forever\/item=3048/)
  assert.doesNotMatch(text, /saddlebagexchange.com\/wow\/|undermine.exchange/)
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
