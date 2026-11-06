"""Forever market feed keys: positive individual house IDs, negative commodities."""

import math

FOREVER_MARKETS = {
    "Alliance Auction House 110 — Items": 110,
    "Alliance Auction House 110 — Commodities": -110,
    "Alliance Auction House 111 — Items": 111,
    "Alliance Auction House 111 — Commodities": -111,
    "Horde Auction House 113 — Items": 113,
    "Horde Auction House 113 — Commodities": -113,
    "Horde Auction House 114 — Items": 114,
    "Horde Auction House 114 — Commodities": -114,
    "Blackwater Auction House 116 — Items": 116,
    "Blackwater Auction House 116 — Commodities": -116,
    "Blackwater Auction House 117 — Items": 117,
    "Blackwater Auction House 117 — Commodities": -117,
    "Alliance Auction House 119 — Items": 119,
    "Alliance Auction House 119 — Commodities": -119,
    "Horde Auction House 120 — Items": 120,
    "Horde Auction House 120 — Commodities": -120,
    "Blackwater Auction House 121 — Items": 121,
    "Blackwater Auction House 121 — Commodities": -121,
    "Alliance Auction House 123 — Items": 123,
    "Alliance Auction House 123 — Commodities": -123,
    "Horde Auction House 124 — Items": 124,
    "Horde Auction House 124 — Commodities": -124,
    "Blackwater Auction House 125 — Items": 125,
    "Blackwater Auction House 125 — Commodities": -125,
}


def is_forever(region):
    return region in ("NAFOREVER", "EUFOREVER")


def faction(feed_id):
    house = abs(int(feed_id))
    if house in (110, 111, 119, 123):
        return "alliance"
    if house in (113, 114, 120, 124):
        return "horde"
    if house in (116, 117, 121, 125):
        return "booty bay"
    return None


def filter_markets(markets, selected_faction):
    return {
        name: int(feed)
        for name, feed in markets.items()
        if faction(feed)
        and (selected_faction == "all" or faction(feed) == selected_faction)
    }


def auction_url(region, feed_id):
    if not faction(feed_id):
        raise ValueError("Invalid Forever feed ID")
    api_region = "us" if region == "NAFOREVER" else "eu"
    suffix = "/commodities" if int(feed_id) < 0 else ""
    return (
        f"https://{api_region}.api.blizzard.com/data/wow/ruleset/1/auctions/"
        f"{abs(int(feed_id))}{suffix}?namespace=dynamic-forever-{api_region}&locale=en_US"
    )


def unit_price(auction, field):
    price, quantity = auction.get(field), auction.get("quantity")
    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        return None
    if not isinstance(quantity, int) or quantity <= 0:
        return None
    return price if field == "unit_price" else price / quantity
