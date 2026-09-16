import { api, ApiError } from "./api.js";

const $ = (selector) => document.querySelector(selector);
const state = {
  authMode: "login",
  presets: null,
  preferences: null,
  provider: null,
  characters: [],
  selectedCharacter: null,
  selectedPhase: null,
  selectedScenario: null,
  chats: [],
  activeChatId: null,
  busy: false,
  openingPreviewSequence: 0,
  openingPreviewTimer: null,
  openingToken: null,
  immersionAvailability: null,
  assistantAvailability: null,
};

const els = {
  authGate: $("#authGate"),
  appShell: $("#appShell"),
  authForm: $("#authForm"),
  authTitle: $("#authTitle"),
  authDescription: $("#authDescription"),
  authSubmit: $("#authSubmit"),
  authUsername: $("#authUsername"),
  authPassword: $("#authPassword"),
  authError: $("#authError"),
  currentUser: $("#currentUser"),
  toggleLeft: $("#toggleLeft"),
  toggleRight: $("#toggleRight"),
  focusModeButton: $("#focusModeButton"),
  characterSearch: $("#characterSearch"),
  researchButton: $("#researchButton"),
  characterList: $("#characterList"),
  toneSelect: $("#toneSelect"),
  toneDescription: $("#toneDescription"),
  timelineSelect: $("#timelineSelect"),
  timelinePeriod: $("#timelinePeriod"),
  timelineDescription: $("#timelineDescription"),
  scenarioSelect: $("#scenarioSelect"),
  scenarioPreview: $("#scenarioPreview"),
  customScenarioFields: $("#customScenarioFields"),
  customScenarioName: $("#customScenarioName"),
  customScenarioWhat: $("#customScenarioWhat"),
  customScenarioWho: $("#customScenarioWho"),
  customScenarioDynamic: $("#customScenarioDynamic"),
  libraryRoot: $("#libraryRoot"),
  saveLibraryButton: $("#saveLibraryButton"),
  chatHistory: $("#chatHistory"),
  newChatButton: $("#newChatButton"),
  activeFranchise: $("#activeFranchise"),
  activeCharacterName: $("#activeCharacterName"),
  activeMedium: $("#activeMedium"),
  activePortrait: $("#activePortrait"),
  heroFranchise: $("#heroFranchise"),
  heroName: $("#heroName"),
  messages: $("#messages"),
  composer: $("#composer"),
  messageInput: $("#messageInput"),
  sendButton: $("#sendButton"),
  frameLabel: $("#frameLabel"),
  sceneLabel: $("#sceneLabel"),
  connectionIndicator: $("#connectionIndicator"),
  themeSelect: $("#themeSelect"),
  backgroundSelect: $("#backgroundSelect"),
  frameSelect: $("#frameSelect"),
  keyStatus: $("#keyStatus"),
  apiKeyInput: $("#apiKeyInput"),
  modelInput: $("#modelInput"),
  temperatureInput: $("#temperatureInput"),
  targetTokensInput: $("#targetTokensInput"),
  maxTokensInput: $("#maxTokensInput"),
  saveProviderButton: $("#saveProviderButton"),
  validateProviderButton: $("#validateProviderButton"),
  removeProviderButton: $("#removeProviderButton"),
  providerFeedback: $("#providerFeedback"),
  logoutButton: $("#logoutButton"),
  immersionButton: $("#immersionButton"),
  immersionStatusBadge: $("#immersionStatusBadge"),
  immersionDialog: $("#immersionDialog"),
  immersionForm: $("#immersionForm"),
  immersionCharacterLabel: $("#immersionCharacterLabel"),
  immersionTimelineSelect: $("#immersionTimelineSelect"),
  immersionToneSelect: $("#immersionToneSelect"),
  immersionScenarioSelect: $("#immersionScenarioSelect"),
  immersionScenarioPreview: $("#immersionScenarioPreview"),
  immersionCustomFields: $("#immersionCustomFields"),
  immersionCustomName: $("#immersionCustomName"),
  immersionCustomWhat: $("#immersionCustomWhat"),
  immersionCustomWho: $("#immersionCustomWho"),
  immersionCustomDynamic: $("#immersionCustomDynamic"),
  immersionFeedback: $("#immersionFeedback"),
  closeImmersionDialog: $("#closeImmersionDialog"),
  cancelImmersionButton: $("#cancelImmersionButton"),
  enterImmersionButton: $("#enterImmersionButton"),
  assistantButton: $("#assistantButton"),
  assistantStatusBadge: $("#assistantStatusBadge"),
  assistantDialog: $("#assistantDialog"),
  assistantForm: $("#assistantForm"),
  assistantCharacterLabel: $("#assistantCharacterLabel"),
  assistantTimelineSelect: $("#assistantTimelineSelect"),
  assistantToneSelect: $("#assistantToneSelect"),
  assistantScenarioSelect: $("#assistantScenarioSelect"),
  assistantScenarioPreview: $("#assistantScenarioPreview"),
  assistantCustomFields: $("#assistantCustomFields"),
  assistantCustomName: $("#assistantCustomName"),
  assistantCustomWhat: $("#assistantCustomWhat"),
  assistantCustomWho: $("#assistantCustomWho"),
  assistantCustomDynamic: $("#assistantCustomDynamic"),
  assistantWardrobeOptions: $("#assistantWardrobeOptions"),
  assistantCustomBackgroundField: $("#assistantCustomBackgroundField"),
  assistantCustomBackground: $("#assistantCustomBackground"),
  assistantFeedback: $("#assistantFeedback"),
  closeAssistantDialog: $("#closeAssistantDialog"),
  cancelAssistantButton: $("#cancelAssistantButton"),
  launchAssistantButton: $("#launchAssistantButton"),
};

boot().catch(showFatal);

async function boot() {
  bindEvents();
  restorePresentationState();
  const status = await api("/api/auth/status");
  if (!status.initialized) {
    state.authMode = "setup";
    els.authPassword.autocomplete = "new-password";
    showAuth("Create the owner account", "First launch: create the local owner account.", "Create & unlock");
    return;
  }
  if (!status.authenticated) {
    state.authMode = "login";
    els.authPassword.autocomplete = "current-password";
    showAuth("Unlock Protean Workspace", "Sign in to your local workspace.", "Unlock");
    return;
  }
  await enterStudio(status.username);
}

