const state = {
  megaData: {},
  desiredItems: {},
  desiredPets: {},
  ilvlList: [],
  petIlvlList: [],
  realmLists: {},
  processRunning: false,
};

const megaForm = document.getElementById("mega-form");
const itemList = document.getElementById("item-list");
const ilvlTable = document.getElementById("ilvl-table");
const petIlvlTable = document.getElementById("pet-ilvl-table");
const logPanel = document.getElementById("log-panel");
const processState = document.getElementById("process-state");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const reloadBtn = document.getElementById("reload-btn");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const backBtn = document.getElementById("back-btn");
const forwardBtn = document.getElementById("forward-btn");
const navButtons = Array.from(document.querySelectorAll(".nav-btn"));
const itemSearchInput = document.getElementById("item-search-input");
const itemSearchBtn = document.getElementById("item-search-btn");
const itemSearchResults = document.getElementById("item-search-results");
const itemSearchStatus = document.getElementById("item-search-status");
const itemFilterInput = document.getElementById("item-filter-input");
const ilvlFilterInput = document.getElementById("ilvl-filter-input");
const petIlvlFilterInput = document.getElementById("pet-ilvl-filter-input");
const petIlvlSearchInput = document.getElementById("pet-ilvl-search-input");
const realmList = document.getElementById("realm-list");
const realmForm = document.getElementById("realm-form");
const realmRegionSelect = document.getElementById("realm-region-select");
const realmNameInput = document.getElementById("realm-name-input");
const realmIdInput = document.getElementById("realm-id-input");
const realmFilterInput = document.getElementById("realm-filter-input");
const resetRealmBtn = document.getElementById("reset-realm-btn");
const removeRealmBtn = document.getElementById("remove-realm-btn");
const resetSettingsBtn = document.getElementById("reset-settings-btn");
const resetItemsBtn = document.getElementById("reset-items-btn");
const resetIlvlBtn = document.getElementById("reset-ilvl-btn");
const resetPetsBtn = document.getElementById("reset-pets-btn");
const petIlvlSearchBtn = document.getElementById("pet-ilvl-search-btn");
const petIlvlSearchResults = document.getElementById("pet-ilvl-search-results");
const petIlvlSearchStatus = document.getElementById("pet-ilvl-search-status");
const ilvlSearchInput = document.getElementById("ilvl-search-input");
const ilvlSearchBtn = document.getElementById("ilvl-search-btn");
const ilvlSearchResults = document.getElementById("ilvl-search-results");
const ilvlSearchStatus = document.getElementById("ilvl-search-status");
const itemSearchSuggest = document.getElementById("item-search-suggest");
const petIlvlSearchSuggest = document.getElementById("pet-ilvl-search-suggest");
const ilvlSearchSuggest = document.getElementById("ilvl-search-suggest");
const importConfigBtn = document.getElementById("import-config-btn");
const exportConfigBtn = document.getElementById("export-config-btn");
const importItemsBtn = document.getElementById("import-items-btn");
const exportItemsBtn = document.getElementById("export-items-btn");
const importIlvlBtn = document.getElementById("import-ilvl-btn");
const exportIlvlBtn = document.getElementById("export-ilvl-btn");
const importPetIlvlBtn = document.getElementById("import-pet-ilvl-btn");
const exportPetIlvlBtn = document.getElementById("export-pet-ilvl-btn");
const pasteConfigBtn = document.getElementById("paste-config-btn");
const copyConfigBtn = document.getElementById("copy-config-btn");
const pasteItemsBtn = document.getElementById("paste-items-btn");
const copyItemsBtn = document.getElementById("copy-items-btn");
const pastePBSItemsBtn = document.getElementById("paste-pbs-items-btn");
const copyPBSItemsBtn = document.getElementById("copy-pbs-items-btn");
const pasteIlvlBtn = document.getElementById("paste-ilvl-btn");
const copyIlvlBtn = document.getElementById("copy-ilvl-btn");
const pastePBSIlvlBtn = document.getElementById("paste-pbs-ilvl-btn");
const copyPBSIlvlBtn = document.getElementById("copy-pbs-ilvl-btn");
const pastePetIlvlBtn = document.getElementById("paste-pet-ilvl-btn");
const copyPetIlvlBtn = document.getElementById("copy-pet-ilvl-btn");
const pastePBSPetIlvlBtn = document.getElementById("paste-pbs-pet-ilvl-btn");
const copyPBSPetIlvlBtn = document.getElementById("copy-pbs-pet-ilvl-btn");
let itemNameMap = {};
let petNameMap = {};

let itemSearchCache = null;
let itemSearchLoading = false;
let petSearchCache = null;
let petSearchLoading = false;

let editingIlvlIndex = null;
let editingPetIlvlIndex = null;

/**
 * Clear ilvl form and reset to "add new" mode
 */
function clearIlvlForm() {
  editingIlvlIndex = null;
  const form = document.getElementById("ilvl-form");
  if (form) {
    form.reset();
    form.ilvl.value = 450;
    form.max_ilvl.value = 10000;
    form.buyout.value = 100000;
    form.required_min_lvl.value = 1;
    form.required_max_lvl.value = 999;
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "Add rule";
    form.ilvl.focus();
  }
}

/**
 * Clear pet ilvl form and reset to "add new" mode
 */
/**
 * Convert pet quality integer to human-readable label
 * @param {number} quality - Quality value (-1, 0, 1, 2, or 3)
 * @returns {string} Human-readable quality label
 */
function getQualityLabel(quality) {
  const qualityMap = {
    "-1": "All",
    "0": "Poor",
    "1": "Common",
    "2": "Uncommon",
    "3": "Rare",
  };
  return qualityMap[String(quality)] || "All";
}

/**
 * Clear pet ilvl form and reset to "add new" mode
 */
function clearPetIlvlForm() {
  editingPetIlvlIndex = null;
  const form = document.getElementById("pet-ilvl-form");
  if (form) {
    form.reset();
    form.minLevel.value = 25;
    form.minQuality.value = "-1"; // Set dropdown to "All"
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "Add pet rule";
    form.petID.focus();
  }
}

/**
 * Get item name with fallback to "Unknown item name" if not found
 * @param {string|number} id - Item ID
 * @returns {string} Item name or "Unknown item name"
 */
function getItemName(id) {
  const key = String(id);
  return itemNameMap[key] || "Unknown item name";
}

function ensureItemName(id, name) {
  const key = String(id);
  if (name) {
    itemNameMap[key] = name;
    return;
  }
  if (itemNameMap[key]) return;
  if (itemSearchCache) {
    const match = itemSearchCache.find((row) => String(row.itemID) === key);
    if (match?.itemName) {
      itemNameMap[key] = match.itemName;
      return;
    }
  }
  fetchItemNames().then(() => {
    const match = itemSearchCache?.find((row) => String(row.itemID) === key);
    if (match?.itemName) itemNameMap[key] = match.itemName;
    renderItemList();
  });
}

/**
 * Get pet name with fallback to "Unknown pet name" if not found
 * @param {string|number} id - Pet ID
 * @returns {string} Pet name or "Unknown pet name"
 */
function getPetName(id) {
  const key = String(id);
  return petNameMap[key] || "Unknown pet name";
}

function ensurePetName(id, name) {
  const key = String(id);
  if (name) {
    petNameMap[key] = name;
    return;
  }
  if (petNameMap[key]) return;
  if (petSearchCache) {
    const match = petSearchCache.find((row) => String(row.itemID) === key);
    if (match?.itemName) {
      petNameMap[key] = match.itemName;
      return;
    }
  }
  fetchPetNames().then(() => {
    const match = petSearchCache?.find((row) => String(row.itemID) === key);
    if (match?.itemName) petNameMap[key] = match.itemName;
    renderPetIlvlRules();
  });
}

