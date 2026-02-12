import requests
from tenacity import retry, stop_after_attempt
from utils.helpers import get_wow_russian_realm_ids


## DISCORD API CALLS ##
def send_embed_discord(embed, webhook_url):
    # Send message
    """Send an embed message to a specified Discord webhook URL.
    Parameters:
        - embed (dict): A dictionary representing the embed content to be sent.
        - webhook_url (str): The Discord webhook URL to which the embed will be sent.
    Returns:
        - bool: True if the embed is sent successfully; False otherwise.
    Processing Logic:
        - Checks the HTTP response status to determine success.
        - Raises an exception for non-2xx status codes.
        - Catches exceptions related to request errors."""
    try:
        print(f"sending embed to discord...")
        req = requests.post(webhook_url, json={"embeds": [embed]})
        if req.status_code != 204 and req.status_code != 200:
            print(f"Failed to send embed to discord: {req.status_code} - {req.text}")
            req.raise_for_status()  # Raise an exception for non-2xx status codes
        else:
            print(f"Embed sent successfully")
        return True  # Message sent successfully
    except requests.exceptions.RequestException as ex:
        print("Error sending Discord message: %s", ex)
        return False  # Failed to send the message


@retry(stop=stop_after_attempt(3))
def send_discord_message(message, webhook_url):
    """Send a message to a Discord channel using a webhook.
    Parameters:
        - message (str): The message content to send to Discord.
        - webhook_url (str): The URL of the Discord webhook to use for sending the message.
    Returns:
        - bool: True if the message was sent successfully, False otherwise.
    Processing Logic:
        - The function uses `requests.post` to send a message via a Discord webhook.
        - It raises an exception for non-2xx HTTP status codes to ensure the request was successful.
        - If an exception occurs during the request, it logs the error and returns False.
    """
    try:
        json_data = {"content": message}
        response = requests.post(webhook_url, json=json_data)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        return True  # Message sent successfully
    except requests.exceptions.RequestException as ex:
        print("Error sending Discord message: %s", ex)
        return False  # Failed to send the message


## BLIZZARD API CALLS ##
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
    """Fetches auction listings for a specific connected realm and region in the World of Warcraft game using the Blizzard API.
    Parameters:
        - connectedRealmId (int): Identifier for the connected realm to fetch auction data from.
        - access_token (str): Authorization token for accessing Blizzard API.
        - region (str): Region code for which the data is to be fetched ('NA' for North America, 'EU' for Europe).
    Returns:
        - list: A list of auction data dictionaries fetched from the specified realm and region.
    Processing Logic:
        - Constructs the API URL based on the region code.
        - Returns a message and exits if the region is unsupported.
        - Sends a GET request with authorization headers to fetch auction data."""
    print(f"gather data from connectedRealmId {connectedRealmId} of region {region}")
    if region == "NA":
        url = f"https://us.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}/auctions?namespace=dynamic-us&locale=en_US"
    elif region == "EU":
        url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}/auctions?namespace=dynamic-eu&locale=en_EU"
    else:
        print(
            f"{region} is not yet supported, reach out for us to add this region option"
        )
        exit(1)

    headers = {"Authorization": f"Bearer {access_token}"}

    req = requests.get(url, headers=headers, timeout=20)

    auction_info = req.json()
    return auction_info["auctions"]


def get_petnames(access_token):
    """Get a dictionary of pet IDs and names from the World of Warcraft API.
    Parameters:
        - access_token (str): An OAuth access token used for authentication in the API request.
    Returns:
        - dict: A dictionary where keys are pet IDs (int) and values are pet names (str).
    Processing Logic:
        - Sends a GET request to the World of Warcraft API using the provided access token for authorization.
        - Parses the JSON response to extract a list of pets.
        - Constructs and returns a dictionary mapping each pet's ID to its name."""
    headers = {"Authorization": f"Bearer {access_token}"}
    pet_info = requests.get(
        f"https://us.api.blizzard.com/data/wow/pet/index?namespace=static-us&locale=en_US",
        headers=headers,
    ).json()["pets"]
    pet_info = {int(pet["id"]): pet["name"] for pet in pet_info}
    return pet_info


## SADDLEBAG AND RAIDBOTS STATIC DATA CALLS ##

# # backup static backups url
# RAW_GITHUB_BACKUP_PATH = "https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/raw/refs/heads/1.2.5.2/StaticData"

