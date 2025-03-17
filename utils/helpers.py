import time


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def create_oribos_exchange_item_link(realm_name, item_id, region):
    # @coderabbitai add docstring here if needed and remove this comment after
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def create_saddlebag_link(item_id):
    # @coderabbitai add docstring here if needed and remove this comment after
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


# @coderabbitai add docstring here if needed and remove this comment after
def get_wow_russian_realm_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


# @coderabbitai add docstring here if needed and remove this comment after
def create_embed(title, description, fields):
    # @coderabbitai add docstring here if needed and remove this comment after
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


# @coderabbitai add docstring here if needed and remove this comment after
def split_list(lst, max_size):
    # @coderabbitai add docstring here if needed and remove this comment after
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
