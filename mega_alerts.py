#!/usr/bin/python3
from __future__ import print_function
import time, json, random, os, sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils.helpers import (
    create_oribos_exchange_pet_link,
    create_oribos_exchange_item_link,
    get_wow_russian_realm_ids,
    create_embed,
    split_list,
)
from PyQt5.QtCore import QThread, pyqtSignal
import utils.mega_data_setup


# Add at the beginning of the file, after imports
class StreamToFile:
    # add docstring here if needed
    def __init__(self, filepath):
        """
        Initialize the StreamToFile instance for redirecting console output.
        
        Ensures that the specified log directory exists, clears any existing log file by writing a new
        header with the current timestamp, and redirects both standard output and error streams to the
        log file.
        
        Args:
            filepath: The path to the log file where console output will be recorded.
        """
        self.filepath = filepath
        self.terminal_out = sys.stdout
        self.terminal_err = sys.stderr
        # Ensure log directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        # Clear previous log file
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(f"=== Log started at {datetime.now()} ===\n")

        # Redirect both stdout and stderr
        sys.stdout = self
        sys.stderr = self

    # add docstring here if needed
    def write(self, text):
        """
        Writes the provided text to the terminal and appends it to the log file.
        
        This method outputs the text using the terminal stream and also appends it to the
        log file specified by the object's file path.
        """
        self.terminal_out.write(text)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(text)

    # add docstring here if needed
    def flush(self):
        """
        Flush the terminal output and error streams.
        
        Ensures that any buffered data is written immediately to both the standard output and error.
        """
        self.terminal_out.flush()
        self.terminal_err.flush()


