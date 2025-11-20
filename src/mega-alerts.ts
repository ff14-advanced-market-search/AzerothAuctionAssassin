import fs from "fs";
import path from "path";
import { setTimeout as delay } from "timers/promises";
import { fetch } from "undici";
import { parentPort } from "worker_threads";

type Json = Record<string, any>;

type MegaConfig = {
  MEGA_WEBHOOK_URL: string;
  WOW_CLIENT_ID: string;
  WOW_CLIENT_SECRET: string;
  WOW_REGION: "EU" | "NA" | "EUCLASSIC" | "NACLASSIC" | "NASODCLASSIC" | "EUSODCLASSIC";
  EXTRA_ALERTS?: string;
  SHOW_BID_PRICES?: boolean | string;
  MEGA_THREADS?: number;
  WOWHEAD_LINK?: boolean;
  NO_LINKS?: boolean;
  NO_RUSSIAN_REALMS?: boolean;
  TOKEN_PRICE?: number;
  SCAN_TIME_MIN?: number;
  SCAN_TIME_MAX?: number;
  REFRESH_ALERTS?: boolean;
  DEBUG?: boolean;
  FACTION?: "all" | "horde" | "alliance" | "booty bay";
};

type IlvlRule = {
  ilvl: number;
  max_ilvl: number;
  buyout: number;
  sockets: boolean;
  speed: boolean;
  leech: boolean;
  avoidance: boolean;
  item_ids: number[];
  required_min_lvl: number;
  required_max_lvl: number;
  bonus_lists: number[];
  item_names: Record<number, string>;
  base_ilvls: Record<number, number>;
  base_required_levels: Record<number, number>;
};

type PetIlvlRule = {
  petID: number;
  price: number;
  minLevel: number;
  minQuality: number;
  excludeBreeds: number[];
};

type UploadTimer = {
  dataSetID: number;
  dataSetName: string[];
  lastUploadMinute: number;
  lastUploadTimeRaw: string;
  lastUploadUnix: number;
  region: string;
  tableName: string;
};

type Auction = any;

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "AzerothAuctionAssassinData");
const STATIC_DIR = path.join(ROOT, "StaticData");
const SADDLEBAG_URL = "http://api.saddlebagexchange.com";

function readJson<T>(p: string, fallback: T): T {
  try {
    const raw = fs.readFileSync(p, "utf8");
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function getRussianRealmIds(): number[] {
  const retail = [1602, 1604, 1605, 1614, 1615, 1623, 1923, 1925, 1928, 1929, 1922];
  const classic = [4452, 4474];
  const sod = [5280, 5285, 5829, 5830];
  return [...retail, ...classic, ...sod];
}

function createEmbed(title: string, description: string, fields: any[]) {
  return {
    title,
    description,
    color: 0x7289da,
    fields,
    footer: {
      text: new Date().toLocaleString("en-US", {
        timeZone: "UTC",
        month: "2-digit",
        day: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }),
    },
  };
}

function splitList<T>(lst: T[], maxSize: number): T[][] {
  const res: T[][] = [];
  for (let i = 0; i < lst.length; i += maxSize) res.push(lst.slice(i, i + maxSize));
  return res;
}

async function httpJson(url: string, opts: any = {}, retries = 3): Promise<any> {
  let lastErr: any;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, opts);
      if (!res.ok) {
        lastErr = new Error(`${res.status} ${res.statusText}`);
        await delay(500);
        continue;
      }
      return await res.json();
    } catch (err) {
      lastErr = err;
      await delay(500);
    }
  }
  throw lastErr;
}

async function httpBuffer(url: string, opts: any = {}, retries = 3): Promise<Buffer> {
  let lastErr: any;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, opts);
      if (!res.ok) {
        lastErr = new Error(`${res.status} ${res.statusText}`);
        await delay(500);
        continue;
      }
      const arr = new Uint8Array(await res.arrayBuffer());
      return Buffer.from(arr);
    } catch (err) {
      lastErr = err;
      await delay(500);
    }
  }
  throw lastErr;
}

async function sendDiscordEmbed(webhook: string, embed: any) {
  await fetch(webhook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ embeds: [embed] }),
  });
}

async function sendDiscordMessage(webhook: string, message: string) {
  await fetch(webhook, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: message }),
  });
}

class MegaData {
  cfg: MegaConfig;
  desiredItems: Record<number, number>;
  desiredIlvlList: IlvlRule[];
  desiredPetIlvlList: PetIlvlRule[];
  THREADS: number;
  SCAN_TIME_MIN: number;
  SCAN_TIME_MAX: number;
  REFRESH_ALERTS: boolean;
  SHOW_BIDPRICES: string;
  EXTRA_ALERTS?: string;
  NO_RUSSIAN_REALMS: boolean;
  DEBUG: boolean;
  NO_LINKS: boolean;
  TOKEN_PRICE?: number;
  WOWHEAD_LINK: boolean;
  FACTION: MegaConfig["FACTION"];
  WEBHOOK_URL: string;
  REGION: MegaConfig["WOW_REGION"];
  WOW_SERVER_NAMES: Record<string, number>;
  upload_timers: Record<number, UploadTimer> = {};
  access_token = "";
  access_token_creation_unix_time = 0;
  ITEM_NAMES: Record<number, string> = {};
  PET_NAMES: Record<number, string> = {};
  DESIRED_ILVL_NAMES: Record<number, string> = {};
  socket_ids = new Set<number>();
  leech_ids = new Set<number>();
  avoidance_ids = new Set<number>();
  speed_ids = new Set<number>();
  ilvl_addition: Record<number, number> = {};

