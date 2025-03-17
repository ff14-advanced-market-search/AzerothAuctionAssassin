from utils.api_requests import get_raidbots_bonus_ids


# @coderabbitai add docstring here if needed and remove this comment after
def get_bonus_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """Retrieve and categorize bonus IDs from raidbot data.
    
    This function obtains bonus ID data from raidbot and organizes it into categories based
    on attributes such as sockets, leech, avoidance, speed, item level additions, haste, crit,
    mastery, and versatility.
    
    Returns:
        dict: A dictionary with bonus category names as keys and their corresponding bonus
        IDs as values.
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_bonus_id_sets():
    # @coderabbitai add docstring here if needed and remove this comment after
    # get raw data
    """Return bonus ID sets by type.
    
    Returns:
        tuple: A tuple with five elements in the following order:
            - A set of bonus IDs for sockets.
            - A set of bonus IDs for leech.
            - A set of bonus IDs for avoidance.
            - A set of bonus IDs for speed.
            - A list of bonus IDs for item level additions.
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


# @coderabbitai add docstring here if needed and remove this comment after
def get_secondary_stats():
    # @coderabbitai add docstring here if needed and remove this comment after
    # get raw data
    """Extract secondary stat bonus IDs.
    
    Retrieves bonus IDs for the secondary stats 'haste', 'crit', 'mastery', and 'versatility'
    from the raidbot data and organizes them into sets.
    
    Returns:
        tuple: Four sets containing bonus IDs for 'haste', 'crit', 'mastery', and 'versatility'.
    """
    bonus_ids = get_bonus_ids()
    # get ids for each bonus type
    haste_ids = set(bonus_ids["haste"].keys())
    crit_ids = set(bonus_ids["crit"].keys())
    mastery_ids = set(bonus_ids["mastery"].keys())
    versatility_ids = set(bonus_ids["versatility"].keys())
    return haste_ids, crit_ids, mastery_ids, versatility_ids
