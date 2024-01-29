# Azeroth Auction Assassin

A super fast Blizzard AH sniper created by Saddlebag Exchange. Version 2.0 of our [MEGA-ALERTS](https://github.com/ff14-advanced-market-search/mega-alerts)

This is a tool capable of alerting you on the best prices for any item you want to buy **across all realms in your region** to alert you on incredible deals seconds after Blizzard AH API data is released.

**Please dontate to our patreon so we can keep the project running.  If you need help setting it up, our creator will personally help any patreon subscribers.**

https://www.patreon.com/indopan

This amazing tool runs every time the blizzard API updates each hour and then alerts you on discord.

Blizzard only sends out new AH data to the API one time per hour, the rest of the time MEGA-ALERTS will sit and wait for new data to come out before sending more alerts. You can see what minute of each hour blizzard releases new data for your realm [here on our upload times page to find when new alerts will be sent to you.](https://saddlebagexchange.com/wow/upload-timers) 

<img src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/dbdf6a86-e560-4f59-b87e-bac7379f3b9d" width="300" height="300">

# Alert Example
<img width="601" alt="image" src="https://user-images.githubusercontent.com/17516896/224507162-53513e8a-69ab-41e2-a5d5-ea4e51a9fc89.png">

# Desktop GUI 

<img width="1639" alt="Screenshot 2024-01-26 at 12 57 32 PM" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/6e115afe-db3f-4f9f-8bed-e90fd4a6b934">

# Installation

1. Download the App: [Windows](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases/) or [Mac](https://www.dropbox.com/scl/fi/ver8u3tajekf3g75u7x7p/AzerothAuctionAssassin-Mac.zip?rlkey=7pthlwmk3hxv95ltkfwevt7lm&dl=0)

2. [Setup a discord channel with a webhook url for sending the alert messages](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) You will use this for the `MEGA_WEBHOOK_URL` later on.

3. Go to the [Saddlebag Exchange Discord](https://discord.gg/SYv8854Tbr) and generate a token with the command `/wow auctionassassintoken`.  Only available for Super Fancy and Elite [Patreon Supporters](https://www.patreon.com/indopan).

<img width="544" alt="Screenshot 2024-01-28 at 2 54 35 PM" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/87d38aeb-012b-4693-9a22-004a7de1ae11">

<img width="564" alt="Screenshot 2024-01-28 at 2 54 48 PM" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/256c05fd-1efe-4f82-add9-c8fa11169d6c">

4. Go to https://develop.battle.net/access/clients and create a client, get the blizzard oauth client and secret ids.  You will use these values for the `WOW_CLIENT_ID` and `WOW_CLIENT_SECRET` later on.

<img width="1304" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/e954289a-ccbc-4afb-9f66-897bbc68f677">

<img width="633" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/595fee57-e0db-4910-995d-5b5ae48190a2">

# Item Selection

Note the separate areas of the GUI app:

<img width="1643" alt="Screenshot 2024-01-28 at 3 58 43 PM" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/06ca3a75-1a31-4880-b2e0-2d32178aca34">

- Red for adding Battle Pets you want to snipe. (like `DESIRED_PETS` from mega-alerts)
- Green for adding regular items you want to snipe like recipes, transmog, mounts, toys, etc. (like `DESIRED_ITEMS` from mega-alerts)
- Blue for adding BOE gear with specific Item Levels and Tertiary stats. (like `DESIRED_ILVL_LIST` from mega-alerts)

If you have created these configurations before while using `mega-alerts` you can import them into the `Azeroth Auction Assassin` using the import buttons.

# Adding Regular Items to Alerts

The ItemID is a special name for each item you can sell on the auction house (not counting pets).

For example the following shows [item id 194641 for the elemental lariat](https://undermine.exchange/#us-thrall/194641).

You can find that id at the end of the undermine exchange link for the item https://undermine.exchange/#us-thrall/194641 or if you look it up on wowhead the url also has the item id https://www.wowhead.com/item=194641/design-elemental-lariat

[You can also use our item id to name lookup tool, which makes this even easier.](https://temp.saddlebagexchange.com/megaitemnames)

Setting the following and clicking on `Add Item` will add this to your snipe list. 

<img width="251" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/f6ed12af-42a4-45fb-914a-804e4f878f4d">

# Adding Battle Pets to Alerts

The PetID is a special name for each Battle Pets species id.

The following shows [pet species id 3390 for the Sophic Amalgamation](https://undermine.exchange/#us-suramar/82800-3390).

You can find that id (3390) at the end of the undermine exchange link for the item next to `82800` (which is the item id for pet cages) https://undermine.exchange/#us-suramar/82800-3390.

[You can also use our pet id to name lookup tool, which makes this even easier.](https://temp.saddlebagexchange.com/itemnames)

Setting the following and clicking on `Add Pet` will add this to your snipe list.

<img width="261" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/976f23d8-5c42-438a-9d84-1695b4eec387">

# Adding BOE Sniping for ILVL and Tertiary stats

If you want to snipe based on ilvl, leech, speed, avoidance or sockets then you can check out the last section of our app. 

Here you can create configurations similar to the following inside the app:

<img width="644" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/9493bfc2-15d4-464b-8aa3-d6fbae0aeae6">

This will produce alerts similar to the following:

<img width="680" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/722e828d-fdbf-485e-82b5-b8bc08827e3a">

This example looks for 2 different items with over an ilvl of 360 with a speed stat because `"speed": true`:

<img width="647" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/b2cc91e3-1315-4f21-991c-281d379bf6b4">

<img width="460" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/1a7250be-e1fe-41f9-b056-a2dc3cfd3abe">


If we change this and also set `"sockets": true` then it will show items over an ilvl of 360 with a speed stat and a socket:

<img width="653" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/f1e80777-b88f-4a6d-92fe-c90e786d9783">


<img width="353" alt="image" src="https://github.com/ff14-advanced-market-search/mega-alerts/assets/17516896/53418363-caa7-4a71-b388-a270aef464eb">


You can also remove the `item_ids` or leave it empty to snipe for all items at that ilvl (warning this may spam so many messages it breaks your webhook, if that happens just make a new webhook):

<img width="648" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/b7dc7078-a83e-4bf6-9fbd-042ab6993b35">

Note that this is all going to a list so you can make as many different combinations and configurations for different items at different stat and ilvls that you want!

# How to run the alerts

Once you setup your data and add some pets, items or BOE by ilvl and stats then just save your inputs and hit start!

<img width="1639" alt="Screenshot 2024-01-26 at 12 57 32 PM" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/6e115afe-db3f-4f9f-8bed-e90fd4a6b934">

You will need the following to run AAA:

- `MEGA_WEBHOOK_URL`
- `WOW_CLIENT_ID`
- `WOW_CLIENT_SECRET`
- `WOW_REGION` either `EU` or `NA`
- Then for your snipe method you must provide at least one correct json data for `DESIRED_ITEMS`, `DESIRED_PETS` or `DESIRED_ILVL`

We also have the following **optional** env vars you can add in to change alert behavior, but you dont need to as all have default values when not manually set:
- `DEBUG=true` This will instantly trigger a scan on all realms against your inputs, this will only run once and then exit the script or container so use it to debug and make sure your data is working.
- `SHOW_BID_PRICES=true` Bid prices below your price limit will also be shown (default false)
- `WOWHEAD_LINK=true` Uses wowhead links instead of undermine and shows pictures, but the message length will be longer (default false)
- `SCAN_TIME_MIN=-1` increase or decrease the minutes before or at the data update time to start scanning (default to keep scanning 1 min after the data updates).
- `SCAN_TIME_MAX=1` increase or decrease the minutes after the data updates to stop scanning (default to keep scanning 3 min after the data updates).
- `MEGA_THREADS=100` increase or decrease the threadcount (default to scan 48 realms at once)(more threads = faster scans, but doing more threads then realms is pointless).
- `REFRESH_ALERTS=false` if set to false then you will not see the same alert more than once (default true)
- `NO_RUSSIAN_REALMS=true` set this to true if you are on EU and do not want to get alerts from russian realms
- `IMPORTANT_EMOJI=🔥` changes the separators from `====` to whatever emoji you set. 

# How to update versions

wip