# main static backups url
RAW_GITHUB_BACKUP_PATH = "https://raw.githubusercontent.com/ff14-advanced-market-search/AzerothAuctionAssassin/refs/heads/main/StaticData"
SADDLEBAG_URL = "https://api.saddlebagexchange.com"

WOW_DISCORD_CONSENT = (
    "I have gone to discord and asked the devs about this api and i know it only updates once per hour "
    "and will not spam the api like an idiot and there is no point in making more than one request per hour "
    "and i will not make request for one item at a time i know many apis support calling multiple items at once"
)


def get_update_timers_backup(REGION, NO_RUSSIAN_REALMS=True):
    """Get backup of update timers for a specific region, optionally excluding Russian realms.
    Parameters:
        - REGION (str): The region identifier for which update timers are retrieved.
        - NO_RUSSIAN_REALMS (bool, optional): Flag indicating whether to exclude Russian realms in the result. Defaults to True.
    Returns:
        - dict: A dictionary mapping dataSetID to update timer data for the specified region.
    Processing Logic:
        - Fetches update timers data via a POST request.
        - Filters out data with invalid dataSetID values (-1, -2) and matches the specified region.
        - Optionally filters out Russian realms from the result if NO_RUSSIAN_REALMS is True.
    """
    update_timers = requests.post(
        f"{SADDLEBAG_URL}/api/wow/uploadtimers",
        json={"discord_consent": WOW_DISCORD_CONSENT},
    ).json()["data"]
    server_update_times = {
        time_data["dataSetID"]: time_data
        for time_data in update_timers
        if time_data["dataSetID"] not in [-1, -2] and time_data["region"] == REGION
    }
    if NO_RUSSIAN_REALMS:
        russian_realm_ids = get_wow_russian_realm_ids()
        server_update_times = {
            k: v
            for k, v in server_update_times.items()
            if v["dataSetID"] not in russian_realm_ids
        }

    return server_update_times


def get_itemnames():
    """Get item names from a specified API or fallback to a GitHub backup.
    Returns:
        - list: A list of item names retrieved from the API or GitHub backup.
    Processing Logic:
        - Sends a POST request to a specified API endpoint to fetch item names.
        - If the request fails, it prints an error message and retrieves item names from a GitHub backup.
        - Returns the item names as a JSON object."""
    try:
        item_names = requests.post(
            f"{SADDLEBAG_URL}/api/wow/itemnames",
            json={"discord_consent": WOW_DISCORD_CONSENT, "return_all": True},
        ).json()
    except Exception as e:
        print(f"Failed to get item names getting backup from github: {e}")
        item_names = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/item_names.json").json()
    return item_names


def get_pet_names_backup():
    """Fetches pet names from a specified API endpoint or a backup source if the request fails.
    Returns:
        - dict: A dictionary mapping pet IDs to their names.
    Processing Logic:
        - Attempts to retrieve pet names from the primary API endpoint.
        - If the API request fails, fetches pet names from a GitHub backup source.
        - Converts the keys of the resulting dictionary to integers."""
    try:
        pet_info = requests.post(
            f"{SADDLEBAG_URL}/api/wow/itemnames",
            json={"discord_consent": WOW_DISCORD_CONSENT, "pets": True},
        ).json()
    except Exception as e:
        print(f"Failed to get pet names getting backup from github: {e}")
        pet_info = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/pet_names.json").json()
    pet_info = {int(k): v for k, v in pet_info.items()}
    return pet_info


RAIDBOTS_BASE = "https://www.raidbots.com/static/data/live"


def get_raidbots_bonus_ids():
    """Fetch bonus IDs from an external source and return them in a dictionary format.
    Returns:
        - dict: A dictionary of bonus IDs keyed by the ID converted to an integer, with corresponding data as values.
    Processing Logic:
        - Initial data is fetched from Raidbots API; if it fails, data is fetched from a GitHub backup.
        - Exceptions are caught and logged to indicate the fallback to the backup source.
        - The function ensures that keys in the returned dictionary are integers."""
    try:
        # thanks so much to Seriallos (Raidbots) and BinaryHabitat (GoblinStockAlerts) for organizing this data!
        bonus_ids = requests.get(f"{RAIDBOTS_BASE}/bonuses.json", timeout=10).json()
    except Exception as e:
        print(f"Failed to get raidbots bonus ids getting backup from github: {e}")
        bonus_ids = requests.get(
            f"{RAW_GITHUB_BACKUP_PATH}/bonuses.json", timeout=10
        ).json()
    return {int(id): data for id, data in bonus_ids.items()}


