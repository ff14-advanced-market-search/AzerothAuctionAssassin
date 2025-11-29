# Azeroth Auction Assassin

A super fast Blizzard AH sniper created by Saddlebag Exchange. Version 2.0 of our [MEGA-ALERTS](https://github.com/ff14-advanced-market-search/mega-alerts)

This tool enables you to quickly find the most amazing deals **across all realms within your region**, notifying you of the lowest prices for any item you're interested in purchasing just seconds after the Blizzard AH API data becomes available.

[AAA dev docs](https://deepwiki.com/ff14-advanced-market-search/AzerothAuctionAssassin)

# [Download latest release here](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases/latest)

[Older Versions available here](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases)

If the EXE doesnt install right try the [Installation with python](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Install-with-Python).


# Video Guides

[![How to install](https://img.youtube.com/vi/BbP7NTPohIU/0.jpg)](https://www.youtube.com/watch?v=BbP7NTPohIU)

[<img width="500" alt="Screenshot 2025-01-12 at 12 31 57 PM" src="https://github.com/user-attachments/assets/3b96a1f0-91a9-4e13-a86a-f255ce8c1ae9" />](https://www.youtube.com/watch?v=7mtAEN6HUN0)

# Node GUI (Electron)

Prefer to avoid the PyQt desktop UI? A lightweight Node/Electron GUI manages the same JSON configs and can launch the scanner.

- Requires Node 18+. Run with `npm start` (downloads Electron on first run).
- Edit `mega_data.json`, desired item/pet targets, ilvl rules, and pet ilvl rules with structured forms.
- Uses the files in `AzerothAuctionAssassinData/` (creates them if missing) and uses `src/mega_alerts.ts` instead of `mega_alerts.py` for scanning.

```
npm install
npm start
# if it doesnt start 
#	rm -rf node_modules/
````

**To build exe:**

Mac:

```bash
npm run build:mac
open "dist-electron/mac/Azeroth Auction Assassin.app"
```

Win:

```bash
npm run build:win
...???...
```


# Desktop GUI 

<img width="500" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/9f1c7e15-6b07-4b56-83ba-b14b998d6ec7">

<img width="500" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/760e8491-1861-4ee5-91ef-ffcddacbac43">

# Alert Example

Latest version:

<img width="543" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/c3d93a48-9c5f-4ab4-9d9b-1dbcbcce0d4e">

Old message format, but cheap Lariat Sniping:

<img width="601" alt="image" src="https://user-images.githubusercontent.com/17516896/224507162-53513e8a-69ab-41e2-a5d5-ea4e51a9fc89.png">

# Description 

We support all game modes including: 
- Retail
- Classic
- Season of Discovery Classic

**Please dontate to our patreon so we can keep the project running.  If you need help setting it up, our creator will personally help any patreon subscribers.**

https://www.patreon.com/indopan

# [Guides](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki)

- [Video Guides](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Video-Guides)
- [Installation](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Installation-Guide)
- [How to update the app](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/How-to-update)
- [All other guides](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki)

<!-- # [Azeroth Auction Target - Automatic Recommended Snipe Lists](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Azeroth-Auction-Target-%E2%80%90-Automatic-Recommended-Snipe-Lists)

<img width="550" alt="image" src="https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/assets/17516896/653e383f-c875-4195-878c-b481c03dcb79">
 -->