  constructor() {
    this.cfg = readJson<MegaConfig>(path.join(DATA_DIR, "mega_data.json"), {} as any);
    this.WEBHOOK_URL = this.cfg.MEGA_WEBHOOK_URL;
    this.REGION = this.cfg.WOW_REGION;
    this.THREADS = this.normalizeInt(this.cfg.MEGA_THREADS, 48);
    this.SCAN_TIME_MIN = this.normalizeInt(this.cfg.SCAN_TIME_MIN, 1);
    this.SCAN_TIME_MAX = this.normalizeInt(this.cfg.SCAN_TIME_MAX, 3);
    this.REFRESH_ALERTS = Boolean(this.cfg.REFRESH_ALERTS);
    this.SHOW_BIDPRICES = String(this.cfg.SHOW_BID_PRICES ?? false);
    this.EXTRA_ALERTS = this.cfg.EXTRA_ALERTS;
    this.NO_RUSSIAN_REALMS = Boolean(this.cfg.NO_RUSSIAN_REALMS);
    this.DEBUG = Boolean(this.cfg.DEBUG);
    this.NO_LINKS = Boolean(this.cfg.NO_LINKS);
    this.TOKEN_PRICE =
      typeof this.cfg.TOKEN_PRICE === "number" ? this.cfg.TOKEN_PRICE : undefined;
    // classic regions set wowhead_link true in python if classic
    if (String(this.REGION).includes("CLASSIC")) {
      this.WOWHEAD_LINK = true;
      this.FACTION = this.cfg.FACTION ?? "all";
    } else {
      this.WOWHEAD_LINK = Boolean(this.cfg.WOWHEAD_LINK);
      this.FACTION = "all";
    }

    this.desiredItems = this.loadDesiredItems();
    this.desiredIlvlList = this.loadDesiredIlvlList();
    this.desiredPetIlvlList = this.loadDesiredPetIlvlList();
    this.validateSnipeLists();
    this.WOW_SERVER_NAMES = this.loadRealmNames();
    this.setBonusIds();
    this.ITEM_NAMES = this.loadItemNames();
    // PET_NAMES from saddlebags (or backup)
    this.PET_NAMES = this.loadPetNamesBackup();
    this.buildIlvlNames();
    this.upload_timers = this.loadUploadTimers();
  }

  normalizeInt(val: any, fallback: number) {
    if (typeof val === "number" && Number.isFinite(val)) return val;
    const n = Number(val);
    return Number.isFinite(n) ? n : fallback;
  }

  loadDesiredItems(): Record<number, number> {
    const raw = readJson<Record<string, number>>(
      path.join(DATA_DIR, "desired_items.json"),
      {}
    );
    const out: Record<number, number> = {};
    Object.entries(raw).forEach(([k, v]) => {
      const id = Number(k);
      if (!Number.isNaN(id)) out[id] = Number(v);
    });
    return out;
  }

  loadDesiredIlvlList(): IlvlRule[] {
    const file = path.join(DATA_DIR, "desired_ilvl_list.json");
    const list = readJson<any[]>(file, []);
    if (!Array.isArray(list) || list.length === 0) return [];

    const grouped: Record<number, number[][]> = {};
    const broad: any[] = [];
    for (const entry of list) {
      if (!entry.item_ids || entry.item_ids.length === 0) {
        broad.push(entry);
      } else {
        grouped[entry.ilvl] = grouped[entry.ilvl] || [];
        grouped[entry.ilvl].push(entry.item_ids);
      }
    }

    const rules: IlvlRule[] = [];
    const addRules = (
      ilvl: number,
      entries: any[],
      itemIds: number[],
      itemNames: Record<number, string>,
      baseIlvls: Record<number, number>,
      baseReq: Record<number, number>
    ) => {
      for (const entry of entries) {
        if (entry.ilvl !== ilvl && entry.item_ids && entry.item_ids.length > 0) continue;
        const rule: IlvlRule = {
          ilvl: entry.ilvl,
          max_ilvl: entry.max_ilvl ?? 10000,
          buyout: Number(entry.buyout),
          sockets: Boolean(entry.sockets),
          speed: Boolean(entry.speed),
          leech: Boolean(entry.leech),
          avoidance: Boolean(entry.avoidance),
          item_ids: entry.item_ids && entry.item_ids.length ? entry.item_ids : itemIds,
          required_min_lvl: entry.required_min_lvl ?? 1,
          required_max_lvl: entry.required_max_lvl ?? 1000,
          bonus_lists: entry.bonus_lists ?? [],
          item_names: {},
          base_ilvls: {},
          base_required_levels: {},
        };
        rule.item_ids.forEach((id: number) => {
          rule.item_names[id] = itemNames[id] ?? "foobar";
          rule.base_ilvls[id] = baseIlvls[id] ?? 1;
          rule.base_required_levels[id] = baseReq[id] ?? 1;
        });
        rules.push(rule);
      }
    };

    for (const [ilvlStr, groups] of Object.entries(grouped)) {
      const ilvl = Number(ilvlStr);
      const allIds = groups.flat();
      const { itemNames, itemIds, baseIlvls, baseReq } = this.getIlvlItems(ilvl, allIds);
      addRules(ilvl, list, Array.from(itemIds), itemNames, baseIlvls, baseReq);
    }

    if (broad.length) {
      const { itemNames, itemIds, baseIlvls, baseReq } = this.getIlvlItems();
      addRules(0, broad, Array.from(itemIds), itemNames, baseIlvls, baseReq);
    }

    return rules;
  }

