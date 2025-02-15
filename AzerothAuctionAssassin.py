# added the code at the beginning of the file
# to tell the script that is being invoked from the windows c# binary
# so it knows from where to load the pre-installed packages
# so it can locate them before doing the other imports
import sys
from datetime import datetime

AAA_VERSION = "1.4.0"

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
    QInputDialog,
)

if sys.platform == "win32":
    myappid = "mycompany.myproduct.subproduct.version"  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


# Add at the beginning of the file after imports
class StreamToFile:
    def __init__(self, filepath):
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

    def write(self, text):
        self.terminal_out.write(text)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(text)

    def flush(self):
        self.terminal_out.flush()
        self.terminal_err.flush()


class Item_And_Pet_Statistics(QThread):
    completed = pyqtSignal(pd.DataFrame, pd.DataFrame)

    def __init__(self, parent=None):
        super(Item_And_Pet_Statistics, self).__init__(parent)
        self.parent = parent
        self.region = "EU"  # Default to EU

    def set_region(self, region):
        """Update region and refresh statistics"""
        if region in ["NA", "EU"]:
            self.region = region
            self.start()  # Refresh the statistics with new region

    def run(self):
        item_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": self.region, "discount": 1},
            ).json()
        )

        pet_statistics = pd.DataFrame(
            data=requests.post(
                f"http://api.saddlebagexchange.com/api/wow/megaitemnames",
                headers={"Accept": "application/json"},
                json={"region": self.region, "discount": 1, "pets": True},
            ).json()
        )

        self.completed.emit(pet_statistics, item_statistics)


