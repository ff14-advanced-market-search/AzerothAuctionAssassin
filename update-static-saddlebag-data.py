#!/usr/bin/python3
import json, requests
from utils.api_requests import (
    get_itemnames,
    get_ilvl_items,
    get_raidbots_bonus_ids,
    get_pet_names_backup,
)

# get the upload timers
upload_timers = requests.post(
    "http://api.saddlebagexchange.com/api/wow/uploadtimers",
    json={},
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

# get the ilvl items
json_data = {
    "ilvl": 201,
    "itemQuality": -1,
    "required_level": -1,
    "item_class": [2, 4],
    "item_subclass": [-1],
    "item_ids": [],
}
ilvl_items = requests.post(
    "http://api.saddlebagexchange.com/api/wow/itemdata",
    json=json_data,
).json()
# write to StaticData/ilvl_items.json
with open("StaticData/ilvl_items.json", "w") as f:
    json.dump(ilvl_items, f, indent=2)

print("Static data created successfully!")