class Alerts(QThread):
    completed = pyqtSignal(int)
    progress = pyqtSignal(str)

    # add docstring here if needed
    def __init__(
        self,
        path_to_data_files=None,
        path_to_desired_items=None,
        path_to_desired_pets=None,
        path_to_desired_ilvl_items=None,
        path_to_desired_ilvl_list=None,
    ):
        """
        Initializes an Alerts instance for monitoring auction data and generating alerts.
        
        This constructor sets up the file paths for auction data and filtering criteria,
        including desired items, pets, and item-level specifications. It also configures
        the logging system by creating a log file and a stream handler that redirects
        both standard output and error streams to the log file.
        
        Args:
            path_to_data_files: Optional path to the directory or file containing auction data.
            path_to_desired_items: Optional path to the configuration file listing desired items.
            path_to_desired_pets: Optional path to the configuration file listing desired pets.
            path_to_desired_ilvl_items: Optional path to the file specifying desired items by item level.
            path_to_desired_ilvl_list: Optional path to the file specifying desired item level thresholds.
        """
        super(Alerts, self).__init__()
        self.running = True
        self.path_to_data_files = path_to_data_files
        self.path_to_desired_items = path_to_desired_items
        self.path_to_desired_pets = path_to_desired_pets
        self.path_to_desired_ilvl_items = path_to_desired_ilvl_items
        self.path_to_desired_ilvl_list = path_to_desired_ilvl_list
        self.alert_record = []

        # Setup logging
        log_path = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "logs")
        os.makedirs(log_path, exist_ok=True)
        log_file = os.path.join(
            log_path, f"mega_alerts_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        # Create stream handler that captures both stdout and stderr
        self.stream_handler = StreamToFile(log_file)
        print(f"Starting Mega Alerts at {datetime.now()}")
        print(f"Log file created at: {log_file}")

    # add docstring here if needed
    def run(self):
        #### FUNCTIONS ####
        # add docstring here if needed
        """
        Executes the alert processing thread.
        
        This method initializes and coordinates the alert system by defining several
        nested helper functions to fetch, filter, and format auction house listings.
        It first sets a brief startup delay to avoid API spamming, then loads global
        data and configuration. Depending on the debug mode, it either runs a single
        fetch of data per realm or enters a continuous loop that concurrently retrieves
        auction data from multiple realms, processes the listings, and sends alerts via
        Discord embeds. Progress updates and completion signals are emitted to track
        the alert process.
        """
        def pull_single_realm_data(connected_id):
            auctions = mega_data.get_listings_single(connected_id)
            clean_auctions = clean_listing_data(auctions, connected_id)
            if not clean_auctions or len(clean_auctions) == 0:
                return

            russian_realms = get_wow_russian_realm_ids()
            # construct message
            suffix = (
                " **(RU)**\n"
                if clean_auctions[0]["realmID"] in russian_realms
                else "\n"
            )
            is_russian_realm = (
                "**(Russian Realm)**"
                if clean_auctions[0]["realmID"] in russian_realms
                else ""
            )

            # add details on each snipe to the message
            embed_fields = []
            for auction in clean_auctions:
                if not self.running:
                    break

                if "itemID" in auction:
                    id_msg = f"`itemID:` {auction['itemID']}\n"
                    saddlebag_link_id = auction["itemID"]
                    if "tertiary_stats" in auction:
                        item_name = mega_data.DESIRED_ILVL_NAMES[auction["itemID"]]
                        # old method
                        # id_msg += f"`Name:` {item_name}\n"
                        id_msg += f"`ilvl:` {auction['ilvl']}\n"
                        if auction["tertiary_stats"]:
                            id_msg += f"`tertiary_stats:` {auction['tertiary_stats']}\n"
                    elif auction["itemID"] in mega_data.ITEM_NAMES:
                        item_name = mega_data.ITEM_NAMES[auction["itemID"]]
                        # old method
                        # id_msg += f"`Name:` {item_name}\n"
                    else:
                        item_name = "Unknown Item"
                        # old method
                        # id_msg += f"`Name:` {item_name}\n"
                    embed_name = item_name
                    if (
                        "required_lvl" in auction
                        and auction["required_lvl"] is not None
                    ):
                        id_msg += f"`required_lvl:` {auction['required_lvl']}\n"
                    if "tertiary_stats" in auction:
                        id_msg += f"`bonus_ids:` {list(auction['bonus_ids'])}\n"
                else:
                    id_msg = f"`petID:` {auction['petID']}\n"
                    saddlebag_link_id = auction["petID"]
                    if auction["petID"] in mega_data.PET_NAMES:
                        pet_name = mega_data.PET_NAMES[auction["petID"]]
                        # old method
                        # id_msg += f"`Name:` {pet_name}\n"
                    else:
                        pet_name = "Unknown Pet"
                        # old method
                        # id_msg += f"`Name:` {pet_name}\n"
                    if "pet_level" in auction:
                        id_msg += f"`pet_level:` {auction['pet_level']}\n"
                    if "quality" in auction:
                        id_msg += f"`quality:` {auction['quality']}\n"
                    if "breed" in auction:
                        id_msg += f"`breed:` {auction['breed']}\n"

                    embed_name = pet_name

                message = ""
                # old method
                # message += f"`region:` {mega_data.REGION}` realmID:` {auction['realmID']} {is_russian_realm}\n"
                # message += f"`realmNames`: {auction['realmNames']}{suffix}\n"
                message += id_msg

                # Add item links, if available
                link_label = (
                    "Wowhead link"
                    if mega_data.WOWHEAD_LINK and "itemID" in auction
                    else "Undermine link"
                )
                link_url = (
                    f"https://www.wowhead.com/item={auction['itemID']}"
                    if mega_data.WOWHEAD_LINK and "itemID" in auction
                    else auction["itemlink"]
                )
                if not mega_data.NO_LINKS:
                    message += f"[{link_label}]({link_url})\n"
                    message += f"[Saddlebag link](https://saddlebagexchange.com/wow/item-data/{saddlebag_link_id})\n"
                    message += f"[Where to Sell](https://saddlebagexchange.com/wow/export-search?itemId={saddlebag_link_id})\n"
                # Add price info, if available
                price_type = (
                    "bid_prices" if "bid_prices" in auction else "buyout_prices"
                )
                message += f"`{price_type}`: {auction[price_type]}\n"

                # send alerts
                if auction not in self.alert_record:
                    # # old method one message per item
                    # mega_data.send_discord_message(message)
                    embed_fields.append(
                        {
                            "name": embed_name,
                            "value": message,
                            "inline": True,
                        }
                    )
                    self.alert_record.append(auction)
                else:
                    print(f"Already sent this alert {auction}")

            if len(embed_fields) != 0:
                # new embed method one message per realm
                desc = f"**region:** {mega_data.REGION}\n"
                desc += (
                    f"**realmID:** {clean_auctions[0]['realmID']} {is_russian_realm}\n"
                )
                desc += f"**realmNames:** {clean_auctions[0]['realmNames']}{suffix}"

                # split it up so message is not too long
                for chunk in split_list(embed_fields, 10):
                    item_embed = create_embed(
                        f"{mega_data.REGION} SNIPE FOUND!", desc, chunk
                    )
                    mega_data.send_discord_embed(item_embed)

        # add docstring here if needed
        def clean_listing_data(auctions, connected_id):
            """
            Processes auction listings to filter and format data for alert messages.
            
            This function iterates over a list of auction listings and applies filtering criteria to
            identify desirable regular items, battle pets, and item-level entries. It extracts bid and
            buyout prices for each matching item and organizes them into structured dictionaries and
            lists. If any filtered results are found, it returns formatted alert messages; otherwise,
            an informational message is printed and no value is returned.
            
            Args:
                auctions: A list of dictionaries representing auction listings with item and price data.
                connected_id: An identifier for the connected auction realm, used in log messages.
            
            Returns:
                Formatted alert messages with the filtered auction data if matches are found, otherwise None.
            """
            all_ah_buyouts = {}
            all_ah_bids = {}
            pet_ah_buyouts = {}
            pet_ah_bids = {}
            ilvl_ah_buyouts = []
            pet_ilvl_ah_buyouts = []

            if len(auctions) == 0:
                print(f"no listings found on {connected_id} of {mega_data.REGION}")
                return

            # add docstring here if needed
            def add_price_to_dict(price, item_id, price_dict, is_pet=False):
                """
                Adds a normalized price to the dictionary if it is below the desired threshold.
                
                Evaluates the given price against a threshold defined in mega_data (using DESIRED_PETS for pets
                or DESIRED_ITEMS for other items). If the price is below the threshold (after scaling by 10000),
                its normalized value (price divided by 10000) is added to the list for the given item_id in price_dict,
                provided it is not already present.
                  
                Parameters:
                    price: The price to evaluate.
                    item_id: Identifier for the item or pet.
                    price_dict: Dictionary mapping item identifiers to lists of normalized prices.
                    is_pet: Optional; indicates whether the item is a pet (defaults to False).
                """
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

                    if "unit_price" in item:
                        price = item["unit_price"]
                        add_price_to_dict(price, item_id, all_ah_buyouts)

                # all caged battle pets have item id 82800
                elif item_id == 82800:
                    # desired pets
                    if item["item"]["pet_species_id"] in mega_data.DESIRED_PETS:
                        pet_id = item["item"]["pet_species_id"]
                        price = 10000000 * 10000

                        if "bid" in item and mega_data.SHOW_BIDPRICES == "true":
                            price = item["bid"]
                            add_price_to_dict(price, pet_id, pet_ah_bids, is_pet=True)

                        if "buyout" in item:
                            price = item["buyout"]
                            add_price_to_dict(
                                price, pet_id, pet_ah_buyouts, is_pet=True
                            )

                    # desired pet ilvl items
                    if item["item"]["pet_species_id"] in [
                        pet["petID"] for pet in mega_data.DESIRED_PET_ILVL_LIST
                    ]:
                        pet_ilvl_item_info = check_pet_ilvl_stats(
                            item,
                            mega_data.DESIRED_PET_ILVL_LIST,
                        )
                        if pet_ilvl_item_info:
                            pet_ilvl_ah_buyouts.append(pet_ilvl_item_info)

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
                or pet_ilvl_ah_buyouts
            ):
                print(
                    f"no listings found matching desires on {connected_id} of {mega_data.REGION}"
                )
                return
            else:
                print(f"Found matches on {connected_id} of {mega_data.REGION}!!!")
                return format_alert_messages(
                    all_ah_buyouts,
                    all_ah_bids,
                    connected_id,
                    pet_ah_buyouts,
                    pet_ah_bids,
                    list(ilvl_ah_buyouts),
                    pet_ilvl_ah_buyouts,
                )

        # add docstring here if needed
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
            """
            Evaluates an auction item against bonus stat and level criteria.
            
            This function inspects an auction's item details and determines whether it meets
            specified conditions based on bonus IDs, tertiary stats (sockets, leech, avoidance,
            and speed), and item level thresholds. It extracts the effective required level from
            item modifiers if available, computes an adjusted item level using provided increments,
            and compares both against desired minimum and maximum thresholds. The function also
            verifies that the item's bonus configuration matches the desired specification, with
            an option for permissive matching when indicated.
            
            Args:
                auction: A dictionary with auction details, including an "item" sub-dictionary
                         that must contain bonus lists and optional modifiers.
                socket_ids: A set of bonus stat IDs representing socket attributes.
                leech_ids: A set of bonus stat IDs representing leech attributes.
                avoidance_ids: A set of bonus stat IDs representing avoidance attributes.
                speed_ids: A set of bonus stat IDs representing speed attributes.
                ilvl_addition: A mapping from bonus IDs to additional item level increments.
                DESIRED_ILVL_ITEMS: A dictionary of configuration values including base item levels,
                                    required level ranges, desired tertiary stat flags, bonus list criteria,
                                    and buyout threshold.
                min_ilvl: The minimum acceptable item level.
            
            Returns:
                False if the auction item fails to meet any criteria; otherwise, a dictionary containing:
                    - item_id: The unique identifier of the item.
                    - buyout: The item's buyout price (or converted bid), scaled appropriately.
                    - tertiary_stats: A dictionary indicating the presence of socket, leech, avoidance,
                                      and speed stats.
                    - bonus_ids: The set of bonus IDs associated with the item.
                    - ilvl: The computed item level after applying any increments.
                    - required_lvl: The item's required level.
            """
            if "bonus_lists" not in auction["item"]:
                return False

            # Check for a modifier with type 9 and get its value (modifier 9 value equals required playerLevel)
            required_lvl = None
            for modifier in auction["item"].get("modifiers", []):
                if modifier["type"] == 9:
                    required_lvl = modifier["value"]
                    break

            # if no modifier["type"] == 9 found, use the base required level for report
            if not required_lvl:
                required_lvl = DESIRED_ILVL_ITEMS["base_required_levels"][
                    auction["item"]["id"]
                ]

            item_bonus_ids = set(auction["item"]["bonus_lists"])
            # look for intersection of bonus_ids and any other lists
            tertiary_stats = {
                "sockets": len(item_bonus_ids & socket_ids) != 0,
                "leech": len(item_bonus_ids & leech_ids) != 0,
                "avoidance": len(item_bonus_ids & avoidance_ids) != 0,
                "speed": len(item_bonus_ids & speed_ids) != 0,
            }

            desired_tertiary_stats = {
                "sockets": DESIRED_ILVL_ITEMS["sockets"],
                "leech": DESIRED_ILVL_ITEMS["leech"],
                "avoidance": DESIRED_ILVL_ITEMS["avoidance"],
                "speed": DESIRED_ILVL_ITEMS["speed"],
            }

            # if we're looking for sockets, leech, avoidance, or speed, skip if none of those are present
            # Check if any of the desired stats are True
            if any(desired_tertiary_stats):
                # Check if all the desired stats are present in the tertiary_stats
                for stat, desired in desired_tertiary_stats.items():
                    if desired and not tertiary_stats.get(stat, False):
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

            # skip if ilvl is too high
            if ilvl > DESIRED_ILVL_ITEMS["max_ilvl"]:
                return False

            # skip if required_lvl is too low
            if required_lvl < DESIRED_ILVL_ITEMS["required_min_lvl"]:
                return False

            # skip if required_lvl is too high
            if required_lvl > DESIRED_ILVL_ITEMS["required_max_lvl"]:
                return False

            # # skip if all DESIRED_ILVL_ITEMS["bonus_ids"] are not in item_bonus_ids
            # if DESIRED_ILVL_ITEMS["bonus_lists"] != [] and not all(
            #     bonus_id in item_bonus_ids
            #     for bonus_id in DESIRED_ILVL_ITEMS["bonus_lists"]
            # ):
            #     return False

            # skip no exact match
            if (
                DESIRED_ILVL_ITEMS["bonus_lists"] != []
                and DESIRED_ILVL_ITEMS["bonus_lists"] != [-1]
                and set(DESIRED_ILVL_ITEMS["bonus_lists"]) != set(item_bonus_ids)
            ):
                return False

            # if the bonus_lists is -1, then we need to check if the item has more than 3 bonus IDs
            # this is when someone wants an item at base stats with no level modifiers
            if DESIRED_ILVL_ITEMS["bonus_lists"] == [-1]:
                temp_bonus_ids = set(item_bonus_ids)
                # Remove all tertiary stat bonus IDs
                temp_bonus_ids -= socket_ids
                temp_bonus_ids -= leech_ids
                temp_bonus_ids -= avoidance_ids
                temp_bonus_ids -= speed_ids
                # If more than 3 bonus IDs remain, skip this item
                if len(temp_bonus_ids) > 3:
                    return False

                # some rare ids dont work like this, so we skip them
                bad_ids = [224637]
                if auction["item"]["id"] in bad_ids:
                    return False

            # if no buyout, use bid
            if "buyout" not in auction and "bid" in auction:
                auction["buyout"] = auction["bid"]

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
                    "required_lvl": required_lvl,
                }

        # add docstring here if needed
        def format_alert_messages(
            all_ah_buyouts,
            all_ah_bids,
            connected_id,
            pet_ah_buyouts,
            pet_ah_bids,
            ilvl_ah_buyouts,
            pet_ilvl_ah_buyouts,
        ):
            """
            Formats auction alert messages from various auction house data.
            
            Constructs a list of alert messages from buyout and bid data for items and pets,
            including those with item or pet level details. It leverages realm names obtained
            via the connected identifier to generate item and pet links and organizes each alert
            as a dictionary ready for notification output.
            
            Args:
                all_ah_buyouts: Dictionary mapping item IDs to auction data for buyout listings.
                all_ah_bids: Dictionary mapping item IDs to auction data for bid listings.
                connected_id: Identifier used to retrieve realm names.
                pet_ah_buyouts: Dictionary mapping pet IDs to auction data for pet buyout listings.
                pet_ah_bids: Dictionary mapping pet IDs to auction data for pet bid listings.
                ilvl_ah_buyouts: List of auction data dictionaries with item level details.
                pet_ilvl_ah_buyouts: List of auction data dictionaries with pet level details.
            
            Returns:
                A list of dictionaries, each representing a formatted alert message.
            """
            results = []
            realm_names = mega_data.get_realm_names(connected_id)
            for itemID, auction in all_ah_buyouts.items():
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
                        "buyout",
                    )
                )

            for petID, auction in pet_ah_buyouts.items():
                # use instead of item name
                itemlink = create_oribos_exchange_pet_link(
                    realm_names[0], petID, mega_data.REGION
                )
                results.append(
                    results_dict(
                        auction,
                        itemlink,
                        connected_id,
                        realm_names,
                        petID,
                        "petID",
                        "buyout",
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
                        auction,
                        itemlink,
                        connected_id,
                        realm_names,
                        itemID,
                        "itemID",
                        "buyout",
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
                            auction,
                            itemlink,
                            connected_id,
                            realm_names,
                            petID,
                            "petID",
                            "bid",
                        )
                    )

            # Add new section for pet level snipes
            for auction in pet_ilvl_ah_buyouts:
                petID = auction["pet_species_id"]
                # use instead of item name
                itemlink = create_oribos_exchange_pet_link(
                    realm_names[0], petID, mega_data.REGION
                )
                results.append(
                    pet_ilvl_results_dict(
                        auction,
                        itemlink,
                        connected_id,
                        realm_names,
                        petID,
                        "petID",
                        "buyout",
                    )
                )

            # end of the line alerts go out from here
            return results

        # add docstring here if needed
        def results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
            """
            Constructs a dictionary summarizing auction details.
            
            Sorts the provided auction list in-place to determine the minimum price and returns a
            dictionary containing regional and realm metadata, an item identifier under a dynamic key
            (from idType), the item link, the minimum price, and a JSON-encoded list of prices under a
            dynamic key (from priceType, appended with '_prices').
            
            Parameters:
                auction: List of auction price values. The list is sorted in-place.
                itemlink: String representing the link to the auction item.
                connected_id: Identifier for the connected realm.
                realm_names: Name or collection of names of the realm(s).
                id: Identifier value for the auctioned item.
                idType: String used as the key for the item identifier in the returned dictionary.
                priceType: String used to form the key for the JSON-encoded auction prices.
            
            Returns:
                A dictionary with keys "region", "realmID", "realmNames", a dynamic key for the
                item identifier, "itemlink", "minPrice", and a dynamic key for the JSON-encoded
                list of auction prices.
            """
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

        # add docstring here if needed
        def ilvl_results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
            """
            Assemble auction item level details into a formatted dictionary.
            
            This function constructs a dictionary from auction data for alert processing.
            It extracts tertiary statistics from the auction, populating dynamic keys for the item
            identifier and price based on the provided idType and priceType. The returned dictionary
            includes region, realm information, item link, price details, bonus IDs, item level, and
            required level.
            
            Args:
                auction (dict): Auction data containing keys such as 'tertiary_stats', 'bonus_ids', 
                    'ilvl', 'required_lvl', and a price value accessed via priceType.
                itemlink (str): A string representing the auction item's link.
                connected_id: Identifier for the connected realm.
                realm_names: Names of the realms associated with the auction.
                id: The item or pet identifier to include under a dynamic key.
                idType (str): The key name to assign to the identifier in the result.
                priceType (str): The key used to fetch the price from auction data and to form a dynamic
                    price key in the result.
            
            Returns:
                dict: A dictionary containing the aggregated auction details.
            """
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
                "required_lvl": auction["required_lvl"],
            }

        # add docstring here if needed
        def pet_ilvl_results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
            """
            Formats pet auction data into a dictionary for alert notifications.
            
            This function constructs a dictionary from pet auction details by combining fixed
            fields such as region, connected realm information, and item link with dynamic keys
            generated from the provided idType and priceType parameters. The auction data should
            include 'buyout', 'current_level', 'quality', and 'breed' keys corresponding to pet
            pricing and attributes.
            
            Args:
                auction (dict): Auction data containing 'buyout', 'current_level', 'quality', and 'breed'.
                itemlink: A reference link for the auctioned pet.
                connected_id: Identifier for the connected realm.
                realm_names: Names of realms associated with the auction data.
                id: The identifier value to be assigned to the dynamic key based on idType.
                idType (str): Key name for the identifier in the result.
                priceType (str): Prefix for the price key; the actual key will be '{priceType}_prices'.
            
            Returns:
                dict: A dictionary formatted for pet level snipe alerts.
            """
            return {
                "region": mega_data.REGION,
                "realmID": connected_id,
                "realmNames": realm_names,
                f"{idType}": id,
                "itemlink": itemlink,
                "minPrice": auction["buyout"],
                f"{priceType}_prices": auction["buyout"],
                "pet_level": auction["current_level"],
                "quality": auction["quality"],
                "breed": auction["breed"],
            }

        # add docstring here if needed
        def check_pet_ilvl_stats(item, desired_pet_list):
            """
            Determines if a pet auction listing meets the desired criteria.
            
            This function checks whether a pet listing from the auction house satisfies specific criteria,
            including matching the desired pet species, minimum level, quality threshold, breed exclusions, 
            and a maximum acceptable buyout price (with the price converted from copper to the unit used in 
            the criteria). It returns a dictionary with the pet details if all criteria are met, or None otherwise.
            
            Args:
                item (dict): Auction house item data from the Blizzard API.
                desired_pet_list (list): List of dictionaries representing desired pet criteria. Each dictionary
                                         should contain keys such as 'petID', 'minLevel', 'minQuality',
                                         'excludeBreeds', and 'price'.
            
            Returns:
                dict: A dictionary with pet details including species ID, current level, buyout price, quality,
                      and breed if the listing satisfies all criteria; otherwise, None.
            """
            # Get the pet species ID from the item data
            pet_species_id = item["item"]["pet_species_id"]

            # Find matching desired pet entry
            desired_pet = next(
                (pet for pet in desired_pet_list if pet["petID"] == pet_species_id),
                None,
            )

            if not desired_pet:
                return None

            # Check if pet meets level requirement
            pet_level = item["item"].get("pet_level")
            if pet_level is None or pet_level < desired_pet["minLevel"]:
                return None

                # Check if quality meets requirement
            if item["item"]["pet_quality_id"] < desired_pet["minQuality"]:
                return None

            # Check if breed is excluded
            # https://www.warcraftpets.com/wow-pet-battles/breeds/
            # 4        14 are the best power
            # 5 15 are the best speed
            # 6 16 are the best health
            if item["item"]["pet_breed_id"] in desired_pet["excludeBreeds"]:
                return None

            # Check if price meets requirement (buyout price should be less than desired price)
            buyout = item.get("buyout")
            if buyout is None or buyout / 10000 > desired_pet["price"]:
                return None

            # If we get here, the pet matches all criteria
            return {
                "pet_species_id": pet_species_id,
                "current_level": item["item"]["pet_level"],
                "buyout": item["buyout"] / 10000,
                "quality": item["item"]["pet_quality_id"],
                "breed": item["item"]["pet_breed_id"],
            }

        #### MAIN ####
        # add docstring here if needed
        def main():
            """
            Dispatches auction alerts based on upload schedules in a continuous loop.
            
            This routine repeatedly checks the current minute to determine if auction data for any realms is due for processing.
            It resets the alert record at the start of the hour if configured, and then identifies realms with expected data updates.
            If extra alerts are enabled and the current minute matches the extra schedule, all realms are processed.
            For each qualifying realm, a task is dispatched in parallel to fetch and process auction data.
            If no realms match the update window, the routine emits a progress update and waits briefly before rechecking.
            Once the running flag is disabled, it signals that the alerts have stopped and completes the operation.
            """
            while self.running:
                current_min = int(datetime.now().minute)

                # refresh alerts 1 time per hour
                if current_min == 1 and mega_data.REFRESH_ALERTS:
                    print(self.alert_record)
                    print("\n\nClearing Alert Record\n\n")
                    self.alert_record = []

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
                            realm["dataSetID"]
                            for realm in mega_data.get_upload_time_list()
                        ]

                if matching_realms != []:
                    self.progress.emit("Sending alerts!")
                    pool = ThreadPoolExecutor(max_workers=mega_data.THREADS)
                    for connected_id in matching_realms:
                        pool.submit(pull_single_realm_data, connected_id)
                    pool.shutdown(wait=True)

                else:
                    self.progress.emit(
                        f"The updates will come\non min {mega_data.get_upload_time_minutes()}\nof each hour."
                    )
                    print(
                        f"Blizzard API data only updates 1 time per hour. The updates will come on minute {mega_data.get_upload_time_minutes()} of each hour. "
                        + f"{datetime.now()} is not the update time. "
                    )
                    time.sleep(20)

            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)

        # add docstring here if needed
        def main_single():
            # run everything once slow
            """
            Executes a single iteration of auction data fetching and processing across realms.
            
            This function iterates over the unique server identifiers defined in the auction house
            configuration and invokes the routine to fetch and process auction data for each realm.
            It is primarily used for debugging and one-time checks.
            """
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pull_single_realm_data(connected_id)

        # add docstring here if needed
        def main_fast():
            """
            Runs a fast round of alert processing concurrently across all realms.
            
            Emits a progress update and dispatches tasks to check auction data for each unique realm using a thread pool, waiting for all tasks to complete.
            """
            self.progress.emit("Sending alerts!")
            # run everything once fast
            pool = ThreadPoolExecutor(max_workers=mega_data.THREADS)
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pool.submit(pull_single_realm_data, connected_id)
            pool.shutdown(wait=True)

        self.progress.emit("Setting data and\nconfig variables!")
        print("Sleep 10 sec on start to avoid spamming the api")
        time.sleep(10)

        if not self.running:
            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)
            return

        #### GLOBALS ####
        mega_data = utils.mega_data_setup.MegaData(
            self.path_to_data_files,
            self.path_to_desired_items,
            self.path_to_desired_pets,
            self.path_to_desired_ilvl_items,
            self.path_to_desired_ilvl_list,
        )

        if not self.running:
            self.progress.emit("Stopped alerts!")
            self.completed.emit(1)
            return

        # show details on run
        print(
            f"Blizzard API data only updates 1 time per hour.\n"
            + f"The updates for region '{mega_data.REGION}' for '{mega_data.FACTION}' faction AH will come on minute {mega_data.get_upload_time_minutes()} of each hour.\n"
            + f"{datetime.now()} may not the update time. "
            + "But we will run once to get the current data so no one asks me about the waiting time.\n"
            + "After the first run we will trigger once per hour when the new data updates.\n"
            + f"Running {mega_data.THREADS} concurrent api calls\n"
            + f"checking for items {mega_data.DESIRED_ITEMS}\n"
            + f"or pets {mega_data.DESIRED_PETS}\n"
            + f"or ilvl items from list {mega_data.DESIRED_ILVL_LIST}\n"
            + f"or pet ilvl items from list {mega_data.DESIRED_PET_ILVL_LIST}\n"
        )

        # start app here
        if mega_data.DEBUG:
            mega_data.send_discord_message(
                "DEBUG MODE: starting mega alerts to run once and then exit operations"
            )
            # for debugging one realm at a time
            main_single()
        else:
            mega_data.send_discord_message(
                "🟢Starting mega alerts and scan all AH data instantly.🟢\n"
                + "🟢These first few messages might be old.🟢\n"
                + "🟢All future messages will release seconds after the new data is available.🟢"
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


if __name__ == "__main__":
    fun = Alerts()
    fun.run()
