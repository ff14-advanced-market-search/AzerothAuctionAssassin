# added the code at the beginning of the file
# to tell the script that is being invoked from the windows c# binary
# so it knows from where to load the pre-installed packages
# so it can locate them before doing the other imports
import sys
from datetime import datetime

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
from mega_alerts import Alerts
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


class Item_And_Pet_Statistics(QThread):
    completed = pyqtSignal(pd.DataFrame, pd.DataFrame)

    def __init__(self):
        super(Item_And_Pet_Statistics, self).__init__()

    def run(self):
        item_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": "EU", "discount": 1},
            ).json()
        )

        pet_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": "EU", "discount": 1, "pets": True},
            ).json()
        )

        self.completed.emit(pet_statistics, item_statistics)


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


class App(QMainWindow):
    def __init__(self):
        super(App, self).__init__()
        self.title = "Azeroth Auction Assassin v1.0.18"
        self.left = 100
        self.top = 100
        self.width = 550
        self.height = 650
        icon_path = "icon.png"

        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
        if windowsApp_Path is not None:
            icon_path = f"{windowsApp_Path}\icon.png"

        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        self.token_auth_url = "http://api.saddlebagexchange.com/api/wow/checkmegatoken"

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

        # default to 10% discount, just use EU for now for less data
        self.api_data_thread = Item_And_Pet_Statistics()
        self.api_data_thread.start()
        self.api_data_thread.completed.connect(self.api_data_received)

        self.pet_statistics = None
        self.item_statistics = None

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

        self.pet_list = {}
        self.items_list = {}
        self.ilvl_list = []
        self.ilvl_items = {}

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.layout_area = QGridLayout(central_widget)

        self.make_side_buttons()

        self.stacked_widget = QStackedWidget(self)

        home_page = QWidget()
        self.home_page_layout = QGridLayout(home_page)

        settings_page = QWidget()
        self.settings_page_layout = QGridLayout(settings_page)

        pet_page = QWidget()
        self.pet_page_layout = QGridLayout(pet_page)

        item_page = QWidget()
        self.item_page_layout = QGridLayout(item_page)

        ilvl_page = QWidget()
        self.ilvl_page_layout = QGridLayout(ilvl_page)

        realms_page = QWidget()
        self.realms_page_layout = QGridLayout(realms_page)

        recommendations_page = QWidget()
        self.recommendations_page_layout = QGridLayout(recommendations_page)

        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(pet_page)
        self.stacked_widget.addWidget(item_page)
        self.stacked_widget.addWidget(ilvl_page)
        self.stacked_widget.addWidget(settings_page)
        self.stacked_widget.addWidget(realms_page)
        self.stacked_widget.addWidget(recommendations_page)

        self.layout_area.addWidget(self.stacked_widget, 0, 1, 17, 2)

        self.make_home_page(home_page=home_page)

        self.make_pet_page(pet_page=pet_page)

        self.make_item_page(item_page=item_page)

        self.make_ilvl_page(ilvl_page=ilvl_page)

        self.make_settings_page(settings_page=settings_page)

        self.make_realm_page(realm_page=realms_page)

        self.make_recommendations_page(recommendations_page=recommendations_page)

        self.check_for_settings()

        # Create a QScrollArea and set its widget to be the container
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(
            True
        )  # Important to make the scroll area adapt to the content
        scrollArea.setWidget(central_widget)

        # Set the QScrollArea as the central widget of the main window
        self.setCentralWidget(scrollArea)

        self.show()

    def make_realm_page(self, realm_page):

        self.realm_region = QComboBox(realm_page)
        self.realm_region_label = QLabel("WoW Region", realm_page)
        self.realm_region_label.setToolTip("")
        self.realm_region_label.setFixedHeight(10)
        self.realm_region.addItems(
            [
                "Click this!!!",
                "EU",
                "NA",
                "EUCLASSIC",
                "NACLASSIC",
                "NASODCLASSIC",
                "EUSODCLASSIC",
            ]
        )
        self.realm_region.currentIndexChanged.connect(self.on_combo_box_region_changed)
        self.realms_page_layout.addWidget(self.realm_region_label, 0, 0, 1, 1)
        self.realms_page_layout.addWidget(self.realm_region, 1, 0, 1, 1)

        self.realm_name_combobox = QComboBox(realm_page)
        self.realm_name_combobox.setEnabled(False)
        self.realm_realm_name_label = QLabel("Realm Name", realm_page)
        self.realm_realm_name_label.setToolTip("")
        self.realm_realm_name_label.setFixedHeight(10)
        self.realms_page_layout.addWidget(self.realm_realm_name_label, 2, 0, 1, 1)
        self.realms_page_layout.addWidget(self.realm_name_combobox, 3, 0, 1, 1)

        self.realm_name_input = QLineEdit(realm_page)
        self.realm_name_input_label = QLabel("Add Realm Name", realm_page)
        self.realm_name_input_label.setToolTip("")
        self.realm_name_input_label.setFixedHeight(10)
        self.realms_page_layout.addWidget(self.realm_name_input_label, 4, 0, 1, 1)
        self.realms_page_layout.addWidget(self.realm_name_input, 5, 0, 1, 1)

        self.realm_id_input = QLineEdit(realm_page)
        self.realm_id_input_label = QLabel("Add Realm ID", realm_page)
        self.realm_id_input_label.setToolTip("")
        self.realm_id_input_label.setFixedHeight(10)
        self.realms_page_layout.addWidget(self.realm_id_input_label, 6, 0, 1, 1)
        self.realms_page_layout.addWidget(self.realm_id_input, 7, 0, 1, 1)

        self.add_realm_button = QPushButton("Add Realm")
        self.add_realm_button.setToolTip("")
        self.add_realm_button.clicked.connect(self.add_realm_to_list)
        self.realms_page_layout.addWidget(self.add_realm_button, 8, 0, 1, 1)

        self.reset_realm_button = QPushButton("Reset Realm List")
        self.reset_realm_button.setToolTip("")
        self.reset_realm_button.clicked.connect(self.reset_realm_list)
        self.realms_page_layout.addWidget(self.reset_realm_button, 9, 0, 1, 1)

        self.remove_realm_button = QPushButton("Remove Realm")
        self.remove_realm_button.setToolTip("")
        self.remove_realm_button.clicked.connect(self.remove_realm_to_list)
        self.realms_page_layout.addWidget(self.remove_realm_button, 10, 0, 1, 1)

        self.realm_list_display = QListWidget(realm_page)
        self.realm_list_display.setSortingEnabled(True)
        self.realm_list_display.itemClicked.connect(self.realm_list_clicked)
        self.realms_page_layout.addWidget(self.realm_list_display, 0, 1, 11, 2)

    def make_side_buttons(self):
        self.go_to_home_button = QPushButton("Home Page")
        self.go_to_home_button.setFixedSize(150, 25)
        self.go_to_home_button.clicked.connect(self.go_to_home_page)
        self.layout_area.addWidget(self.go_to_home_button, 0, 0)

        self.go_to_pet_button = QPushButton("Pets")
        self.go_to_pet_button.setFixedSize(150, 25)
        self.go_to_pet_button.clicked.connect(self.go_to_pet_page)
        self.layout_area.addWidget(self.go_to_pet_button, 1, 0)

        self.go_to_item_button = QPushButton("Items")
        self.go_to_item_button.setFixedSize(150, 25)
        self.go_to_item_button.clicked.connect(self.go_to_item_page)
        self.layout_area.addWidget(self.go_to_item_button, 2, 0)

        self.go_to_ilvl_button = QPushButton("ILvl List")
        self.go_to_ilvl_button.setFixedSize(150, 25)
        self.go_to_ilvl_button.clicked.connect(self.go_to_ilvl_page)
        self.layout_area.addWidget(self.go_to_ilvl_button, 3, 0)

        self.go_to_settings_button = QPushButton("Application Settings")
        self.go_to_settings_button.setFixedSize(150, 25)
        self.go_to_settings_button.clicked.connect(self.go_to_settings_page)
        self.layout_area.addWidget(self.go_to_settings_button, 4, 0)

        self.go_to_realm_button = QPushButton("Realm Lists")
        self.go_to_realm_button.setFixedSize(150, 25)
        self.go_to_realm_button.clicked.connect(self.go_to_realms_page)
        self.layout_area.addWidget(self.go_to_realm_button, 5, 0)

        self.go_to_recommendations_button = QPushButton("Recommendations")
        self.go_to_recommendations_button.setFixedSize(150, 25)
        self.go_to_recommendations_button.clicked.connect(
            self.go_to_recommendations_page
        )
        self.layout_area.addWidget(self.go_to_recommendations_button, 6, 0)

        # # add a line to separate the buttons from the rest of the UI
        # self.line = QLabel(self)
        # self.line.setStyleSheet("background-color: white")
        # self.line.setFixedSize(150, 25)
        #
        # self.layout_area.addWidget(self.line, 6, 0)

        self.save_data_button = QPushButton("Save Data")
        self.save_data_button.setFixedSize(150, 25)
        self.save_data_button.clicked.connect(self.save_data_to_json)
        self.save_data_button.setToolTip("Save data without starting a scan.")
        self.layout_area.addWidget(self.save_data_button, 7, 0)

        self.reset_data_button = QPushButton("Reset Data")
        self.reset_data_button.setFixedSize(150, 25)
        self.reset_data_button.clicked.connect(self.reset_app_data)
        self.reset_data_button.setToolTip("Erase all data and reset the app.")
        self.layout_area.addWidget(self.reset_data_button, 8, 0)

        self.start_button = QPushButton("Start Alerts")
        self.start_button.setFixedSize(150, 25)
        self.start_button.clicked.connect(self.start_alerts)
        self.start_button.setToolTip(
            "Start the scan! Runs once on start and then waits for new data to send more alerts."
        )
        self.layout_area.addWidget(self.start_button, 9, 0)

        self.stop_button = QPushButton("Stop Alerts")
        self.stop_button.setFixedSize(150, 25)
        self.stop_button.clicked.connect(self.stop_alerts)
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip(
            "Gracefully stop the alerts.\nThis will not stop alerts in progress.\nYou may need to kill the process for a force stop."
        )
        self.layout_area.addWidget(self.stop_button, 10, 0)

        self.mega_alerts_progress = QLabel("Waiting for user to Start!")
        self.mega_alerts_progress.setFixedSize(150, 25)
        self.layout_area.addWidget(self.mega_alerts_progress, 11, 0)

    def make_home_page(self, home_page):

        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
        icon_path = "icon.ico"
        if windowsApp_Path is not None:
            icon_path = f"{windowsApp_Path}/icon.ico"

        # display the icon.ico
        self.icon = QLabel(home_page)
        self.icon.setPixmap(QtGui.QPixmap(icon_path))
        self.home_page_layout.addWidget(self.icon, 0, 0)

        # add the title
        self.title = QLabel(home_page)
        self.title.setText("Azeroth Auction Ace")
        self.title.setFont((QtGui.QFont("Arial", 30, QtGui.QFont.Bold)))
        self.home_page_layout.addWidget(self.title, 1, 0)

        # add link to patreon
        self.patreon_link = QLabel(home_page)
        self.patreon_link.setText(
            "<a href='https://www.patreon.com/indopan' style='color: white;'>Support the Project on Patreon</a>"
        )
        self.patreon_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.patreon_link.setOpenExternalLinks(True)
        self.home_page_layout.addWidget(self.patreon_link, 2, 0)

        # add discord link
        self.discord_link = QLabel(home_page)
        self.discord_link.setText(
            "<a href='https://discord.gg/9dHx2rEq9F' style='color: white;'>Join the Discord</a>"
        )
        self.discord_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.discord_link.setOpenExternalLinks(True)
        self.home_page_layout.addWidget(self.discord_link, 3, 0)

        # add main website link
        self.website_link = QLabel(home_page)
        self.website_link.setText(
            "<a href='https://saddlebagexchange.com' style='color: white;'>Check out our main website: Saddlebag Exchange</a>"
        )
        self.website_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.website_link.setOpenExternalLinks(True)
        self.home_page_layout.addWidget(self.website_link, 4, 0)

        # add a guides link
        self.guides_link = QLabel(home_page)
        self.guides_link.setText(
            "<a href='https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki' style='color: white;'>Check out our guides</a>"
        )
        self.guides_link.setFont((QtGui.QFont("Arial", 12, QtGui.QFont.Bold)))
        self.guides_link.setOpenExternalLinks(True)
        self.home_page_layout.addWidget(self.guides_link, 5, 0)

    def make_settings_page(self, settings_page):

        self.discord_webhook_input = QLineEdit(settings_page)
        self.discord_webhook_input_label = QLabel("Discord Webhook", settings_page)
        self.discord_webhook_input_label.setToolTip(
            "Setup a discord channel with a webhook url for sending the alert messages."
        )
        self.settings_page_layout.addWidget(
            self.discord_webhook_input_label, 0, 0, 1, 2
        )
        self.settings_page_layout.addWidget(self.discord_webhook_input, 1, 0, 1, 2)

        self.wow_client_id_input = QLineEdit(settings_page)
        self.wow_client_id_input_label = QLabel("WoW Client ID", settings_page)
        self.wow_client_id_input_label.setToolTip(
            "Go to https://develop.battle.net/access/clients\nand create a client, get the blizzard oauth client and secret ids."
        )
        self.settings_page_layout.addWidget(self.wow_client_id_input_label, 2, 0, 1, 2)
        self.settings_page_layout.addWidget(self.wow_client_id_input, 3, 0, 1, 2)

        self.wow_client_secret_input = QLineEdit(settings_page)
        self.wow_client_secret_input_label = QLabel("WoW Client Secret", settings_page)
        self.wow_client_secret_input_label.setToolTip(
            "Go to https://develop.battle.net/access/clients\nand create a client, get the blizzard oauth client and secret ids."
        )
        self.settings_page_layout.addWidget(
            self.wow_client_secret_input_label, 4, 0, 1, 2
        )
        self.settings_page_layout.addWidget(self.wow_client_secret_input, 5, 0, 1, 2)

        self.authentication_token = QLineEdit(settings_page)
        self.authentication_token_label = QLabel(
            "Auction Assassin Token", settings_page
        )
        self.authentication_token_label.setToolTip(
            "Go to the Saddlebag Exchange Discord and generate a token with the bot command:\n/wow auctionassassintoken"
        )
        self.settings_page_layout.addWidget(self.authentication_token_label, 6, 0, 1, 2)
        self.settings_page_layout.addWidget(self.authentication_token, 7, 0, 1, 2)

        self.wow_region = QComboBox(settings_page)
        self.wow_region.addItems(
            ["EU", "NA", "EUCLASSIC", "NACLASSIC", "NASODCLASSIC", "EUSODCLASSIC"]
        )
        self.wow_region_label = QLabel("Auction Assassin Token", settings_page)
        self.wow_region_label.setToolTip(
            "Pick your region, currently supporting: EU, NA, EU-Classic, NA-Classic, EU-SoD-Classic and NA-SoD-Classic."
        )
        self.settings_page_layout.addWidget(self.wow_region_label, 8, 0, 1, 1)
        self.settings_page_layout.addWidget(self.wow_region, 9, 0, 1, 1)

        self.number_of_mega_threads = QLineEdit(settings_page)
        self.number_of_mega_threads.setText("48")
        self.number_of_mega_threads_label = QLabel("Number of Threads", settings_page)
        self.number_of_mega_threads_label.setToolTip(
            "Change the thread count.\nDo 100 for the fastest scans, but RIP to ur CPU and MEM."
        )
        self.settings_page_layout.addWidget(
            self.number_of_mega_threads_label, 8, 1, 1, 1
        )
        self.settings_page_layout.addWidget(self.number_of_mega_threads, 9, 1, 1, 1)

        self.scan_time_min = QLineEdit(settings_page)
        self.scan_time_min.setText("1")
        self.scan_time_min_label = QLabel("Scan Time Min", settings_page)
        self.scan_time_min_label.setToolTip(
            "Increase or decrease the minutes before or after the data update to start timed scans."
        )
        self.settings_page_layout.addWidget(self.scan_time_min_label, 10, 1, 1, 1)
        self.settings_page_layout.addWidget(self.scan_time_min, 11, 1, 1, 1)

        self.scan_time_max = QLineEdit(settings_page)
        self.scan_time_max.setText("3")
        self.scan_time_max_label = QLabel("Scan Time Max", settings_page)
        self.scan_time_max_label.setToolTip(
            "Increase or decrease the minutes before or after the data update to stop running scans."
        )
        self.settings_page_layout.addWidget(self.scan_time_max_label, 12, 1, 1, 1)
        self.settings_page_layout.addWidget(self.scan_time_max, 13, 1, 1, 1)

        self.discount_percent = QLineEdit(settings_page)
        self.discount_percent.setText("10")
        self.discount_percent_label = QLabel("Discount vs Average", settings_page)
        self.discount_percent_label.setToolTip(
            "Set the price recommendation discount\n"
            + "1 to 100, smaller number means a better price.\n"
            + "ex: if you set 10 pecent and avg price is 100k, it recommends you snipe for 10k."
        )
        self.settings_page_layout.addWidget(self.discount_percent_label, 14, 1, 1, 1)
        self.settings_page_layout.addWidget(self.discount_percent, 15, 1, 1, 1)

        self.show_bid_prices = QCheckBox("Show Bid Prices", settings_page)
        self.show_bid_prices.setToolTip(
            "Show items with Bid prices below your price limit on Desired Items"
        )
        self.settings_page_layout.addWidget(self.show_bid_prices, 10, 0, 1, 1)

        self.wow_head_link = QCheckBox("Show wowhead link", settings_page)
        self.wow_head_link.setToolTip(
            "Uses wowhead links instead of Undermine and shows pictures."
        )
        self.settings_page_layout.addWidget(self.wow_head_link, 11, 0, 1, 1)

        self.no_links = QCheckBox("Disable Web Links", settings_page)
        self.no_links.setToolTip(
            "Disable all Wowhead, undemine and saddlebag links from discord messages."
        )
        self.settings_page_layout.addWidget(self.no_links, 12, 0, 1, 1)

        self.russian_realms = QCheckBox("No Russian Realms", settings_page)
        self.russian_realms.setChecked(True)
        self.russian_realms.setToolTip("Removes alerts from Russian Realms.")
        self.settings_page_layout.addWidget(self.russian_realms, 13, 0, 1, 1)

        self.refresh_alerts = QCheckBox("Refresh Alerts", settings_page)
        self.refresh_alerts.setToolTip("Set to true to refresh alerts every 1 hour.")
        self.settings_page_layout.addWidget(self.refresh_alerts, 14, 0, 1, 1)

        self.debug_mode = QCheckBox("Debug Mode", settings_page)
        self.debug_mode.setToolTip(
            "Trigger a scan on all realms once.\nUse this to test make sure your data is working."
        )
        self.settings_page_layout.addWidget(self.debug_mode, 15, 0, 1, 1)

        self.faction = QComboBox(settings_page)
        self.faction.addItems(["all", "horde", "alliance", "booty bay"])
        self.faction_label = QLabel("Faction AH", settings_page)
        self.faction_label.setToolTip(
            "Pick your faction for classic or pick 'all' to see all auctionhouses, Retail uses 'all' by default for cross faction AH."
        )
        self.settings_page_layout.addWidget(self.faction_label, 16, 0, 1, 1)
        self.settings_page_layout.addWidget(self.faction, 17, 0, 1, 1)

        self.import_config_button = QPushButton("Import Config")
        self.import_config_button.clicked.connect(self.import_configs)
        self.import_config_button.setToolTip("Import your mega_data.json config.")

        self.settings_page_layout.addWidget(self.import_config_button, 18, 0, 1, 1)

    def make_pet_page(self, pet_page):

        self.pet_id_input = QLineEdit(pet_page)
        self.pet_id_input_label = QLabel("Pet ID", pet_page)
        self.pet_id_input_label.setToolTip(
            "Add the Pet ID that you want to snipe.\nYou can find that id at the end of the undermine exchange link for the item next to 82800 (which is the item id for pet cages)\nhttps://undermine.exchange/#us-suramar/82800-3390."
        )
        self.pet_page_layout.addWidget(self.pet_id_input_label, 0, 0, 1, 1)
        self.pet_page_layout.addWidget(self.pet_id_input, 1, 0, 1, 1)

        self.pet_price_input = QLineEdit(pet_page)
        self.pet_price_input_label = QLabel("Price", pet_page)
        self.pet_price_input_label.setToolTip(
            "Pick a price you want to buy at or under."
        )
        self.pet_page_layout.addWidget(self.pet_price_input_label, 0, 1, 1, 1)
        self.pet_page_layout.addWidget(self.pet_price_input, 1, 1, 1, 1)

        self.pet_name_input = QComboBox(pet_page)
        self.pet_name_input.setEnabled(False)
        self.pet_page_layout.addWidget(self.pet_name_input, 2, 0, 1, 2)

        self.add_pet_button = QPushButton("Add/Update Pet")
        self.add_pet_button.setToolTip("Add/Update pet to your snipe list.")
        self.add_pet_button.clicked.connect(self.add_pet_to_dict)
        self.pet_page_layout.addWidget(self.add_pet_button, 3, 0, 1, 1)

        self.remove_pet_button = QPushButton("Remove Pet")
        self.remove_pet_button.setToolTip("Remove pet from your snipe list.")
        self.remove_pet_button.clicked.connect(self.remove_pet_to_dict)
        self.pet_page_layout.addWidget(self.remove_pet_button, 3, 1, 1, 1)

        self.pet_list_display = QListWidget(pet_page)

        self.pet_list_display.setSortingEnabled(True)

        self.pet_list_display.itemClicked.connect(self.pet_list_double_clicked)
        self.pet_page_layout.addWidget(self.pet_list_display, 4, 0, 13, 2)

        self.import_pet_data_button = QPushButton("Import Pet Data")
        self.import_pet_data_button.setToolTip("Import your desired_pets.json config")
        self.import_pet_data_button.clicked.connect(self.import_pet_data)
        self.pet_page_layout.addWidget(self.import_pet_data_button, 17, 0, 1, 2)

        self.erase_pet_data_button = QPushButton("Erase Pet Data")
        self.erase_pet_data_button.setToolTip("Erase your pet list")
        self.erase_pet_data_button.clicked.connect(self.erase_pet_data)
        self.pet_page_layout.addWidget(self.erase_pet_data_button, 18, 0, 1, 2)

    def make_item_page(self, item_page):

        self.item_id_input = QLineEdit(item_page)
        self.item_id_input_label = QLabel("Item ID", item_page)
        self.item_id_input_label.setToolTip(
            "Add the item id of any item you want to buy.\nYou can search by name for them here with recommended prices\nhttps://temp.saddlebagexchange.com/megaitemnames"
        )
        self.item_page_layout.addWidget(self.item_id_input_label, 0, 0, 1, 1)
        self.item_page_layout.addWidget(self.item_id_input, 1, 0, 1, 1)

        self.item_price_input = QLineEdit(item_page)
        self.item_price_input_label = QLabel("Price", item_page)
        self.item_price_input_label.setToolTip(
            "Pick a price you want to buy at or under."
        )
        self.item_page_layout.addWidget(self.item_price_input_label, 0, 1, 1, 1)
        self.item_page_layout.addWidget(self.item_price_input, 1, 1, 1, 1)

        self.item_name_input = QComboBox(item_page)
        self.item_name_input.setEnabled(False)
        self.item_page_layout.addWidget(self.item_name_input, 2, 0, 1, 2)

        self.add_item_button = QPushButton("Add/Update Item")
        self.add_item_button.setToolTip("Add/Update item to your snipe list.")
        self.add_item_button.clicked.connect(self.add_item_to_dict)
        self.item_page_layout.addWidget(self.add_item_button, 3, 0, 1, 1)

        self.remove_item_button = QPushButton("Remove Item")
        self.remove_item_button.setToolTip("Remove item from your snipe list.")
        self.remove_item_button.clicked.connect(self.remove_item_to_dict)
        self.item_page_layout.addWidget(self.remove_item_button, 3, 1, 1, 1)

        self.item_list_display = QListWidget(item_page)
        self.item_list_display.setSortingEnabled(True)

        self.item_list_display.itemClicked.connect(self.item_list_double_clicked)
        self.item_page_layout.addWidget(self.item_list_display, 4, 0, 13, 2)

        self.import_item_data_button = QPushButton("Import Item Data")
        self.import_item_data_button.setToolTip("Import your desired_items.json config")
        self.import_item_data_button.clicked.connect(self.import_item_data)
        self.item_page_layout.addWidget(self.import_item_data_button, 17, 0, 1, 1)

        self.import_pbs_data_button = QPushButton("Import PBS Data")
        self.import_pbs_data_button.setToolTip(
            "Import your Point Blank Sniper text files"
        )
        self.import_pbs_data_button.clicked.connect(self.import_pbs_data)
        self.item_page_layout.addWidget(self.import_pbs_data_button, 17, 1, 1, 1)

        self.erase_item_data_button = QPushButton("Erase Item Data")
        self.erase_item_data_button.setToolTip("Erase your desired_items.json config")
        self.erase_item_data_button.clicked.connect(self.erase_item_data)
        self.item_page_layout.addWidget(self.erase_item_data_button, 18, 0, 1, 1)

    def make_ilvl_page(self, ilvl_page):

        self.ilvl_item_input = QLineEdit(ilvl_page)
        self.ilvl_item_input_label = QLabel("Item ID(s)", ilvl_page)
        self.ilvl_item_input_label.setToolTip(
            "Leave blank to snipe all items at this Ilvl.\nAdd the Item IDs of the BOE you want to snipe specific items separated by a comma\nex: 1,2,99,420420"
        )
        self.ilvl_item_input_label.setFixedSize(75, 15)
        self.ilvl_item_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_item_input_label, 0, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_item_input, 1, 0, 1, 1)

        self.ilvl_input = QLineEdit(ilvl_page)
        self.ilvl_input_label = QLabel("Item level", ilvl_page)
        self.ilvl_input_label.setToolTip(
            "Set the minimum item level you want to snipe."
        )
        self.ilvl_input_label.setFixedSize(75, 15)
        self.ilvl_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_input_label, 2, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_input, 3, 0, 1, 1)

        self.ilvl_price_input = QLineEdit(ilvl_page)
        self.ilvl_price_input_label = QLabel("Buyout", ilvl_page)
        self.ilvl_price_input_label.setToolTip(
            "Set the maximum buyout you want to snipe."
        )
        self.ilvl_price_input_label.setFixedSize(75, 15)
        self.ilvl_price_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_price_input_label, 4, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_price_input, 5, 0, 1, 1)

        self.ilvl_sockets = QCheckBox("Sockets", ilvl_page)
        self.ilvl_sockets.setToolTip("Do you want the item to have Sockets?")
        self.ilvl_page_layout.addWidget(self.ilvl_sockets, 6, 0, 1, 1)

        self.ilvl_speed = QCheckBox("Speed", ilvl_page)
        self.ilvl_speed.setToolTip("Do you want the item to have Speed?")
        self.ilvl_page_layout.addWidget(self.ilvl_speed, 7, 0, 1, 1)

        self.ilvl_leech = QCheckBox("Leech", ilvl_page)
        self.ilvl_leech.setToolTip("Do you want the item to have Leech?")
        self.ilvl_page_layout.addWidget(self.ilvl_leech, 8, 0, 1, 1)

        self.ilvl_avoidance = QCheckBox("Avoidance", ilvl_page)
        self.ilvl_avoidance.setToolTip("Do you want the item to have Avoidance?")
        self.ilvl_page_layout.addWidget(self.ilvl_avoidance, 9, 0, 1, 1)

        self.add_ilvl_button = QPushButton("Add/Update Item", ilvl_page)
        self.add_ilvl_button.setToolTip("Add/Update item to your snipe list.")
        self.add_ilvl_button.clicked.connect(self.add_ilvl_to_list)
        self.ilvl_page_layout.addWidget(self.add_ilvl_button, 10, 0, 1, 1)

        self.remove_ilvl_button = QPushButton("Remove Item", ilvl_page)
        self.remove_ilvl_button.setToolTip("Remove item from your snipe list.")
        self.remove_ilvl_button.clicked.connect(self.remove_ilvl_to_list)
        self.ilvl_page_layout.addWidget(self.remove_ilvl_button, 11, 0, 1, 1)

        self.ilvl_list_display = QListWidget(ilvl_page)
        self.ilvl_list_display.setSortingEnabled(True)

        self.ilvl_list_display.itemClicked.connect(self.ilvl_list_double_clicked)
        self.ilvl_page_layout.addWidget(self.ilvl_list_display, 0, 1, 11, 2)

        self.import_ilvl_data_button = QPushButton("Import Desired ILvl List Data")
        self.import_ilvl_data_button.setToolTip(
            "Import your desired_ilvl_list.json config"
        )
        self.import_ilvl_data_button.clicked.connect(self.import_ilvl_data)
        self.ilvl_page_layout.addWidget(self.import_ilvl_data_button, 11, 1, 1, 2)

        self.erase_ilvl_data_button = QPushButton("erase Desired ILvl List Data")
        self.erase_ilvl_data_button.setToolTip(
            "erase your desired_ilvl_list.json config"
        )
        self.erase_ilvl_data_button.clicked.connect(self.erase_ilvl_data)
        self.ilvl_page_layout.addWidget(self.erase_ilvl_data_button, 12, 1, 1, 2)

    def make_recommendations_page(self, recommendations_page):
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

        self.minimum_average_price_input = QLineEdit(recommendations_page)
        self.minimum_average_price_input.setText("2000")
        self.minimum_average_price_input_label = QLabel(
            "Minimum Desired average price", recommendations_page
        )
        self.minimum_average_price_input_label.setToolTip("")
        self.minimum_average_price_input_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.minimum_average_price_input_label, 0, 0, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.minimum_average_price_input, 1, 0, 1, 1
        )

        self.minimum_desired_sales_input = QLineEdit(recommendations_page)
        self.minimum_desired_sales_input.setText("0.1")
        self.minimum_desired_sales_input_label = QLabel(
            "Minimum Desired sales per day", recommendations_page
        )
        self.minimum_desired_sales_input_label.setToolTip("")
        self.minimum_desired_sales_input_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.minimum_desired_sales_input_label, 0, 1, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.minimum_desired_sales_input, 1, 1, 1, 1
        )

        self.recommendations_region = QComboBox(recommendations_page)
        self.recommendations_region_label = QLabel(
            "Select your Region", recommendations_page
        )
        self.recommendations_region_label.setToolTip("")
        self.recommendations_region_label.setFixedHeight(20)
        self.recommendations_region.addItems(["Europe", "North America"])
        self.recommendations_region.currentIndexChanged.connect(
            self.region_combo_changed
        )
        self.recommendations_page_layout.addWidget(
            self.recommendations_region_label, 2, 0, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.recommendations_region, 3, 0, 1, 1
        )

        self.recommendations_realm_combobox = QComboBox(recommendations_page)
        self.recommendations_realm_combobox.setEditable(True)
        self.recommendations_realm_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.recommendations_realm_combobox.completer()
        self.recommendations_realm_combobox.addItems(self.eu_realms)
        self.realm_recommendations_realm_label = QLabel(
            "Search for server by name", recommendations_page
        )
        self.realm_recommendations_realm_label.setToolTip("")
        self.realm_recommendations_realm_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.realm_recommendations_realm_label, 2, 1, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.recommendations_realm_combobox, 3, 1, 1, 1
        )

        self.item_sub_category = QComboBox(recommendations_page)
        self.item_sub_category_label = QLabel("Item Sub Category", recommendations_page)
        self.item_sub_category_label.setToolTip("")
        self.item_sub_category_label.setFixedHeight(20)
        self.item_sub_category.addItems(["All"])
        self.recommendations_page_layout.addWidget(
            self.item_sub_category_label, 4, 1, 1, 1
        )
        self.recommendations_page_layout.addWidget(self.item_sub_category, 5, 1, 1, 1)

        self.item_category = QComboBox(recommendations_page)
        self.item_category_label = QLabel("Item Category", recommendations_page)
        self.item_category_label.setToolTip("")
        self.item_category.currentIndexChanged.connect(self.category_combo_changed)
        self.item_category_label.setFixedHeight(20)
        self.item_category.addItems(self.item_category_list)
        self.recommendations_page_layout.addWidget(self.item_category_label, 4, 0, 1, 1)
        self.recommendations_page_layout.addWidget(self.item_category, 5, 0, 1, 1)

        self.item_quality = QComboBox(recommendations_page)
        self.item_quality_label = QLabel("Item Quality", recommendations_page)
        self.item_quality_label.setToolTip("")
        self.item_quality_label.setFixedHeight(20)
        self.item_quality.addItems(self.item_quality_list)
        self.recommendations_page_layout.addWidget(self.item_quality_label, 6, 0, 1, 1)
        self.recommendations_page_layout.addWidget(self.item_quality, 7, 0, 1, 1)

        self.minimum_item_level_input = QLineEdit(recommendations_page)
        self.minimum_item_level_input.setText("-1")
        self.minimum_item_level_input_label = QLabel(
            "Minimum Base Item Level (ilvl)", recommendations_page
        )
        self.minimum_item_level_input_label.setToolTip("")
        self.minimum_item_level_input_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.minimum_item_level_input_label, 6, 1, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.minimum_item_level_input, 7, 1, 1, 1
        )

        self.minimum_required_level_input = QLineEdit(recommendations_page)
        self.minimum_required_level_input.setText("-1")
        self.minimum_required_level_input_label = QLabel(
            "Minimum Required Level", recommendations_page
        )
        self.minimum_required_level_input_label.setToolTip("")
        self.minimum_required_level_input_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.minimum_required_level_input_label, 8, 0, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.minimum_required_level_input, 9, 0, 1, 1
        )

        self.commodity_items = QCheckBox("Commodity items", recommendations_page)
        self.commodity_items.setToolTip("DO NOT USE, WILL ADD THIS LATER")
        self.recommendations_page_layout.addWidget(self.commodity_items, 8, 1, 1, 1)

        self.local_discount_percent = QLineEdit(recommendations_page)
        self.local_discount_percent.setText("50")
        self.local_discount_percent_label = QLabel(
            "Local Discount Percent", recommendations_page
        )
        self.local_discount_percent_label.setToolTip(
            "What percent of normal price do you want it?\nex: if it sells for 10k and we pick 30% then we try too snipe at 3k."
        )
        self.local_discount_percent_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.local_discount_percent_label, 10, 0, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.local_discount_percent, 11, 0, 1, 1
        )

        self.minimum_market_value = QLineEdit(recommendations_page)
        self.minimum_market_value.setText("5000")
        self.minimum_market_value_label = QLabel(
            "Minimum Market Value", recommendations_page
        )
        self.minimum_market_value_label.setToolTip(
            "Minimum gold an item earns per day on any average server."
        )
        self.minimum_market_value_label.setFixedHeight(20)
        self.recommendations_page_layout.addWidget(
            self.minimum_market_value_label, 10, 1, 1, 1
        )
        self.recommendations_page_layout.addWidget(
            self.minimum_market_value, 11, 1, 1, 1
        )

        self.search_button = QPushButton("Search")
        self.recommendations_page_layout.addWidget(self.search_button, 12, 0, 1, 2)

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
            else:
                return

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

    def go_to_home_page(self):
        self.stacked_widget.setCurrentIndex(0)

    def go_to_pet_page(self):
        self.stacked_widget.setCurrentIndex(1)

    def go_to_item_page(self):
        self.stacked_widget.setCurrentIndex(2)

    def go_to_ilvl_page(self):
        self.stacked_widget.setCurrentIndex(3)

    def go_to_settings_page(self):
        self.stacked_widget.setCurrentIndex(4)

    def go_to_realms_page(self):
        self.stacked_widget.setCurrentIndex(5)

    def go_to_recommendations_page(self):
        self.stacked_widget.setCurrentIndex(6)

    def api_data_received(self, pet_statistics, item_statistics):
        self.pet_statistics = pet_statistics
        self.item_statistics = item_statistics

        self.pet_name_input.addItems(
            self.pet_statistics.sort_values(by="itemName")["itemName"].tolist()
        )
        self.pet_name_input.setEditable(True)
        self.pet_name_input.setInsertPolicy(QComboBox.NoInsert)
        self.pet_name_input.completer()
        self.pet_name_input.currentIndexChanged.connect(self.on_combo_box_pet_changed)

        self.item_name_input.addItems(
            self.item_statistics.sort_values(by="itemName")["itemName"].tolist()
        )
        self.item_name_input.setEditable(True)
        self.item_name_input.setInsertPolicy(QComboBox.NoInsert)
        self.item_name_input.completer()
        self.item_name_input.currentIndexChanged.connect(self.on_combo_box_item_changed)

        self.item_name_input.setEnabled(True)
        self.item_name_input.setStyleSheet(
            "QComboBox { background-color: #1D2023; color: white; }"
            "QComboBox::editable { background: #1D2023; color: white; }"
            "QComboBox::drop-down { border: 0px; }"
        )
        self.pet_name_input.setEnabled(True)
        self.pet_name_input.setStyleSheet(
            "QComboBox { background-color: #1D2023; color: white; }"
            "QComboBox::editable { background: #1D2023; color: white; }"
            "QComboBox::drop-down { border: 0px; }"
        )

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

    def on_combo_box_pet_changed(self, index):
        # This function will be called whenever the user selects a different item
        selected_pet = self.pet_name_input.currentText()
        selected_pet_stats = self.pet_statistics[
            self.pet_statistics["itemName"] == selected_pet
        ]
        selected_pet_id = selected_pet_stats["itemID"].iloc[0]
        if str(selected_pet_id) in self.pet_list.keys():
            selected_pet_price = self.pet_list[str(selected_pet_id)]
        else:
            selected_pet_price = selected_pet_stats["desiredPrice"].iloc[0]

        # if the user has not set a price for the item, set the price from TSM stats
        if not self.pet_price_input.text() or str(selected_pet_id) not in self.pet_list:
            try:
                discount_percent = int(self.discount_percent.text()) / 100
                recommended_price = str(
                    int(float(selected_pet_price) * discount_percent)
                )
                self.pet_price_input.setText(recommended_price)
            except:
                self.pet_price_input.setText("10")
                recommended_price = str(int(float(selected_pet_price) * 0.1))
                self.pet_price_input.setText(recommended_price)

        else:
            self.pet_price_input.setText(str(selected_pet_price))

        self.pet_id_input.setText(str(selected_pet_id))

    def on_combo_box_region_changed(self, index):
        self.realm_list_display.clear()
        self.realm_name_combobox.clear()
        selected_realm = self.realm_region.currentText()
        match selected_realm:
            case "EU":
                from utils.realm_data import EU_CONNECTED_REALMS_IDS as realm_list

                data_to_insert = self.eu_connected_realms

            case "NA":
                from utils.realm_data import NA_CONNECTED_REALMS_IDS as realm_list

                data_to_insert = self.na_connected_realms

            case "EUCLASSIC":
                from utils.realm_data import (
                    EUCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.EUCLASSIC_connected_realms

            case "NACLASSIC":
                from utils.realm_data import (
                    NACLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.NACLASSIC_connected_realms

            case "NASODCLASSIC":
                from utils.realm_data import (
                    NASODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.NASODCLASSIC_connected_realms

            case "EUSODCLASSIC":
                from utils.realm_data import (
                    EUSODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.EUSODCLASSIC_connected_realms

            case _:
                QMessageBox.critical(self, "Region List", "Select valid region.")
                return False

        with open(data_to_insert, "r") as f:
            data = json.load(f)

        self.realm_name_combobox.addItems(list(realm_list.keys()))
        self.realm_name_combobox.setEditable(True)
        self.realm_name_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.realm_name_combobox.completer()
        self.realm_name_combobox.currentIndexChanged.connect(
            self.on_combo_box_realm_name_changed
        )
        self.realm_name_combobox.setStyleSheet(
            "QComboBox { background-color: #1D2023; color: white; }"
            "QComboBox::editable { background: #1D2023; color: white; }"
            "QComboBox::drop-down { border: 0px; }"
        )
        self.realm_name_combobox.setEnabled(True)

        for key, value in data.items():
            self.realm_list_display.insertItem(
                self.realm_list_display.count(), f"Name: {key}; ID: {value};"
            )

    def on_combo_box_realm_name_changed(self, index):
        selected_realm_name = self.realm_name_combobox.currentText()
        if selected_realm_name == "":
            return 0
        selected_realm = self.realm_region.currentText()
        match selected_realm:
            case "EU":
                from utils.realm_data import EU_CONNECTED_REALMS_IDS as realm_list

            case "NA":
                from utils.realm_data import NA_CONNECTED_REALMS_IDS as realm_list

            case "EUCLASSIC":
                from utils.realm_data import (
                    EUCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

            case "NACLASSIC":
                from utils.realm_data import (
                    NACLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

            case "NASODCLASSIC":
                from utils.realm_data import (
                    NASODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

            case "EUSODCLASSIC":
                from utils.realm_data import (
                    EUSODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

            case _:
                QMessageBox.critical(self, "Region List", "Select valid region.")
                return False

        self.realm_name_input.setText(str(selected_realm_name))
        self.realm_id_input.setText(str(realm_list[selected_realm_name]))

    def add_realm_to_list(self):
        if self.realm_name_input.text() == "":
            return 0

        selected_realm = self.realm_region.currentText()
        match selected_realm:
            case "EU":
                data_to_insert = self.eu_connected_realms

            case "NA":
                data_to_insert = self.na_connected_realms

            case "EUCLASSIC":
                data_to_insert = self.EUCLASSIC_connected_realms

            case "NACLASSIC":
                data_to_insert = self.NACLASSIC_connected_realms

            case "NASODCLASSIC":
                data_to_insert = self.NASODCLASSIC_connected_realms

            case "EUSODCLASSIC":
                data_to_insert = self.EUSODCLASSIC_connected_realms

            case _:
                QMessageBox.critical(self, "Region List", "Select valid region.")
                return False

        with open(data_to_insert, "r") as f:
            data = json.load(f)

        data[self.realm_name_input.text()] = int(self.realm_id_input.text())

        self.realm_list_display.clear()

        for key, value in data.items():
            self.realm_list_display.insertItem(
                self.realm_list_display.count(), f"Name: {key}; ID: {value};"
            )

        self.save_json_file(data_to_insert, data)

    def remove_realm_to_list(self):
        if self.realm_name_input.text() == "":
            return 0

        selected_realm = self.realm_region.currentText()
        match selected_realm:
            case "EU":
                data_to_insert = self.eu_connected_realms

            case "NA":
                data_to_insert = self.na_connected_realms

            case "EUCLASSIC":
                data_to_insert = self.EUCLASSIC_connected_realms

            case "NACLASSIC":
                data_to_insert = self.NACLASSIC_connected_realms

            case "NASODCLASSIC":
                data_to_insert = self.NASODCLASSIC_connected_realms

            case "EUSODCLASSIC":
                data_to_insert = self.EUSODCLASSIC_connected_realms

            case _:
                QMessageBox.critical(self, "Region List", "Select valid region.")
                return False

        with open(data_to_insert, "r") as f:
            data = json.load(f)

        try:
            del data[self.realm_name_input.text()]

        except KeyError as e:
            QMessageBox.critical(
                self,
                "Removing Realm Error",
                f"Realm already not in the list",
            )
            return 0

        self.realm_list_display.clear()

        for key, value in data.items():
            self.realm_list_display.insertItem(
                self.realm_list_display.count(), f"Name: {key}; ID: {value};"
            )

        self.realm_name_input.setText("")
        self.realm_id_input.setText("")

        self.save_json_file(data_to_insert, data)

    def reset_realm_list(self):
        selected_realm = self.realm_region.currentText()
        match selected_realm:
            case "EU":
                from utils.realm_data import EU_CONNECTED_REALMS_IDS as realm_list

                data_to_insert = self.eu_connected_realms

            case "NA":
                from utils.realm_data import NA_CONNECTED_REALMS_IDS as realm_list

                data_to_insert = self.na_connected_realms

            case "EUCLASSIC":
                from utils.realm_data import (
                    EUCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.EUCLASSIC_connected_realms

            case "NACLASSIC":
                from utils.realm_data import (
                    NACLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.NACLASSIC_connected_realms

            case "NASODCLASSIC":
                from utils.realm_data import (
                    NASODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.NASODCLASSIC_connected_realms

            case "EUSODCLASSIC":
                from utils.realm_data import (
                    EUSODCLASSIC_CONNECTED_REALMS_IDS as realm_list,
                )

                data_to_insert = self.EUSODCLASSIC_connected_realms

            case _:
                QMessageBox.critical(self, "Region List", "Select valid region.")
                return False

        with open(data_to_insert, "w") as json_file:
            json.dump(realm_list, json_file, indent=4)

        self.realm_list_display.clear()

        for key, value in realm_list.items():
            self.realm_list_display.insertItem(
                self.realm_list_display.count(), f"Name: {key}; ID: {value};"
            )

    def check_config_file(self, path_to_config):
        try:
            with open(path_to_config, encoding="utf-8") as json_file:
                raw_mega_data = json.load(json_file)
            if "MEGA_WEBHOOK_URL" in raw_mega_data:
                self.discord_webhook_input.setText(raw_mega_data["MEGA_WEBHOOK_URL"])

            if "WOW_CLIENT_ID" in raw_mega_data:
                self.wow_client_id_input.setText(raw_mega_data["WOW_CLIENT_ID"])

            if "WOW_CLIENT_SECRET" in raw_mega_data:
                self.wow_client_secret_input.setText(raw_mega_data["WOW_CLIENT_SECRET"])

            if "AUTHENTICATION_TOKEN" in raw_mega_data:
                self.authentication_token.setText(raw_mega_data["AUTHENTICATION_TOKEN"])

            if "WOW_REGION" in raw_mega_data:
                index = self.wow_region.findText(raw_mega_data["WOW_REGION"])
                if index >= 0:
                    self.wow_region.setCurrentIndex(index)

            if "FACTION" in raw_mega_data:
                index = self.faction.findText(raw_mega_data["FACTION"])
                if index >= 0:
                    self.faction.setCurrentIndex(index)

            if "SHOW_BID_PRICES" in raw_mega_data:
                self.show_bid_prices.setChecked(raw_mega_data["SHOW_BID_PRICES"])

            if "MEGA_THREADS" in raw_mega_data:
                self.number_of_mega_threads.setText(str(raw_mega_data["MEGA_THREADS"]))

            if "WOWHEAD_LINK" in raw_mega_data:
                self.wow_head_link.setChecked(raw_mega_data["WOWHEAD_LINK"])

            if "NO_LINKS" in raw_mega_data:
                self.no_links.setChecked(raw_mega_data["NO_LINKS"])

            if "DISCOUNT_PERCENT" in raw_mega_data:
                self.discount_percent.setText(str(raw_mega_data["DISCOUNT_PERCENT"]))

            if "NO_RUSSIAN_REALMS" in raw_mega_data:
                self.russian_realms.setChecked(raw_mega_data["NO_RUSSIAN_REALMS"])

            if "REFRESH_ALERTS" in raw_mega_data:
                self.refresh_alerts.setChecked(raw_mega_data["REFRESH_ALERTS"])

            if "SCAN_TIME_MAX" in raw_mega_data:
                self.scan_time_max.setText(str(raw_mega_data["SCAN_TIME_MAX"]))

            if "SCAN_TIME_MIN" in raw_mega_data:
                self.scan_time_min.setText(str(raw_mega_data["SCAN_TIME_MIN"]))

            if "DEBUG" in raw_mega_data:
                self.debug_mode.setChecked(raw_mega_data["DEBUG"])
        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Parsing Error", f"Could not parse JSON data in {path_to_config}"
            )
        except:
            QMessageBox.critical(
                self,
                "Loading Error",
                f"Could not load config settings from {path_to_config}",
            )

    def check_for_settings(self):
        data_folder = os.path.join(os.getcwd(), "AzerothAuctionAssassinData")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        backup_data_folder = os.path.join(
            os.getcwd(), "AzerothAuctionAssassinData", "backup"
        )
        if not os.path.exists(backup_data_folder):
            os.makedirs(backup_data_folder)

        if not os.path.exists(self.eu_connected_realms):
            from utils.realm_data import EU_CONNECTED_REALMS_IDS

            with open(self.eu_connected_realms, "w") as json_file:
                json.dump(EU_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.na_connected_realms):
            from utils.realm_data import NA_CONNECTED_REALMS_IDS

            with open(self.na_connected_realms, "w") as json_file:
                json.dump(NA_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.EUCLASSIC_connected_realms):
            from utils.realm_data import EUCLASSIC_CONNECTED_REALMS_IDS

            with open(self.EUCLASSIC_connected_realms, "w") as json_file:
                json.dump(EUCLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.NACLASSIC_connected_realms):
            from utils.realm_data import NACLASSIC_CONNECTED_REALMS_IDS

            with open(self.NACLASSIC_connected_realms, "w") as json_file:
                json.dump(NACLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.NASODCLASSIC_connected_realms):
            from utils.realm_data import NASODCLASSIC_CONNECTED_REALMS_IDS

            with open(self.NASODCLASSIC_connected_realms, "w") as json_file:
                json.dump(NASODCLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.EUSODCLASSIC_connected_realms):
            from utils.realm_data import EUSODCLASSIC_CONNECTED_REALMS_IDS

            with open(self.EUSODCLASSIC_connected_realms, "w") as json_file:
                json.dump(EUSODCLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if os.path.exists(self.path_to_data):
            self.check_config_file(self.path_to_data)

        if os.path.exists(self.path_to_desired_pets):
            self.pet_list = json.load(open(self.path_to_desired_pets))
            for key, value in self.pet_list.items():
                self.pet_list_display.insertItem(
                    self.pet_list_display.count(), f"Pet ID: {key}, Price: {value}"
                )

        if os.path.exists(self.path_to_desired_items):
            self.items_list = json.load(open(self.path_to_desired_items))
            for key, value in self.items_list.items():
                self.item_list_display.insertItem(
                    self.item_list_display.count(),
                    f"Item ID: {key}, Price: {value}",
                )

        if os.path.exists(self.path_to_desired_ilvl_list):
            self.ilvl_list = json.load(open(self.path_to_desired_ilvl_list))
            for ilvl_dict_data in self.ilvl_list:
                if "item_ids" not in ilvl_dict_data:
                    ilvl_dict_data["item_ids"] = []
                string_with_data = f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}"
                self.ilvl_list_display.insertItem(
                    self.ilvl_list_display.count(), string_with_data
                )

    def ilvl_list_double_clicked(self, item):
        item_split = item.text().replace(" ", "").split(":")

        item_id = item_split[1].split(";")[0]
        buyout = item_split[2].split(";")[0]
        ilvl = item_split[3].split(";")[0]
        sockets = item_split[4].split(";")[0]
        speed = item_split[5].split(";")[0]
        leech = item_split[6].split(";")[0]
        avoidance = item_split[7]

        self.ilvl_item_input.setText(item_id)
        self.ilvl_price_input.setText(buyout)

        self.ilvl_sockets.setChecked(sockets == "True")
        self.ilvl_speed.setChecked(speed == "True")
        self.ilvl_leech.setChecked(leech == "True")
        self.ilvl_avoidance.setChecked(avoidance == "True")

        self.ilvl_input.setText(ilvl)

    def realm_list_clicked(self, item):
        realm_split = item.text().split(":")
        realm_name = realm_split[1].split(";")[0][1::]
        realm_id = realm_split[2].split(";")[0][1::]

        self.realm_name_input.setText(realm_name)

        self.realm_id_input.setText(realm_id)

    def add_ilvl_to_list(self):
        ilvl = self.ilvl_input.text()
        price = self.ilvl_price_input.text()

        if ilvl == "" or price == "":
            QMessageBox.critical(
                self,
                "Incomplete Information",
                "Both ilvl and price fields are required.",
            )
            return False

        try:
            ilvl_int = int(ilvl)
            price_int = int(price)
        except ValueError:
            QMessageBox.critical(
                self, "Invalid Input", "Ilvl and price should be numbers."
            )
            return False

        # Check if ilvl is between 1 and 999
        if not 1 <= ilvl_int <= 999:
            QMessageBox.critical(
                self, "Incorrect Ilvl Value", "Ilvl must be between 1 and 999."
            )
            return False

        # Check if Price is between 1 and 10 million
        if not 1 <= price_int <= 10000000:
            QMessageBox.critical(
                self, "Incorrect Price", "Price must be between 1 and 10 million."
            )
            return False

        item_ids_text = self.ilvl_item_input.text()
        if item_ids_text == "":
            item_ids_list = []
        else:
            # Validate item IDs
            try:
                item_ids_list = list(
                    map(int, item_ids_text.replace(" ", "").split(","))
                )

                # Check if all items are between 100k and 500k
                if any(not 1 <= item_id <= 500000 for item_id in item_ids_list):
                    QMessageBox.critical(
                        self,
                        "Invalid Item ID",
                        "All item IDs should be between 1 and 500k.",
                    )
                    return False
            except ValueError:
                QMessageBox.critical(
                    self, "Invalid Input", f"Item IDs should be numbers."
                )
                return False

        # Create a dictionary with the data
        ilvl_dict_data = {
            "ilvl": ilvl_int,
            "buyout": price_int,
            "sockets": self.ilvl_sockets.isChecked(),
            "speed": self.ilvl_speed.isChecked(),
            "leech": self.ilvl_leech.isChecked(),
            "avoidance": self.ilvl_avoidance.isChecked(),
            "item_ids": item_ids_list,
        }

        if ilvl_dict_data not in self.ilvl_list:
            self.ilvl_list.append(ilvl_dict_data)
            self.ilvl_list_display.insertItem(
                self.ilvl_list_display.count(),
                f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}",
            )

        return True

    def remove_ilvl_to_list(self):
        if len(self.ilvl_input.text()) == 0:
            QMessageBox.critical(
                self,
                "Ilvl Removal Issue",
                "Please double click an ilvl json to remove it!",
            )
            return
        if self.ilvl_item_input.text() == "":
            item_ids_list = []
        else:
            item_ids_list = list(
                map(int, self.ilvl_item_input.text().replace(" ", "").split(","))
            )

        ilvl_dict_data = {
            "ilvl": int(self.ilvl_input.text()),
            "buyout": int(self.ilvl_price_input.text()),
            "sockets": self.ilvl_sockets.isChecked(),
            "speed": self.ilvl_speed.isChecked(),
            "leech": self.ilvl_leech.isChecked(),
            "avoidance": self.ilvl_avoidance.isChecked(),
            "item_ids": item_ids_list,
        }

        if ilvl_dict_data in self.ilvl_list:
            string_with_data = f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}"
            print(string_with_data)
            for x in range(self.ilvl_list_display.count()):
                if self.ilvl_list_display.item(x).text() == string_with_data:
                    self.ilvl_list_display.takeItem(x)
                    self.ilvl_list.remove(ilvl_dict_data)
                    return

    def erase_ilvl_data(self):
        self.ilvl_list_display.clear()
        self.ilvl_list = []

    def import_ilvl_data(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        try:
            with open(pathname) as file:
                a = self.ilvl_list
                self.ilvl_list += json.load(file)
            if not isinstance(self.ilvl_list, list):
                raise ValueError(
                    "Invalid JSON file.\nFile should contain a list of Desired Ilvl Objects."
                )
            # clear display before inserting new data
            self.ilvl_list_display.clear()
            for ilvl_dict_data in self.ilvl_list:
                if "item_ids" not in ilvl_dict_data:
                    item_ids = []
                else:
                    item_ids = ilvl_dict_data["item_ids"]
                buyout_price = ilvl_dict_data["buyout"]
                ilvl = ilvl_dict_data["ilvl"]
                sockets = ilvl_dict_data["sockets"]
                speed = ilvl_dict_data["speed"]
                leech = ilvl_dict_data["leech"]
                avoidance = ilvl_dict_data["avoidance"]

                # Check that all item IDs are valid integers, but allow list to be empty
                if not all(
                    isinstance(id, int) and 1 <= id <= 500000 for id in item_ids
                ):
                    raise ValueError(
                        f"Invalid item ID(s) in {item_ids}.\nIDs must be integers between 1-500,000."
                    )

                # Check that price is a valid integer within range
                if not (1 <= buyout_price <= 10000000):
                    raise ValueError(
                        f"Invalid buyout price {buyout_price}.\nPrices must be integers between 1-10,000,000."
                    )

                # Check that ilvl is a valid integer within range
                if not (200 <= ilvl <= 1000):
                    raise ValueError(
                        f"Invalid ILvl {ilvl}.\nILvl must be an integer between 200-1000."
                    )

                # Check that sockets, speed, leech and avoidance are booleans
                if not all(
                    isinstance(val, bool) for val in [sockets, speed, leech, avoidance]
                ):
                    raise ValueError(
                        "Sockets, speed, leech, and avoidance should be boolean values."
                    )

                string_with_data = f"Item ID: {','.join(map(str, item_ids))}; Price: {buyout_price}; ILvl: {ilvl}; Sockets: {sockets}; Speed: {speed}; Leech: {leech}; Avoidance: {avoidance}"
                self.ilvl_list_display.insertItem(
                    self.ilvl_list_display.count(), string_with_data
                )

        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Invalid JSON", "Please provide a valid JSON file!"
            )
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

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

    def erase_item_data(self):
        self.item_list_display.clear()
        self.items_list = {}

    def import_item_data(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.item_list_display.clear()

        try:
            with open(pathname) as file:
                self.items_list.update(json.load(file))
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

    def pet_list_double_clicked(self, item):
        item_split = item.text().replace(" ", "").split(":")
        pet_id = item_split[1].split(",")[0]
        self.pet_id_input.setText(pet_id)
        self.pet_price_input.setText(item_split[2])
        # find the itemName value from item_id in the item_statistics
        try:
            pet_name = self.pet_statistics[
                self.pet_statistics["itemID"] == int(pet_id)
            ].iloc[0]["itemName"]
            index = self.pet_name_input.findText(pet_name)
            self.pet_name_input.setCurrentIndex(index)
        except:
            self.pet_name_input.setCurrentText("Item ID not found")

    def add_pet_to_dict(self):
        pet_id = self.pet_id_input.text()
        pet_price = self.pet_price_input.text()

        if pet_id == "" or pet_price == "":
            QMessageBox.critical(
                self, "Incomplete Information", "All fields are required."
            )
            return False

        try:
            pet_id_int = int(pet_id)
            pet_price_int = int(pet_price)
        except ValueError:
            QMessageBox.critical(
                self, "Invalid Input", "Pet ID and Price should be numbers."
            )
            return False

        # Check if Pet ID is between 1 and 10000
        if not 1 <= pet_id_int <= 10000:
            QMessageBox.critical(
                self, "Incorrect Pet ID", "Pet ID must be between 1 and 10000."
            )
            return False

        # Check if Price is between 1 and 10 million
        if not 1 <= pet_price_int <= 10000000:
            QMessageBox.critical(
                self, "Incorrect Price", "Price must be between 1 and 10 million."
            )
            return False

        # If pet_id is already in the list, remove it
        if pet_id in self.pet_list:
            for existing_entry in range(self.pet_list_display.count()):
                if (
                    self.pet_list_display.item(existing_entry).text()
                    == f"Pet ID: {pet_id}, Price: {self.pet_list[pet_id]}"
                ):
                    self.pet_list_display.takeItem(existing_entry)
                    break

        # Add or replace an item in pet_list
        self.pet_list[pet_id] = pet_price
        # Add new item to the display list
        self.pet_list_display.insertItem(
            self.pet_list_display.count(), f"Pet ID: {pet_id}, Price: {pet_price}"
        )

        return True

    def remove_pet_to_dict(self):
        if self.pet_id_input.text() in self.pet_list:
            for x in range(self.pet_list_display.count()):
                if (
                    self.pet_list_display.item(x).text()
                    == f"Pet ID: {self.pet_id_input.text()}, Price: {self.pet_list[self.pet_id_input.text()]}"
                ):
                    self.pet_list_display.takeItem(x)
                    del self.pet_list[self.pet_id_input.text()]
                    return

    def erase_pet_data(self):
        self.pet_list_display.clear()
        self.pet_list = {}

    def import_pet_data(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.pet_list_display.clear()

        try:
            with open(pathname) as file:
                self.pet_list.update(json.load(file))
            for key, value in self.pet_list.items():
                if not (1 <= int(key) <= 10000):
                    raise ValueError(
                        f"Invalid pet ID {key}.\nIDs must be integers between 1-500,000."
                    )
                if not (1 <= int(value) <= 10000000):
                    raise ValueError(
                        f"Invalid price {value} for pet ID {key}.\nPrices must be integers between 1-10,000,000."
                    )
                self.pet_list_display.insertItem(
                    self.pet_list_display.count(), f"Pet ID: {key}, Price: {value}"
                )
        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Invalid JSON", "Please provide a valid JSON file!"
            )
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def import_configs(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return
        self.check_config_file(pathname)

    def reset_app_data(self):
        self.ilvl_list_display.clear()
        self.pet_list_display.clear()
        self.item_list_display.clear()

        self.discord_webhook_input.setText(""),
        self.wow_client_id_input.setText(""),
        self.wow_client_secret_input.setText(""),
        self.authentication_token.setText(""),
        self.show_bid_prices.setChecked(False),
        self.number_of_mega_threads.setText("48"),
        self.wow_head_link.setChecked(False),
        self.no_links.setChecked(False),
        self.discount_percent.setText("10"),
        self.russian_realms.setChecked(True),
        self.refresh_alerts.setChecked(True),
        self.scan_time_min.setText("1"),
        self.scan_time_max.setText("3"),
        self.debug_mode.setChecked(False)

        self.pet_list = {}
        self.items_list = {}
        self.ilvl_list = []

        self.save_data_to_json()

    def validate_application_settings(self):
        wow_region = self.wow_region.currentText()

        # Check if WOW_REGION is either 'NA', 'EU', 'NACLASSIC', 'EUCLASSIC', 'NASODCLASSIC'
        if wow_region not in [
            "NA",
            "EU",
            "NACLASSIC",
            "EUCLASSIC",
            "NASODCLASSIC",
            "EUSODCLASSIC",
        ]:
            QMessageBox.critical(
                self,
                "Invalid Region",
                "WOW region must be either 'NA', 'EU', 'NACLASSIC', 'EUCLASSIC', 'EUSODCLASSIC or 'NASODCLASSIC'.",
            )
            return False

        required_fields = {
            "MEGA_WEBHOOK_URL": self.discord_webhook_input.text().strip(),
            "WOW_CLIENT_ID": self.wow_client_id_input.text().strip(),
            "WOW_CLIENT_SECRET": self.wow_client_secret_input.text().strip(),
        }

        for field, value in required_fields.items():
            if not value:
                QMessageBox.critical(self, "Empty Field", f"{field} cannot be empty.")
                return False
            if len(value) < 20:
                QMessageBox.critical(
                    self,
                    "Required Field Error",
                    f"{field} value {value} is invalid. "
                    + "Contact the devs on discord.",
                )
                return False

        mega_threads = self.number_of_mega_threads.text()
        scan_time_max = self.scan_time_max.text()
        scan_time_min = self.scan_time_min.text()
        discount_percent = self.discount_percent.text()
        faction = self.faction.currentText()

        # Check if MEGA_THREADS, SCAN_TIME_MAX, and SCAN_TIME_MIN are integers
        integer_fields = {
            "MEGA_THREADS": mega_threads,
            "SCAN_TIME_MAX": scan_time_max,
            "SCAN_TIME_MIN": scan_time_min,
            "DISCOUNT_PERCENT": discount_percent,
        }

        for field, value in integer_fields.items():
            try:
                int(value)
            except ValueError:
                QMessageBox.critical(
                    self, "Invalid Value", f"{field} should be an integer."
                )
                return False

        show_bids = self.show_bid_prices.isChecked()
        wowhead = self.wow_head_link.isChecked()
        no_links = self.no_links.isChecked()
        no_russians = self.russian_realms.isChecked()
        refresh_alerts = self.refresh_alerts.isChecked()
        debug = self.debug_mode.isChecked()

        boolean_fields = {
            "SHOW_BID_PRICES": show_bids,
            "WOWHEAD_LINK": wowhead,
            "NO_LINKS": no_links,
            "NO_RUSSIAN_REALMS": no_russians,
            "REFRESH_ALERTS": refresh_alerts,
            "DEBUG": debug,
        }

        # Ensure all boolean fields have a boolean value.
        for field, value in boolean_fields.items():
            if type(value) != bool:
                QMessageBox.critical(
                    self, "Invalid Value", f"{field} should be a boolean."
                )
                return False

        # If all tests pass, save data to JSON.
        config_json = {
            "MEGA_WEBHOOK_URL": required_fields["MEGA_WEBHOOK_URL"],
            "WOW_CLIENT_ID": required_fields["WOW_CLIENT_ID"],
            "WOW_CLIENT_SECRET": required_fields["WOW_CLIENT_SECRET"],
            "AUTHENTICATION_TOKEN": self.authentication_token.text().strip(),
            "WOW_REGION": wow_region,
            "SHOW_BID_PRICES": show_bids,
            "MEGA_THREADS": int(mega_threads),
            "WOWHEAD_LINK": wowhead,
            "NO_LINKS": no_links,
            "DISCOUNT_PERCENT": int(self.discount_percent.text()),
            "NO_RUSSIAN_REALMS": no_russians,
            "REFRESH_ALERTS": refresh_alerts,
            "SCAN_TIME_MAX": int(scan_time_max),
            "SCAN_TIME_MIN": int(scan_time_min),
            "DEBUG": debug,
            "FACTION": faction,
        }
        return config_json

    def validate_item_lists(self):
        # Check if items_list and pet_list are not empty
        if (
            len(self.items_list) == 0
            and len(self.pet_list) == 0
            and len(self.ilvl_list) == 0
        ):
            QMessageBox.critical(
                self,
                "Empty Lists",
                "Please add items, pets or ilvl data to the lists. All appear to be empty.",
            )
            return False

        # Check if all item IDs are valid integers
        if not all(1 <= int(key) <= 500000 for key in self.items_list.keys()):
            QMessageBox.critical(
                self,
                "Invalid Item ID",
                "All item IDs should be integers between 1 and 500000.",
            )
            return False

        # Check if all pet IDs are valid integers
        if not all(1 <= int(key) <= 10000 for key in self.pet_list.keys()):
            QMessageBox.critical(
                self,
                "Invalid Pet ID",
                "All pet IDs should be integers between 1 and 10000.",
            )
            return False

        # Check if all ilvl data is valid
        for ilvl_dict_data in self.ilvl_list:
            if not (ilvl_dict_data["ilvl"] <= 1000):
                QMessageBox.critical(
                    self,
                    "Invalid ILvl",
                    "All ilvl values should be integers below 1000.",
                )
                return False

            if not all(
                1 <= item_id <= 500000 for item_id in ilvl_dict_data["item_ids"]
            ):
                QMessageBox.critical(
                    self,
                    "Invalid Item ID",
                    "All item IDs should be integers between 1 and 500,000.",
                )
                return False

        return True

    def save_data_to_json(self):
        # Validate application settings
        config_json = self.validate_application_settings()
        if not config_json:
            return False

        # validate pet or item and ilvl data
        if not self.validate_item_lists():
            return False

        # Save JSON files
        self.save_json_file(self.path_to_data, config_json)
        self.save_json_file(self.path_to_desired_pets, self.pet_list)
        self.save_json_file(self.path_to_desired_items, self.items_list)
        self.save_json_file(self.path_to_desired_ilvl_list, self.ilvl_list)
        self.save_json_file(self.path_to_desired_ilvl_items, self.ilvl_items)

        # Save Backups
        time_int = (
            datetime.now().year * 10**6
            + datetime.now().month * 10**4
            + datetime.now().day * 10**2
            + datetime.now().hour
        )
        path_to_backup_mega_data = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "backup",
            f"{time_int}_mega_data.json",
        )
        path_to_backup_items = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "backup",
            f"{time_int}_desired_items.json",
        )
        path_to_backup_pets = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "backup",
            f"{time_int}_desired_pets.json",
        )
        path_to_backup_ilvl_list = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "backup",
            f"{time_int}_desired_ilvl_list.json",
        )
        self.save_json_file(path_to_backup_mega_data, config_json)
        self.save_json_file(path_to_backup_items, self.items_list)
        self.save_json_file(path_to_backup_pets, self.pet_list)
        self.save_json_file(path_to_backup_ilvl_list, self.ilvl_list)

        return True

    def save_json_file(self, path, data):
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

    def start_alerts(self):
        response = requests.post(
            self.token_auth_url,
            json={"token": f"{self.authentication_token.text()}"},
        )

        response_dict = response.json()

        if response.status_code != 200:
            QMessageBox.critical(
                self,
                "Request Error",
                f"Could not reach server, status code : {response.status_code}",
            )
            return

        if len(response_dict) == 0:
            QMessageBox.critical(
                self,
                "Auction Assassin Token",
                "Please provide a valid Auction Assassin token!",
            )
            return

        if "succeeded" not in response_dict:
            QMessageBox.critical(
                self,
                "Auction Assassin Token",
                "Please provide a valid Auction Assassin token!",
            )
            return

        if not response_dict["succeeded"]:
            QMessageBox.critical(
                self,
                "Auction Assassin Token",
                "Your Auction Assassin token is incorrect or expired!\n\n"
                + "You must run the bot command once every 14 days to get a new token.",
            )
            return

        if not self.save_data_to_json():
            QMessageBox.critical(
                self,
                "Save Error",
                "Could not save data to JSON.\nAbort scan.\nYour inputs may be invalid",
            )
            return

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.alerts_thread = Alerts(
            path_to_data_files=self.path_to_data,
            path_to_desired_items=self.path_to_desired_items,
            path_to_desired_pets=self.path_to_desired_pets,
            path_to_desired_ilvl_items=self.path_to_desired_ilvl_items,
            path_to_desired_ilvl_list=self.path_to_desired_ilvl_list,
        )
        self.alerts_thread.start()
        self.alerts_thread.progress.connect(self.alerts_progress_changed)
        self.alerts_thread.finished.connect(self.alerts_thread_finished)

    def stop_alerts(self):
        self.alerts_thread.running = False
        self.stop_button.setText("Stopping Process")
        self.alerts_progress_changed("Stopping alerts!")
        self.stop_button.setEnabled(False)

    def alerts_thread_finished(self):
        self.stop_button.setText("Stop Alerts")
        self.start_button.setEnabled(True)
        self.alerts_progress_changed("Waiting for user to Start!")

    def alerts_progress_changed(self, progress_str):
        self.mega_alerts_progress.setText(progress_str)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file = QFile(":/dark/stylesheet.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    ex = App()
    exit(app.exec_())