function setRunning(running) {
  state.processRunning = running;
  processState.textContent = running ? "AH Scan Running" : "Not Running";
  processState.style.background = running
    ? "rgba(74,210,149,0.18)"
    : "rgba(128,255,234,0.1)";
  startBtn.disabled = running;
  stopBtn.disabled = !running;
}

function showView(view) {
  document
    .querySelectorAll(".view")
    .forEach((node) =>
      node.classList.toggle("active", node.dataset.view === view)
    );
  navButtons.forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.viewTarget === view)
  );
}

function parseNums(text) {
  if (!text) return [];
  return text
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => Number(t))
    .filter((n) => !Number.isNaN(n));
}

function updateSuggestions(inputEl, suggestEl, cache) {
  const term = (inputEl.value || "").toLowerCase().trim();
  if (!cache || !cache.length) return;
  const matches = cache
    .filter((row) => row.itemName && row.itemName.toLowerCase().includes(term))
    .slice(0, 12);
  suggestEl.innerHTML = matches
    .map((row) => `<option value="${row.itemName}"></option>`)
    .join("");
}

async function handleImport(target, btn) {
  const res = await window.aaa.importJson(target);
  if (res?.error) {
    appendLog(`Import error: ${res.error}\n`);
    return;
  }
  await loadState();
  flashButton(btn, "Imported!");
}

async function handleExport(target, btn) {
  const res = await window.aaa.exportJson(target);
  if (res?.error) {
    appendLog(`Export error: ${res.error}\n`);
  } else {
    flashButton(btn, "Exported!");
  }
}

function flashButton(btn, label = "Done") {
  if (!btn) return;
  const original = btn.textContent;
  btn.textContent = label;
  btn.disabled = true;
  setTimeout(() => {
    btn.textContent = original;
    btn.disabled = false;
  }, 900);
}

