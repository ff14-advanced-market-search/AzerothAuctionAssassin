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
    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self, filepath):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initialize the stream redirection to a log file.
        
        Sets the provided file path for logging, ensures the directory exists, and clears
        any previous log content by writing a start message with the current timestamp.
        Also saves the original sys.stdout and sys.stderr, then redirects them to this instance.
         
        Args:
            filepath: The file system path to the log file.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def write(self, text):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Writes text to both the terminal and a log file.
        
        This method outputs the provided text to the terminal and simultaneously appends it to a log file at the location specified by the object's filepath.
          
        Args:
            text (str): The text to be output.
        """
        self.terminal_out.write(text)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(text)

    # @coderabbitai add docstring here if needed and remove this comment after
    def flush(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Flushes the terminal's output and error streams.
        
        This method calls flush() on both the output and error stream objects
        to ensure that all buffered text is immediately written out.
        """
        self.terminal_out.flush()
        self.terminal_err.flush()


class Alerts(QThread):
    completed = pyqtSignal(int)
    progress = pyqtSignal(str)

    def __init__(
        self,
        path_to_data_files=None,
        path_to_desired_items=None,
        path_to_desired_pets=None,
        path_to_desired_ilvl_items=None,
        path_to_desired_ilvl_list=None,
    ):
        """
        Initializes the Alerts instance and configures logging for auction monitoring.
        
        This constructor sets up file paths for auction data and desired criteria (items, pets, and item levels), initializes an empty alert record, and creates a log file with a timestamped name in the "AzerothAuctionAssassinData/logs" directory. Standard output and error streams are redirected to this log file via a custom stream handler, and startup messages confirming the alert start time and log file location are printed.
            
        Args:
            path_to_data_files (str, optional): Path to the data files containing auction listings.
            path_to_desired_items (str, optional): Path to the file listing auction items to monitor.
            path_to_desired_pets (str, optional): Path to the file listing auction pets to monitor.
            path_to_desired_ilvl_items (str, optional): Path to the file specifying desired item-level items.
            path_to_desired_ilvl_list (str, optional): Path to the file specifying desired item level thresholds.
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

    # @coderabbitai add docstring here if needed and remove this comment after
    def run(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        #### FUNCTIONS ####
        # @coderabbitai add docstring here if needed and remove this comment after
        """Starts the alert system, fetching auction data periodically and sending alerts.
        
        Initializes global configuration and delays startup to avoid API spamming. Depending on the
        debug mode, it either performs a single data fetch or enters a continuous loop to retrieve auction
        listings, process alerts, and emit progress and completion signals.
        """
        
        """Fetch and process auction listings for a specific realm.
        
        Retrieves auction data for the given realm identifier, cleans and formats the listings, and sends
        alerts via embed messages if new matching auctions are found.
        """
        
        """Clean and aggregate auction listings for a given realm.
        
        Processes raw auction data by filtering items and pets based on desired criteria, aggregating pricing
        data for bids and buyouts, and returning formatted alert messages if matches exist.
        """
        
        """Add a price to the corresponding price dictionary if it is below the desired threshold.
        
        Converts the raw price to standard units and updates the dictionary for either regular items or pets,
        ensuring no duplicate price entries are added.
        """
        
        """Validate an auction item against desired item level and bonus criteria.
        
        Checks bonus IDs and calculates the effective item level and required level. Returns a dictionary with
        item details if the auction item meets all specified thresholds; otherwise, returns False.
        """
        
        """Format alert messages for various auction types.
        
        Compiles alert data from different auction categories (regular items, pets, and item-level auctions)
        into structured dictionaries suitable for sending as Discord embed messages.
        """
        
        """Construct alert details for a regular item auction.
        
        Sorts the auction prices to determine the minimum value and returns a dictionary containing regional info,
        realm details, item links, and pricing information.
        """
        
        """Construct alert details for an item-level auction.
        
        Returns a dictionary with detailed auction information, including bonus statistics, computed item level,
        and required level, formatted for alert messaging.
        """
        
        """Format pet-level auction results for alerts.
        
        Returns a dictionary containing pet auction details such as level, quality, breed, and pricing, along with
        regional and realm information.
        """
        
        KEEP_EXISTING
        
        """Run the continuous alert fetching loop.
        
        Monitors the current time to trigger auction data fetches at scheduled intervals, clears the alert record
        hourly, and dispatches concurrent API calls for matching realms. Emits progress notifications and
        terminates when alerts are stopped.
        """
        
        """Execute a single round of auction data retrieval.
        
        Processes auction listings for each realm once, intended for debugging and validation purposes.
        """
        
        """Quickly fetch auction data for all realms concurrently.
        
        Initiates parallel API calls to fetch auction data in a single fast run and emits progress messages.
        """
        def pull_single_realm_data(connected_id):
            # @coderabbitai add docstring here if needed and remove this comment after
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

        # @coderabbitai add docstring here if needed and remove this comment after
        def clean_listing_data(auctions, connected_id):
            # @coderabbitai add docstring here if needed and remove this comment after
            """
            Cleans and organizes auction listings for alert generation.
            
            Processes a list of auction entries by filtering regular items, pets, and item level
            snipes based on predefined desired criteria. Aggregates bid and buyout prices for
            each category, and compiles alert messages using formatted data if matches are found.
            Prints status messages indicating whether listings were found or if no matching data
            was available.
            
            Args:
                auctions: List of auction dictionaries to process.
                connected_id: Identifier for the connected realm, used in status messages.
            
            Returns:
                The formatted alert messages if matching listings are found; otherwise, None.
            """
            
            """
            Adds a normalized price to a price dictionary if it is below the desired threshold.
            
            Converts the given price by dividing it by 10,000 and adds it to the provided
            dictionary under the specified item identifier. The function checks against desired
            price limits for items or pets before adding the normalized price, ensuring duplicate
            prices are not inserted.
            
            Args:
                price: The original price value in the smallest monetary unit.
                item_id: Identifier for the item or pet.
                price_dict: Dictionary mapping item identifiers to lists of normalized prices.
                is_pet: Boolean flag indicating whether the item is a pet (default is False).
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

            # @coderabbitai add docstring here if needed and remove this comment after
            def add_price_to_dict(price, item_id, price_dict, is_pet=False):
                # @coderabbitai add docstring here if needed and remove this comment after
                """
                Add a price to the dictionary if it is below the designated threshold.
                
                This function compares the provided price to a threshold (multiplied by 10000) defined
                in mega_data for either items or pets. If the price is below the threshold, it is
                converted by dividing by 10000 and added to the list associated with the item_id in
                price_dict, ensuring that duplicate converted prices are not inserted.
                
                Args:
                    price: The raw price to evaluate.
                    item_id: The identifier for the item or pet.
                    price_dict: A dictionary mapping item identifiers to lists of converted price values.
                    is_pet: A flag indicating whether to use the pet-specific threshold.
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

        def format_alert_messages(
            all_ah_buyouts,
            all_ah_bids,
            connected_id,
            pet_ah_buyouts,
            pet_ah_bids,
            ilvl_ah_buyouts,
            pet_ilvl_ah_buyouts,
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

        def results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
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
                "required_lvl": auction["required_lvl"],
            }

        def pet_ilvl_results_dict(
            auction, itemlink, connected_id, realm_names, id, idType, priceType
        ):
            """
            Format auction data for pet level snipe alerts.
            
            Constructs a standardized dictionary for pet alerts using auction details and
            additional parameters. The keys for the pet identifier and its corresponding price
            are dynamically generated based on the provided idType and priceType.
            
            Args:
                auction: Dictionary containing auction details with keys 'buyout',
                         'current_level', 'quality', and 'breed'.
                itemlink: Pet item link identifier.
                connected_id: Identifier for the connected realm.
                realm_names: Name(s) of the realm where the auction took place.
                id: Identifier for the pet item.
                idType: String used to denote the key name for the pet item ID.
                priceType: String used to denote the key suffix for price details.
            
            Returns:
                dict: A dictionary with formatted alert details including region, realm info,
                      pet level, quality, and breed.
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

        # @coderabbitai add docstring here if needed and remove this comment after
        def check_pet_ilvl_stats(item, desired_pet_list):
            # @coderabbitai add docstring here if needed and remove this comment after
            """
            Checks if a pet auction listing satisfies the specified criteria.
            
            This function verifies that the auction item matches one of the desired pet criteria by
            validating pet species, minimum level, minimum quality, exclusion of specific breeds, and
            price threshold. If all conditions are met, it returns a dictionary with the pet's details;
            otherwise, it returns None.
            
            Args:
                item (dict): Auction listing data containing pet details.
                desired_pet_list (list): List of dictionaries defining desired pet criteria, including
                    keys such as 'petID', 'minLevel', 'minQuality', 'excludeBreeds', and 'price'.
            
            Returns:
                dict or None: A dictionary with pet details—species ID, current level, buyout price (in
                standardized units), quality, and breed—or None if the auction does not meet the criteria.
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
        # @coderabbitai add docstring here if needed and remove this comment after
        def main():
            # @coderabbitai add docstring here if needed and remove this comment after
            """
            Continuously monitors auction timings and dispatches alert tasks.
            
            This function runs in a loop until the running flag is cleared. It checks the
            current minute to decide whether to clear the alert record or to fetch new
            auction data for relevant realms. When the alert criteria are met, it schedules
            data fetching concurrently using a thread pool executor while emitting progress
            updates. Once stopped, it signals completion.
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

        # @coderabbitai add docstring here if needed and remove this comment after
        def main_single():
            # @coderabbitai add docstring here if needed and remove this comment after
            # run everything once slow
            """
            Performs a single iteration of auction data fetching for each realm.
            
            Iterates over the unique realm identifiers from the WoW server names and calls 
            pull_single_realm_data for each, executing the alert logic once in a slower, more 
            thorough manner often used for debugging.
            """
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pull_single_realm_data(connected_id)

        # @coderabbitai add docstring here if needed and remove this comment after
        def main_fast():
            # @coderabbitai add docstring here if needed and remove this comment after
            """Run a fast, concurrent alert fetching process for all realms.
            
            Emits a progress update and concurrently submits tasks using pull_single_realm_data
            for each unique realm via a thread pool. The function blocks until all tasks complete.
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
