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
            Retrieves and validates a configuration variable value.
        
            This function attempts to load the value identified by var_name from the provided
            raw_mega_data dictionary and, if not found, from environment variables. If the variable
            is marked as required but is not found, an exception is raised. Special handling and
            validation are applied for specific variable names, such as enforcing allowed region codes
            for WOW_REGION, defaulting and validating FACTION, and ensuring numeric values for MEGA_THREADS,
            SCAN_TIME_MAX, and SCAN_TIME_MIN. Boolean variables (e.g., NO_RUSSIAN_REALMS, REFRESH_ALERTS,
            DEBUG, NO_LINKS) are also processed to enforce default behaviors.
        
            Parameters:
                var_name: The name of the configuration variable.
                raw_mega_data: A dictionary containing configuration data loaded from a JSON file.
                required: A flag indicating whether the variable must be present.
        
            Returns:
                The validated and normalized value of the configuration variable, or None if it is optional
                and not found.
        
            Raises:
                Exception: If a required variable is missing or if an invalid region code is provided.
            """
        """
                Converts the provided variable value to a boolean based on the specified default.
        
                If the string representation of var_value matches the default behavior (ignoring case)
                or equals the default, the default is returned; otherwise, the opposite boolean value is returned.
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
            Evaluate a variable against a default behavior and return a boolean.
            
            Converts var_value to a lowercase string for comparison with default_behaviour. If
            the value matches the default (by direct comparison or case-insensitively), the
            function returns default_behaviour; otherwise, it returns the opposite boolean.
                
            Args:
                var_value: The input value to evaluate, which can be a boolean or its string
                           representation.
                default_behaviour: The default boolean value used for comparison and as the
                                   return value when a match is found.
                
            Returns:
                bool: default_behaviour if var_value matches it; otherwise, the negation of
                      default_behaviour.
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
        Checks and refreshes the Blizzard OAuth access token if it is older than 20 hours.
        
        Returns the current access token if it was created less than 20 hours ago. Otherwise,
        it requests a new token using client credentials, updates the token and its creation time,
        and returns the new token.
        
        Raises:
            Exception: If the token retrieval fails or the response does not contain an access token.
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
        Retrieves and filters item names for desired items.
        
        Fetches a mapping of item IDs to names from an external source and returns only
        those entries whose IDs are present in the DESIRED_ITEMS dictionary. The keys
        in the returned dictionary are converted to integers.
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
        Load desired items from a JSON file or environment variable.
        
        This function loads a mapping of item IDs to numerical values representing desired items. It first
        attempts to read data from a JSON file specified by the optional path (or defaults to the "AzerothAuctionAssassinData"
        directory using the provided list name). If the file is not found or contains no data, it falls back to
        an environment variable keyed by the uppercase version of the list name. The raw data is then converted so
        that keys become integers and values become floats.
        
        Args:
            item_list_name: Name used to generate the file name and environment variable key.
            path_to_data: Optional; explicit path to the JSON file containing desired items.
        
        Returns:
            A dictionary mapping item IDs (int) to their associated values (float). If no valid data is found, an
            empty dictionary is returned.
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
        Load and organize desired item level configuration for auction snipe.
        
        This function retrieves desired item level data from a specified JSON file, a default file location, or an
        environment variable if file-based configuration is not available. It groups items by their item level and processes
        each group into structured snipe entries using an internal setup function. If no valid configuration is found, it returns
        an empty list.
        
        Args:
            path_to_data (str, optional): File path to a JSON file containing desired item level information.
            
        Returns:
            list: A list of dictionaries representing snipe configuration entries for each item level group.
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
            Validates and organizes item level filtering information for snipe configuration.
        
            This method processes a dictionary of item level criteria by setting default values for
            optional keys, verifying that all required keys are present, and ensuring that boolean and
            integer fields have correct types. It constructs and returns a structured configuration
            dictionary (snipe_info) used for auction data filtering. If 'item_ids' is empty, global item
            names and base level data are used; otherwise, configuration is built based on the provided
            item IDs. An exception is raised if any required keys are missing or if value types are invalid.
        
            Args:
                ilvl_info (dict): Dictionary with item level criteria and filtering constraints.
                    Expected keys include 'ilvl', 'buyout', 'max_ilvl', 'sockets', 'speed', 'leech',
                    'avoidance', 'item_ids', 'required_min_lvl', 'required_max_lvl', and 'bonus_lists'.
                item_names (dict): Mapping of item IDs to item names, used when 'item_ids' is empty.
                base_ilvls (dict): Mapping of item IDs to base item levels for default configuration.
                base_required_levels (dict): Mapping of item IDs to required levels for default configuration.
        
            Returns:
                tuple: A tuple containing:
                    - dict: A dictionary with the validated snipe configuration.
                    - int: The target item level threshold extracted from ilvl_info.
            
            Raises:
                Exception: If required keys are missing in ilvl_info or if any key values do not have the expected type.
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
        Load and validate pet item-level filtering data.
        
        This method loads desired pet item-level filter configurations from a JSON file or an environment
        variable. If a file path is provided, it attempts to load from that location; otherwise, it checks a
        default file path. When no data is found in the file, it falls back to the environment variable.
        Each pet entry is validated to contain the required keys: "petID", "price", "minLevel", "minQuality",
        and "excludeBreeds". The method enforces correct data types by converting applicable values to integers,
        ensures "minLevel" is between 1 and 25, and that "price" is greater than 0. An exception is raised if any
        pet entry is missing a required key or contains invalid values.
        
        Args:
            path_to_data: Optional; a file system path to a JSON file containing pet item-level data.
        
        Returns:
            A list of dictionaries with validated pet filter settings.
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
        Load realm names from a JSON file and filter out Russian realms if enabled.
        
        This method reads a JSON file whose name is based on the lowercased region value
        (self.REGION) from the 'AzerothAuctionAssassinData' directory. If the
        NO_RUSSIAN_REALMS flag is set, it removes entries corresponding to Russian
        realms, as determined by the get_wow_russian_realm_ids function.
        
        Returns:
            dict: A mapping of connected realm IDs to realm names.
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
            Validates that at least one snipe data list is provided.
        
            Checks that at least one of the following lists is non-empty:
            DESIRED_ITEMS, DESIRED_PETS, DESIRED_ILVL_ITEMS, DESIRED_ILVL_LIST, or DESIRED_PET_ILVL_LIST.
            Raises an exception with a detailed error message if all lists are empty.
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
        Returns a list of upload timers for auction data.
        
        The list is generated from the values stored in the internal upload_timers dictionary.
        """
        return list(self.upload_timers.values())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_upload_time_minutes(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Return unique upload time minutes from auction timer records.
        
        Extracts the "lastUploadMinute" value from each record in the upload time list and returns a
        set of those unique minute values. This helps in identifying distinct time checkpoints for auction
        data uploads.
        """
        return set(realm["lastUploadMinute"] for realm in self.get_upload_time_list())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_realm_names(self, connectedRealmId):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves the sorted realm names for a given connected realm ID.
        
        Filters the realm names from the WOW_SERVER_NAMES mapping based on the provided connected realm ID,
        sorts them alphabetically, and returns the resulting list.
        
        Args:
            connectedRealmId: The identifier of the connected realm used for filtering.
            
        Returns:
            A sorted list of realm names corresponding to the connected realm.
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
        Retrieve auction listings for a connected realm using appropriate endpoints.
        
        If connectedRealmId is -1 or -2, retrieves commodity auction listings; otherwise,
        fetches auction data for the specified realm by iterating over endpoints determined
        by region and faction settings. Merges results from multiple endpoints if necessary.
        
        Args:
            connectedRealmId: The identifier for the connected realm. Use -1 or -2 to fetch
                commodity auctions.
        
        Returns:
            A list of auction listings, or an empty list if no auctions are found.
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
            Constructs the auction API URL for a connected realm.
        
            Builds the URL for fetching auction data from Blizzard's API using region-specific
            settings. Adjusts the namespace and locale based on the region, and modifies the
            namespace for classic or Soul of the Dragon variants as needed.
        
            Args:
                connectedRealmId: The identifier of the connected realm.
                endpoint: A URL segment to append to the auctions path.
        
            Returns:
                A string representing the complete API URL.
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
        Makes an authenticated GET request to the Blizzard auction house API.
        
        This function retrieves auction data by sending a GET request with a bearer token.
        It handles rate limits and other API errors by pausing briefly and raising an exception.
        If a 'Last-Modified' header is present, local timers for the specified connected realm
        are updated accordingly.
        
        Args:
            url: The API endpoint to fetch auction data from.
            connectedRealmId: The Blizzard connected realm identifier used for timer updates.
        
        Raises:
            Exception: If the API returns a rate limit (HTTP 429) or any non-success status.
        
        Returns:
            A dictionary containing auction data parsed from the JSON response.
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
        Updates the local upload timer record based on raw timestamp data.
        
        Parses a raw upload time string to extract the minute and Unix timestamp, then
        builds and stores a timer record for the specified dataset. For commodity listings
        (dataSetID -1 or -2), commodity-specific table and name values are used; otherwise,
        the realm names are determined using the provided dataset ID.
          
        Args:
            dataSetID: Integer identifier for the dataset; negative values indicate commodity listings.
            lastUploadTimeRaw: Raw upload time as a string in the format '%a, %d %b %Y %H:%M:%S %Z'.
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
        Retrieve commodity auction data from Blizzard API.
        
        Constructs the commodity auction endpoint URL based on the configured region
        ("NA" for U.S. or "EU" for Europe) and makes an authenticated GET request using an
        OAuth token. Processes the response to update local upload timers via the
        Last-Modified header and returns the parsed JSON auction data. Raises an exception
        for invalid regions or API errors, including rate limiting.
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
        Sends a message to Discord via the configured webhook.
        
        Relays the given message to the Discord webhook URL stored in the object's WEBHOOK_URL attribute.
        """
        send_discord_message(message, self.WEBHOOK_URL)

    # @coderabbitai add docstring here if needed and remove this comment after
    def send_discord_embed(self, embed):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Sends an embed message to the Discord webhook.
        
        This method forwards the provided embed payload to the Discord webhook using the
        configured webhook URL.
          
        Args:
            embed: The embed content to be sent.
        """
        send_embed_discord(embed, self.WEBHOOK_URL)