function bindEvents() {
  els.authForm.addEventListener("submit", handleAuth);
  els.researchButton.addEventListener("click", () => researchCharacters(els.characterSearch.value));
  els.characterSearch.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      researchCharacters(els.characterSearch.value);
    }
  });
  els.toneSelect.addEventListener("change", async () => {
    await savePreferences({ tone_id: els.toneSelect.value });
    renderToneDescription();
    startFreshChat();
  });
  els.timelineSelect.addEventListener("change", async () => {
    state.selectedPhase = phaseById(state.selectedCharacter, els.timelineSelect.value);
    state.selectedScenario = defaultScenarioForPhase(state.selectedPhase);
    await savePreferences({ active_phase_id: els.timelineSelect.value });
    renderTimelineControls();
    renderScenarioControls();
    renderActiveCharacter();
    startFreshChat();
  });
  els.scenarioSelect.addEventListener("change", () => {
    if (els.scenarioSelect.value === "custom") {
      state.selectedScenario = customScenarioFromFields();
      loadCustomScenarioDraft();
    } else {
      state.selectedScenario = scenarioById(state.selectedPhase, els.scenarioSelect.value);
    }
    renderScenarioControls();
    startFreshChat();
  });
  [els.customScenarioName, els.customScenarioWhat, els.customScenarioWho, els.customScenarioDynamic].forEach((field) => {
    field.addEventListener("input", () => {
      if (els.scenarioSelect.value !== "custom") return;
      state.selectedScenario = customScenarioFromFields();
      state.openingToken = null;
      saveCustomScenarioDraft();
      renderScenarioPreview(state.selectedScenario);
    });
    field.addEventListener("change", () => {
      if (els.scenarioSelect.value === "custom") startFreshChat();
    });
  });
  els.saveLibraryButton.addEventListener("click", saveLibraryRoot);
  els.newChatButton.addEventListener("click", startFreshChat);
  els.composer.addEventListener("submit", sendMessage);
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.composer.requestSubmit();
    }
  });
  els.messageInput.addEventListener("input", autoGrowComposer);
  els.themeSelect.addEventListener("change", () => updateAppearance("theme_id", els.themeSelect.value));
  els.backgroundSelect.addEventListener("change", () => updateAppearance("background_id", els.backgroundSelect.value));
  els.frameSelect.addEventListener("change", () => updateAppearance("frame_id", els.frameSelect.value));
  els.saveProviderButton.addEventListener("click", saveProvider);
  els.validateProviderButton.addEventListener("click", validateProvider);
  els.removeProviderButton.addEventListener("click", removeProvider);
  els.logoutButton.addEventListener("click", logout);
  els.toggleLeft.addEventListener("click", () => togglePanel("left"));
  els.toggleRight.addEventListener("click", () => togglePanel("right"));
  els.focusModeButton.addEventListener("click", toggleFocusMode);
  els.immersionButton.addEventListener("click", openImmersionDialog);
  els.closeImmersionDialog.addEventListener("click", closeImmersionDialog);
  els.cancelImmersionButton.addEventListener("click", closeImmersionDialog);
  els.immersionForm.addEventListener("submit", startImmersion);
  els.immersionTimelineSelect.addEventListener("change", renderImmersionScenarioOptions);
  els.immersionScenarioSelect.addEventListener("change", handleImmersionScenarioChange);
  [els.immersionCustomName, els.immersionCustomWhat, els.immersionCustomWho, els.immersionCustomDynamic].forEach((field) => {
    field.addEventListener("input", renderImmersionScenarioPreview);
  });
  els.assistantButton.addEventListener("click", openAssistantDialog);
  els.closeAssistantDialog.addEventListener("click", closeAssistantDialog);
  els.cancelAssistantButton.addEventListener("click", closeAssistantDialog);
  els.assistantForm.addEventListener("submit", startAssistant);
  els.assistantTimelineSelect.addEventListener("change", renderAssistantScenarioOptions);
  els.assistantScenarioSelect.addEventListener("change", handleAssistantScenarioChange);
  [els.assistantCustomName, els.assistantCustomWhat, els.assistantCustomWho, els.assistantCustomDynamic].forEach((field) => {
    field.addEventListener("input", renderAssistantScenarioPreview);
  });
  document.querySelectorAll('input[name="assistantBackground"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      els.assistantCustomBackgroundField.hidden = radio.value !== "custom" || !radio.checked;
    });
  });
  window.addEventListener("keydown", handleWorkspaceShortcut);
}

async function handleAuth(event) {
  event.preventDefault();
  els.authError.textContent = "";
  setButtonBusy(els.authSubmit, true, state.authMode === "setup" ? "Creating…" : "Unlocking…");
  try {
    const user = await api(`/api/auth/${state.authMode}`, {
      method: "POST",
      body: { username: els.authUsername.value.trim(), password: els.authPassword.value },
    });
    els.authPassword.value = "";
    await enterStudio(user.username);
  } catch (error) {
    els.authError.textContent = error.message;
  } finally {
    setButtonBusy(els.authSubmit, false, state.authMode === "setup" ? "Create & unlock" : "Unlock");
  }
}

function showAuth(title, description, buttonText) {
  els.authTitle.textContent = title;
  els.authDescription.textContent = description;
  setButtonBusy(els.authSubmit, false, buttonText);
  els.authGate.hidden = false;
  els.appShell.hidden = true;
  queueMicrotask(() => els.authUsername.focus());
}

async function enterStudio(username) {
  els.currentUser.textContent = username ? `@${username}` : "";
  els.authGate.hidden = true;
  els.appShell.hidden = false;
  const [presets, preferences, provider, chats] = await Promise.all([
    api("/api/ui/presets"),
    api("/api/settings/preferences"),
    api("/api/settings/provider"),
    api("/api/chats"),
  ]);
  state.presets = presets;
  state.preferences = preferences;
  state.provider = provider;
  state.chats = chats;
  renderPresetControls();
  renderProvider();
  renderChatHistory();
  applyAppearance();
  els.libraryRoot.value = preferences.library_root;
  await researchCharacters("");
  await refreshImmersionAvailability();
  await refreshAssistantAvailability();
  await restoreChatAfterImmersion();
  els.messageInput.focus();
}

function renderPresetControls() {
  fillSelect(els.toneSelect, state.presets.tones, state.preferences.tone_id);
  fillSelect(els.themeSelect, state.presets.themes, state.preferences.theme_id);
  fillSelect(els.backgroundSelect, state.presets.backgrounds, state.preferences.background_id);
  fillSelect(els.frameSelect, state.presets.frames, state.preferences.frame_id);
  renderToneDescription();
}

function fillSelect(select, items, selected) {
  select.replaceChildren(...items.map((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    option.selected = item.id === selected;
    return option;
  }));
}

function renderToneDescription() {
  const tone = state.presets?.tones.find((item) => item.id === els.toneSelect.value);
  els.toneDescription.textContent = tone?.description || "";
}

