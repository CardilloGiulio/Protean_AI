const api = window.proteanAssistant;
const $ = (selector) => document.querySelector(selector);
const state = {
  session: null,
  reaction: "neutral",
  spritePaths: {},
  screenEnabled: false,
  inputKind: null,
  inputType: "speech",
  clickCount: 0,
  clickTimer: null,
  busy: false,
  lastScreenFingerprint: "",
  lastIdleAt: 0,
  customBackgroundUrl: "",
};

const els = {
  root: $("#assistantRoot"),
  customBackground: $("#customBackground"),
  spriteStage: $("#spriteStage"),
  sprite: $("#sprite"),
  bubble: $("#bubble"),
  bubbleText: $("#bubbleText"),
  radialMenu: $("#radialMenu"),
  inputPanel: $("#inputPanel"),
  inputTitle: $("#inputTitle"),
  interactMode: $("#interactMode"),
  assistantInput: $("#assistantInput"),
  submitInput: $("#submitInput"),
  closeInput: $("#closeInput"),
  wardrobePanel: $("#wardrobePanel"),
  wardrobeList: $("#wardrobeList"),
  closeWardrobe: $("#closeWardrobe"),
  screenStatus: $("#screenStatus"),
  statusLine: $("#statusLine"),
};

boot().catch((error) => showFatal(error.message));

async function boot() {
  bindEvents();
  state.session = await api.request("GET", "/api/assistant/session");
  state.screenEnabled = Boolean(state.session.screen_enabled);
  state.spritePaths = state.session.sprite_paths || {};
  els.root.dataset.background = state.session.background_mode || "transparent";
  if (state.session.background_mode === "custom" && state.session.has_custom_background) {
    state.customBackgroundUrl = await api.customBackground();
    els.customBackground.style.backgroundImage = `url("${state.customBackgroundUrl}")`;
  }
  renderWardrobe();
  setReaction("neutral");
  els.statusLine.textContent = `${state.session.character_name} · ${state.session.phase_name}`;
  await api.setClickThrough(true);
  await sendEvent({ event_type: "launch" });
  state.lastScreenFingerprint = "";
  state.lastIdleAt = Date.now();
  setInterval(idleTick, 4000);
}

function bindEvents() {
  document.addEventListener("mousemove", handlePointerPassThrough);
  els.spriteStage.addEventListener("click", handleSpriteClick);
  els.radialMenu.addEventListener("click", handleMenuAction);
  els.closeInput.addEventListener("click", closeInputPanel);
  els.closeWardrobe.addEventListener("click", closeWardrobePanel);
  els.submitInput.addEventListener("click", submitInput);
  els.assistantInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitInput();
    }
  });
  els.interactMode.addEventListener("click", (event) => {
    const button = event.target.closest("[data-input-type]");
    if (!button) return;
    state.inputType = button.dataset.inputType;
    els.interactMode.querySelectorAll("[data-input-type]").forEach((item) => item.classList.toggle("active", item === button));
  });
  els.wardrobeList.addEventListener("click", handleWardrobeClick);
  els.screenStatus.addEventListener("click", toggleScreenAwareness);
  api.onToggleScreen(toggleScreenAwareness);
}

function handlePointerPassThrough(event) {
  const target = document.elementFromPoint(event.clientX, event.clientY);
  const interactive = Boolean(target && target.closest(".interactive, button, textarea"));
  api.setClickThrough(!interactive).catch(() => {});
}

function handleSpriteClick() {
  state.clickCount += 1;
  clearTimeout(state.clickTimer);
  state.clickTimer = setTimeout(async () => {
    const count = state.clickCount;
    state.clickCount = 0;
    if (count === 1) {
      toggleMenu(true);
      await sendEvent({ event_type: "menu_open", screen: await currentScreen() });
    } else {
      toggleMenu(false);
      els.spriteStage.classList.remove("poke");
      void els.spriteStage.offsetWidth;
      els.spriteStage.classList.add("poke");
      await sendEvent({ event_type: "poke", poke_count: Math.min(50, count), screen: await currentScreen() });
    }
  }, 285);
}

