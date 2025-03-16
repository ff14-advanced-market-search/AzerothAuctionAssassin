import requests
from tenacity import retry, stop_after_attempt
from utils.helpers import get_wow_russian_realm_ids


## DISCORD API CALLS ##
def send_embed_discord(embed, webhook_url):
    # Send message
    """
    Send an embed message to Discord using a webhook URL.
    
    Sends an HTTP POST request with the given embed data to the provided Discord 
    webhook. Returns True if the request is successful (HTTP status 200 or 204), 
    and False if an error occurs.
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
    Send a plain text message to a Discord channel via a webhook.
    
    Attempts an HTTP POST request to the provided Discord webhook URL with the given message.
    Returns True if the request is successful; otherwise, prints an error message and returns False.
    
    Args:
        message (str): The message to send.
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
    access_token = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    ).json()["access_token"]
    return access_token


@retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
def get_listings_single(connectedRealmId: int, access_token: str, region: str):
    """
    Fetch auction listings for a given connected realm and region.
    
    Constructs the appropriate Blizzard API URL based on the specified region ('NA' or 'EU') 
    and retrieves auction listings using the provided access token. If an unsupported region 
    is specified, an error message is printed and the program terminates.
    
    Parameters:
        connectedRealmId (int): The ID of the connected realm.
        access_token (str): Blizzard API access token for authorization.
        region (str): Region code determining the API endpoint ('NA' for North America, 'EU' for Europe).
    
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
    """Retrieve a mapping of pet IDs to names from the World of Warcraft API.
    
    Uses the provided OAuth access token to fetch pet data from Blizzard's API and
    returns a dictionary mapping each pet's numeric ID to its corresponding name.
    
    Args:
        access_token (str): OAuth token used to authenticate the API request.
    
    Returns:
        dict: A dictionary with pet IDs (int) as keys and pet names (str) as values.
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
    Fetch backup update timers for a specified region.
    
    Retrieves update timer data from an external service and filters out entries with
    invalid dataset IDs. If NO_RUSSIAN_REALMS is True, data for Russian realms is omitted.
    
    Args:
        REGION (str): The region identifier for which update timers are fetched.
        NO_RUSSIAN_REALMS (bool, optional): Flag to exclude Russian realm data. Defaults to True.
    
    Returns:
        dict: A dictionary mapping valid dataSetID values to corresponding update timer data.
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
    Retrieves item names from an API endpoint with a GitHub backup fallback.
    
    Attempts a POST request to obtain item names. If the request fails, prints an error message and retrieves the names via a GET request from a GitHub backup.
    
    Returns:
        list: The list of item names.
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
    Retrieves pet names from the primary API with a backup fallback.
    
    This function sends a POST request to obtain a dictionary mapping pet IDs to names.
    If the request fails, it retrieves the data from a GitHub backup via a GET request.
    The keys of the returned dictionary are converted to integers.
    
    Returns:
        dict: A mapping from pet IDs (as integers) to their names.
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
    Retrieve bonus IDs from the Raidbots API with a GitHub backup fallback.
    
    This function attempts to fetch bonus IDs by sending a GET request to the Raidbots API and converts the keys 
    of the JSON response to integers. If the API request fails, it prints an error message and retrieves the data 
    from a GitHub backup instead.
    
    Returns:
        dict: A dictionary mapping bonus IDs (as integers) to their associated data.
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
    Retrieve detailed information for items based on a base item level and an optional list of item IDs.
    
    When no item IDs are provided (or the list is empty), the function resets the item level filter to 201
    and retrieves all items meeting this default threshold. Data is fetched from the primary Saddlebag API,
    falling back to a GitHub backup on failure.
    
    Args:
        ilvl (int): The item level threshold for filtering items. This value is ignored if a list of item IDs is provided.
        item_ids (list): Optional list of item IDs to filter; if empty or None, items are retrieved based on the default item level.
    
    Returns:
        tuple: A four-element tuple containing:
            - dict: Mapping of item IDs (int) to item names (str).
            - set: Set of item IDs (int).
            - dict: Mapping of item IDs (int) to base item levels.
            - dict: Mapping of item IDs (int) to base required levels.
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
