from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QLineEdit, QPushButton, QComboBox, QListWidget, QMessageBox, QCheckBox, QFileDialog, QSystemTrayIcon
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon
import sys, os
import requests
from sys import exit
import json
from mega_alerts import Alerts

import ctypes

if sys.platform == "win32":
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


class LabelTextbox(QMainWindow):

    def __init__(self,parent=None, labeltext=None,xposition=None,yposition=None, width=None, height=None):
        super(LabelTextbox,self).__init__()
        self.Label = QLabel(parent)
        self.Label.setText(labeltext)
        self.Label.move(xposition,yposition-30)
        self.Label.resize(width,height)
        self.Label.setFont((QtGui.QFont("Arial",12,QtGui.QFont.Bold)))
        self.Text = QLineEdit(parent)
        self.Text.move(xposition, yposition)
        self.Text.resize(width,height)
        self.Text.setFont((QtGui.QFont("Arial",12)))

class UIButtons(QMainWindow):

    def __init__(self, parent=None, title=None, xposition=None,yposition=None,width=None,heigth=None):
        super(UIButtons,self).__init__()
        self.Button=QPushButton(title, parent)
        self.Button.setFont((QtGui.QFont("Arial",12,QtGui.QFont.Bold)))
        self.Button.move(xposition,yposition)
        self.Button.resize(width,heigth)

class ComboBoxes(QMainWindow):
    def __init__(self,parent=None,xposition=None,yposition=None, width=None, height=None):
        super(ComboBoxes,self).__init__()
        self.Combo=QComboBox(parent)
        self.Combo.setGeometry(xposition,yposition,width,height)

class LabelText(QMainWindow):
    def __init__(self,parent=None, labeltext=None,xposition=None,yposition=None, width=None, height=None):
        super(LabelText,self).__init__()
        self.Label = QLabel(parent)
        self.Label.setText(labeltext)
        self.Label.move(xposition,yposition-30)
        self.Label.resize(width,height)
        self.Label.setFont((QtGui.QFont("Arial",12,QtGui.QFont.Bold)))

class ListView(QMainWindow):
    def __init__(self,parent=None, xposition=None,yposition=None, width=None, height=None):
        super(ListView,self).__init__()
        self.List = QListWidget(parent)
        self.List.move(xposition,yposition)
        self.List.resize(width,height)
        self.List.setFont((QtGui.QFont("Arial",12,QtGui.QFont.Bold)))

class CheckBox(QMainWindow):
    def __init__(self,parent=None,labeltext=None,xposition=None,yposition=None, width=None, height=None):
        super(CheckBox,self).__init__()
        self.Checkbox=QCheckBox(labeltext,parent)
        self.Checkbox.setGeometry(xposition,yposition,width,height)
        self.Checkbox.setFont((QtGui.QFont("Arial",12,QtGui.QFont.Bold)))

