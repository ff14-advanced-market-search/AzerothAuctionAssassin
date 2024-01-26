#!/usr/bin/python3
from __future__ import print_function
import json, requests, os, time
from datetime import datetime
from tenacity import retry, stop_after_attempt
from utils.api_requests import send_discord_message, get_itemnames, get_ilvl_items
from utils.bonus_ids import get_bonus_id_sets
from utils.helpers import get_wow_russian_realm_ids


class MegaData:
    def __init__(self, 
                 path_to_data_files=None, 
                 path_to_desired_items = None, 
                 path_to_desired_pets = None,
                 path_to_desired_ilvl_items = None,
                 path_to_desired_ilvl_list = None,):
        # the raw file users can write their input into
        if path_to_data_files == None:
            raw_mega_data = json.load(open("user_data/mega/mega_data.json"))
        else:
            raw_mega_data = json.load(open(path_to_data_files))

        self.THREADS = self.__set_mega_vars("MEGA_THREADS", raw_mega_data)
        self.SCAN_TIME_MIN = self.__set_mega_vars("SCAN_TIME_MIN", raw_mega_data)
        self.SCAN_TIME_MAX = self.__set_mega_vars("SCAN_TIME_MAX", raw_mega_data)
        self.REFRESH_ALERTS = self.__set_mega_vars("REFRESH_ALERTS", raw_mega_data)

        # set generic values usually in the env vars
        self.WOW_CLIENT_ID = self.__set_mega_vars("WOW_CLIENT_ID", raw_mega_data, True)
        self.WOW_CLIENT_SECRET = self.__set_mega_vars(
            "WOW_CLIENT_SECRET", raw_mega_data, True
        )
        self.WEBHOOK_URL = self.__set_mega_vars("MEGA_WEBHOOK_URL", raw_mega_data, True)
        self.WOWHEAD_LINK = self.__set_mega_vars("WOWHEAD_LINK", raw_mega_data)
        self.SHOW_BIDPRICES = self.__set_mega_vars("SHOW_BID_PRICES", raw_mega_data)
        self.REGION = self.__set_mega_vars("WOW_REGION", raw_mega_data, True)
        self.EXTRA_ALERTS = self.__set_mega_vars("EXTRA_ALERTS", raw_mega_data)
        self.WOW_SERVER_NAMES = json.load(
            open(f"data/{str(self.REGION).lower()}-wow-connected-realm-ids.json")
        )
        # set access token for wow api
        self.access_token_creation_unix_time = 0
        self.access_token = self.check_access_token()

        # setup items to snipe
        self.DESIRED_ITEMS = self.__set_desired_items("desired_items", path_to_desired_items)
        self.DESIRED_PETS = self.__set_desired_items("desired_pets", path_to_desired_pets)
        self.DESIRED_ILVL_ITEMS, self.min_ilvl = self.__set_desired_ilvl_single(path_to_desired_ilvl_items)
        self.DESIRED_ILVL_LIST = self.__set_desired_ilvl_list(path_to_desired_ilvl_list)
        self.__validate_snipe_lists()

        ## should do this here and only get the names of desired items to limit data
        # get name dictionaries
        self.ITEM_NAMES = self.__set_item_names()
        self.PET_NAMES = self.__set_pet_names()
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
        self.NO_RUSSIAN_REALMS = self.__set_mega_vars(
            "NO_RUSSIAN_REALMS", raw_mega_data
        )
        self.upload_timers = self.__set_upload_timers()

    #### VARIABLE RELATED FUNCTIONS ####
    @staticmethod
    def __set_mega_vars(var_name, raw_mega_data, required=False):
        if len(raw_mega_data) != 0 and var_name in raw_mega_data.keys():
            print(f"loading {var_name} from user_data/mega/mega_data.json")
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
        if var_name == "REGION":
            if var_value.upper() not in ["US", "EU", "NA"]:
                raise Exception(f"error {var_value} not a valid region")
            # for people who are confused about US vs NA, all our data uses NA
            if var_value.upper() == "US":
                var_value = "NA"
            else:
                var_value = var_value.upper()

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

        if var_name == "REFRESH_ALERTS":
            if var_value == "false" or var_value == False:
                var_value = False
            else:
                var_value = True

        return var_value

    # access token setter
    @retry(stop=stop_after_attempt(3))
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

    def __set_pet_names(self):
        pet_info = requests.get(
            f"https://us.api.blizzard.com/data/wow/pet/index?namespace=static-us&locale=en_US&access_token={self.access_token}"
        ).json()["pets"]
        pet_info = {int(pet["id"]): pet["name"] for pet in pet_info}
        return pet_info

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
            
            desired_items_raw = json.load(open(f"user_data/mega/{file_name}"))
        else:
            desired_items_raw = json.load(open(path_to_data))
        # if file is not set use env var
        if len(desired_items_raw) == 0:
            print(
                f"no desired items found in user_data/mega/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                desired_items_raw = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                desired_items_raw = {}
        desired_items = {}
        for k, v in desired_items_raw.items():
            desired_items[int(k)] = int(v)
        return desired_items

    def __set_desired_ilvl_single(self, path_to_data=None):
        item_list_name = "desired_ilvl"
        file_name = f"{item_list_name}.json"
        env_var_name = item_list_name.upper()

        if path_to_data == None:
            ilvl_info = json.load(open(f"user_data/mega/{file_name}"))
        else:
            ilvl_info = json.load(open(path_to_data))

        # if file is not set use env var
        if len(ilvl_info) == 0:
            print(
                f"no desired items found in user_data/mega/{file_name} pulling from env vars"
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
            ilvl_info = json.load(open(f"user_data/mega/{file_name}"))
        else:
            ilvl_info = json.load(open(path_to_data))

        # if file is not set use env var
        if len(ilvl_info) == 0:
            print(
                f"no desired items found in user_data/mega/{file_name} pulling from env vars"
            )
            if os.getenv(env_var_name):
                ilvl_info = json.loads(os.getenv(env_var_name))
            else:
                print(f"skipping {item_list_name} its not set in file or env var")
                return []
        DESIRED_ILVL_LIST = []
        for ilvl_info_single in ilvl_info:
            snipe_info, min_ilvl = self.__set_desired_ilvl(ilvl_info_single)
            DESIRED_ILVL_LIST.append(snipe_info)
        return DESIRED_ILVL_LIST

    def __set_desired_ilvl(self, ilvl_info):
        # add empty item_ids if not set
        if "item_ids" not in ilvl_info.keys():
            ilvl_info["item_ids"] = []

        example = {
            "ilvl": 360,
            "buyout": 50000,
            "sockets": False,
            "speed": True,
            "leech": False,
            "avoidance": False,
            "item_ids": [12345, 67890],
        }

        if ilvl_info.keys() != example.keys():
            raise Exception(
                f"error missing required keys {set(example.keys())} from info:\n{ilvl_info}"
            )

        snipe_info = {}
        bool_vars = ["sockets", "speed", "leech", "avoidance"]
        int_vars = ["ilvl", "buyout"]
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

        if ilvl_info["ilvl"] < 201:
            raise Exception(
                f"error we do not snipe for any legacy items below ilvl 201 it will be too much spam"
            )

        # get names and ids of items
        (
            snipe_info["item_names"],
            snipe_info["item_ids"],
            snipe_info["base_ilvls"],
        ) = get_ilvl_items(ilvl_info["ilvl"], ilvl_info["item_ids"])

        return snipe_info, ilvl_info["ilvl"]

    def __validate_snipe_lists(self):
        if (
            len(self.DESIRED_ITEMS) == 0
            and len(self.DESIRED_PETS) == 0
            and len(self.DESIRED_ILVL_ITEMS) == 0
            and len(self.DESIRED_ILVL_LIST) == 0
        ):
            error_message = "Error no snipe data found!\n"
            error_message += "You need to set env vars for DESIRED_ITEMS or DESIRED_PETS, DESIRED_ILVL or DESIRED_ILVL_LIST\n"
            error_message += "Or you need to set up your user_data/mega/ json files with one of the following files:\n"
            error_message += "- desired_items.json\n"
            error_message += "- desired_pets.json\n"
            error_message += "- desired_ilvl.json\n"
            error_message += "- desired_ilvl_list.json\n"
            raise Exception(error_message)

    def __set_upload_timers(self):
        update_timers = requests.post(
            "http://api.saddlebagexchange.com/api/wow/uploadtimers",
            json={},
        ).json()["data"]
        server_update_times = {
            time_data["dataSetID"]: time_data
            for time_data in update_timers
            if time_data["dataSetID"] not in [-1, -2]
            and time_data["region"] == self.REGION
        }
        if self.NO_RUSSIAN_REALMS:
            russian_realm_ids = get_wow_russian_realm_ids()
            server_update_times = {
                k: v
                for k, v in server_update_times.items()
                if v["dataSetID"] not in russian_realm_ids
            }

        return server_update_times

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
        print("==========================================")
        print(
            f"gather data from connectedRealmId {connectedRealmId} of region {self.REGION}"
        )
        # we want to use check_access_token here to update the token when expired
        if self.REGION == "NA":
            url = f"https://us.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}"
            url += f"/auctions?namespace=dynamic-us&locale=en_US&access_token={self.check_access_token()}"
        elif self.REGION == "EU":
            url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{str(connectedRealmId)}"
            url += f"/auctions?namespace=dynamic-eu&locale=en_EU&access_token={self.check_access_token()}"
        else:
            raise Exception(
                f"{self.REGION} is not yet supported, reach out for us to add this region option"
            )

        req = requests.get(url, timeout=20)
        # check for api errors
        if req.status_code == 429:
            print(
                f"{req} BLIZZARD too many requests error on {self.REGION} {str(connectedRealmId)} realm data, sleep 30 min and exit"
            )
            time.sleep(30 * 60)
            exit(1)
        elif req.status_code != 200:
            print(
                f"{req} BLIZZARD error getting {self.REGION} {str(connectedRealmId)} realm data"
            )
            exit(1)

        # this auto updates self.upload_timers for each realm
        if "Last-Modified" in dict(req.headers):
            try:
                lastUploadTimeRaw = dict(req.headers)["Last-Modified"]
                self.update_local_timers(connectedRealmId, lastUploadTimeRaw)
            except Exception as ex:
                print(f"The exception was:", ex)

        auction_info = req.json()
        return auction_info["auctions"]

    def update_local_timers(self, dataSetID, lastUploadTimeRaw):
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

    #### GENERAL USE FUNCTIONS ####
    def send_discord_message(self, message):
        send_discord_message(message, self.WEBHOOK_URL)
