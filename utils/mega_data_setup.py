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
        self.IMPORTANT_EMOJI = self.__set_mega_vars("IMPORTANT_EMOJI", raw_mega_data)
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
        self.DESIRED_ILVL_ITEMS, self.min_ilvl = self.__set_desired_ilvl_single(
            path_to_desired_ilvl_items
        )
        self.DESIRED_ILVL_LIST = self.__set_desired_ilvl_list(path_to_desired_ilvl_list)
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
    def __set_mega_vars(var_name, raw_mega_data, required=False):
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

        if var_name == "IMPORTANT_EMOJI":
            if len(str(var_value)) != 1:
                var_value = "🔥"
            else:
                var_value = str(var_value)

        ## save old method just incase, can probably delete it later
        # if var_name == "DEBUG":
        #     if str(var_value).lower() == "true" or var_value == True:
        #         var_value = True
        #     else:
        #         var_value = False

        # if var_name == "NO_RUSSIAN_REALMS":
        #     if var_value == "false" or var_value == False:
        #         var_value = False
        #     else:
        #         var_value = True

        # if var_name == "REFRESH_ALERTS":
        #     if str(var_value).lower() == "false" or var_value == False:
        #         var_value = False
        #     else:
        #         var_value = True

        # handle cases where we need a default value to be true or false
        def process_var(var_value, default_behaviour):
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
    def check_access_token(self):
        # tokens are valid for 24 hours
        if (
            int(datetime.now().timestamp()) - self.access_token_creation_unix_time
            < 20 * 60 * 60
        ):
            return self.access_token
        # if over 20 hours make a new token and reset the creation time
        else:
            access_token_raw = requests.post(
                "https://oauth.battle.net/token",
                data={"grant_type": "client_credentials"},
                auth=(self.WOW_CLIENT_ID, self.WOW_CLIENT_SECRET),
            ).json()
            self.access_token = access_token_raw["access_token"]
            self.access_token_creation_unix_time = int(datetime.now().timestamp())
            return self.access_token

    def __set_item_names(self):
        item_names = get_itemnames()
        item_names = {
            int(id): name
            for id, name in item_names.items()
            if int(id) in self.DESIRED_ITEMS.keys()
        }
        return item_names

    def __set_desired_items(self, item_list_name, path_to_data=None):
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()
        if path_to_data == None:
            desired_items_raw = json.load(
                open(f"AzerothAuctionAssassinData/{file_name}")
            )
        else:
            desired_items_raw = json.load(open(path_to_data))
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
        desired_items = {}
        for k, v in desired_items_raw.items():
            desired_items[int(k)] = float(v)
        return desired_items

    def __set_desired_ilvl_single(self, path_to_data=None):
        item_list_name = "desired_ilvl"
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()

        if path_to_data == None:
            ilvl_info = json.load(open(f"AzerothAuctionAssassinData/{file_name}"))
        else:
            ilvl_info = json.load(open(path_to_data))

        # if file is not set use env var
        if len(ilvl_info) == 0:
            print(
                f"no desired items found in AzerothAuctionAssassinData/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                ilvl_info = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                return {}, 201
        DESIRED_ILVL_ITEMS, min_ilvl = self.__set_desired_ilvl(ilvl_info)
        return DESIRED_ILVL_ITEMS, min_ilvl

    def __set_desired_ilvl_list(self, path_to_data=None):
        item_list_name = "desired_ilvl_list"
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()
        if path_to_data == None:
            ilvl_info = json.load(open(f"AzerothAuctionAssassinData/{file_name}"))
        else:
            ilvl_info = json.load(open(path_to_data))

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
        ilvl_info["item_ids"] = ilvl_info.get("item_ids", [])
        ilvl_info["required_min_lvl"] = ilvl_info.get("required_min_lvl", 1)
        ilvl_info["required_max_lvl"] = ilvl_info.get("required_max_lvl", 1000)
        ilvl_info["max_ilvl"] = ilvl_info.get("max_ilvl", 10000)

        example = {
            "ilvl": 360,
            "max_ilvl": 10000,
            "buyout": 50000,
            "sockets": False,
            "speed": True,
            "leech": False,
            "avoidance": False,
            "item_ids": [12345, 67890],
            "required_min_lvl": 1,
            "required_max_lvl": 1000,
        }

        if ilvl_info.keys() != example.keys():
            raise Exception(
                f"error missing required keys {set(example.keys())} from info:\n{ilvl_info}"
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

        if ilvl_info["item_ids"] == []:
            snipe_info["item_names"] = item_names
            snipe_info["item_ids"] = set(item_names.keys())
            snipe_info["base_ilvls"] = base_ilvls
            snipe_info["base_required_levels"] = base_required_levels
        else:
            snipe_info["item_names"] = {
                item_id: item_names[item_id] for item_id in ilvl_info["item_ids"]
            }
            snipe_info["item_ids"] = set(ilvl_info["item_ids"])
            snipe_info["base_ilvls"] = {
                item_id: base_ilvls[item_id] for item_id in ilvl_info["item_ids"]
            }
            snipe_info["base_required_levels"] = {
                item_id: base_required_levels[item_id]
                for item_id in ilvl_info["item_ids"]
            }

        return snipe_info, ilvl_info["ilvl"]

    def __set_realm_names(self):
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

    def __validate_snipe_lists(self):
        if (
            len(self.DESIRED_ITEMS) == 0
            and len(self.DESIRED_PETS) == 0
            and len(self.DESIRED_ILVL_ITEMS) == 0
            and len(self.DESIRED_ILVL_LIST) == 0
        ):
            error_message = "Error no snipe data found!\n"
            error_message += "You need to set env vars for DESIRED_ITEMS or DESIRED_PETS, DESIRED_ILVL or DESIRED_ILVL_LIST\n"
            error_message += "Or you need to set up your AzerothAuctionAssassinData/ json files with one of the following files:\n"
            error_message += "- desired_items.json\n"
            error_message += "- desired_pets.json\n"
            error_message += "- desired_ilvl.json\n"
            error_message += "- desired_ilvl_list.json\n"
            raise Exception(error_message)

    def get_upload_time_list(self):
        return list(self.upload_timers.values())

    def get_upload_time_minutes(self):
        return set(realm["lastUploadMinute"] for realm in self.get_upload_time_list())

    def get_realm_names(self, connectedRealmId):
        realm_names = [
            name for name, id in self.WOW_SERVER_NAMES.items() if id == connectedRealmId
        ]
        realm_names.sort()
        return realm_names

    #### AH API CALLS ####
    @retry(stop=stop_after_attempt(3), retry_error_callback=lambda state: {})
    def get_listings_single(self, connectedRealmId: int):
        if connectedRealmId in [-1, -2]:
            print("==========================================")
            print(f"gather data from {self.REGION} commodities")
            auction_info = self.make_commodity_ah_api_request()
            return auction_info["auctions"]
        else:
            print("==========================================")
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
            if auction_info == None or "auctions" not in auction_info:
                print(
                    f"{self.REGION} {str(connectedRealmId)} realm data, no auctions found"
                )
                continue
            # merge all the auctions
            all_auctions.extend(auction_info["auctions"])

        return all_auctions

    def construct_api_url(self, connectedRealmId, endpoint):
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
    def make_ah_api_request(self, url, connectedRealmId):
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

        if "Last-Modified" in dict(req.headers):
            try:
                lastUploadTimeRaw = dict(req.headers)["Last-Modified"]
                self.update_local_timers(connectedRealmId, lastUploadTimeRaw)
            except Exception as ex:
                print(f"The exception was:", ex)

        auction_info = req.json()
        return auction_info

    def update_local_timers(self, dataSetID, lastUploadTimeRaw):
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
    def make_commodity_ah_api_request(self):
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

        if "Last-Modified" in dict(req.headers):
            try:
                lastUploadTimeRaw = dict(req.headers)["Last-Modified"]
                self.update_local_timers(connectedRealmId, lastUploadTimeRaw)
            except Exception as ex:
                print(f"The exception was:", ex)

        auction_info = req.json()
        return auction_info

    #### GENERAL USE FUNCTIONS ####
    def send_discord_message(self, message):
        send_discord_message(message, self.WEBHOOK_URL)

    def send_discord_embed(self, embed):
        send_embed_discord(embed, self.WEBHOOK_URL)