def _normalize_equippable_items(data):
    """Build lookup { item_id: { baseItemLevel } } from Raidbots array or dict."""
    if not data:
        return {}
    if isinstance(data, list):
        return {
            str(e["id"]): {"baseItemLevel": e.get("itemLevel")}
            for e in data
            if isinstance(e, dict) and "id" in e
        }
    return data


def get_raidbots_equippable_items():
    """Fetch equippable items (DBC base item level) from Raidbots for post-midnight ilvl resolver."""
    try:
        data = requests.get(f"{RAIDBOTS_BASE}/equippable-items.json", timeout=10).json()
        return _normalize_equippable_items(data)
    except Exception as e:
        print(f"Failed to get raidbots equippable-items: {e}")
        try:
            raw = requests.get(
                f"{RAW_GITHUB_BACKUP_PATH}/equippable-items.json", timeout=10
            ).json()
            return _normalize_equippable_items(raw)
        except Exception as e2:
            print(f"Fallback equippable-items not found: {e2}")
            return {}


def get_raidbots_item_curves():
    """Fetch item curves from Raidbots for post-midnight ilvl resolver."""
    try:
        data = requests.get(f"{RAIDBOTS_BASE}/item-curves.json", timeout=10).json()
        return data
    except Exception as e:
        print(f"Failed to get raidbots item-curves: {e}")
        try:
            return requests.get(
                f"{RAW_GITHUB_BACKUP_PATH}/item-curves.json", timeout=10
            ).json()
        except Exception as e2:
            print(f"Fallback item-curves not found: {e2}")
            return {}


def get_raidbots_item_squish_era():
    """Fetch item squish era list from Raidbots for post-midnight ilvl resolver."""
    try:
        data = requests.get(f"{RAIDBOTS_BASE}/item-squish-era.json", timeout=10).json()
        return data
    except Exception as e:
        print(f"Failed to get raidbots item-squish-era: {e}")
        try:
            return requests.get(
                f"{RAW_GITHUB_BACKUP_PATH}/item-squish-era.json", timeout=10
            ).json()
        except Exception as e2:
            print(f"Fallback item-squish-era not found: {e2}")
            return {}


def get_ilvl_items(ilvl=201, item_ids=[]):
    """Get item details based on the item level and item IDs provided.
    Parameters:
        - ilvl (int): The item level threshold for filtering items, default is 201.
        - item_ids (list): List of item IDs to filter; if empty or None, items are fetched based on ilvl only.
    Returns:
        - tuple: A tuple containing four elements:
            - dict: Item names keyed by item ID.
            - set: A set of item IDs.
            - dict: Base item levels keyed by item ID.
            - dict: Base required levels keyed by item ID.
    Processing Logic:
        - If item_ids is not provided or is empty, resets ilvl to 201.
        - Fetches item data from the Saddlebag URL, using a backup source if the request fails.
        - Filters results specifically for item IDs if given."""
    try:
        # if no item_ids are given, get all items at or above the given ilvl
        # this gets weird when someone wants a high ilvl item as we have the base ilvl in the DB
        # but not the max ilvl, so we just set it to 201
        if item_ids is None:
            item_ids = []
        if not item_ids:
            ilvl = 201
        json_data = {
            "discord_consent": WOW_DISCORD_CONSENT,
            "ilvl": ilvl,
            "itemQuality": -1,
            "required_level": -1,
            "item_class": [2, 4],
            "item_subclass": [-1],
            "item_ids": item_ids,
        }
        results = requests.post(
            f"{SADDLEBAG_URL}/api/wow/itemdata",
            json=json_data,
            timeout=10,
        ).json()
    except Exception as e:
        print(f"Failed to get ilvl items getting backup from github: {e}")
        results = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/ilvl_items.json").json()
    # if len(results) == 0:
    #     raise Exception(
    #         f"No items found at or above a base ilvl of {ilvl}, contact us on discord"
    #     )
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
    base_required_levels = {
        int(itemID): item_info["required_level"]
        for itemID, item_info in results.items()
    }
    return item_names, set(item_names.keys()), base_ilvls, base_required_levels
