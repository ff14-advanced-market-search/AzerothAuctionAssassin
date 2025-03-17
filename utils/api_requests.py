import requests
from tenacity import retry, stop_after_attempt
from utils.helpers import get_wow_russian_realm_ids


## DISCORD API CALLS ##
def send_embed_discord(embed, webhook_url):
    # Send message
    """Sends an embed message to a Discord webhook URL.

    Sends the given embed content as a JSON payload via a POST request to the specified
    Discord webhook URL. Returns True if the embed is sent successfully (HTTP status 200 or 204),
    or False if a request error occurs.

    Args:
        embed (dict): The embed content to include in the message.
        webhook_url (str): The Discord webhook URL to send the embed to.

    Returns:
        bool: True if the embed is sent successfully, False otherwise.
    """
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
    """
    Sends a message to a Discord channel via a webhook.

    Args:
        message (str): The content of the message.
        webhook_url (str): The Discord webhook URL.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
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
    """
    Fetches an OAuth access token from the Blizzard API.

    This function sends a POST request to Blizzard's Battle.net OAuth token endpoint using the
    provided client credentials. It returns the access token as a string for use in authenticating
    subsequent API requests.

    Args:
        client_id: The Blizzard API client identifier.
        client_secret: The Blizzard API client secret.

    Returns:
        The access token as a string.
    """
    access_token = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    ).json()["access_token"]
    return access_token


@retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
def get_listings_single(connectedRealmId: int, access_token: str, region: str):
    """
    Fetches auction listings for a connected realm in a specified region.

    Retrieves auction data from Blizzard's World of Warcraft API for the given
    connected realm and region. Supported region codes are "NA" and "EU". If the
    region is unsupported, the function prints a notification and terminates the
    program.

    Parameters:
        connectedRealmId (int): Identifier for the connected realm.
        access_token (str): Blizzard API OAuth access token.
        region (str): Region code ("NA" for North America or "EU" for Europe).

    Returns:
        list: A list of auction data dictionaries.
    """
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
    """Fetch a mapping of World of Warcraft pet IDs to their names.

    Retrieves pet data from the Blizzard World of Warcraft API using the provided OAuth access token.
    Returns a dictionary where each key is a pet ID (int) and each value is the corresponding pet name (str).

    Args:
        access_token: An OAuth access token used for authenticating the API request.
    """
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
SADDLEBAG_URL = "http://api.saddlebagexchange.com"


def get_update_timers_backup(REGION, NO_RUSSIAN_REALMS=True):
    """
    Retrieves backup update timers for a specified region.

    This function fetches update timer data from an external API and filters the results to include only those
    timers that match the provided region and have valid dataSetID values. If enabled, it further excludes
    timers for Russian realms.

    Args:
        REGION (str): The region identifier for which timers are retrieved.
        NO_RUSSIAN_REALMS (bool, optional): If True, excludes timers associated with Russian realms. Defaults to True.

    Returns:
        dict: A mapping of valid dataSetID values to their corresponding update timer data.
    """
    update_timers = requests.post(
        f"{SADDLEBAG_URL}/api/wow/uploadtimers",
        json={},
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
    """
    Retrieves a list of item names from the primary API, falling back to a backup source if necessary.

    This function attempts to fetch item names by sending a POST request to the primary API endpoint. If an exception occurs during the request, it prints an error message and retrieves the item names from a GitHub backup.

    Returns:
        list: A list of item names.
    """
    try:
        item_names = requests.post(
            f"{SADDLEBAG_URL}/api/wow/itemnames",
            json={"return_all": True},
        ).json()
    except Exception as e:
        print(f"Failed to get item names getting backup from github: {e}")
        item_names = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/item_names.json").json()
    return item_names


def get_pet_names_backup():
    """
    Retrieve pet names from the primary API or a GitHub backup.

    This function sends a POST request with a JSON payload to obtain pet names. If the request fails,
    it falls back to retrieving the data from a GitHub backup. The resulting dictionary is processed to
    convert its keys to integers.

    Returns:
        dict: A mapping of pet IDs (integers) to their corresponding names.
    """
    try:
        pet_info = requests.post(
            f"{SADDLEBAG_URL}/api/wow/itemnames",
            json={"pets": True},
        ).json()
    except Exception as e:
        print(f"Failed to get pet names getting backup from github: {e}")
        pet_info = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/pet_names.json").json()
    pet_info = {int(k): v for k, v in pet_info.items()}
    return pet_info


def get_raidbots_bonus_ids():
    """
    Fetch bonus IDs from the Raidbots API and return them as a dictionary.

    Returns:
        dict: A dictionary mapping bonus IDs (as integers) to their corresponding data.

    If the primary API request fails, a backup source is used to retrieve the data.
    """
    try:
        # thanks so much to Seriallos (Raidbots) and BinaryHabitat (GoblinStockAlerts) for organizing this data!
        bonus_ids = requests.get(
            "https://www.raidbots.com/static/data/live/bonuses.json"
        ).json()
    except Exception as e:
        print(f"Failed to get raidbots bonus ids getting backup from github: {e}")
        bonus_ids = requests.get(f"{RAW_GITHUB_BACKUP_PATH}/bonuses.json").json()
    return {int(id): data for id, data in bonus_ids.items()}


def get_ilvl_items(ilvl=201, item_ids=[]):
    """
    Retrieves item details based on item level and optional item IDs.

    This function fetches World of Warcraft item data from a primary API endpoint using the specified item level
    and an optional list of item IDs for filtering. If no item IDs are provided, the item level is reset to 201, ensuring
    a default query is executed. On failure to retrieve data from the primary source, a backup source is used.

    Args:
        ilvl (int, optional): Threshold for filtering items by level. When no item IDs are provided, this is overridden to 201.
            Defaults to 201.
        item_ids (list, optional): List of item IDs to filter the results. If empty or None, filtering is based solely on the item level.

    Returns:
        tuple: A four-element tuple containing:
            - dict: Mapping of item IDs (int) to item names (str).
            - set: Set of item IDs (int) present in the result.
            - dict: Mapping of item IDs (int) to their base item levels.
            - dict: Mapping of item IDs (int) to their required levels.
    """
    try:
        # if no item_ids are given, get all items at or above the given ilvl
        # this gets weird when someone wants a high ilvl item as we have the base ilvl in the DB
        # but not the max ilvl, so we just set it to 201
        if item_ids is None:
            item_ids = []
        if not item_ids:
            ilvl = 201
        json_data = {
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
