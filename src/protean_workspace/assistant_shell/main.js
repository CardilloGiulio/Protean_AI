const { app, BrowserWindow, desktopCapturer, globalShortcut, ipcMain, shell } = require("electron");
const { execFile } = require("node:child_process");
const path = require("node:path");

const baseUrl = String(process.env.PROTEAN_ASSISTANT_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const token = String(process.env.PROTEAN_ASSISTANT_TOKEN || "");
let win = null;
let lastExternal = null;
let quitting = false;

function closeForSessionFailure() {
  if (quitting) return;
  quitting = true;
  setImmediate(() => app.quit());
}

if (!token) {
  app.exit(2);
}

function createWindow() {
  win = new BrowserWindow({
    width: 390,
    height: 540,
    minWidth: 310,
    minHeight: 410,
    maxWidth: 620,
    maxHeight: 820,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: false,
    focusable: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: false,
    },
  });
  win.setAlwaysOnTop(true, "pop-up-menu");
  if (typeof win.setVisibleOnAllWorkspaces === "function") {
    try { win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true }); } catch { /* platform-specific */ }
  }
  win.loadFile(path.join(__dirname, "assistant.html"));
  win.once("ready-to-show", () => {
    placeBottomRight();
    win.showInactive();
  });
  win.on("closed", () => { win = null; });
}

function placeBottomRight() {
  if (!win) return;
  const display = require("electron").screen.getDisplayNearestPoint(require("electron").screen.getCursorScreenPoint());
  const area = display.workArea;
  const [width, height] = win.getSize();
  win.setPosition(Math.round(area.x + area.width - width - 20), Math.round(area.y + area.height - height - 20), false);
}

async function apiRequest(method, requestPath, body = null) {
  const allowed = new Set([
    "/api/assistant/session",
    "/api/assistant/session/events",
    "/api/assistant/session/wardrobe",
    "/api/assistant/session/close",
  ]);
  if (!allowed.has(requestPath)) throw new Error("Assistant shell request path is not allowed");
  let response;
  try {
    response = await fetch(`${baseUrl}${requestPath}`, {
      method,
      headers: {
        "Authorization": `Bearer ${token}`,
        ...(body == null ? {} : { "Content-Type": "application/json" }),
      },
      body: body == null ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    closeForSessionFailure();
    throw new Error("Virtual Assistant lost its backend session", { cause: error });
  }
  let data = null;
  try { data = await response.json(); } catch { data = null; }
  if (!response.ok) {
    if (response.status === 401) closeForSessionFailure();
    const message = data && data.detail ? String(data.detail) : `Assistant request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

async function customBackground() {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/assistant/session/background`, {
      headers: { "Authorization": `Bearer ${token}` },
    });
  } catch (error) {
    closeForSessionFailure();
    throw new Error("Custom background is unavailable", { cause: error });
  }
  if (response.status === 401) closeForSessionFailure();
  if (!response.ok) throw new Error("Custom background is unavailable");
  const bytes = Buffer.from(await response.arrayBuffer());
  return `data:${response.headers.get("content-type") || "image/webp"};base64,${bytes.toString("base64")}`;
}

function foregroundWindowWindows() {
  if (process.platform !== "win32") return Promise.resolve(null);
  const script = `
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class ProteanWin32 {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
}
"@;
$h=[ProteanWin32]::GetForegroundWindow();
$sb=New-Object System.Text.StringBuilder 2048;
[void][ProteanWin32]::GetWindowText($h,$sb,$sb.Capacity);
$pidValue=0; [void][ProteanWin32]::GetWindowThreadProcessId($h,[ref]$pidValue);
$p=Get-Process -Id $pidValue -ErrorAction SilentlyContinue;
[PSCustomObject]@{handle=$h.ToInt64();title=$sb.ToString();pid=$pidValue;process=if($p){$p.ProcessName}else{""}} | ConvertTo-Json -Compress
`;
  return new Promise((resolve) => {
    execFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { windowsHide: true, timeout: 2500 }, (error, stdout) => {
      if (error || !stdout) return resolve(null);
      try { resolve(JSON.parse(stdout.trim())); } catch { resolve(null); }
    });
  });
}

async function captureContext() {
  let info = await foregroundWindowWindows();
  if (info && Number(info.pid) !== process.pid && String(info.title || "").trim()) {
    lastExternal = info;
  } else if (lastExternal) {
    info = lastExternal;
  }
  if (!info) return { application: "", window_title: "", image_data_url: "" };

  let imageDataUrl = "";
  try {
    const sources = await desktopCapturer.getSources({
      types: ["window"],
      thumbnailSize: { width: 960, height: 540 },
      fetchWindowIcons: false,
    });
    const handle = String(info.handle || "");
    const title = String(info.title || "").trim();
    const source = sources.find((item) => handle && item.id.startsWith(`window:${handle}:`))
      || sources.find((item) => title && item.name === title)
      || sources.find((item) => title && (item.name.includes(title) || title.includes(item.name)));
    if (source && !source.thumbnail.isEmpty()) {
      imageDataUrl = `data:image/jpeg;base64,${source.thumbnail.toJPEG(68).toString("base64")}`;
    }
  } catch { /* title/app context remains useful */ }
  return {
    application: String(info.process || ""),
    window_title: String(info.title || ""),
    image_data_url: imageDataUrl,
  };
}

ipcMain.handle("assistant:request", async (_event, method, requestPath, body) => {
  return apiRequest(String(method || "GET").toUpperCase(), String(requestPath || ""), body ?? null);
});
ipcMain.handle("assistant:custom-background", customBackground);
ipcMain.handle("assistant:capture", captureContext);
ipcMain.handle("assistant:search", async (_event, query) => {
  const value = String(query || "").trim().slice(0, 1000);
  if (!value) return false;
  await shell.openExternal(`https://duckduckgo.com/?q=${encodeURIComponent(value)}`);
  return true;
});
ipcMain.handle("assistant:set-click-through", (_event, enabled) => {
  if (!win) return false;
  win.setIgnoreMouseEvents(Boolean(enabled), { forward: true });
  return true;
});
ipcMain.handle("assistant:set-focusable", (_event, enabled) => {
  if (!win) return false;
  const value = Boolean(enabled);
  win.setFocusable(value);
  if (value) { win.setIgnoreMouseEvents(false); win.focus(); }
  return true;
});
ipcMain.handle("assistant:open-workspace", async () => {
  await shell.openExternal(`${baseUrl}/?assistant_return=1`);
  return true;
});
ipcMain.handle("assistant:quit", () => {
  quitting = true;
  app.quit();
  return true;
});

app.whenReady().then(() => {
  createWindow();
  globalShortcut.register("CommandOrControl+Shift+Alt+P", () => {
    if (win) win.webContents.send("assistant:toggle-screen");
  });
});

app.on("window-all-closed", () => app.quit());
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("before-quit", () => {
  if (quitting) return;
  fetch(`${baseUrl}/api/assistant/session/close`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` },
  }).catch(() => {});
});
