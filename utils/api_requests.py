import requests
from tenacity import retry, stop_after_attempt


@retry(stop=stop_after_attempt(3))
def send_discord_message(message, webhook_url):
    try:
        json_data = {"content": message}
        response = requests.post(webhook_url, json=json_data)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        return True  # Message sent successfully
    except requests.exceptions.RequestException as ex:
        print("Error sending Discord message: %s", ex)
        return False  # Failed to send the message


@retry(stop=stop_after_attempt(3))
def get_wow_access_token(client_id, client_secret):
    access_token = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    ).json()["access_token"]
    return access_token


@retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
def get_listings_single(connectedRealmId: int, access_token: str, region: str):
    print("==========================================")
    print(f"gather data from connectedRealmId {connectedRealmId} of region {region}")
    if region == "NA":
        url = f"https://us.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}/auctions?namespace=dynamic-us&locale=en_US&access_token={access_token}"
    elif region == "EU":
        url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}/auctions?namespace=dynamic-eu&locale=en_EU&access_token={access_token}"
    else:
        print(
            f"{region} is not yet supported, reach out for us to add this region option"
        )
        exit(1)

    req = requests.get(url, timeout=20)

    auction_info = req.json()
    return auction_info["auctions"]


def get_update_timers(region, simple_snipe=False):
    # get from api every time
    update_timers = requests.post(
        "http://api.saddlebagexchange.com/api/wow/uploadtimers",
        json={},
    ).json()["data"]

    # cover specific realms
    if simple_snipe:
        if region == "EU":
            update_id = -2
        else:
            update_id = -1
        server_update_times = [
            time_data
            for time_data in update_timers
            if time_data["dataSetID"] == update_id
        ]
    else:
        server_update_times = [
            time_data
            for time_data in update_timers
            if time_data["dataSetID"] not in [-1, -2] and time_data["region"] == region
        ]
        print(server_update_times)

    return server_update_times


def get_itemnames():
    item_names = requests.post(
        "http://api.saddlebagexchange.com/api/wow/itemnames",
        json={"return_all": True},
    ).json()

    return item_names


def get_petnames(client_id, client_secret):
    access_token = get_wow_access_token(client_id, client_secret)
    pet_info = requests.get(
        f"https://us.api.blizzard.com/data/wow/pet/index?namespace=static-us&locale=en_US&access_token={access_token}"
    ).json()["pets"]
    pet_info = {pet["id"]: pet["name"] for pet in pet_info}
    return pet_info


def get_raidbots_bonus_ids():
    # thanks so much to Seriallos (Raidbots) and BinaryHabitat (GoblinStockAlerts) for organizing this data!
    bonus_ids = requests.get(
        "https://www.raidbots.com/static/data/live/bonuses.json"
    ).json()
    return {int(id): data for id, data in bonus_ids.items()}


def get_ilvl_items(ilvl, item_ids=[]):
    # hardcode for dragonflight only
    ilvl = 201

    json_data = {
        "ilvl": ilvl,
        "itemQuality": -1,
        "required_level": -1,
        "item_class": [2, 4],
        "item_subclass": [-1],
    }
    results = requests.post(
        "http://api.saddlebagexchange.com/api/wow/itemdata",
        json=json_data,
    ).json()
    if len(results) == 0:
        raise Exception(
            f"No items found at or above a base ilvl of {ilvl}, contact us on discord"
        )
    # filter only for specific item ids when given, use everything when not given
    if len(item_ids) > 0:
        results = {
            itemID: item_info
            for itemID, item_info in results.items()
            if int(itemID) in item_ids
        }

    item_names = {
        int(itemID): item_info["itemName"] for itemID, item_info in results.items()
    }
    base_ilvls = {
        int(itemID): item_info["ilvl"] for itemID, item_info in results.items()
    }
    return item_names, set(item_names.keys()), base_ilvls


def simple_snipe(json_data):
    snipe_results = requests.post(
        "http://api.saddlebagexchange.com/api/wow/regionpricecheck",
        json=json_data,
    ).json()

    return snipe_results
