import { api, ApiError } from "./api.js";

const $ = (selector) => document.querySelector(selector);
const SESSION_KEY = "protean.immersion.session";
const RETURN_CHAT_KEY = "protean.returnChatId";

const state = {
  session: null,
  chat: null,
  currentBackgroundId: null,
  currentLocation: null,
  backgroundLayer: 0,
  spritePath: null,
  stageX: 0,
  stageScale: 1,
  busy: false,
};

const els = {
  loadingGate: $("#loadingGate"),
  shell: $("#immersionShell"),
  backgroundA: $("#backgroundA"),
  backgroundB: $("#backgroundB"),
  characterStage: $("#characterStage"),
  characterSprite: $("#characterSprite"),
  characterName: $("#characterName"),
  phaseName: $("#phaseName"),
  scenarioName: $("#scenarioName"),
  toneName: $("#toneName"),
  sceneLabel: $("#sceneLabel"),
  messages: $("#messages"),
  composer: $("#composer"),
  messageInput: $("#messageInput"),
  sendButton: $("#sendButton"),
  backButton: $("#backButton"),
};

boot().catch(fail);

async function boot() {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return returnToWorkspace();
  try {
    state.session = JSON.parse(raw);
  } catch {
    sessionStorage.removeItem(SESSION_KEY);
    return returnToWorkspace();
  }

  const auth = await api("/api/auth/status");
  if (!auth.authenticated) return returnToWorkspace();

  const chatId = state.session?.chat?.id;
  if (!chatId) return returnToWorkspace();
  state.chat = await api(`/api/chats/${chatId}`);

  bindEvents();
  renderSessionMeta();
  renderMessages();
  applyPresentation(state.session.presentation, { initial: true });
  els.loadingGate.hidden = true;
  els.shell.hidden = false;
  requestAnimationFrame(() => els.messageInput.focus());
}

function bindEvents() {
  els.backButton.addEventListener("click", returnToWorkspace);
  els.composer.addEventListener("submit", sendMessage);
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.composer.requestSubmit();
    }
  });
  els.messageInput.addEventListener("input", autoGrowComposer);
}

function renderSessionMeta() {
  els.characterName.textContent = state.session.character_name || "Character";
  els.phaseName.textContent = state.session.phase_name || state.chat.phase_id;
  els.scenarioName.textContent = state.session.scenario_name || state.chat.scenario_name;
  els.toneName.textContent = state.session.tone_name || state.chat.tone_id;
}

function renderMessages() {
  els.messages.replaceChildren();
  for (const message of state.chat.messages || []) {
    addMessage(message.role, message.content);
  }
  scrollMessages();
}

