const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("proteanAssistant", {
  baseUrl: String(process.env.PROTEAN_ASSISTANT_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, ""),
  request: (method, path, body = null) => ipcRenderer.invoke("assistant:request", method, path, body),
  customBackground: () => ipcRenderer.invoke("assistant:custom-background"),
  captureContext: () => ipcRenderer.invoke("assistant:capture"),
  openSearch: (query) => ipcRenderer.invoke("assistant:search", query),
  setClickThrough: (enabled) => ipcRenderer.invoke("assistant:set-click-through", enabled),
  setFocusable: (enabled) => ipcRenderer.invoke("assistant:set-focusable", enabled),
  openWorkspace: () => ipcRenderer.invoke("assistant:open-workspace"),
  quit: () => ipcRenderer.invoke("assistant:quit"),
  onToggleScreen: (callback) => ipcRenderer.on("assistant:toggle-screen", () => callback()),
});
