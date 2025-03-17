import time


def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    """
    Constructs a pet link URL for the Undermine Exchange.

    Normalizes the realm name by converting it to lowercase and replacing apostrophes
    and spaces with hyphens. Uses the URL region "us" when the provided region is "NA",
    and "eu" otherwise. Incorporates the pet ID with a constant prefix "82800" to form
    the final URL.

    Args:
        realm_name: The name of the realm to be normalized.
        pet_id: The identifier of the pet.
        region: The region code, where "NA" maps to "us" and any other value maps to "eu".

    Returns:
        A string representing the formatted pet link URL.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


def create_oribos_exchange_item_link(realm_name, item_id, region):
    """
    Constructs a URL for an item link on the Undermine Exchange.

    Normalizes the realm name by converting it to lowercase and replacing apostrophes and spaces with hyphens. Maps the provided region to "us" when it is "NA" or to "eu" for any other value, and returns the resulting URL string.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


def create_saddlebag_link(item_id):
    """
    Constructs a URL for accessing item data on the Saddlebag Exchange.

    Args:
        item_id: The unique identifier for the item.

    Returns:
        A formatted URL string pointing to the Saddlebag Exchange item data.
    """
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


def get_wow_russian_realm_ids():
    """
    Return a list of Russian realm IDs for World of Warcraft.

    Aggregates predefined realm IDs from retail, classic, and Shadowlands categories into a single list.
    """
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


def create_embed(title, description, fields):
    """
    Creates a Discord embed with a title, description, and fields.

    The embed defaults to a blurple color and includes the current local time in its footer.
    The fields should be provided as a list of dictionaries, each defining a field with keys like 'name' and 'value'.

    Args:
        title (str): The title of the embed.
        description (str): The description text of the embed.
        fields (list): A list of dictionaries representing the embed fields.

    Returns:
        dict: A dictionary structured as a Discord embed object.
    """
    embed = {
        "title": title,
        "description": description,
        "color": 0x7289DA,  # Blurple color code
        "fields": fields,
        "footer": {
            "text": time.strftime(
                "%m/%d/%Y %I:%M %p", time.localtime()
            )  # Adds current time as footer
        },
    }
    return embed


def split_list(lst, max_size):
    """
    Splits a list into smaller sublists of a specified maximum size.

    This function divides the input list into consecutive sublists, each containing up to max_size elements.

    Args:
        lst: The list to be split.
        max_size: The maximum number of elements each sublist may contain.

    Returns:
        A list of sublists, where each sublist has a length not exceeding max_size.
    """
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
