import time


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Constructs a pet link URL for the Oribos Exchange.
    
    This function normalizes the provided realm name by converting it to lowercase and replacing
    apostrophes and spaces with hyphens. It maps the region 'NA' to 'us' and all other values to 'eu',
    then constructs and returns the URL incorporating a fixed pet code along with the normalized realm
    name and pet identifier.
    
    Args:
        realm_name: The realm name to include in the URL.
        pet_id: The identifier of the pet.
        region: The region code; 'NA' maps to 'us', any other value maps to 'eu'.
    
    Returns:
        A URL string for the pet link on the Undermine Exchange.
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
    Creates a URL for an item on Undermine Exchange.
    
    This function converts the provided realm name to a URL-friendly format by lowercasing the text, removing apostrophes, and replacing spaces with hyphens. The region parameter determines the URL's region code: "NA" maps to "us" while any other value maps to "eu". The function returns a URL embedding the region code, formatted realm name, and item ID.
        
    Args:
        realm_name: The realm name which may include spaces or apostrophes.
        item_id: The identifier for the item.
        region: The region code used to determine URL prefix.
        
    Returns:
        A string representing the fully constructed item URL.
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
    Constructs a URL for the Saddlebag Exchange item link.
    
    Args:
        item_id: The unique identifier of the item.
    
    Returns:
        A string representing the URL to access the item's data on the Saddlebag Exchange.
    """
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def get_wow_russian_realm_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Retrieve a combined list of WOW Russian realm IDs.
    
    This function aggregates predefined realm IDs from retail, classic, and sod categories.
    
    Returns:
        list[int]: The aggregated list of realm IDs.
    """
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


# @coderabbitai add docstring here if needed and remove this comment after
def create_embed(title, description, fields):
    # @coderabbitai add docstring here if needed and remove this comment after
    """
    Creates a Discord embed message.
    
    Constructs and returns a dictionary representing a Discord embed with the given
    title, description, and fields. The embed is assigned a default blurple color 
    (0x7289DA) and includes the current local time in the footer.
    
    Args:
        title (str): The embed's title.
        description (str): The embed's description.
        fields (list): A list of dictionaries, each representing an embed field.
    
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
    Splits a list into smaller sublists of a specified maximum size.
    
    Divides the input list into consecutive sublists where each contains up to max_size elements,
    preserving the original order. Returns a list of these sublists.
    """
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
