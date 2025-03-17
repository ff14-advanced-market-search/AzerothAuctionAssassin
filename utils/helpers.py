import time


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Constructs a pet link URL for Oribos Exchange.
    
    Formats the realm name by converting it to lowercase, removing apostrophes, and replacing spaces with hyphens.
    Selects a region identifier based on the provided region ("NA" maps to "us"; otherwise "eu") and embeds it along with
    the pet ID into a URL for referencing the pet on Undermine Exchange.
    
    Parameters:
        realm_name: The name of the realm to format.
        pet_id: The identifier of the pet.
        region: A region code that influences the URL formation ("NA" for North America, others default to European).
    
    Returns:
        A string containing the formatted pet link URL.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_item_link(realm_name, item_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Constructs an Oribos Exchange item URL.
    
    Formats the given realm name by converting it to lowercase, removing apostrophes, and replacing spaces with hyphens. Depending on the region, it assigns "us" for NA and "eu" for other regions, then returns the URL constructed with the formatted realm name and item ID.
    
    Args:
        realm_name (str): The name of the realm.
        item_id (str or int): The identifier of the item.
        region (str): The region code; "NA" maps to "us", others to "eu".
    
    Returns:
        str: The complete URL for the item on Oribos Exchange.
    """
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def create_saddlebag_link(item_id):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Generates a Saddlebag item link URL for the given item ID.
    
    Args:
        item_id: The unique identifier for the item.
    
    Returns:
        A URL string pointing to the Saddlebag item data.
    """
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def get_wow_russian_realm_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Returns a combined list of Russian World of Warcraft realm IDs.
    
    This function aggregates IDs from retail, classic, and sod realms.
    """
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


# @coderabbitai add docstring here if needed and remove this comment after
def create_embed(title, description, fields):
    # @coderabbitai add docstring here if needed and remove this comment after
    """Creates a Discord embed.
    
    Constructs a dictionary representing a Discord embed with the specified title,
    description, and fields. The embed is assigned a default blurple color and includes
    the current local time as its footer.
    
    Args:
        title (str): The title of the embed.
        description (str): The description text of the embed.
        fields (list): A list of dictionaries representing embed fields, each containing a
            field's name and value.
    
    Returns:
        dict: The Discord embed object.
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


# @coderabbitai add docstring here if needed and remove this comment after
def split_list(lst, max_size):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Splits a list into sublists each containing at most max_size elements.
    
    Args:
        lst: The list to split.
        max_size: The maximum number of elements allowed in each sublist.
    
    Returns:
        A list of sublists, where each sublist has up to max_size elements.
    """
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