/**
 * Show a toast notification message
 * @param {string} message - The message to display
 * @param {string} type - 'error' or 'success' (default: 'error')
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = "error", duration = 3000) {
  // Remove any existing toast
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast ${type === "success" ? "success" : ""}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toastSlideIn 0.3s ease-out reverse";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showPasteModal(title, placeholder, onSubmit) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  const modal = document.createElement("div");
  modal.className = "modal";
  const heading = document.createElement("div");
  heading.style.fontWeight = "700";
  heading.textContent = title;
  const ta = document.createElement("textarea");
  ta.placeholder = placeholder;
  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const cancel = document.createElement("button");
  cancel.className = "ghost";
  cancel.textContent = "Cancel";
  const apply = document.createElement("button");
  apply.className = "primary";
  apply.textContent = "Import";
  actions.appendChild(cancel);
  actions.appendChild(apply);
  modal.appendChild(heading);
  modal.appendChild(ta);
  modal.appendChild(actions);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);
  ta.focus();

  const cleanup = () => overlay.remove();
  cancel.onclick = cleanup;
  overlay.onclick = (e) => {
    if (e.target === overlay) cleanup();
  };
  apply.onclick = async () => {
    const text = ta.value;
    if (!text.trim()) return cleanup();
    await onSubmit(text);
    cleanup();
  };
}

async function handlePasteAAA(target, btn) {
  showPasteModal("Import AAA JSON", "{...}", async (raw) => {
    try {
      const parsed = JSON.parse(raw);
      if (target === "megaData") {
        state.megaData = await window.aaa.saveMegaData(parsed);
      } else if (target === "desiredItems") {
        state.desiredItems = await window.aaa.saveItems(parsed);
      } else if (target === "ilvlList") {
        state.ilvlList = await window.aaa.saveIlvl(parsed);
      } else if (target === "petIlvlList") {
        state.petIlvlList = await window.aaa.savePetIlvl(parsed);
      }
      await loadState();
      flashButton(btn, "Imported!");
    } catch (err) {
      appendLog(`Paste error: ${err}\n`);
    }
  });
}

async function handleCopyAAA(target, btn) {
  let data;
  if (target === "megaData") data = state.megaData;
  else if (target === "desiredItems") data = state.desiredItems;
  else if (target === "ilvlList") data = state.ilvlList;
  else if (target === "petIlvlList") data = state.petIlvlList;
  if (data === undefined) return;
  await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
  appendLog("Copied JSON to clipboard\n");
  flashButton(btn, "Copied!");
}

function discountPercent() {
  const val = Number(state.megaData?.DISCOUNT_PERCENT || state.megaData?.discount_percent || 10);
  if (!Number.isFinite(val)) return 10;
  return val;
}

async function handlePastePBSItems(btn) {
  showPasteModal("Import PBS items", 'Example: Snipe?"Item";;0;0;0;0;0;0;0;50000;;#;;', async (text) => {
    await fetchItemNames();
    const pbs_data = text.replace(/\r|\n/g, "").split("^");
    const pbs_prices = {};
    for (const entry of pbs_data) {
      const parts = entry.split(";;");
      if (!parts[0]) continue;
      let item_name = parts[0].trim();
      if (item_name.startsWith('"') && item_name.endsWith('"')) {
        item_name = item_name.slice(1, -1);
      }
      const price_parts = (parts[1] || "").split(";");
      const last = price_parts[price_parts.length - 1];
      const price = last && !Number.isNaN(Number(last)) ? Number(last) : null;
      pbs_prices[item_name.toLowerCase()] = price;
    }
    const tempItems = { ...state.desiredItems };
    for (const row of itemSearchCache || []) {
      const lower = row.itemName.toLowerCase();
      if (pbs_prices.hasOwnProperty(lower)) {
        const price = pbs_prices[lower];
        if (price !== null) {
          tempItems[String(row.itemID)] = price;
        } else {
          const pct = discountPercent() / 100;
          tempItems[String(row.itemID)] = Math.round(Number(row.desiredPrice || 0) * pct);
        }
      }
    }
    state.desiredItems = await window.aaa.saveItems(tempItems);
    await loadState();
    flashButton(btn, "Imported!");
  });
}

async function handleCopyPBSItems(btn) {
  await fetchItemNames();
  const entries = [];
  let first = true;
  for (const [id, price] of Object.entries(state.desiredItems)) {
    const name = getItemName(id);
    const prefix = first ? "Snipe?" : "";
    entries.push(`${prefix}"${name}";;0;0;0;0;0;0;0;${Math.trunc(Number(price))};;#;;`);
    first = false;
  }
  const out = entries.join("");
  await navigator.clipboard.writeText(out);
  appendLog("Copied PBS items string to clipboard\n");
  flashButton(btn, "Copied!");
}

async function handlePastePBSIlvl(btn) {
  showPasteModal("Import PBS ilvl string", 'Example: Snipe?"Item";;430;470;1;80;0;0;0;50000;;#;;', async (text) => {
    await fetchItemNames();
    const pbs_data = text.replace(/\r|\n/g, "").split("^");
    const rules = [...state.ilvlList];
    for (const entry of pbs_data) {
      const parts = entry.split(";;");
      if (parts.length < 2) continue;
      let item_name = parts[0].trim();
      if (item_name.startsWith('"') && item_name.endsWith('"')) {
        item_name = item_name.slice(1, -1);
      }
      const values = parts[1].split(";");
      if (values.length < 8) continue;
      if (values[0] === "0" && values[1] === "0" && values[2] === "0" && values[3] === "0") {
        continue;
      }
      const min_ilvl = Number(values[0]) || 1;
      const max_ilvl = Number(values[1]) || 10000;
      const min_level = Number(values[2]) || 1;
      const max_level = Number(values[3]) || 999;
      const price = Number(values[7]) || 0;
      const match = (itemSearchCache || []).find(
        (row) => row.itemName && row.itemName.toLowerCase() === item_name.toLowerCase()
      );
      const item_ids = match ? [Number(match.itemID)] : [];
      const rule = {
        ilvl: min_ilvl,
        max_ilvl: max_ilvl,
        buyout: price,
        sockets: false,
        speed: false,
        leech: false,
        avoidance: false,
        item_ids,
        required_min_lvl: min_level,
        required_max_lvl: max_level,
        bonus_lists: [],
        item_names: {},
        base_ilvls: {},
        base_required_levels: {},
      };
      rules.push(rule);
    }
    state.ilvlList = await window.aaa.saveIlvl(rules);
    await loadState();
    flashButton(btn, "Imported!");
  });
}

async function handleCopyPBSIlvl(btn) {
  await fetchItemNames();
  const entries = [];
  let first = true;
  for (const rule of state.ilvlList) {
    const ids = rule.item_ids && rule.item_ids.length ? rule.item_ids : [0];
    for (const id of ids) {
      const name = getItemName(id);
      const prefix = first ? "Snipe?" : "";
      entries.push(
        `${prefix}"${name}";;${rule.ilvl};${rule.max_ilvl};${rule.required_min_lvl || 0};${rule.required_max_lvl || 0};0;0;0;${Math.trunc(
          Number(rule.buyout) || 0
        )};;#;;`
      );
      first = false;
    }
  }
  const out = entries.join("");
  await navigator.clipboard.writeText(out);
  appendLog("Copied PBS ilvl string to clipboard\n");
  flashButton(btn, "Copied!");
}

async function handlePastePBSPetIlvl(btn) {
  showPasteModal("Import PBS pets", 'Example: Snipe?"Pet";;0;0;0;0;0;0;0;50000;;#;;', async (text) => {
    await fetchPetNames();
    const pbs_data = text.replace(/\r|\n/g, "").split("^");
    const rules = [...state.petIlvlList];
    for (const pet of pbs_data) {
      const parts = pet.split(";;");
      if (!parts[0]) continue;
      let pet_name = parts[0].trim();
      if (pet_name.startsWith('"') && pet_name.endsWith('"')) {
        pet_name = pet_name.slice(1, -1);
      }
      const price_parts = (parts[1] || "").split(";");
      const last = price_parts[price_parts.length - 1];
      const price = last && !Number.isNaN(Number(last)) ? Number(last) : null;
      const match = (petSearchCache || []).find(
        (row) => row.itemName && row.itemName.toLowerCase() === pet_name.toLowerCase()
      );
      if (!match) continue;
      rules.push({
        petID: Number(match.itemID),
        price: price !== null ? price : Number(match.desiredPrice || 0),
        minLevel: 1,
        minQuality: -1,
        excludeBreeds: [],
      });
    }
    state.petIlvlList = await window.aaa.savePetIlvl(rules);
    await loadState();
    flashButton(btn, "Imported!");
  });
}

async function handleCopyPBSPetIlvl(btn) {
  await fetchPetNames();
  const entries = [];
  for (let i = 0; i < state.petIlvlList.length; i++) {
    const rule = state.petIlvlList[i];
    const name = getPetName(rule.petID);
    const prefix = i === 0 ? "Snipe^" : "";
    entries.push(`${prefix}"${name}";;0;0;0;0;0;0;0;${Math.trunc(Number(rule.price) || 0)};;#;;`);
  }
  const out = entries.join("");
  await navigator.clipboard.writeText(out);
  appendLog("Copied PBS pet string to clipboard\n");
  flashButton(btn, "Copied!");
}

function renderMegaForm(data) {
  const formData = new FormData(megaForm);
  for (const [key] of formData.entries()) {
    const el = megaForm.elements[key];
    if (!el) continue;
    if (el.type === "checkbox") {
      el.checked = Boolean(data[key]);
    } else {
      el.value = data[key] ?? "";
    }
  }
}

function readMegaForm() {
  const formData = new FormData(megaForm);
  const out = {};
  for (const [key, value] of formData.entries()) {
    const el = megaForm.elements[key];
    if (el.type === "checkbox") {
      out[key] = el.checked;
    } else if (el.type === "number") {
      const num = Number(value);
      out[key] = Number.isNaN(num) ? "" : num;
    } else {
      out[key] = value;
    }
  }
  return out;
}

function renderKVList(target, data, onRemove, labelFn, onClick) {
  target.innerHTML = "";
  const entries = Object.entries(data);
  if (entries.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No entries yet.";
    li.style.color = "#90a4b8";
    target.appendChild(li);
    return;
  }
  entries.forEach(([id, price]) => {
    const li = document.createElement("li");
    const label = labelFn ? labelFn(id, price) : `<strong>${id}</strong> → ${price}`;
    const labelDiv = document.createElement("div");
    labelDiv.innerHTML = label;
    if (onClick) {
      labelDiv.style.cursor = "pointer";
      labelDiv.onclick = (e) => {
        e.stopPropagation();
        onClick(id, price);
      };
    }
    li.appendChild(labelDiv);
    const btn = document.createElement("button");
    btn.textContent = "Remove";
    btn.className = "ghost";
    btn.onclick = (e) => {
      e.stopPropagation();
      onRemove(id);
    };
    li.appendChild(btn);
    target.appendChild(li);
  });
}

function renderItemList() {
  const filterTerm = itemFilterInput ? itemFilterInput.value.toLowerCase().trim() : "";
  let filteredData = { ...state.desiredItems };
  
  if (filterTerm) {
    filteredData = {};
    Object.entries(state.desiredItems).forEach(([id, price]) => {
      const name = getItemName(id);
      const searchText = `${id} ${name}`.toLowerCase();
      if (searchText.includes(filterTerm)) {
        filteredData[id] = price;
      }
    });
  }
  
  const itemForm = document.getElementById("item-form");
  const handleItemClick = (itemId, price) => {
    if (itemForm) {
      itemForm.id.value = itemId;
      itemForm.price.value = price;
      itemForm.id.focus();
    }
  };
  
  renderKVList(itemList, filteredData, removeItem, (itemId, p) => {
    const name = getItemName(itemId);
    const itemLink = `https://www.wowhead.com/item=${itemId}`;
    return `<strong><a href="${itemLink}" target="_blank" rel="noopener noreferrer" data-wowhead="item=${itemId}">${itemId}</a> • ${name}</strong> → ${p}`;
  }, handleItemClick);
}

function renderIlvlRules() {
  ilvlTable.innerHTML = "";
  if (!state.ilvlList.length) {
    const div = document.createElement("div");
    div.className = "table-row";
    div.textContent = "No ilvl rules yet.";
    div.style.color = "#90a4b8";
    ilvlTable.appendChild(div);
    return;
  }

  const filterTerm = ilvlFilterInput ? ilvlFilterInput.value.toLowerCase().trim() : "";
  let filteredRules = state.ilvlList;

  if (filterTerm) {
    filteredRules = state.ilvlList.filter((rule) => {
      const itemIds = (rule.item_ids || []).map(String);
      const itemNames = itemIds.map((id) => getItemName(id));
      const searchText = `${itemIds.join(" ")} ${itemNames.join(" ")} ${rule.bonus_lists?.join(" ") || ""}`.toLowerCase();
      return searchText.includes(filterTerm);
    });
  }

  if (!filteredRules.length) {
    const div = document.createElement("div");
    div.className = "table-row";
    div.textContent = filterTerm ? "No rules match your filter." : "No ilvl rules yet.";
    div.style.color = "#90a4b8";
    ilvlTable.appendChild(div);
    return;
  }

  filteredRules.forEach((rule, filteredIdx) => {
    const idx = state.ilvlList.indexOf(rule);
    const names = (rule.item_ids || []).map((id) => {
      const nm = getItemName(id);
      const itemLink = `https://www.wowhead.com/item=${id}`;
      return `${nm} (<a href="${itemLink}" target="_blank" rel="noopener noreferrer" data-wowhead="item=${id}">${id}</a>)`;
    });
    const row = document.createElement("div");
    row.className = "table-row";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <div class="pill">#${filteredIdx + 1}</div>
      <div>ilvl ${rule.ilvl}-${rule.max_ilvl}</div>
      <div>${rule.buyout} gold</div>
      <div>
        ${
          rule.item_ids?.length
            ? `Items: ${names.slice(0, 5).join(", ")}${names.length > 5 ? "…" : ""}`
            : "Any items"
        }
        <div class="bonuses">Bonus IDs: ${rule.bonus_lists?.join(", ") || "Any"}</div>
        <div class="bonuses">Player lvl: ${rule.required_min_lvl}-${rule.required_max_lvl}</div>
        <div class="bonuses">Sockets:${rule.sockets ? "Y" : "N"} Speed:${rule.speed ? "Y" : "N"} Leech:${rule.leech ? "Y" : "N"} Avoid:${rule.avoidance ? "Y" : "N"}</div>
      </div>
    `;
    const button = document.createElement("button");
    button.textContent = "Remove";
    button.className = "ghost";
    button.onclick = (e) => {
      e.stopPropagation();
      removeIlvlRule(idx);
    };
    row.appendChild(button);
    
    // Make row clickable to populate form
    row.onclick = (e) => {
      if (e.target === button || e.target.closest("button")) return;
      const form = document.getElementById("ilvl-form");
      if (form) {
        editingIlvlIndex = idx;
        form.ilvl.value = rule.ilvl || 450;
        form.max_ilvl.value = rule.max_ilvl || 10000;
        form.buyout.value = rule.buyout || 100000;
        form.item_ids.value = (rule.item_ids || []).join(", ");
        form.bonus_lists.value = (rule.bonus_lists || []).join(", ");
        form.required_min_lvl.value = rule.required_min_lvl || 1;
        form.required_max_lvl.value = rule.required_max_lvl || 1000;
        form.sockets.checked = rule.sockets || false;
        form.speed.checked = rule.speed || false;
        form.leech.checked = rule.leech || false;
        form.avoidance.checked = rule.avoidance || false;
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.textContent = "Update rule";
        form.ilvl.focus();
      }
    };
    
    ilvlTable.appendChild(row);
  });
}

function renderPetIlvlRules() {
  petIlvlTable.innerHTML = "";
  if (!state.petIlvlList.length) {
    const div = document.createElement("div");
    div.className = "table-row";
    div.textContent = "No pet rules yet.";
    div.style.color = "#90a4b8";
    petIlvlTable.appendChild(div);
    return;
  }

  const filterTerm = petIlvlFilterInput ? petIlvlFilterInput.value.toLowerCase().trim() : "";
  let filteredRules = state.petIlvlList;

  if (filterTerm) {
    filteredRules = state.petIlvlList.filter((rule) => {
      const name = getPetName(rule.petID);
      const searchText = `${rule.petID} ${name}`.toLowerCase();
      return searchText.includes(filterTerm);
    });
  }

  if (!filteredRules.length) {
    const div = document.createElement("div");
    div.className = "table-row";
    div.textContent = filterTerm ? "No rules match your filter." : "No pet rules yet.";
    div.style.color = "#90a4b8";
    petIlvlTable.appendChild(div);
    return;
  }

  filteredRules.forEach((rule, filteredIdx) => {
    const idx = state.petIlvlList.indexOf(rule);
    const name = getPetName(rule.petID);
    const row = document.createElement("div");
    row.className = "table-row";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <div class="pill">#${filteredIdx + 1}</div>
      <div>Pet ${rule.petID} • ${name}</div>
      <div>${rule.price} gold</div>
      <div class="bonuses">Min lvl ${rule.minLevel}, quality ${getQualityLabel(rule.minQuality)}, exclude breeds: ${rule.excludeBreeds?.join(",") || "none"}</div>
    `;
    const button = document.createElement("button");
    button.textContent = "Remove";
    button.className = "ghost";
    button.onclick = (e) => {
      e.stopPropagation();
      removePetIlvlRule(idx);
    };
    row.appendChild(button);
    
    // Make row clickable to populate form
    row.onclick = (e) => {
      if (e.target === button || e.target.closest("button")) return;
      const form = document.getElementById("pet-ilvl-form");
      if (form) {
        editingPetIlvlIndex = idx;
        form.petID.value = rule.petID || "";
        form.price.value = rule.price || "";
        form.minLevel.value = rule.minLevel || 25;
        form.minQuality.value = rule.minQuality !== undefined ? String(rule.minQuality) : "-1";
        form.excludeBreeds.value = (rule.excludeBreeds || []).join(", ");
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.textContent = "Update pet rule";
        form.petID.focus();
      }
    };
    
    petIlvlTable.appendChild(row);
  });
}

function appendLog(line) {
  logPanel.textContent += line;
  logPanel.scrollTop = logPanel.scrollHeight;
}

async function loadState() {
  const payload = await window.aaa.loadState();
  state.megaData = payload.megaData || {};
  state.desiredItems = payload.desiredItems || {};
  state.ilvlList = payload.ilvlList || [];
  state.petIlvlList = payload.petIlvlList || [];
  setRunning(Boolean(payload.processRunning));
  renderMegaForm(state.megaData);
  renderItemList();
  renderIlvlRules();
  renderPetIlvlRules();
  await loadRealmLists();

  // attempt to hydrate name maps so existing lists show names once fetched
  fetchItemNames().then(() => {
    renderItemList();
    renderIlvlRules();
  });
  fetchPetNames().then(() => {
    renderPetIlvlRules();
  });
}

async function fetchItemNames() {
  if (itemSearchLoading) return itemSearchCache;
  if (itemSearchCache) return itemSearchCache;

  itemSearchLoading = true;
  itemSearchStatus.textContent = "Loading item names…";
  const region = state.megaData?.WOW_REGION || "EU";
  try {
    const resp = await fetch("http://api.saddlebagexchange.com/api/wow/megaitemnames", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ region, discount: 1 }),
    });
    const data = await resp.json();
    itemSearchCache = Array.isArray(data) ? data : [];
    itemNameMap = {};
    itemSearchCache.forEach((row) => {
      if (row?.itemID && row?.itemName) {
        itemNameMap[String(row.itemID)] = row.itemName;
      }
    });
    itemSearchStatus.textContent = `Loaded ${itemSearchCache.length} entries for ${region}`;
    updateSuggestions(itemSearchInput, itemSearchSuggest, itemSearchCache);
    updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, itemSearchCache);
  } catch (err) {
    console.error("Item search fetch failed", err);
    itemSearchStatus.textContent = "Failed to load items (check connection)";
    itemSearchCache = [];
  } finally {
    itemSearchLoading = false;
  }
  return itemSearchCache;
}

function renderItemSearchResults(results) {
  itemSearchResults.innerHTML = "";
  if (!results.length) {
    const div = document.createElement("div");
    div.className = "muted tiny";
    div.textContent = "No matches.";
    itemSearchResults.appendChild(div);
    return;
  }
  results.forEach((row) => {
    const div = document.createElement("div");
    div.className = "search-result";
    div.innerHTML = `
      <div>
        <div><strong>${row.itemName}</strong></div>
        <div class="meta">ID: ${row.itemID} • Recommended: ${row.desiredPrice}</div>
      </div>
    `;
    const btn = document.createElement("button");
    btn.textContent = "Use";
    btn.className = "primary";
    btn.onclick = () => {
      const form = document.getElementById("item-form");
      form.id.value = row.itemID;
      form.price.value = row.desiredPrice;
      ensureItemName(String(row.itemID), row.itemName);
      showView("items");
    };
    div.appendChild(btn);
    itemSearchResults.appendChild(div);
  });
}

async function handleItemSearch() {
  const term = (itemSearchInput.value || "").toLowerCase().trim();
  if (!term) {
    itemSearchStatus.textContent = "Enter a search term.";
    return;
  }
  const items = await fetchItemNames();
  if (!items.length) return;
  updateSuggestions(itemSearchInput, itemSearchSuggest, items);
  const matches = items
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30);
  itemSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`;
  renderItemSearchResults(matches);
}

function renderIlvlSearchResults(results) {
  ilvlSearchResults.innerHTML = "";
  if (!results.length) {
    const div = document.createElement("div");
    div.className = "muted tiny";
    div.textContent = "No matches.";
    ilvlSearchResults.appendChild(div);
    return;
  }
  results.forEach((row) => {
    const div = document.createElement("div");
    div.className = "search-result";
    div.innerHTML = `
      <div>
        <div><strong>${row.itemName}</strong></div>
        <div class="meta">ID: ${row.itemID} • Recommended: ${row.desiredPrice}</div>
      </div>
    `;
    const btn = document.createElement("button");
    btn.textContent = "Use";
    btn.className = "primary";
    btn.onclick = () => {
      const form = document.getElementById("ilvl-form");
      const current = parseNums(form.item_ids.value);
      if (!current.includes(Number(row.itemID))) {
        current.push(Number(row.itemID));
      }
      form.item_ids.value = current.join(", ");
      if (!form.buyout.value || Number(form.buyout.value) === 0) {
        form.buyout.value = row.desiredPrice;
      }
      ensureItemName(String(row.itemID), row.itemName);
      showView("ilvl");
    };
    div.appendChild(btn);
    ilvlSearchResults.appendChild(div);
  });
}

async function handleIlvlSearch() {
  const term = (ilvlSearchInput.value || "").toLowerCase().trim();
  if (!term) {
    ilvlSearchStatus.textContent = "Enter a search term.";
    return;
  }
  const items = await fetchItemNames();
  if (!items.length) return;
  updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, items);
  const matches = items
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30);
  ilvlSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`;
  renderIlvlSearchResults(matches);
}

async function fetchPetNames() {
  if (petSearchLoading) return petSearchCache;
  if (petSearchCache) return petSearchCache;

  petSearchLoading = true;
  petIlvlSearchStatus.textContent = "Loading pets…";
  const region = state.megaData?.WOW_REGION || "EU";
  try {
    const resp = await fetch("http://api.saddlebagexchange.com/api/wow/megaitemnames", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ region, discount: 1, pets: true }),
    });
    const data = await resp.json();
    petSearchCache = Array.isArray(data) ? data : [];
    petNameMap = {};
    petSearchCache.forEach((row) => {
      if (row?.itemID && row?.itemName) {
        petNameMap[String(row.itemID)] = row.itemName;
      }
    });
    petIlvlSearchStatus.textContent = `Loaded ${petSearchCache.length} pet entries for ${region}`;
  } catch (err) {
    console.error("Pet search fetch failed", err);
    petIlvlSearchStatus.textContent = "Failed to load pets (check connection)";
    petSearchCache = [];
  } finally {
    petSearchLoading = false;
  }
  return petSearchCache;
}

function renderPetSearchResults(results) {
  petIlvlSearchResults.innerHTML = "";
  if (!results.length) {
    const div = document.createElement("div");
    div.className = "muted tiny";
    div.textContent = "No matches.";
    petIlvlSearchResults.appendChild(div);
    return;
  }
  results.forEach((row) => {
    const div = document.createElement("div");
    div.className = "search-result";
    div.innerHTML = `
      <div>
        <div><strong>${row.itemName}</strong></div>
        <div class="meta">ID: ${row.itemID} • Recommended: ${row.desiredPrice}</div>
      </div>
    `;
    const btn = document.createElement("button");
    btn.textContent = "Use";
    btn.className = "primary";
    btn.onclick = () => {
      const form = document.getElementById("pet-ilvl-form");
      form.petID.value = row.itemID;
      form.price.value = row.desiredPrice;
      ensurePetName(String(row.itemID), row.itemName);
      showView("pet-ilvl");
    };
    div.appendChild(btn);
    petIlvlSearchResults.appendChild(div);
  });
}

async function handlePetSearch() {
  const term = (petIlvlSearchInput.value || "").toLowerCase().trim();
  if (!term) {
    petIlvlSearchStatus.textContent = "Enter a search term.";
    return;
  }
  const pets = await fetchPetNames();
  if (!pets.length) return;
  updateSuggestions(petIlvlSearchInput, petIlvlSearchSuggest, pets);
  const matches = pets
    .filter((x) => x.itemName && x.itemName.toLowerCase().includes(term))
    .slice(0, 30);
  petIlvlSearchStatus.textContent = `Showing ${matches.length} results for "${term}"`;
  renderPetSearchResults(matches);
}

/**
 * Validate authentication token by calling the checkmegatoken API
 * @param {string} token - The authentication token to validate
 * @returns {Promise<{valid: boolean, error?: string}>}
 */