class App(QMainWindow):
    def __init__(self):
        try:
            super(App, self).__init__()
            # Setup logging before anything else
            log_path = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "logs")
            os.makedirs(log_path, exist_ok=True)
            log_file = os.path.join(
                log_path, f"aaa_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            # Create stream handler that captures both stdout and stderr
            self.stream_handler = StreamToFile(log_file)
            print(f"Starting Azeroth Auction Assassin at {datetime.now()}")
            print(f"Log file created at: {log_file}")

            # Install exception hook to catch Qt exceptions
            sys.excepthook = self.handle_exception

            self.title = f"Azeroth Auction Assassin v{AAA_VERSION}"
            self.left = 100
            self.top = 100
            self.width = 650
            self.height = 750
            icon_path = "icon.png"

            # checking if the app is invoked from the windows binary and if yes then change the icon file path.
            if windowsApp_Path is not None:
                icon_path = f"{windowsApp_Path}\\{icon_path}"

            icon = QIcon(icon_path)
            self.setWindowIcon(icon)

            self.token_auth_url = (
                "http://api.saddlebagexchange.com/api/wow/checkmegatoken"
            )

            self.eu_connected_realms = os.path.join(
                os.getcwd(),
                "AzerothAuctionAssassinData",
                "eu-wow-connected-realm-ids.json",
            )
            self.na_connected_realms = os.path.join(
                os.getcwd(),
                "AzerothAuctionAssassinData",
                "na-wow-connected-realm-ids.json",
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
            self.api_data_thread = Item_And_Pet_Statistics(self)
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
            self.path_to_desired_pet_ilvl_list = os.path.join(
                os.getcwd(), "AzerothAuctionAssassinData", "desired_pet_ilvl_list.json"
            )

            self.pet_list = {}
            self.items_list = {}
            self.ilvl_list = []
            self.ilvl_items = {}
            self.pet_ilvl_rules = []

            # Load existing pet level rules if file exists
            if os.path.exists(self.path_to_desired_pet_ilvl_list):
                try:
                    with open(self.path_to_desired_pet_ilvl_list, "r") as f:
                        self.pet_ilvl_rules = json.load(f)
                except Exception as e:
                    print(f"Error loading pet level rules: {e}")

            self.initUI()
        except Exception as e:
            print("=== CRASH REPORT ===")
            print(f"Crash occurred at: {datetime.now()}")
            print(f"Error: {str(e)}")
            import traceback

            print("Full traceback:")
            print(traceback.format_exc())
            print("=== END CRASH REPORT ===")
            raise

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle keyboard interrupt differently
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        print("=== CRASH REPORT ===")
        print(f"Crash occurred at: {datetime.now()}")
        print(f"Error Type: {exc_type.__name__}")
        print(f"Error: {exc_value}")
        print("Full traceback:")
        import traceback

        print("".join(traceback.format_tb(exc_traceback)))
        print("=== END CRASH REPORT ===")

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

        pet_ilvl_page = QWidget()
        self.pet_ilvl_page_layout = QGridLayout(pet_ilvl_page)

        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(pet_page)
        self.stacked_widget.addWidget(item_page)
        self.stacked_widget.addWidget(ilvl_page)
        self.stacked_widget.addWidget(settings_page)
        self.stacked_widget.addWidget(realms_page)
        self.stacked_widget.addWidget(pet_ilvl_page)

        self.layout_area.addWidget(self.stacked_widget, 0, 1, 17, 2)

        self.make_home_page(home_page=home_page)

        self.make_pet_page(pet_page=pet_page)

        self.make_item_page(item_page=item_page)

        self.make_ilvl_page(ilvl_page=ilvl_page)

        self.make_pet_ilvl_page(pet_ilvl_page=pet_ilvl_page)

        self.make_settings_page(settings_page=settings_page)

        self.make_realm_page(realm_page=realms_page)

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

        self.go_to_pet_ilvl_button = QPushButton("Pet Levels")
        self.go_to_pet_ilvl_button.setFixedSize(150, 25)
        self.go_to_pet_ilvl_button.clicked.connect(self.go_to_pet_ilvl_page)
        self.layout_area.addWidget(self.go_to_pet_ilvl_button, 4, 0)

        self.go_to_settings_button = QPushButton("Application Settings")
        self.go_to_settings_button.setFixedSize(150, 25)
        self.go_to_settings_button.clicked.connect(self.go_to_settings_page)
        self.layout_area.addWidget(self.go_to_settings_button, 5, 0)

        self.go_to_realm_button = QPushButton("Realm Lists")
        self.go_to_realm_button.setFixedSize(150, 25)
        self.go_to_realm_button.clicked.connect(self.go_to_realms_page)
        self.layout_area.addWidget(self.go_to_realm_button, 6, 0)

        # add a line to separate the buttons from the rest of the UI
        self.line = QLabel(self)
        self.line.setStyleSheet("background-color: white")
        self.line.setFixedSize(150, 25)

        self.layout_area.addWidget(self.line, 7, 0)

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

        self.start_button = QPushButton("Start Alerts")
        self.start_button.setFixedSize(150, 25)
        self.start_button.clicked.connect(self.start_alerts)
        self.start_button.setToolTip(
            "Start the scan! Runs once on start and then waits for new data to send more alerts."
        )
        self.layout_area.addWidget(self.start_button, 10, 0)

        self.stop_button = QPushButton("Stop Alerts")
        self.stop_button.setFixedSize(150, 25)
        self.stop_button.clicked.connect(self.stop_alerts)
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip(
            "Gracefully stop the alerts.\nThis will not stop alerts in progress.\nYou may need to kill the process for a force stop."
        )
        self.layout_area.addWidget(self.stop_button, 11, 0)

        self.mega_alerts_progress = QLabel("Waiting for user to Start!")
        # this is important, if the messages from mega alerts status are too long, it will break the UI
        self.mega_alerts_progress.setFixedSize(150, 100)
        self.layout_area.addWidget(self.mega_alerts_progress, 12, 0)

    def make_home_page(self, home_page):

        # checking if the app is invoked from the windows binary and if yes then change the icon file path.
        icon_path = "icon.ico"
        if windowsApp_Path is not None:
            icon_path = f"{windowsApp_Path}\\icon.ico"

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
        # Add handler for region changes
        self.wow_region.currentTextChanged.connect(self.on_region_changed)
        self.wow_region_label = QLabel("Auction Assassin Token", settings_page)
        self.wow_region_label.setToolTip(
            "Pick your region, currently supporting: EU, NA, EU-Classic, NA-Classic, EU-SoD-Classic and NA-SoD-Classic."
        )
        self.settings_page_layout.addWidget(self.wow_region_label, 8, 0, 1, 1)
        self.settings_page_layout.addWidget(self.wow_region, 9, 0, 1, 1)

        self.number_of_mega_threads = QLineEdit(settings_page)
        self.number_of_mega_threads.setText("10")
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

    def on_region_changed(self, new_region):
        """Handle region changes and refresh statistics if needed"""
        if new_region in ["NA", "EU"]:
            self.api_data_thread.set_region(new_region)

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
        self.pet_page_layout.addWidget(self.import_pet_data_button, 17, 0, 1, 1)

        # Add new PBS import button for pets
        self.import_pbs_pet_data_button = QPushButton("Import PBS Pet Data")
        self.import_pbs_pet_data_button.setToolTip(
            "Import your Point Blank Sniper pet text files"
        )
        self.import_pbs_pet_data_button.clicked.connect(self.import_pbs_pet_data)
        self.pet_page_layout.addWidget(self.import_pbs_pet_data_button, 17, 1, 1, 1)

        self.erase_pet_data_button = QPushButton("Erase Pet Data")
        self.erase_pet_data_button.setToolTip("Erase your pet list")
        self.erase_pet_data_button.clicked.connect(self.erase_pet_data)
        self.pet_page_layout.addWidget(self.erase_pet_data_button, 18, 0, 1, 1)

        # Add convert to PBS button for pets
        self.convert_pets_to_pbs_button = QPushButton("Convert AAA to PBS")
        self.convert_pets_to_pbs_button.setToolTip(
            "Convert your AAA pet list to PBS format."
        )
        self.convert_pets_to_pbs_button.clicked.connect(self.convert_pets_to_pbs)
        self.pet_page_layout.addWidget(self.convert_pets_to_pbs_button, 18, 1, 1, 1)

    def make_item_page(self, item_page):

        self.item_id_input = QLineEdit(item_page)
        self.item_id_input_label = QLabel("Item ID", item_page)
        self.item_id_input_label.setToolTip(
            "Add the item id of any item you want to buy.\n"
            + "You can search by name for them here with recommended prices\n"
            + "https://temp.saddlebagexchange.com/megaitemnames"
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

        # Add the button to convert AAA JSON to PBS
        self.convert_to_pbs_button = QPushButton("Convert AAA to PBS")
        self.convert_to_pbs_button.setToolTip(
            "Convert your AAA JSON list to PBS format."
        )
        self.convert_to_pbs_button.clicked.connect(self.convert_to_pbs)
        self.item_page_layout.addWidget(self.convert_to_pbs_button, 18, 1, 1, 1)

    def make_ilvl_page(self, ilvl_page):

        self.ilvl_item_input = QLineEdit(ilvl_page)
        self.ilvl_item_input_label = QLabel("Item ID(s)", ilvl_page)
        self.ilvl_item_input_label.setToolTip(
            "Leave blank to snipe all items at this Ilvl.\n"
            + "Add the Item IDs of the BOE you want to snipe specific items separated by a comma\n"
            + "ex: 1,2,99,420420"
        )
        self.ilvl_item_input_label.setFixedSize(120, 15)
        self.ilvl_item_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_item_input_label, 0, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_item_input, 1, 0, 1, 1)

        # Item Level inputs group
        self.ilvl_input = QLineEdit(ilvl_page)
        self.ilvl_input_label = QLabel("Min Item Level", ilvl_page)
        self.ilvl_input_label.setToolTip(
            "Set the minimum item level (ilvl) you want to snipe. Ex: 400 ilvl."
        )
        self.ilvl_input_label.setFixedSize(120, 15)
        self.ilvl_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_input_label, 2, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_input, 3, 0, 1, 1)

        self.ilvl_max_input = QLineEdit(ilvl_page)
        self.ilvl_max_input_label = QLabel("Max Item Level", ilvl_page)
        self.ilvl_max_input.setPlaceholderText("10000")
        self.ilvl_max_input_label.setToolTip(
            "Set the maximum item level (ilvl) you want to snipe. Ex: 500 ilvl."
        )
        self.ilvl_max_input_label.setFixedSize(120, 15)
        self.ilvl_max_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_max_input_label, 4, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_max_input, 5, 0, 1, 1)

        self.ilvl_price_input = QLineEdit(ilvl_page)
        self.ilvl_price_input_label = QLabel("Buyout", ilvl_page)
        self.ilvl_price_input_label.setToolTip(
            "Set the maximum buyout you want to snipe."
        )
        self.ilvl_price_input_label.setFixedSize(120, 15)
        self.ilvl_price_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_price_input_label, 6, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_price_input, 7, 0, 1, 1)

        self.ilvl_sockets = QCheckBox("Sockets", ilvl_page)
        self.ilvl_sockets.setToolTip("Do you want the item to have Sockets?")
        self.ilvl_page_layout.addWidget(self.ilvl_sockets, 8, 0, 1, 1)

        self.ilvl_speed = QCheckBox("Speed", ilvl_page)
        self.ilvl_speed.setToolTip("Do you want the item to have Speed?")
        self.ilvl_page_layout.addWidget(self.ilvl_speed, 9, 0, 1, 1)

        self.ilvl_leech = QCheckBox("Leech", ilvl_page)
        self.ilvl_leech.setToolTip("Do you want the item to have Leech?")
        self.ilvl_page_layout.addWidget(self.ilvl_leech, 10, 0, 1, 1)

        self.ilvl_avoidance = QCheckBox("Avoidance", ilvl_page)
        self.ilvl_avoidance.setToolTip("Do you want the item to have Avoidance?")
        self.ilvl_page_layout.addWidget(self.ilvl_avoidance, 11, 0, 1, 1)

        self.ilvl_min_required_lvl_input = QLineEdit(ilvl_page)
        self.ilvl_min_required_lvl_input_label = QLabel("Min Player Level", ilvl_page)
        self.ilvl_min_required_lvl_input.setPlaceholderText("1")
        self.ilvl_min_required_lvl_input_label.setToolTip(
            "Set the minimum required character level to use gear.\n"
            + "Ex: required level 80 for TWW items, 70 for DF items, etc."
        )
        self.ilvl_min_required_lvl_input_label.setFixedSize(120, 15)
        self.ilvl_min_required_lvl_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(
            self.ilvl_min_required_lvl_input_label, 12, 0, 1, 1
        )
        self.ilvl_page_layout.addWidget(self.ilvl_min_required_lvl_input, 13, 0, 1, 1)

        self.ilvl_max_required_lvl_input = QLineEdit(ilvl_page)
        self.ilvl_max_required_lvl_input_label = QLabel("Max Player Level", ilvl_page)
        self.ilvl_max_required_lvl_input.setPlaceholderText("1000")
        self.ilvl_max_required_lvl_input_label.setToolTip(
            "Set the maximum required character level to use gear.\n"
            + "Ex: required level 70 for TWW twink items, etc."
        )
        self.ilvl_max_required_lvl_input_label.setFixedSize(120, 15)
        self.ilvl_max_required_lvl_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(
            self.ilvl_max_required_lvl_input_label, 14, 0, 1, 1
        )
        self.ilvl_page_layout.addWidget(self.ilvl_max_required_lvl_input, 15, 0, 1, 1)

        self.add_ilvl_button = QPushButton("Add/Update Item", ilvl_page)
        self.add_ilvl_button.setToolTip("Add/Update item to your snipe list.")
        self.add_ilvl_button.clicked.connect(self.add_ilvl_to_list)
        self.ilvl_page_layout.addWidget(self.add_ilvl_button, 11, 1, 1, 1)

        self.remove_ilvl_button = QPushButton("Remove Item", ilvl_page)
        self.remove_ilvl_button.setToolTip("Remove item from your snipe list.")
        self.remove_ilvl_button.clicked.connect(self.remove_ilvl_to_list)
        self.ilvl_page_layout.addWidget(self.remove_ilvl_button, 12, 1, 1, 1)

        self.import_ilvl_data_button = QPushButton("Import ILVL Data")
        self.import_ilvl_data_button.setToolTip(
            "Import your desired_ilvl_list.json config"
        )
        self.import_ilvl_data_button.clicked.connect(self.import_ilvl_data)
        self.ilvl_page_layout.addWidget(self.import_ilvl_data_button, 13, 1, 1, 1)

        self.erase_ilvl_data_button = QPushButton("Erase ILvl Data")
        self.erase_ilvl_data_button.setToolTip(
            "Erase your desired_ilvl_list.json config"
        )
        self.erase_ilvl_data_button.clicked.connect(self.erase_ilvl_data)
        self.ilvl_page_layout.addWidget(self.erase_ilvl_data_button, 14, 1, 1, 1)

        self.ilvl_list_display = QListWidget(ilvl_page)
        self.ilvl_list_display.setSortingEnabled(True)

        self.ilvl_list_display.itemClicked.connect(self.ilvl_list_double_clicked)
        self.ilvl_page_layout.addWidget(self.ilvl_list_display, 0, 1, 11, 2)

        # Add new bonus lists input after the existing ilvl inputs
        self.ilvl_bonus_lists_input = QLineEdit(ilvl_page)
        self.ilvl_bonus_lists_input_label = QLabel("Bonus Lists", ilvl_page)
        self.ilvl_bonus_lists_input_label.setToolTip(
            "Comma-separated list of bonus IDs to match.\n"
            + "Example: 6652,10844\n"
            + "Leave empty to match any bonus lists."
        )
        self.ilvl_bonus_lists_input_label.setFixedSize(120, 15)
        self.ilvl_bonus_lists_input.setFixedSize(120, 25)
        self.ilvl_page_layout.addWidget(self.ilvl_bonus_lists_input_label, 16, 0, 1, 1)
        self.ilvl_page_layout.addWidget(self.ilvl_bonus_lists_input, 17, 0, 1, 1)

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

    def go_to_pet_ilvl_page(self):
        self.stacked_widget.setCurrentIndex(6)

    def api_data_received(self, pet_statistics, item_statistics):
        self.pet_statistics = pet_statistics
        self.item_statistics = item_statistics

        # Populate both pet name dropdowns
        pet_names = self.pet_statistics.sort_values(by="itemName")["itemName"].tolist()

        self.pet_name_input.addItems(pet_names)
        self.pet_name_input.setEditable(True)
        self.pet_name_input.setInsertPolicy(QComboBox.NoInsert)
        self.pet_name_input.completer()
        self.pet_name_input.currentIndexChanged.connect(self.on_combo_box_pet_changed)

        self.pet_ilvl_name_input.addItems(pet_names)
        self.pet_ilvl_name_input.setEnabled(True)

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
            # After loading config, update region and start the thread
            if hasattr(self, "wow_region"):
                selected_region = self.wow_region.currentText()
                if selected_region in ["NA", "EU"]:
                    self.api_data_thread.set_region(selected_region)
            self.api_data_thread.start()

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
            # Load item level list from file
            with open(self.path_to_desired_ilvl_list) as file:
                self.ilvl_list = json.load(file)
            # Process each item level data dictionary
            for ilvl_dict_data in self.ilvl_list:
                # Add missing keys if not present
                if "item_ids" not in ilvl_dict_data:
                    ilvl_dict_data["item_ids"] = []
                if "required_min_lvl" not in ilvl_dict_data:
                    ilvl_dict_data["required_min_lvl"] = 1
                if "required_max_lvl" not in ilvl_dict_data:
                    ilvl_dict_data["required_max_lvl"] = 999
                if "max_ilvl" not in ilvl_dict_data:
                    ilvl_dict_data["max_ilvl"] = 10000
                if "bonus_lists" not in ilvl_dict_data:
                    ilvl_dict_data["bonus_lists"] = []

                # Create a formatted string with the item data
                item_ids = ",".join(map(str, ilvl_dict_data["item_ids"]))
                display_string = (
                    f"Item ID: {item_ids}; "
                    f"Price: {ilvl_dict_data['buyout']}; "
                    f"ILvl: {ilvl_dict_data['ilvl']}; "
                    f"Sockets: {ilvl_dict_data['sockets']}; "
                    f"Speed: {ilvl_dict_data['speed']}; "
                    f"Leech: {ilvl_dict_data['leech']}; "
                    f"Avoidance: {ilvl_dict_data['avoidance']}; "
                    f"MinLevel: {ilvl_dict_data['required_min_lvl']}; "
                    f"MaxLevel: {ilvl_dict_data['required_max_lvl']}; "
                    f"Max ILvl: {ilvl_dict_data['max_ilvl']}; "
                    f"Bonus Lists: {ilvl_dict_data['bonus_lists']}"
                )
                # Insert the string into the display list
                self.ilvl_list_display.insertItem(
                    self.ilvl_list_display.count(), display_string
                )

    def ilvl_list_double_clicked(self, item):
        item_split = item.text().replace(" ", "").split(":")

        item_id = item_split[1].split(";")[0]
        buyout = item_split[2].split(";")[0]
        ilvl = item_split[3].split(";")[0]
        sockets = item_split[4].split(";")[0]
        speed = item_split[5].split(";")[0]
        leech = item_split[6].split(";")[0]
        avoidance = item_split[7].split(";")[0]
        required_min_lvl = item_split[8].split(";")[0]
        required_max_lvl = item_split[9].split(";")[0]
        ilvl_max = item_split[10].split(";")[0]
        bonus_lists = item_split[11].split(";")[
            0
        ]  # Get bonus lists from display string
        self.ilvl_bonus_lists_input.setText(bonus_lists.strip("[]").replace(" ", ""))

        self.ilvl_item_input.setText(item_id)
        self.ilvl_price_input.setText(buyout)

        self.ilvl_sockets.setChecked(sockets == "True")
        self.ilvl_speed.setChecked(speed == "True")
        self.ilvl_leech.setChecked(leech == "True")
        self.ilvl_avoidance.setChecked(avoidance == "True")

        self.ilvl_input.setText(ilvl)
        self.ilvl_min_required_lvl_input.setText(required_min_lvl)
        self.ilvl_max_required_lvl_input.setText(required_max_lvl)
        self.ilvl_max_input.setText(ilvl_max)

    def realm_list_clicked(self, item):
        realm_split = item.text().split(":")
        realm_name = realm_split[1].split(";")[0][1::]
        realm_id = realm_split[2].split(";")[0][1::]

        self.realm_name_input.setText(realm_name)

        self.realm_id_input.setText(realm_id)

    def add_ilvl_to_list(self):
        ilvl = self.ilvl_input.text()
        ilvl_max = self.ilvl_max_input.text() or "10000"  # Default to 10000 if empty
        price = self.ilvl_price_input.text()

        if ilvl == "" or price == "":
            QMessageBox.critical(
                self,
                "Incomplete Information",
                "Both ilvl and buyout fields are required.",
            )
            return False

        try:
            ilvl_int = int(ilvl)
            ilvl_max_int = int(ilvl_max)
            price_int = int(price)
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Input",
                "Min Ilvl, Max Ilvl, and price should be numbers.",
            )
            return False

        # Check if ilvl is between 1 and 999
        if not 1 <= ilvl_int <= 999:
            QMessageBox.critical(
                self, "Incorrect Ilvl Value", "Ilvl must be between 1 and 999."
            )
            return False

        # Check if ilvl_max is between ilvl and 10000
        if not ilvl_int <= ilvl_max_int <= 10000:
            QMessageBox.critical(
                self,
                "Incorrect Ilvl Max Value",
                "Max Ilvl must be between Ilvl and a max of 10000.",
            )
            return False

        # Check if Price is between 1 and 10 million
        if not 1 <= price_int <= 10000000:
            QMessageBox.critical(
                self, "Incorrect Price", "Price must be between 1 and 10 million."
            )
            return False

        # Optional ilvl inputs
        item_ids_text = self.ilvl_item_input.text()
        if item_ids_text == "":
            item_ids_list = []
        else:
            # Validate item IDs
            try:
                item_ids_list = list(
                    map(int, item_ids_text.replace(" ", "").split(","))
                )

                # Check all item ids are between 1 and 500000
                if any(not 1 <= item_id <= 500000 for item_id in item_ids_list):
                    QMessageBox.critical(
                        self,
                        "Invalid Item ID",
                        "All item IDs should be between 1 and 500,000.",
                    )
                    return False
            except ValueError:
                QMessageBox.critical(
                    self, "Invalid Input", f"Item IDs should be numbers."
                )
                return False

        required_min_lvl = self.ilvl_min_required_lvl_input.text()
        if required_min_lvl == "":
            required_min_lvl = 1
        else:
            # Validate min level
            try:
                required_min_lvl = int(required_min_lvl)
                if not 1 <= required_min_lvl <= 999:
                    QMessageBox.critical(
                        self,
                        "Invalid Min Level",
                        "Min level must be between 1 and 999.",
                    )
                    return False
            except ValueError:
                QMessageBox.critical(
                    self, "Invalid Input", "Min level should be a number."
                )
                return False

        required_max_lvl = self.ilvl_max_required_lvl_input.text()
        if required_max_lvl == "":
            required_max_lvl = 999
        else:
            # Validate max level
            try:
                required_max_lvl = int(required_max_lvl)
                if not 1 <= required_max_lvl <= 999:
                    QMessageBox.critical(
                        self,
                        "Invalid Max Level",
                        "Max level must be between 1 and 999.",
                    )
                    return False
                elif required_max_lvl < required_min_lvl:
                    QMessageBox.critical(
                        self,
                        "Invalid Level Range",
                        "Max level must be greater than or equal to Min level.",
                    )
                    return False
            except ValueError:
                QMessageBox.critical(
                    self, "Invalid Input", "Max level should be a number."
                )
                return False

        # Parse bonus lists
        bonus_lists = []
        if self.ilvl_bonus_lists_input.text().strip():
            try:
                bonus_lists = [
                    int(x.strip())
                    for x in self.ilvl_bonus_lists_input.text().split(",")
                ]
                # Validate bonus IDs are positive integers
                if not all(x > 0 for x in bonus_lists):
                    raise ValueError("Bonus list IDs must be positive integers")
            except ValueError:
                QMessageBox.critical(
                    self,
                    "Invalid Input",
                    "Bonus lists must be comma-separated integers",
                )
                return False

        # Create a dictionary with the data, including ilvl_max
        ilvl_dict_data = {
            "ilvl": ilvl_int,
            "buyout": price_int,
            "sockets": self.ilvl_sockets.isChecked(),
            "speed": self.ilvl_speed.isChecked(),
            "leech": self.ilvl_leech.isChecked(),
            "avoidance": self.ilvl_avoidance.isChecked(),
            "item_ids": item_ids_list,
            "required_min_lvl": int(required_min_lvl),
            "required_max_lvl": int(required_max_lvl),
            "max_ilvl": ilvl_max_int,
            "bonus_lists": bonus_lists,  # Add the bonus lists field
        }

        # Only append and display if the dictionary is not already in the list
        if ilvl_dict_data not in self.ilvl_list:
            self.ilvl_list.append(ilvl_dict_data)

            # Format the display string
            item_ids = ",".join(map(str, ilvl_dict_data["item_ids"]))
            display_string = (
                f"Item ID: {item_ids}; "
                f"Price: {ilvl_dict_data['buyout']}; "
                f"ILvl: {ilvl_dict_data['ilvl']}; "
                f"Sockets: {ilvl_dict_data['sockets']}; "
                f"Speed: {ilvl_dict_data['speed']}; "
                f"Leech: {ilvl_dict_data['leech']}; "
                f"Avoidance: {ilvl_dict_data['avoidance']}; "
                f"MinLevel: {ilvl_dict_data['required_min_lvl']}; "
                f"MaxLevel: {ilvl_dict_data['required_max_lvl']}; "
                f"Max ILvl: {ilvl_dict_data['max_ilvl']}; "
                f"Bonus Lists: {ilvl_dict_data['bonus_lists']}"
            )

            # Insert the formatted string into the display list
            self.ilvl_list_display.insertItem(
                self.ilvl_list_display.count(), display_string
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

        if self.ilvl_min_required_lvl_input.text() == "":
            required_min_lvl = 1
        else:
            required_min_lvl = int(self.ilvl_min_required_lvl_input.text())

        if self.ilvl_max_required_lvl_input.text() == "":
            required_max_lvl = 999
        else:
            required_max_lvl = int(self.ilvl_max_required_lvl_input.text())

        if self.ilvl_max_input.text() == "":
            ilvl_max = 10000
        else:
            ilvl_max = int(self.ilvl_max_input.text())

        # Parse bonus lists
        bonus_lists = []
        if self.ilvl_bonus_lists_input.text().strip():
            bonus_lists = [
                int(x.strip()) for x in self.ilvl_bonus_lists_input.text().split(",")
            ]

        # Create a dictionary with the data
        ilvl_dict_data = {
            "ilvl": int(self.ilvl_input.text()),
            "buyout": int(self.ilvl_price_input.text()),
            "sockets": self.ilvl_sockets.isChecked(),
            "speed": self.ilvl_speed.isChecked(),
            "leech": self.ilvl_leech.isChecked(),
            "avoidance": self.ilvl_avoidance.isChecked(),
            "item_ids": item_ids_list,
            "required_min_lvl": required_min_lvl,
            "required_max_lvl": required_max_lvl,
            "max_ilvl": ilvl_max,
            "bonus_lists": bonus_lists,
        }

        # Check if the item data is already in the list
        if ilvl_dict_data in self.ilvl_list:
            # Create the display string
            item_ids = ",".join(map(str, ilvl_dict_data["item_ids"]))
            string_with_data = (
                f"Item ID: {item_ids}; "
                f"Price: {ilvl_dict_data['buyout']}; "
                f"ILvl: {ilvl_dict_data['ilvl']}; "
                f"Sockets: {ilvl_dict_data['sockets']}; "
                f"Speed: {ilvl_dict_data['speed']}; "
                f"Leech: {ilvl_dict_data['leech']}; "
                f"Avoidance: {ilvl_dict_data['avoidance']}; "
                f"MinLevel: {ilvl_dict_data['required_min_lvl']}; "
                f"MaxLevel: {ilvl_dict_data['required_max_lvl']}; "
                f"Max ILvl: {ilvl_dict_data['max_ilvl']}; "
                f"Bonus Lists: {ilvl_dict_data['bonus_lists']}"
            )

            # Print the formatted string
            print(f"Removing | {string_with_data}")

            # Remove the item from the list and display if it exists
            for x in range(self.ilvl_list_display.count()):
                if self.ilvl_list_display.item(x).text() == string_with_data:
                    self.ilvl_list_display.takeItem(x)
                    self.ilvl_list.remove(ilvl_dict_data)
                    return

    def erase_ilvl_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.ilvl_list_display.clear()
            self.ilvl_list = []

    def import_ilvl_data(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        try:
            with open(pathname) as file:
                self.ilvl_list += json.load(file)
            if not isinstance(self.ilvl_list, list):
                raise ValueError(
                    "Invalid JSON file.\nFile should contain a list of Desired Ilvl Objects."
                )
            # clear display before inserting new data
            self.ilvl_list_display.clear()
            for ilvl_dict_data in self.ilvl_list:
                item_ids = ilvl_dict_data.get("item_ids", [])
                buyout_price = ilvl_dict_data["buyout"]
                ilvl = ilvl_dict_data["ilvl"]
                sockets = ilvl_dict_data["sockets"]
                speed = ilvl_dict_data["speed"]
                leech = ilvl_dict_data["leech"]
                avoidance = ilvl_dict_data["avoidance"]
                required_min_lvl = ilvl_dict_data.get("required_min_lvl", 1)
                required_max_lvl = ilvl_dict_data.get("required_max_lvl", 999)
                ilvl_max = ilvl_dict_data.get("max_ilvl", 10000)

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
                if not (200 <= ilvl_max <= 10000):
                    raise ValueError(
                        f"Invalid Max ILvl {ilvl_max}.\nMax ILvl must be an integer between 200-10000."
                    )
                if not ilvl_max >= ilvl:
                    raise ValueError(
                        f"Max ILvl {ilvl_max} must be greater than ILvl {ilvl}."
                    )

                # Check that min and max levels are integers within range
                if not (1 <= required_min_lvl <= 999):
                    raise ValueError(
                        f"Invalid Min Level {required_min_lvl}.\nMin level must be between 1-999."
                    )
                if not (1 <= required_max_lvl <= 999):
                    raise ValueError(
                        f"Invalid Max Level {required_max_lvl}.\nMax level must be between 1-999."
                    )
                if required_max_lvl < required_min_lvl:
                    raise ValueError(
                        f"Max level {required_max_lvl} must be greater than or equal to Min level {required_min_lvl}."
                    )

                # Check that sockets, speed, leech and avoidance are booleans
                if not all(
                    isinstance(val, bool) for val in [sockets, speed, leech, avoidance]
                ):
                    raise ValueError(
                        "Sockets, speed, leech, and avoidance should be boolean values."
                    )

                string_with_data = (
                    f"Item ID: {','.join(map(str, item_ids))}; "
                    f"Price: {buyout_price}; "
                    f"ILvl: {ilvl}; "
                    f"Sockets: {sockets}; "
                    f"Speed: {speed}; "
                    f"Leech: {leech}; "
                    f"Avoidance: {avoidance}; "
                    f"MinLevel: {required_min_lvl}; "
                    f"MaxLevel: {required_max_lvl}; "
                    f"Max ILvl: {ilvl_max}"
                )
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
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.item_list_display.clear()
            self.items_list = {}

    def process_import_data(self, data_source, is_file=False, data_type="item"):
        try:
            # Load the JSON data from the appropriate source
            if is_file:
                with open(data_source, "r") as file:
                    data = json.load(file)
            else:
                data = json.loads(data_source)

            # Determine the target list and display based on data type
            if data_type == "item":
                target_list = self.items_list
                display_widget = self.item_list_display
                id_range = (1, 500000)
                price_range = (0, 10000000)
            elif data_type == "pet":
                target_list = self.pet_list
                display_widget = self.pet_list_display
                id_range = (1, 10000)
                price_range = (1, 10000000)
            else:
                raise ValueError("Invalid data type specified.")

            # Clear the display and update the target list
            display_widget.clear()
            target_list.update(data)

            # Validate and display each entry
            for entry_id, price in target_list.items():
                if not (id_range[0] <= int(entry_id) <= id_range[1]):
                    raise ValueError(
                        f"Invalid {data_type} ID {entry_id}.\nIDs must be integers between {id_range[0]}-{id_range[1]}."
                    )
                if not (price_range[0] <= float(price) <= price_range[1]):
                    raise ValueError(
                        f"Invalid price {price} for {data_type} ID {entry_id}.\nPrices must be integers between {price_range[0]}-{price_range[1]}."
                    )
                display_widget.insertItem(
                    display_widget.count(),
                    f"{data_type.capitalize()} ID: {entry_id}, Price: {price}",
                )

        except json.JSONDecodeError:
            QMessageBox.critical(
                self,
                "Invalid JSON",
                f"Please provide a valid JSON string or file for {data_type} data!",
            )
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def import_item_data(self):
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Import AAA-Transformer Data",
            "Paste your Item Data from AAA-Transformer here:",
        )
        if not ok or not text.strip():
            return

        self.process_import_data(text, data_type="item")

    # an option if we want to switch to a file import instead of a text import
    def import_item_data_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import AAA-Transformer Data from File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        self.process_import_data(file_path, is_file=True, data_type="item")

    def import_pbs_data(self):
        # Open a dialog to allow users to paste the PBS data
        """
        Import PBS (Price Breakdown Sheet) data into the application's item tracking system.

        This method allows users to paste PBS data, which contains item names and their corresponding prices. It processes the pasted data, matches item names with the application's item statistics, and updates the item list with prices.

        Parameters:
            None (uses self context)

        Behavior:
            - Opens a multi-line input dialog for users to paste PBS data
            - Parses the pasted data, extracting item names and prices
            - Matches item names with existing item statistics
            - Updates item list with PBS prices or calculates discounted prices
            - Populates the item list display with matched items and their prices

        Raises:
            ValueError: If invalid numeric values are encountered during price parsing
            Exception: For any unexpected errors during data processing

        Notes:
            - Handles items with or without quotes in their names
            - Supports fallback to discounted default prices if PBS price is not available
            - Converts item names to lowercase for case-insensitive matching
        """
        text, ok = QInputDialog.getMultiLineText(
            self, "Import PBS Data", "Paste your PBS data here:"
        )
        if not ok or not text.strip():
            return

        self.item_list_display.clear()

        try:
            # Process the pasted PBS data
            pbs_data = text.replace("\n", "").replace("\r", "").split("^")

            # Create a dictionary to map item names to prices from the PBS data
            pbs_prices = {}
            for item in pbs_data:
                # parts will be like ['Skullflame shield', '0;0;0;0;0;50000', '#', '']
                parts = item.split(";;")
                item_name = parts[0].strip().lower()
                # strip off " if the name begins and ends with "
                if item_name[0] == '"' and item_name[-1] == '"':
                    item_name = item_name[1:-1]
                if len(parts) > 1:
                    price_parts = parts[1].split(";")
                    item_price = (
                        float(price_parts[-1])
                        if self.isfloat(price_parts[-1])
                        else None
                    )
                    pbs_prices[item_name] = item_price
                else:
                    pbs_prices[item_name] = None

            temp_items_list = {}
            pbs_item_names = list(pbs_prices.keys())
            for _index, item in self.item_statistics.iterrows():
                item_name_lower = item["itemName"].lower()
                if item_name_lower in pbs_item_names:
                    price = pbs_prices[item_name_lower]
                    if price is not None:
                        temp_items_list[str(item["itemID"])] = pbs_prices[
                            item_name_lower
                        ]
                    else:
                        # Use default behavior if price is not set in PBS
                        default_price = item["desiredPrice"]
                        discount_percent = int(self.discount_percent.text()) / 100
                        discount_price = round(
                            float(default_price) * discount_percent, 4
                        )
                        temp_items_list[str(item["itemID"])] = discount_price

            for key, value in temp_items_list.items():
                self.item_list_display.insertItem(
                    self.item_list_display.count(),
                    f"Item ID: {key}, Price: {value}",
                )
                self.items_list[str(key)] = value

        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def convert_to_pbs(self):
        try:
            # Assuming `self.items_list` is the AAA JSON list of items and prices
            pbs_string = self.convert_aaa_json_to_pbs(self.items_list)

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(pbs_string)

            QMessageBox.information(
                self, "Success", "Converted PBS string copied to clipboard."
            )
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", str(e))

    def convert_aaa_json_to_pbs(self, json_data):
        # Prepare the PBS list
        pbs_list = []

        for item_id, price in json_data.items():
            # Find the item name by matching the itemID in item_statistics
            item_name = self.item_statistics.loc[
                self.item_statistics["itemID"] == int(item_id), "itemName"
            ]

            # not sure what up but sometimes we dont find a name i guess
            if item_name.empty:
                continue
            item_name = item_name.iloc[0]

            # Construct the PBS entry
            pbs_entry = f"Snipe^{item_name};;0;0;0;0;0;0;0;{int(float(price))};;#;;"

            # Append the PBS entry to the list
            pbs_list.append(pbs_entry)

        # Join the PBS entries into a single string
        pbs_string = "".join(pbs_list)

        return pbs_string

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
            pet_price_int = float(pet_price)
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
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pet_list_display.clear()
            self.pet_list = {}

    def import_pet_data(self):
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Import AAA-Transformer Data",
            "Paste your Pet Data from AAA-Transformer here:",
        )
        if not ok or not text.strip():
            return
        self.process_import_data(text, data_type="pet")

    # an option if we want to switch to a file import instead of a text import
    def import_pet_data_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import AAA-Transformer Pet Data from File",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        self.process_import_data(file_path, is_file=True, data_type="pet")

    def import_configs(self):
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return
        self.check_config_file(pathname)

    def reset_app_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.ilvl_list_display.clear()
            self.pet_list_display.clear()
            self.item_list_display.clear()

            self.discord_webhook_input.setText(""),
            self.wow_client_id_input.setText(""),
            self.wow_client_secret_input.setText(""),
            self.authentication_token.setText(""),
            self.show_bid_prices.setChecked(False),
            self.number_of_mega_threads.setText("10"),
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

        # confirm the client id and secret are not the same value
        if required_fields["WOW_CLIENT_ID"] == required_fields["WOW_CLIENT_SECRET"]:
            QMessageBox.critical(
                self,
                "Invalid Client ID and Secret",
                "Client ID and Secret cannot be the same value. Read the wiki:\n\n"
                + "https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Installation-Guide#4-go-to-httpsdevelopbattlenetaccessclients-and-create-a-client-get-the-blizzard-oauth-client-and-secret-ids--you-will-use-these-values-for-the-wow_client_id-and-wow_client_secret-later-on",
            )
            return False

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
        # Check if items_list, pet_list, ilvl_list, or pet_ilvl_rules are not empty
        if (
            len(self.items_list) == 0
            and len(self.pet_list) == 0
            and len(self.ilvl_list) == 0
            and len(self.pet_ilvl_rules) == 0  # Add check for pet level rules
        ):
            QMessageBox.critical(
                self,
                "Empty Lists",
                "Please add items, pets, ilvl data, or pet level rules to the lists. All appear to be empty.",
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

        # Add validation for pet level rules
        for rule in self.pet_ilvl_rules:
            if not (1 <= rule["petID"] <= 10000):
                QMessageBox.critical(
                    self,
                    "Invalid Pet ID",
                    "All pet IDs in level rules should be between 1 and 10000.",
                )
                return False
            if not (1 <= rule["minLevel"] <= 25):
                QMessageBox.critical(
                    self,
                    "Invalid Pet Level",
                    "All pet minimum levels should be between 1 and 25.",
                )
                return False
            if not (-1 <= rule["minQuality"] <= 3):
                QMessageBox.critical(
                    self,
                    "Invalid Pet Quality",
                    "All pet minimum qualities should be between -1 and 3.",
                )
                return False

        return True

    def save_data_to_json(self):
        # Validate application settings
        """
        Save application data and configuration to JSON files with backup mechanism.

        This method performs the following key actions:
        - Validates application settings and item lists
        - Saves configuration and user-defined lists to primary JSON files
        - Creates timestamped backup files for data preservation

        Parameters:
            None

        Returns:
            bool: True if data saving is successful, False if validation fails

        Raises:
            No explicit exceptions, but may raise file I/O related errors during JSON saving

        Side Effects:
            - Writes JSON files to predefined paths
            - Creates backup files with timestamp in filename
            - Modifies filesystem by creating new JSON files

        Notes:
            - Saves configuration, desired pets, items, item levels, and pet item levels
            - Backup files are created in 'AzerothAuctionAssassinData/backup' directory
            - Backup filename includes timestamp for unique identification
        """
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
        self.save_json_file(self.path_to_desired_pet_ilvl_list, self.pet_ilvl_rules)

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
        path_to_backup_pet_ilvl_list = os.path.join(
            os.getcwd(),
            "AzerothAuctionAssassinData",
            "backup",
            f"{time_int}_desired_pet_ilvl_list.json",
        )
        self.save_json_file(path_to_backup_mega_data, config_json)
        self.save_json_file(path_to_backup_items, self.items_list)
        self.save_json_file(path_to_backup_pets, self.pet_list)
        self.save_json_file(path_to_backup_ilvl_list, self.ilvl_list)
        self.save_json_file(path_to_backup_pet_ilvl_list, self.pet_ilvl_rules)

        return True

    def save_json_file(self, path, data):
        """
        Save data to a JSON file with UTF-8 encoding and formatted indentation.

        Parameters:
            path (str): The file path where the JSON file will be saved
            data (dict or list): The data to be serialized and saved to the JSON file

        Raises:
            IOError: If the file cannot be written due to permission or path issues
            TypeError: If the data cannot be JSON serialized
        """
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

    # Add after the make_ilvl_page method
    def make_pet_ilvl_page(self, pet_ilvl_page):
        # Pet ID input
        """
        Configures the pet item level (ilvl) page in the Azeroth Auction Assassin application.

        This method sets up a comprehensive UI for managing pet sniping rules, including:
        - Input fields for pet ID, max price, name, minimum level, and minimum quality
        - Dropdown for pet name selection
        - Input for excluded breed IDs
        - Buttons for adding, removing, importing, and exporting pet level rules
        - A list widget to display current pet level rules

        The page allows users to:
        - Define specific criteria for pet auction sniping
        - Add and manage multiple pet level rules
        - Import rules from different sources (including Point Blank Sniper)
        - Convert rules between different formats

        Parameters:
            pet_ilvl_page (QWidget): The parent widget for the pet item level page

        Side Effects:
            - Creates and configures multiple QLineEdit, QLabel, QComboBox, QPushButton, and QListWidget
            - Populates the pet level rules list display
            - Connects various UI elements to corresponding event handlers
        """
        self.pet_ilvl_id_input = QLineEdit(pet_ilvl_page)
        self.pet_ilvl_id_input_label = QLabel("Pet ID", pet_ilvl_page)
        self.pet_ilvl_id_input_label.setToolTip("Enter the Pet ID you want to snipe")
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_id_input_label, 0, 0, 1, 1)
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_id_input, 1, 0, 1, 1)

        # Price input
        self.pet_ilvl_price_input = QLineEdit(pet_ilvl_page)
        self.pet_ilvl_price_input_label = QLabel("Max Price", pet_ilvl_page)
        self.pet_ilvl_price_input_label.setToolTip(
            "Maximum price you're willing to pay"
        )
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_price_input_label, 0, 1, 1, 1)
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_price_input, 1, 1, 1, 1)

        # Pet name dropdown (populated from pet_statistics)
        self.pet_ilvl_name_input = QComboBox(pet_ilvl_page)
        self.pet_ilvl_name_input.setEnabled(False)
        self.pet_ilvl_name_input.setEditable(True)
        self.pet_ilvl_name_input.setInsertPolicy(QComboBox.NoInsert)
        self.pet_ilvl_name_input.completer()
        self.pet_ilvl_name_input.currentIndexChanged.connect(
            self.on_combo_box_pet_ilvl_changed
        )
        self.pet_ilvl_name_input.setStyleSheet(
            "QComboBox { background-color: #1D2023; color: white; }"
            "QComboBox::editable { background: #1D2023; color: white; }"
            "QComboBox::drop-down { border: 0px; }"
        )
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_name_input, 2, 0, 1, 2)

        # Min Level input
        self.pet_ilvl_min_level_input = QLineEdit(pet_ilvl_page)
        self.pet_ilvl_min_level_input.setText("1")
        self.pet_ilvl_min_level_input_label = QLabel("Minimum Level", pet_ilvl_page)
        self.pet_ilvl_min_level_input_label.setToolTip("Minimum pet level (1-25)")
        self.pet_ilvl_page_layout.addWidget(
            self.pet_ilvl_min_level_input_label, 3, 0, 1, 1
        )
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_min_level_input, 4, 0, 1, 1)

        # Min Quality input
        self.pet_ilvl_min_quality_input = QLineEdit(pet_ilvl_page)
        self.pet_ilvl_min_quality_input.setText("-1")
        self.pet_ilvl_min_quality_input_label = QLabel(
            "Minimum Quality (-1 to 3)", pet_ilvl_page
        )
        self.pet_ilvl_min_quality_input_label.setToolTip(
            "Minimum pet quality (-1 for any, 0-3 for Poor to Rare)"
        )
        self.pet_ilvl_page_layout.addWidget(
            self.pet_ilvl_min_quality_input_label, 3, 1, 1, 1
        )
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_min_quality_input, 4, 1, 1, 1)

        # Excluded Breeds input
        self.pet_ilvl_breeds_input = QLineEdit(pet_ilvl_page)
        self.pet_ilvl_breeds_input_label = QLabel("Excluded Breeds", pet_ilvl_page)
        self.pet_ilvl_breeds_input_label.setToolTip(
            "Comma-separated list of breed IDs to exclude.\n"
            + "[Breed IDs can be found on warcraftpets.com](https://www.warcraftpets.com/wow-pet-battles/breeds/)\n"
            + "For the best pets exclude: 7, 17, 8, 18, 9, 19, 10, 20, 3, 13, 11, 21, 2, 22"
        )
        self.pet_ilvl_page_layout.addWidget(
            self.pet_ilvl_breeds_input_label, 5, 0, 1, 2
        )
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_breeds_input, 6, 0, 1, 2)

        # Add/Update and Remove buttons
        self.add_pet_ilvl_button = QPushButton("Add/Update Pet Level Rule")
        self.add_pet_ilvl_button.clicked.connect(self.add_pet_ilvl_to_list)
        self.pet_ilvl_page_layout.addWidget(self.add_pet_ilvl_button, 7, 0, 1, 1)

        self.remove_pet_ilvl_button = QPushButton("Remove Pet Level Rule")
        self.remove_pet_ilvl_button.clicked.connect(self.remove_pet_ilvl_from_list)
        self.pet_ilvl_page_layout.addWidget(self.remove_pet_ilvl_button, 7, 1, 1, 1)

        # List display
        self.pet_ilvl_list_display = QListWidget(pet_ilvl_page)
        self.pet_ilvl_list_display.setSortingEnabled(True)
        self.pet_ilvl_list_display.itemClicked.connect(self.pet_ilvl_list_clicked)
        self.pet_ilvl_page_layout.addWidget(self.pet_ilvl_list_display, 8, 0, 8, 2)

        # Import/Export buttons
        self.import_pet_ilvl_button = QPushButton("Import Pet Level Rules")
        self.import_pet_ilvl_button.clicked.connect(self.import_pet_ilvl_data)
        self.pet_ilvl_page_layout.addWidget(self.import_pet_ilvl_button, 16, 0, 1, 1)

        self.erase_pet_ilvl_button = QPushButton("Erase Pet Level Rules")
        self.erase_pet_ilvl_button.clicked.connect(self.erase_pet_ilvl_data)
        self.pet_ilvl_page_layout.addWidget(self.erase_pet_ilvl_button, 17, 0, 1, 1)

        # Load existing rules into display
        for rule in self.pet_ilvl_rules:
            display_string = (
                f"Pet ID: {rule['petID']}; "
                f"Price: {rule['price']}; "
                f"Min Level: {rule['minLevel']}; "
                f"Min Quality: {rule['minQuality']}; "
                f"Excluded Breeds: {rule['excludeBreeds']}"
            )
            self.pet_ilvl_list_display.addItem(display_string)

        # Add after the existing import/export buttons in make_pet_ilvl_page method
        self.import_pbs_pet_ilvl_button = QPushButton("Import PBS Pet Data")
        self.import_pbs_pet_ilvl_button.setToolTip(
            "Import your Point Blank Sniper pet text files"
        )
        self.import_pbs_pet_ilvl_button.clicked.connect(self.import_pbs_pet_ilvl_data)
        self.pet_ilvl_page_layout.addWidget(
            self.import_pbs_pet_ilvl_button, 16, 1, 1, 1
        )

        self.convert_pet_ilvl_to_pbs_button = QPushButton("Convert AAA to PBS")
        self.convert_pet_ilvl_to_pbs_button.setToolTip(
            "Convert your AAA pet level rules to PBS format"
        )
        self.convert_pet_ilvl_to_pbs_button.clicked.connect(
            self.convert_pet_ilvl_to_pbs
        )
        self.pet_ilvl_page_layout.addWidget(
            self.convert_pet_ilvl_to_pbs_button, 17, 1, 1, 1
        )

    def add_pet_ilvl_to_list(self):
        """Add or update a pet level rule in the list"""
        try:
            # Get and validate inputs
            if not self.pet_ilvl_min_level_input.text().strip():
                raise ValueError("Please set a pet level (1-25)")

            pet_id = int(self.pet_ilvl_id_input.text())
            # Convert price to float instead of int
            price = float(self.pet_ilvl_price_input.text())
            min_level = int(self.pet_ilvl_min_level_input.text())
            min_quality = int(self.pet_ilvl_min_quality_input.text())

            # Validate excluded breeds
            excluded_breeds = []
            if self.pet_ilvl_breeds_input.text().strip():
                excluded_breeds = [
                    int(x.strip()) for x in self.pet_ilvl_breeds_input.text().split(",")
                ]

            # Validation checks
            if not (1 <= pet_id <= 10000):
                raise ValueError("Pet ID must be between 1 and 10000")
            if price <= 0:
                raise ValueError("Price must be greater than 0")
            if not (1 <= min_level <= 25):
                raise ValueError("Minimum level must be between 1 and 25")
            if not (-1 <= min_quality <= 3):
                raise ValueError("Minimum quality must be between -1 and 3")

            # Create pet level rule dictionary
            pet_rule = {
                "petID": pet_id,
                "price": price,  # Store as float
                "minLevel": min_level,
                "minQuality": min_quality,
                "excludeBreeds": excluded_breeds,
            }

            # Update the rules list
            # Remove existing rule for this pet if it exists
            self.pet_ilvl_rules = [
                rule for rule in self.pet_ilvl_rules if rule["petID"] != pet_id
            ]
            # Add the new rule
            self.pet_ilvl_rules.append(pet_rule)

            # Format display string
            display_string = (
                f"Pet ID: {pet_id}; "
                f"Price: {price}; "
                f"Min Level: {min_level}; "
                f"Min Quality: {min_quality}; "
                f"Excluded Breeds: {excluded_breeds}"
            )

            # Update list display
            for i in range(self.pet_ilvl_list_display.count()):
                item = self.pet_ilvl_list_display.item(i)
                if str(pet_id) in item.text():
                    self.pet_ilvl_list_display.takeItem(i)
                    break

            self.pet_ilvl_list_display.addItem(display_string)

        except ValueError as e:
            QMessageBox.critical(self, "Invalid Input", str(e))
            return False

        return True

    def remove_pet_ilvl_from_list(self):
        """Remove a pet level rule from the list"""
        current_item = self.pet_ilvl_list_display.currentItem()
        if not current_item:
            QMessageBox.critical(
                self, "Selection Error", "Please select a pet level rule to remove"
            )
            return

        # Get the pet ID from the display string
        pet_id = int(current_item.text().split(";")[0].split(":")[1].strip())
        # Remove from rules list
        self.pet_ilvl_rules = [
            rule for rule in self.pet_ilvl_rules if rule["petID"] != pet_id
        ]

        self.pet_ilvl_list_display.takeItem(
            self.pet_ilvl_list_display.row(current_item)
        )

    def pet_ilvl_list_clicked(self, item):
        """Handle clicking on a pet level rule in the list"""
        # Parse the display string
        parts = item.text().split(";")
        pet_id = parts[0].split(":")[1].strip()
        price = parts[1].split(":")[1].strip()
        min_level = parts[2].split(":")[1].strip()
        min_quality = parts[3].split(":")[1].strip()
        excluded_breeds = parts[4].split(":")[1].strip()

        # Update input fields
        self.pet_ilvl_id_input.setText(pet_id)
        self.pet_ilvl_price_input.setText(price)
        self.pet_ilvl_min_level_input.setText(min_level)
        self.pet_ilvl_min_quality_input.setText(min_quality)
        self.pet_ilvl_breeds_input.setText(excluded_breeds.strip("[]"))

        # Update pet name dropdown if possible
        try:
            pet_name = self.pet_statistics[
                self.pet_statistics["itemID"] == int(pet_id)
            ].iloc[0]["itemName"]
            index = self.pet_ilvl_name_input.findText(pet_name)
            self.pet_ilvl_name_input.setCurrentIndex(index)
        except:
            self.pet_ilvl_name_input.setCurrentText("Pet ID not found")

    def import_pet_ilvl_data(self):
        """Import pet level rules from a file"""
        pathname = QFileDialog().getOpenFileName(self)[0]
        if not pathname:
            return

        try:
            with open(pathname) as file:
                data = json.load(file)

            self.pet_ilvl_list_display.clear()
            for rule in data:
                # Validate rule format
                required_keys = {
                    "petID",
                    "price",
                    "minLevel",
                    "minQuality",
                    "excludeBreeds",
                }
                if not all(key in rule for key in required_keys):
                    raise ValueError(f"Invalid rule format: {rule}")

                # Format display string
                display_string = (
                    f"Pet ID: {rule['petID']}; "
                    f"Price: {rule['price']}; "
                    f"Min Level: {rule['minLevel']}; "
                    f"Min Quality: {rule['minQuality']}; "
                    f"Excluded Breeds: {rule['excludeBreeds']}"
                )
                self.pet_ilvl_list_display.addItem(display_string)

        except json.JSONDecodeError:
            QMessageBox.critical(
                self, "Invalid JSON", "Please provide a valid JSON file"
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def erase_pet_ilvl_data(self):
        """Clear all pet level rules"""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all pet level rules? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pet_ilvl_list_display.clear()
            self.pet_ilvl_rules = []

    def on_combo_box_pet_ilvl_changed(self, index):
        # This function will be called whenever the user selects a different pet
        """
        Update the pet item level input fields when a new pet is selected from the dropdown.

        This method is triggered when the user changes the selected pet in the pet item level (ilvl) combo box. It performs the following actions:
        - Retrieves the selected pet's details from the pet statistics DataFrame
        - Populates the pet ID input field with the corresponding item ID
        - Sets a recommended price based on the pet's desired price and a user-defined discount percentage
        - Provides a default price of 10 if no price can be calculated

        Parameters:
            index (int): The index of the selected item in the combo box (unused)

        Side Effects:
            - Updates pet_ilvl_id_input with the selected pet's item ID
            - Updates pet_ilvl_price_input with a recommended or default price
        """
        selected_pet = self.pet_ilvl_name_input.currentText()
        selected_pet_stats = self.pet_statistics[
            self.pet_statistics["itemName"] == selected_pet
        ]
        selected_pet_id = selected_pet_stats["itemID"].iloc[0]

        # Set the pet ID input
        self.pet_ilvl_id_input.setText(str(selected_pet_id))

        # Set a default price if none exists
        if not self.pet_ilvl_price_input.text():
            try:
                selected_pet_price = selected_pet_stats["desiredPrice"].iloc[0]
                discount_percent = int(self.discount_percent.text()) / 100
                recommended_price = str(
                    int(float(selected_pet_price) * discount_percent)
                )
                self.pet_ilvl_price_input.setText(recommended_price)
            except:
                self.pet_ilvl_price_input.setText("10")

    def import_pbs_pet_ilvl_data(self):
        """
        Import PBS pet data and convert to pet level rules.

        This method allows users to paste PBS (Presumably Pet Battle System) pet data and
        automatically generates pet trading rules based on the imported information.

        Parameters:
            None (uses self context)

        Functionality:
            - Opens a multi-line input dialog for users to paste PBS pet data
            - Parses the pasted data to extract pet names and prices
            - Creates pet trading rules with extracted information
            - Handles various data parsing scenarios and edge cases
            - Provides fallback pricing using default discount mechanism
            - Updates the pet level rules list and displays the rules

        Raises:
            QMessageBox warnings/errors for:
            - Invalid data format
            - No valid pets imported
            - Parsing errors

        Returns:
            None (updates internal state and UI components)

        Notes:
            - Supports flexible data parsing with multiple semicolon-separated fields
            - Handles pet names with/without quotes
            - Provides default pricing if no valid price is found
        """
        text, ok = QInputDialog.getMultiLineText(
            self, "Import PBS Pet Data", "Paste your PBS pet data here:"
        )
        if not ok or not text.strip():
            return

        self.pet_ilvl_list_display.clear()
        self.pet_ilvl_rules = []

        try:
            # Process the pasted PBS data
            # (Note: We remove any newlines but DO NOT over-filter the entries)
            pbs_data = text.replace("\n", "").replace("\r", "").split("^")

            # Create a dictionary to map pet names to prices from the PBS data
            pbs_prices = {}
            for pet in pbs_data:
                # Each 'pet' string might look like:  "Battle Pet Name;;0;0;0;0;0;50000" (etc.)
                parts = pet.split(";;")
                if not parts:
                    continue

                # 1) Extract the pet name
                # Strip whitespace, remove leading/trailing quotes if they exist
                pet_name = parts[0].strip()
                if pet_name.startswith('"') and pet_name.endswith('"'):
                    pet_name = pet_name[1:-1]

                pet_name_lower = pet_name.lower()

                # 2) Extract the pet price if present
                pet_price = None
                if len(parts) > 1:
                    # Split the second portion on semicolons
                    price_parts = parts[1].split(";")
                    # Try to parse the last or any valid digit
                    # (same approach as your working function)
                    if price_parts and self.isfloat(price_parts[-1]):
                        pet_price = float(price_parts[-1])
                    else:
                        # If the last part isn't numeric, you could search backwards
                        # for the first digit-like part:
                        for p in reversed(price_parts):
                            if self.isfloat(p):
                                pet_price = float(p)
                                break

                # Store the parsed price (even if None) in the dictionary
                pbs_prices[pet_name_lower] = pet_price

            # Create pet level rules
            temp_pet_rules = []
            for _index, pet in self.pet_statistics.iterrows():
                pet_name_lower = pet["itemName"].lower()
                if pet_name_lower in pbs_prices:
                    parsed_price = pbs_prices[pet_name_lower]

                    # If the parsed price is None, fallback to the default price logic,
                    # or any discount logic you prefer
                    if parsed_price is None or parsed_price <= 0:
                        default_price = pet["desiredPrice"]
                        discount_percent = int(self.discount_percent.text()) / 100.0
                        parsed_price = round(float(default_price) * discount_percent, 4)

                    # Create a pet-level rule
                    pet_rule = {
                        "petID": int(pet["itemID"]),
                        "price": float(parsed_price),
                        "minLevel": 1,  # Default minimum level
                        "minQuality": -1,  # Default to any quality
                        "excludeBreeds": [],  # Default to no excluded breeds
                    }
                    temp_pet_rules.append(pet_rule)

            # Update rules list and display
            self.pet_ilvl_rules = temp_pet_rules
            for rule in self.pet_ilvl_rules:
                display_string = (
                    f"Pet ID: {rule['petID']}; "
                    f"Price: {rule['price']}; "
                    f"Min Level: {rule['minLevel']}; "
                    f"Min Quality: {rule['minQuality']}; "
                    f"Excluded Breeds: {rule['excludeBreeds']}"
                )
                self.pet_ilvl_list_display.addItem(display_string)

            if not self.pet_ilvl_rules:
                QMessageBox.warning(
                    self,
                    "Import Warning",
                    "No valid pets were imported. Check the PBS data format.",
                )

        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def convert_pet_ilvl_to_pbs(self):
        """Convert pet level rules to PBS format"""
        try:
            pbs_list = []
            for rule in self.pet_ilvl_rules:
                # Find the pet name from the ID
                pet_name = self.pet_statistics.loc[
                    self.pet_statistics["itemID"] == rule["petID"], "itemName"
                ]
                if pet_name.empty:
                    continue

                pet_name = pet_name.iloc[0]

                # Construct PBS entry (using only ID and price, other fields don't map to PBS)
                pbs_entry = f'Snipe^"{pet_name}";;0;0;0;0;0;{rule["price"]};;#;;'
                pbs_list.append(pbs_entry)

            # Join all entries and copy to clipboard
            pbs_string = "".join(pbs_list)
            clipboard = QApplication.clipboard()
            clipboard.setText(pbs_string)

            QMessageBox.information(
                self, "Success", "Converted PBS pet string copied to clipboard."
            )
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", str(e))

    def import_pbs_pet_data(self):
        # Open a dialog to allow users to paste the PBS data
        """
        Import pet data from PBS (Probably Battle Stones) format into the application.

        This method allows users to paste a formatted text containing pet data, which is then processed
        to extract pet names and their corresponding prices. The method supports various input formats
        and handles price extraction with fallback mechanisms.

        Parameters:
            None (uses self context)

        Raises:
            ValueError: If invalid data is encountered during parsing
            Exception: For any unexpected errors during data processing

        Behavior:
            - Opens a multi-line input dialog for users to paste PBS pet data
            - Parses the input, extracting pet names and prices
            - Matches pet names against existing pet statistics
            - Populates the pet list with extracted prices or calculated discounted prices
            - Updates the pet list display with imported pet IDs and prices
            - Handles cases where prices might be missing by applying a default discount

        Example:
            Input format: "Pet Name;;0;0;0;0;0;50000^Another Pet;;0;0;0;0;0;25000"
        """
        text, ok = QInputDialog.getMultiLineText(
            self, "Import PBS Pet Data", "Paste your PBS pet data here:"
        )
        if not ok or not text.strip():
            return

        self.pet_list_display.clear()

        try:
            # Process the pasted PBS data
            pbs_data = text.replace("\n", "").replace("\r", "").split("^")

            # Create a dictionary to map pet names to prices from the PBS data
            pbs_prices = {}
            for pet in pbs_data:
                # parts will be like ['Battle Pet Name', '0;0;0;0;0;50000', '#', '']
                parts = pet.split(";;")
                pet_name = parts[0].strip().lower()
                # strip off " if the name begins and ends with "
                if pet_name[0] == '"' and pet_name[-1] == '"':
                    pet_name = pet_name[1:-1]
                if len(parts) > 1:
                    price_parts = parts[1].split(";")
                    pet_price = (
                        float(price_parts[-1])
                        if self.isfloat(price_parts[-1])
                        else None
                    )
                    pbs_prices[pet_name] = pet_price
                else:
                    pbs_prices[pet_name] = None

            temp_pet_list = {}
            pbs_pet_names = list(pbs_prices.keys())
            for _index, pet in self.pet_statistics.iterrows():
                pet_name_lower = pet["itemName"].lower()
                if pet_name_lower in pbs_pet_names:
                    price = pbs_prices[pet_name_lower]
                    if price is not None:
                        temp_pet_list[str(pet["itemID"])] = pbs_prices[pet_name_lower]
                    else:
                        # Use default behavior if price is not set in PBS
                        default_price = pet["desiredPrice"]
                        discount_percent = int(self.discount_percent.text()) / 100
                        discount_price = round(
                            float(default_price) * discount_percent, 4
                        )
                        temp_pet_list[str(pet["itemID"])] = discount_price

            for key, value in temp_pet_list.items():
                self.pet_list_display.insertItem(
                    self.pet_list_display.count(),
                    f"Pet ID: {key}, Price: {value}",
                )
                self.pet_list[str(key)] = value

        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def convert_pets_to_pbs(self):
        try:
            # Convert the AAA pet list to PBS format
            pbs_string = self.convert_aaa_pets_to_pbs(self.pet_list)

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(pbs_string)

            QMessageBox.information(
                self, "Success", "Converted PBS pet string copied to clipboard."
            )
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", str(e))

    def convert_aaa_pets_to_pbs(self, pet_data):
        # Prepare the PBS list
        """
        Convert AAA pet data format to PBS (Panda Bot Sniper) format.

        This method transforms a dictionary of pet IDs and prices into a PBS-compatible string
        for use in automated pet sniping tools.

        Parameters:
            pet_data (dict): A dictionary with pet item IDs as keys and their corresponding prices as values.

        Returns:
            str: A concatenated string of PBS-formatted pet snipe entries, where each entry follows
                 the format: 'Snipe^"Pet Name";;0;0;0;0;0;price;;#;;'

        Notes:
            - Skips pets that cannot be found in the pet_statistics DataFrame
            - Converts prices to integers
            - Requires self.pet_statistics DataFrame with 'itemID' and 'itemName' columns
        """
        pbs_list = []

        for pet_id, price in pet_data.items():
            # Find the pet name by matching the itemID in pet_statistics
            pet_name = self.pet_statistics.loc[
                self.pet_statistics["itemID"] == int(pet_id), "itemName"
            ]

            # Skip if we don't find a name
            if pet_name.empty:
                continue
            pet_name = pet_name.iloc[0]

            # Construct the PBS entry
            # Format: Snipe^"Pet Name";;0;0;0;0;0;price;;#;;
            pbs_entry = f'Snipe^"{pet_name}";;0;0;0;0;0;{int(float(price))};;#;;'

            # Append the PBS entry to the list
            pbs_list.append(pbs_entry)

        # Join the PBS entries into a single string
        pbs_string = "".join(pbs_list)

        return pbs_string

    def isfloat(self, value):
        """Check if a value can be converted to float.

        Args:
            value: The value to check

        Returns:
            bool: True if value can be converted to float, False otherwise
        """
        try:
            float(value)
            return True
        except ValueError:
            return False


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        file = QFile(":/dark/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())
        ex = App()
        exit(app.exec_())
    except Exception as e:
        print("=== CRASH REPORT ===")
        print(f"Crash occurred at: {datetime.now()}")
        print(f"Error: {str(e)}")
        import traceback

        print("Full traceback:")
        print(traceback.format_exc())
        print("=== END CRASH REPORT ===")
        # Re-raise the exception after logging
        raise
