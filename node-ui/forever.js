/* Forever feed IDs are local list keys, not Blizzard realm IDs. */
const Forever = {
  isRegion: (region) => ["NAFOREVER", "EUFOREVER"].includes(region),
  region: (region) => (region === "NAFOREVER" ? "NA" : "EU"),
  faction(id) {
    const house = Math.abs(Number(id))
    if ([110, 111, 119, 123].includes(house)) return "alliance"
    if ([113, 114, 120, 124].includes(house)) return "horde"
    if ([116, 117, 121, 125].includes(house)) return "booty bay"
    return null
  },
  filter(markets, faction = "all") {
    return Object.fromEntries(
      Object.entries(markets).filter(
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
