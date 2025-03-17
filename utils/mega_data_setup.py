#!/usr/bin/python3
from __future__ import print_function
import json, requests, os, time
from datetime import datetime
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from utils.api_requests import (
    send_discord_message,
    get_itemnames,
    get_ilvl_items,
    send_embed_discord,
    get_pet_names_backup,
    get_petnames,
    get_update_timers_backup,
)
from utils.bonus_ids import get_bonus_id_sets
from utils.helpers import get_wow_russian_realm_ids
from collections import defaultdict


class MegaData:
    # add docstring here if needed
    def __init__(
        self,
        path_to_data_files=None,
        path_to_desired_items=None,
        path_to_desired_pets=None,
        path_to_desired_ilvl_items=None,
        path_to_desired_ilvl_list=None,
        path_to_desired_pet_ilvl_list=None,
    ):
        # the raw file users can write their input into
        """
        Initializes MegaData with configuration, API tokens, and auction parameters.
        
        This constructor loads configuration data from a JSON file (defaulting to
        "AzerothAuctionAssassinData/mega_data.json" if not provided) and sets up both
        optional and required environment variables necessary for auction scanning.
        It retrieves access tokens for the WoW API, obtains realm names, and establishes
        desired snipe lists for items and pets (including legacy item-level configurations).
        Additionally, it gathers item names, bonus identifier sets for item level adjustments,
        and initializes upload timers. A fallback mechanism is used for pet name retrieval if
        the primary API call fails.
        
        Args:
            path_to_data_files: Optional file path for the primary configuration JSON file.
            path_to_desired_items: Optional file path to override the desired items configuration.
            path_to_desired_pets: Optional file path to override the desired pets configuration.
            path_to_desired_ilvl_items: (Deprecated) Optional file path for legacy item-level data.
            path_to_desired_ilvl_list: Optional file path to override the desired item-level list.
            path_to_desired_pet_ilvl_list: Optional file path to override the desired pet item-level list.
        """
        if path_to_data_files == None:
            raw_mega_data = json.load(open("AzerothAuctionAssassinData/mega_data.json"))
        else:
            raw_mega_data = json.load(open(path_to_data_files))

        # set optional env vars
        self.THREADS = self.__set_mega_vars("MEGA_THREADS", raw_mega_data)
        self.SCAN_TIME_MIN = self.__set_mega_vars("SCAN_TIME_MIN", raw_mega_data)
        self.SCAN_TIME_MAX = self.__set_mega_vars("SCAN_TIME_MAX", raw_mega_data)
        self.REFRESH_ALERTS = self.__set_mega_vars("REFRESH_ALERTS", raw_mega_data)
        self.SHOW_BIDPRICES = self.__set_mega_vars("SHOW_BID_PRICES", raw_mega_data)
        self.EXTRA_ALERTS = self.__set_mega_vars("EXTRA_ALERTS", raw_mega_data)
        self.NO_RUSSIAN_REALMS = self.__set_mega_vars(
            "NO_RUSSIAN_REALMS", raw_mega_data
        )
        self.DEBUG = self.__set_mega_vars("DEBUG", raw_mega_data)
        self.NO_LINKS = self.__set_mega_vars("NO_LINKS", raw_mega_data)

        # set required env vars
        self.WOW_CLIENT_ID = self.__set_mega_vars("WOW_CLIENT_ID", raw_mega_data, True)
        self.WOW_CLIENT_SECRET = self.__set_mega_vars(
            "WOW_CLIENT_SECRET", raw_mega_data, True
        )
        self.WEBHOOK_URL = self.__set_mega_vars("MEGA_WEBHOOK_URL", raw_mega_data, True)
        self.REGION = self.__set_mega_vars("WOW_REGION", raw_mega_data, True)

        # classic regions dont have undermine exchange
        if "CLASSIC" in self.REGION:
            self.WOWHEAD_LINK = True
            self.FACTION = self.__set_mega_vars("FACTION", raw_mega_data)
        else:
            self.WOWHEAD_LINK = self.__set_mega_vars("WOWHEAD_LINK", raw_mega_data)
            self.FACTION = "all"

        self.WOW_SERVER_NAMES = self.__set_realm_names()
        # set access token for wow api
        self.access_token_creation_unix_time = 0
        self.access_token = self.check_access_token()

        # setup items to snipe
        self.DESIRED_ITEMS = self.__set_desired_items(
            "desired_items", path_to_desired_items
        )
        self.DESIRED_PETS = self.__set_desired_items(
            "desired_pets", path_to_desired_pets
        )

        # this should be depreciated now
        self.DESIRED_ILVL_ITEMS, self.min_ilvl = {}, 100000
        # this should be depreciated now

        self.DESIRED_ILVL_LIST = self.__set_desired_ilvl_list(path_to_desired_ilvl_list)
        self.DESIRED_PET_ILVL_LIST = self.__set_desired_pet_ilvl_list(
            path_to_desired_pet_ilvl_list
        )
        self.__validate_snipe_lists()

        ## should do this here and only get the names of desired items to limit data
        # get name dictionaries
        self.ITEM_NAMES = self.__set_item_names()
        try:
            self.PET_NAMES = get_petnames(self.access_token)
        except Exception as ex:
            # it's better to avoid using saddlebag apis if possible
            print(
                f"Error getting pet names from blizzard api, using backup method: {ex}"
            )
            self.PET_NAMES = get_pet_names_backup()

        # get static lists of ALL bonus id values from raidbots, note this is the index for all ilvl gear
        (
            self.socket_ids,
            self.leech_ids,
            self.avoidance_ids,
            self.speed_ids,
            self.ilvl_addition,
            # self.ilvl_base,
        ) = get_bonus_id_sets()

        # get item names from desired ilvl entries
        self.DESIRED_ILVL_NAMES = {}
        if len(self.DESIRED_ILVL_ITEMS) > 0:
            for k, v in self.DESIRED_ILVL_ITEMS["item_names"].items():
                self.DESIRED_ILVL_NAMES[k] = v

        for desired_ilvl_item in self.DESIRED_ILVL_LIST:
            for k, v in desired_ilvl_item["item_names"].items():
                self.DESIRED_ILVL_NAMES[k] = v

        # get upload times once from api and then we get it dynamically from each scan
        self.upload_timers = {}
        # # no longer need this it works better without using upload timers from the api
        # self.upload_timers = get_update_timers_backup(self.REGION, self.NO_RUSSIAN_REALMS)

    #### VARIABLE RELATED FUNCTIONS ####
    @staticmethod
    # add docstring here if needed
    def __set_mega_vars(var_name, raw_mega_data, required=False):
        """
        Retrieves and validates a configuration variable from JSON data or environment variables.
        
        This function looks for a configuration variable in the provided raw JSON data and, if not found, in the environment variables. If the variable is marked as required and is absent in both sources, an exception is raised. Depending on the variable name, the function enforces specific validations and default values:
          
          - For "WOW_REGION", the value must be one of "EU", "NA", "NACLASSIC", "NASODCLASSIC", "EUCLASSIC", or "EUSODCLASSIC"; otherwise, an exception is raised.
          - For "FACTION", if the value is missing or invalid, it defaults to "all".
          - For "MEGA_THREADS", the value is converted to an integer greater than 1; if not, it defaults to 48.
          - For "SCAN_TIME_MAX", the value must be a numeric value between 1 and 14, defaulting to 3 if out of range.
          - For "SCAN_TIME_MIN", the value must fall between -10 and 9, defaulting to 1 otherwise.
          - Boolean flags such as "NO_RUSSIAN_REALMS", "REFRESH_ALERTS", "DEBUG", and "NO_LINKS" are processed to establish a boolean value based on predefined default behaviors.
        
        Args:
            var_name: The name of the configuration variable.
            raw_mega_data: A dictionary containing configuration data, typically loaded from a JSON file.
            required: A flag indicating whether the variable must be present; if True and the variable is missing, an exception is raised.
        
        Returns:
            The validated and appropriately converted value for the configuration variable.
        """
        if len(raw_mega_data) != 0 and var_name in raw_mega_data.keys():
            print(f"loading {var_name} from AzerothAuctionAssassinData/mega_data.json")
            var_value = raw_mega_data[var_name]
        elif os.getenv(var_name):
            print(f"loading {var_name} from environment variables")
            var_value = os.getenv(var_name)
        elif required:
            raise Exception(
                f"Error required variable {var_name} not found in env or mega_data.json"
            )
        else:
            print(f"Optional variable {var_name} not found in env or mega_data.json")
            var_value = None

        # need to do this no matter where we get the region from
        if var_name == "WOW_REGION":
            if var_value not in [
                "EU",
                "NA",
                "NACLASSIC",
                "NASODCLASSIC",
                "EUCLASSIC",
                "EUSODCLASSIC",
            ]:
                raise Exception(f"error {var_value} not a valid region")

        # default to all but change for classic
        if var_name == "FACTION":
            if not var_value:
                var_value = "all"
            if var_value not in [
                "all",
                "horde",
                "alliance",
                "booty bay",
            ]:
                print(f"error {var_value} not a valid faction, default to scan all")
                var_value = "all"

        # default to 48 threads if not set
        if var_name == "MEGA_THREADS":
            if str(var_value).isdigit() or isinstance(var_value, int):
                if 1 < int(var_value):
                    var_value = int(var_value)
                else:
                    var_value = 48
            else:
                var_value = 48

        if var_name == "SCAN_TIME_MAX":
            if str(var_value).isnumeric() or isinstance(var_value, int):
                if 1 <= int(var_value) < 15:
                    var_value = int(var_value)
                else:
                    var_value = 3
            else:
                var_value = 3

        if var_name == "SCAN_TIME_MIN":
            if str(var_value).replace("-", "").isnumeric() or isinstance(
                var_value, int
            ):
                if -10 <= int(var_value) < 10:
                    var_value = int(var_value)
                else:
                    var_value = 1
            else:
                var_value = 1

        # handle cases where we need a default value to be true or false
        # add docstring here if needed
        def process_var(var_value, default_behaviour):
            """
            Return default_behaviour if var_value equals it; otherwise return its inverse.
            
            This function compares var_value and default_behaviour by converting both to their
            lowercase string representations and checking for equality. If they match (or are directly
            equal), it returns default_behaviour; otherwise, it returns the logical negation of default_behaviour.
            """
            if (
                str(var_value).lower() == str(default_behaviour).lower()
                or var_value == default_behaviour
            ):
                return default_behaviour
            else:
                return not default_behaviour

        default_true = ["NO_RUSSIAN_REALMS", "REFRESH_ALERTS"]
        default_false = ["DEBUG", "NO_LINKS"]

        if var_name in default_true:
            var_value = process_var(var_value, True)
        if var_value in default_false:
            var_value = process_var(var_value, False)

        return var_value

    # access token setter
    @retry(stop=stop_after_attempt(10))
    # add docstring here if needed
    def check_access_token(self):
        # tokens are valid for 24 hours
        """
        Checks and returns a valid Blizzard OAuth access token.
        
        If the current token is less than 20 hours old, it is returned. Otherwise, a new token
        is obtained via a POST request to Blizzard's OAuth endpoint using client credentials.
        The token and its creation time are updated accordingly. Raises an exception if the token
        retrieval fails or if the response lacks an access token.
        """
        if (
            int(datetime.now().timestamp()) - self.access_token_creation_unix_time
            < 20 * 60 * 60
        ):
            return self.access_token
        # if over 20 hours make a new token and reset the creation time
        else:
            response = requests.post(
                "https://oauth.battle.net/token",
                data={"grant_type": "client_credentials"},
                auth=(self.WOW_CLIENT_ID, self.WOW_CLIENT_SECRET),
            )

            if response.status_code != 200:
                raise Exception(
                    f"Failed to get blizzard oauth access token. Try again at: https://develop.battle.net/access/clients . Status code: {response.status_code}, Response: {response.text}"
                )

            access_token_raw = response.json()

            if "access_token" not in access_token_raw:
                raise Exception(
                    f"No access token in response. Response: {access_token_raw}"
                )

            self.access_token = access_token_raw["access_token"]
            self.access_token_creation_unix_time = int(datetime.now().timestamp())
            return self.access_token

    # add docstring here if needed
    def __set_item_names(self):
        """
        Retrieves item names for the desired items.
        
        This method fetches all available item names and returns a dictionary
        that includes only those items whose identifiers (converted to integers)
        are present in the DESIRED_ITEMS configuration.
        
        Returns:
            dict: A mapping from item ID (int) to item name (str) for desired items.
        """
        item_names = get_itemnames()
        item_names = {
            int(id): name
            for id, name in item_names.items()
            if int(id) in self.DESIRED_ITEMS.keys()
        }
        return item_names

    # add docstring here if needed
    def __set_desired_items(self, item_list_name, path_to_data=None):
        """
        Load desired items from a JSON file or environment variable.
        
        This method attempts to load desired item data by constructing a file name from the
        given list name. If a custom file path is provided and exists, it loads data from that
        location; otherwise, it checks the default "AzerothAuctionAssassinData/{item_list_name}.json"
        path. If no data is found in the file, it then tries to load the JSON data from an 
        environment variable named using the uppercase version of the list name. Finally, it
        converts the item keys to integers and the values to floats.
        
        Parameters:
            item_list_name: Identifier for the desired items list, used to form file and env var names.
            path_to_data: Optional path to a JSON file containing desired items.
        
        Returns:
            A dictionary mapping item IDs (int) to their associated desired values (float).
        """
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()
        desired_items_raw = {}

        if path_to_data:
            if os.path.exists(path_to_data):
                desired_items_raw = json.load(open(path_to_data))
            else:
                print(f"File not found: {path_to_data}")
        else:
            file_path = f"AzerothAuctionAssassinData/{file_name}"
            if os.path.exists(file_path):
                desired_items_raw = json.load(open(file_path))
            else:
                print(f"File not found: {file_path}")

        # if file is not set use env var
        if len(desired_items_raw) == 0:
            print(
                f"no desired items found in AzerothAuctionAssassinData/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                desired_items_raw = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                desired_items_raw = {}

        # convert to int keys and float values
        desired_items = {}
        for k, v in desired_items_raw.items():
            desired_items[int(k)] = float(v)
        return desired_items

    # add docstring here if needed
    def __set_desired_ilvl_list(self, path_to_data=None):
        """
        Loads and processes desired item level configuration data.
        
        This method attempts to load item level information from a specified JSON file if a path is provided or from the default
        file "AzerothAuctionAssassinData/desired_ilvl_list.json". If no valid data is found in a file, it falls back to reading the
        environment variable "DESIRED_ILVL_LIST". The loaded information is grouped by item level, with items lacking specific
        IDs handled as broad groups, and then processed via an internal helper to create a list of snipe configuration entries.
        
        Args:
            path_to_data: Optional path to a JSON file with item level configuration data.
        
        Returns:
            A list of snipe configuration entries for desired item levels, or an empty list if no valid configuration is found.
        """
        item_list_name = "desired_ilvl_list"
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()
        ilvl_info = {}

        if path_to_data:
            if os.path.exists(path_to_data):
                ilvl_info = json.load(open(path_to_data))
            else:
                print(f"File not found: {path_to_data}")
        else:
            file_path = f"AzerothAuctionAssassinData/{file_name}"
            if os.path.exists(file_path):
                ilvl_info = json.load(open(file_path))
            else:
                print(f"File not found: {file_path}")

        # if file is not set use env var
        if len(ilvl_info) == 0:
            print(
                f"no desired items found in AzerothAuctionAssassinData/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                ilvl_info = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                return []

        # Group items by ilvl
        ilvl_groups = defaultdict(list)
        broad_groups = []
        for item in ilvl_info:
            if "item_ids" not in item or len(item["item_ids"]) == 0:
                broad_groups.append(item)
            else:
                ilvl_groups[item["ilvl"]].append(item["item_ids"])

        DESIRED_ILVL_LIST = []

        # groups with user defined ilvls
        for ilvl, item_id_groups in ilvl_groups.items():
            # Flatten the list of item ids
            all_item_ids = [item_id for group in item_id_groups for item_id in group]
            item_names, item_ids, base_ilvls, base_required_levels = get_ilvl_items(
                ilvl, all_item_ids
            )

            for item in ilvl_info:
                if item["ilvl"] == ilvl:
                    snipe_info, min_ilvl = self.__set_desired_ilvl(
                        item, item_names, base_ilvls, base_required_levels
                    )
                    DESIRED_ILVL_LIST.append(snipe_info)

        # broad groups
        if broad_groups:
            # with a broad group we dont care about ilvl or item_ids
            # its the same generic info for all of them
            item_names, item_ids, base_ilvls, base_required_levels = get_ilvl_items()
            # add the item names an base ilvl to each broad group
            for item in broad_groups:
                snipe_info, min_ilvl = self.__set_desired_ilvl(
                    item, item_names, base_ilvls, base_required_levels
                )
                DESIRED_ILVL_LIST.append(snipe_info)

        return DESIRED_ILVL_LIST

    # add docstring here if needed
    def __set_desired_ilvl(
        self, ilvl_info, item_names, base_ilvls, base_required_levels
    ):
        # Set default values if not present
        """
            Construct and validate desired item level configuration.
            
            Processes the provided ilvl_info dictionary by setting defaults for missing optional
            fields and verifying that all required keys are present with appropriate types.
            Specifically, boolean flags and integer values are validated, and bonus lists are checked
            to contain only integers if provided. Depending on whether specific item IDs are specified,
            the function either uses all available items from item_names or filters based on the provided
            list, associating them with their corresponding base ilvls and required levels.
            
            Args:
                ilvl_info (dict): Configuration dictionary for item levels containing keys such as
                    "ilvl", "max_ilvl", "buyout", "sockets", "speed", "leech", "avoidance", "item_ids",
                    "required_min_lvl", "required_max_lvl", and "bonus_lists".
                item_names (dict): Mapping of item IDs to item names, used when no specific item_ids are provided.
                base_ilvls (dict): Mapping of item IDs to their base item levels.
                base_required_levels (dict): Mapping of item IDs to their base required levels.
            
            Returns:
                tuple: A tuple where the first element is a dictionary with the processed
                       snipe configuration and the second element is the target item level.
            
            Raises:
                Exception: If required keys are missing from ilvl_info or if any field fails type validation.
            """
        ilvl_info["item_ids"] = ilvl_info.get("item_ids", [])
        ilvl_info["required_min_lvl"] = ilvl_info.get("required_min_lvl", 1)
        ilvl_info["required_max_lvl"] = ilvl_info.get("required_max_lvl", 1000)
        ilvl_info["max_ilvl"] = ilvl_info.get("max_ilvl", 10000)
        ilvl_info["bonus_lists"] = ilvl_info.get("bonus_lists", [])
        ilvl_info["sockets"] = ilvl_info.get("sockets", False)
        ilvl_info["speed"] = ilvl_info.get("speed", False)
        ilvl_info["leech"] = ilvl_info.get("leech", False)
        ilvl_info["avoidance"] = ilvl_info.get("avoidance", False)

        required_keys = {
            "ilvl",
            "max_ilvl",
            "buyout",
            "sockets",
            "speed",
            "leech",
            "avoidance",
            "item_ids",
            "required_min_lvl",
            "required_max_lvl",
            "bonus_lists",
        }

        # Check if all required keys are present
        missing_keys = required_keys - set(ilvl_info.keys())
        if missing_keys:
            raise Exception(
                f"Error: Missing required keys {missing_keys} in ilvl_info:\n{ilvl_info}"
            )

        snipe_info = {}
        bool_vars = ["sockets", "speed", "leech", "avoidance"]
        int_vars = [
            "ilvl",
            "max_ilvl",
            "buyout",
            "required_min_lvl",
            "required_max_lvl",
        ]
        for key, value in ilvl_info.items():
            if key in bool_vars:
                if isinstance(ilvl_info[key], bool):
                    snipe_info[key] = value
                else:
                    raise Exception(f"error in ilvl info '{key}' must be true or false")
            elif key in int_vars:
                if isinstance(ilvl_info[key], int):
                    snipe_info[key] = value
                else:
                    raise Exception(f"error in ilvl info '{key}' must be an int")

        # Validate bonus lists are integers
        if ilvl_info["bonus_lists"] != [] and not all(
            isinstance(x, int) for x in ilvl_info["bonus_lists"]
        ):
            raise Exception(
                "error in ilvl info 'bonus_lists' must contain only integers"
            )

        if ilvl_info["item_ids"] == []:
            snipe_info["item_names"] = item_names
            snipe_info["item_ids"] = set(item_names.keys())
            snipe_info["base_ilvls"] = base_ilvls
            snipe_info["base_required_levels"] = base_required_levels
            snipe_info["bonus_lists"] = ilvl_info["bonus_lists"]
        else:
            snipe_info["item_names"] = {
                item_id: item_names.get(item_id, "foobar")
                for item_id in ilvl_info["item_ids"]
            }
            snipe_info["item_ids"] = set(ilvl_info["item_ids"])
            snipe_info["base_ilvls"] = {
                item_id: base_ilvls.get(item_id, 1) for item_id in ilvl_info["item_ids"]
            }
            snipe_info["base_required_levels"] = {
                item_id: base_required_levels.get(item_id, 1)
                for item_id in ilvl_info["item_ids"]
            }
            snipe_info["bonus_lists"] = ilvl_info["bonus_lists"]

        return snipe_info, ilvl_info["ilvl"]

    # add docstring here if needed
    def __set_desired_pet_ilvl_list(self, path_to_data=None):
        """
        Load and validate pet item level configuration.
        
        This function reads pet item level data from a JSON file or, if not found, from the
        DESIRED_PET_ILVL_LIST environment variable. When a custom file path is provided and exists,
        the data is loaded from that file; otherwise, it attempts to load data from the default path
        'AzerothAuctionAssassinData/desired_pet_ilvl_list.json'. If no data is available, an empty list is returned.
        Each pet entry must contain the keys 'petID', 'price', 'minLevel', 'minQuality', and 'excludeBreeds';
        the function converts appropriate fields to integers and validates that 'minLevel' is between 1 and 25
        and that 'price' is greater than 0.
        
        Args:
            path_to_data (str, optional): Path to the JSON file containing pet configuration data.
        
        Returns:
            list: A list of dictionaries with validated pet configuration data.
        
        Raises:
            Exception: If any pet entry is missing a required key or contains invalid field values.
        """
        item_list_name = "desired_pet_ilvl_list"
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()
        pet_ilvl_info = {}

        if path_to_data:
            if os.path.exists(path_to_data):
                pet_ilvl_info = json.load(open(path_to_data))
            else:
                print(f"File not found: {path_to_data}")
        else:
            file_path = f"AzerothAuctionAssassinData/{file_name}"
            if os.path.exists(file_path):
                pet_ilvl_info = json.load(open(file_path))
            else:
                print(f"File not found: {file_path}")

        # if file is not set use env var
        if len(pet_ilvl_info) == 0:
            print(
                f"no desired items found in AzerothAuctionAssassinData/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                pet_ilvl_info = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                return []

        # Validate and process each pet entry
        processed_pet_list = []
        for pet in pet_ilvl_info:
            pet["minQuality"] = int(pet.get("minQuality", -1))
            pet["excludeBreeds"] = list(pet.get("excludeBreeds", []))
            if not all(
                key in pet
                for key in ["petID", "price", "minLevel", "minQuality", "excludeBreeds"]
            ):
                raise Exception(
                    f"Error: Each pet entry must contain 'petID', 'price', 'minLevel', 'minQuality', 'excludeBreeds'. Found: {pet}"
                )

            # Validate types and convert as needed
            processed_pet = {
                "petID": int(pet["petID"]),  # Match the API's
                "price": int(pet["price"]),
                "minLevel": int(pet["minLevel"]),  # Handle both string and int inputs
                "minQuality": pet["minQuality"],
                "excludeBreeds": [int(breed) for breed in pet["excludeBreeds"]],
            }

            # Validate value ranges
            if not (1 <= processed_pet["minLevel"] <= 25):
                raise Exception(
                    f"Error: minLevel must be between 1 and 25. Found: {processed_pet['minLevel']}"
                )
            if processed_pet["price"] <= 0:
                raise Exception(
                    f"Error: price must be greater than 0. Found: {processed_pet['price']}"
                )

            processed_pet_list.append(processed_pet)

        return processed_pet_list

    # add docstring here if needed
    def __set_realm_names(self):
        """
        Retrieve realm names for the configured region.
        
        This method loads a JSON file containing connected realm IDs and names based on the
        instance's REGION attribute. If the instance is set to exclude Russian realms, it
        filters out any realm names that are associated with Russian realm IDs obtained via
        get_wow_russian_realm_ids. The resulting dictionary of realm names is then returned.
        """
        realm_names = json.load(
            open(
                f"AzerothAuctionAssassinData/{str(self.REGION).lower()}-wow-connected-realm-ids.json"
            )
        )
        if self.NO_RUSSIAN_REALMS:
            russian_realm_ids = get_wow_russian_realm_ids()
            realm_names = {
                k: v for k, v in realm_names.items() if v not in russian_realm_ids
            }
        return realm_names

    # add docstring here if needed
    def __validate_snipe_lists(self):
        """
        Validates that at least one snipe list is configured.
        
        Checks whether the lists for items, pets, item levels, and pet item levels are all empty.
        If so, raises an Exception with instructions on setting the appropriate environment variables or JSON files.
        """
        if (
            len(self.DESIRED_ITEMS) == 0
            and len(self.DESIRED_PETS) == 0
            and len(self.DESIRED_ILVL_ITEMS) == 0
            and len(self.DESIRED_ILVL_LIST) == 0
            and len(self.DESIRED_PET_ILVL_LIST) == 0
        ):
            error_message = "Error no snipe data found!\n"
            error_message += "You need to set env vars for DESIRED_ITEMS or DESIRED_PETS, DESIRED_ILVL, DESIRED_ILVL_LIST or DESIRED_PET_ILVL_LIST\n"
            error_message += "Or you need to set up your AzerothAuctionAssassinData/ json files with one of the following files:\n"
            error_message += "- desired_items.json\n"
            error_message += "- desired_pets.json\n"
            error_message += "- desired_ilvl.json\n"
            error_message += "- desired_ilvl_list.json\n"
            error_message += "- desired_pet_ilvl_list.json\n"
            raise Exception(error_message)

    # add docstring here if needed
    def get_upload_time_list(self):
        """
        Retrieves a list of upload timer values.
        
        Returns:
            list: A list containing the values of the internal upload timers.
        """
        return list(self.upload_timers.values())

    # add docstring here if needed
    def get_upload_time_minutes(self):
        """
        Return unique last upload minutes from auction upload timers.
        
        Extracts the 'lastUploadMinute' field from each timer in the list provided by 
        get_upload_time_list and aggregates them into a set.
        """
        return set(realm["lastUploadMinute"] for realm in self.get_upload_time_list())

    # add docstring here if needed
    def get_realm_names(self, connectedRealmId):
        """
        Return a sorted list of realm names for the specified connected realm ID.
        
        This method filters the instance's WOW_SERVER_NAMES dictionary to extract realm
        names that match the given connected realm ID and returns them in alphabetical order.
        
        Args:
            connectedRealmId: An integer representing the connected realm ID used for filtering.
        
        Returns:
            A list of sorted realm names corresponding to the provided connected realm ID.
        """
        realm_names = [
            name for name, id in self.WOW_SERVER_NAMES.items() if id == connectedRealmId
        ]
        realm_names.sort()
        return realm_names

    #### AH API CALLS ####
    @retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
    # add docstring here if needed
    def get_listings_single(self, connectedRealmId: int):
        """
        Retrieves auction listings for a connected realm.
        
        This method obtains auction data by calling the appropriate API endpoint based on the
        provided connected realm identifier. Special values (-1 or -2) indicate that commodity
        auction data should be retrieved. For other identifiers, the method selects endpoints
        based on the region and faction (for classic areas) and aggregates auction listings.
        If no valid data is returned, an empty list is provided.
        
        Args:
            connectedRealmId (int): Identifier for the connected realm or a special value
                (-1, -2) to fetch commodity auctions.
        
        Returns:
            list: A list of auction listings, or an empty list if no auctions are found.
        """
        if connectedRealmId in [-1, -2]:
            print(f"gather data from {self.REGION} commodities")
            auction_info = self.make_commodity_ah_api_request()
            if auction_info is None:
                return []
            return auction_info["auctions"]
        else:
            print(
                f"gather data from connectedRealmId {connectedRealmId} of region {self.REGION}"
            )

        all_auctions = []
        if "CLASSIC" in self.REGION:
            if self.FACTION == "alliance":
                endpoints = ["/2"]
            elif self.FACTION == "horde":
                endpoints = ["/6"]
            elif self.FACTION == "booty bay":
                endpoints = ["/7"]
            else:
                endpoints = ["/2", "/6", "/7"]
        else:
            endpoints = [""]

        for endpoint in endpoints:
            url = self.construct_api_url(connectedRealmId, endpoint)

            auction_info = self.make_ah_api_request(url, connectedRealmId)
            if auction_info is None or "auctions" not in auction_info:
                print(
                    f"{self.REGION} {str(connectedRealmId)} realm data, no auctions found"
                )
                continue
            # merge all the auctions
            all_auctions.extend(auction_info["auctions"])

        return all_auctions

    # add docstring here if needed
    def construct_api_url(self, connectedRealmId, endpoint):
        """
        Constructs the Blizzard WoW auction API URL for the specified connected realm.
        
        This method generates the full API URL for fetching auction data based on the
        configured region. The URL is tailored according to whether the region is North
        America or Europe, with further adjustments for Classic or SOD variants.
            
        Args:
            connectedRealmId: The ID of the connected realm.
            endpoint: The endpoint suffix to append to the auctions route.
            
        Returns:
            The complete URL as a string.
        """
        base_url = (
            "https://us.api.blizzard.com"
            if "NA" in self.REGION
            else "https://eu.api.blizzard.com"
        )
        namespace = "dynamic-us" if "NA" in self.REGION else "dynamic-eu"
        locale = "en_US" if "NA" in self.REGION else "en_EU"

        if "SOD" in self.REGION:
            namespace = f"dynamic-classic1x-{namespace.split('-')[-1]}"
        elif "CLASSIC" in self.REGION:
            namespace = f"dynamic-classic-{namespace.split('-')[-1]}"

        url = f"{base_url}/data/wow/connected-realm/{str(connectedRealmId)}/auctions{endpoint}?namespace={namespace}&locale={locale}"

        return url

    @retry(
        stop=stop_after_attempt(10),
        retry=retry_if_exception_type(requests.RequestException),
        retry_error_callback=lambda retry_state: {"auctions": []},
    )
    # add docstring here if needed
    def make_ah_api_request(self, url, connectedRealmId):
        """
        Requests auction house data from the Blizzard API and returns the parsed JSON.
        
        This method sends an HTTP GET request to the specified URL using an OAuth bearer token
        obtained from `check_access_token`. It handles rate limiting by delaying and raising an
        exception if the response status code is 429, or any non-200 status code, and updates
        local timers using the 'Last-Modified' header when present.
        
        Args:
            url: The full API endpoint URL for fetching auction data.
            connectedRealmId: The identifier of the connected realm for which auction data is requested.
        
        Returns:
            A dictionary containing the auction house data parsed from the JSON response.
        
        Raises:
            Exception: If the API call fails due to rate limiting or other errors.
        """
        headers = {"Authorization": f"Bearer {self.check_access_token()}"}
        req = requests.get(url, headers=headers, timeout=20)

        # check for api errors
        if req.status_code == 429:
            error_message = f"{req} BLIZZARD too many requests error on {self.REGION} {str(connectedRealmId)} realm data, skipping"
            print(error_message)
            time.sleep(3)
            raise Exception(error_message)
        elif req.status_code != 200:
            error_message = f"{req} BLIZZARD error getting {self.REGION} {str(connectedRealmId)} realm data"
            print(error_message)
            time.sleep(1)
            raise Exception(error_message)

        current_time = int(datetime.now().timestamp())
        if "Last-Modified" in dict(req.headers):
            try:
                lastUploadTimeRaw = dict(req.headers)["Last-Modified"]
                self.update_local_timers(connectedRealmId, lastUploadTimeRaw)

                # Convert Last-Modified time to unix timestamp
                last_upload_time = int(
                    datetime.strptime(
                        lastUploadTimeRaw, "%a, %d %b %Y %H:%M:%S %Z"
                    ).timestamp()
                )

                # # Check if data is older than 2 hours (7200 seconds)
                # if current_time - last_upload_time > 7200:
                #     print(
                #         f"Data for realm {connectedRealmId} is too old (>2 hours), skipping"
                #     )
                #     return None

            except Exception as ex:
                print(f"The exception was:", ex)

        auction_info = req.json()
        return auction_info

    # add docstring here if needed
    def update_local_timers(self, dataSetID, lastUploadTimeRaw):
        """
        Update local upload timers with the latest auction data timestamp.
        
        Parses the raw upload time string to extract the minute and Unix timestamp, determines
        the appropriate table and dataset names based on the dataSetID (with -1 and -2 reserved
        for commodity listings), and updates the upload_timers mapping accordingly.
        
        Args:
            dataSetID: Identifier for the dataset. Use -1 or -2 for commodity listings.
            lastUploadTimeRaw: Raw timestamp string formatted as "%a, %d %b %Y %H:%M:%S %Z".
        """
        if dataSetID == -1:
            tableName = f"{self.REGION}_retail_commodityListings"
            dataSetName = [f"{self.REGION} Commodities"]
        elif dataSetID == -2:
            tableName = f"{self.REGION}_retail_commodityListings"
            dataSetName = [f"{self.REGION} Commodities"]
        else:
            tableName = f"{dataSetID}_singleMinPrices"
            dataSetName = self.get_realm_names(dataSetID)

        lastUploadMinute = int(lastUploadTimeRaw.split(":")[1])
        lastUploadUnix = int(
            datetime.strptime(lastUploadTimeRaw, "%a, %d %b %Y %H:%M:%S %Z").timestamp()
        )
        new_realm_time = {
            "dataSetID": dataSetID,
            "dataSetName": dataSetName,
            "lastUploadMinute": lastUploadMinute,
            "lastUploadTimeRaw": lastUploadTimeRaw,
            "lastUploadUnix": lastUploadUnix,
            "region": self.REGION,
            "tableName": tableName,
        }
        self.upload_timers[dataSetID] = new_realm_time

    @retry(
        stop=stop_after_attempt(10),
        retry=retry_if_exception_type(requests.RequestException),
        retry_error_callback=lambda retry_state: {"auctions": []},
    )
    # add docstring here if needed
    def make_commodity_ah_api_request(self):
        """
        Fetches commodity auction data from the Blizzard API.
        
        Determines the appropriate API endpoint for the current region ("NA" or "EU") and sends
        an HTTP GET request using a valid OAuth access token. If a "Last-Modified" header is present,
        updates local upload timers accordingly. Handles rate limiting and other API errors by printing
        an error message, pausing briefly, and raising an exception. Returns the auction data as a
        JSON-decoded dictionary.
        """
        if self.REGION == "NA":
            url = f"https://us.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-us&locale=en_US"
            connectedRealmId = -1
        elif self.REGION == "EU":
            url = f"https://eu.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-eu&locale=en_EU"
            connectedRealmId = -2
        else:
            raise Exception(
                f"invalid region {self.REGION} passed to get_raw_commodity_listings()"
            )
        headers = {"Authorization": f"Bearer {self.check_access_token()}"}
        req = requests.get(url, headers=headers, timeout=20)

        # check for api errors
        if req.status_code == 429:
            error_message = f"{req} BLIZZARD too many requests error on {self.REGION} commodities data, skipping"
            print(error_message)
            time.sleep(3)
            raise Exception(error_message)
        elif req.status_code != 200:
            error_message = f"{req} BLIZZARD error getting {self.REGION} {str(connectedRealmId)} realm data"
            print(error_message)
            time.sleep(1)
            raise Exception(error_message)

        current_time = int(datetime.now().timestamp())
        if "Last-Modified" in dict(req.headers):
            try:
                lastUploadTimeRaw = dict(req.headers)["Last-Modified"]
                self.update_local_timers(connectedRealmId, lastUploadTimeRaw)

                # Convert Last-Modified time to unix timestamp
                last_upload_time = int(
                    datetime.strptime(
                        lastUploadTimeRaw, "%a, %d %b %Y %H:%M:%S %Z"
                    ).timestamp()
                )

                # # Check if data is older than 2 hours (7200 seconds)
                # if current_time - last_upload_time > 7200:
                #     print(f"Commodity data is too old (>2 hours), skipping")
                #     return {"auctions": []}

            except Exception as ex:
                print(f"The exception was:", ex)

        auction_info = req.json()
        return auction_info

    #### GENERAL USE FUNCTIONS ####
    # add docstring here if needed
    def send_discord_message(self, message):
        """
        Sends a message to the Discord channel via a webhook.
        
        This method forwards the given message to the webhook URL configured in the instance.
        Args:
            message: The text message to be sent.
        """
        send_discord_message(message, self.WEBHOOK_URL)

    # add docstring here if needed
    def send_discord_embed(self, embed):
        """
        Sends an embed message to the configured Discord webhook.
        
        This function forwards the provided Discord embed payload to the webhook URL
        stored in the instance, using the send_embed_discord helper.
        """
        send_embed_discord(embed, self.WEBHOOK_URL)
