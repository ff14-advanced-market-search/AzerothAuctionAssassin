# added the code at the beginning of the file
# to tell the script that is being invoked from the windows c# binary
# so it knows from where to load the pre-installed packages
# so it can locate them before doing the other imports
import sys

AAT_VERSION = "0.0.2"

windowsApp_Path = None
try:
    if sys.argv[1] == "run-from-windows-bin":
        sys.path.append(f"{sys.argv[2]}")
        sys.path.append(f"{sys.argv[3]}")

        windowsApp_Path = f"{sys.argv[2]}"
    else:
        pass
except Exception as ex:
    pass
# i hate the way that looks but if it isnt broken dont fix it

import breeze_resources
import ctypes
import pandas as pd
import json
from sys import exit
import requests
import os
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QThread, pyqtSignal, QFile, QTextStream
from PyQt5 import QtGui
from PyQt5.QtWidgets import (
    QGridLayout,
    QStackedWidget,
    QMainWindow,
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QListWidget,
    QMessageBox,
    QCheckBox,
    QFileDialog,
    QWidget,
    QScrollArea,
)

if sys.platform == "win32":
    myappid = "mycompany.myproduct.subproduct.version"  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


# make directory if it does not exist
data_folder = os.path.join(os.getcwd(), "AzerothAuctionAssassinData")
if not os.path.exists(data_folder):
    os.makedirs(data_folder)