class App(QMainWindow):

    def __init__(self):
        super(App,self).__init__()
        self.title = 'Azeroth Auction Assassin'
        self.left = 0
        self.top = 0
        self.width = 1650
        self.height = 800

        icon = QIcon('icon.png')
        self.setWindowIcon(icon)

        self.token_auth_url = "http://api.saddlebagexchange.com/api/wow/checkmegatoken"

        self.eu_connected_realms = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "eu-wow-connected-realm-ids.json")
        self.na_connected_realms = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "na-wow-connected-realm-ids.json")
        self.EUCLASSIC_connected_realms = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "euclassic-wow-connected-realm-ids.json")
        self.NACLASSIC_connected_realms = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "naclassic-wow-connected-realm-ids.json")

        self.path_to_data = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "mega_data.json")
        self.path_to_desired_items = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "desired_items.json")
        self.path_to_desired_pets = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "desired_pets.json")
        self.path_to_desired_ilvl_items = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "desired_ilvl.json")
        self.path_to_desired_ilvl_list = os.path.join(os.getcwd(), "AzerothAuctionAssassinData", "desired_ilvl_list.json")

        self.pet_list = {}
        self.items_list = {}
        self.ilvl_list = []
        self.ilvl_items = {}

        self.initUI()

    def initUI(self):

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)


        self.discord_webhook_input=LabelTextbox(self,"Discord Webhook",25,25,425,40)
        self.discord_webhook_input.Label.setToolTip('Setup a discord channel with a webhook url for sending the alert messages.')

        self.wow_client_id_input=LabelTextbox(self,"WoW Client ID",25,100,425,40)
        self.wow_client_id_input.Label.setToolTip('Go to https://develop.battle.net/access/clients\nand create a client, get the blizzard oauth client and secret ids.')

        self.wow_client_secret_input=LabelTextbox(self,"WoW Client Secret",25,175,425,40)
        self.wow_client_secret_input.Label.setToolTip('Go to https://develop.battle.net/access/clients\nand create a client, get the blizzard oauth client and secret ids.')

        self.authentication_token=LabelTextbox(self,"Auction Assassin Token",25,250,425,40)
        self.authentication_token.Label.setToolTip('Go to the Saddlebag Exchange Discord and generate a token with the bot command:\n/wow auctionassassintoken')

        self.wow_region_label = LabelText(self, 'Wow Region', 25, 325, 200, 40)
        self.wow_region=ComboBoxes(self,25,325,200,40)
        self.wow_region.Combo.addItems(['EU','NA','EUCLASSIC','NACLASSIC'])
        self.wow_region_label.Label.setToolTip('Pick your region, currently supporting: EU, NA, EU-Classic and NA-Classic')

        self.number_of_mega_threads=LabelTextbox(self,"Number of Threads",250,325,200,40)
        self.number_of_mega_threads.Text.setText('48')
        self.number_of_mega_threads.Label.setToolTip('Change the thread count.\nDo 100 for the fastest scans, but RIP to ur CPU and MEM.')

        self.scan_time_min=LabelTextbox(self,"Scan Time Min",250,400,200,40)
        self.scan_time_min.Text.setText('1')
        self.scan_time_min.Label.setToolTip('Increase or decrease the minutes before or after the data update to start timed scans.')

        self.scan_time_max=LabelTextbox(self,"Scan Time Max",250,475,200,40)
        self.scan_time_max.Text.setText('3')
        self.scan_time_max.Label.setToolTip('Increase or decrease the minutes before or after the data update to stop running scans.')

        self.important_emoji=LabelTextbox(self,"Important Emoji",250,550,200,40)
        self.important_emoji.Text.setText('🔥')
        self.important_emoji.Label.setToolTip('Changes the separators from ==== to whatever emoji you want.')

        self.show_bid_prices = CheckBox(self, 'Show Bid Prices', 25, 375, 200, 40)
        self.show_bid_prices.Checkbox.setToolTip('Show items with Bid prices below your price limit on Desired Items')

        self.wow_head_link = CheckBox(self, 'Show WoWHead Link', 25, 405, 200, 40)
        self.wow_head_link.Checkbox.setToolTip('Uses WoWHead links instead of Undermine and shows pictures.')

        self.russian_realms = CheckBox(self, 'No Russian Realms', 25, 435, 200, 40)
        self.russian_realms.Checkbox.setChecked(True)
        self.russian_realms.Checkbox.setToolTip('Removes alerts from Russian Realms.')

        self.refresh_alerts = CheckBox(self, 'Refresh Alerts', 25, 465, 200, 40)
        self.refresh_alerts.Checkbox.setChecked(True)
        self.refresh_alerts.Checkbox.setToolTip('Set to true to refresh alerts every 1 hour.')

        self.debug_mode = CheckBox(self, 'Debug Mode', 25, 495, 200, 40)
        self.debug_mode.Checkbox.setToolTip('Trigger a scan on all realms once.\nUse this to test make sure your data is working.')

        self.import_config_button = UIButtons(self, "Import Config", 25, 550, 200, 50)
        self.import_config_button.Button.clicked.connect(self.import_configs)
        self.import_config_button.Button.setToolTip('Import your mega_data.json config.')

        self.save_data_button = UIButtons(self, "Save Data", 25, 625, 200, 50)
        self.save_data_button.Button.clicked.connect(self.save_data_to_json)
        self.save_data_button.Button.setToolTip('Save data without starting a scan.')

        self.reset_data_button = UIButtons(self, "Reset Data", 250, 625, 200, 50)
        self.reset_data_button.Button.clicked.connect(self.reset_app_data)
        self.reset_data_button.Button.setToolTip('Erase all data and reset the app.')

        self.start_button = UIButtons(self, "Start Alerts", 25, 700, 200, 50)
        self.start_button.Button.clicked.connect(self.start_alerts)
        self.start_button.Button.setToolTip('Start the scan! Runs once on start and then waits for new data to send more alerts.')

        self.stop_button = UIButtons(self, "Stop Alerts", 250, 700, 200, 50)
        self.stop_button.Button.clicked.connect(self.stop_alerts)
        self.stop_button.Button.setEnabled(False)
        self.stop_button.Button.setToolTip('Gracefully stop the alerts.\nThis will not stop alerts in progress.\nYou may need to kill the process for a force stop.')

        self.mega_alerts_progress = LabelText(self, 'Waiting for user to Start!', 25, 775, 1000, 40)

        ########################## PET STUFF ###################################################

        self.pet_id_input=LabelTextbox(self,"Pet ID",500,25,100,40)
        self.pet_id_input.Label.setToolTip('Add the Pet ID that you want to snipe.\nYou can find that id at the end of the undermine exchange link for the item next to 82800 (which is the item id for pet cages)\nhttps://undermine.exchange/#us-suramar/82800-3390.')

        self.pet_price_input=LabelTextbox(self,"Price",625,25,100,40)
        self.pet_price_input.Label.setToolTip('Pick a price you want to buy at or under.')

        self.add_pet_button = UIButtons(self, "Add Pet", 500, 100, 100, 50)
        self.add_pet_button.Button.clicked.connect(self.add_pet_to_dict)
        self.add_pet_button.Button.setToolTip('Add pet to your snipe list.')

        self.remove_pet_button = UIButtons(self, "Remove\nPet", 625, 100, 100, 50)
        self.remove_pet_button.Button.clicked.connect(self.remove_pet_to_dict)
        self.remove_pet_button.Button.setToolTip('Remove pet from your snipe list.')

        self.pet_list_display = ListView(self,500,175,225,400)
        self.pet_list_display.List.itemClicked.connect(self.pet_list_double_clicked)

        self.import_pet_data_button = UIButtons(self, "Import Pet Data", 500, 600, 225, 50)
        self.import_pet_data_button.Button.clicked.connect(self.import_pet_data)
        self.import_pet_data_button.Button.setToolTip('Import your desired_pets.json config')

        ########################## ITEM STUFF ###################################################

        self.item_id_input=LabelTextbox(self,"Item ID",750,25,100,40)
        self.item_id_input.Label.setToolTip('Add the item id of and item you want to buy.\nYou can search by name for them here with recommended prices\nhttps://temp.saddlebagexchange.com/megaitemnames')

        self.item_price_input=LabelTextbox(self,"Price",875,25,100,40)
        self.item_price_input.Label.setToolTip('Pick a price you want to buy at or under.')

        self.add_item_button = UIButtons(self, "Add Item", 750, 100, 100, 50)
        self.add_item_button.Button.clicked.connect(self.add_item_to_dict)
        self.add_item_button.Button.setToolTip('Add item to your snipe list.')

        self.remove_item_button = UIButtons(self, "Remove\nItem", 875, 100, 100, 50)
        self.remove_item_button.Button.clicked.connect(self.remove_item_to_dict)
        self.remove_item_button.Button.setToolTip('Remove item from your snipe list.')

        self.item_list_display = ListView(self,750,175,225,400)
        self.item_list_display.List.itemClicked.connect(self.item_list_double_clicked)

        self.import_item_data_button = UIButtons(self, "Import Item Data", 750, 600, 225, 50)
        self.import_item_data_button.Button.clicked.connect(self.import_item_data)
        self.import_item_data_button.Button.setToolTip('Import your desired_items.json config')

        ########################## ILVL STUFF ###################################################

        self.ilvl_item_input=LabelTextbox(self,"Item ID(s)",1000,25,100,40)
        self.ilvl_item_input.Label.setToolTip('Leave blank to snipe all items at this Ilvl.\nAdd the Item IDs of the BOE you want to snipe specific items separated by a comma\nex: 1,2,99,420420')

        self.ilvl_input=LabelTextbox(self,"Item level",1000,100,100,40)
        self.ilvl_input.Label.setToolTip('Set the minimum item level you want to snipe.')

        self.ilvl_price_input=LabelTextbox(self,"Buyout",1000,175,100,40)
        self.ilvl_price_input.Label.setToolTip('Set the maximum buyout you want to snipe.')

        self.ilvl_sockets=CheckBox(self,"Sockets",1000,225,100,40)
        self.ilvl_sockets.Checkbox.setToolTip('Do you want the item to have Sockets?')

        self.ilvl_speed=CheckBox(self,"Speed",1000,275,100,40)
        self.ilvl_speed.Checkbox.setToolTip('Do you want the item to have Speed?')

        self.ilvl_leech=CheckBox(self,"Leech",1000,325,100,40)
        self.ilvl_leech.Checkbox.setToolTip('Do you want the item to have Leech?')

        self.ilvl_avoidance=CheckBox(self,"Avoidance",1000,375,100,40)
        self.ilvl_avoidance.Checkbox.setToolTip('Do you want the item to have Avoidance?')

        self.add_ilvl_button = UIButtons(self, "Add Item", 1000, 425, 100, 50)
        self.add_ilvl_button.Button.clicked.connect(self.add_ilvl_to_list)
        self.add_ilvl_button.Button.setToolTip('Add item to your snipe list.')

        self.remove_ilvl_button = UIButtons(self, "Remove\nItem", 1000, 500, 100, 50)
        self.remove_ilvl_button.Button.clicked.connect(self.remove_ilvl_to_list)
        self.remove_ilvl_button.Button.setToolTip('Remove item from your snipe list.')

        self.ilvl_list_display = ListView(self,1125,25,500,550)
        self.ilvl_list_display.List.itemClicked.connect(self.ilvl_list_double_clicked)

        self.import_ilvl_data_button = UIButtons(self, "Import Desired ILvl List Data", 1125, 600, 500, 50)
        self.import_ilvl_data_button.Button.clicked.connect(self.import_ilvl_data)
        self.import_ilvl_data_button.Button.setToolTip('Import your desired_ilvl_list.json config')

        self.check_for_settings()

        self.show()

    def check_config_file(self, path_to_config):
        try:
            with open(path_to_config, encoding="utf-8") as json_file:
                raw_mega_data = json.load(json_file)
            if 'MEGA_WEBHOOK_URL' in raw_mega_data:
                self.discord_webhook_input.Text.setText(raw_mega_data['MEGA_WEBHOOK_URL'])

            if 'WOW_CLIENT_ID' in raw_mega_data:
                self.wow_client_id_input.Text.setText(raw_mega_data['WOW_CLIENT_ID'])
            
            if 'WOW_CLIENT_SECRET' in raw_mega_data:
                self.wow_client_secret_input.Text.setText(raw_mega_data['WOW_CLIENT_SECRET'])

            if 'AUTHENTICATION_TOKEN' in raw_mega_data:
                self.authentication_token.Text.setText(raw_mega_data['AUTHENTICATION_TOKEN'])

            if 'WOW_REGION' in raw_mega_data:
                index=self.wow_region.Combo.findText(raw_mega_data['WOW_REGION'])
                if index>=0:
                    self.wow_region.Combo.setCurrentIndex(index)

            if 'SHOW_BID_PRICES' in raw_mega_data:
                self.show_bid_prices.Checkbox.setChecked(raw_mega_data['SHOW_BID_PRICES'])

            if 'MEGA_THREADS' in raw_mega_data:
                self.number_of_mega_threads.Text.setText(str(raw_mega_data['MEGA_THREADS']))

            if 'WOWHEAD_LINK' in raw_mega_data:
                self.wow_head_link.Checkbox.setChecked(raw_mega_data['WOWHEAD_LINK'])

            if 'IMPORTANT_EMOJI' in raw_mega_data:
                self.important_emoji.Text.setText(raw_mega_data['IMPORTANT_EMOJI'])

            if 'NO_RUSSIAN_REALMS' in raw_mega_data:
                self.russian_realms.Checkbox.setChecked(raw_mega_data['NO_RUSSIAN_REALMS'])

            if 'REFRESH_ALERTS' in raw_mega_data:
                self.refresh_alerts.Checkbox.setChecked(raw_mega_data['REFRESH_ALERTS'])

            if 'SCAN_TIME_MAX' in raw_mega_data:
                self.scan_time_max.Text.setText(str(raw_mega_data['SCAN_TIME_MAX']))

            if 'SCAN_TIME_MIN' in raw_mega_data:
                self.scan_time_min.Text.setText(str(raw_mega_data['SCAN_TIME_MIN']))

            if 'DEBUG' in raw_mega_data:
                self.debug_mode.Checkbox.setChecked(raw_mega_data['DEBUG'])
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Parsing Error", f"Could not parse JSON data in {path_to_config}")
        except:
            QMessageBox.critical(self, "Loading Error", f"Could not load config settings from {path_to_config}")

    def check_for_settings(self):

        data_folder = os.path.join(os.getcwd(), "AzerothAuctionAssassinData")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        if not os.path.exists(self.eu_connected_realms):
            from utils.realm_data import EU_CONNECTED_REALMS_IDS

            with open(self.eu_connected_realms, 'w') as json_file:
                json.dump(EU_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.na_connected_realms):
            from utils.realm_data import NA_CONNECTED_REALMS_IDS

            with open(self.na_connected_realms, 'w') as json_file:
                json.dump(NA_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.EUCLASSIC_connected_realms):
            from utils.realm_data import EUCLASSIC_CONNECTED_REALMS_IDS

            with open(self.EUCLASSIC_connected_realms, 'w') as json_file:
                json.dump(EUCLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if not os.path.exists(self.NACLASSIC_connected_realms):
            from utils.realm_data import NACLASSIC_CONNECTED_REALMS_IDS

            with open(self.NACLASSIC_connected_realms, 'w') as json_file:
                json.dump(NACLASSIC_CONNECTED_REALMS_IDS, json_file, indent=4)

        if os.path.exists(self.path_to_data):
            self.check_config_file(self.path_to_data)
                
        if os.path.exists(self.path_to_desired_pets):
            self.pet_list = json.load(open(self.path_to_desired_pets))
            for key,value in self.pet_list.items():
                self.pet_list_display.List.insertItem(self.pet_list_display.List.count() , f'Pet ID: {key}, Price: {value}')

        if os.path.exists(self.path_to_desired_items):
            self.items_list = json.load(open(self.path_to_desired_items))
            for key,value in self.items_list.items():
                self.item_list_display.List.insertItem(self.item_list_display.List.count() , f'Item ID: {key}, Price: {value}')

        if os.path.exists(self.path_to_desired_ilvl_list):
            self.ilvl_list = json.load(open(self.path_to_desired_ilvl_list))
            for ilvl_dict_data in self.ilvl_list:
                if "item_ids" not in ilvl_dict_data:
                    ilvl_dict_data['item_ids'] = []
                string_with_data = f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}"
                self.ilvl_list_display.List.insertItem(self.ilvl_list_display.List.count() , string_with_data)


    def ilvl_list_double_clicked(self,item):
        item_split = item.text().replace(' ', '').split(':')

        item_id = item_split[1].split(';')[0]
        buyout = item_split[2].split(';')[0]
        ilvl = item_split[3].split(';')[0]
        sockets = item_split[4].split(';')[0]
        speed = item_split[5].split(';')[0]
        leech = item_split[6].split(';')[0]
        avoidance = item_split[7]

        self.ilvl_item_input.Text.setText(item_id)
        self.ilvl_price_input.Text.setText(buyout)

        self.ilvl_sockets.Checkbox.setChecked(sockets == "True")
        self.ilvl_speed.Checkbox.setChecked(speed == "True")
        self.ilvl_leech.Checkbox.setChecked(leech == "True")
        self.ilvl_avoidance.Checkbox.setChecked(avoidance == "True")

        self.ilvl_input.Text.setText(ilvl)

    def add_ilvl_to_list(self):
        ilvl = self.ilvl_input.Text.text()
        price = self.ilvl_price_input.Text.text()

        if ilvl == "" or price == "":
            QMessageBox.critical(self, "Incomplete Information", "Both ilvl and price fields are required.")
            return False

        try:
            ilvl_int = int(ilvl)
            price_int = int(price)
        except ValueError:
            QMessageBox.critical(self, "Invalid Input", "Ilvl and price should be numbers.")
            return False

        # Check if ilvl is between 1 and 999
        if not 1 <= ilvl_int <= 999:
            QMessageBox.critical(self, "Incorrect Ilvl Value", "Ilvl must be between 1 and 999.")
            return False
        
        # Check if Price is between 1 and 10 million
        if not 1 <= price_int <= 10000000:
            QMessageBox.critical(self, "Incorrect Price", "Price must be between 1 and 10 million.")
            return False

        item_ids_text = self.ilvl_item_input.Text.text()
        if item_ids_text == "":
            item_ids_list = []
        else:
            # Validate item IDs
            try:
                item_ids_list = list(map(int, item_ids_text.replace(' ', '').split(',')))

                # Check if all items are between 100k and 500k
                if any(not 100000 <= item_id <= 500000 for item_id in item_ids_list):
                    QMessageBox.critical(self, "Invalid Item ID", "All item IDs should be between 100k and 500k.")
                    return False
            except ValueError:
                QMessageBox.critical(self, "Invalid Input", f"Item IDs should be numbers.")
                return False

        # Create a dictionary with the data
        ilvl_dict_data = {
            'ilvl': ilvl_int,
            'buyout': price_int,
            'sockets': self.ilvl_sockets.Checkbox.isChecked(),
            'speed': self.ilvl_speed.Checkbox.isChecked(),
            'leech': self.ilvl_leech.Checkbox.isChecked(),
            'avoidance': self.ilvl_avoidance.Checkbox.isChecked(),
            'item_ids': item_ids_list,
        }

        if ilvl_dict_data not in self.ilvl_list:
            self.ilvl_list.append(ilvl_dict_data)
            self.ilvl_list_display.List.insertItem(
                self.ilvl_list_display.List.count(),
                f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}")

        return True


    def remove_ilvl_to_list(self):
        if len(self.ilvl_input.Text.text()) == 0:
            QMessageBox.critical(self, "Ilvl Removal Issue", "Please double click an ilvl json to remove it!")
            return
        if self.ilvl_item_input.Text.text() == "":
            item_ids_list = []
        else:
            item_ids_list = list(map(int, self.ilvl_item_input.Text.text().replace(' ', '').split(',')))

        ilvl_dict_data = {
            'ilvl': int(self.ilvl_input.Text.text()),
            'buyout': int(self.ilvl_price_input.Text.text()),
            'sockets': self.ilvl_sockets.Checkbox.isChecked(),
            'speed': self.ilvl_speed.Checkbox.isChecked(),
            'leech': self.ilvl_leech.Checkbox.isChecked(),
            'avoidance': self.ilvl_avoidance.Checkbox.isChecked(),
            'item_ids': item_ids_list,
        }

        if ilvl_dict_data in self.ilvl_list:
            string_with_data = f"Item ID: {','.join(map(str, ilvl_dict_data['item_ids']))}; Price: {ilvl_dict_data['buyout']}; ILvl: {ilvl_dict_data['ilvl']}; Sockets: {ilvl_dict_data['sockets']}; Speed: {ilvl_dict_data['speed']}; Leech: {ilvl_dict_data['leech']}; Avoidance: {ilvl_dict_data['avoidance']}"
            print(string_with_data)
            for x in range(self.ilvl_list_display.List.count()):
                if self.ilvl_list_display.List.item(x).text() == string_with_data:
                    self.ilvl_list_display.List.takeItem(x)
                    self.ilvl_list.remove(ilvl_dict_data)
                    return

    def import_ilvl_data(self):
        pathname=QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.ilvl_list_display.List.clear()
        self.ilvl_list = {}

        try:
            with open(pathname) as file:
                self.ilvl_list = json.load(file)
            if not isinstance(self.ilvl_list, list):
                raise ValueError("Invalid JSON file.\nFile should contain a list of Desired Ilvl Objects.")
            for ilvl_dict_data in self.ilvl_list:
                if "item_ids" not in ilvl_dict_data:
                    item_ids = []
                else:
                    item_ids = ilvl_dict_data['item_ids']
                buyout_price = ilvl_dict_data['buyout']
                ilvl = ilvl_dict_data['ilvl']
                sockets = ilvl_dict_data['sockets']
                speed = ilvl_dict_data['speed']
                leech = ilvl_dict_data['leech']
                avoidance = ilvl_dict_data['avoidance']

                # Check that all item IDs are valid integers, but allow list to be empty
                if not all(isinstance(id, int) and 1 <= id <= 500000 for id in item_ids):
                    raise ValueError(f"Invalid item ID(s) in {item_ids}.\nIDs must be integers between 1-500,000.")

                # Check that price is a valid integer within range
                if not (1 <= buyout_price <= 10000000):
                    raise ValueError(f"Invalid buyout price {buyout_price}.\nPrices must be integers between 1-10,000,000.")

                # Check that ilvl is a valid integer within range
                if not (200 <= ilvl <= 1000):
                    raise ValueError(f"Invalid ILvl {ilvl}.\nILvl must be an integer between 200-1000.")

                # Check that sockets, speed, leech and avoidance are booleans
                if not all(isinstance(val, bool) for val in [sockets, speed, leech, avoidance]):
                    raise ValueError("Sockets, speed, leech, and avoidance should be boolean values.")

                string_with_data = f"Item ID: {','.join(map(str, item_ids))}; Price: {buyout_price}; ILvl: {ilvl}; Sockets: {sockets}; Speed: {speed}; Leech: {leech}; Avoidance: {avoidance}"
                self.ilvl_list_display.List.insertItem(self.ilvl_list_display.List.count(), string_with_data)

        except json.JSONDecodeError:
            QMessageBox.critical(self, "Invalid JSON", "Please provide a valid JSON file!")
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))


    def item_list_double_clicked(self,item):
        item_split = item.text().replace(' ', '').split(':')
        item_id = item_split[1].split(',')[0]
        self.item_id_input.Text.setText(item_id)
        self.item_price_input.Text.setText(item_split[2])

    def add_item_to_dict(self):
        item_id = self.item_id_input.Text.text()
        item_price = self.item_price_input.Text.text()

        if item_id == "" or item_price == "":
            QMessageBox.critical(self, "Incomplete Information", "All fields are required.")
            return False

        try:
            item_id_int = int(item_id)
            item_price_int = int(item_price)
        except ValueError:
            QMessageBox.critical(self, "Invalid Input", "Item ID and Price should be numbers.")
            return False

        # Check if Item ID is between 1 and 500000
        if not 1 <= item_id_int <= 500000:
            QMessageBox.critical(self, "Incorrect Item ID", "Item ID must be between 1 and 500000.")
            return False

        # Check if Price is between 1 and 10 million
        if not 1 <= item_price_int <= 10000000:
            QMessageBox.critical(self, "Incorrect Price", "Price must be between 1 and 10 million.")
            return False

        # If item is already in the items_list, remove it
        if item_id in self.items_list:
            for existing_item in range(self.item_list_display.List.count()):
                if self.item_list_display.List.item(existing_item).text() == f'Item ID: {item_id}, Price: {self.items_list[item_id]}':
                    self.item_list_display.List.takeItem(existing_item)
                    break

        # Add or Update item in the items_list
        self.items_list[item_id] = item_price
        self.item_list_display.List.insertItem(self.item_list_display.List.count(), f'Item ID: {item_id}, Price: {item_price}')

        return True

    def remove_item_to_dict(self):
        if self.item_id_input.Text.text() in self.items_list:
            for x in range(self.item_list_display.List.count()):
                if self.item_list_display.List.item(x).text() == f'Item ID: {self.item_id_input.Text.text()}, Price: {self.items_list[self.item_id_input.Text.text()]}':

                    self.item_list_display.List.takeItem(x)
                    del self.items_list[self.item_id_input.Text.text()]
                    return

    def import_item_data(self):
        pathname=QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.item_list_display.List.clear()
        self.items_list = {}

        try:
            with open(pathname) as file:
                self.items_list = json.load(file)
            for key,value in self.items_list.items():
                if not (1 <= int(key) <= 500000):
                    raise ValueError(f"Invalid item ID {key}.\nIDs must be integers between 1-500,000.")
                if not (1 <= int(value) <= 10000000):
                    raise ValueError(f"Invalid price {value} for item ID {key}.\nPrices must be integers between 1-10,000,000.")
                self.item_list_display.List.insertItem(self.item_list_display.List.count(), f'Item ID: {key}, Price: {value}')

        except json.JSONDecodeError:
            QMessageBox.critical(self, "Invalid JSON", "Please provide a valid JSON file!")
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def pet_list_double_clicked(self,item):
        item_split = item.text().replace(' ', '').split(':')
        pet_id = item_split[1].split(',')[0]
        self.pet_id_input.Text.setText(pet_id)
        self.pet_price_input.Text.setText(item_split[2])

    def add_pet_to_dict(self):
        pet_id = self.pet_id_input.Text.text()
        pet_price = self.pet_price_input.Text.text()
        
        if pet_id == "" or pet_price == "":
            QMessageBox.critical(self, "Incomplete Information", "All fields are required.")
            return False

        try:
            pet_id_int = int(pet_id)
            pet_price_int = int(pet_price)
        except ValueError:
            QMessageBox.critical(self, "Invalid Input", "Pet ID and Price should be numbers.")
            return False
        
        # Check if Pet ID is between 1 and 10000
        if not 1 <= pet_id_int <= 10000:
            QMessageBox.critical(self, "Incorrect Pet ID", "Pet ID must be between 1 and 10000.")
            return False

        # Check if Price is between 1 and 10 million
        if not 1 <= pet_price_int <= 10000000:
            QMessageBox.critical(self, "Incorrect Price", "Price must be between 1 and 10 million.")
            return False
        
        # If pet_id is already in the list, remove it
        if pet_id in self.pet_list:
            for existing_entry in range(self.pet_list_display.List.count()):
                if self.pet_list_display.List.item(existing_entry).text() == f'Pet ID: {pet_id}, Price: {self.pet_list[pet_id]}':
                    self.pet_list_display.List.takeItem(existing_entry)
                    break

        # Add or replace an item in pet_list
        self.pet_list[pet_id] = pet_price
        # Add new item to the display list
        self.pet_list_display.List.insertItem(self.pet_list_display.List.count(), f'Pet ID: {pet_id}, Price: {pet_price}')

        return True

    def remove_pet_to_dict(self):
        if self.pet_id_input.Text.text() in self.pet_list:
            for x in range(self.pet_list_display.List.count()):
                if self.pet_list_display.List.item(x).text() == f'Pet ID: {self.pet_id_input.Text.text()}, Price: {self.pet_list[self.pet_id_input.Text.text()]}':

                    self.pet_list_display.List.takeItem(x)
                    del self.pet_list[self.pet_id_input.Text.text()]
                    return

    def import_pet_data(self):
        pathname=QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return

        self.pet_list_display.List.clear()
        self.pet_list = {}

        try:
            with open(pathname) as file:
                self.pet_list = json.load(file)
            for key,value in self.pet_list.items():
                if not (1 <= int(key) <= 10000):
                    raise ValueError(f"Invalid pet ID {key}.\nIDs must be integers between 1-500,000.")
                if not (1 <= int(value) <= 10000000):
                    raise ValueError(f"Invalid price {value} for pet ID {key}.\nPrices must be integers between 1-10,000,000.")
                self.pet_list_display.List.insertItem(self.pet_list_display.List.count(), f'Pet ID: {key}, Price: {value}')
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Invalid JSON", "Please provide a valid JSON file!")
        except ValueError as ve:
            QMessageBox.critical(self, "Invalid Value", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Unknown Error", str(e))

    def import_configs(self):
        pathname=QFileDialog().getOpenFileName(self)[0]
        if not pathname or pathname == "":
            return
        self.check_config_file(pathname)

    def reset_app_data(self):
        self.ilvl_list_display.List.clear()
        self.pet_list_display.List.clear()
        self.item_list_display.List.clear()

        self.discord_webhook_input.Text.setText(''),
        self.wow_client_id_input.Text.setText(''),
        self.wow_client_secret_input.Text.setText(''),
        self.authentication_token.Text.setText(''),
        self.show_bid_prices.Checkbox.setChecked(False),
        self.number_of_mega_threads.Text.setText('48'),
        self.wow_head_link.Checkbox.setChecked(False),
        self.important_emoji.Text.setText('🔥'),
        self.russian_realms.Checkbox.setChecked(True),
        self.refresh_alerts.Checkbox.setChecked(True),
        self.scan_time_min.Text.setText('1'),
        self.scan_time_max.Text.setText('3'),
        self.debug_mode.Checkbox.setChecked(False)


        self.pet_list = {}
        self.items_list = {}
        self.ilvl_list = []

        self.save_data_to_json()

    def save_data_to_json(self):
        wow_region = self.wow_region.Combo.currentText()

        # Check if WOW_REGION is either 'NA', 'EU', 'NACLASSIC', 'EUCLASSIC'
        if wow_region not in ['NA', 'EU', 'NACLASSIC', 'EUCLASSIC']:
            QMessageBox.critical(self, "Invalid Region", "WOW region must be either 'NA', 'EU', 'NACLASSIC' or 'EUCLASSIC'.")
            return False

        mega_threads = self.number_of_mega_threads.Text.text()
        scan_time_max = self.scan_time_max.Text.text()
        scan_time_min = self.scan_time_min.Text.text()

        # Check if MEGA_THREADS, SCAN_TIME_MAX, and SCAN_TIME_MIN are integers 
        integer_fields = {'MEGA_THREADS': mega_threads, 'SCAN_TIME_MAX': scan_time_max, 'SCAN_TIME_MIN': scan_time_min}

        for field, value in integer_fields.items():
            try:
                int(value)
            except ValueError:
                QMessageBox.critical(self, "Invalid Value", f"{field} should be an integer.")
                return False

        show_bids = self.show_bid_prices.Checkbox.isChecked()
        wowhead = self.wow_head_link.Checkbox.isChecked()
        no_russians = self.russian_realms.Checkbox.isChecked()
        refresh_alerts = self.refresh_alerts.Checkbox.isChecked()
        debug = self.debug_mode.Checkbox.isChecked()

        boolean_fields = {'SHOW_BID_PRICES': show_bids, 'WOWHEAD_LINK': wowhead, 'NO_RUSSIAN_REALMS': no_russians, 'REFRESH_ALERTS': refresh_alerts, 'DEBUG': debug}

        # Ensure all boolean fields have a boolean value.
        for field, value in boolean_fields.items():
            if type(value) != bool:
                QMessageBox.critical(self, "Invalid Value", f"{field} should be a boolean.")
                return False

        # If all tests pass, save data to JSON.
        config_json = {
            'MEGA_WEBHOOK_URL': self.discord_webhook_input.Text.text(),
            'WOW_CLIENT_ID': self.wow_client_id_input.Text.text(),
            'WOW_CLIENT_SECRET': self.wow_client_secret_input.Text.text(),
            'AUTHENTICATION_TOKEN': self.authentication_token.Text.text(),
            'WOW_REGION': wow_region,
            'SHOW_BID_PRICES': show_bids,
            'MEGA_THREADS': int(mega_threads),
            'WOWHEAD_LINK': wowhead,
            'IMPORTANT_EMOJI': self.important_emoji.Text.text(),
            'NO_RUSSIAN_REALMS': no_russians,
            'REFRESH_ALERTS': refresh_alerts,
            'SCAN_TIME_MAX': int(scan_time_max),
            'SCAN_TIME_MIN': int(scan_time_min),
            'DEBUG': debug
        }

        # Save JSON files
        self.save_json_file(self.path_to_data, config_json)
        self.save_json_file(self.path_to_desired_pets, self.pet_list)
        self.save_json_file(self.path_to_desired_items, self.items_list)
        self.save_json_file(self.path_to_desired_ilvl_list, self.ilvl_list)
        self.save_json_file(self.path_to_desired_ilvl_items, self.ilvl_items)

        return True

    def save_json_file(self, path, data):
        with open(path, 'w', encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

    def start_alerts(self):

        response = requests.post(self.token_auth_url, json={"token":f"{self.authentication_token.Text.text()}"})

        response_dict = response.json()

        if response.status_code != 200:
            QMessageBox.critical(self, "Request Error", f"Could not reach server, status code : {response.status_code}")
            return

        if len(response_dict) == 0:
            QMessageBox.critical(self, "Auction Assassin Token", "Please provide a valid Auction Assassin token!")
            return

        if 'succeeded' not in response_dict:
            QMessageBox.critical(self, "Auction Assassin Token", "Please provide a valid Auction Assassin token!")
            return

        if not response_dict['succeeded']:
            QMessageBox.critical(self, "Auction Assassin Token", "Your Auction Assassin token is incorrect or expired!")
            return

        self.start_button.Button.setEnabled(False)
        self.stop_button.Button.setEnabled(True)

        if not self.save_data_to_json():
            QMessageBox.critical(self, "Save Error", "Could not save data to JSON.\nAbort scan.\nYour inputs may be invalid")
            return

        self.alerts_thread = Alerts(
            path_to_data_files = self.path_to_data,
            path_to_desired_items = self.path_to_desired_items,
            path_to_desired_pets = self.path_to_desired_pets,
            path_to_desired_ilvl_items = self.path_to_desired_ilvl_items,
            path_to_desired_ilvl_list = self.path_to_desired_ilvl_list
            )
        self.alerts_thread.start()
        self.alerts_thread.progress.connect(self.alerts_progress_changed)
        self.alerts_thread.finished.connect(self.alerts_thread_finished)

    def stop_alerts(self):
        self.alerts_thread.running=False
        self.stop_button.Button.setText('Stopping Process')
        self.alerts_progress_changed("Stopping alerts!")
        self.stop_button.Button.setEnabled(False)

    def alerts_thread_finished(self):
        self.stop_button.Button.setText("Stop Alerts")
        self.start_button.Button.setEnabled(True)
        self.alerts_progress_changed('Waiting for user to Start!')

    def alerts_progress_changed(self, progress_str):
        self.mega_alerts_progress.Label.setText(progress_str)

if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = App()
    exit(app.exec_())