async function researchCharacters(query) {
  setButtonBusy(els.researchButton, true, "Scanning…");
  try {
    const result = await api("/api/characters/research", { method: "POST", body: { query } });
    state.characters = result.characters;
    const preferred = state.characters.find((item) => item.id === state.preferences.active_character_id)
      || state.characters[0]
      || null;
    if (preferred) {
      state.selectedCharacter = preferred;
      state.selectedPhase = phaseById(preferred, state.preferences.active_phase_id);
      state.selectedScenario = defaultScenarioForPhase(state.selectedPhase);
    }
    renderCharacters();
    renderTimelineControls();
    renderScenarioControls();
    renderActiveCharacter();
    renderImmersionButton();
    renderAssistantButton();
    renderEmptyChat();
  } catch (error) {
    els.characterList.replaceChildren(createMicrocopy(error.message));
  } finally {
    setButtonBusy(els.researchButton, false, "Research");
  }
}

function renderCharacters() {
  els.characterList.replaceChildren();
  if (!state.characters.length) {
    els.characterList.append(createMicrocopy("No matching character files found."));
    return;
  }
  for (const character of state.characters) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `character-card${character.id === state.selectedCharacter?.id ? " active" : ""}`;

    const thumb = createCharacterImage(character, "character-thumb");
    const copy = document.createElement("span");
    copy.className = "character-card-copy";
    const name = document.createElement("strong");
    name.textContent = character.name;
    const franchise = document.createElement("span");
    franchise.textContent = character.franchise;
    copy.append(name, franchise);
    button.append(thumb, copy, icon("i-chevron"));

    button.addEventListener("click", async () => {
      state.selectedCharacter = character;
      state.selectedPhase = phaseById(character, character.default_phase_id);
      state.selectedScenario = defaultScenarioForPhase(state.selectedPhase);
      await savePreferences({
        active_character_id: character.id,
        active_phase_id: state.selectedPhase?.id || "default",
      });
      renderCharacters();
      renderTimelineControls();
      renderScenarioControls();
      renderActiveCharacter();
      renderImmersionButton();
      renderAssistantButton();
      startFreshChat();
      closeMobilePanels();
    });
    els.characterList.append(button);
  }
}

function phaseById(character, phaseId) {
  if (!character) return null;
  const phases = Array.isArray(character.phases) ? character.phases : [];
  if (!phases.length) {
    return {
      id: "default",
      name: "Default",
      period: "",
      summary: character.description || "",
      first_message: character.first_message || "",
      medium_type: character.medium_type || "chat",
      default_scenario_id: "",
      scenarios: [],
    };
  }
  return phases.find((phase) => phase.id === phaseId)
    || phases.find((phase) => phase.id === character.default_phase_id)
    || phases[0];
}

function defaultScenarioForPhase(phase) {
  if (!phase) return null;
  const scenarios = Array.isArray(phase.scenarios) ? phase.scenarios : [];
  if (!scenarios.length) return null;
  return scenarios.find((item) => item.id === phase.default_scenario_id) || scenarios[0];
}

function scenarioById(phase, scenarioId) {
  if (!phase) return null;
  const scenarios = Array.isArray(phase.scenarios) ? phase.scenarios : [];
  return scenarios.find((item) => item.id === scenarioId) || defaultScenarioForPhase(phase);
}

function renderScenarioControls() {
  const phase = state.selectedPhase;
  if (!phase) {
    els.scenarioSelect.replaceChildren();
    els.scenarioSelect.disabled = true;
    els.scenarioPreview.hidden = true;
    els.customScenarioFields.hidden = true;
    return;
  }
  const scenarios = Array.isArray(phase.scenarios) ? phase.scenarios : [];
  if (!state.selectedScenario && scenarios.length) state.selectedScenario = defaultScenarioForPhase(phase);
  const isCustom = state.selectedScenario?.custom || state.selectedScenario?.id === "custom";
  const options = scenarios.map((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.name;
    option.selected = !isCustom && scenario.id === state.selectedScenario?.id;
    return option;
  });
  const customOption = document.createElement("option");
  customOption.value = "custom";
  customOption.textContent = "+ Custom scene…";
  customOption.selected = isCustom;
  options.push(customOption);
  els.scenarioSelect.disabled = false;
  els.scenarioSelect.replaceChildren(...options);
  els.customScenarioFields.hidden = !isCustom;
  if (isCustom) {
    if (!els.customScenarioWhat.value && !els.customScenarioWho.value && !els.customScenarioDynamic.value) {
      loadCustomScenarioDraft();
    }
    state.selectedScenario = customScenarioFromFields();
  }
  renderScenarioPreview(state.selectedScenario);
}

function renderScenarioPreview(scenario) {
  els.scenarioPreview.replaceChildren();
  if (!scenario) {
    els.scenarioPreview.hidden = true;
    return;
  }
  els.scenarioPreview.hidden = false;
  const facts = [
    ["What", scenario.what_happening],
    ["Who", scenario.who_involved],
    ["Dynamic", scenario.dynamic],
  ];
  for (const [label, value] of facts) {
    if (!value) continue;
    const item = document.createElement("div");
    item.className = "scenario-fact";
    const heading = document.createElement("strong");
    heading.textContent = label;
    const copy = document.createElement("span");
    copy.textContent = value;
    item.append(heading, copy);
    els.scenarioPreview.append(item);
  }
}

function customScenarioDraftKey() {
  return `protean.custom-scenario.${state.selectedCharacter?.id || "none"}.${state.selectedPhase?.id || "default"}`;
}

function customScenarioFromFields() {
  return {
    id: "custom",
    custom: true,
    name: els.customScenarioName.value.trim() || "Custom scene",
    what_happening: els.customScenarioWhat.value.trim(),
    who_involved: els.customScenarioWho.value.trim(),
    dynamic: els.customScenarioDynamic.value.trim(),
    first_message: "",
  };
}

function saveCustomScenarioDraft() {
  const scene = customScenarioFromFields();
  localStorage.setItem(customScenarioDraftKey(), JSON.stringify(scene));
}

function loadCustomScenarioDraft(scene = null) {
  let draft = scene;
  if (!draft) {
    try { draft = JSON.parse(localStorage.getItem(customScenarioDraftKey()) || "null"); } catch { draft = null; }
  }
  els.customScenarioName.value = draft?.name || "Custom scene";
  els.customScenarioWhat.value = draft?.what_happening || "";
  els.customScenarioWho.value = draft?.who_involved || "";
  els.customScenarioDynamic.value = draft?.dynamic || "";
  state.selectedScenario = customScenarioFromFields();
}

