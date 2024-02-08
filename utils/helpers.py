def create_oribos_exchange_pet_link(realm_name, pet_id, region):
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://oribos.exchange/#{url_region}-{fixed_realm_name}/82800-{pet_id}"


def create_oribos_exchange_item_link(realm_name, item_id, region):
    fixed_realm_name = realm_name.lower().replace("'", "").replace(" ", "-")
    if region == "NA":
        url_region = "us"
    else:
        url_region = "eu"
    return f"https://oribos.exchange/#{url_region}-{fixed_realm_name}/{item_id}"


def get_wow_russian_realm_ids():
    retail_realms = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922]
    classic_realms = [4452, 4474]
    sod_realms = [5280, 5285, 5829, 5830]
    return retail_realms + classic_realms + sod_realms
