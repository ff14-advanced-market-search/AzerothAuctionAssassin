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
        Retrieves and validates a configuration variable.
        
        This helper function obtains the value of a configuration variable from a provided
        data dictionary or the environment. If the variable is found in the raw data, its
        value is used; otherwise, the corresponding environment variable is checked.
        If the variable is marked as required and is not found, an exception is raised.
        For recognized variables such as WOW_REGION, FACTION, MEGA_THREADS, SCAN_TIME_MAX,
        and SCAN_TIME_MIN, the function applies specific validation rules and defaults.
        Additionally, boolean-like variables are processed to ensure they adhere to expected
        default behaviors.
        
        Parameters:
            var_name: The name of the configuration variable.
            raw_mega_data: A dictionary containing configuration data.
            required: A flag indicating whether the variable must be present.
        
        Returns:
            The validated value of the configuration variable, which may be a string, integer,
            boolean, or None.
        
        Raises:
            Exception: If a required variable is missing or if an invalid value is provided for
            WOW_REGION.
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
            Process a variable against a default behavior to yield a boolean result.
            
            This function compares the input value with the default behavior by both direct
            equality and by comparing their lowercase string representations. If the input
            value matches the default behavior, the default is returned; otherwise, the
            logical negation of the default is returned.
            
            Args:
                var_value: The value to evaluate, which may be a boolean or its string form.
                default_behaviour: The expected default boolean value.
            
            Returns:
                bool: The default behavior if a match is detected; otherwise, its negation.
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
        Checks and refreshes the OAuth access token.
        
        Returns the current Blizzard OAuth access token if it was created within 20 hours.
        Otherwise, requests a new token from Blizzard's OAuth service, updates the token and its
        creation time, and returns the new token.
        
        Raises:
            Exception: If the token request fails or the response does not contain an access token.
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
        
        This method obtains item names using an external source and converts the
        item IDs to integers. Only items whose IDs are present in the desired items
        list (DESIRED_ITEMS) are retained.
        
        Returns:
            dict: A mapping of item IDs (int) to their corresponding names (str).
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
        Load desired items configuration from a file or environment variable.
        
        This method attempts to load a JSON mapping of desired items using the provided
        item_list_name. If a file path is provided via path_to_data, that file is used;
        otherwise, it looks for a file named "{item_list_name}.json" within the
        "AzerothAuctionAssassinData" directory. If the file is not found or contains no
        data, the method falls back to an environment variable named as the uppercase
        version of item_list_name. The loaded data is then converted so that keys become
        integers and values become floats.
        
        Parameters:
            item_list_name: The base name for the desired items configuration.
            path_to_data: Optional path to a JSON file with desired items.
        
        Returns:
            A dictionary mapping item IDs (int) to their corresponding values (float).
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
        Processes and returns desired item level configurations for auction sniping.
        
        This method loads item level configuration data either from a specified JSON file or from a default
        directory. If the file cannot be found or contains no data, it attempts to load the data from an
        environment variable. The configurations are grouped by their provided item level, with special
        handling for entries lacking specific item IDs. Each configuration is processed to generate snipe
        information using auxiliary methods, and an aggregated list of these configurations is returned.
        If no configuration data is found, an empty list is returned.
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
        Processes and validates item level configuration for auction sniping.
        
        This method sets default values for missing keys in the provided item level
        configuration and validates that all required keys are present and have the
        expected types. Depending on whether specific item IDs are provided in the
        configuration, it constructs a snipe information dictionary using either all
        available item names or a filtered subset. The method also ensures that bonus
        lists contain only integers.
        
        Parameters:
            ilvl_info (dict): Configuration for item level criteria, expected to include
                keys such as "ilvl", "max_ilvl", "buyout", "sockets", "speed", "leech",
                "avoidance", "item_ids", "required_min_lvl", "required_max_lvl", and "bonus_lists".
            item_names (dict): Mapping of item IDs to their display names.
            base_ilvls (dict): Mapping of item IDs to their base item levels.
            base_required_levels (dict): Mapping of item IDs to their base required levels.
        
        Returns:
            tuple: A tuple containing:
                - snipe_info (dict): The processed and validated configuration for auction sniping.
                - int: The target item level from ilvl_info.
                
        Raises:
            Exception: If required keys are missing or if any configuration value does not
                match the expected data type.
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
        Load and validate desired pet item level data from a file or environment variable.
        
        This method loads pet item level data from a JSON file specified by the optional
        path_to_data parameter, or from the default file 
        "AzerothAuctionAssassinData/desired_pet_ilvl_list.json". If no file data is found,
        it falls back to the 'DESIRED_PET_ILVL_LIST' environment variable. Each pet entry is 
        validated to ensure it contains the keys 'petID', 'price', 'minLevel', 'minQuality', and 
        'excludeBreeds', and values are converted to the appropriate types. An exception is raised
        if any required key is missing, or if 'minLevel' is not between 1 and 25, or if 'price' is 
        not greater than 0.
        
        :param path_to_data: Optional file path to a JSON file containing pet item level data.
        :return: A list of processed pet entries as dictionaries.
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
        Load and filter connected realm names based on the configured region.
        
        This method reads realm names from a region-specific JSON file within the
        AzerothAuctionAssassinData directory, using the object's REGION setting.
        If the NO_RUSSIAN_REALMS flag is enabled, it filters out realms that appear in
        the list provided by get_wow_russian_realm_ids.
        
        Returns:
            dict: A dictionary mapping connected realm IDs to their corresponding names.
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
        Validates that at least one snipe data list is populated.
        
        Checks if all snipe data lists for items, pets, item levels, and pet item levels are empty.
        If so, raises an Exception with a detailed message suggesting the required environment variables
        or JSON configuration files to set up snipe data.
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
        Retrieves the list of auction upload timer values.
        
        Returns:
            list: A list of timer values extracted from the internal upload_timers.
        """
        return list(self.upload_timers.values())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_upload_time_minutes(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves unique upload minutes.
        
        This method obtains upload time records via get_upload_time_list and returns a set of the
        unique "lastUploadMinute" values extracted from each record.
        
        Returns:
            set: A set of unique upload minute values.
        """
        return set(realm["lastUploadMinute"] for realm in self.get_upload_time_list())

    # @coderabbitai add docstring here if needed and remove this comment after
    def get_realm_names(self, connectedRealmId):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Retrieves and sorts realm names for the specified connected realm ID.
        
        Args:
            connectedRealmId: The identifier of the connected realm to match in the WOW_SERVER_NAMES mapping.
        
        Returns:
            A list of realm names sorted in ascending order.
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
        Fetch auction listings for a specific connected realm.
        
        Retrieves auction data from the auction house API using the given connected realm identifier.
        For identifiers -1 and -2, commodity auction data is fetched separately. For all other values,
        the method determines the appropriate API endpoints based on the region and faction and aggregates
        auction listings from each. If no auctions are found for an endpoint, that response is skipped.
        
        Args:
            connectedRealmId (int): The identifier of the connected realm; use -1 or -2 for commodity data.
        
        Returns:
            list: A list of auction listings aggregated from the API responses.
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
        Constructs the API URL for retrieving auction data.
        
        This method builds a Blizzard API URL using the connected realm ID and an endpoint. It determines the base URL, namespace, and locale based on the region associated with the instance. For classic regions, the namespace is further adjusted to reflect legacy endpoints.
        
        Args:
            connectedRealmId: The identifier of the connected realm.
            endpoint: Additional auction endpoint details to be appended to the URL.
        
        Returns:
            A string representing the fully constructed API URL.
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
        Fetches auction house data from the Blizzard API.
        
        Makes a GET request to the specified URL using a current access token. Handles API 
        errors such as rate limiting (HTTP 429) and other non-200 responses by pausing briefly 
        and raising an exception. If the response includes a Last-Modified header, updates local 
        timers based on its value before returning the auction data.
        
        Args:
            url: The API endpoint URL for auction data.
            connectedRealmId: The identifier of the connected realm for which data is retrieved.
        
        Returns:
            A dictionary containing the auction data parsed from the API response.
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
        Update the local upload timers with API response data.
        
        This method computes and stores timing details for the given dataset using a raw
        upload time string. For dataset IDs -1 or -2, which indicate commodity listings, it
        sets the table name and dataset names accordingly. For other IDs, it derives the table
        name using the dataset ID and retrieves corresponding realm names. The raw upload
        time (expected in the format '%a, %d %b %Y %H:%M:%S %Z') is used to extract the upload
        minute and to compute the Unix timestamp. The resulting timing information is stored
        in the instance's upload_timers dictionary.
            
        Args:
            dataSetID: Identifier of the dataset (-1/-2 for commodities; otherwise, a realm ID).
            lastUploadTimeRaw: Raw timestamp string from the API, formatted as
                '%a, %d %b %Y %H:%M:%S %Z'.
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
        Fetch commodity auction data from the Blizzard API.
        
        Based on the configured region ("NA" or "EU"), this method builds the appropriate endpoint URL 
        and retrieves commodity auction listings. If a "Last-Modified" header is present in the response, 
        it updates local upload timers. An exception is raised for an invalid region or on API errors 
        including rate limiting.
        
        Returns:
            dict: The parsed auction data.
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
        Sends a Discord message via the configured webhook.
        
        Sends the specified plain text message to the Discord webhook URL stored in the instance.
            
        Args:
            message: The message content to be sent.
        """
        send_discord_message(message, self.WEBHOOK_URL)

    # @coderabbitai add docstring here if needed and remove this comment after
    def send_discord_embed(self, embed):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Sends an embedded message to the Discord webhook.
        
        Args:
            embed: The embed object containing the message details.
        """
        send_embed_discord(embed, self.WEBHOOK_URL)
