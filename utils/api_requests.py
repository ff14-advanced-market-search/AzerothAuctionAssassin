import requests
from tenacity import retry, stop_after_attempt
from utils.helpers import get_wow_russian_realm_ids


## DISCORD API CALLS ##
# add docstring here if needed
def send_embed_discord(embed, webhook_url):
    # Send message
    """Send an embed message to a Discord channel via a webhook.
    
    Parameters:
        embed (dict): The embed payload as a dictionary.
        webhook_url (str): The Discord webhook URL where the embed will be sent.
    
    Returns:
        bool: True if the embed is sent successfully; False if an error occurs.
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
# add docstring here if needed
def send_discord_message(message, webhook_url):
    """Send a plain text message to Discord via a webhook.
    
    Sends the provided message to the Discord webhook at the specified URL.
    Returns True if the message is sent successfully; otherwise, returns False.
    
    Args:
        message: The text message to send.
        webhook_url: The Discord webhook URL.
    
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
# add docstring here if needed
def get_wow_access_token(client_id, client_secret):
    """
    Retrieves a World of Warcraft access token from the Blizzard API.
    
    This function authenticates with Blizzard's OAuth service using the provided
    client credentials and returns the access token extracted from the JSON response.
    
    Parameters:
        client_id: Blizzard API client identifier.
        client_secret: Blizzard API client secret.
    
    Returns:
        str: The access token.
    """
    access_token = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    ).json()["access_token"]
    return access_token


@retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
# add docstring here if needed
def get_listings_single(connectedRealmId: int, access_token: str, region: str):
    """
    Fetches auction listings for a connected realm and region.
    
    Retrieves auction data from the Blizzard API for the specified connected realm
    and region. Supported regions are 'NA' (North America) and 'EU' (Europe). If an
    unsupported region is provided, the function prints an error message and exits
    the process.
    
    Args:
        connectedRealmId: The identifier of the connected realm.
        access_token: Blizzard API authorization token.
        region: Region code ('NA' or 'EU') indicating which region's data to fetch.
    
    Returns:
        A list of auction data dictionaries.
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


# add docstring here if needed
def get_petnames(access_token):
    """Retrieve pet IDs and names from the World of Warcraft API.
    
    Parameters:
        access_token (str): OAuth token for API authentication.
    
    Returns:
        dict: A mapping of pet IDs (int) to pet names (str).
    
    Processing Logic:
        Sends a GET request to the WoW API to obtain pet data, extracts the pet list from the JSON response,
        and constructs a dictionary mapping each pet's ID to its name.
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


# add docstring here if needed
def get_update_timers_backup(REGION, NO_RUSSIAN_REALMS=True):
    """
    Fetch backup update timer data for a region.
    
    Retrieves update timer data from a backup source and returns a dictionary of valid timer entries filtered by region. Optionally excludes Russian realm data when specified.
    
    Parameters:
        REGION (str): The region identifier.
        NO_RUSSIAN_REALMS (bool, optional): If True, excludes Russian realm entries. Defaults to True.
    
    Returns:
        dict: A mapping of dataSetID to update timer data for the specified region.
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


# add docstring here if needed
def get_itemnames():
    """
    Retrieves item names from a primary API, falling back to a GitHub backup if necessary.
    
    This function attempts to fetch item names by sending a POST request to the primary API endpoint.
    If the request fails, it prints an error message and retrieves the item names from a backup GitHub URL.
    Returns a list of item names as obtained from the API or backup.
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


# add docstring here if needed
def get_pet_names_backup():
    """
    Retrieve pet names from the API, falling back to a backup on failure.
    
    This function attempts to retrieve pet names from the primary API endpoint. If the
    request fails, it fetches the names from a backup JSON file hosted on GitHub. The pet ID
    keys are converted to integers before returning a dictionary mapping pet IDs to names.
    
    Returns:
        dict: A dictionary mapping pet IDs (as integers) to their corresponding names.
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


# add docstring here if needed
def get_raidbots_bonus_ids():
    """
    Fetch bonus IDs from the Raidbots API with a backup mechanism.
    
    This function retrieves bonus ID data from the Raidbots API. If the request fails, it falls back to fetching the data from a GitHub backup. The returned dictionary maps each bonus ID, converted to an integer, to its corresponding information.
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


# add docstring here if needed
def get_ilvl_items(ilvl=201, item_ids=[]):
    """
    Retrieve World of Warcraft item details using an item level threshold and optional ID filters.
    
    If no item IDs are provided (or if the list is empty), the function defaults the base
    item level to 201. It fetches item data via an HTTP POST request to an external service,
    falling back to a backup source on failure. When specific item IDs are provided, the results
    are filtered accordingly.
    
    Args:
        ilvl (int): The item level threshold for filtering items. This value is reset to 201 when
            no specific item IDs are supplied.
        item_ids (list): Optional list of item IDs to filter the results.
    
    Returns:
        tuple: A tuple containing:
            - dict: A mapping of item IDs (int) to item names (str).
            - set: A set of item IDs.
            - dict: A mapping of item IDs (int) to their base item levels (int).
            - dict: A mapping of item IDs (int) to their required levels (int).
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
