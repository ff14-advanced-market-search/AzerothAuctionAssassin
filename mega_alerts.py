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
        Initialize the StreamToFile instance for logging.
        
        Ensures the log file directory exists, clears any previous log file content,
        writes an initial timestamped log header, and redirects standard output and error
        to this instance while preserving the original streams.
        
        Args:
            filepath (str): The path to the log file.
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
        Writes text to the terminal and appends it to the log file.
        
        The provided string is output via the terminal stream and then appended to
        the file specified by the object's filepath attribute.
        """
        self.terminal_out.write(text)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(text)

    # @coderabbitai add docstring here if needed and remove this comment after
    def flush(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Flush the terminal output and error streams.
        
        Ensures that both the output and error buffers are emptied by flushing the associated streams.
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
        Initialize an Alerts instance with configuration paths and logging setup.
        
        This constructor initializes instance variables for various data file paths and flags the
        instance as running. It also configures logging by creating a timestamped log file in the
        "AzerothAuctionAssassinData/logs" directory relative to the current working directory and
        sets up a stream handler to capture both stdout and stderr. Startup messages are printed
        to indicate the start of the alert system and the log file location.
        
        Parameters:
            path_to_data_files: Optional; path to the file or directory containing auction data.
            path_to_desired_items: Optional; path to the file listing desired auction items.
            path_to_desired_pets: Optional; path to the file listing desired auction pets.
            path_to_desired_ilvl_items: Optional; path to the file listing items with specific item levels.
            path_to_desired_ilvl_list: Optional; path to the file containing desired item level specifications.
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
        """
        Run the auction alerts system in a dedicated thread.
        
        This method initializes configuration and data components required for monitoring the 
        auction house, then continuously checks for updates based on timing rules. Depending 
        on debug settings and scheduled update times, it fetches auction data concurrently, 
        formats alert messages, and sends notifications via Discord. Progress updates and a 
        completion signal are emitted as the thread runs.
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
            """Process auction listings and return formatted alert messages.
            
            This function filters a list of auction listings using thresholds defined in a global
            configuration (mega_data). It categorizes regular items, pets, and items for item level
            (ilvl) snipe by aggregating bid and buyout prices (normalized by dividing by 10,000).
            If matching listings are found, it returns structured alert messages via a helper
            formatter; otherwise, it prints an informational message and returns None.
            
            Args:
                auctions: List of dictionaries representing auction listings.
                connected_id: Identifier for the auction realm or connection.
            
            Returns:
                Formatted alert messages (e.g., a structured dictionary) if matching listings are found;
                otherwise, None.
            """
            
            """Add a normalized price to the given price dictionary if it falls below the threshold.
            
            For pet items (when is_pet is True), the price is compared against a pet-specific threshold;
            otherwise, it is compared with the regular item threshold. The price is normalized by dividing
            by 10,000 and is added to the dictionary for the given item if not already present.
            
            Args:
                price: The raw price value from an auction listing.
                item_id: Identifier for the item (or pet).
                price_dict: Dictionary mapping item identifiers to lists of normalized prices.
                is_pet: Boolean indicating whether the item is a pet.
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
                Add a valid converted price to the dictionary.
                
                If the provided price is below the desired threshold for the specified item, the price is
                converted by dividing by 10000 and added to price_dict under item_id. For pet items (when
                is_pet is True), the threshold is taken from mega_data.DESIRED_PETS; otherwise, it is
                taken from mega_data.DESIRED_ITEMS. Only unique converted price values are stored.
                    
                Args:
                    price: The raw price value.
                    item_id: The identifier for the item.
                    price_dict: A dictionary mapping item IDs to lists of normalized prices.
                    is_pet: Flag indicating whether the item is a pet.
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
            Format pet auction alert data for snipe results.
            
            Constructs a dictionary containing formatted pet auction data used for alert notifications.
            The returned dictionary includes region information, realm details, auction buyout price (both as
            a minimum price and under a dynamic price key), pet level, quality, and breed. A dynamic key for
            the auction identifier is created based on the provided idType.
            
            Args:
                auction (dict): Auction data with keys "buyout", "current_level", "quality", and "breed".
                itemlink (str): A string representing the hyperlink for the pet auction item.
                connected_id: Identifier for the connected realm.
                realm_names: Collection of realm names.
                id: Auction identifier value to be included under the dynamic key.
                idType (str): Key name for storing the auction identifier in the result.
                priceType (str): Prefix used to form the key for price details in the result.
            
            Returns:
                dict: Formatted pet auction alert data.
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
            Determines whether a pet auction listing meets the desired criteria.
            
            This function validates an auction entry for a pet against a set of criteria defined
            in the desired pet list. It checks for a matching pet species ID, a minimum pet level,
            a minimum pet quality, exclusion based on breed, and an acceptable buyout price. If
            all conditions are met, it returns a dictionary containing the pet's details; otherwise,
            it returns None.
            
            Args:
                item (dict): Auction data for a pet, including attributes like pet level, quality,
                    breed ID, and buyout price.
                desired_pet_list (list): A list of criteria dictionaries where each dictionary
                    specifies keys such as 'petID', 'minLevel', 'minQuality', 'excludeBreeds', and
                    'price' to define acceptable pet characteristics.
            
            Returns:
                dict: A dictionary with keys 'pet_species_id', 'current_level', 'buyout', 'quality',
                    and 'breed' if the auction satisfies all specified criteria; otherwise, None.
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
            Runs the main alert loop for auction alert processing.
            
            This method continuously checks the current minute to determine if it's time to send auction alerts. Depending on the current time and configured alert intervals, it refreshes the alert record once per hour and uses a thread pool to concurrently fetch and process auction data for matching realms. Progress messages are emitted throughout the process, and once the loop ends, a completion signal is sent.
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
            Executes a single round of auction data retrieval for each game realm.
            
            Iterates over unique realm identifiers defined in the WOW_SERVER_NAMES and fetches auction listings for each realm using pull_single_realm_data.
            """
            for connected_id in set(mega_data.WOW_SERVER_NAMES.values()):
                pull_single_realm_data(connected_id)

        # @coderabbitai add docstring here if needed and remove this comment after
        def main_fast():
            # @coderabbitai add docstring here if needed and remove this comment after
            """
            Runs a fast, concurrent alert update across all connected realms.
            
            This method emits a progress update and uses a thread pool to fetch and process
            auction data from each unique realm. It submits each realm's data-processing task
            and waits for all tasks to complete before finishing.
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