function renderTimelineControls() {
  const character = state.selectedCharacter;
  if (!character) {
    els.timelineSelect.replaceChildren();
    els.timelineSelect.disabled = true;
    els.timelinePeriod.textContent = "";
    els.timelineDescription.textContent = "Select a character first.";
    return;
  }
  const phases = Array.isArray(character.phases) && character.phases.length
    ? character.phases
    : [phaseById(character, "default")];
  if (!state.selectedPhase || !phases.some((phase) => phase.id === state.selectedPhase.id)) {
    state.selectedPhase = phaseById(character, state.preferences?.active_phase_id);
  }
  els.timelineSelect.disabled = phases.length <= 1;
  els.timelineSelect.replaceChildren(...phases.map((phase) => {
    const option = document.createElement("option");
    option.value = phase.id;
    option.textContent = phase.name;
    option.selected = phase.id === state.selectedPhase?.id;
    return option;
  }));
  const phase = state.selectedPhase || phases[0];
  els.timelinePeriod.textContent = phase?.period || "";
  els.timelineDescription.textContent = phase?.summary || "";
}

function renderActiveCharacter() {
  const character = state.selectedCharacter;
  const phase = state.selectedPhase || phaseById(character, state.preferences?.active_phase_id);
  els.activeCharacterName.textContent = character?.name || "Select a character";
  els.activeFranchise.textContent = character?.franchise || "";
  els.activeMedium.textContent = phase?.medium_type || character?.medium_type || "";
  els.heroName.textContent = character?.name || "Select a character";
  els.heroFranchise.textContent = phase?.name ? `${character?.franchise || ""} · ${phase.name}` : (character?.franchise || "");
  renderImmersionButton();
  renderAssistantButton();
  if (character?.portrait) {
    els.activePortrait.src = character.portrait;
    els.activePortrait.alt = `${character.name} portrait`;
  } else {
    els.activePortrait.removeAttribute("src");
    els.activePortrait.alt = "";
  }
}

function currentChatSetupPayload() {
  return {
    character_id: state.selectedCharacter?.id || null,
    phase_id: state.selectedPhase?.id || state.selectedCharacter?.default_phase_id || "default",
    scenario_id: state.selectedScenario?.custom ? "custom" : (state.selectedScenario?.id || null),
    custom_scenario: state.selectedScenario?.custom ? {
      name: state.selectedScenario.name || "Custom scene",
      what_happening: state.selectedScenario.what_happening || "",
      who_involved: state.selectedScenario.who_involved || "",
      dynamic: state.selectedScenario.dynamic || "",
    } : null,
    tone_id: els.toneSelect.value,
  };
}

function customScenarioIsComplete() {
  if (!state.selectedScenario?.custom) return true;
  return Boolean(
    state.selectedScenario.what_happening?.trim()
    && state.selectedScenario.who_involved?.trim()
    && state.selectedScenario.dynamic?.trim()
  );
}

async function renderEmptyChat() {
  if (state.activeChatId) return;
  const sequence = ++state.openingPreviewSequence;
  state.openingToken = null;
  els.messages.replaceChildren();
  if (!state.selectedCharacter) return;
  if (!customScenarioIsComplete()) {
    addSystemNote("Complete What, Who, and Dynamic to generate this custom opening.");
    return;
  }
  if (!state.provider?.configured) {
    addSystemNote("Add your OpenRouter key in Connection settings first, then re-click the character to generate a new opening.");
    return;
  }

  const pending = addSystemNote("Generating opening…");
  try {
    const preview = await api("/api/chats/opening-preview", {
      method: "POST",
      body: currentChatSetupPayload(),
    });
    if (sequence !== state.openingPreviewSequence || state.activeChatId) return;
    state.openingToken = preview.opening_token;
    els.messages.replaceChildren();
    addMessage("assistant", preview.message, state.selectedCharacter.name);
  } catch (error) {
    if (sequence !== state.openingPreviewSequence || state.activeChatId) return;
    pending.remove();
    state.openingToken = null;
    addSystemNote(
      error instanceof ApiError && error.status === 409
        ? "Add your OpenRouter key in Connection settings first, then re-click the character to generate a new opening."
        : (error.message || "Could not generate the opening scene."),
    );
  }
}

function scheduleOpeningPreview() {
  clearTimeout(state.openingPreviewTimer);
  state.openingPreviewTimer = setTimeout(() => {
    renderEmptyChat();
  }, 320);
}

function startFreshChat() {
  state.activeChatId = null;
  state.openingToken = null;
  state.openingPreviewSequence += 1;
  document.querySelectorAll(".history-item").forEach((item) => item.classList.remove("active"));
  els.messages.replaceChildren();
  scheduleOpeningPreview();
  els.messageInput.focus();
}

async function ensureActiveChat() {
  if (state.activeChatId) return state.activeChatId;
  if (!state.selectedCharacter) throw new Error("Select a character first.");
  clearTimeout(state.openingPreviewTimer);
  state.openingPreviewSequence += 1;
  document.querySelectorAll(".system-note").forEach((note) => {
    if (note.textContent === "Preparing scene…") note.remove();
  });
  if (!customScenarioIsComplete()) throw new Error("Complete What, Who, and Dynamic before starting this custom scene.");
  if (!state.openingToken) {
    throw new Error("Generate the opening first by re-clicking the character after your provider key is configured.");
  }
  const chat = await api("/api/chats", {
    method: "POST",
    body: { ...currentChatSetupPayload(), opening_token: state.openingToken },
  });
  state.openingToken = null;
  state.activeChatId = chat.id;
  state.chats.unshift(chat);
  renderChatHistory();
  return chat.id;
}

async function sendMessage(event) {
  event.preventDefault();
  const text = els.messageInput.value.trim();
  if (!text || state.busy) return;
  state.busy = true;
  els.sendButton.disabled = true;
  els.messageInput.disabled = true;
  try {
    const chatId = await ensureActiveChat();
    addMessage("user", text, "You");
    els.messageInput.value = "";
    autoGrowComposer();
    const pending = addSystemNote("Composing…");
    const response = await api(`/api/chats/${chatId}/messages`, {
      method: "POST",
      body: { message: text, request_id: newRequestId() },
    });
    pending.remove();
    addMessage("assistant", response.reply, state.selectedCharacter?.name || "Character");
    await refreshChats();
  } catch (error) {
    addSystemNote(
      error instanceof ApiError && error.status === 409
        ? "Add an OpenRouter key in the right workspace panel first."
        : error.message,
    );
  } finally {
    state.busy = false;
    els.sendButton.disabled = false;
    els.messageInput.disabled = false;
    els.messageInput.focus();
  }
}

function newRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

function addMessage(role, content, speaker) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const header = document.createElement("div");
  header.className = "message-header";
  header.textContent = speaker;
  const body = document.createElement("div");
  body.className = "message-body";
  body.append(renderTranscript(content));
  article.append(header, body);
  els.messages.append(article);
  scrollMessages();
  return article;
}

