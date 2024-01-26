# Azeroth Auction Assassin

A super fast Blizzard AH sniper created by Saddlebag Exchange. Version 2.0 of our [MEGA-ALERTS](https://github.com/ff14-advanced-market-search/mega-alerts)

**Please dontate to our patreon so we can keep the project running.  If you need help setting it up, our creator will personally help any patreon subscribers.**

https://www.patreon.com/indopan

This amazing tool runs every time the blizzard API updates each hour and then alerts you on discord.

Blizzard only sends out new AH data to the API one time per hour, the rest of the time MEGA-ALERTS will sit and wait for new data to come out before sending more alerts. You can see what minute of each hour blizzard releases new data for your realm [here on our upload times page to find when new alerts will be sent to you.](https://saddlebagexchange.com/wow/upload-timers) 

<img src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/dbdf6a86-e560-4f59-b87e-bac7379f3b9d" width="300" height="300">

# Alert Example
<img width="601" alt="image" src="https://user-images.githubusercontent.com/17516896/224507162-53513e8a-69ab-41e2-a5d5-ea4e51a9fc89.png">

# Installation

1. Download the App: [Windows](https://www.dropbox.com/scl/fi/3n5n4fa5e6n1cqrpqmpeg/mega_alerts_gui-windows.zip?rlkey=w25mrnwynyw2yc07fx1iejqxp&dl=0) or [Mac](https://www.dropbox.com/scl/fi/jmzj7ifr5xa599xg2ubr6/mega_alerts_gui-mac.zip?rlkey=9jh8xbpu4qd4cos06o1tf1s12&dl=0)

2. Go to https://develop.battle.net/access/clients and create a client, get the blizzard oauth client and secret ids.  You will use these values for the `WOW_CLIENT_ID` and `WOW_CLIENT_SECRET` later on.

<img width="1304" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/e954289a-ccbc-4afb-9f66-897bbc68f677">

<img width="633" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/595fee57-e0db-4910-995d-5b5ae48190a2">


3. [Setup a discord channel with a webhook url for sending the alert messages](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) You will use this for the `MEGA_WEBHOOK_URL` later on.

4. Go to the [Saddlebag Exchange Discord](https://discord.gg/SYv8854Tbr) and ask us for a 30 day Auction Assasin Token.  Soon we will have our discord bot generate these for Super Fancy [Patreon Supporters](https://www.patreon.com/indopan). 


# Item Selection
1. If you have specific items and prices you want, then make a json object with the item ids and prices that you want to snipe for!

This is what you will set for `DESIRED_ITEMS` or you can set `{}` if you only want to snipe pets.

* The item ids for items you want to snipe are as the keys
* and set the price in gold for each item as the value

For example the following looks for [item id 194641 (which is the elemental lariat)](https://undermine.exchange/#us-thrall/194641) for under 500k and another item for under 40k.

```
{"194641": 500000, "159840":40000}
```

[Paste that into this json checker if you want to make sure your json is valid](https://jsonlint.com/)

You can find that id at the end of the undermine exchange link for the item https://undermine.exchange/#us-thrall/194641 or if you look it up on wowhead the url also has the item id https://www.wowhead.com/item=194641/design-elemental-lariat

[You can also use our item id to name lookup tool, which makes this even easier.](https://temp.saddlebagexchange.com/itemnames)

2.  If you have specific pets and prices you want, then make a json object with the pet ids and prices that you want to snipe for!

This is what you will set for `DESIRED_PETS` or you can set `{}` if you only want to snipe regular items.

* The pet ids for items you want to snipe are as the keys
* and set the price in gold for each item as the value

For example the following looks for [pet species id 3390 (which is the Sophic Amalgamation)](https://undermine.exchange/#us-suramar/82800-3390) for under 3K.

```
{"3390": 3000}
```

You can find that id at the end of the undermine exchange link for the item next to `82800` (which is the item id for pet cages) https://undermine.exchange/#us-suramar/82800-3390.

3. If you want to snipe based on ilvl, leech, speed, avoidance or sockets then setup the json object for that:

We now have an extra option similar to the `DESIRED_ITEMS` or `DESIRED_PETS` for sniping items based on ilvl.  This also lets you search for items with specific item levels and leech, sockets, speed or avoidance.

To enable this set the env var `DESIRED_ILVL` with json similar to the following. This example looks for items with over an ilvl of 360 with a speed stat:

```
{"ilvl": 424, "buyout": 1000, "sockets": false, "speed": true, "leech": false, "avoidance": false}
```

If we change this to and set `"sockets": true` then it will show items over an ilvl of 360 with a speed stat or a socket:

```
{"ilvl": 424, "buyout": 1000, "sockets": true, "speed": true, "leech": false, "avoidance": false}
```

4. If you want to run locally with python or pycharm, first clone the repo or [download the code](https://github.com/ff14-advanced-market-search/mega-alerts/archive/refs/heads/main.zip).  Then set all your user values in the data files under the [user_data/mega](https://github.com/ff14-advanced-market-search/mega-alerts/blob/main/user_data/) json files:

- [Set the item ids and prices you want](https://github.com/ff14-advanced-market-search/mega-alerts/blob/main/user_data/mega/desired_items.json)
- [Set the pet ids and prices you want](https://github.com/ff14-advanced-market-search/mega-alerts/blob/main/user_data/mega/desired_pets.json)
- [Set the ilvl and price info for snipe by ilvl and stats](https://github.com/ff14-advanced-market-search/mega-alerts/blob/main/user_data/mega/desired_ilvl.json)
- [Set up all the other important details for alerts](https://github.com/ff14-advanced-market-search/mega-alerts/blob/main/user_data/mega/mega_data.json)


Even if you are not going to run directly in python then you should still save this somewhere in a text file.


# How to run the alerts

With whatever method you choose you will provide all the details the code needs in *Environmental Variables*.  You must provide at least the following:

- `MEGA_WEBHOOK_URL`
- `WOW_CLIENT_ID`
- `WOW_CLIENT_SECRET`
- `WOW_REGION` either `EU` or `NA`
- Then for your snipe method you must provide at least one correct json data for `DESIRED_ITEMS`, `DESIRED_PETS` or `DESIRED_ILVL`

We also have the following **optional** env vars you can add in to change alert behavior, but you dont need to as all have default values when not manually set:
- `DEBUG="true"` This will instantly trigger a scan on all realms against your inputs, this will only run once and then exit the script or container so use it to debug and make sure your data is working.
- `SHOW_BID_PRICES=true` Bid prices below your price limit will also be shown (default false)
- `WOWHEAD_LINK=true` Uses wowhead links instead of undermine and shows pictures, but the message length will be longer (default false)
- `SCAN_TIME_MIN=-1` increase or decrease the minutes before or at the data update time to start scanning (default to keep scanning 1 min after the data updates).
- `SCAN_TIME_MAX=1` increase or decrease the minutes after the data updates to stop scanning (default to keep scanning 3 min after the data updates).
- `MEGA_THREADS=100` increase or decrease the threadcount (default to scan 48 realms at once)(more threads = faster scans, but doing more threads then realms is pointless).
- `REFRESH_ALERTS="false"` if set to false then you will not see the same alert more than once (default true)
- `NO_RUSSIAN_REALMS="true"` set this to true if you are on EU and do not want to get alerts from russian realms
- `IMPORTANT_EMOJI=🔥` changes the separators from `====` to whatever emoji you set. 

## Starting and Stopping the Sniper 

You can use any combination of `DESIRED_ITEMS`, `DESIRED_PETS`, `DESIRED_ILVL` or `DESIRED_ILVL_LIST` but at least one must be set.

# How to update versions

wip

# Snipe by ilvl and tertiary stats

We now have an extra option similar to the `DESIRED_ITEMS` or `DESIRED_PETS` for sniping items based on ilvl.  This also lets you search for items with specific item levels and leech, sockets, speed or avoidance.

To enable this set the env var `DESIRED_ILVL` with json similar to the following. 

This example will snipe anything based on ilvl (just make sure all the stats are set to false for ilvl alone):

```json
{
  "ilvl": 420,
  "buyout": 1000,
  "sockets": false,
  "speed": false,
  "leech": false,
  "avoidance": false,
  "item_ids": [204423, 204410]
}
```

<img width="680" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/722e828d-fdbf-485e-82b5-b8bc08827e3a">


This example looks for items with over an ilvl of 360 with a speed stat because `"speed": true`:

```json
{
  "ilvl": 424,
  "buyout": 1000,
  "sockets": false,
  "speed": true,
  "leech": false,
  "avoidance": false,
  "item_ids": [204966, 204920]
}
```

<img width="460" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/1a7250be-e1fe-41f9-b056-a2dc3cfd3abe">


If we change this and also set `"sockets": true` then it will show items over an ilvl of 360 with a speed stat or a socket:

```json
{
  "ilvl": 424,
  "buyout": 1000,
  "sockets": true,
  "speed": true,
  "leech": false,
  "avoidance": false,
  "item_ids": [204948, 204951, 204965]
}
```

<img width="353" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/53418363-caa7-4a71-b388-a270aef464eb">


You can also remove the `item_ids` or leave it empty to snipe for all items at that ilvl (warning this may spam so many messages it breaks your webhook, if that happens just make a new webhook):

```json
{
  "ilvl": 424,
  "buyout": 1000,
  "sockets": false,
  "speed": false,
  "leech": false,
  "avoidance": false
}
```

If you want to set specific snipes for multiple different items with different prices or ilvls then you can set a list and give it to `DESIRED_ILVL_LIST`:

```json
[
  {"ilvl": 457, "buyout":175001, "sockets": false, "speed": false, "leech": false, "avoidance": false,"item_ids": [208420]},
  {"ilvl": 470, "buyout": 220001, "sockets": true, "speed": false, "leech": true, "avoidance": true,"item_ids": [208426, 208428, 208431]},
  {"ilvl": 483, "buyout": 1200001, "sockets": false, "speed": false, "leech": true, "avoidance": false,"item_ids": [208426, 208427]}
]
```
