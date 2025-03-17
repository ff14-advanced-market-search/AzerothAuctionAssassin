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
    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_mega_vars(var_name, raw_mega_data, required=False):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves and validates a configuration variable from input data or the environment.
        
        Parameters:
            var_name (str): The name of the configuration variable.
            raw_mega_data (dict): Dictionary containing configuration values.
            required (bool, optional): If True, the variable is required and must be present in
                raw_mega_data or as an environment variable; otherwise, an Exception is raised.
        
        Returns:
            The processed value for the configuration variable. Returns None if the variable is
            optional and not found.
        
        Raises:
            Exception: If a required variable is missing or if a variable value (e.g., WOW_REGION)
            does not meet the allowed criteria.
        
        Note:
            Specific variable names are subject to custom validations and conversions:
              - "WOW_REGION" must be one of: "EU", "NA", "NACLASSIC", "NASODCLASSIC", "EUCLASSIC", or "EUSODCLASSIC".
              - "FACTION" defaults to "all" if not provided or invalid.
              - "MEGA_THREADS", "SCAN_TIME_MAX", and "SCAN_TIME_MIN" are coerced to integers within defined ranges.
              - Boolean variables listed in default_true and default_false are processed based on their default behavior.
        """
        
                    """
                    Determines the boolean value for a variable based on its default behavior.
        
                    Returns the default behavior if the provided value (as a string, case-insensitive) matches;
                    otherwise, returns the opposite of the default behavior.
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
        # @coderabbitai add docstring here if needed and remove this comment after
        def process_var(var_value, default_behaviour):
            # @coderabbitai add docstring here if needed and remove this comment after
            """
            Determines the effective boolean setting based on input compared to a default value.
            
            This function compares the input value against the default behavior by converting both to
            lowercase strings. If they match—or if the values are directly equal—the default behavior is
            returned; otherwise, the negation of the default behavior is returned.
            
            Args:
                var_value: The value to evaluate, which may be provided as a string or a boolean.
                default_behaviour: The default boolean setting against which var_value is compared.
            
            Returns:
                bool: The evaluated boolean result, either default_behaviour or its opposite.
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
    # @coderabbitai add docstring here if needed and remove this comment after
    def check_access_token(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        # tokens are valid for 24 hours
        """
        Validates and refreshes the Blizzard OAuth access token.
        
        Returns the current token if it is less than 20 hours old; otherwise, requests a new token
        from the Blizzard OAuth API using client credentials, updates the stored token and timestamp,
        and returns the new token. Raises an exception if the token request fails or if the response
        lacks a valid access token.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_item_names(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves and filters item names based on desired items.
        
        This method calls a utility to obtain all item names and returns a dictionary
        containing only those items whose IDs (converted to integers) are present in the
        DESIRED_ITEMS attribute.
        """
        item_names = get_itemnames()
        item_names = {
            int(id): name
            for id, name in item_names.items()
            if int(id) in self.DESIRED_ITEMS.keys()
        }
        return item_names

    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_desired_items(self, item_list_name, path_to_data=None):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Loads desired items from a JSON file or environment variable.
        
        Attempts to load a mapping of desired items using the provided list name. If a
        custom file path is given, it checks that file; otherwise it looks for a file named
        "<item_list_name>.json" in the default directory. If no data is found, it falls back
        to an environment variable named as the uppercase form of the list name.
        Finally, the function converts the mapping keys to integers and values to floats.
        
        Args:
            item_list_name: The base name for the desired items, used to construct the JSON
                            filename and corresponding environment variable.
            path_to_data: Optional; a custom path to the desired items data file.
            
        Returns:
            A dictionary mapping item identifiers (int) to their associated values (float).
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_desired_ilvl_list(self, path_to_data=None):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Loads and processes desired item level entries.
        
        This method reads desired ilvl configuration from a JSON file or the corresponding
        environment variable if the file is missing or empty. If a custom path is provided,
        it loads the data from that file; otherwise, it defaults to the file "AzerothAuctionAssassinData/desired_ilvl_list.json".
        Data entries are then grouped based on their specified ilvl, with entries lacking item IDs
        handled separately as broad groups. For each group, additional item details are retrieved
        and processed using helper functions, and the resulting configurations are compiled into a list.
        
        Args:
            path_to_data (str, optional): Path to a JSON file containing the desired ilvl entries.
                Defaults to None, in which case a preset file location and/or environment variable is used.
        
        Returns:
            list: A list of processed desired ilvl configurations, or an empty list if no valid data is found.
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

    def __set_desired_ilvl(
        self, ilvl_info, item_names, base_ilvls, base_required_levels
    ):
        # Set default values if not present
        """
        Constructs and validates the desired item level configuration for auction sniping.
        
        This method assigns defaults to missing keys in the ilvl_info dictionary, checks that
        all required keys are present and of the correct type, and then builds a structured
        configuration dictionary for sniping auctions. When no specific item IDs are provided,
        it uses the full mapping from item_names along with base ilvl and required level data.
        
        Args:
            ilvl_info: A dictionary containing item level settings. It must include keys
                'ilvl', 'max_ilvl', 'buyout', 'sockets', 'speed', 'leech', 'avoidance',
                'item_ids', 'required_min_lvl', 'required_max_lvl', and 'bonus_lists'. Default
                values are applied for keys that are missing.
            item_names: A dictionary mapping item IDs to their names.
            base_ilvls: A dictionary mapping item IDs to their baseline item level values.
            base_required_levels: A dictionary mapping item IDs to their baseline required level values.
        
        Returns:
            A tuple consisting of:
                - A dictionary with the validated and structured configuration (snipe_info).
                - The target item level extracted from ilvl_info['ilvl'].
        
        Raises:
            Exception: If any required keys are missing from ilvl_info or if any value does not
            have the expected type.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_desired_pet_ilvl_list(self, path_to_data=None):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieve and validate desired pet item level data from file or environment variables.
        
        This method loads a JSON-formatted list of pet item level configurations from a provided file path or a default file
        ("AzerothAuctionAssassinData/desired_pet_ilvl_list.json"). If the file is not found or yields no data, it will attempt
        to load the configuration from an environment variable. Each pet entry is validated to ensure it includes the keys
        'petID', 'price', 'minLevel', 'minQuality', and 'excludeBreeds', with values converted as needed. The 'minLevel' must be
        between 1 and 25 and 'price' must be greater than 0. An exception is raised if any pet entry is invalid.
        
        Args:
            path_to_data: Optional file path to the pet item level JSON data.
        
        Returns:
            A list of dictionaries containing the processed pet item level entries, or an empty list if no valid data is found.
        
        Raises:
            Exception: If any pet entry is missing required keys or contains invalid values.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def __set_realm_names(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
            Loads realm names from a region-specific JSON file, optionally filtering Russian realms.
        
            This method reads a JSON file containing connected realm IDs and names based on the
            current region. If the NO_RUSSIAN_REALMS flag is enabled, it filters out any realms
            whose names appear in the list of Russian realm IDs.
        
            Returns:
                dict: A dictionary mapping realm IDs to realm names.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def __validate_snipe_lists(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Validate that at least one snipe list is provided.
        
        Checks that at least one of the snipe data lists (desired items, desired pets, 
        item level items, item level list, or pet item level list) is non-empty. If all are empty,
        raises an Exception with a message detailing the required configuration.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_upload_time_list(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieve a list of upload timers.
        
        Returns:
            list: The values of the upload timers.
        """
        return list(self.upload_timers.values())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_upload_time_minutes(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Return a set of unique last upload minutes from the auction data timers.
        
        This method extracts the "lastUploadMinute" value from each dictionary in the list
        returned by get_upload_time_list() and aggregates these values into a set to ensure
        uniqueness.
        """
        return set(realm["lastUploadMinute"] for realm in self.get_upload_time_list())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_realm_names(self, connectedRealmId):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Return a sorted list of realm names associated with the given connected realm ID.
        
        Args:
            connectedRealmId: The identifier for the connected realm used to filter realm names.
        
        Returns:
            A sorted list of realm names that correspond to the specified connected realm ID.
        """
        realm_names = [
            name for name, id in self.WOW_SERVER_NAMES.items() if id == connectedRealmId
        ]
        realm_names.sort()
        return realm_names

    #### AH API CALLS ####
    @retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
    # @coderabbitai add docstring here if needed and remove this comment after
    def get_listings_single(self, connectedRealmId: int):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves auction listings for a given connected realm.
        
        If the connected realm identifier is -1 or -2, fetches commodity auction data for the
        configured region. Otherwise, aggregates auction listings from one or more API endpoints,
        determined by the region and faction settings. The function returns merged auction
        data or an empty list if no listings are available.
        
        Parameters:
            connectedRealmId (int): The identifier for the connected realm. Special values
                                    (-1, -2) trigger commodity auction retrieval.
        
        Returns:
            list: A list of auction listings.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def construct_api_url(self, connectedRealmId, endpoint):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Builds the Blizzard API URL for retrieving auction data for a connected realm.
        
        This method constructs the URL by choosing the correct base URL, namespace, and locale
        based on the region configuration. It adapts the namespace for special region cases such
        as Classic and SOD to ensure the URL targets the appropriate auction data endpoint.
        
        Args:
            connectedRealmId: The identifier for the connected realm.
            endpoint: The API endpoint extension appended after the auctions path.
        
        Returns:
            The fully constructed API URL as a string.
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
    # @coderabbitai add docstring here if needed and remove this comment after
    def make_ah_api_request(self, url, connectedRealmId):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Sends a GET request to the Blizzard auction API and returns auction data.
        
        This method adds an authorization header using a valid access token and sends an HTTP GET
        request to the specified URL. It handles rate-limited (HTTP 429) and other non-successful
        responses by printing an error message, waiting, and raising an Exception. If a 'Last-Modified'
        header is present in the response, the method updates local upload timers and converts the
        timestamp for potential additional use.
        
        Parameters:
            url: The auction API endpoint.
            connectedRealmId: The identifier of the connected realm for which auction data is requested.
        
        Returns:
            The auction data parsed from the JSON response.
        
        Raises:
            Exception: If the API returns a rate limit error or any non-200 status code.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def update_local_timers(self, dataSetID, lastUploadTimeRaw):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Update local upload timers with new upload time details.
        
        Extracts the minute component and Unix timestamp from the provided raw upload time string,
        then updates the upload_timers dictionary with dataset identification and timing details.
        For dataset identifiers -1 and -2, the function applies retail commodity listing conventions;
        for other identifiers, it retrieves realm names via the get_realm_names method.
        
        Args:
            dataSetID: Identifier for the dataset, with -1 and -2 signifying retail commodities.
            lastUploadTimeRaw: Raw upload time string formatted as "%a, %d %b %Y %H:%M:%S %Z".
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
    # @coderabbitai add docstring here if needed and remove this comment after
    def make_commodity_ah_api_request(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves commodity auction data for the configured region.
        
        Builds the Blizzard API URL for commodity auctions based on the region and sends an
        authenticated GET request. Handles API errors including rate limits and invalid regions,
        updates local timers from the Last-Modified header when available, and returns the
        auction data parsed from JSON.
        
        Raises:
            Exception: If the region is invalid, if too many requests are encountered, or if the
                       API returns a non-success status.
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
    # @coderabbitai add docstring here if needed and remove this comment after
    def send_discord_message(self, message):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Sends a plain text message to the configured Discord webhook.
        
        Args:
            message: The content of the Discord message to send.
        """
        send_discord_message(message, self.WEBHOOK_URL)

    # @coderabbitai add docstring here if needed and remove this comment after
    def send_discord_embed(self, embed):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Send an embedded message to a Discord webhook.
        
        Sends the provided embed payload to the Discord webhook URL defined by the instance.
        The embed should be structured according to Discord's embed message schema.
        """
        send_embed_discord(embed, self.WEBHOOK_URL)