function renderTranscript(content) {
  const fragment = document.createDocumentFragment();
  const source = String(content || "");
  const pattern = /(\*\*[\s\S]*?\*\*|"[^"\n]*"|\([^()]*\))/g;
  let last = 0;
  for (const match of source.matchAll(pattern)) {
    if (match.index > last) appendTranscriptSegment(fragment, "narrative", source.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("**")) appendTranscriptSegment(fragment, "action", token.slice(2, -2));
    else if (token.startsWith('"')) appendTranscriptSegment(fragment, "speech", token.slice(1, -1));
    else appendTranscriptSegment(fragment, "dev", token.slice(1, -1));
    last = match.index + token.length;
  }
  if (last < source.length) appendTranscriptSegment(fragment, "narrative", source.slice(last));
  if (!fragment.childNodes.length) appendTranscriptSegment(fragment, "narrative", source);
  return fragment;
}

function appendTranscriptSegment(fragment, kind, text) {
  const clean = kind === "narrative" ? text.trim() : text.trim();
  if (!clean) return;
  const span = document.createElement("span");
  span.className = `transcript-segment transcript-${kind}`;
  span.textContent = clean;
  fragment.append(span);
}

function addSystemNote(text) {
  const note = document.createElement("div");
  note.className = "system-note";
  note.textContent = text;
  els.messages.append(note);
  scrollMessages();
  return note;
}

async function refreshChats() {
  state.chats = await api("/api/chats");
  renderChatHistory();
}

function renderChatHistory() {
  els.chatHistory.replaceChildren();
  for (const chat of state.chats) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `history-item${chat.id === state.activeChatId ? " active" : ""}`;
    button.textContent = chat.title;
    button.addEventListener("click", () => loadChat(chat.id));
    els.chatHistory.append(button);
  }
  if (!state.chats.length) els.chatHistory.append(createMicrocopy("No saved conversations yet."));
}

async function loadChat(chatId) {
  clearTimeout(state.openingPreviewTimer);
  state.openingPreviewSequence += 1;
  const chat = await api(`/api/chats/${chatId}`);
  state.activeChatId = chat.id;
  state.openingToken = null;
  let character = state.characters.find((item) => item.id === chat.character_id);
  if (!character) {
    const result = await api("/api/characters/research", { method: "POST", body: { query: "" } });
    state.characters = result.characters;
    character = state.characters.find((item) => item.id === chat.character_id);
  }
  if (character) {
    state.selectedCharacter = character;
    state.selectedPhase = phaseById(character, chat.phase_id);
    if (chat.scenario?.custom || chat.scenario_id === "custom") {
      loadCustomScenarioDraft(chat.scenario || null);
      state.selectedScenario = customScenarioFromFields();
    } else {
      state.selectedScenario = scenarioById(state.selectedPhase, chat.scenario_id);
    }
    state.preferences.active_character_id = character.id;
    state.preferences.active_phase_id = state.selectedPhase?.id || chat.phase_id || "default";
    renderCharacters();
    renderTimelineControls();
    renderScenarioControls();
    renderActiveCharacter();
  }
  if (state.presets.tones.some((tone) => tone.id === chat.tone_id)) {
    els.toneSelect.value = chat.tone_id;
    renderToneDescription();
  }
  els.messages.replaceChildren();
  for (const message of chat.messages) {
    addMessage(
      message.role,
      message.content,
      message.role === "user" ? "You" : (character?.name || "Character"),
    );
  }
  renderChatHistory();
  closeMobilePanels();
}


async function refreshImmersionAvailability() {
  try {
    state.immersionAvailability = await api("/api/immersion/availability");
  } catch {
    state.immersionAvailability = { enabled: false, characters: [] };
  }
  renderImmersionButton();
}

function immersionCharacterOption(characterId = state.selectedCharacter?.id) {
  return state.immersionAvailability?.characters?.find((item) => item.character_id === characterId) || null;
}

function renderImmersionButton() {
  if (!els.immersionButton) return;
  const option = immersionCharacterOption();
  const implemented = Boolean(option?.phases?.length);
  els.immersionButton.hidden = !implemented;
  if (els.immersionStatusBadge) {
    els.immersionStatusBadge.textContent = implemented ? "Implemented" : "Not yet implemented";
  }
  if (implemented) {
    els.immersionButton.title = `Start Immersion · ${option.phases.length} supported timeline${option.phases.length === 1 ? "" : "s"}`;
  } else {
    els.immersionButton.removeAttribute("title");
  }
}

function openImmersionDialog() {
  const character = state.selectedCharacter;
  const available = immersionCharacterOption(character?.id);
  if (!character || !available?.phases?.length) return;
  els.immersionFeedback.textContent = "";
  els.immersionCharacterLabel.textContent = `${character.name} · only ready visual timelines are listed`;

  const currentPhaseSupported = available.phases.some((phase) => phase.id === state.selectedPhase?.id);
  const selectedPhaseId = currentPhaseSupported ? state.selectedPhase.id : available.phases[0].id;
  els.immersionTimelineSelect.replaceChildren(...available.phases.map((phase) => {
    const option = document.createElement("option");
    option.value = phase.id;
    option.textContent = phase.name;
    option.selected = phase.id === selectedPhaseId;
    return option;
  }));
  fillSelect(els.immersionToneSelect, state.presets.tones, els.toneSelect.value);
  renderImmersionScenarioOptions();
  els.immersionDialog.showModal();
}

function closeImmersionDialog() {
  if (els.immersionDialog.open) els.immersionDialog.close();
}

function immersionPhase() {
  return phaseById(state.selectedCharacter, els.immersionTimelineSelect.value);
}

function renderImmersionScenarioOptions() {
  const phase = immersionPhase();
  if (!phase) return;
  const scenarios = Array.isArray(phase.scenarios) ? phase.scenarios : [];
  const previous = els.immersionScenarioSelect.value;
  const normalSelected = state.selectedPhase?.id === phase.id ? state.selectedScenario?.id : null;
  const desired = previous === "custom" || normalSelected === "custom"
    ? "custom"
    : scenarios.some((item) => item.id === previous)
      ? previous
      : scenarios.some((item) => item.id === normalSelected)
        ? normalSelected
        : phase.default_scenario_id || scenarios[0]?.id || "custom";

  const options = scenarios.map((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = scenario.name;
    option.selected = scenario.id === desired;
    return option;
  });
  const custom = document.createElement("option");
  custom.value = "custom";
  custom.textContent = "+ Custom scene…";
  custom.selected = desired === "custom";
  options.push(custom);
  els.immersionScenarioSelect.replaceChildren(...options);

  handleImmersionScenarioChange();
}