  loadDesiredPetIlvlList(): PetIlvlRule[] {
    const file = path.join(DATA_DIR, "desired_pet_ilvl_list.json");
    const list = readJson<any[]>(file, []);
    const out: PetIlvlRule[] = [];
    for (const pet of list) {
      out.push({
        petID: Number(pet.petID),
        price: Number(pet.price),
        minLevel: Number(pet.minLevel),
        minQuality: Number(pet.minQuality ?? -1),
        excludeBreeds: (pet.excludeBreeds || []).map((b: any) => Number(b)),
      });
    }
    return out;
  }

  loadRealmNames(): Record<string, number> {
    const file = path.join(
      DATA_DIR,
      `${String(this.REGION).toLowerCase()}-wow-connected-realm-ids.json`
    );
    let realmNames = readJson<Record<string, number>>(file, {});
    if (this.NO_RUSSIAN_REALMS) {
      const russian = new Set(getRussianRealmIds());
      realmNames = Object.fromEntries(
        Object.entries(realmNames).filter(([, id]) => !russian.has(id))
      );
    }
    return realmNames;
  }

  validateSnipeLists() {
    if (
      Object.keys(this.desiredItems).length === 0 &&
      this.desiredIlvlList.length === 0 &&
      this.desiredPetIlvlList.length === 0
    ) {
      throw new Error("No snipe data found in desired_items, desired_ilvl_list, desired_pet_ilvl_list");
    }
  }

  async fetchAccessToken(): Promise<string> {
    if (this.access_token && Date.now() / 1000 - this.access_token_creation_unix_time < 20 * 60 * 60) {
      return this.access_token;
    }
    const res = await fetch("https://oauth.battle.net/token", {
      method: "POST",
      body: new URLSearchParams({ grant_type: "client_credentials" }),
      headers: {
        Authorization:
          "Basic " +
          Buffer.from(`${this.cfg.WOW_CLIENT_ID}:${this.cfg.WOW_CLIENT_SECRET}`).toString("base64"),
      },
    });
    if (!res.ok) {
      throw new Error(`Failed to get access token: ${res.status} ${await res.text()}`);
    }
    const json = (await res.json()) as any;
    if (!json.access_token) {
      throw new Error(`No access_token in response: ${JSON.stringify(json)}`);
    }
    this.access_token = json.access_token;
    this.access_token_creation_unix_time = Math.floor(Date.now() / 1000);
    return this.access_token;
  }