async function sendMessage(event) {
  event.preventDefault();
  const text = els.messageInput.value.trim();
  if (!text || state.busy) return;
  state.busy = true;
  els.sendButton.disabled = true;
  els.messageInput.disabled = true;
  addMessage("user", text);
  els.messageInput.value = "";
  autoGrowComposer();
  const pending = addSystemNote("Composing…");
  try {
    const response = await api(`/api/immersion/${state.chat.id}/messages`, {
      method: "POST",
      body: {
        message: text,
        request_id: newRequestId(),
        current_background_id: state.currentBackgroundId,
        current_location: state.currentLocation,
      },
    });
    pending.remove();
    addMessage("assistant", response.reply);
    applyPresentation(response.presentation);
  } catch (error) {
    pending.remove();
    addSystemNote(
      error instanceof ApiError && error.status === 409
        ? (error.message.includes("OpenRouter") ? "Add an OpenRouter key in the normal Workspace connection panel first." : error.message)
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

function applyPresentation(presentation, { initial = false } = {}) {
  if (!presentation) return;
  document.body.dataset.renderMode = presentation.render_mode || "sprite";
  state.currentBackgroundId = presentation.background_id || state.currentBackgroundId;
  state.currentLocation = presentation.location || state.currentLocation;
  els.sceneLabel.textContent = state.currentLocation || readableSceneName(state.currentBackgroundId);
  if (presentation.background_path) applyBackground(presentation.background_path, initial);

  if (presentation.render_mode === "diary") {
    els.characterStage.classList.add("is-diary");
    els.characterSprite.classList.remove("ready");
    return;
  }

  els.characterStage.classList.remove("is-diary");
  if (presentation.sprite_path) applySprite(presentation.sprite_path, presentation.expression, initial);
  applyMovement(presentation.movement || "idle");
}

function applyBackground(path, initial) {
  const layers = [els.backgroundA, els.backgroundB];
  if (initial || !layers[state.backgroundLayer].getAttribute("src")) {
    const active = layers[state.backgroundLayer];
    active.src = path;
    active.classList.add("active");
    return;
  }
  if (layers[state.backgroundLayer].getAttribute("src") === path) return;
  const nextIndex = state.backgroundLayer === 0 ? 1 : 0;
  const current = layers[state.backgroundLayer];
  const next = layers[nextIndex];
  next.classList.remove("active");
  next.src = path;
  next.onload = () => {
    next.classList.add("active");
    current.classList.remove("active");
    state.backgroundLayer = nextIndex;
  };
}

function applySprite(path, expression, initial) {
  els.characterSprite.dataset.expression = expression || "neutral";
  if (state.spritePath === path) {
    els.characterSprite.classList.add("ready");
    return;
  }
  state.spritePath = path;
  if (!initial) els.characterSprite.classList.remove("ready");
  const preload = new Image();
  preload.src = path;
  preload.onload = () => {
    els.characterSprite.src = path;
    requestAnimationFrame(() => els.characterSprite.classList.add("ready"));
  };
}

function applyMovement(movement) {
  const name = movement || "idle";
  if (name === "approach") state.stageScale = clamp(state.stageScale + .02, .92, 1.10);
  if (name === "retreat") state.stageScale = clamp(state.stageScale - .02, .90, 1.08);
  if (name === "left") state.stageX = clamp(state.stageX - 3.2, -16, 16);
  if (name === "right") state.stageX = clamp(state.stageX + 3.2, -16, 16);
  document.documentElement.style.setProperty("--stage-x", `${state.stageX}vw`);
  document.documentElement.style.setProperty("--stage-scale", state.stageScale.toFixed(3));

  for (const cls of [...els.characterSprite.classList]) {
    if (cls.startsWith("motion-")) els.characterSprite.classList.remove(cls);
  }
  if (name !== "idle") {
    void els.characterSprite.offsetWidth;
    els.characterSprite.classList.add(`motion-${name}`);
    window.setTimeout(() => els.characterSprite.classList.remove(`motion-${name}`), 950);
  }
}

function addMessage(role, content) {
  const article = document.createElement("article");
  article.className = `immersion-message ${role}`;
  const speaker = document.createElement("div");
  speaker.className = "immersion-speaker";
  speaker.textContent = role === "user" ? "You" : (state.session.character_name || "Character");
  const body = document.createElement("div");
  body.className = "immersion-body";
  body.append(renderTranscript(content));
  article.append(speaker, body);
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
    if (match.index > last) appendSegment(fragment, "narrative", source.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("**")) appendSegment(fragment, "action", token.slice(2, -2));
    else if (token.startsWith('"')) appendSegment(fragment, "speech", token.slice(1, -1));
    else appendSegment(fragment, "dev", token.slice(1, -1));
    last = match.index + token.length;
  }
  if (last < source.length) appendSegment(fragment, "narrative", source.slice(last));
  if (!fragment.childNodes.length) appendSegment(fragment, "narrative", source);
  return fragment;
}

function appendSegment(fragment, kind, text) {
  const clean = String(text || "").trim();
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

function readableSceneName(id) {
  return String(id || "scene")
    .replace(/^bg-/, "")
    .replace(/^hp-/, "")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function returnToWorkspace() {
  const chatId = state.chat?.id || state.session?.chat?.id;
  if (chatId) sessionStorage.setItem(RETURN_CHAT_KEY, chatId);
  sessionStorage.removeItem(SESSION_KEY);
  window.location.assign("/");
}

function autoGrowComposer() {
  els.messageInput.style.height = "auto";
  els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 130)}px`;
}

function scrollMessages() {
  requestAnimationFrame(() => { els.messages.scrollTop = els.messages.scrollHeight; });
}

function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

function fail(error) {
  console.error(error);
  els.loadingGate.innerHTML = "";
  const title = document.createElement("strong");
  title.textContent = "Immersion could not start";
  const detail = document.createElement("span");
  detail.textContent = error?.message || String(error);
  detail.style.maxWidth = "560px";
  detail.style.textAlign = "center";
  detail.style.color = "rgba(255,255,255,.55)";
  const back = document.createElement("button");
  back.className = "hud-button";
  back.textContent = "Back to Workspace";
  back.addEventListener("click", returnToWorkspace);
  els.loadingGate.append(title, detail, back);
}