function handleImmersionScenarioChange() {
  const phase = immersionPhase();
  if (!phase) return;
  const isCustom = els.immersionScenarioSelect.value === "custom";
  els.immersionCustomFields.hidden = !isCustom;
  if (isCustom && !els.immersionCustomWhat.value && state.selectedScenario?.custom && state.selectedPhase?.id === phase.id) {
    els.immersionCustomName.value = state.selectedScenario.name || "Custom scene";
    els.immersionCustomWhat.value = state.selectedScenario.what_happening || "";
    els.immersionCustomWho.value = state.selectedScenario.who_involved || "";
    els.immersionCustomDynamic.value = state.selectedScenario.dynamic || "";
  }
  renderImmersionScenarioPreview();
}

function immersionScenarioPayload() {
  const phase = immersionPhase();
  if (els.immersionScenarioSelect.value !== "custom") {
    return {
      scenario_id: els.immersionScenarioSelect.value,
      custom_scenario: null,
      scene: scenarioById(phase, els.immersionScenarioSelect.value),
    };
  }
  const scene = {
    id: "custom",
    custom: true,
    name: els.immersionCustomName.value.trim() || "Custom scene",
    what_happening: els.immersionCustomWhat.value.trim(),
    who_involved: els.immersionCustomWho.value.trim(),
    dynamic: els.immersionCustomDynamic.value.trim(),
  };
  return {
    scenario_id: "custom",
    custom_scenario: {
      name: scene.name,
      what_happening: scene.what_happening,
      who_involved: scene.who_involved,
      dynamic: scene.dynamic,
    },
    scene,
  };
}

function renderImmersionScenarioPreview() {
  const { scene } = immersionScenarioPayload();
  els.immersionScenarioPreview.replaceChildren();
  if (!scene) return;
  for (const [label, value] of [["What", scene.what_happening], ["Who", scene.who_involved], ["Dynamic", scene.dynamic]]) {
    if (!value) continue;
    const item = document.createElement("div");
    item.className = "scenario-fact";
    const heading = document.createElement("strong");
    heading.textContent = label;
    const copy = document.createElement("span");
    copy.textContent = value;
    item.append(heading, copy);
    els.immersionScenarioPreview.append(item);
  }
}

async function startImmersion(event) {
  event.preventDefault();
  const character = state.selectedCharacter;
  if (!character) return;
  const phaseId = els.immersionTimelineSelect.value;
  const scenario = immersionScenarioPayload();
  if (scenario.custom_scenario && !(scenario.custom_scenario.what_happening && scenario.custom_scenario.who_involved && scenario.custom_scenario.dynamic)) {
    els.immersionFeedback.textContent = "Complete What, Who, and Dynamic before entering a custom Immersion scene.";
    return;
  }
  els.immersionFeedback.textContent = "";
  setButtonBusy(els.enterImmersionButton, true, "Entering…");
  try {
    const result = await api("/api/immersion/start", {
      method: "POST",
      body: {
        character_id: character.id,
        phase_id: phaseId,
        scenario_id: scenario.scenario_id,
        custom_scenario: scenario.custom_scenario,
        tone_id: els.immersionToneSelect.value,
      },
    });
    sessionStorage.setItem("protean.immersion.session", JSON.stringify(result));
    closeImmersionDialog();
    window.location.assign("/immersion");
  } catch (error) {
    els.immersionFeedback.textContent = error.message;
  } finally {
    setButtonBusy(els.enterImmersionButton, false, "Enter scene");
  }
}


async function refreshAssistantAvailability() {
  try {
    state.assistantAvailability = await api("/api/assistant/availability");
  } catch {
    state.assistantAvailability = { enabled: false, characters: [] };
  }
  renderAssistantButton();
}

function assistantCharacterOption(characterId = state.selectedCharacter?.id) {
  return state.assistantAvailability?.characters?.find((item) => item.character_id === characterId) || null;
}

function renderAssistantButton() {
  if (!els.assistantButton) return;
  const option = assistantCharacterOption();
  const implemented = Boolean(option?.phases?.length && option?.wardrobes?.some((item) => item.status === "ready"));
  els.assistantButton.hidden = !implemented;
  if (els.assistantStatusBadge) {
    els.assistantStatusBadge.textContent = implemented ? "Implemented" : "Not yet implemented";
  }
  if (implemented) {
    els.assistantButton.title = `Launch Virtual Assistant · ${option.phases.length} supported timeline${option.phases.length === 1 ? "" : "s"}`;
  } else {
    els.assistantButton.removeAttribute("title");
  }
}

function openAssistantDialog() {
  const character = state.selectedCharacter;
  const available = assistantCharacterOption(character?.id);
  if (!character || !available?.phases?.length) return;
  els.assistantFeedback.textContent = "";
  els.assistantCharacterLabel.textContent = `${character.name} · desktop companion mode`;
  const currentPhaseSupported = available.phases.some((phase) => phase.id === state.selectedPhase?.id);
  const selectedPhaseId = currentPhaseSupported ? state.selectedPhase.id : available.phases[0].id;
  els.assistantTimelineSelect.replaceChildren(...available.phases.map((phase) => {
    const option = document.createElement("option");
    option.value = phase.id;
    option.textContent = phase.name;
    option.selected = phase.id === selectedPhaseId;
    return option;
  }));
  fillSelect(els.assistantToneSelect, state.presets.tones, els.toneSelect.value);
  renderAssistantWardrobes(available);
  renderAssistantScenarioOptions();
  const selectedBg = document.querySelector('input[name="assistantBackground"]:checked');
  els.assistantCustomBackgroundField.hidden = selectedBg?.value !== "custom";
  els.assistantDialog.showModal();
}

function closeAssistantDialog() {
  if (els.assistantDialog.open) els.assistantDialog.close();
}

function assistantPhase() {
  return phaseById(state.selectedCharacter, els.assistantTimelineSelect.value);
}

function renderAssistantScenarioOptions() {
  const phase = assistantPhase();
  if (!phase) return;
  const scenarios = Array.isArray(phase.scenarios) ? phase.scenarios : [];
  const preferred = state.selectedPhase?.id === phase.id && state.selectedScenario?.id
    ? state.selectedScenario.id
    : phase.default_scenario_id;
  const options = scenarios.map((scene) => {
    const option = document.createElement("option");
    option.value = scene.id;
    option.textContent = scene.name;
    option.selected = scene.id === preferred;
    return option;
  });
  const custom = document.createElement("option");
  custom.value = "custom";
  custom.textContent = "Custom scene…";
  options.push(custom);
  els.assistantScenarioSelect.replaceChildren(...options);
  handleAssistantScenarioChange();
}