async function validateToken(token) {
  if (!token || !token.trim()) {
    return { valid: false, error: "Please provide a valid Auction Assassin token to save data!" };
  }
  
  try {
    const response = await fetch("http://api.saddlebagexchange.com/api/wow/checkmegatoken", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ token: token.trim() }),
    });
    
    if (response.status !== 200) {
      return { 
        valid: false, 
        error: `Could not reach server, status code: ${response.status}` 
      };
    }
    
    const responseData = await response.json();
    
    if (!responseData || Object.keys(responseData).length === 0) {
      return { 
        valid: false, 
        error: "Please provide a valid Auction Assassin token to save data!" 
      };
    }
    
    if (!("succeeded" in responseData)) {
      return { 
        valid: false, 
        error: "Please provide a valid Auction Assassin token to save data!" 
      };
    }
    
    if (!responseData.succeeded) {
      return { 
        valid: false, 
        error: "Your Auction Assassin token is incorrect or expired!\n\nYou must run the bot command once every 14 days to get a new token." 
      };
    }
    
    return { valid: true };
  } catch (err) {
    return { 
      valid: false, 
      error: `Request error: ${err.message || String(err)}` 
    };
  }
}

async function saveMegaData(skipValidation = false) {
  const data = readMegaForm();
  
  if (!skipValidation) {
    // Validate required string fields
    const requiredFields = {
      "MEGA_WEBHOOK_URL": { value: (data.MEGA_WEBHOOK_URL || "").trim(), field: megaForm.MEGA_WEBHOOK_URL, label: "Discord Webhook URL" },
      "WOW_CLIENT_ID": { value: (data.WOW_CLIENT_ID || "").trim(), field: megaForm.WOW_CLIENT_ID, label: "WoW Client ID" },
      "WOW_CLIENT_SECRET": { value: (data.WOW_CLIENT_SECRET || "").trim(), field: megaForm.WOW_CLIENT_SECRET, label: "WoW Client Secret" },
    };
    
    for (const [key, { value, field, label }] of Object.entries(requiredFields)) {
      if (!value) {
        const errorMsg = `${label} cannot be empty.`;
        showToast(errorMsg, "error");
        field?.focus();
        return false;
      }
      if (value.length < 20) {
        const errorMsg = `${label} value is invalid. Contact the devs on discord.`;
        showToast(errorMsg, "error");
        field?.focus();
        return false;
      }
    }
    
    // Validate that Client ID and Secret are not the same
    if (requiredFields.WOW_CLIENT_ID.value === requiredFields.WOW_CLIENT_SECRET.value) {
      const errorMsg = "Client ID and Secret cannot be the same value. Read the wiki:\n\nhttps://github.com/ff14-advanced-market-search/AzerothAuctionAssassin/wiki/Installation-Guide#4-go-to-httpsdevelopbattlenetaccessclients-and-create-a-client-get-the-blizzard-oauth-client-and-secret-ids--you-will-use-these-values-for-the-wow_client_id-and-wow_client_secret-later-on";
      showToast(errorMsg, "error");
      megaForm.WOW_CLIENT_SECRET.focus();
      return false;
    }
    
    // Validate WOW_REGION
    const validRegions = ["EU", "NA", "EUCLASSIC", "NACLASSIC", "NASODCLASSIC", "EUSODCLASSIC"];
    const region = (data.WOW_REGION || "").trim();
    if (!validRegions.includes(region)) {
      const errorMsg = `WOW region must be either 'NA', 'EU', 'NACLASSIC', 'EUCLASSIC', 'EUSODCLASSIC' or 'NASODCLASSIC'.`;
      showToast(errorMsg, "error");
      megaForm.WOW_REGION.focus();
      return false;
    }
    
    // Validate all integer fields
    const integerFields = {
      "MEGA_THREADS": { value: data.MEGA_THREADS, field: megaForm.MEGA_THREADS, label: "Threads" },
      "SCAN_TIME_MIN": { value: data.SCAN_TIME_MIN, field: megaForm.SCAN_TIME_MIN, label: "Scan start offset" },
      "SCAN_TIME_MAX": { value: data.SCAN_TIME_MAX, field: megaForm.SCAN_TIME_MAX, label: "Scan end offset" },
      "DISCOUNT_PERCENT": { value: data.DISCOUNT_PERCENT, field: megaForm.DISCOUNT_PERCENT, label: "Discount vs Average" },
      "TOKEN_PRICE": { value: data.TOKEN_PRICE, field: megaForm.TOKEN_PRICE, label: "Token alert min price" },
    };
    
    for (const [key, { value, field, label }] of Object.entries(integerFields)) {
      if (value === "" || value === null || value === undefined) {
        const errorMsg = `${label} is required and must be an integer.`;
        showToast(errorMsg, "error");
        field?.focus();
        return false;
      }
      
      const numValue = Number(value);
      if (Number.isNaN(numValue) || !Number.isInteger(numValue)) {
        const errorMsg = `${label} should be an integer.`;
        showToast(errorMsg, "error");
        field?.focus();
        return false;
      }
    }
    
    // Validate discount percent range (1-99)
    const discount = Number(data.DISCOUNT_PERCENT);
    if (!(1 <= discount && discount <= 99)) {
      const errorMsg = "Discount vs Average must be between 1 and 99.";
      showToast(errorMsg, "error");
      megaForm.DISCOUNT_PERCENT.focus();
      return false;
    }
    
    // Validate authentication token
    const token = data.AUTHENTICATION_TOKEN || "";
    const tokenValidation = await validateToken(token);
    if (!tokenValidation.valid) {
      showToast(tokenValidation.error || "Invalid token", "error");
      megaForm.AUTHENTICATION_TOKEN.focus();
      return false;
    }
  }
  
  state.megaData = await window.aaa.saveMegaData(data);
  renderMegaForm(state.megaData);
  if (!skipValidation) {
    showToast("Settings saved successfully!", "success", 2000);
  }
  return true;
}