# @coderabbitai add docstring here if needed and remove this comment after
def save_json_file(path, data):

    """
    Saves JSON data to the specified file.
    
    Writes the provided JSON-serializable data to the given file path using UTF-8 encoding.
    The output is formatted with a 4-space indent and preserves non-ASCII characters.
    
    Args:
        path (str): The file path where the JSON data will be written.
        data: The JSON-serializable data to be saved.
    """
    with open(path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


class RecommendationsRequest(QThread):
    """
    RecommendationsRequest class is designed to request and process recommendations for items based on specified market data.
    Parameters:
        - realm_id (int): Identifier for the realm.
        - region (str): The region of the market data.
        - commodity (str): Type of commodity for market evaluation.
        - desired_avg_price (float): Target average price for the commodity.
        - desired_sales_per_day (int): Expected sales volume per day.
        - item_quality (int): Quality level of the item.
        - required_level (int): Minimum level required for the item use.
        - item_class (int): Class category of the item.
        - item_subclass (int): Subclass category of the item.
        - ilvl (int): Item level indicator.
        - discount_percent (float): Discount rate applied to market value calculations.
        - minimum_market_value (float): Threshold for the lowest acceptable market price.
        - expansion_number (int): Identifier for the game's expansion pack.
    Processing Logic:
        - Initializes base class with super().
        - Creates a dictionary for request data with provided parameters.
        - Sets discount percent and minimum market value as instance variables.
        - Validates 'homeRealmId' ensuring it is greater than 0.
        - Sends a POST request to retrieve item statistics using provided request data.
        - Filters items based on historic market value and calculates recommended prices with a discount.
    """

    completed = pyqtSignal(dict)

    def __init__(
        self,
        realm_id,
        region,
        commodity,
        desired_avg_price,
        desired_sales_per_day,
        item_quality,
        required_level,
        item_class,
        item_subclass,
        ilvl,
        discount_percent,
        minimum_market_value,
        expansion_number,
    ):
        """
        Initialize a market data request with auction parameters.
        
        This initializer creates a request data dictionary from the provided parameters
        and stores the discount rate and minimum market value as instance attributes.
        
        Parameters:
            realm_id (int): The identifier for the realm.
            region (str): The region for retrieving market data.
            commodity (str): The commodity type to evaluate.
            desired_avg_price (float): The target average price.
            desired_sales_per_day (int): The expected daily sales volume.
            item_quality (int): The quality level of the item.
            required_level (int): The minimum required level for using the item.
            item_class (int): The class category of the item.
            item_subclass (int): The subclass category of the item.
            ilvl (int): The item level.
            discount_percent (float): The discount rate applied in market value calculations.
            minimum_market_value (float): The minimum acceptable market price.
            expansion_number (int): The identifier for the game's expansion pack.
        """
        super().__init__()
        self.request_data = {
            "homeRealmId": realm_id,
            "region": region,
            "commodity": commodity,
            "desired_avg_price": desired_avg_price,
            "desired_sales_per_day": desired_sales_per_day,
            "itemQuality": item_quality,
            "required_level": required_level,
            "item_class": item_class,
            "item_subclass": item_subclass,
            "ilvl": ilvl,
            "expansion_number": expansion_number,
        }
        self.l_discount_percent = discount_percent
        self.minimum_market_value = minimum_market_value

    # @coderabbitai add docstring here if needed and remove this comment after
    def run(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Fetch and process item recommendations based on market data.
        
        Validates the home realm ID before sending a POST request to retrieve item statistics.
        Calculates recommended prices by applying a discount to historic prices and emits the results via
        the 'completed' signal. If the home realm ID is invalid (i.e., not greater than 0), emits an empty
        dictionary.
        """
        if self.request_data["homeRealmId"] <= 0:
            # return error that commodities are not a realm, tick the box and pick your home server
            self.completed.emit({})
            return

        marketshare_recommendations = requests.post(
            f"http://api.saddlebagexchange.com/api/wow/itemstats",
            headers={"Accept": "application/json"},
            json=self.request_data,
        ).json()
        print(self.request_data)

        recommended_items = {
            str(item["itemID"]): round(
                item["historicPrice"] * self.l_discount_percent, 4
            )
            for item in marketshare_recommendations["data"]
            if item["historicMarketValue"] >= self.minimum_market_value
        }

        self.completed.emit(recommended_items)


class Item_Statistics(QThread):
    """
    The Item_Statistics class runs a thread to fetch item statistics using the Saddlebag Exchange API.
    Parameters:
        - None: The constructor does not take any parameters.
    Processing Logic:
        - Utilizes the Saddlebag Exchange API to request item statistics.
        - Transforms the JSON response from the API into a pandas DataFrame.
        - Emits the DataFrame via a PyQt signal to indicate completion.
    """

    completed = pyqtSignal(pd.DataFrame)

    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        # # old way
        # super(Item_Statistics, self).__init__()
        # # coderabbit says do this
        """
        Initializes the Item_Statistics thread.
        
        Sets up the asynchronous worker for fetching item statistics from the external API by
        invoking the parent QThread initializer.
        """
        super().__init__()

    # @coderabbitai add docstring here if needed and remove this comment after
    def run(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """Fetches item statistics from the Saddlebag Exchange API.
        
        Sends a POST request to retrieve item data, converts the JSON response into a pandas
        DataFrame, and emits the DataFrame via the 'completed' signal.
        """
        item_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": "EU", "discount": 1},
            ).json()
        )

        self.completed.emit(item_statistics)


class RecommendationsPage(QWidget):
    """Initializes a page to configure settings for generating item recommendations based on data from World of Warcraft realms.
    Parameters:
        - None
    Processing Logic:
        - Initializes paths to JSON files containing realm data for Europe and North America, and loads this data.
        - Sets up predefined dictionaries for item qualities, categories, expansions, sub-categories, and custom pet categories.
        - Calls a method to populate the page with various input widgets including dropdowns, checkboxes, and text fields for user interaction.
    Returns:
        - None"""

    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initializes the RecommendationsPage with realm data and item configurations.
        
        Loads EU and NA realm connection data from JSON files stored in the AzerothAuctionAssassinData
        directory and sets up dictionaries for item qualities, categories, expansions, sub-categories,
        and custom pet categories. Calls make_page() to construct the page layout.
        """

        super(RecommendationsPage, self).__init__()
        self.layout = QGridLayout(self)
        self.eu_connected_realms = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "eu-wow-connected-realm-ids.json"
        )
        self.na_connected_realms = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "na-wow-connected-realm-ids.json"
        )

        self.eu_realms = json.load(open(self.eu_connected_realms))
        self.na_realms = json.load(open(self.na_connected_realms))

        self.item_quality_list = {
            "Common": 1,
            "Uncommon": 2,
            "Rare": 3,
            "Epic": 4,
            "Legendary": 5,
            "Artifact": 6,
            "Heirloom": 7,
        }

        self.item_category_list = {
            "Recipe": 9,
            "All": -1,
            # "Consumable": 0,
            "Container": 1,
            "Weapon": 2,
            # "Gem": 3,
            "Armor": 4,
            # "Tradegoods": 7,
            # "Item Enhancement": 8,
            "Quest Item": 12,
            "Miscellaneous": 15,
            # "Glyph": 16,
            # "Battle Pet": 17,
            "Profession": 19,
        }
        self.expansion_list = {
            "All": -1,
            "Classic": 1,
            "The Burning Crusade": 2,
            "Wrath of the Lich King": 3,
            "Cataclysm": 4,
            "Mists of Pandaria": 5,
            "Warlords of Draenor": 6,
            "Legion": 7,
            "Battle for Azeroth": 8,
            "Shadowlands": 9,
            "Dragonflight": 10,
            "The War Within": 11,
        }
        self.item_sub_category_lists = {
            "All": {"All": -1},
            "Consumable": {
                "All": -1,
                "Generic": 0,
                "Potion": 1,
                "Elixir": 2,
                "Flasks & Phials": 3,
                "Food & Drink": 4,
                "Food & Drink 2": 5,
                "Bandage": 6,
                "Other": 7,
                "Other 2": 8,
                "Vantus Rune": 9,
            },
            "Container": {
                "All": -1,
                "Bag": 0,
                "Soul Bag": 1,
                "Herb Bag": 2,
                "Enchanting Bag": 3,
                "Engineering Bag": 4,
                "Gem Bag": 5,
                "Mining Bag": 6,
                "Leatherworking Bag": 7,
                "Inscription Bag": 8,
                "Tackle Box": 9,
                "Cooking Bag": 10,
            },
            "Weapon": {
                "All": -1,
                "One-Handed Axes": 0,
                "Two-Handed Axes": 1,
                "Bows": 2,
                "Guns": 3,
                "One-Handed Maces": 4,
                "Two-Handed Maces": 5,
                "Polearms": 6,
                "One-Handed Swords": 7,
                "Two-Handed Swords": 8,
                "Warglaives": 9,
                "Staves": 10,
                "Bear Claws": 11,
                "CatClaws": 12,
                "Fist Weapons": 13,
                "Miscellaneous": 14,
                "Daggers": 15,
                "Thrown": 16,
                "Crossbows": 18,
                "Wands": 19,
                "Fishing Poles": 20,
            },
            "Gem": {
                "All": -1,
                "Intellect": 0,
                "Agility": 1,
                "Strength": 2,
                "Stamina": 3,
                "Spirit": 4,
                "Critical Strike": 5,
                "Mastery": 6,
                "Haste": 7,
                "Versatility": 8,
                "Other": 9,
                "Multiple Stats": 10,
                "Artifact Relic": 11,
            },
            "Armor": {
                "All": -1,
                "Miscellaneous: Trinkets, Rings, Necks, Spellstones, Firestones, etc.": 0,
                "Cloth": 1,
                "Leather": 2,
                "Mail": 3,
                "Plate": 4,
                "Cosmetic": 5,
                "Shields": 6,
                "Librams": 7,
                "Idols": 8,
                "Totems": 9,
                "Sigils": 10,
                "Relic": 11,
            },
            "Tradegoods": {
                "All": -1,
                "Parts": 1,
                "Jewelcrafting": 4,
                "Cloth": 5,
                "Leather": 6,
                "Metal & Stone": 7,
                "Cooking": 8,
                "Herb": 9,
                "Elemental": 10,
                "Other": 11,
                "Enchanting": 12,
                "Inscription": 16,
                "Optional Reagents": 18,
                "Finishing Reagents": 19,
            },
            "Item Enhancement": {
                "All": -1,
                "Head": 0,
                "Neck": 1,
                "Shoulder": 2,
                "Cloak": 3,
                "Chest": 4,
                "Wrist": 5,
                "Hands": 6,
                "Waist": 7,
                "Legs": 8,
                "Feet": 9,
                "Finger": 10,
                "One-Handed Weapon": 11,
                "Two-Handed Weapon": 12,
                "Shield/Off-hand": 13,
                "Misc": 14,
            },
            "Recipe": {
                "All": -1,
                "Book": 0,
                "Leatherworking": 1,
                "Tailoring": 2,
                "Engineering": 3,
                "Blacksmithing": 4,
                "Cooking": 5,
                "Alchemy": 6,
                "First Aid": 7,
                "Enchanting": 8,
                "Fishing": 9,
                "Jewelcrafting": 10,
                "Inscription": 11,
            },
            "Quest Item": {"Quest Item": 0},
            "Miscellaneous": {
                "All": -1,
                "Junk": 0,
                "Reagent": 1,
                "Companion Pets": 2,
                "Holiday": 3,
                "Other": 4,
                "Mount": 5,
                "Mount Equipment": 6,
                "Toys": 199,
            },
            "Glyph": {
                "All": -1,
                "Warrior": 1,
                "Paladin": 2,
                "Hunter": 3,
                "Rogue": 4,
                "Priest": 5,
                "Death Knight": 6,
                "Shaman": 7,
                "Mage": 8,
                "Warlock": 9,
                "Monk": 10,
                "Druid": 11,
                "Demon Hunter": 12,
            },
            "Battle Pet": {
                "All": -1,
                "Humanoid": 0,
                "Dragonkin": 1,
                "Flying": 2,
                "Undead": 3,
                "Critter": 4,
                "Magic": 5,
                "Elemental": 6,
                "Beast": 7,
                "Aquatic": 8,
                "Mechanical": 9,
            },
            "Profession": {
                "All": -1,
                "Blacksmithing": 0,
                "Leatherworking": 1,
                "Alchemy": 2,
                "Herbalism": 3,
                "Cooking": 4,
                "Mining": 5,
                "Tailoring": 6,
                "Engineering": 7,
                "Enchanting": 8,
                "Fishing": 9,
                "Skinning": 10,
                "Jewelcrafting": 11,
                "Inscription": 12,
                "Archaeology": 13,
            },
        }
        self.pet_custom_categories = {
            "-1": "Vendor Pets",
            "-2": "Crafted Pets",
            "-3": "Top rated pets from https://www.warcraftpets.com/wow-pets/top-twenty/",
        }

        self.make_page()

    # @coderabbitai add docstring here if needed and remove this comment after
    def make_page(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Set up and arrange widgets for item filtering configuration.
        
        This method initializes various input controls (e.g., text inputs, dropdowns, checkboxes, and buttons) in a grid layout and configures their default values and signal connections to enable users to specify criteria for filtering auction items.
        """
        self.minimum_average_price_input = QLineEdit(self)
        self.minimum_average_price_input.setText("2000")
        self.minimum_average_price_input_label = QLabel(
            "Minimum Desired average price", self
        )
        self.minimum_average_price_input_label.setToolTip("")
        self.minimum_average_price_input_label.setFixedHeight(20)
        self.layout.addWidget(self.minimum_average_price_input_label, 0, 0, 1, 1)
        self.layout.addWidget(self.minimum_average_price_input, 1, 0, 1, 1)

        self.minimum_desired_sales_input = QLineEdit(self)
        self.minimum_desired_sales_input.setText("0.1")
        self.minimum_desired_sales_input_label = QLabel(
            "Minimum Desired sales per day", self
        )
        self.minimum_desired_sales_input_label.setToolTip("")
        self.minimum_desired_sales_input_label.setFixedHeight(20)
        self.layout.addWidget(self.minimum_desired_sales_input_label, 0, 1, 1, 1)
        self.layout.addWidget(self.minimum_desired_sales_input, 1, 1, 1, 1)

        self.recommendations_region = QComboBox(self)
        self.recommendations_region_label = QLabel("Select your Region", self)
        self.recommendations_region_label.setToolTip("")
        self.recommendations_region_label.setFixedHeight(20)
        self.recommendations_region.addItems(["Europe", "North America"])
        self.recommendations_region.currentIndexChanged.connect(
            self.region_combo_changed
        )
        self.layout.addWidget(self.recommendations_region_label, 2, 0, 1, 1)
        self.layout.addWidget(self.recommendations_region, 3, 0, 1, 1)

        self.recommendations_realm_combobox = QComboBox(self)
        self.recommendations_realm_combobox.setEditable(True)
        self.recommendations_realm_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.recommendations_realm_combobox.completer()
        self.recommendations_realm_combobox.addItems(self.eu_realms)
        self.realm_recommendations_realm_label = QLabel(
            "Search for server by name", self
        )
        self.realm_recommendations_realm_label.setToolTip("")
        self.realm_recommendations_realm_label.setFixedHeight(20)
        self.layout.addWidget(self.realm_recommendations_realm_label, 2, 1, 1, 1)
        self.layout.addWidget(self.recommendations_realm_combobox, 3, 1, 1, 1)

        self.item_sub_category = QComboBox(self)
        self.item_sub_category_label = QLabel("Item Sub Category", self)
        self.item_sub_category_label.setToolTip("")
        self.item_sub_category_label.setFixedHeight(20)
        self.item_sub_category.addItems(["All"])
        self.layout.addWidget(self.item_sub_category_label, 4, 1, 1, 1)
        self.layout.addWidget(self.item_sub_category, 5, 1, 1, 1)

        self.item_category = QComboBox(self)
        self.item_category_label = QLabel("Item Category", self)
        self.item_category_label.setToolTip("")
        self.item_category.currentIndexChanged.connect(self.category_combo_changed)
        self.item_category_label.setFixedHeight(20)
        self.item_category.addItems(self.item_category_list)
        self.layout.addWidget(self.item_category_label, 4, 0, 1, 1)
        self.layout.addWidget(self.item_category, 5, 0, 1, 1)

        self.expansion_number = QComboBox(self)
        self.expansion_number_label = QLabel("Expansion Number", self)
        self.expansion_number_label.setToolTip("")
        self.expansion_number_label.setFixedHeight(20)
        self.expansion_number.addItems(self.expansion_list)
        self.layout.addWidget(self.expansion_number_label, 4, 2, 1, 1)
        self.layout.addWidget(self.expansion_number, 5, 2, 1, 1)

        self.item_quality = QComboBox(self)
        self.item_quality_label = QLabel("Item Quality", self)
        self.item_quality_label.setToolTip("")
        self.item_quality_label.setFixedHeight(20)
        self.item_quality.addItems(self.item_quality_list)
        self.layout.addWidget(self.item_quality_label, 6, 0, 1, 1)
        self.layout.addWidget(self.item_quality, 7, 0, 1, 1)

        self.minimum_item_level_input = QLineEdit(self)
        self.minimum_item_level_input.setText("-1")
        self.minimum_item_level_input_label = QLabel(
            "Minimum Base Item Level (ilvl)", self
        )
        self.minimum_item_level_input_label.setToolTip("")
        self.minimum_item_level_input_label.setFixedHeight(20)
        self.layout.addWidget(self.minimum_item_level_input_label, 6, 1, 1, 1)
        self.layout.addWidget(self.minimum_item_level_input, 7, 1, 1, 1)

        self.minimum_required_level_input = QLineEdit(self)
        self.minimum_required_level_input.setText("-1")
        self.minimum_required_level_input_label = QLabel("Minimum Required Level", self)
        self.minimum_required_level_input_label.setToolTip("")
        self.minimum_required_level_input_label.setFixedHeight(20)
        self.layout.addWidget(self.minimum_required_level_input_label, 8, 0, 1, 1)
        self.layout.addWidget(self.minimum_required_level_input, 9, 0, 1, 1)

        self.commodity_items = QCheckBox("Commodity items", self)
        self.commodity_items.setToolTip("DO NOT USE, WILL ADD THIS LATER")
        self.layout.addWidget(self.commodity_items, 8, 1, 1, 1)

        self.local_discount_percent = QLineEdit(self)
        self.local_discount_percent.setText("50")
        self.local_discount_percent_label = QLabel("Local Discount Percent", self)
        self.local_discount_percent_label.setToolTip(
            "What percent of normal price do you want it?\nex: if it sells for 10k and we pick 30% then we try too snipe at 3k."
        )
        self.local_discount_percent_label.setFixedHeight(20)
        self.layout.addWidget(self.local_discount_percent_label, 10, 0, 1, 1)
        self.layout.addWidget(self.local_discount_percent, 11, 0, 1, 1)

        self.minimum_market_value = QLineEdit(self)
        self.minimum_market_value.setText("5000")
        self.minimum_market_value_label = QLabel("Minimum Market Value", self)
        self.minimum_market_value_label.setToolTip(
            "Minimum gold an item earns per day on any average server."
        )
        self.minimum_market_value_label.setFixedHeight(20)
        self.layout.addWidget(self.minimum_market_value_label, 10, 1, 1, 1)
        self.layout.addWidget(self.minimum_market_value, 11, 1, 1, 1)

        self.search_button = QPushButton("Search")
        self.layout.addWidget(self.search_button, 12, 0, 1, 2)

    # @coderabbitai add docstring here if needed and remove this comment after
    def category_combo_changed(self, index):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Updates the sub-category dropdown based on the current category selection.
        
        If the selected category is not "All", the sub-category list is cleared and repopulated
        with the corresponding entries from the available sub-categories.
        """
        selected_category = self.item_category.currentText()
        if selected_category == "All":
            return
        self.item_sub_category.clear()
        self.item_sub_category.addItems(self.item_sub_category_lists[selected_category])

    # @coderabbitai add docstring here if needed and remove this comment after
    def region_combo_changed(self, index):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Update realm combobox based on the selected region.
        
        Clears the current realms and repopulates the combobox with region-specific options.
        If the selected region is "Europe", European realms are added; if "North America",
        North American realms are added. The combobox is then enabled for user interaction.
        
        Parameters:
            index (int): The index of the selected region from the combobox (not directly used).
        """
        self.recommendations_realm_combobox.clear()
        if self.recommendations_region.currentText() == "Europe":
            self.recommendations_realm_combobox.addItems(self.eu_realms)
        elif self.recommendations_region.currentText() == "North America":
            self.recommendations_realm_combobox.addItems(self.na_realms)

        self.recommendations_realm_combobox.setEnabled(True)


class HomePage(QWidget):
    """Creates the user interface for the application homepage with an icon, title, and multiple hyperlinked labels.
    Parameters:
        - None: The class does not take parameters upon initialization.
    Processing Logic:
        - Adjusts the icon file path conditionally if the app is run from a specific Windows binary path.
        - Configures a grid layout to arrange various UI elements such as an icon and text labels.
        - Each label in the layout is assigned a hyperlink for external websites, styled with specific fonts.
        - Ensures open external links feature is enabled for the labels containing hyperlinks.
    """

    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initializes the HomePage widget.
        
        Sets up a grid layout for the widget and builds the home page UI.
        """
        super(HomePage, self).__init__()
        self.layout = QGridLayout(self)
        self.make_page()

    # @coderabbitai add docstring here if needed and remove this comment after
    def make_page(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
        """
        Constructs the user interface page with the application icon, title, and external links.
        
        Adjusts the icon path when running from a Windows binary and adds clickable labels
        linking to Patreon, Discord, the main website, and guides.
        """
        icon_path = "target.png"
        if windowsApp_Path is not None:
            icon_path = f"{windowsApp_Path}\\{icon_path}"

        # display the icon.ico
        self.icon = QLabel(self)
        self.icon.setPixmap(QtGui.QPixmap(icon_path))
        self.layout.addWidget(self.icon, 0, 0)

        # add the title
        self.title = QLabel(self)
        self.title.setText("Azeroth Auction Target")
        self.title.setFont((QtGui.QFont("Arial", 30, QtGui.QFont.Bold)))
        self.layout.addWidget(self.title, 1, 0)

        # add link to patreon
        self.patreon_link = QLabel(self)
        self.patreon_link.setText(
            "<a href='https://www.patreon.com/indopan' style='color: white;'>Support the Project on Patreon</a>"
        )
        self.patreon_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.patreon_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.patreon_link, 2, 0)

        # add discord link
        self.discord_link = QLabel(self)
        self.discord_link.setText(
            "<a href='https://discord.gg/9dHx2rEq9F' style='color: white;'>Join the Discord</a>"
        )
        self.discord_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.discord_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.discord_link, 3, 0)

        # add main website link
        self.website_link = QLabel(self)
        self.website_link.setText(
            "<a href='https://saddlebagexchange.com' style='color: white;'>Check out our main website: Saddlebag Exchange</a>"
        )
        self.website_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.website_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.website_link, 4, 0)

        # add a guides link
        self.guides_link = QLabel(self)
        self.guides_link.setText(
            "<a href='https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki' style='color: white;'>Check out our guides</a>"
        )
        self.guides_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.guides_link.setOpenExternalLinks(True)
        self.layout.addWidget(self.guides_link, 5, 0)