function handleAssistantScenarioChange() {
  const phase = assistantPhase();
  const isCustom = els.assistantScenarioSelect.value === "custom";
  els.assistantCustomFields.hidden = !isCustom;
  if (isCustom && !els.assistantCustomWhat.value && state.selectedScenario?.custom && state.selectedPhase?.id === phase?.id) {
    els.assistantCustomName.value = state.selectedScenario.name || "Custom scene";
    els.assistantCustomWhat.value = state.selectedScenario.what_happening || "";
    els.assistantCustomWho.value = state.selectedScenario.who_involved || "";
    els.assistantCustomDynamic.value = state.selectedScenario.dynamic || "";
  }
  renderAssistantScenarioPreview();
}

function assistantScenarioPayload() {
  const phase = assistantPhase();
  if (els.assistantScenarioSelect.value !== "custom") {
    return {
      scenario_id: els.assistantScenarioSelect.value,
      custom_scenario: null,
      scene: scenarioById(phase, els.assistantScenarioSelect.value),
    };
  }
  const scene = {
    id: "custom",
    custom: true,
    name: els.assistantCustomName.value.trim() || "Custom scene",
    what_happening: els.assistantCustomWhat.value.trim(),
    who_involved: els.assistantCustomWho.value.trim(),
    dynamic: els.assistantCustomDynamic.value.trim(),
  };
  return {
    scenario_id: "custom",
    custom_scenario: {
      name: scene.name,
      what_happening: scene.what_happening,
      who_involved: scene.who_involved,
      dynamic: scene.dynamic,
    },
    scene,
  };
}

function renderAssistantScenarioPreview() {
  const { scene } = assistantScenarioPayload();
  els.assistantScenarioPreview.replaceChildren();
  if (!scene) return;
  for (const [label, value] of [["What", scene.what_happening], ["Who", scene.who_involved], ["Dynamic", scene.dynamic]]) {
    if (!value) continue;
    const item = document.createElement("div");
    item.className = "scenario-fact";
    const heading = document.createElement("strong");
    heading.textContent = label;
    const copy = document.createElement("span");
    copy.textContent = value;
    item.append(heading, copy);
    els.assistantScenarioPreview.append(item);
  }
}

function renderAssistantWardrobes(available) {
  els.assistantWardrobeOptions.replaceChildren();
  const ready = available.wardrobes?.filter((item) => item.status === "ready") || [];
  const preferred = ready.some((item) => item.id === available.default_wardrobe_id)
    ? available.default_wardrobe_id
    : ready[0]?.id;
  for (const wardrobe of available.wardrobes || []) {
    const label = document.createElement("label");
    label.className = `assistant-wardrobe-card ${wardrobe.status === "ready" ? "ready" : "locked"}`;
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "assistantWardrobe";
    radio.value = wardrobe.id;
    radio.disabled = wardrobe.status !== "ready";
    radio.checked = wardrobe.id === preferred;
    const name = document.createElement("span");
    name.textContent = wardrobe.label;
    const status = document.createElement("small");
    status.textContent = wardrobe.status === "ready" ? "Ready" : "🔒 Locked";
    label.append(radio, name, status);
    if (wardrobe.lock_reason) label.title = wardrobe.lock_reason;
    els.assistantWardrobeOptions.append(label);
  }
}

async function startAssistant(event) {
  event.preventDefault();
  const character = state.selectedCharacter;
  if (!character) return;
  const scenario = assistantScenarioPayload();
  if (scenario.custom_scenario && !(scenario.custom_scenario.what_happening && scenario.custom_scenario.who_involved && scenario.custom_scenario.dynamic)) {
    els.assistantFeedback.textContent = "Complete What, Who, and Dynamic before launching a custom Assistant session.";
    return;
  }
  const wardrobe = document.querySelector('input[name="assistantWardrobe"]:checked')?.value;
  if (!wardrobe) {
    els.assistantFeedback.textContent = "Choose one of the ready wardrobe skins.";
    return;
  }
  const backgroundMode = document.querySelector('input[name="assistantBackground"]:checked')?.value || "transparent";
  let customBackgroundDataUrl = null;
  let customBackgroundName = null;
  if (backgroundMode === "custom") {
    const file = els.assistantCustomBackground.files?.[0];
    if (!file) {
      els.assistantFeedback.textContent = "Choose a custom PNG, JPEG, or WebP background.";
      return;
    }
    if (file.size > 6 * 1024 * 1024) {
      els.assistantFeedback.textContent = "Custom background must be 6 MB or smaller.";
      return;
    }
    customBackgroundDataUrl = await fileToDataUrl(file);
    customBackgroundName = file.name;
  }
  els.assistantFeedback.textContent = "";
  setButtonBusy(els.launchAssistantButton, true, "Launching…");
  try {
    const result = await api("/api/assistant/start", {
      method: "POST",
      body: {
        character_id: character.id,
        phase_id: els.assistantTimelineSelect.value,
        scenario_id: scenario.scenario_id,
        custom_scenario: scenario.custom_scenario,
        tone_id: els.assistantToneSelect.value,
        wardrobe_id: wardrobe,
        background_mode: backgroundMode,
        custom_background_data_url: customBackgroundDataUrl,
        custom_background_name: customBackgroundName,
      },
    });
    if (result.launched) {
      closeAssistantDialog();
      window.location.assign(result.bridge_url || "/assistant");
    }
  } catch (error) {
    els.assistantFeedback.textContent = error.message;
  } finally {
    setButtonBusy(els.launchAssistantButton, false, "Launch companion");
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read the custom background image."));
    reader.readAsDataURL(file);
  });
}

async function restoreChatAfterImmersion() {
  const chatId = sessionStorage.getItem("protean.returnChatId");
  if (!chatId) return;
  sessionStorage.removeItem("protean.returnChatId");
  try {
    await loadChat(chatId);
  } catch {
    // The chat may have been deleted or the bound character library may have changed.
  }
}

async function saveLibraryRoot() {
  setButtonBusy(els.saveLibraryButton, true, "Checking…");
  try {
    await savePreferences({ library_root: els.libraryRoot.value.trim() });
    await researchCharacters("");
    await refreshImmersionAvailability();
    await refreshAssistantAvailability();
  } catch (error) {
    addSystemNote(error.message);
  } finally {
    setButtonBusy(els.saveLibraryButton, false, "Use this folder");
  }
}

async function savePreferences(patch) {
  state.preferences = await api("/api/settings/preferences", { method: "PUT", body: patch });
  els.libraryRoot.value = state.preferences.library_root;
  applyAppearance();
  return state.preferences;
}

async function updateAppearance(field, value) {
  const previous = state.preferences?.[field];
  if (state.preferences) state.preferences[field] = value;
  applyAppearance();
  try {
    await savePreferences({ [field]: value });
  } catch (error) {
    if (state.preferences) state.preferences[field] = previous;
    applyAppearance();
    addSystemNote(`Could not save appearance: ${error.message}`);
  }
}

