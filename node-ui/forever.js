/* Forever feed IDs are local list keys, not Blizzard realm IDs. */
// Verified against Undermine's realm catalog and matching Blizzard snapshots
// for all 12 houses in both regions (2026-11-06).
const MARKETS = {
  110: {
    name: "PvP Alliance",
    slug: "pvp-alliance",
  },
  111: {
    name: "Normal Alliance",
    slug: "pve-alliance",
  },
  113: {
    name: "PvP Horde",
    slug: "pvp-horde",
  },
  114: {
    name: "Normal Horde",
    slug: "pve-horde",
  },
  116: {
    name: "PvP Neutral",
    slug: "pvp-neutral",
  },
  117: {
    name: "Normal Neutral",
    slug: "pve-neutral",
  },
  119: {
    name: "Roleplay Alliance",
    slug: "rp-alliance",
  },
  120: {
    name: "Roleplay Horde",
    slug: "rp-horde",
  },
  121: {
    name: "Roleplay Neutral",
    slug: "rp-neutral",
  },
  123: {
    name: "Roleplay PvP Alliance",
    slug: "rppvp-alliance",
  },
  124: {
    name: "Roleplay PvP Horde",
    slug: "rppvp-horde",
  },
  125: {
    name: "Roleplay PvP Neutral",
    slug: "rppvp-neutral",
  },
}

const Forever = {
  isRegion: (region) => ["NAFOREVER", "EUFOREVER"].includes(region),
  region: (region) => (region === "NAFOREVER" ? "NA" : "EU"),
  name(id) {
    const market = MARKETS[Math.abs(Number(id))]
    return market
      ? `${market.name} — ${Number(id) < 0 ? "Commodities" : "Items"}`
      : null
  },
  rename(markets) {
    return Object.fromEntries(
      Object.entries(markets).map(([name, id]) => [
        /^(Alliance|Horde|Blackwater) Auction House \d+ — (Items|Commodities)$/.test(
          name
        )
          ? this.name(id) || name
          : name,
        id,
      ])
    )
  },
  undermine(region, id, itemId) {
    const market = MARKETS[Math.abs(Number(id))]
    if (!market) throw new Error("Invalid Forever feed ID")
    const prefix = region === "NAFOREVER" ? "usf" : "euf"
    return `https://undermine.exchange/#${prefix}-${market.slug}/${itemId}`
  },
  faction(id) {
    const house = Math.abs(Number(id))
    if ([110, 111, 119, 123].includes(house)) return "alliance"
    if ([113, 114, 120, 124].includes(house)) return "horde"
    if ([116, 117, 121, 125].includes(house)) return "booty bay"
    return null
  },
  filter(markets, faction = "all") {
    return Object.fromEntries(
      Object.entries(this.rename(markets)).filter(
        ([, id]) =>
          this.faction(id) &&
          (faction === "all" || this.faction(id) === faction)
      )
    )
  },
  url(region, id) {
    if (!Number.isInteger(Number(id)) || !this.faction(id))
      throw new Error("Invalid Forever feed ID")
    const apiRegion = region === "NAFOREVER" ? "us" : "eu"
    const feed = Number(id) < 0 ? "/commodities" : ""
    return `https://${apiRegion}.api.blizzard.com/data/wow/ruleset/1/auctions/${Math.abs(
      Number(id)
    )}${feed}?namespace=dynamic-forever-${apiRegion}&locale=en_US`
  },
  unitPrice(auction, field) {
    const quantity = Number(auction.quantity)
    const price = Number(auction[field])
    if (
      !Number.isFinite(price) ||
      price <= 0 ||
      !Number.isInteger(quantity) ||
      quantity <= 0
    )
      return null
    return field === "unit_price" ? price : price / quantity
  },
}
if (typeof module !== "undefined") module.exports = Forever