class ItemPage(QWidget):
    """Establishes a user interface for managing items, including item selection, display, and import functionalities.
    Parameters:
        - None: The class is initialized without external parameters.
    Processing Logic:
        - Uses QGridLayout to organize UI elements such as input fields, labels, and buttons.
        - Employs signal connections to handle button actions and list interactions.
        - Implements methods for item addition, removal, and importing item data from files.
    """

    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initialize the item page user interface.
        
        Creates a grid layout, sets up an empty dictionary for item storage, and builds the page.
        """
        super(ItemPage, self).__init__()
        self.layout = QGridLayout(self)
        self.items_list = {}
        self.make_page()

    # @coderabbitai add docstring here if needed and remove this comment after
    def make_page(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Creates and arranges the UI components for item selection and management.
        
        Initializes input fields for item ID and price, a combo box for item names, action
        buttons for adding, removing, and importing items, and a sortable list widget to display
        items. Connects UI events to their respective handler methods.
        """
        self.item_id_input = QLineEdit(self)
        self.item_id_input_label = QLabel("Item ID", self)
        self.item_id_input_label.setToolTip(
            "Add the item id of any item you want to buy.\nYou can search by name for them here with recommended prices\nhttps://temp.saddlebagexchange.com/megaitemnames"
        )
        self.layout.addWidget(self.item_id_input_label, 0, 0, 1, 1)
        self.layout.addWidget(self.item_id_input, 1, 0, 1, 1)

        self.item_price_input = QLineEdit(self)
        self.item_price_input_label = QLabel("Price", self)
        self.item_price_input_label.setToolTip(
            "Pick a price you want to buy at or under."
        )
        self.layout.addWidget(self.item_price_input_label, 0, 1, 1, 1)
        self.layout.addWidget(self.item_price_input, 1, 1, 1, 1)

        self.item_name_input = QComboBox(self)
        self.item_name_input.setEnabled(False)
        self.layout.addWidget(self.item_name_input, 2, 0, 1, 2)

        self.add_item_button = QPushButton("Add Item")
        self.add_item_button.setToolTip("Add item to your snipe list.")
        self.add_item_button.clicked.connect(self.add_item_to_dict)
        self.layout.addWidget(self.add_item_button, 3, 0, 1, 1)

        self.remove_item_button = QPushButton("Remove Item")
        self.remove_item_button.setToolTip("Remove item from your snipe list.")
        self.remove_item_button.clicked.connect(self.remove_item_to_dict)
        self.layout.addWidget(self.remove_item_button, 3, 1, 1, 1)

        self.item_list_display = QListWidget(self)
        self.item_list_display.setSortingEnabled(True)

        self.item_list_display.itemClicked.connect(self.item_list_double_clicked)
        self.layout.addWidget(self.item_list_display, 4, 0, 13, 2)

        self.import_item_data_button = QPushButton("Import Item Data")
        self.import_item_data_button.setToolTip("Import your desired_items.json config")
        self.import_item_data_button.clicked.connect(self.import_item_data)
        self.layout.addWidget(self.import_item_data_button, 17, 0, 1, 1)

        self.import_pbs_data_button = QPushButton("Import PBS Data")
        self.import_pbs_data_button.setToolTip(
            "Import your Point Blank Sniper text files"
        )
        self.import_pbs_data_button.clicked.connect(self.import_pbs_data)
        self.layout.addWidget(self.import_pbs_data_button, 17, 1, 1, 1)

    # @coderabbitai add docstring here if needed and remove this comment after
    def add_item_to_dict(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """Add an item and its price to the dictionary and update the display list.
        
        Retrieves the item ID and price from input fields, validates that both are provided, numeric, and within the accepted 
        ranges (item ID: 1–500000 and price: 0–10,000,000). If an item with the same ID exists in the display, it is removed before 
        adding the updated entry. Displays an error message and returns False if the input is invalid.
        
        Returns:
            bool: True if the item was successfully added or updated, False otherwise.
        """
        item_id = self.item_id_input.text()
        item_price = self.item_price_input.text()

        if item_id == "" or item_price == "":
            QMessageBox.critical(
                self, "Incomplete Information", "All fields are required."
            )
            return False

        try:
            item_id_int = int(item_id)
            item_price_int = float(item_price)
        except ValueError:
            QMessageBox.critical(
                self, "Invalid Input", "Item ID and Price should be numbers."
            )
            return False

        # Check if Item ID is between 1 and 500000
        if not 1 <= item_id_int <= 500000:
            QMessageBox.critical(
                self, "Incorrect Item ID", "Item ID must be between 1 and 500000."
            )
            return False

        # Check if Price is between 1 and 10 million
        if not 0 <= item_price_int <= 10000000:
            QMessageBox.critical(
                self, "Incorrect Price", "Price must be between 0 and 10 million."
            )
            return False

        # If item is already in the items_list, remove it
        if item_id in self.items_list:
            for existing_item in range(self.item_list_display.count()):
                if (
                    self.item_list_display.item(existing_item).text()
                    == f"Item ID: {item_id}, Price: {self.items_list[item_id]}"
                ):
                    self.item_list_display.takeItem(existing_item)
                    break

        # Add or Update item in the items_list
        self.items_list[item_id] = item_price
        self.item_list_display.insertItem(
            self.item_list_display.count(),
            f"Item ID: {item_id}, Price: {item_price}",
        )

        return True

    # @coderabbitai add docstring here if needed and remove this comment after
    def item_list_double_clicked(self, item):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Handles a double-click event on an item by updating the corresponding detail fields.
        
        Args:
            item (QListWidgetItem): The item that was double-clicked in the list.
        
        Extracts the item ID and price from the item's text and updates the respective input fields.
        Attempts to retrieve the item's name from stored statistics and set it in the name selector;
        if the item is not found, displays a default message.
        """
        item_split = item.text().replace(" ", "").split(":")
        item_id = item_split[1].split(",")[0]
        self.item_id_input.setText(item_id)
        self.item_price_input.setText(item_split[2])
        # find the itemName value from item_id in the item_statistics
        try:
            item_name = self.item_statistics[
                self.item_statistics["itemID"] == int(item_id)
            ].iloc[0]["itemName"]
            index = self.item_name_input.findText(item_name)
            self.item_name_input.setCurrentIndex(index)

        except:
            self.item_name_input.setCurrentText("Item ID not found")

    # @coderabbitai add docstring here if needed and remove this comment after
    def remove_item_to_dict(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """Remove an item from the internal items dictionary and update the display.
        
        Checks if the item ID from the input field exists in the dictionary. If found, removes
        its corresponding entry from the display list and deletes it from the dictionary.
        """
        if self.item_id_input.text() in self.items_list:
            for x in range(self.item_list_display.count()):
                if (
                    self.item_list_display.item(x).text()
                    == f"Item ID: {self.item_id_input.text()}, Price: {self.items_list[self.item_id_input.text()]}"
                ):
                    self.item_list_display.takeItem(x)
                    del self.items_list[self.item_id_input.text()]
                    return

    # @coderabbitai add docstring here if needed and remove this comment after
    def import_item_data(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Import and display item data from a JSON file.
        
        Opens a file dialog for user selection of a JSON file containing item data, then clears the current
        display and imports the data after validating that item IDs are between 1 and 500,000 and prices
        are between 0 and 10,000,000. Error messages are shown if the file is invalid or the data fails validation.
        """
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.item_list_display.clear()
        self.items_list = {}

        try:
            with open(pathname) as file:
                self.items_list = json.load(file)
            for key, value in self.items_list.items():
                if not (1 <= int(key) <= 500000):
                    raise ValueError(
                        f"Invalid item ID {key}.\nIDs must be integers between 1-500,000."
                    )
                if not (0 <= int(value) <= 10000000):
                    raise ValueError(
                        f"Invalid price {value} for item ID {key}.\nPrices must be integers between 0-10,000,000."
                    )
                self.item_list_display.insertItem(
                    self.item_list_display.count(),
                    f"Item ID: {key}, Price: {value}",
                )

        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Invalid JSON", "Please provide a valid JSON file!"
            )
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    # @coderabbitai add docstring here if needed and remove this comment after
    def import_pbs_data(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """Import PBS data from a file and update the item list with discounted prices.
        
        This method opens a file dialog for the user to select a PBS data file. It clears the current item display 
        and internal record before reading the file to extract PBS item names. It then matches these names against 
        existing item statistics to retrieve desired prices, applies a discount based on the user-provided percentage, 
        and updates both the display and the internal item list with the discounted prices. Errors during processing 
        are reported via message dialogs.
        """
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.item_list_display.clear()
        self.items_list = {}

        try:
            # open and read the text file
            with open(pathname, "r") as file:
                pbs_names = [
                    item.split(";;")[0].lower().replace("\n", "")
                    for item in file.read().split("^")
                ]

            temp_items_list = {
                str(item["itemID"]): item["desiredPrice"]
                for index, item in self.item_statistics.iterrows()
                if item["itemName"].lower() in pbs_names
            }
            self.items_list = {}
            for key, value in temp_items_list.items():
                discount_percent = int(self.discount_percent.text()) / 100
                discount_price = round(float(value) * discount_percent, 4)
                self.item_list_display.insertItem(
                    self.item_list_display.count(),
                    f"Item ID: {key}, Price: {discount_price}",
                )
                self.items_list[str(key)] = discount_price
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    # @coderabbitai add docstring here if needed and remove this comment after
    def on_combo_box_item_changed(self, index):
        # @coderabbitai add docstring here if needed and remove this comment after
        # This function will be called whenever the user selects a different item
        """
        Update item details when the combo box selection changes.
        
        Retrieves the selected item's statistics and updates the associated item ID and price
        fields. If a custom price is not provided, the function computes a discounted price
        using the user-specified discount percentage, defaulting to a 10% discount on conversion
        failure.
        
        Args:
            index (int): The index of the selected combo box item (unused).
        """

        selected_item = self.item_name_input.currentText()
        selected_item_stats = self.item_statistics[
            self.item_statistics["itemName"] == selected_item
        ]
        selected_item_id = selected_item_stats["itemID"].iloc[0]
        if str(selected_item_id) in self.items_list.keys():
            selected_item_price = self.items_list[str(selected_item_id)]
        else:
            selected_item_price = selected_item_stats["desiredPrice"].iloc[0]

        # if the user has not set a price for the item, set the price from TSM stats
        if (
            not self.item_price_input.text()
            or str(selected_item_id) not in self.items_list
        ):
            try:
                discount_percent = int(self.discount_percent.text()) / 100
                recommended_price = str(
                    int(float(selected_item_price) * discount_percent)
                )
                self.item_price_input.setText(recommended_price)
            except:
                self.item_price_input.setText("10")
                recommended_price = str(int(float(selected_item_price) * 0.1))
                self.item_price_input.setText(recommended_price)

        else:
            self.item_price_input.setText(str(selected_item_price))

        self.item_id_input.setText(str(selected_item_id))


class App(QMainWindow):
    """A graphical application interface for Azeroth Auction management, integrating item statistics and recommendations.
    Parameters:
        - None
    Processing Logic:
        - Sets the application title with the specified version.
        - Determines the correct path for the icon file based on the environment.
        - Configures paths for various data files used by the application.
        - Initiates and connects the API data retrieval thread for handling item statistics.
    """

    # @coderabbitai add docstring here if needed and remove this comment after
    def __init__(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initialize the App instance with UI configuration and data management.
        
        Configures the main window's properties (title, dimensions, and icon), adjusts the icon path when running from a Windows binary, sets up paths for data files, and starts a background thread to fetch item statistics from an external API.
        """
        super(App, self).__init__()
        self.title = f"Azeroth Auction Tartet v{AAT_VERSION}"
        self.left = 100
        self.top = 100
        self.width = 750
        self.height = 750
        icon_path = "target.png"

        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
        if windowsApp_Path is not None:
            icon_path = f"{windowsApp_Path}\\{icon_path}"

        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        self.token_auth_url = "http://api.saddlebagexchange.com/api/wow/checkmegatoken"

        # default to 10% discount, just use EU for now for less data
        self.api_data_thread = Item_Statistics()
        self.api_data_thread.start()
        self.api_data_thread.completed.connect(self.api_data_received)

        self.path_to_data = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "mega_data.json"
        )
        self.path_to_desired_items = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "desired_items.json"
        )
        self.path_to_desired_pets = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "desired_pets.json"
        )
        self.path_to_desired_ilvl_items = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "desired_ilvl.json"
        )
        self.path_to_desired_ilvl_list = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "desired_ilvl_list.json"
        )

        self.eu_connected_realms = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "eu-wow-connected-realm-ids.json"
        )
        self.na_connected_realms = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "na-wow-connected-realm-ids.json"
        )
        self.EUCLASSIC_connected_realms = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "euclassic-wow-connected-realm-ids.json",
        )
        self.NACLASSIC_connected_realms = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "naclassic-wow-connected-realm-ids.json",
        )
        self.NASODCLASSIC_connected_realms = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "nasodclassic-wow-connected-realm-ids.json",
        )
        self.EUSODCLASSIC_connected_realms = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "eusodclassic-wow-connected-realm-ids.json",
        )

        self.initUI()

    # @coderabbitai add docstring here if needed and remove this comment after
    def initUI(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Initialize and set up the main user interface of the application.
        
        This method configures the main window by setting its title and geometry, creating a central widget
        with a grid layout, and adding side buttons along with a stacked widget that contains the home, item,
        and recommendation pages. It also embeds the layout in a scrollable area and connects the recommendation
        page's search button to its handler before displaying the window.
        """
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.layout_area = QGridLayout(central_widget)

        self.make_side_buttons()

        self.stacked_widget = QStackedWidget(self)

        self.home_page = HomePage()
        self.item_page = ItemPage()
        self.recommendation_page = RecommendationsPage()
        self.check_for_settings()

        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.item_page)
        self.stacked_widget.addWidget(self.recommendation_page)

        self.layout_area.addWidget(self.stacked_widget, 0, 1, 17, 2)

        # Create a QScrollArea and set its widget to be the container
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(
            True
        )  # Important to make the scroll area adapt to the content
        scrollArea.setWidget(central_widget)

        # Set the QScrollArea as the central widget of the main window
        self.setCentralWidget(scrollArea)

        self.recommendation_page.search_button.clicked.connect(self.search)

        self.show()

    # @coderabbitai add docstring here if needed and remove this comment after
    def make_side_buttons(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """Create and arrange side buttons for navigation and data actions.
        
        This method creates buttons for Home Page, Recommendations, Items, Save Data, and Reset Data.
        Each button is assigned a fixed size of 150x25, connected to its specific functionality, and
        added to the interface's grid layout at designated positions.
        """
        self.go_to_home_button = QPushButton("Home Page")

        self.go_to_home_button.setFixedSize(150, 25)
        self.go_to_home_button.clicked.connect(lambda: self.go_to_page_number(0))
        self.layout_area.addWidget(self.go_to_home_button, 0, 0)

        self.go_to_recommendations_button = QPushButton("Recommendations")

        self.go_to_recommendations_button.setFixedSize(150, 25)
        self.go_to_recommendations_button.clicked.connect(
            lambda: self.go_to_page_number(2)
        )
        self.layout_area.addWidget(self.go_to_recommendations_button, 1, 0)

        self.go_to_item_button = QPushButton("Items")

        self.go_to_item_button.setFixedSize(150, 25)

        self.go_to_item_button.clicked.connect(lambda: self.go_to_page_number(1))
        self.layout_area.addWidget(self.go_to_item_button, 3, 0)

        self.save_data_button = QPushButton("Save Data")

        self.save_data_button.setFixedSize(150, 25)

        self.save_data_button.clicked.connect(self.save_data_to_json)
        self.save_data_button.setToolTip("Save data without starting a scan.")
        self.layout_area.addWidget(self.save_data_button, 8, 0)

        self.reset_data_button = QPushButton("Reset Data")

        self.reset_data_button.setFixedSize(150, 25)

        self.reset_data_button.clicked.connect(self.reset_app_data)
        self.reset_data_button.setToolTip("Erase all data and reset the app.")
        self.layout_area.addWidget(self.reset_data_button, 9, 0)

    # @coderabbitai add docstring here if needed and remove this comment after
    def go_to_page_number(self, index):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Switches the current page displayed in the application.
        
        Updates the stacked widget to show the page at the specified index.
        
        Args:
            index: An integer representing the target page number to display.
        """
        self.stacked_widget.setCurrentIndex(index)

    # @coderabbitai add docstring here if needed and remove this comment after
    def search(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Searches for auction recommendations using user-selected criteria.
        
        Extracts search parameters from the recommendations page UI—including realm, region, item
        category, quality, pricing, and other filters—converts them as needed, and starts a background
        thread to retrieve recommendation data. The thread's completion signal is connected to a handler
        to process the received data.
        """
        if self.recommendation_page.recommendations_region.currentText() == "Europe":
            realm_id = self.recommendation_page.eu_realms[
                self.recommendation_page.recommendations_realm_combobox.currentText()
            ]
            region = "EU"
        elif (
            self.recommendation_page.recommendations_region.currentText()
            == "North America"
        ):
            realm_id = self.recommendation_page.na_realms[
                self.recommendation_page.recommendations_realm_combobox.currentText()
            ]
            region = "NA"

        item_category_name = self.recommendation_page.item_category.currentText()
        item_category = self.recommendation_page.item_category_list[item_category_name]
        if item_category == -1:
            item_sub_category = -1
        else:
            item_sub_category = self.recommendation_page.item_sub_category_lists[
                item_category_name
            ][self.recommendation_page.item_sub_category.currentText()]

        item_quality = self.recommendation_page.item_quality_list[
            self.recommendation_page.item_quality.currentText()
        ]
        expansion_number = self.recommendation_page.expansion_list[
            self.recommendation_page.expansion_number.currentText()
        ]
        self.recommendation_request_thread = RecommendationsRequest(
            realm_id=realm_id,
            region=region,
            commodity=self.recommendation_page.commodity_items.isChecked(),
            # dont ask me why i did this one in coppers instead of using floats
            desired_avg_price=int(
                float(self.recommendation_page.minimum_average_price_input.text())
                * 10000
            ),
            desired_sales_per_day=float(
                self.recommendation_page.minimum_desired_sales_input.text()
            ),
            item_quality=item_quality,
            required_level=int(
                self.recommendation_page.minimum_required_level_input.text()
            ),
            item_class=item_category,
            item_subclass=item_sub_category,
            ilvl=int(self.recommendation_page.minimum_item_level_input.text()),
            discount_percent=int(self.recommendation_page.local_discount_percent.text())
            / 100,
            minimum_market_value=int(
                self.recommendation_page.minimum_market_value.text()
            ),
            expansion_number=expansion_number,
        )
        self.recommendation_request_thread.start()
        self.recommendation_request_thread.completed.connect(
            self.recommendation_data_received
        )

    # @coderabbitai add docstring here if needed and remove this comment after
    def recommendation_data_received(self, recommended_items):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Processes and displays recommended items on the item page.
        
        This method clears the current item display and updates it with new recommendations.
        Each item in the provided dictionary is validated to ensure that its ID is between 1 and 500,000 and its price is between 0 and 10,000,000.
        A ValueError is raised if any item fails validation.
        
        Parameters:
            recommended_items (dict): Mapping of item IDs (int) to their prices (int).
        """
        self.item_page.item_list_display.clear()
        self.item_page.items_list = recommended_items

        for key, value in self.item_page.items_list.items():
            if not (1 <= int(key) <= 500000):
                raise ValueError(
                    f"Invalid item ID {key}.\nIDs must be integers between 1-500,000."
                )
            if not (0 <= int(value) <= 10000000):
                raise ValueError(
                    f"Invalid price {value} for item ID {key}.\nPrices must be integers between 0-10,000,000."
                )
            self.item_page.item_list_display.insertItem(
                self.item_page.item_list_display.count(),
                f"Item ID: {key}, Price: {value}",
            )

    # @coderabbitai add docstring here if needed and remove this comment after
    def api_data_received(self, item_statistics):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Update the UI's item name input field with sorted item names.
        
        This method updates the internal item statistics with the provided DataFrame and populates
        the item name combo box with names sorted in alphabetical order. It enables editing,
        sets the input policy, applies styling suitable for a dark theme, and connects the widget’s
        index change event to its handler.
        
        Args:
            item_statistics (DataFrame): Statistical data containing item names and metadata.
        """
        self.item_page.item_statistics = item_statistics

        self.item_page.item_name_input.addItems(
            self.item_page.item_statistics.sort_values(by="itemName")[
                "itemName"
            ].tolist()
        )
        self.item_page.item_name_input.setEditable(True)
        self.item_page.item_name_input.setInsertPolicy(QComboBox.NoInsert)
        self.item_page.item_name_input.completer()
        self.item_page.item_name_input.currentIndexChanged.connect(
            self.item_page.on_combo_box_item_changed
        )

        self.item_page.item_name_input.setEnabled(True)
        self.item_page.item_name_input.setStyleSheet(
            "QComboBox { background-color: #1D2023; color: white; }"
            "QComboBox::editable { background: #1D2023; color: white; }"
            "QComboBox::drop-down { border: 0px; }"
        )

    # @coderabbitai add docstring here if needed and remove this comment after
    def check_for_settings(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Check and initialize application settings and data directory.
        
        Creates the data folder if it does not exist and loads desired item settings from a JSON file,
        updating the item list display if available.
        """
        data_folder = os.path.join(os.getcwd(), "AzerothAuctionAssassinData")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        if os.path.exists(self.path_to_desired_items):
            self.item_page.items_list = json.load(open(self.path_to_desired_items))
            for key, value in self.item_page.items_list.items():
                self.item_page.item_list_display.insertItem(
                    self.item_page.item_list_display.count(),
                    f"Item ID: {key}, Price: {value}",
                )

    # @coderabbitai add docstring here if needed and remove this comment after
    def reset_app_data(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Reset the application's item data and update the stored configuration.
        
        This method clears the item list display, resets the internal item list to an empty
        state, and persists the changes by saving the updated data to a JSON file.
        """
        self.item_page.item_list_display.clear()
        self.item_page.items_list = {}
        self.save_data_to_json()

    # @coderabbitai add docstring here if needed and remove this comment after
    def validate_item_lists(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        # Check if items_list and pet_list are not empty
        """
        Validates that item, pet, and ilvl lists contain entries and valid item IDs.
        
        This method ensures that at least one of the lists has data and that every item ID
        in the items list is an integer within the range 1 to 500000. An error message is
        displayed if any check fails.
        
        Returns:
            bool: True if the lists are valid, False otherwise.
        """
        if (
            len(self.item_page.items_list) == 0
            and len(self.pet_page.pet_list) == 0
            and len(self.ilvl_page.ilvl_list) == 0
        ):
            QMessageBox.critical(
                self,
                "Empty Lists",
                "Please add items, pets or ilvl data to the lists. All appear to be empty.",
            )
            return False

        # Check if all item IDs are valid integers
        if not all(1 <= int(key) <= 500000 for key in self.item_page.items_list.keys()):
            QMessageBox.critical(
                self,
                "Invalid Item ID",
                "All item IDs should be integers between 1 and 500000.",
            )
            return False

        return True

    # @coderabbitai add docstring here if needed and remove this comment after
    def save_data_to_json(self):
        # @coderabbitai add docstring here if needed and remove this comment after
        """
        Saves the current item list to a JSON file.
        
        Calls save_json_file with the file path from self.path_to_desired_items and the
        item list from self.item_page.items_list, then returns True.
        """
        save_json_file(self.path_to_desired_items, self.item_page.items_list)
        return True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file = QFile(":/dark/stylesheet.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    ex = App()
    exit(app.exec_())
