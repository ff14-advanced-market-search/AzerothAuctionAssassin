#!/usr/bin/python3
import json, requests
from utils.api_requests import (
    WOW_DISCORD_CONSENT,
    get_itemnames,
    get_ilvl_items,
    get_raidbots_bonus_ids,
    get_raidbots_equippable_items,
    get_raidbots_item_curves,
    get_raidbots_item_squish_era,
    get_pet_names_backup,
)

# get the upload timers
upload_timers = requests.post(
    "https://api.saddlebagexchange.com/api/wow/uploadtimers",
    json={"discord_consent": WOW_DISCORD_CONSENT},
).json()
# write to StaticData/upload_timers.json
with open("StaticData/upload_timers.json", "w") as f:
    json.dump(upload_timers, f, indent=2)

# get the item names
item_names = get_itemnames()
# write to StaticData/item_names.json
with open("StaticData/item_names.json", "w") as f:
    json.dump(item_names, f, indent=2)

# get the pet names
pet_names = get_pet_names_backup()
# write to StaticData/pet_names.json
with open("StaticData/pet_names.json", "w") as f:
    json.dump(pet_names, f, indent=2)

# get the raidbots bonus ids
bonuses = get_raidbots_bonus_ids()
# write to StaticData/bonuses.json
with open("StaticData/bonuses.json", "w") as f:
    json.dump(bonuses, f, indent=2)

# optional: post-midnight ilvl fallbacks (Raidbots equippable-items, item-curves, item-squish-era)
equippable = get_raidbots_equippable_items()
if equippable:
    with open("StaticData/equippable-items.json", "w") as f:
        json.dump(equippable, f, indent=2)
curves = get_raidbots_item_curves()
if curves:
    with open("StaticData/item-curves.json", "w") as f:
        json.dump(curves, f, indent=2)
squish_era = get_raidbots_item_squish_era()
if squish_era:
    with open("StaticData/item-squish-era.json", "w") as f:
        json.dump(squish_era, f, indent=2)

# get the ilvl items
json_data = {
    "discord_consent": WOW_DISCORD_CONSENT,
    "ilvl": 201,
    "itemQuality": -1,
    "required_level": -1,
    "item_class": [2, 4],
    "item_subclass": [-1],
    "item_ids": [],
}
ilvl_items = requests.post(
    "https://api.saddlebagexchange.com/api/wow/itemdata",
    json=json_data,
).json()
# write to StaticData/ilvl_items.json
with open("StaticData/ilvl_items.json", "w") as f:
    json.dump(ilvl_items, f, indent=2)

print("Static data created successfully!")