async function handleMenuAction(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "search") {
    await openInputPanel("search");
    await sendEvent({ event_type: "search_open", screen: await currentScreen() });
    return;
  }
  if (action === "interact") {
    await openInputPanel("interact");
    await sendEvent({ event_type: "interact_open", screen: await currentScreen() });
    return;
  }
  if (action === "wardrobe") {
    els.wardrobePanel.hidden = false;
    els.inputPanel.hidden = true;
    toggleMenu(false);
    await api.setFocusable(true);
    await sendEvent({ event_type: "wardrobe_open", screen: await currentScreen() });
    return;
  }
  if (action === "quit") {
    toggleMenu(false);
    await quitAssistant();
  }
}

async function openInputPanel(kind) {
  state.inputKind = kind;
  toggleMenu(false);
  els.wardrobePanel.hidden = true;
  els.inputPanel.hidden = false;
  els.inputTitle.textContent = kind === "search" ? "Search online" : "Interact";
  els.interactMode.hidden = kind !== "interact";
  els.assistantInput.placeholder = kind === "search" ? "What do you want to find?" : "Speak to the character…";
  els.assistantInput.value = "";
  await api.setFocusable(true);
  els.assistantInput.focus();
}

async function closeInputPanel() {
  els.inputPanel.hidden = true;
  state.inputKind = null;
  await api.setFocusable(false);
  await api.setClickThrough(true);
}

async function closeWardrobePanel() {
  els.wardrobePanel.hidden = true;
  await api.setFocusable(false);
  await api.setClickThrough(true);
}

async function submitInput() {
  const value = els.assistantInput.value.trim();
  if (!value || state.busy) return;
  state.busy = true;
  try {
    const screen = await currentScreen();
    if (state.inputKind === "search") {
      await api.openSearch(value);
      await sendEvent({ event_type: "search", query: value, screen }, { alreadyBusy: true });
    } else {
      await sendEvent(
        { event_type: "interact", input_type: state.inputType, text: value, screen },
        { alreadyBusy: true },
      );
    }
    await closeInputPanel();
  } finally {
    state.busy = false;
  }
}

function renderWardrobe() {
  els.wardrobeList.replaceChildren();
  for (const item of state.session.wardrobes || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "wardrobe-item";
    button.dataset.wardrobeId = item.id;
    const ready = item.status === "ready";
    if (!ready) button.classList.add("locked");
    if (item.id === state.session.wardrobe_id) button.classList.add("current");
    button.disabled = !ready;
    const label = document.createElement("span");
    label.textContent = item.label;
    const status = document.createElement("small");
    status.textContent = ready ? (item.id === state.session.wardrobe_id ? "Wearing" : "Ready") : "🔒 Locked";
    button.append(label, status);
    els.wardrobeList.append(button);
  }
}

async function handleWardrobeClick(event) {
  const button = event.target.closest("[data-wardrobe-id]");
  if (!button || button.disabled || state.busy) return;
  state.busy = true;
  try {
    const newId = button.dataset.wardrobeId;
    if (newId === state.session.wardrobe_id) return;
    const oldId = state.session.wardrobe_id;
    const changed = await api.request("POST", "/api/assistant/session/wardrobe", { wardrobe_id: newId });
    state.session.wardrobe_id = changed.wardrobe_id;
    state.session.wardrobe_label = changed.wardrobe_label;
    state.spritePaths = changed.sprite_paths || {};
    setReaction(state.reaction);
    renderWardrobe();
    await sendEvent({
      event_type: "wardrobe_change",
      old_wardrobe_id: oldId,
      new_wardrobe_id: newId,
      screen: await currentScreen(),
    }, { alreadyBusy: true });
  } finally {
    state.busy = false;
  }
}

function toggleMenu(show) {
  els.radialMenu.hidden = !show;
  if (show) {
    els.inputPanel.hidden = true;
    els.wardrobePanel.hidden = true;
  }
}

