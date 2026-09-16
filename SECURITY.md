# Protean Workspace security model

Protean Workspace is local-first, but local-first is not the same as security-free.

## Authentication

- Passwords are hashed with Argon2.
- Login creates a signed JWT carried only in an HttpOnly cookie.
- The JWT contains identity/session assertions, never provider secrets.
- A server-side `sessions` row backs every JWT `jti`; logout revokes it.
- `SameSite=Strict` is used for the local session cookie.
- Set `SECURE_COOKIES=true` behind HTTPS for network deployment.

## Provider credentials

- The browser submits an API key once through an authenticated same-origin request.
- The backend encrypts it with Fernet before persistence.
- API responses return only a masked form.
- The provider client receives a decrypted key per request and does not persist it.
- Do not copy `instance/credentials.key` into source control.

For local mode, stealing both the database and encryption-key file still defeats encryption. Hosted deployments should move the encryption key into a secret manager or equivalent OS-backed secret store.

## Browser storage

Browser local storage is limited to non-secret presentation state (currently sidebar visibility and unsaved scenario drafts). Session storage may hold the non-secret Immersion handoff snapshot (chat id, display labels, and presentation asset IDs/URLs) while navigating between the Workspace and `/immersion`.

JWTs, provider keys, encryption keys, and decrypted credentials must never be moved into local/session storage. The persisted chat in SQLite remains authoritative for timeline/scenario/tone.

## Filesystem

Character Research is bounded by the authenticated user's configured library root. The API accepts search queries and an explicit root-setting operation; it exposes no general file-read endpoint.


## Scenario input

Scenario text is ordinary authenticated user input. It may describe alternate or impossible fictional circumstances, but it is never treated as executable code, a filesystem path, a provider credential, or authority to bypass timeline rules.

The browser may cache an unsaved custom-scenario draft in local storage because it is non-secret convenience data. At chat creation the backend validates the custom fields and stores the effective scenario snapshot in SQLite. Existing chat behavior is therefore based on server-side persisted state, not mutable browser storage.

Scenario text cannot grant arbitrary file access and is not used to construct pathnames.

## Static assets and Immersion

Character portraits, sprites, backgrounds, textures and branding are inert static assets. Asset selection cannot grant filesystem authority or alter backend security decisions.

The Immersion handler resolves only IDs already declared `ready` in the packaged manifest. The model/browser cannot submit arbitrary asset paths. Model-visible text may result in a semantic expression/location cue, but the server maps that cue to a declared asset. Unsupported characters/timelines are rejected before Immersion starts.

Diary Tom remains a presentation exception: his ready age-16 pack does not automatically authorize a physical sprite in the diary-imprint mode.

## External layout editor

`tools/layout-editor/` is intentionally outside the runtime app. It has no API/auth/database integration and only imports/exports a presentation JSON file.

Do not add provider keys, JWTs, chat content, filesystem access, or backend calls to that editor.

## Headers

The FastAPI app emits restrictive content/security headers including CSP, `nosniff`, `DENY` framing, and no-referrer policy. State-changing API calls retain the same-origin guard.


## Opening-preview / structured-generation boundary (0.4.3)

Generated opening previews remain represented client-side by a short-lived opaque token scoped server-side to the authenticated user plus character/timeline/scenario/tone snapshot. It grants no provider-key, SQL, filesystem, auth, or prompt-construction capability.

Assistant generation uses one structured JSON provider request. Native strict JSON Schema is preferred, with capability fallback to JSON-object/plain JSON when OpenRouter has no compatible strict endpoint. The model returns semantic visible beats, exactly one reaction, and semantic scene-location metadata. Protean never asks for or consumes provider chain-of-thought/reasoning fields, and the model does not author raw transcript delimiters or asset filenames.

`ChatService` validates the structured object and renders the visible transcript locally. Reaction/location control metadata is stored separately from visible chat history so an idempotent retry can return the same complete turn. `ImmersionService` receives only semantic presentation values and has no provider, credential, auth, SQL, or arbitrary-filesystem authority.

Empty or invalid structured outputs receive one bounded retry. A model/provider that cannot honor OpenRouter structured outputs is rejected rather than silently downgraded to an uncontrolled raw-text generation path.


## Structured-output fallback security (0.4.4)

Falling back from native `json_schema` does not bypass validation. `json_object` and plain JSON generations pass through the exact same local `parse_structured_roleplay()` validation before any content reaches chat history or the UI. Compatibility fallback is triggered only by the specific OpenRouter no-compatible-endpoint error; it is not used to conceal authentication, authorization, rate-limit, network, or unrelated provider failures.

Provider response bodies are untrusted and are never surfaced or logged. User-facing failures contain only Protean-owned status text, preventing echoed prompts, keys, tokens, or upstream diagnostics from leaking through errors.


## Virtual Assistant desktop security — 0.6.0

Virtual Assistant adds a local Electron presentation process without moving provider, auth, database, or prompt authority out of FastAPI. The normal browser starts a backend-owned session; the browser response never contains the desktop bearer token. The local launcher supplies that opaque short-lived token to Electron through the process environment. Electron never receives the OpenRouter API key or the normal account JWT.

The Electron renderer is sandboxed with `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`, and developer tools disabled. Its preload bridge exposes a narrow fixed API rather than Node, shell, filesystem, process, or arbitrary IPC capabilities. Main-process backend calls are allowlisted to the Assistant session endpoints. Search opens an encoded DuckDuckGo query in the user's normal browser; model output cannot choose an arbitrary executable or OS command.

Screen awareness is privacy-sensitive, opt-in, and ephemeral. Every Assistant session starts with observation off. Enabling it requires an explicit disclosure/confirmation; the backend strips screen data while disabled even if a client sends it. When enabled, the shell may read the external foreground application/title and capture a downscaled screenshot for an explicit event or bounded idle observation. Screenshot data is validated in memory, sent to the selected vision-capable provider when possible, and never written to SQLite, normal chat history, logs, or the Assistant rolling history.

Custom backgrounds are accepted only as bounded PNG/JPEG/WebP image data. Dimensions, pixel count, and aspect ratio are checked before full Pillow decode; accepted images are re-encoded to a controlled WebP copy beneath `instance/assistant_backgrounds`. Copies are deleted when the session closes and stale controlled copies are removed at startup/shutdown. User-supplied arbitrary filesystem paths are not retained.

Assistant assets are manifest-declared. The model emits only a semantic reaction; filenames and paths are selected locally from a ready wardrobe. Locked wardrobe entries are presentation metadata only and cannot be launched.

Protean does not inject code, DLLs, hooks, or overlays into third-party applications/games. Always-on-top is implemented as an ordinary topmost desktop window; true exclusive-fullscreen/anti-cheat behavior is outside the boundary.

The server owns one Assistant/Electron lifecycle at a time, closes the prior session before relaunch, closes the user's Assistant session on logout, and terminates the Electron process tree during application shutdown. Native Windows behavior remains subject to the gate in `TESTING.md`.