async function removeItem(id) {
  delete state.desiredItems[id];
  state.desiredItems = await window.aaa.saveItems(state.desiredItems);
  renderItemList();
}

async function removeIlvlRule(idx) {
  state.ilvlList.splice(idx, 1);
  state.ilvlList = await window.aaa.saveIlvl(state.ilvlList);
  renderIlvlRules();
}

async function removePetIlvlRule(idx) {
  state.petIlvlList.splice(idx, 1);
  state.petIlvlList = await window.aaa.savePetIlvl(state.petIlvlList);
  renderPetIlvlRules();
}

// Event wiring
document.getElementById("item-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const id = form.id.value.trim();
  const price = Number(form.price.value);
  
  // Validation
  if (!id || form.price.value === "") {
    const errorMsg = "All fields are required.";
    showToast(errorMsg, "error");
    form.id.focus();
    return;
  }
  
  if (Number.isNaN(price)) {
    const errorMsg = "Item ID and Price should be numbers.";
    showToast(errorMsg, "error");
    form.price.focus();
    return;
  }
  
  const itemIdInt = Number(id);
  if (!(1 <= itemIdInt && itemIdInt <= 500000)) {
    const errorMsg = "Item ID must be between 1 and 500000.";
    showToast(errorMsg, "error");
    form.id.focus();
    return;
  }
  
  if (!(0 <= price && price <= 10000000)) {
    const errorMsg = "Price must be between 0 and 10 million.";
    showToast(errorMsg, "error");
    form.price.focus();
    return;
  }
  
  state.desiredItems[id] = price;
  // try to keep name map
  ensureItemName(id);
  state.desiredItems = await window.aaa.saveItems(state.desiredItems);
  renderItemList();
  form.reset();
  showToast("Item saved successfully!", "success", 2000);
});