  async getUploadTimers(): Promise<Record<number, UploadTimer>> {
    try {
      const data = await httpJson(`${SADDLEBAG_URL}/api/wow/uploadtimers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const timers: Record<number, UploadTimer> = {};
      const russian = new Set(getRussianRealmIds());
      for (const t of data.data || []) {
        if (t.dataSetID === -1 || t.dataSetID === -2) continue;
        if (t.region !== this.REGION) continue;
        if (this.NO_RUSSIAN_REALMS && russian.has(t.dataSetID)) continue;
        timers[t.dataSetID] = {
          dataSetID: t.dataSetID,
          dataSetName: t.dataSetName,
          lastUploadMinute: t.lastUploadMinute,
          lastUploadTimeRaw: t.lastUploadTimeRaw,
          lastUploadUnix: t.lastUploadUnix,
          region: t.region,
          tableName: t.tableName,
        };
      }
      return timers;
    } catch (err) {
      console.error("Failed to load upload timers", err);
      return {};
    }
  }

  loadUploadTimers(): Record<number, UploadTimer> {
    return {};
  }

  send_discord_message(message: string) {
    return sendDiscordMessage(this.WEBHOOK_URL, message);
  }

  send_discord_embed(embed: any) {
    return sendDiscordEmbed(this.WEBHOOK_URL, embed);
  }

  get_upload_time_list() {
    return Object.values(this.upload_timers);
  }
  get_upload_time_minutes() {
    return new Set(this.get_upload_time_list().map((r) => r.lastUploadMinute));
  }
  get_realm_names(connectedRealmId: number) {
    return Object.entries(this.WOW_SERVER_NAMES)
      .filter(([, id]) => id === connectedRealmId)
      .map(([name]) => name)
      .sort();
  }

  async makeAhRequest(url: string, connectedRealmId: number) {
    const headers = { Authorization: `Bearer ${await this.fetchAccessToken()}` };
    const res = await fetch(url, { headers });
    if (res.status === 429) throw new Error("429");
    if (res.status !== 200) throw new Error(`${res.status}`);
    const data = await res.json();

    const lastMod = res.headers.get("last-modified");
    if (lastMod) {
      this.update_local_timers(connectedRealmId, lastMod);
    }
    return data;
  }

  async makeCommodityRequest() {
    const region = this.REGION;
    const endpoint =
      region === "NA"
        ? "https://us.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-us&locale=en_US"
        : "https://eu.api.blizzard.com/data/wow/auctions/commodities?namespace=dynamic-eu&locale=en_EU";
    const connectedId = region === "NA" ? -1 : -2;
    const headers = { Authorization: `Bearer ${await this.fetchAccessToken()}` };
    const res = await fetch(endpoint, { headers });
    if (res.status === 429) throw new Error("429");
    if (res.status !== 200) throw new Error(`${res.status}`);
    const data = await res.json();
    const lastMod = res.headers.get("last-modified");
    if (lastMod) this.update_local_timers(connectedId, lastMod);
    return data;
  }

  update_local_timers(dataSetID: number, lastUploadTimeRaw: string) {
    let tableName: string;
    let dataSetName: string[];
    if (dataSetID === -1 || dataSetID === -2) {
      tableName = `${this.REGION}_retail_commodityListings`;
      dataSetName = [`${this.REGION} Commodities`];
    } else {
      tableName = `${dataSetID}_singleMinPrices`;
      dataSetName = this.get_realm_names(dataSetID);
    }
    const lastUploadMinute = Number(lastUploadTimeRaw.split(":")[1]);
    const lastUploadUnix = Math.floor(new Date(lastUploadTimeRaw).getTime() / 1000);
    this.upload_timers[dataSetID] = {
      dataSetID,
      dataSetName,
      lastUploadMinute,
      lastUploadTimeRaw,
      lastUploadUnix,
      region: this.REGION,
      tableName,
    };
  }

  construct_api_url(connectedRealmId: number, endpoint: string) {
    const base_url = this.REGION.includes("NA")
      ? "https://us.api.blizzard.com"
      : "https://eu.api.blizzard.com";
    let namespace = this.REGION.includes("NA") ? "dynamic-us" : "dynamic-eu";
    const locale = this.REGION.includes("NA") ? "en_US" : "en_EU";
    if (this.REGION.includes("SOD")) {
      namespace = `dynamic-classic1x-${namespace.split("-").pop()}`;
    } else if (this.REGION.includes("CLASSIC")) {
      namespace = `dynamic-classic-${namespace.split("-").pop()}`;
    }
    return `${base_url}/data/wow/connected-realm/${connectedRealmId}/auctions${endpoint}?namespace=${namespace}&locale=${locale}`;
  }

  async get_listings_single(connectedRealmId: number): Promise<any[]> {
    if (connectedRealmId === -1 || connectedRealmId === -2) {
      const commodity: any = await this.makeCommodityRequest();
      return commodity?.auctions || [];
    }
    const endpoints: string[] = [];
    if (this.REGION.includes("CLASSIC")) {
      if (this.FACTION === "alliance") endpoints.push("/2");
      else if (this.FACTION === "horde") endpoints.push("/6");
      else if (this.FACTION === "booty bay") endpoints.push("/7");
      else endpoints.push("/2", "/6", "/7");
    } else {
      endpoints.push("");
    }
    const all: any[] = [];
    for (const ep of endpoints) {
      try {
        const url = this.construct_api_url(connectedRealmId, ep);
        const data: any = await this.makeAhRequest(url, connectedRealmId);
        if (data?.auctions) all.push(...data.auctions);
      } catch (err) {
        console.error("AH request failed", err);
      }
    }
    return all;
  }

  async get_wow_token_price() {
    let url: string;
    if (this.REGION === "NA") {
      url = "https://us.api.blizzard.com/data/wow/token/index?namespace=dynamic-us&locale=en_US";
    } else if (this.REGION === "EU") {
      url = "https://eu.api.blizzard.com/data/wow/token/index?namespace=dynamic-eu&locale=en_EU";
    } else return null;
    const headers = { Authorization: `Bearer ${await this.fetchAccessToken()}` };
    const res = await fetch(url, { headers });
    if (!res.ok) return null;
    const json: any = await res.json();
    if (!("price" in json)) return null;
    return json.price / 10000;
  }

  loadItemNames(): Record<number, string> {
    try {
      const itemNames = readJson<Record<string, string>>(
        path.join(STATIC_DIR, "item_names.json"),
        {}
      );
      const filtered: Record<number, string> = {};
      Object.entries(itemNames).forEach(([k, v]) => {
        const id = Number(k);
        if (this.desiredItems[id] !== undefined) filtered[id] = v;
      });
      return filtered;
    } catch {
      return {};
    }
  }

  loadPetNamesBackup(): Record<number, string> {
    try {
      const petNames = readJson<Record<string, string>>(
        path.join(STATIC_DIR, "pet_names.json"),
        {}
      );
      const res: Record<number, string> = {};
      Object.entries(petNames).forEach(([k, v]) => {
        const id = Number(k);
        if (!Number.isNaN(id)) res[id] = v;
      });
      return res;
    } catch {
      return {};
    }
  }

  setBonusIds() {
    try {
      const bonus = readJson<Record<string, any>>(
        path.join(STATIC_DIR, "bonuses.json"),
        {}
      );
      const socket: number[] = [];
      const speed: number[] = [];
      const leech: number[] = [];
      const avoidance: number[] = [];
      const ilvlAdd: Record<number, number> = {};
      for (const [idStr, data] of Object.entries(bonus)) {
        const id = Number(idStr);
        if (data.socket) socket.push(id);
        if (data.speed) speed.push(id);
        if (data.leech) leech.push(id);
        if (data.avoidance) avoidance.push(id);
        if (typeof data.level === "number") ilvlAdd[id] = data.level;
      }
      this.socket_ids = new Set(socket);
      this.speed_ids = new Set(speed);
      this.leech_ids = new Set(leech);
      this.avoidance_ids = new Set(avoidance);
      this.ilvl_addition = ilvlAdd;
    } catch (err) {
      console.error("Failed to load bonus ids", err);
    }
  }

  getIlvlItems(
    ilvl = 201,
    item_ids: number[] = []
  ): {
    itemNames: Record<number, string>;
    itemIds: Set<number>;
    baseIlvls: Record<number, number>;
    baseReq: Record<number, number>;
  } {
    const results = readJson<Record<string, any>>(
      path.join(STATIC_DIR, "ilvl_items.json"),
      {}
    );
    if (item_ids && item_ids.length) {
      for (const key of Object.keys(results)) {
        if (!item_ids.includes(Number(key))) {
          delete (results as any)[key];
        }
      }
    }
    const itemNames: Record<number, string> = {};
    const baseIlvls: Record<number, number> = {};
    const baseReq: Record<number, number> = {};
    for (const [k, v] of Object.entries(results)) {
      const id = Number(k);
      itemNames[id] = (v as any).itemName;
      baseIlvls[id] = (v as any).ilvl;
      baseReq[id] = (v as any).required_level;
    }
    return { itemNames, itemIds: new Set(Object.keys(itemNames).map(Number)), baseIlvls, baseReq };
  }

  buildIlvlNames() {
    this.DESIRED_ILVL_NAMES = {};
    for (const rule of this.desiredIlvlList) {
      for (const [idStr, name] of Object.entries(rule.item_names)) {
        this.DESIRED_ILVL_NAMES[Number(idStr)] = name;
      }
    }
  }
}

type AlertResult = {
  region: string;
  realmID: number;
  realmNames: string[];
  itemID?: number;
  petID?: number;
  itemlink: string;
  minPrice: number;
  buyout_prices?: string | number;
  bid_prices?: string | number;
  pet_level?: number;
  quality?: number;
  breed?: number;
  tertiary_stats?: string[];
  bonus_ids?: Set<number>;
  ilvl?: number;
  required_lvl?: number;
};

let STOP_REQUESTED = false;
if (parentPort) {
  const origLog = console.log;
  console.log = (...args) => {
    origLog(...args);
    parentPort?.postMessage({ type: "log", data: args.join(" ") });
  };
  parentPort.on("message", (msg) => {
    if (msg === "stop") {
      STOP_REQUESTED = true;
    }
  });
}

async function runAlerts(
  state: MegaData,
  progress: (msg: string) => void,
  runOnce = false
) {
  let running = true;
  const alert_record: any[] = [];
  state.upload_timers = await state.getUploadTimers();

  const pull_single_realm_data = async (connected_id: number) => {
    const auctions = await state.get_listings_single(connected_id);
    const clean = clean_listing_data(auctions, connected_id);
    if (connected_id === -1 || connected_id === -2) {
      await check_token_price();
    }
    if (!clean || clean.length === 0) return;

    const russian = new Set(getRussianRealmIds());
    const suffix =
      clean[0].realmID && russian.has(clean[0].realmID) ? " **(RU)**\n" : "\n";
    const is_russian_realm =
      clean[0].realmID && russian.has(clean[0].realmID) ? "**(Russian Realm)**" : "";

    const embed_fields: any[] = [];
    for (const auction of clean) {
      if (!running) break;
      let id_msg = "";
      let embed_name = "";
      let saddlebag_link_id: number;
      if ("itemID" in auction) {
        saddlebag_link_id = (auction as any).itemID;
        if ("tertiary_stats" in auction) {
          const item_name = state.DESIRED_ILVL_NAMES[(auction as any).itemID];
          embed_name = item_name ?? "Unknown Item";
          id_msg += "`itemID:` " + (auction as any).itemID + "\n";
          id_msg += "`ilvl:` " + (auction as any).ilvl + "\n";
          if ((auction as any).tertiary_stats) {
            id_msg += "`tertiary_stats:` " + (auction as any).tertiary_stats + "\n";
          }
          if ("required_lvl" in auction && (auction as any).required_lvl !== null) {
            id_msg += "`required_lvl:` " + (auction as any).required_lvl + "\n";
          }
          if ("bonus_ids" in auction) {
            id_msg += "`bonus_ids:` " + JSON.stringify(Array.from((auction as any).bonus_ids)) + "\n";
          }
        } else if (state.ITEM_NAMES[(auction as any).itemID]) {
          embed_name = state.ITEM_NAMES[(auction as any).itemID];
          id_msg += "`itemID:` " + (auction as any).itemID + "\n";
        } else {
          embed_name = "Unknown Item";
          id_msg += "`itemID:` " + (auction as any).itemID + "\n";
        }
      } else {
        saddlebag_link_id = (auction as any).petID;
        embed_name =
          state.PET_NAMES[(auction as any).petID] !== undefined
            ? state.PET_NAMES[(auction as any).petID]
            : "Unknown Pet";
        id_msg += "`petID:` " + (auction as any).petID + "\n";
        if ("pet_level" in auction) id_msg += "`pet_level:` " + (auction as any).pet_level + "\n";
        if ("quality" in auction) id_msg += "`quality:` " + (auction as any).quality + "\n";
        if ("breed" in auction) id_msg += "`breed:` " + (auction as any).breed + "\n";
      }

      let message = id_msg;
      const link_label = state.WOWHEAD_LINK && "itemID" in auction ? "Wowhead link" : "Undermine link";
      const link_url =
        state.WOWHEAD_LINK && "itemID" in auction
          ? `https://www.wowhead.com/item=${(auction as any).itemID}`
          : (auction as any).itemlink;
      if (!state.NO_LINKS) {
        message += `[${link_label}](${link_url})\n`;
        message += `[Saddlebag link](https://saddlebagexchange.com/wow/item-data/${saddlebag_link_id})\n`;
        message += `[Where to Sell](https://saddlebagexchange.com/wow/export-search?itemId=${saddlebag_link_id})\n`;
      }
      const price_type = "bid_prices" in auction ? "bid_prices" : "buyout_prices";
      message += "`" + price_type + "`: " + (auction as any)[price_type] + "\n";

      if (!alert_record.includes(auction)) {
        embed_fields.push({ name: embed_name, value: message, inline: true });
        alert_record.push(auction);
      } else {
        console.log("Already sent this alert", auction);
      }
    }

    if (embed_fields.length) {
      let desc = `**region:** ${state.REGION}\n`;
      desc += `**realmID:** ${clean[0].realmID ?? ""} ${is_russian_realm}\n`;
      desc += `**realmNames:** ${clean[0].realmNames}${suffix}`;
      for (const chunk of splitList(embed_fields, 10)) {
        const item_embed = createEmbed(`${state.REGION} SNIPE FOUND!`, desc, chunk);
        await state.send_discord_embed(item_embed);
      }
    }
  };

  async function check_token_price() {
    try {
      if (state.TOKEN_PRICE) {
        const token_price = await state.get_wow_token_price();
        if (token_price && token_price < state.TOKEN_PRICE) {
          const token_embed = createEmbed(
            `WoW Token Alert - ${state.REGION}`,
            `**Token Price:** ${token_price.toLocaleString()} gold\n**Threshold:** ${state.TOKEN_PRICE.toLocaleString()} gold\n**Region:** ${state.REGION}`,
            []
          );
          await state.send_discord_embed(token_embed);
        }
      }
    } catch (err) {
      console.error("Error checking token price", err);
    }
  }

  function results_dict(
    auction: number[],
    itemlink: string,
    connected_id: number,
    realm_names: string[],
    id: number,
    idType: "itemID" | "petID",
    priceType: "buyout" | "bid"
  ): AlertResult {
    const sorted = [...auction].sort((a, b) => a - b);
    const minPrice = sorted[0];
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice,
      [`${priceType}_prices`]: JSON.stringify(auction),
    } as AlertResult;
  }

