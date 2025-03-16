import time


def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


def create_oribos_exchange_item_link(realm_name, item_id, region):
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://undermine.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


def create_saddlebag_link(item_id):
    return f"https://saddlebagexchange.com/wow/item-data/{item_id}"


def get_wow_russian_realm_ids():
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms


def create_embed(title, description, fields):
    """Create a Discord embed object.
    
    Creates and returns a dictionary representing a Discord embed with the given title,
    description, and fields. The embed features a default blurple color and includes the
    current local time as its footer.
    
    Parameters:
        title (str): The embed's title.
        description (str): The embed's description.
        fields (list): A list of dictionaries where each dictionary defines a field with
            a name and corresponding value.
    
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


def split_list(lst, max_size):
    return [lst[i : i + max_size] for i in range(0, len(lst), max_size)]