document.getElementById("ilvl-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  
  // Validation
  const ilvlStr = form.ilvl.value.trim();
  const maxIlvlStr = form.max_ilvl.value.trim();
  const buyoutStr = form.buyout.value.trim();
  
  if (!ilvlStr || !buyoutStr) {
    const errorMsg = "Both ilvl and buyout fields are required.";
    showToast(errorMsg, "error");
    form.ilvl.focus();
    return;
  }
  
  const ilvl = Number(ilvlStr);
  const maxIlvl = Number(maxIlvlStr) || 10000;
  const buyout = Number(buyoutStr);
  
  if (Number.isNaN(ilvl) || Number.isNaN(maxIlvl) || Number.isNaN(buyout)) {
    const errorMsg = "Min Ilvl, Max Ilvl, and price should be numbers. No decimals.";
    showToast(errorMsg, "error");
    form.ilvl.focus();
    return;
  }
  
  if (!(1 <= ilvl && ilvl <= 999)) {
    const errorMsg = "Ilvl must be between 1 and 999.";
    showToast(errorMsg, "error");
    form.ilvl.focus();
    return;
  }
  
  if (!(ilvl <= maxIlvl && maxIlvl <= 10000)) {
    const errorMsg = "Max Ilvl must be between Ilvl and a max of 10000.";
    showToast(errorMsg, "error");
    form.max_ilvl.focus();
    return;
  }
  
  if (!(1 <= buyout && buyout <= 10000000)) {
    const errorMsg = "Price must be between 1 and 10 million.";
    showToast(errorMsg, "error");
    form.buyout.focus();
    return;
  }
  
  // Validate item IDs if provided
  const itemIdsText = form.item_ids.value.trim();
  if (itemIdsText) {
    try {
      const itemIds = parseNums(itemIdsText);
      if (!itemIds.every(id => 1 <= id && id <= 500000)) {
        const errorMsg = "All item IDs should be between 1 and 500,000.";
        showToast(errorMsg, "error");
        form.item_ids.focus();
        return;
      }
    } catch (err) {
      const errorMsg = "Item IDs should be numbers.";
      showToast(errorMsg, "error");
      form.item_ids.focus();
      return;
    }
  }
  
  // Validate player levels
  const minLevel = Number(form.required_min_lvl.value) || 1;
  const maxLevel = Number(form.required_max_lvl.value) || 1000;
  
  if (!(1 <= minLevel && minLevel <= 999)) {
    const errorMsg = "Min level must be between 1 and 999.";
    showToast(errorMsg, "error");
    form.required_min_lvl.focus();
    return;
  }
  
  if (!(1 <= maxLevel && maxLevel <= 999)) {
    const errorMsg = "Max level must be between 1 and 999.";
    showToast(errorMsg, "error");
    form.required_max_lvl.focus();
    return;
  }
  
  if (maxLevel < minLevel) {
    const errorMsg = "Max level must be greater than or equal to Min level.";
    showToast(errorMsg, "error");
    form.required_max_lvl.focus();
    return;
  }
  
  const rule = {
    ilvl: ilvl,
    max_ilvl: maxIlvl,
    buyout: buyout,
    sockets: form.sockets.checked,
    speed: form.speed.checked,
    leech: form.leech.checked,
    avoidance: form.avoidance.checked,
    item_ids: parseNums(form.item_ids.value),
    bonus_lists: parseNums(form.bonus_lists.value),
    required_min_lvl: minLevel,
    required_max_lvl: maxLevel,
  };
  
  if (editingIlvlIndex !== null && editingIlvlIndex >= 0 && editingIlvlIndex < state.ilvlList.length) {
    state.ilvlList[editingIlvlIndex] = rule;
    editingIlvlIndex = null;
  } else {
    state.ilvlList.push(rule);
  }
  state.ilvlList = await window.aaa.saveIlvl(state.ilvlList);
  renderIlvlRules();
  clearIlvlForm();
  appendLog("Ilvl rule saved successfully\n");
  showToast("Rule saved successfully!", "success", 2000);
});

