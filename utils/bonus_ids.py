from utils.api_requests import get_raidbots_bonus_ids


# add docstring here if needed
def get_bonus_ids():
    """Categorize bonus IDs from raidbot data into predefined groups.
    
    Retrieves bonus ID entries and organizes them into categories such as sockets, leech,
    avoidance, speed, item level additions, haste, crit, mastery, and versatility based on
    their attributes. Returns a dictionary mapping each category to its corresponding bonus IDs.
    """
    bonus_id_dict = get_raidbots_bonus_ids()
    # sockets are simple
    sockets = {k: v for k, v in bonus_id_dict.items() if "socket" in v.keys()}

    # maybe do this in the future, we can rely on the saddlebag api for now
    # base_level = {k: v["base_level"] for k, v in bonus_id_dict.items() if "base_level" in v.keys()}

    # should be the ilvl added to the items base level
    ilvl_addition = {
        k: v["level"]
        for k, v in bonus_id_dict.items()
        if list(v.keys()) == ["id", "level"]
    }

    # the rest are buried in rawStats
    leech, avoidance, speed = {}, {}, {}
    haste, crit, mastery, versatility = {}, {}, {}, {}
    for k, v in bonus_id_dict.items():
        if "rawStats" in v.keys():
            for stats in v["rawStats"]:
                if "Leech" in stats.values():
                    leech[k] = v
                if "Avoidance" in stats.values():
                    avoidance[k] = v
                if "RunSpeed" in stats.values():
                    speed[k] = v
                if "Haste" in stats.values():
                    haste[k] = v
                if "Crit" in stats.values():
                    crit[k] = v
                if "Mastery" in stats.values():
                    mastery[k] = v
                if "Versatility" in stats.values():
                    versatility[k] = v
    return {
        "sockets": sockets,
        "leech": leech,
        "avoidance": avoidance,
        "speed": speed,
        "ilvl_addition": ilvl_addition,
        # "ilvl_base": base_level,
        "haste": haste,
        "crit": crit,
        "mastery": mastery,
        "versatility": versatility,
    }


# add docstring here if needed
def get_bonus_id_sets():
    # get raw data
    """Get sets of bonus IDs categorized by type.
    
    Returns:
        tuple: A tuple containing:
            - A set of bonus IDs for sockets.
            - A set of bonus IDs for leech.
            - A set of bonus IDs for avoidance.
            - A set of bonus IDs for speed.
            - A list of item level additions.
    """
    bonus_ids = get_bonus_ids()
    # get ids for each bonus type
    socket_ids = set(bonus_ids["sockets"].keys())
    leech_ids = set(bonus_ids["leech"].keys())
    avoidance_ids = set(bonus_ids["avoidance"].keys())
    speed_ids = set(bonus_ids["speed"].keys())
    return (
        socket_ids,
        leech_ids,
        avoidance_ids,
        speed_ids,
        bonus_ids["ilvl_addition"],
    )  # , bonus_ids["ilvl_base"]


# add docstring here if needed
def get_secondary_stats():
    # get raw data
    """
    Extract secondary stat bonus IDs.
    
    This function retrieves bonus IDs and returns four sets corresponding to the
    secondary stats: haste, crit, mastery, and versatility.
    
    Returns:
        tuple: A tuple containing four sets in the order (haste, crit, mastery, versatility).
    """
    bonus_ids = get_bonus_ids()
    # get ids for each bonus type
    haste_ids = set(bonus_ids["haste"].keys())
    crit_ids = set(bonus_ids["crit"].keys())
    mastery_ids = set(bonus_ids["mastery"].keys())
    versatility_ids = set(bonus_ids["versatility"].keys())
    return haste_ids, crit_ids, mastery_ids, versatility_ids
