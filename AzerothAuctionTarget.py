# added the code at the beginning of the file
# to tell the script that is being invoked from the windows c# binary
# so it knows from where to load the pre-installed packages
# so it can locate them before doing the other imports
import sys

AAT_VERSION = "0.0.1"

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


def save_json_file(path, data):

    with open(path, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


class RecommendationsRequest(QThread):
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
    ):
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
        }
        self.l_discount_percent = discount_percent
        self.minimum_market_value = minimum_market_value

    def run(self):
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
    completed = pyqtSignal(pd.DataFrame)

    def __init__(self):
        # # old way
        # super(Item_Statistics, self).__init__()
        # # coderabbit says do this
        super().__init__()

    def run(self):
        item_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": "EU", "discount": 1},
            ).json()
        )

        self.completed.emit(item_statistics)


class RecommendationsPage(QWidget):

    def __init__(self):

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

    def make_page(self):
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

    def category_combo_changed(self, index):
        selected_category = self.item_category.currentText()
        if selected_category == "All":
            return
        self.item_sub_category.clear()
        self.item_sub_category.addItems(self.item_sub_category_lists[selected_category])

    def region_combo_changed(self, index):
        self.recommendations_realm_combobox.clear()
        if self.recommendations_region.currentText() == "Europe":
            self.recommendations_realm_combobox.addItems(self.eu_realms)
        elif self.recommendations_region.currentText() == "North America":
            self.recommendations_realm_combobox.addItems(self.na_realms)

        self.recommendations_realm_combobox.setEnabled(True)


class HomePage(QWidget):
    def __init__(self):
        super(HomePage, self).__init__()
        self.layout = QGridLayout(self)
        self.make_page()

    def make_page(self):
        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
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
    def __init__(self):
        super(ItemPage, self).__init__()
        self.layout = QGridLayout(self)
        self.items_list = {}
        self.make_page()

    def make_page(self):
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

    def add_item_to_dict(self):
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

    def item_list_double_clicked(self, item):
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

    def remove_item_to_dict(self):
        if self.item_id_input.text() in self.items_list:
            for x in range(self.item_list_display.count()):
                if (
                    self.item_list_display.item(x).text()
                    == f"Item ID: {self.item_id_input.text()}, Price: {self.items_list[self.item_id_input.text()]}"
                ):
                    self.item_list_display.takeItem(x)
                    del self.items_list[self.item_id_input.text()]
                    return

    def import_item_data(self):
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

    def import_pbs_data(self):
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

    def on_combo_box_item_changed(self, index):
        # This function will be called whenever the user selects a different item

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
    def __init__(self):
        super(App, self).__init__()
        self.title = f"Azeroth Auction Tartet v{AAT_VERSION}"
        self.left = 100
        self.top = 100
        self.width = 550
        self.height = 650
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

    def initUI(self):
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

    def make_side_buttons(self):
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

    def go_to_page_number(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def search(self):
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
        )
        self.recommendation_request_thread.start()
        self.recommendation_request_thread.completed.connect(
            self.recommendation_data_received
        )

    def recommendation_data_received(self, recommended_items):
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

    def api_data_received(self, item_statistics):
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

    def check_for_settings(self):
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

    def reset_app_data(self):
        self.item_page.item_list_display.clear()
        self.item_page.items_list = {}
        self.save_data_to_json()

    def validate_item_lists(self):
        # Check if items_list and pet_list are not empty
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

    def save_data_to_json(self):
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
