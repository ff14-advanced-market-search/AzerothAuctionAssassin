const state = {
  megaData: {},
  desiredItems: {},
  desiredPets: {},
  ilvlList: [],
  petIlvlList: [],
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
const navButtons = Array.from(document.querySelectorAll(".nav-btn"));
const itemSearchInput = document.getElementById("item-search-input");
const itemSearchBtn = document.getElementById("item-search-btn");
const itemSearchResults = document.getElementById("item-search-results");
const itemSearchStatus = document.getElementById("item-search-status");
const itemFilterInput = document.getElementById("item-filter-input");
const ilvlFilterInput = document.getElementById("ilvl-filter-input");
const petIlvlFilterInput = document.getElementById("pet-ilvl-filter-input");
const petIlvlSearchInput = document.getElementById("pet-ilvl-search-input");
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
    const name = itemNameMap[id] || id;
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
      const name = itemNameMap[id] || "";
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
  for (const rule of state.petIlvlList) {
    const name = petNameMap[rule.petID] || rule.petID;
    entries.push(`Snipe^"${name}";;0;0;0;0;0;0;0;${Math.trunc(Number(rule.price) || 0)};;#;;`);
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
      const name = itemNameMap[id] || "";
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
    const name = itemNameMap[itemId];
    return `<strong>${itemId}${name ? ` • ${name}` : ""}</strong> → ${p}`;
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
      const itemNames = itemIds.map((id) => itemNameMap[id] || "").filter(Boolean);
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
      const nm = itemNameMap[String(id)];
      return nm ? `${nm} (${id})` : id;
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
      const name = petNameMap[String(rule.petID)] || "";
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
    const name = petNameMap[String(rule.petID)];
    const row = document.createElement("div");
    row.className = "table-row";
    row.style.cursor = "pointer";
    row.innerHTML = `
      <div class="pill">#${filteredIdx + 1}</div>
      <div>Pet ${rule.petID}${name ? ` • ${name}` : ""}</div>
      <div>${rule.price} gold</div>
      <div class="bonuses">Min lvl ${rule.minLevel}, quality ${rule.minQuality}, exclude breeds: ${rule.excludeBreeds?.join(",") || "none"}</div>
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
        form.minQuality.value = rule.minQuality !== undefined ? rule.minQuality : -1;
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

async function saveMegaData() {
  const data = readMegaForm();
  state.megaData = await window.aaa.saveMegaData(data);
  renderMegaForm(state.megaData);
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
  const id = e.target.id.value.trim();
  const price = Number(e.target.price.value);
  if (!id || Number.isNaN(price)) return;
  state.desiredItems[id] = price;
  // try to keep name map
  ensureItemName(id);
  state.desiredItems = await window.aaa.saveItems(state.desiredItems);
  renderItemList();
  e.target.reset();
});

document.getElementById("ilvl-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const rule = {
    ilvl: Number(form.ilvl.value) || 0,
    max_ilvl: Number(form.max_ilvl.value) || Number(form.ilvl.value) || 0,
    buyout: Number(form.buyout.value) || 0,
    sockets: form.sockets.checked,
    speed: form.speed.checked,
    leech: form.leech.checked,
    avoidance: form.avoidance.checked,
    item_ids: parseNums(form.item_ids.value),
    bonus_lists: parseNums(form.bonus_lists.value),
    required_min_lvl: Number(form.required_min_lvl.value) || 1,
    required_max_lvl: Number(form.required_max_lvl.value) || 1000,
  };
  if (editingIlvlIndex !== null && editingIlvlIndex >= 0 && editingIlvlIndex < state.ilvlList.length) {
    state.ilvlList[editingIlvlIndex] = rule;
    editingIlvlIndex = null;
  } else {
    state.ilvlList.push(rule);
  }
  state.ilvlList = await window.aaa.saveIlvl(state.ilvlList);
  renderIlvlRules();
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.textContent = "Add rule";
  form.reset();
});

document
  .getElementById("pet-ilvl-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const rule = {
      petID: Number(form.petID.value) || 0,
      price: Number(form.price.value) || 0,
      minLevel: Number(form.minLevel.value) || 1,
      minQuality:
        form.minQuality.value === ""
          ? -1
          : Number(form.minQuality.value) || -1,
      excludeBreeds: parseNums(form.excludeBreeds.value),
    };
    if (!rule.petID || !rule.price) return;
    if (editingPetIlvlIndex !== null && editingPetIlvlIndex >= 0 && editingPetIlvlIndex < state.petIlvlList.length) {
      state.petIlvlList[editingPetIlvlIndex] = rule;
      editingPetIlvlIndex = null;
    } else {
      state.petIlvlList.push(rule);
    }
    ensurePetName(rule.petID);
    state.petIlvlList = await window.aaa.savePetIlvl(state.petIlvlList);
    renderPetIlvlRules();
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = "Add pet rule";
    form.reset();
  });

saveSettingsBtn.addEventListener("click", async () => {
  await saveMegaData();
  flashButton(saveSettingsBtn, "Saved ✓");
});

reloadBtn.addEventListener("click", async () => {
  await loadState();
  flashButton(reloadBtn, "Reloaded ✓");
});

startBtn.addEventListener("click", async () => {
  await saveMegaData();
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
});
