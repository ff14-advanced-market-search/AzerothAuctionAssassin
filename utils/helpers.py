import time


# add docstring here if needed
def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    """
    Generates a URL for a pet link on the Undermine Exchange.
    
    This function converts the given realm name to a URL-friendly format by converting it
    to lowercase and replacing apostrophes and spaces with hyphens. It selects a region
    prefix based on the provided region ("us" for "NA", and "eu" otherwise) and embeds
    the given pet ID into the URL.
    
    Args:
        realm_name: The name of the realm used in the URL.
        pet_id: The identifier for the pet.
        region: A string indicating the region; "NA" results in a US prefix.
        
    Returns:
        A formatted URL string linking to the pet's page on the Undermine Exchange.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


# add docstring here if needed
def create_oribos_exchange_item_link(realm_name, item_id, region):
    """
    Generates a URL for an Undermine Exchange item link.
    
    Formats the provided realm name by converting it to lowercase, removing apostrophes, and replacing spaces with hyphens. Determines the URL region code based on the region parameter ("us" for "NA", "eu" for all other values) and returns a URL string incorporating the formatted realm name and item ID.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


# add docstring here if needed
def create_saddlebag_link(item_id):
    """
    Construct a Saddlebag Exchange item URL.
    
    Builds and returns a URL string for accessing item data on the Saddlebag Exchange
    using the specified item ID.
    
    Args:
        item_id: The unique identifier for the item.
    
    Returns:
        str: The formatted URL string that includes the provided item ID.
    """
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


# add docstring here if needed
def get_wow_russian_realm_ids():
    """
    Returns a list of World of Warcraft Russian realm IDs.
    
    Combines predefined lists of realm IDs for retail, classic, and Shadowlands realms into a
    single aggregated list.
    """
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


# add docstring here if needed
def create_embed(title, description, fields):
    """Create a Discord embed with specified title, description, and fields.
    Parameters:
        - title (str): The title of the embed message.
        - description (str): The description content of the embed message.
        - fields (list): A list of dictionaries, each representing a field with name and value.
    Returns:
        - dict: A dictionary representing the Discord embed object.
    Processing Logic:
        - Uses a default blurple color code for the embed.
        - Adds the current local time as a footer in the embed."""
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


# add docstring here if needed
def split_list(lst, max_size):
    """
    Splits a list into smaller sublists.
    
    Divides the input list into consecutive chunks, each containing up to max_size elements.
    The final chunk may contain fewer elements if the total count is not a multiple of max_size.
    
    Args:
        lst: The list to be split.
        max_size: The maximum number of elements allowed in each sublist.
    
    Returns:
        A list of sublists, each with at most max_size elements.
    """
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
