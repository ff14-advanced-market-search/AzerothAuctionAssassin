import requests
from tenacity import retry, stop_after_attempt
from utils.helpers import get_wow_russian_realm_ids


## DISCORD API CALLS ##
# @coderabbitai add docstring here if needed and remove this comment after
def send_embed_discord(embed, webhook_url):
    # @coderabbitai add docstring here if needed and remove this comment after
    # Send message
    """Send an embed message to a Discord webhook.
    
    Attempts to post the specified embed to the provided webhook URL and returns a boolean
    indicating success. On failure, the function handles request exceptions and returns False.
    
    Parameters:
        embed (dict): A dictionary containing the embed data.
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
# @coderabbitai add docstring here if needed and remove this comment after
def send_discord_message(message, webhook_url):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Sends a plain text message to a Discord channel via a webhook.
    
    Args:
        message (str): The text content to send.
        webhook_url (str): The Discord webhook URL.
    
    Returns:
        bool: True if the message was sent successfully; otherwise, False.
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
# @coderabbitai add docstring here if needed and remove this comment after
def get_wow_access_token(client_id, client_secret):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieves an OAuth access token from Blizzard API.
    
    Sends a POST request to Blizzard's OAuth token endpoint with the provided client
    credentials and returns the access token extracted from the JSON response.
    
    Args:
        client_id: Blizzard API client identifier.
        client_secret: Blizzard API client secret.
    
    Returns:
        The OAuth access token as a string.
    """
    access_token = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    ).json()["access_token"]
    return access_token


@retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
# @coderabbitai add docstring here if needed and remove this comment after
def get_listings_single(connectedRealmId: int, access_token: str, region: str):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Fetch auction listings for a connected realm and region.
    
    This function retrieves auction data from the Blizzard API using the provided
    connected realm ID, access token, and region. Supported regions are 'NA' and
    'EU'. If an unsupported region is provided, an error is printed and the process
    terminates.
    
    Parameters:
        connectedRealmId (int): The ID of the connected realm.
        access_token (str): Blizzard API OAuth access token.
        region (str): The region code ('NA' for North America, 'EU' for Europe).
    
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_petnames(access_token):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieves a mapping of pet IDs to pet names from the World of Warcraft API.
    
    Parameters:
        access_token (str): OAuth access token for API authentication.
    
    Returns:
        dict: A dictionary mapping pet IDs (int) to their corresponding names (str).
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_update_timers_backup(REGION, NO_RUSSIAN_REALMS=True):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieve backup update timers for the specified region.
    
    This function retrieves update timer data from an external source and filters out invalid entries
    and those not matching the specified region. If NO_RUSSIAN_REALMS is True, Russian realms are omitted
    from the results.
    
    Args:
        REGION (str): The region identifier used to filter update timers.
        NO_RUSSIAN_REALMS (bool, optional): Flag to exclude Russian realms. Defaults to True.
    
    Returns:
        dict: A mapping of dataSetID to update timer information for the specified region.
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_itemnames():
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieve item names from the main API or a GitHub backup.
    
    This function sends a POST request to fetch item names from the primary API. If the request fails,
    it prints an error message and retrieves the names from a GitHub backup.
    
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_pet_names_backup():
    # @coderabbitai add docstring here if needed and remove this comment after
    """Retrieve pet names with a fallback to backup data.
    
    Attempts to fetch pet names from the primary API endpoint; if that fails, retrieves
    the data from a GitHub backup. The returned dictionary maps pet IDs (converted to integers)
    to their corresponding names.
    
    Returns:
        dict: A mapping of pet IDs (int) to pet names (str).
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_raidbots_bonus_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Fetch bonus IDs from Raidbots and return them as a dictionary.
    
    Attempts to retrieve bonus data from the Raidbots API and falls back to a GitHub backup on failure.
    The returned dictionary maps bonus IDs (as integers) to their corresponding data.
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_ilvl_items(ilvl=201, item_ids=[]):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieve item details for a given item level and optional list of item IDs.
    
    If no item IDs are specified, the function resets the item level threshold to 201 and
    retrieves all items meeting that criterion. It first attempts to fetch data from the primary
    source and, on failure, falls back to a backup source.
    
    Args:
        ilvl (int, optional): Minimum item level for filtering items (default is 201).
        item_ids (list, optional): List of item IDs to filter by. If empty or None, filtering is
            based solely on the item level.
    
    Returns:
        tuple: A tuple containing:
            - dict: Mapping of item IDs to their item names.
            - set: Set of item IDs.
            - dict: Mapping of item IDs to their base item levels.
            - dict: Mapping of item IDs to their required levels.
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
