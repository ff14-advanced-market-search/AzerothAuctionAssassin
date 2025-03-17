from utils.api_requests import get_raidbots_bonus_ids


# @coderabbitai add docstring here if needed and remove this comment after
def get_bonus_ids():
    # @coderabbitai add docstring here if needed and remove this comment after
    """Get categorized bonus IDs based on specific attributes from raidbot data.
    Returns:
        - dict: A dictionary with keys representing bonus categories and values containing bonus IDs matching category criteria.
    Processing Logic:
        - Identify socket bonuses directly from the bonus_id_dict.
        - Level bonuses are those with specific key sets indicating an item level addition.
        - Use "rawStats" to determine other bonus categories such as Leech, Avoidance, Speed, and others.
        - Aggregate categorized bonus IDs into a consolidated dictionary for easy access.
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
    """Get sets of bonus IDs categorized by type.
    Returns:
        - tuple: A tuple containing sets of IDs for sockets, leech, avoidance, speed, and a list of item level additions.
    Processing Logic:
        - Extracts bonus IDs from a predefined data structure.
        - Organizes the IDs into sets based on the bonus type.
        - Retrieves additional item level bonuses separately."""
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
    Returns:
        - tuple: A tuple containing four sets representing the bonus IDs for 'haste', 'crit', 'mastery', and 'versatility'.
    Processing Logic:
        - Retrieves raw data for bonus IDs using the `get_bonus_ids()` function.
        - Extracts bonus type IDs from the raw data and organizes them into sets for easy manipulation and access.
    """
    bonus_ids = get_bonus_ids()
    # get ids for each bonus type
    haste_ids = set(bonus_ids["haste"].keys())
    crit_ids = set(bonus_ids["crit"].keys())
    mastery_ids = set(bonus_ids["mastery"].keys())
    versatility_ids = set(bonus_ids["versatility"].keys())
    return haste_ids, crit_ids, mastery_ids, versatility_ids
