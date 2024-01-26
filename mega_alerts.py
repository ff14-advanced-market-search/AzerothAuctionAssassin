#!/usr/bin/python3
from __future__ import print_function
import time, json, random, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils.helpers import (
    create_oribos_exchange_pet_link,
    create_oribos_exchange_item_link,
)
from PyQt5.QtCore import QThread, pyqtSignal
import utils.mega_data_setup

class Alerts(QThread):

    completed = pyqtSignal(int)
    progress = pyqtSignal(str)

    def __init__(self, path_to_data_files=None, path_to_desired_items=None, path_to_desired_pets=None, path_to_desired_ilvl_items=None, path_to_desired_ilvl_list=None):
        super(Alerts,self).__init__()
        self.running=True
        self.path_to_data_files=path_to_data_files
        self.path_to_desired_items= path_to_desired_items
        self.path_to_desired_pets = path_to_desired_pets
        self.path_to_desired_ilvl_items = path_to_desired_ilvl_items
        self.path_to_desired_ilvl_list = path_to_desired_ilvl_list

    def run(self):

        #### FUNCTIONS ####
        def pull_single_realm_data(connected_id):
            auctions = mega_data.get_listings_single(connected_id)
            clean_auctions = clean_listing_data(auctions, connected_id)
            if not clean_auctions:
                return
            for auction in clean_auctions:
                if not self.running:
                    break
            
                if "itemID" in auction:
                    id_msg = f"`itemID:` {auction['itemID']}\n"
                    if "tertiary_stats" in auction:
                        item_name = mega_data.DESIRED_ILVL_NAMES[auction["itemID"]]
                        id_msg += f"`Name:` {item_name}\n"
                        id_msg += f"`ilvl:` {auction['ilvl']}\n"
                        id_msg += f"`tertiary_stats:` {auction['tertiary_stats']}\n"
                        id_msg += f"`bonus_ids:` {list(auction['bonus_ids'])}\n"
                    elif auction["itemID"] in mega_data.ITEM_NAMES:
                        item_name = mega_data.ITEM_NAMES[auction["itemID"]]
                        id_msg += f"`Name:` {item_name}\n"
                else:
                    id_msg = f"`petID:` {auction['petID']}\n"
                    if auction["petID"] in mega_data.PET_NAMES:
                        pet_name = mega_data.PET_NAMES[auction["petID"]]
                        id_msg += f"`Name:` {pet_name}\n"
                if os.getenv("IMPORTANT_EMOJI"):
                    if len(os.getenv("IMPORTANT_EMOJI")) == 1:
                        message = os.getenv("IMPORTANT_EMOJI") * 20 + "\n"
                    else:
                        message = "🔥🔥🔥🔥🔥🟢🟢🟢🟢🟢🟢🟢🔥🔥🔥🔥🔥\n"
                else:
                    message = "==================================\n"
                message += (
                    f"`region:` {mega_data.REGION} "
                    + f"`realmID:` {auction['realmID']} "
                    + id_msg
                    + f"`realmNames`: {auction['realmNames']}\n"
                )
                if mega_data.WOWHEAD_LINK and "itemID" in auction:
                    item_id = auction["itemID"]
                    message += f"[Wowhead link](https://www.wowhead.com/item={item_id})\n"
                else:
                    message += f"[Undermine link]({auction['itemlink']})\n"
                if "bid_prices" in auction:
                    message += f"`bid_prices`: {auction['bid_prices']}\n"
                else:
                    message += f"`buyout_prices`: {auction['buyout_prices']}\n"
                if os.getenv("IMPORTANT_EMOJI"):
                    if len(os.getenv("IMPORTANT_EMOJI")) == 1:
                        message += os.getenv("IMPORTANT_EMOJI") * 20 + "\n"
                    else:
                        message += "🔥🔥🔥🔥🔥🟢🟢🟢🟢🟢🟢🟢🔥🔥🔥🔥🔥\n"
                else:
                    message += "==================================\n"
                if auction not in alert_record:
                    mega_data.send_discord_message(message)
                    alert_record.append(auction)

        def clean_listing_data(auctions, connected_id):
            all_ah_buyouts = {}
            all_ah_bids = {}
            pet_ah_buyouts = {}
            pet_ah_bids = {}
            ilvl_ah_buyouts = []

            def add_price_to_dict(price, item_id, price_dict, is_pet=False):
                if is_pet:
                    if price < mega_data.DESIRED_PETS[item_id] * 10000:
                        if item_id not in price_dict:
                            price_dict[item_id] = [price / 10000]
                        elif price / 10000 not in price_dict[item_id]:
                            price_dict[item_id].append(price / 10000)
                elif price < mega_data.DESIRED_ITEMS[item_id] * 10000:
                    if item_id not in price_dict:
                        price_dict[item_id] = [price / 10000]
                    elif price / 10000 not in price_dict[item_id]:
                        price_dict[item_id].append(price / 10000)

            for item in auctions:
                item_id = item["item"]["id"]

                # regular items
                if item_id in mega_data.DESIRED_ITEMS and item_id != 82800:
                    price = 10000000 * 10000

                    if "bid" in item and mega_data.SHOW_BIDPRICES == "true":
                        price = item["bid"]
                        add_price_to_dict(price, item_id, all_ah_bids)

                    if "buyout" in item:
                        price = item["buyout"]
                        add_price_to_dict(price, item_id, all_ah_buyouts)

                # all caged battle pets have item id 82800
                elif item_id == 82800:
                    if item["item"]["pet_species_id"] in mega_data.DESIRED_PETS:
                        pet_id = item["item"]["pet_species_id"]
                        price = 10000000 * 10000

                        if "bid" in item and mega_data.SHOW_BIDPRICES == "true":
                            price = item["bid"]
                            add_price_to_dict(price, pet_id, pet_ah_bids, is_pet=True)

                        if "buyout" in item:
                            price = item["buyout"]
                            add_price_to_dict(price, pet_id, pet_ah_buyouts, is_pet=True)

                # ilvl snipe items
                if (
                    mega_data.DESIRED_ILVL_ITEMS
                    and item_id in mega_data.DESIRED_ILVL_ITEMS["item_ids"]
                ):
                    ilvl_item_info = check_tertiary_stats_generic(
                        item,
                        mega_data.socket_ids,
                        mega_data.leech_ids,
                        mega_data.avoidance_ids,
                        mega_data.speed_ids,
                        mega_data.ilvl_addition,
                        mega_data.DESIRED_ILVL_ITEMS,
                        mega_data.min_ilvl,
                    )
                    if ilvl_item_info:
                        ilvl_ah_buyouts.append(ilvl_item_info)

                for desired_ilvl_item in mega_data.DESIRED_ILVL_LIST:
                    if item_id in desired_ilvl_item["item_ids"]:
                        ilvl_item_info = check_tertiary_stats_generic(
                            item,
                            mega_data.socket_ids,
                            mega_data.leech_ids,
                            mega_data.avoidance_ids,
                            mega_data.speed_ids,
                            mega_data.ilvl_addition,
                            desired_ilvl_item,
                            desired_ilvl_item["ilvl"],
                        )
                        if ilvl_item_info:
                            ilvl_ah_buyouts.append(ilvl_item_info)

            if not (
                all_ah_buyouts
                or all_ah_bids
                or pet_ah_buyouts
                or pet_ah_bids
                or ilvl_ah_buyouts
            ):
                print(
                    f"no listings found matching items {mega_data.DESIRED_ITEMS} "
                    f"or pets {mega_data.DESIRED_PETS} "
                    f"or items to snipe by ilvl and stats "
                    f"on {connected_id} "
                    f"{mega_data.REGION}"
                )
                return
            else:
                return format_alert_messages(
                    all_ah_buyouts,
                    all_ah_bids,
                    connected_id,
                    pet_ah_buyouts,
                    pet_ah_bids,
                    list(ilvl_ah_buyouts),
                )

        def check_tertiary_stats_generic(
            auction,
            socket_ids,
            leech_ids,
            avoidance_ids,
            speed_ids,
            ilvl_addition,
            DESIRED_ILVL_ITEMS,
            min_ilvl,
        ):
            if "bonus_lists" not in auction["item"]:
                return False
            item_bonus_ids = set(auction["item"]["bonus_lists"])
            # look for intersection of bonus_ids and any other lists
            tertiary_stats = {
                "sockets": len(item_bonus_ids & socket_ids) != 0,
                "leech": len(item_bonus_ids & leech_ids) != 0,
                "avoidance": len(item_bonus_ids & avoidance_ids) != 0,
                "speed": len(item_bonus_ids & speed_ids) != 0,
            }

            # if we're looking for sockets, leech, avoidance, or speed, skip if none of those are present
            if (
                DESIRED_ILVL_ITEMS["sockets"]
                or DESIRED_ILVL_ITEMS["leech"]
                or DESIRED_ILVL_ITEMS["avoidance"]
                or DESIRED_ILVL_ITEMS["speed"]
            ):
                if not (
                    (DESIRED_ILVL_ITEMS["sockets"] and tertiary_stats["sockets"])
                    or (DESIRED_ILVL_ITEMS["leech"] and tertiary_stats["leech"])
                    or (DESIRED_ILVL_ITEMS["avoidance"] and tertiary_stats["avoidance"])
                    or (DESIRED_ILVL_ITEMS["speed"] and tertiary_stats["speed"])
                ):
                    return False

            # get ilvl
            base_ilvl = DESIRED_ILVL_ITEMS["base_ilvls"][auction["item"]["id"]]
            ilvl_addition = [
                ilvl_addition[bonus_id]
                for bonus_id in item_bonus_ids
                if bonus_id in ilvl_addition.keys()
            ]
            if len(ilvl_addition) > 0:
                ilvl = base_ilvl + sum(ilvl_addition)
            else:
                ilvl = base_ilvl

            # skip if ilvl is too low
            if ilvl < min_ilvl:
                return False

            # if we get through everything and still haven't skipped, add to matching
            buyout = round(auction["buyout"] / 10000, 2)
            if buyout > DESIRED_ILVL_ITEMS["buyout"]:
                return False
            else:
                return {
                    "item_id": auction["item"]["id"],
                    "buyout": buyout,
                    "tertiary_stats": tertiary_stats,
                    "bonus_ids": item_bonus_ids,
                    "ilvl": ilvl,
                }

        def format_alert_messages(
            all_ah_buyouts,
            all_ah_bids,
            connected_id,
            pet_ah_buyouts,
            pet_ah_bids,
            ilvl_ah_buyouts,
        ):
            results = []
            realm_names = mega_data.get_realm_names(connected_id)
            for itemID, auction in all_ah_buyouts.items():
                # use instead of item name
                itemlink = create_oribos_exchange_item_link(
                    realm_names[0], itemID, mega_data.REGION
                )
                results.append(
                    results_dict(
                        auction, itemlink, connected_id, realm_names, itemID, "itemID", "buyout"
                    )
                )

            for petID, auction in pet_ah_buyouts.items():
                # use instead of item name
                itemlink = create_oribos_exchange_pet_link(
                    realm_names[0], petID, mega_data.REGION
                )
                results.append(
                    results_dict(
                        auction, itemlink, connected_id, realm_names, petID, "petID", "buyout"
                    )
                )

            for auction in ilvl_ah_buyouts:
                itemID = auction["item_id"]
                # use instead of item name
                itemlink = create_oribos_exchange_item_link(
                    realm_names[0], itemID, mega_data.REGION
                )
                results.append(
                    ilvl_results_dict(
                        auction, itemlink, connected_id, realm_names, itemID, "itemID", "buyout"
                    )
                )

            if mega_data.SHOW_BIDPRICES == "true":
                for itemID, auction in all_ah_bids.items():
                    # use instead of item name
                    itemlink = create_oribos_exchange_item_link(
                        realm_names[0], itemID, mega_data.REGION
                    )
                    results.append(
                        results_dict(
                            auction,
                            itemlink,
                            connected_id,
                            realm_names,
                            itemID,
                            "itemID",
                            "bid",
                        )
                    )

                for petID, auction in pet_ah_bids.items():
                    # use instead of item name
                    itemlink = create_oribos_exchange_pet_link(
                        realm_names[0], petID, mega_data.REGION
                    )
                    results.append(
                        results_dict(
                            auction, itemlink, connected_id, realm_names, petID, "petID", "bid"
                        )
                    )

            # end of the line alerts go out from here
            return results

        def results_dict(auction, itemlink, connected_id, realm_names, id, idType, priceType):
            auction.sort()
            minPrice = auction[0]
            return {
                "region": mega_data.REGION,
                "realmID": connected_id,
                "realmNames": realm_names,
                f"{idType}": id,
                "itemlink": itemlink,
                "minPrice": minPrice,
                f"{priceType}_prices": json.dumps(auction),
            }

        def ilvl_results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
            tertiary_stats = [
                stat for stat, present in auction["tertiary_stats"].items() if present
            ]
            return {
                "region": mega_data.REGION,
                "realmID": connected_id,
                "realmNames": realm_names,
                f"{idType}": id,
                "itemlink": itemlink,
                "minPrice": auction[priceType],
                f"{priceType}_prices": auction[priceType],
                "tertiary_stats": tertiary_stats,
                "bonus_ids": auction["bonus_ids"],
                "ilvl": auction["ilvl"],
            }

        #### MAIN ####
        def main():
            global alert_record
            while self.running:
                current_min = int(datetime.now().minute)

                # refresh alerts 1 time per hour
                if current_min == 1 and mega_data.REFRESH_ALERTS:
                    print("\n\nClearing Alert Record\n\n")
                    alert_record = []

                matching_realms = [
                    realm["dataSetID"]
                    for realm in mega_data.get_upload_time_list()
                    if realm["lastUploadMinute"] + mega_data.SCAN_TIME_MIN
                    <= current_min
                    <= realm["lastUploadMinute"] + mega_data.SCAN_TIME_MAX
                ]
                # mega wants extra alerts
                if mega_data.EXTRA_ALERTS:
                    extra_alert_mins = json.loads(mega_data.EXTRA_ALERTS)
                    if current_min in extra_alert_mins:
                        matching_realms = [
                            realm["dataSetID"] for realm in mega_data.get_upload_time_list()
                        ]

                if matching_realms != []:
                    self.progress.emit("Sending alerts!")
                    pool = ThreadPoolExecutor(max_workers=mega_data.THREADS)
                    for connected_id in matching_realms:
                        pool.submit(pull_single_realm_data, connected_id)
                    pool.shutdown(wait=True)

                else:
                    self.progress.emit(f"The updates will come on minute {list(mega_data.get_upload_time_minutes())[0]} of each hour.")
                    print(
                        f"Blizzard API data only updates 1 time per hour. The updates will come on minute {mega_data.get_upload_time_minutes()} of each hour. "
                        + f"{datetime.now()} is not the update time. "
                        + f"Waiting to run {mega_data.THREADS} concurrent api calls: "
                        + f"checking for items {mega_data.DESIRED_ITEMS} "
                        + f"or pets {mega_data.DESIRED_PETS} "
                        + f"or items to snipe by ilvl and stats "
                    )
                    time.sleep(20)
            
            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)

        def main_single():
            # run everything once slow
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pull_single_realm_data(connected_id)

        def main_fast():
            self.progress.emit("Sending alerts!")
            # run everything once fast
            pool = ThreadPoolExecutor(max_workers=mega_data.THREADS)
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pool.submit(pull_single_realm_data, connected_id)
            pool.shutdown(wait=True)

        self.progress.emit("Setting data and config variables!")
        print("Sleep 10 sec on start to avoid spamming the api")
        time.sleep(10)

        if not self.running:
            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)
            return

        #### GLOBALS ####
        alert_record = []
        mega_data = utils.mega_data_setup.MegaData(
            self.path_to_data_files,
            self.path_to_desired_items,
            self.path_to_desired_pets,
            self.path_to_desired_ilvl_items,
            self.path_to_desired_ilvl_list)

        if not self.running:
            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)
            return

        # start app here
        if os.getenv("DEBUG"):
            mega_data.send_discord_message(
                "DEBUG MODE: starting mega alerts to run once and then exit operations"
            )
            # for debugging one realm at a time
            main_single()
            # # for debugging all realms at once in threads
            # main_fast()
        else:
            mega_data.send_discord_message(
                "🟢Starting mega alerts and scan all AH data instantly.🟢\n"
                + "🟢These first few messages might be old.🟢\n"
                + "🟢All future messages will release seconds after the new data is available.🟢"
            )
            print(
                f"Blizzard API data only updates 1 time per hour. "
                + f"The updates will come on minute {mega_data.get_upload_time_minutes()} of each hour. "
                + f"{datetime.now()} may not the update time. "
                + "But we will run once to get the current data so no one asks me about the waiting time. "
                + "After the first run we will trigger once per hour when the new data updates. "
            )
            time.sleep(1)

            if not self.running:
                self.progress.emit("Stopped alerts!")
                self.completed.emit(1)
                return
        
            # im sick of idiots asking me about the waiting time just run once on startup
            main_fast()

            if not self.running:
                self.progress.emit("Stopped alerts!")
                self.completed.emit(1)
                return
            
            # then run the main loop
            main()

if __name__ == '__main__':
    fun = Alerts()
    fun.run()