  function ilvl_results_dict(
    auction: any,
    itemlink: string,
    connected_id: number,
    realm_names: string[],
    id: number,
    idType: "itemID",
    priceType: "buyout"
  ): AlertResult {
    const tertiary_stats = Object.entries(auction.tertiary_stats)
      .filter(([, present]) => present)
      .map(([stat]) => stat);
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice: auction[priceType],
      [`${priceType}_prices`]: auction[priceType],
      tertiary_stats,
      bonus_ids: auction.bonus_ids,
      ilvl: auction.ilvl,
      required_lvl: auction.required_lvl,
    };
  }

  function pet_ilvl_results_dict(
    auction: any,
    itemlink: string,
    connected_id: number,
    realm_names: string[],
    id: number,
    idType: "petID",
    priceType: "buyout"
  ): AlertResult {
    return {
      region: state.REGION,
      realmID: connected_id,
      realmNames: realm_names,
      [idType]: id,
      itemlink,
      minPrice: auction.buyout,
      [`${priceType}_prices`]: auction.buyout,
      pet_level: auction.current_level,
      quality: auction.quality,
      breed: auction.breed,
    };
  }

  function check_tertiary_stats_generic(
    auction: any,
    rule: IlvlRule,
    min_ilvl: number
  ) {
    if (!auction.item?.bonus_lists) return false;
    const item_bonus_ids = new Set<number>(auction.item.bonus_lists);
    const required_lvl =
      auction.item.modifiers?.find((m: any) => m.type === 9)?.value ??
      rule.base_required_levels[auction.item.id];

    const tertiary_stats = {
      sockets: intersection(item_bonus_ids, state.socket_ids),
      leech: intersection(item_bonus_ids, state.leech_ids),
      avoidance: intersection(item_bonus_ids, state.avoidance_ids),
      speed: intersection(item_bonus_ids, state.speed_ids),
    };
    const desired = {
      sockets: rule.sockets,
      leech: rule.leech,
      avoidance: rule.avoidance,
      speed: rule.speed,
    };
    if (Object.values(desired).some(Boolean)) {
      for (const [stat, want] of Object.entries(desired)) {
        if (want && !(tertiary_stats as any)[stat]) return false;
      }
    }

    const base_ilvl = rule.base_ilvls[auction.item.id];
    const ilvl_addition = [...item_bonus_ids]
      .map((b) => state.ilvl_addition[b] || 0)
      .reduce((a, b) => a + b, 0);
    const ilvl = base_ilvl + ilvl_addition;
    if (ilvl < min_ilvl) return false;
    if (ilvl > rule.max_ilvl) return false;
    if (required_lvl < rule.required_min_lvl) return false;
    if (required_lvl > rule.required_max_lvl) return false;

    if (
      rule.bonus_lists.length &&
      rule.bonus_lists[0] !== -1 &&
      setEqual(new Set(rule.bonus_lists), item_bonus_ids) === false
    ) {
      return false;
    }
    if (rule.bonus_lists.length === 1 && rule.bonus_lists[0] === -1) {
      const temp = new Set(item_bonus_ids);
      for (const bid of state.socket_ids) temp.delete(bid);
      for (const bid of state.leech_ids) temp.delete(bid);
      for (const bid of state.avoidance_ids) temp.delete(bid);
      for (const bid of state.speed_ids) temp.delete(bid);
      if (temp.size > 3) return false;
      const bad_ids = [224637];
      if (bad_ids.includes(auction.item.id)) return false;
    }

    if (!auction.buyout && auction.bid) auction.buyout = auction.bid;
    if (!auction.buyout) return false;
    const buyout = Math.round((auction.buyout / 10000) * 100) / 100;
    if (buyout > rule.buyout) return false;
    return {
      item_id: auction.item.id,
      buyout,
      tertiary_stats,
      bonus_ids: item_bonus_ids,
      ilvl,
      required_lvl,
    };
  }

  function check_pet_ilvl_stats(item: any, desired_pet_list: PetIlvlRule[]) {
    const pet_species_id = item.item.pet_species_id;
    const desired = desired_pet_list.find((p) => p.petID === pet_species_id);
    if (!desired) return null;
    const pet_level = item.item.pet_level;
    if (pet_level == null || pet_level < desired.minLevel) return null;
    if (item.item.pet_quality_id < desired.minQuality) return null;
    if (desired.excludeBreeds.includes(item.item.pet_breed_id)) return null;
    const buyout = item.buyout;
    if (buyout == null || buyout / 10000 > desired.price) return null;
    return {
      pet_species_id,
      current_level: pet_level,
      buyout: buyout / 10000,
      quality: item.item.pet_quality_id,
      breed: item.item.pet_breed_id,
    };
  }

  function clean_listing_data(auctions: Auction[], connected_id: number): AlertResult[] | undefined {
    const all_ah_buyouts: Record<number, number[]> = {};
    const all_ah_bids: Record<number, number[]> = {};
    const pet_ah_buyouts: Record<number, number[]> = {};
    const pet_ah_bids: Record<number, number[]> = {};
    const ilvl_ah_buyouts: any[] = [];
    const pet_ilvl_ah_buyouts: any[] = [];

    if (!auctions || auctions.length === 0) {
      console.log(`no listings found on ${connected_id} of ${state.REGION}`);
      return;
    }

    const add_price_to_dict = (
      price: number,
      item_id: number,
      price_dict: Record<number, number[]>
    ) => {
      if (price_dict[item_id]) {
        const gold = price / 10000;
        if (!price_dict[item_id].includes(gold)) price_dict[item_id].push(gold);
      } else {
        price_dict[item_id] = [price / 10000];
      }
    };

    for (const item of auctions) {
      const item_id = item.item?.id;
      if (!item_id) continue;

      if (item_id in state.desiredItems && item_id !== 82800) {
        if ("bid" in item && state.SHOW_BIDPRICES === "true") {
          add_price_to_dict(item.bid, item_id, all_ah_bids);
        }
        if ("buyout" in item) add_price_to_dict(item.buyout, item_id, all_ah_buyouts);
        if ("unit_price" in item) add_price_to_dict(item.unit_price, item_id, all_ah_buyouts);
      } else if (item_id === 82800) {
        if (state.desiredPetIlvlList.length) {
          const info = check_pet_ilvl_stats(item, state.desiredPetIlvlList);
          if (info) pet_ilvl_ah_buyouts.push(info);
        }
      }

      for (const desired_ilvl_item of state.desiredIlvlList) {
        if (desired_ilvl_item.item_ids.includes(item_id)) {
          const info = check_tertiary_stats_generic(item, desired_ilvl_item, desired_ilvl_item.ilvl);
          if (info) ilvl_ah_buyouts.push(info);
        }
      }
    }

    if (
      !(
        Object.keys(all_ah_buyouts).length ||
        Object.keys(all_ah_bids).length ||
        Object.keys(pet_ah_buyouts).length ||
        Object.keys(pet_ah_bids).length ||
        ilvl_ah_buyouts.length ||
        pet_ilvl_ah_buyouts.length
      )
    ) {
      console.log(`no listings found matching desires on ${connected_id} of ${state.REGION}`);
      return;
    }
    console.log(`Found matches on ${connected_id} of ${state.REGION}!!!`);
    return format_alert_messages(
      all_ah_buyouts,
      all_ah_bids,
      connected_id,
      pet_ah_buyouts,
      pet_ah_bids,
      ilvl_ah_buyouts,
      pet_ilvl_ah_buyouts
    );
  }

  function format_alert_messages(
    all_ah_buyouts: Record<number, number[]>,
    all_ah_bids: Record<number, number[]>,
    connected_id: number,
    pet_ah_buyouts: Record<number, number[]>,
    pet_ah_bids: Record<number, number[]>,
    ilvl_ah_buyouts: any[],
    pet_ilvl_ah_buyouts: any[]
  ): AlertResult[] {
    const results: AlertResult[] = [];
    const realm_names = state.get_realm_names(connected_id);
    for (const [itemIDStr, auction] of Object.entries(all_ah_buyouts)) {
      const itemID = Number(itemIDStr);
      const itemlink = create_oribos_exchange_item_link(realm_names[0], itemID, state.REGION);
      results.push(results_dict(auction, itemlink, connected_id, realm_names, itemID, "itemID", "buyout"));
    }
    for (const [itemIDStr, auction] of Object.entries(ilvl_ah_buyouts)) {
      const itemID = Number((auction as any).item_id);
      const itemlink = create_oribos_exchange_item_link(realm_names[0], itemID, state.REGION);
      results.push(
        ilvl_results_dict(auction, itemlink, connected_id, realm_names, itemID, "itemID", "buyout")
      );
    }
    if (state.SHOW_BIDPRICES === "true") {
      for (const [itemIDStr, auction] of Object.entries(all_ah_bids)) {
        const itemID = Number(itemIDStr);
        const itemlink = create_oribos_exchange_item_link(realm_names[0], itemID, state.REGION);
        results.push(results_dict(auction, itemlink, connected_id, realm_names, itemID, "itemID", "bid"));
      }
    }
    for (const auction of pet_ilvl_ah_buyouts) {
      const petID = auction.pet_species_id;
      const itemlink = create_oribos_exchange_pet_link(realm_names[0], petID, state.REGION);
      results.push(pet_ilvl_results_dict(auction, itemlink, connected_id, realm_names, petID, "petID", "buyout"));
    }
    return results;
  }

  function intersection(setA: Set<number>, setB: Set<number>) {
    for (const v of setA) if (setB.has(v)) return true;
    return false;
  }
  function setEqual(a: Set<number>, b: Set<number>) {
    if (a.size !== b.size) return false;
    for (const v of a) if (!b.has(v)) return false;
    return true;
  }

  // initial fast run across all realms
  const initialRealms = Array.from(new Set(Object.values(state.WOW_SERVER_NAMES)));
  if (initialRealms.length) {
    progress("Sending alerts!");
    await runPool(
      initialRealms.map((id) => () => pull_single_realm_data(id)),
      state.THREADS
    );
  }

  if (runOnce) return;

  while (running && !STOP_REQUESTED) {
    const current_min = new Date().getMinutes();
    if (current_min === 1 && state.REFRESH_ALERTS) {
      alert_record.length = 0;
    }
    if (!Object.keys(state.upload_timers).length) {
      state.upload_timers = await state.getUploadTimers();
    }
    let matching_realms = state
      .get_upload_time_list()
      .filter(
        (realm) =>
          realm.lastUploadMinute + state.SCAN_TIME_MIN <= current_min &&
          current_min <= realm.lastUploadMinute + state.SCAN_TIME_MAX
      )
      .map((r) => r.dataSetID);
    if (state.EXTRA_ALERTS) {
      try {
        const extra = JSON.parse(state.EXTRA_ALERTS) as number[];
        if (extra.includes(current_min)) {
          matching_realms = state.get_upload_time_list().map((r) => r.dataSetID);
        }
      } catch {}
    }

    if (matching_realms.length) {
      progress("Sending alerts!");
      await runPool(
        matching_realms.map((id) => () => pull_single_realm_data(id)),
        state.THREADS
      );
    } else {
      progress(
        `The updates will come\non min ${Array.from(state.get_upload_time_minutes()).join(
          ","
        )}\nof each hour.`
      );
      console.log(
        `Blizzard API data only updates 1 time per hour. The updates will come on minute ${Array.from(
          state.get_upload_time_minutes()
        )} of each hour. ${new Date().toISOString()} is not the update time.`
      );
      await delay(20000);
    }
  }
}

