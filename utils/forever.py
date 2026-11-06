"""Forever market feed keys: positive individual house IDs, negative commodities."""

import math
import re

# Verified against Undermine's realm catalog and Blizzard snapshots in both regions.
MARKETS = {
    110: ("PvP Alliance", "pvp-alliance"),
    111: ("Normal Alliance", "pve-alliance"),
    113: ("PvP Horde", "pvp-horde"),
    114: ("Normal Horde", "pve-horde"),
    116: ("PvP Neutral", "pvp-neutral"),
    117: ("Normal Neutral", "pve-neutral"),
    119: ("Roleplay Alliance", "rp-alliance"),
    120: ("Roleplay Horde", "rp-horde"),
    121: ("Roleplay Neutral", "rp-neutral"),
    123: ("Roleplay PvP Alliance", "rppvp-alliance"),
    124: ("Roleplay PvP Horde", "rppvp-horde"),
    125: ("Roleplay PvP Neutral", "rppvp-neutral"),
}

FOREVER_MARKETS = {
    "PvP Alliance — Items": 110,
    "PvP Alliance — Commodities": -110,
    "Normal Alliance — Items": 111,
    "Normal Alliance — Commodities": -111,
    "PvP Horde — Items": 113,
    "PvP Horde — Commodities": -113,
    "Normal Horde — Items": 114,
    "Normal Horde — Commodities": -114,
    "PvP Neutral — Items": 116,
    "PvP Neutral — Commodities": -116,
    "Normal Neutral — Items": 117,
    "Normal Neutral — Commodities": -117,
    "Roleplay Alliance — Items": 119,
    "Roleplay Alliance — Commodities": -119,
    "Roleplay Horde — Items": 120,
    "Roleplay Horde — Commodities": -120,
    "Roleplay Neutral — Items": 121,
    "Roleplay Neutral — Commodities": -121,
    "Roleplay PvP Alliance — Items": 123,
    "Roleplay PvP Alliance — Commodities": -123,
    "Roleplay PvP Horde — Items": 124,
    "Roleplay PvP Horde — Commodities": -124,
    "Roleplay PvP Neutral — Items": 125,
    "Roleplay PvP Neutral — Commodities": -125,
}


def is_forever(region):
    return region in ("NAFOREVER", "EUFOREVER")


def market_name(feed_id):
    market = MARKETS.get(abs(int(feed_id)))
    if not market:
        return None
    feed = "Commodities" if int(feed_id) < 0 else "Items"
    return f"{market[0]} — {feed}"


def rename_markets(markets):
    return {
        (
            (market_name(feed) or name)
            if re.fullmatch(
                r"(Alliance|Horde|Blackwater) Auction House \d+ — (Items|Commodities)",
                name,
            )
            else name
        ): feed
        for name, feed in markets.items()
    }


def undermine_link(region, feed_id, item_id):
    market = MARKETS.get(abs(int(feed_id)))
    if not market:
        raise ValueError("Invalid Forever feed ID")
    prefix = "usf" if region == "NAFOREVER" else "euf"
    return f"https://undermine.exchange/#{prefix}-{market[1]}/{item_id}"


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
        for name, feed in rename_markets(markets).items()
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