function applyAppearance() {
  if (!state.preferences) return;
  document.body.dataset.theme = state.preferences.theme_id;
  document.body.dataset.background = state.preferences.background_id;
  document.body.dataset.frame = state.preferences.frame_id;
  const frame = state.presets?.frames.find((item) => item.id === state.preferences.frame_id);
  const scene = state.presets?.backgrounds.find((item) => item.id === state.preferences.background_id);
  els.frameLabel.textContent = frame?.name || state.preferences.frame_id;
  els.sceneLabel.textContent = scene?.name || state.preferences.background_id;
}

function renderProvider() {
  const provider = state.provider;
  els.keyStatus.textContent = provider.configured ? provider.masked_key : "Not configured";
  els.keyStatus.classList.toggle("ready", provider.configured);
  els.connectionIndicator.lastChild.textContent = provider.configured ? "Key saved" : "No key";
  els.connectionIndicator.classList.toggle("ready", provider.configured);
  els.modelInput.value = provider.model;
  els.temperatureInput.value = provider.temperature;
  els.targetTokensInput.value = provider.target_tokens;
  els.maxTokensInput.value = provider.max_tokens;
}

async function saveProvider() {
  setButtonBusy(els.saveProviderButton, true, "Saving…");
  els.providerFeedback.textContent = "";
  try {
    const body = {
      model: els.modelInput.value.trim(),
      temperature: Number(els.temperatureInput.value),
      target_tokens: Number(els.targetTokensInput.value),
      max_tokens: Number(els.maxTokensInput.value),
    };
    if (els.apiKeyInput.value.trim()) body.api_key = els.apiKeyInput.value.trim();
    state.provider = await api("/api/settings/provider", { method: "PUT", body });
    els.apiKeyInput.value = "";
    renderProvider();
    els.providerFeedback.textContent = "Connection settings saved on the backend.";
  } catch (error) {
    els.providerFeedback.textContent = error.message;
  } finally {
    setButtonBusy(els.saveProviderButton, false, "Save connection");
  }
}

async function validateProvider() {
  setButtonBusy(els.validateProviderButton, true, "Checking…");
  try {
    const result = await api("/api/settings/provider/validate", { method: "POST" });
    els.providerFeedback.textContent = result.valid
      ? `Valid${result.label ? ` · ${result.label}` : ""}${result.limit_remaining != null ? ` · ${result.limit_remaining} credits remaining` : ""}`
      : `Validation failed: ${result.detail}`;
  } catch (error) {
    els.providerFeedback.textContent = error.message;
  } finally {
    setButtonBusy(els.validateProviderButton, false, "Validate");
  }
}

async function removeProvider() {
  await api("/api/settings/provider/key", { method: "DELETE" });
  state.provider = await api("/api/settings/provider");
  renderProvider();
  els.providerFeedback.textContent = "Key removed.";
}

async function logout() {
  await api("/api/auth/logout", { method: "POST" });
  state.authMode = "login";
  els.authPassword.autocomplete = "current-password";
  state.activeChatId = null;
  els.authUsername.value = "";
  els.authPassword.value = "";
  showAuth("Unlock Protean Workspace", "Your workspace is locked.", "Unlock");
}

function togglePanel(side) {
  if (window.matchMedia("(max-width: 840px)").matches) {
    const openClass = side === "left" ? "mobile-left-open" : "mobile-right-open";
    const other = side === "left" ? "mobile-right-open" : "mobile-left-open";
    document.body.classList.toggle(openClass);
    document.body.classList.remove(other);
    return;
  }
  document.body.classList.toggle(`${side}-hidden`);
  persistPresentationState();
}

function toggleFocusMode() {
  const isFocused = document.body.classList.contains("left-hidden")
    && document.body.classList.contains("right-hidden");
  document.body.classList.toggle("left-hidden", !isFocused);
  document.body.classList.toggle("right-hidden", !isFocused);
  persistPresentationState();
}

function handleWorkspaceShortcut(event) {
  if (!(event.ctrlKey || event.metaKey)) return;
  if (event.key === "[") {
    event.preventDefault();
    togglePanel("left");
  }
  if (event.key === "]") {
    event.preventDefault();
    togglePanel("right");
  }
  if (event.key === "\\") {
    event.preventDefault();
    toggleFocusMode();
  }
}

function restorePresentationState() {
  try {
    const saved = JSON.parse(localStorage.getItem("protean.presentation") || "{}");
    document.body.classList.toggle("left-hidden", Boolean(saved.leftHidden));
    document.body.classList.toggle("right-hidden", Boolean(saved.rightHidden));
  } catch {
    localStorage.removeItem("protean.presentation");
  }
}

function persistPresentationState() {
  localStorage.setItem("protean.presentation", JSON.stringify({
    leftHidden: document.body.classList.contains("left-hidden"),
    rightHidden: document.body.classList.contains("right-hidden"),
  }));
}

function closeMobilePanels() {
  document.body.classList.remove("mobile-left-open", "mobile-right-open");
}

function autoGrowComposer() {
  els.messageInput.style.height = "auto";
  els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 150)}px`;
}

function scrollMessages() {
  requestAnimationFrame(() => {
    els.messages.scrollTop = els.messages.scrollHeight;
  });
}

function setButtonBusy(button, busy, text) {
  button.disabled = busy;
  const label = button.querySelector(".button-label");
  if (label) label.textContent = text;
  else button.textContent = text;
}

function icon(id) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("icon");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#${id}`);
  svg.append(use);
  return svg;
}

function createCharacterImage(character, className) {
  if (!character.portrait) {
    const fallback = document.createElement("span");
    fallback.className = className;
    fallback.textContent = initials(character.name);
    return fallback;
  }
  const image = document.createElement("img");
  image.className = className;
  image.src = character.portrait;
  image.alt = "";
  image.loading = "lazy";
  image.addEventListener("error", () => {
    image.removeAttribute("src");
    image.alt = initials(character.name);
  }, { once: true });
  return image;
}

function createMicrocopy(text) {
  const element = document.createElement("p");
  element.className = "microcopy";
  element.textContent = text;
  return element;
}

function initials(name) {
  return String(name).split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase();
}

function showFatal(error) {
  console.error(error);
  document.body.innerHTML = "";
  const gate = document.createElement("main");
  gate.className = "auth-gate";
  const card = document.createElement("section");
  card.className = "auth-card";
  const title = document.createElement("h1");
  title.textContent = "Startup error";
  const detail = document.createElement("p");
  detail.className = "form-error";
  detail.textContent = error?.message || String(error);
  card.append(title, detail);
  gate.append(card);
  document.body.append(gate);
}