document
  .getElementById("pet-ilvl-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    
    // Validation
    const petIdStr = form.petID.value.trim();
    const priceStr = form.price.value.trim();
    const minLevelStr = form.minLevel.value.trim();
    
    if (!petIdStr || !priceStr || !minLevelStr) {
      const errorMsg = "Please set a pet level (1-25)";
      showToast(errorMsg, "error");
      form.minLevel.focus();
      return;
    }
    
    const petID = Number(petIdStr);
    const price = Number(priceStr);
    const minLevel = Number(minLevelStr);
    // Get minQuality from dropdown (already an integer string)
    const minQuality = form.minQuality.value === "" ? -1 : Number(form.minQuality.value);
    
    if (Number.isNaN(petID) || Number.isNaN(price) || Number.isNaN(minLevel) || Number.isNaN(minQuality)) {
      const errorMsg = "Pet ID, Price, and Min Level should be numbers.";
      showToast(errorMsg, "error");
      form.petID.focus();
      return;
    }
    
    if (!(1 <= petID && petID <= 10000)) {
      const errorMsg = "Pet ID must be between 1 and 10000";
      showToast(errorMsg, "error");
      form.petID.focus();
      return;
    }
    
    if (price <= 0) {
      const errorMsg = "Price must be greater than 0";
      showToast(errorMsg, "error");
      form.price.focus();
      return;
    }
    
    if (!(1 <= minLevel && minLevel <= 25)) {
      const errorMsg = "Minimum level must be between 1 and 25";
      showToast(errorMsg, "error");
      form.minLevel.focus();
      return;
    }
    
    if (!(-1 <= minQuality && minQuality <= 3)) {
      const errorMsg = "Minimum quality must be between -1 and 3";
      showToast(errorMsg, "error");
      form.minQuality.focus();
      return;
    }
    
    // Validate excluded breeds
    let excludeBreeds = [];
    if (form.excludeBreeds.value.trim()) {
      try {
        excludeBreeds = parseNums(form.excludeBreeds.value);
      } catch (err) {
        const errorMsg = "Excluded breeds should be comma-separated numbers.";
        showToast(errorMsg, "error");
        form.excludeBreeds.focus();
        return;
      }
    }
    
    const rule = {
      petID: petID,
      price: price,
      minLevel: minLevel,
      minQuality: minQuality,
      excludeBreeds: excludeBreeds,
    };
    if (editingPetIlvlIndex !== null && editingPetIlvlIndex >= 0 && editingPetIlvlIndex < state.petIlvlList.length) {
      state.petIlvlList[editingPetIlvlIndex] = rule;
      editingPetIlvlIndex = null;
    } else {
      state.petIlvlList.push(rule);
    }
    ensurePetName(rule.petID);
    state.petIlvlList = await window.aaa.savePetIlvl(state.petIlvlList);
    renderPetIlvlRules();
    clearPetIlvlForm();
    showToast("Pet rule saved successfully!", "success", 2000);
  });

// Add event listeners for "New Item" buttons
document.getElementById("new-ilvl-btn")?.addEventListener("click", () => {
  clearIlvlForm();
});

document.getElementById("new-pet-ilvl-btn")?.addEventListener("click", () => {
  clearPetIlvlForm();
});

// Reset button handlers
resetSettingsBtn?.addEventListener("click", async () => {
  if (confirm("Reset all settings to defaults? This will clear all your current settings.")) {
    await window.aaa.resetMegaData();
    await loadState();
    flashButton(resetSettingsBtn, "Reset!");
  }
});

resetItemsBtn?.addEventListener("click", async () => {
  if (confirm("Clear all items? This will remove all items from your snipe list.")) {
    await window.aaa.resetItems();
    await loadState();
    flashButton(resetItemsBtn, "Reset!");
  }
});

resetIlvlBtn?.addEventListener("click", async () => {
  if (confirm("Clear all ilvl rules? This will remove all ilvl sniping rules.")) {
    await window.aaa.resetIlvl();
    await loadState();
    flashButton(resetIlvlBtn, "Reset!");
  }
});

resetPetsBtn?.addEventListener("click", async () => {
  if (confirm("Clear all pet rules? This will remove all pet sniping rules.")) {
    await window.aaa.resetPetIlvl();
    await loadState();
    flashButton(resetPetsBtn, "Reset!");
  }
});

saveSettingsBtn.addEventListener("click", async () => {
  const saved = await saveMegaData();
  if (saved) {
    flashButton(saveSettingsBtn, "Saved ✓");
  }
});

reloadBtn.addEventListener("click", async () => {
  await loadState();
  flashButton(reloadBtn, "Reloaded ✓");
});

// Navigation history management
function updateNavigationButtons() {
  window.aaa.canGoBack().then((canBack) => {
    if (backBtn) backBtn.disabled = !canBack;
  });
  window.aaa.canGoForward().then((canForward) => {
    if (forwardBtn) forwardBtn.disabled = !canForward;
  });
}

backBtn?.addEventListener("click", async () => {
  await window.aaa.goBack();
  updateNavigationButtons();
});

forwardBtn?.addEventListener("click", async () => {
  await window.aaa.goForward();
  updateNavigationButtons();
});

// Update navigation buttons periodically to reflect navigation state
setInterval(updateNavigationButtons, 500);

startBtn.addEventListener("click", async () => {
  // Validate and save before starting
  const saved = await saveMegaData();
  if (!saved) {
    return; // Validation failed, don't start
  }
  
  await window.aaa.runMega();
  setRunning(true);
});

stopBtn.addEventListener("click", async () => {
  await window.aaa.stopMega();
  setRunning(false);
});