function create_oribos_exchange_pet_link(realm_name: string, pet_id: number, region: string) {
  const fixed_realm_name = realm_name.toLowerCase().replace("'", "").replace(/ /g, "-");
  const url_region = region === "NA" ? "us" : "eu";
  return `https://undermine.exchange/#${url_region}-${fixed_realm_name}/82800-${pet_id}`;
}

function create_oribos_exchange_item_link(realm_name: string, item_id: number, region: string) {
  const fixed_realm_name = realm_name.toLowerCase().replace("'", "").replace(/ /g, "-");
  const url_region = region === "NA" ? "us" : "eu";
  return `https://undermine.exchange/#${url_region}-${fixed_realm_name}/${item_id}`;
}

async function runPool(tasks: (() => Promise<any>)[], concurrency: number) {
  const results: any[] = [];
  const executing: Promise<any>[] = [];
  for (const task of tasks) {
    const p = task();
    results.push(p);
    if (concurrency <= tasks.length) {
      const e: Promise<any> = p.then(() => {
        executing.splice(executing.indexOf(e), 1);
      });
      executing.push(e);
      if (executing.length >= concurrency) {
        await Promise.race(executing);
      }
    }
  }
  return Promise.all(results);
}

async function main() {
  const state = new MegaData();
  console.log(
    `Starting mega-alerts-ts for region=${state.REGION}, items=${Object.keys(
      state.desiredItems
    ).length}, ilvl rules=${state.desiredIlvlList.length}, pet ilvl rules=${state.desiredPetIlvlList.length}`
  );
  if (state.DEBUG) {
    await sendDiscordMessage(
      state.WEBHOOK_URL,
      "DEBUG MODE: starting mega alerts to run once and then exit operations"
    );
    await runAlerts(state, () => {}, true);
  } else {
    await sendDiscordMessage(
      state.WEBHOOK_URL,
      "🟢Starting mega alerts and scan all AH data instantly.🟢\n" +
        "🟢These first few messages might be old.🟢\n" +
        "🟢All future messages will release seconds after the new data is available.🟢"
    );
    await delay(1000);
    await runAlerts(state, (msg) => console.log("[progress]", msg));
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