async function toggleScreenAwareness() {
  if (state.busy) return;
  const enabling = !state.screenEnabled;
  if (enabling) {
    const accepted = window.confirm(
      "Enable screen awareness? Protean may send the active application name, window/page title, and one downscaled screenshot to your configured AI provider for an Assistant remark. Screenshots are not stored. You can pause this at any time.",
    );
    if (!accepted) return;
  }
  state.screenEnabled = !state.screenEnabled;
  els.screenStatus.classList.toggle("paused", !state.screenEnabled);
  els.screenStatus.textContent = state.screenEnabled ? "◉ Screen" : "○ Paused";
  els.screenStatus.title = state.screenEnabled ? "Pause screen awareness · Ctrl+Shift+Alt+P" : "Resume screen awareness · Ctrl+Shift+Alt+P";
  await sendEvent({ event_type: "screen_toggle", text: state.screenEnabled ? "on" : "off" });
}

async function currentScreen() {
  if (!state.screenEnabled) return { application: "", window_title: "", image_data_url: "" };
  try { return await api.captureContext(); } catch { return { application: "", window_title: "", image_data_url: "" }; }
}

async function idleTick() {
  if (!state.screenEnabled || state.busy || !els.inputPanel.hidden || !els.wardrobePanel.hidden) return;
  const screen = await currentScreen();
  const fp = fingerprint(screen);
  const now = Date.now();
  const changed = fp && fp !== state.lastScreenFingerprint;
  const periodic = now - state.lastIdleAt >= 60000;
  if (!changed && !periodic) return;
  state.lastScreenFingerprint = fp;
  state.lastIdleAt = now;
  await sendEvent({ event_type: "idle_observation", screen });
}

function fingerprint(screen) {
  return `${screen?.application || ""}|${screen?.window_title || ""}`;
}

async function sendEvent(payload, { alreadyBusy = false } = {}) {
  if (state.busy && !alreadyBusy) return null;
  if (!alreadyBusy) state.busy = true;
  try {
    const response = await api.request("POST", "/api/assistant/session/events", payload);
    state.reaction = response.reaction || "neutral";
    if (response.sprite_paths) state.spritePaths = response.sprite_paths;
    if (response.wardrobe_id) {
      state.session.wardrobe_id = response.wardrobe_id;
      state.session.wardrobe_label = response.wardrobe_label;
    }
    setReaction(state.reaction);
    showRemark(response.remark);
    return response;
  } catch (error) {
    showRemark(`(${error.message})`, true);
    return null;
  } finally {
    state.busy = false;
  }
}

function setReaction(reaction) {
  const safe = state.spritePaths[reaction] ? reaction : "neutral";
  const path = state.spritePaths[safe] || Object.values(state.spritePaths)[0];
  if (!path) return;
  els.sprite.style.opacity = "0";
  const next = `${api.baseUrl}${path}`;
  const image = new Image();
  image.onload = () => {
    els.sprite.src = next;
    requestAnimationFrame(() => { els.sprite.style.opacity = "1"; });
  };
  image.src = next;
}

let bubbleTimer = null;
function showRemark(text, error = false) {
  clearTimeout(bubbleTimer);
  els.bubbleText.textContent = text || "…";
  els.bubble.style.borderColor = error ? "rgba(215,110,110,.35)" : "";
  els.bubble.hidden = false;
  bubbleTimer = setTimeout(() => { els.bubble.hidden = true; }, Math.min(14000, Math.max(5500, (text || "").length * 70)));
}

async function quitAssistant() {
  const response = await sendEvent({ event_type: "quit", screen: await currentScreen() });
  if (response?.remark) await delay(Math.min(2800, Math.max(1400, response.remark.length * 38)));
  try { await api.request("POST", "/api/assistant/session/close"); } catch { /* close locally anyway */ }
  try { await api.openWorkspace(); } catch { /* browser can be opened manually */ }
  await api.quit();
}

function showFatal(message) {
  els.statusLine.textContent = "Assistant unavailable";
  showRemark(`(${message})`, true);
  setTimeout(() => api.quit(), 4500);
}

function delay(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
