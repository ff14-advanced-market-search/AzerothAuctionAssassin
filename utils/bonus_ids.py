from utils.api_requests import get_raidbots_bonus_ids


def get_bonus_ids():
    """
    Get categorized bonus IDs from raidbot data.
    
    Retrieves and categorizes bonus IDs by analyzing attributes in raidbot data.
    Socket bonuses are identified from entries containing the 'socket' key, while
    item level additions are detected in entries whose only keys are 'id' and 'level'.
    Additional stats such as Leech, Avoidance, Speed, Haste, Crit, Mastery, and Versatility
    are extracted from the 'rawStats' field.
    
    Returns:
        dict: A dictionary with keys 'sockets', 'leech', 'avoidance', 'speed',
        'ilvl_addition', 'haste', 'crit', 'mastery', and 'versatility' mapping to their
        corresponding bonus IDs.
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


def get_bonus_id_sets():
    # get raw data
    """Return bonus ID sets categorized by type.
    
    Returns:
        tuple: A tuple containing a set of socket bonus IDs, a set of leech bonus IDs,
        a set of avoidance bonus IDs, a set of speed bonus IDs, and a list of item level bonus additions.
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


def get_secondary_stats():
    # get raw data
    """Extract secondary stat bonus IDs from categorized raidbot data.
    
    Retrieves bonus IDs using internal logic and collects keys for the secondary stats:
    'haste', 'crit', 'mastery', and 'versatility' into individual sets. Returns a tuple of these sets.
    
    Returns:
        tuple: A tuple of four sets corresponding to the bonus IDs for haste, crit, mastery, and versatility.
    """
    bonus_ids = get_bonus_ids()
    # get ids for each bonus type
    haste_ids = set(bonus_ids["haste"].keys())
    crit_ids = set(bonus_ids["crit"].keys())
    mastery_ids = set(bonus_ids["mastery"].keys())
    versatility_ids = set(bonus_ids["versatility"].keys())
    return haste_ids, crit_ids, mastery_ids, versatility_ids
