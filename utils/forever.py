"""Forever market feed keys: positive individual house IDs, negative commodities."""

import math
import re
import json
import tempfile
from pathlib import Path

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
    if not isinstance(markets, dict):
        return {}
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


def validate_names(data):
    if not isinstance(data, dict) or not data:
        raise ValueError("Invalid or empty Forever names response")
    for item_id, name in data.items():
        # Validate conversion here so malformed API IDs trigger the backup path.
        if not re.fullmatch(r"[0-9]+", str(item_id)):
            raise ValueError("Invalid Forever item ID")
        if int(item_id) <= 0 or not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid Forever names response")
    return data


def validate_statistics(data):
    if not isinstance(data, list) or not data:
        raise ValueError("Invalid or empty Forever statistics response")
    for row in data:
        if (
            not isinstance(row, dict)
            or isinstance(row.get("itemID"), bool)
            or not isinstance(row.get("itemID"), int)
            or not isinstance(row.get("itemName"), str)
            or not row["itemName"].strip()
        ):
            raise ValueError("Invalid Forever statistics row")
        for field in ("desiredPrice", "salesPerDay"):
            value = row.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or (isinstance(value, float) and not math.isfinite(value))
                or value < 0
            ):
                raise ValueError(f"Invalid Forever statistics {field}")
    return data


def save_markets(path, markets):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=path.name + ".",
            delete=False,
        ) as target:
            temporary = Path(target.name)
            json.dump(markets, target, indent=4)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_markets(path, migrate=False):
    path = Path(path)
    if not path.exists():
        markets = FOREVER_MARKETS.copy()
        if migrate:
            save_markets(path, markets)
        return markets
    try:
        original = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(original, dict):
            raise ValueError("expected a market object")
        for feed in original.values():
            if not re.fullmatch(r"-?[0-9]+", str(feed)) or not faction(feed):
                raise ValueError("invalid Forever feed ID")
        markets = rename_markets(original)
    except (OSError, ValueError) as error:
        print(
            f"Invalid Forever market file {path}; preserving file and using defaults: {error}"
        )
        return FOREVER_MARKETS.copy()
    if migrate and markets != original:
        save_markets(path, markets)
    return markets
