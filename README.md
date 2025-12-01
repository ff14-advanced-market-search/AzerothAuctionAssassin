# Azeroth Auction Assassin

A super fast Blizzard AH sniper created by Saddlebag Exchange. Version 2.0 of our [MEGA-ALERTS](https://github.com/ff14-advanced-market-search/mega-alerts)

This tool enables you to quickly find the most amazing deals **across all realms within your region**, notifying you of the lowest prices for any item you're interested in purchasing just seconds after the Blizzard AH API data becomes available.

[AAA dev docs](https://deepwiki.com/ff14-advanced-market-search/AzerothAuctionAssassin)

# [Download latest release here](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases/latest)

[Older Versions available here](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/releases)

If the EXE doesnt install right try the [Installation with python](https://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Install-with-Python).


# Video Guides

#### How to Install

[![How to install](https://img.youtube.com/vi/BbP7NTPohIU/0.jpg)](https://www.youtube.com/watch?v=BbP7NTPohIU)

#### How to Make Snipe Lists

[<img width="500" alt="Screenshot 2025-01-12 at 12 31 57 PM" src="https://github.com/user-attachments/assets/3b96a1f0-91a9-4e13-a86a-f255ce8c1ae9" />](https://www.youtube.com/watch?v=7mtAEN6HUN0)

#### AAA 2.0.0 UI

[<img width="500" alt="Saddlebag-Gold-Capped" src="https://github.com/user-attachments/assets/649eced4-09ef-49f3-9da2-2259a3ef5f41" />](https://www.youtube.com/watch?v=uBrrO8rLDSA)

# Desktop GUI 

<img width="500" alt="image" src="https://github.com/user-attachments/assets/ba8d087e-b5bc-4229-9033-9f39d071a868" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/6f1ee039-b39a-48a3-8304-48efbbdb115d" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/900ed28d-f134-460b-8632-ca168e956e88" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/60ee2d8f-2d66-489f-8025-3fb35dd12caa" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/1db130d9-f8bc-4908-8501-d1c0b902251d" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/e508a8ab-1849-4781-8f87-2b46fc67334f" />


# Alert Example

<img width="500" alt="image" src="https://github.com/user-attachments/assets/6982a201-a7d5-41e8-b8cf-9127356c5ba1" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/6c7fbc5d-893c-4126-aa8c-9d402c744dd9" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/37b6ccd2-5811-47e2-8feb-526c9ad60e44" />

<img width="500" alt="image" src="https://github.com/user-attachments/assets/de09ccca-6158-428f-91a1-037a0747976d" />

Old message format, but cheap Lariat Sniping from dragonflight sniping the most valuable recipes for 1/10th normal cost!

<img width="601" alt="image" src="https://user-images.githubusercontent.com/17516896/224507162-53513e8a-69ab-41e2-a5d5-ea4e51a9fc89.png">


# Node GUI (Electron)

Prefer to avoid the PyQt desktop UI? A lightweight Node/Electron GUI manages the same JSON configs and can launch the scanner.

- Requires Node 18+. Run with `npm start` (downloads Electron on first run).
- Edit `mega_data.json`, desired item/pet targets, ilvl rules, and pet ilvl rules with structured forms.
- Uses the files in `AzerothAuctionAssassinData/` (creates them if missing) and uses `src/mega_alerts.ts` instead of `mega_alerts.py` for scanning.

```bash
npm install
npm start
# if it doesn't start 
#  rm -rf node_modules/
```

**To build exe:**

Mac:

```bash
npm run build:mac
open "dist-electron/mac/Azeroth Auction Assassin.app"
```

Win:

```powershell
npm run build:win
.\dist-electron\"Azeroth Auction Assassin Setup 2.0.0.exe"
```

# Description 

We support all game modes including: 
- Retail
- Classic (will be available when blizzard fixes their api)
- Season of Discovery Classic (will be available when blizzard fixes their api)

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
