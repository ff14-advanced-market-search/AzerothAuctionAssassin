import time


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Generates a pet link URL for the Undermine Exchange.
    
    This function constructs a URL for accessing a pet's details on the Undermine Exchange by processing the given realm name and pet ID. The realm name is normalized by converting to lowercase, removing apostrophes, and replacing spaces with hyphens. Depending on the region, the URL region is set to "us" for "NA" and "eu" for any other value.
    
    Args:
        realm_name (str): The name of the realm.
        pet_id (int or str): The identifier of the pet.
        region (str): The region code, typically "NA" for North America or another value for Europe.
    
    Returns:
        str: A formatted URL string pointing to the pet's details on the Undermine Exchange.
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
    Creates a URL for an Undermine Exchange item link.
    
    Formats the provided realm name into a slug by converting it to lowercase and replacing apostrophes and spaces with hyphens.
    Depending on the region parameter ("NA" maps to "us" and any other value to "eu"), it constructs and returns a formatted URL that includes the processed realm name and item ID.
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
    Constructs a URL for accessing item data on the Saddlebag Exchange.
    
    Args:
        item_id: The identifier of the item to look up.
    
    Returns:
        A URL string pointing to the Saddlebag Exchange page for the specified item.
    """
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def get_wow_russian_realm_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Returns a list of World of Warcraft realm IDs.
    
    Combines predefined lists for retail, classic, and sod realms into a single list.
    
    Returns:
        List[int]: A concatenated list of realm IDs.
    """
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


# @coderabbitai add docstring here if needed and remove this comment after
def create_embed(title, description, fields):
    # @coderabbitai add docstring here if needed and remove this comment after
    """Create a Discord embed object.
    
    Constructs a Discord embed with the specified title, description, and fields.
    The embed uses a default blurple color and includes a footer with the current local time.
    
    Args:
        title (str): The embed title.
        description (str): The embed description.
        fields (list): A list of dictionaries representing embed fields, each with 'name' and 'value' keys.
    
    Returns:
        dict: A dictionary representing the Discord embed.
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
    Splits the input list into sublists of a specified maximum size.
    
    Divides the provided list into chunks where each sublist contains at most max_size elements.
    If the list length is not an exact multiple of max_size, the final chunk may contain fewer elements.
    
    Args:
        lst: The list to split.
        max_size: The maximum number of elements for each sublist.
    
    Returns:
        A list of sublists derived from the original list.
    """
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