itemSearchBtn.addEventListener("click", handleItemSearch);
itemSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleItemSearch();
  }
});

ilvlSearchBtn.addEventListener("click", handleIlvlSearch);
ilvlSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handleIlvlSearch();
  }
});

petIlvlSearchBtn.addEventListener("click", handlePetSearch);
petIlvlSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    handlePetSearch();
  }
});

itemSearchInput.addEventListener("input", async () => {
  if (!itemSearchCache) await fetchItemNames();
  updateSuggestions(itemSearchInput, itemSearchSuggest, itemSearchCache || []);
});
ilvlSearchInput.addEventListener("input", async () => {
  if (!itemSearchCache) await fetchItemNames();
  updateSuggestions(ilvlSearchInput, ilvlSearchSuggest, itemSearchCache || []);
});
petIlvlSearchInput.addEventListener("input", async () => {
  if (!petSearchCache) await fetchPetNames();
  updateSuggestions(
    petIlvlSearchInput,
    petIlvlSearchSuggest,
    petSearchCache || []
  );
});

itemSearchInput.addEventListener("focus", () => fetchItemNames());
ilvlSearchInput.addEventListener("focus", () => fetchItemNames());
petIlvlSearchInput.addEventListener("focus", () => fetchPetNames());

// Realm list functions
function renderRealmList() {
  if (!realmList) return;
  const region = realmRegionSelect?.value || "EU";
  const realms = state.realmLists[region] || {};
  const filter = realmFilterInput?.value?.toLowerCase() || "";
  
  realmList.innerHTML = "";
  
  const entries = Object.entries(realms)
    .filter(([name, id]) => {
      if (!filter) return true;
      return name.toLowerCase().includes(filter) || String(id).includes(filter);
    })
    .sort(([a], [b]) => a.localeCompare(b));
  
  for (const [name, id] of entries) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div>Name: ${name}; ID: ${id};</div>
      <button class="remove-btn" data-name="${name}" data-id="${id}">Remove</button>
    `;
    li.onclick = (e) => {
      if (e.target.classList.contains("remove-btn")) return;
      realmNameInput.value = name;
      realmIdInput.value = id;
    };
    const removeBtn = li.querySelector(".remove-btn");
    removeBtn.onclick = (e) => {
      e.stopPropagation();
      removeRealm(name, id);
    };
    realmList.appendChild(li);
  }
}

async function loadRealmLists() {
  try {
    const lists = await window.aaa.loadRealmLists();
    state.realmLists = lists || {};
    renderRealmList();
  } catch (err) {
    console.error("Failed to load realm lists:", err);
  }
}

async function saveRealmList(region) {
  try {
    const realms = state.realmLists[region] || {};
    await window.aaa.saveRealmList(region, realms);
  } catch (err) {
    console.error("Failed to save realm list:", err);
  }
}

async function addRealm(region, name, id) {
  if (!name || !id) return;
  if (!state.realmLists[region]) {
    state.realmLists[region] = {};
  }
  state.realmLists[region][name] = Number(id);
  await saveRealmList(region);
  renderRealmList();
  realmNameInput.value = "";
  realmIdInput.value = "";
}

async function removeRealm(name, id) {
  const region = realmRegionSelect?.value || "EU";
  if (!state.realmLists[region]) return;
  delete state.realmLists[region][name];
  await saveRealmList(region);
  renderRealmList();
}

async function resetRealmList() {
  const region = realmRegionSelect?.value || "EU";
  if (!window.REALM_DATA) {
    console.error("Realm data not loaded");
    return;
  }
  const defaultList = window.REALM_DATA.getRealmListByRegion(region);
  if (!defaultList) {
    console.error(`No default list for region: ${region}`);
    return;
  }
  state.realmLists[region] = { ...defaultList };
  await saveRealmList(region);
  renderRealmList();
}

realmForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const region = formData.get("region") || "EU";
  const name = formData.get("realmName")?.trim();
  const id = formData.get("realmId");
  if (name && id) {
    await addRealm(region, name, Number(id));
  }
});

realmRegionSelect?.addEventListener("change", () => {
  renderRealmList();
});

realmFilterInput?.addEventListener("input", () => {
  renderRealmList();
});

resetRealmBtn?.addEventListener("click", () => {
  if (confirm(`Reset realm list for ${realmRegionSelect?.value || "EU"}?`)) {
    resetRealmList();
  }
});

removeRealmBtn?.addEventListener("click", () => {
  const name = realmNameInput.value.trim();
  const id = realmIdInput.value;
  if (name && id) {
    removeRealm(name, Number(id));
  }
});

importConfigBtn?.addEventListener("click", () => handleImport("megaData", importConfigBtn));
exportConfigBtn?.addEventListener("click", () => handleExport("megaData", exportConfigBtn));
pasteConfigBtn?.addEventListener("click", () => handlePasteAAA("megaData"));
copyConfigBtn?.addEventListener("click", () => handleCopyAAA("megaData", copyConfigBtn));
importItemsBtn?.addEventListener("click", () => handleImport("desiredItems", importItemsBtn));
exportItemsBtn?.addEventListener("click", () => handleExport("desiredItems", exportItemsBtn));
pasteItemsBtn?.addEventListener("click", () => handlePasteAAA("desiredItems", pasteItemsBtn));
copyItemsBtn?.addEventListener("click", () => handleCopyAAA("desiredItems", copyItemsBtn));
pastePBSItemsBtn?.addEventListener("click", () => handlePastePBSItems(pastePBSItemsBtn));
copyPBSItemsBtn?.addEventListener("click", () => handleCopyPBSItems(copyPBSItemsBtn));
itemFilterInput?.addEventListener("input", () => renderItemList());
ilvlFilterInput?.addEventListener("input", () => renderIlvlRules());
petIlvlFilterInput?.addEventListener("input", () => renderPetIlvlRules());
importIlvlBtn?.addEventListener("click", () => handleImport("ilvlList", importIlvlBtn));
exportIlvlBtn?.addEventListener("click", () => handleExport("ilvlList", exportIlvlBtn));
pasteIlvlBtn?.addEventListener("click", () => handlePasteAAA("ilvlList", pasteIlvlBtn));
copyIlvlBtn?.addEventListener("click", () => handleCopyAAA("ilvlList", copyIlvlBtn));
pastePBSIlvlBtn?.addEventListener("click", () => handlePastePBSIlvl(pastePBSIlvlBtn));
copyPBSIlvlBtn?.addEventListener("click", () => handleCopyPBSIlvl(copyPBSIlvlBtn));
importPetIlvlBtn?.addEventListener("click", () => handleImport("petIlvlList", importPetIlvlBtn));
exportPetIlvlBtn?.addEventListener("click", () => handleExport("petIlvlList", exportPetIlvlBtn));
pastePetIlvlBtn?.addEventListener("click", () => handlePasteAAA("petIlvlList", pastePetIlvlBtn));
copyPetIlvlBtn?.addEventListener("click", () => handleCopyAAA("petIlvlList", copyPetIlvlBtn));
pastePBSPetIlvlBtn?.addEventListener("click", () => handlePastePBSPetIlvl(pastePBSPetIlvlBtn));
copyPBSPetIlvlBtn?.addEventListener("click", () => handleCopyPBSPetIlvl(copyPBSPetIlvlBtn));

window.aaa.onMegaLog((line) => appendLog(line));
window.aaa.onMegaExit((code) => {
  appendLog(`\nProcess exited with code ${code}\n`);
  setRunning(false);
});

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => showView(btn.dataset.viewTarget));
});

window.addEventListener("DOMContentLoaded", async () => {
  await loadState();
  showView("home");
  updateNavigationButtons();
});
