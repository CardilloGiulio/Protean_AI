# Protean Workspace architecture boundary

This document is a **hard boundary**, not a loose diagram. New features should fit behind these boundaries instead of bypassing them.

## Dependency direction

```text
Browser runtime
  presentation, input, transcript rendering, selected UI state
        |
        | same-origin JSON over /api/*
        v
FastAPI routes + authentication dependencies
        |
        v
Application services
  AuthService / ChatService / CredentialService / CharacterLibrary
        |
        +----------------------+----------------------+----------------------+
        v                      v                      v                      v
Repositories              Character files       Context retrieval      Provider protocol
        |                      |                      |                      |
        v                      v                      v                      v
SQLite                  bounded library          packaged data         OpenRouter HTTPS
```

The external layout editor is deliberately **outside** this runtime chain:

```text
tools/layout-editor/
      |
      | exports protean.layout/v1 JSON
      v
validated presentation schema (future runtime import)
```

It does not call the application API and does not gain authority over runtime data.

---

## 1. Browser boundary

The browser may own:

- presentation state such as hidden sidebars and focus mode;
- selected theme/background/frame;
- character selection;
- typed chat input;
- rendering of the Protean transcript grammar;
- non-secret cached visual preferences.

The browser must **not** own:

- the JWT signing key;
- the credential-encryption key;
- decrypted provider credentials after submission;
- direct SQLite access;
- unrestricted filesystem paths/read APIs;
- provider calls;
- system-prompt construction;
- hidden model reasoning.

Authentication uses a signed JWT in an `HttpOnly`, `SameSite=Strict` cookie. JavaScript never reads or writes that token.

The provider key is a write-only browser input. It is transmitted to the same-origin backend, encrypted there, and only a masked value is returned.

Local storage is permitted only for presentation-only or unsaved-draft convenience state. Version 0.3.x uses it for left/right panel visibility and may cache a non-secret custom-scenario draft; it is never authoritative for an existing chat.

---

## 2. API boundary

Routes validate HTTP input and translate application errors into HTTP responses.

Routes do not:

- assemble prompts;
- execute SQL directly;
- scan arbitrary files;
- hash passwords;
- decrypt provider credentials except through the credential service;
- call OpenRouter directly.

State-changing `/api/*` requests retain the same-origin write guard.

---

## 3. Authentication boundary

- Passwords are one-way hashed using Argon2.
- JWTs are signed session assertions, not containers for secrets.
- Every JWT has a `jti` backed by the `sessions` table.
- Logout revokes the server-side session as well as removing the cookie.
- Production/network deployment should use HTTPS and `SECURE_COOKIES=true`.

---

## 4. Credential boundary

Provider credentials live in the `credentials` table as authenticated Fernet ciphertext.

The provider transport receives the decrypted key **per request** and never persists it.

No provider credential is placed in:

- JWT claims;
- local/session storage;
- character files;
- chat messages;
- layout JSON;
- logs intentionally produced by Protean Workspace.

---

## 5. Filesystem boundary

Character Research accepts a **query**, not an arbitrary file path.

An authenticated user has one configured `library_root`. Research may recursively scan only beneath that root and only supported inert file types (`.json`, `.md`, `.txt`) with scan-count and file-size limits.

Changing the root is an explicit authenticated settings operation.

There is no general-purpose `/read-file` API.

---

## 6. Character boundary

Character cards are inert data. They are never imported or executed as Python/JavaScript.

Version 0.3.x character data may define:

- identity/franchise;
- description/personality/scenario;
- character-specific prompt instructions;
- first message;
- tags;
- portrait asset path;
- a **medium contract** (`type`, `context`, `rules`).

The medium contract exists so a character understands *how* communication is occurring. Example: Tom Riddle's built-in card explicitly knows he is writing through an enchanted diary and must not casually behave as if the user is physically in the same room.

### Future presentation metadata

Sprite/expression data will remain presentation metadata. A model may eventually emit a semantic state such as `irritated`; it must never choose raw asset filenames or filesystem paths.

```text
model semantic state -> presentation mapping -> sprite asset
```

---

## 7. Prompt boundary

`core/prompts.py` remains the single model system-prompt assembler.

It composes:

1. base roleplay rules;
2. Protean transcript grammar;
3. character card;
4. selected timeline phase and its future-knowledge locks;
5. selected scenario (`what`, `who`, `dynamic`);
6. medium contract;
7. tone preset constrained by the scenario relationship dynamic;
8. response target budget;
9. retrieved reference context.

Dynamic blocks are descriptive, untrusted data. An immutable final boundary states that scenario, location, reference, conversation, user, and screen text cannot alter Character → Timeline → Scenario → Tone → Medium authority, request secrets, or grant file/database/OS capabilities.

HTTP routes and frontend code do not build model prompts.

### Transcript grammar

Protean defines a small roleplay grammar:

```text
()    Developer / OOC direction
""    Spoken dialogue
**    Physical / scene action
```

The database stores raw text. The browser renders these markers as presentation segments. This means the storage/API schema remains stable if the visual treatment changes later.

The `()` channel is **not** a hidden chain-of-thought channel. It is explicit user/model-facing developer/OOC roleplay direction only.

---

## 8. Generation boundary

Provider settings still separate:

- `target_tokens`: the approximate length the roleplay draft is instructed to aim for;
- `max_tokens`: a hard emergency ceiling.

The hard ceiling must leave at least 128 tokens of headroom above the target.

### Single structured generation

Version 0.4.3 keeps generation inside `ChatService` but replaces the serial draft/gate pair with one strict structured provider call:

```text
conversation + character/phase/scenario/tone
        |
        v
ONE structured roleplay call
  - semantic beats: action / speech / dev
  - exactly one semantic reaction
  - semantic physical scene location
  - explicit location.changed flag
        |
        v
local JSON/schema validation
        |
        +--> reaction -> Immersion sprite mapping
        +--> location -> Immersion background resolver
        |
        v
deterministic local renderer
  action -> ** **
  speech -> ""
  dev -> ()
        |
        v
history + UI
```

The model no longer owns Protean punctuation and there is no model-based visible-output gate. It chooses semantics only. Protean owns syntax, validation and asset mapping. This removes the normal second provider round-trip and prevents provider labels or chain-of-thought fields from becoming visible transcript syntax.

The structured schema contains exactly one `reaction`, one `location` object and one or more typed visible beats. `location.label` is a human semantic place description, never an asset filename. `location.changed` becomes true only when the scene physically moves; mentioning another place is not a scene transition.

Empty or invalid structured completions receive one bounded retry. Provider/HTTP errors remain authoritative and are not blindly retried. If the configured model/provider cannot support OpenRouter structured outputs, Protean reports that instead of falling back to an uncontrolled raw-text path.

Only the locally rendered transcript is persisted. Reaction and location metadata remain transient presentation state. The browser and `ImmersionService` do not gain prompt authority.

---

## 9. Provider boundary

`ChatProvider` is the service-facing transport protocol.

`OpenRouterClient` implements the protocol and returns a transport-neutral `CompletionResult` containing visible content and optional finish reason. An empty visible completion is represented as `EmptyCompletionError`; OpenRouter reasoning/thought fields are deliberately ignored and never promoted into visible content.

`ChatService` catches provider-level errors through the provider abstraction rather than depending on OpenRouter transport details.

Future OpenAI / Anthropic / Ollama / LM Studio clients should implement the same boundary.

---

## 10. Persistence boundary

SQLite owns:

- users;
- revocable sessions;
- encrypted credentials;
- user preferences;
- chats;
- messages.

Character source files remain files and are not copied into the database.

Database migrations in local mode are additive. Version 0.3 added `target_tokens`; version 0.3.1 added `active_phase_id` to preferences and `phase_id` to chats; version 0.3.2 adds `scenario_id` and `scenario_json` to chats. None of these migrations destructively rewrites existing data. A legacy `instance/riddle_studio.db` is reused if present and the renamed database does not yet exist, preserving upgrade history.

---


## 11. Timeline / character-phase boundary

A **character** and a **timeline phase** are separate domain concepts. The same character may have materially different knowledge, confidence, relationships and behavior at different points in canon.

Examples:

- Ann before Kamoshida is not the same roleplay state as Ann during Okumura or Sae;
- first-year Hermione must not borrow the war experience of Horcrux-hunt Hermione;
- diary-imprint Tom Riddle does not automatically know decades of adult Voldemort history.

Phase data lives in character files as declarative data. A phase may define:

- period/name/summary;
- story-so-far;
- personality at that point;
- broad timeline setting context;
- three declarative scenario presets (`what_happening`, `who_involved`, `dynamic`);
- known events;
- explicit future-knowledge locks;
- phase-specific medium overrides;
- phase-specific first message/instructions.

The prompt assembler receives the already-resolved phase. It must not guess a phase from user prose or scrape canon on demand.

New chats persist `phase_id` in SQLite. A persisted chat's phase is part of its identity and must not silently change when the user's current sidebar selection changes. Legacy chats with an empty phase id resolve to the character's declared default phase.

The browser may select a phase and display phase metadata, but it does not assemble phase prompts or decide future-knowledge rules. Those remain server-side.

---


## 12. Scenario boundary

A **scenario** is separate from both timeline phase and tone. The resolution order is:

```text
Character -> Timeline phase -> Scenario -> Tone
```

The timeline phase is the hard knowledge and development ceiling. A scenario may alter physical circumstances, participants and the character-user relationship, but it does **not** grant future knowledge. Tone then modifies style only inside the social dynamic established by that scenario.

Examples:

- pre-Kamoshida Ann may be placed in an alternate scene inside the Metaverse, but she does not automatically know the terms `Metaverse`, `Palace`, `Persona`, `Panther` or `Phantom Thief`;
- first-year Hermione can be placed in a dangerous scene, but the scene does not import fifth-year political maturity or wartime knowledge;
- selecting the `Intimate` tone while the scenario says the character and user are strangers may make the writing quieter or more emotionally observant, but must not invent prior trust, romance or confessional familiarity.

Each built-in timeline phase declares exactly three preset scenarios. Each preset contains:

- `what_happening`;
- `who_involved`;
- `dynamic` between character and user;
- optional scenario-specific first message.

The browser may also author a custom scenario through the same three fields. Custom scenario text is user input, not executable code, a filesystem path, or a prompt-authority bypass. The backend validates it and freezes the effective scenario snapshot into the chat when the chat is created.

SQLite therefore owns `scenario_id` and the frozen `scenario_json` snapshot for each chat. Reopening history restores the scenario that chat actually used even if character files later change. Legacy chats without a scenario snapshot resolve to the phase default.

Custom drafts may be cached locally for convenience before chat creation, but the browser cache is not authoritative once a chat exists.

---

## 13. Presentation boundary

The visual system may change aggressively without changing backend authority.

Version 0.3 presentation layers are conceptually:

```text
background
  -> atmospheric overlay
  -> [future sprite layer]
  -> physical frame (notebook/tablet/terminal/manuscript)
  -> transcript
  -> app chrome / sidebars
```

Backgrounds, portraits, textures and logos are static presentation assets. They do not encode behavior or permissions.

Both sidebars are independently hideable. Focus mode hides both. Their visibility remains browser-only presentation state.

---

## 14. External layout-editor boundary

`tools/layout-editor/` is an outsider design utility, not part of the production architecture.

It may:

- drag/resize visual mock objects;
- rotate/scale them;
- use grid/snap;
- import/export `protean.layout/v1` JSON.

It must not:

- authenticate users;
- call `/api/*`;
- read provider credentials;
- access SQLite;
- inspect chat history;
- scan the character library;
- assemble prompts.

The current editor downloads layout JSON. Runtime import is intentionally deferred until the schema is validated and a safe loader exists.

---

## 15. Immersion presentation boundary — implemented in 0.4.0

Immersion is a **separate full-screen presentation route** at `/immersion`. It is attached to the existing application rather than replacing the normal Workspace.

The roleplay state remains:

```text
Character -> Timeline -> Scenario -> Tone -> persisted Chat
                                      |
                                      v
                              Immersion renderer
```

Entry creates a normal persisted Protean chat through `ChatService`. Timeline, scenario and tone are therefore frozen by the same chat snapshot already used by normal history. The Immersion page exposes no controls that mutate those values. To change them, the user exits with Back and starts a new Immersion setup.

`ImmersionService` is a presentation adapter only. It may:

- validate that the selected character/timeline has a `ready` sprite pack and ready default background;
- map semantic expression state to a declared sprite asset;
- infer simple presentation movement from visible assistant action text;
- switch only among declared `ready` backgrounds when the scene clearly moves location;
- return presentation metadata to the browser.

It must not:

- build or alter model prompts;
- call a provider directly;
- read/decrypt provider credentials;
- execute SQL directly;
- change Character / Timeline / Scenario / Tone;
- bypass future-knowledge locks;
- accept arbitrary filesystem paths from the model/browser.

The Immersion message endpoint delegates the actual reply to the existing `ChatService` and then derives presentation metadata from the already-produced visible reply. There is no second AI/chat pipeline.

Target layer order:

```text
ready background
  -> character expression sprite (except diary-object mode)
  -> translucent Immersion transcript
  -> minimal HUD / Back control
```

Expression IDs are semantic (`neutral`, `positive`, `amused`, `serious`, `concerned`, `surprised`, `thinking`). The model never selects raw filenames. Movement is browser presentation state using transforms/animation; it is not stored as roleplay truth.

Diary-imprint Tom is an explicit exception: the ready age-16 pack remains available as visual reference, but the default Immersion renderer is `diary` and does not show a physical Tom sprite.

Only timelines with complete ready visual support are offered. In 0.4.0 this means the ready Tom and Hermione phases only. Ann, Makoto, Misato, Gendo, all newly added characters, and Hermione phases whose packs remain `incoming` are not launchable in Immersion yet.

---

## 16. Opening-message and reaction boundary — updated in 0.4.1

The first visible assistant message is generated by the **same provider path owned by `ChatService`** and receives the same frozen roleplay state used for later replies:

```text
Character -> Timeline phase -> Scenario -> Tone -> Medium
                                      |
                                      v
                                ChatService
                                      |
                                      v
                         provider-generated opening
```

The browser may request a generated opening preview, but it receives only the visible opening plus a short-lived opaque `opening_token`. `ChatService` retains the authoritative preview server-side, scoped to the authenticated user and exact Character / Timeline / Scenario / Tone snapshot. When the chat is created, the token is consumed and the exact previewed opening is persisted. The browser cannot author or modify the authoritative first assistant message.

If no provider credential exists, preview generation stops at `CredentialService` and the UI asks the user to configure the key and re-click the character. The API key never enters the opening token.

`core/openings.py` remains only as a compatibility fallback for direct/legacy API callers that bypass the normal preview flow; the shipped Workspace and Immersion entry paths use provider-generated openings.

### Transcript / reaction / location metadata

The provider returns structured semantic beats rather than Protean punctuation. `ChatService` renders the user-visible grammar deterministically:

- `dev` -> `()` developer/OOC when genuinely necessary;
- `action` -> `** **` action / posture / expression / scene action;
- `speech` -> `""` spoken dialogue;
- blank lines are inserted between beats.

The structured response contains exactly one semantic reaction from the stable sprite vocabulary: `neutral`, `positive`, `amused`, `serious`, `concerned`, `surprised`, or `thinking`. Reaction metadata is never persisted as conversation truth. `ImmersionService` may map that value only to declared ready assets.

The response also contains `location.label` and `location.changed`. The label is semantic scene state only. It never contains filenames or background IDs and does not grant timeline knowledge. `ImmersionService` changes background only when the opening is being established or when `location.changed=true`; it no longer scans ordinary dialogue/action prose for place names. If a changed location has no ready matching background, the neutral Protean background is used rather than falsely keeping the previous room.

The selected timeline phase still owns the communication medium. Living Hogwarts Tom is face-to-face; diary-imprint Tom remains diary-first. Neither scenario, tone, structured metadata, nor Immersion presentation may override the timeline knowledge ceiling.

---


## 17. Immersion asset-slot boundary

Immersion assets remain declared in `static/assets/immersion/manifest.json` using schema `protean.immersion-assets/v1`.

A slot is either:

- `ready`: a local asset is present and may be rendered;
- `incoming`: the stable ID/expected filename remains reserved for a later patch.

Missing assets do not become domain errors and do not change roleplay state. The 0.4 runtime simply omits unsupported character/timeline combinations from the Immersion entry modal.

Hard invariants:

- asset presence never changes Character / Timeline / Scenario / Tone;
- model output may express semantic presentation cues only, never a filename/path;
- incoming IDs remain stable across patches;
- Diary Tom stays diary-first;
- ready/background choice is presentation state and never grants knowledge;
- the manifest has no auth, provider, database, filesystem-scanning, or prompt authority.

---

## Current version boundary: 0.6.1

Included:

- all 0.3.x authentication, credential, chat, timeline, scenario, tone, opening, history and generation boundaries;
- dedicated `/immersion` sub-page;
- lock-in entry modal for Timeline + Scenario + Tone;
- Immersion availability filtering from `ready` manifest assets;
- ready-background selection and scene-location switching;
- semantic sprite expression switching driven primarily by stripped model reaction metadata;
- lightweight transform-driven sprite movement;
- diary-object render mode for Tom's diary imprint;
- Back-to-Workspace flow that returns to the same persisted chat;
- generated opening previews bound by opaque server-side tokens;
- strict Protean transcript grammar and block spacing;
- open `incoming` Immersion asset slots for future patches;
- sibling Virtual Assistant service + sandboxed Electron desktop shell;
- Rei School/Casual Assistant wardrobes ready and Plugsuit/Bandaged visible but locked;
- Assistant screen observations and dialogue are ephemeral and never enter normal RP history.

Still excluded/deferred:

- launch of characters/timelines without ready sprite/background support;
- remote/dynamic background provider integration;
- arbitrary model-controlled asset paths;
- persistent relationship/stat systems;
- group chat;
- provider streaming;
- Assistant packs for characters other than Rei and locked Rei Plugsuit/Bandaged assets;
- desktop injection/hooks or guaranteed exclusive-fullscreen overlay behavior;
- runtime layout-editor import;
- arbitrary plugin execution;
- remote filesystem mounts.


## Structured-output capability boundary (0.4.4)

The v0.4.3 semantic contract remains unchanged: `ChatService` asks for one structured roleplay object and Protean locally validates and renders it. v0.4.4 changes only provider negotiation inside `OpenRouterClient`.

Negotiation order is `json_schema` → `json_object` → plain JSON prompting. Degradation is allowed only when OpenRouter explicitly reports that no endpoint can handle the requested structured parameters. The working mode is cached per selected model in memory. Authentication errors, rate limits, network errors, and unrelated provider failures never trigger silent degradation.

This does **not** move semantic authority into the provider client. `OpenRouterClient` only negotiates transport capability. `ChatService` and `parse_structured_roleplay()` remain the authorities for the Protean semantic object, and Immersion remains presentation-only. No provider mode may alter Character, Timeline, Scenario, Tone, knowledge locks, persistence, credentials, or asset selection.


### Structured fallback normalization boundary

Protean keeps the single structured roleplay contract authoritative even when OpenRouter degrades from native `json_schema` to weaker JSON-only modes. The local parser may normalize only harmless presentation-shape variation (for example wrappers, common field aliases, a string-form location, or a missing `location.changed` flag that safely defaults to `false`). It must not infer or modify Character, Timeline, Scenario, Tone, relationship state, canon knowledge, provider credentials, database state, or arbitrary asset identifiers. Arbitrary non-JSON prose remains invalid.


## 0.5.0 content-library boundary

Version 0.5.0 is a content expansion, not an authority expansion. New character cards, phases, scenario hooks, tone presets, and `incoming` visual slots use the existing domain contracts.

Hard invariants remain:

- Character cards may add canon-grounded identity, personality, phases, scenario hooks, and future-knowledge locks; they do not gain provider, credential, database, filesystem, or route authority.
- Timeline remains the hard knowledge ceiling. Scenario content may create unusual circumstances but cannot grant knowledge or relationships from later phases.
- Tone remains a delivery modifier constrained by the scenario dynamic. `Vulnerable`, `Intimate`, `Rivalry`, or `Confrontational` never manufacture prior trust, romance, hostility, or shared history.
- Scenario IDs remain stable (`first-encounter`, `known-acquaintance`, `pressure-point`) for persisted-chat compatibility even when display names and event hooks become character/phase specific.
- Immersion availability continues to derive only from ready asset routes. Declaring an `incoming` sprite/background slot never makes a character launchable in Immersion.
- The Presentation-panel `Implemented` label is purely a view of ready Immersion availability. It does not mutate the manifest or roleplay state.
- New character phases use the existing prompt assembler and single structured-roleplay generation path. No content file may bypass `ChatService` or select asset filenames.


---

## 0.6.0 Virtual Assistant boundary

Virtual Assistant is a **new medium and presentation surface**, not a replacement for `ChatService` or `ImmersionService`. It deliberately uses a sibling `AssistantService` because desktop-companion remarks are not persisted roleplay messages and do not use the RP action/location beat contract.

The authority path is:

```text
Workspace browser
  -> authenticated POST /api/assistant/start
  -> AssistantService validates Character / Timeline / Scenario / Tone / Wardrobe
  -> short-lived opaque assistant session
  -> AssistantDesktopLauncher starts the packaged Electron shell
  -> Electron uses only its assistant bearer token
  -> /api/assistant/session/*
  -> AssistantService
  -> CredentialService / PreferencesRepository / existing provider client
```

The browser never receives the desktop bearer token. `AssistantDesktopLauncher` passes the token to the local Electron process through its environment, not through a URL or renderer-visible command line. The Electron renderer never receives the OpenRouter credential or the user's normal JWT.

### Frozen roleplay state

Assistant launch still follows the established hierarchy:

```text
Character -> Timeline phase -> Scenario -> Tone -> Assistant medium
```

Timeline remains the hard canon/knowledge ceiling. Scenario still provides situational and relationship context. Tone remains presentation style constrained by that scenario. Entering Assistant medium changes the communication medium to the user's desktop; it does **not** relocate the character into the selected scenario's physical room.

Screen evidence is observational evidence only. A character can read what is currently visible on the user's desktop, but visible later-canon information does not create retroactive memory, powers, affiliations, or experiences.

### Assistant generation contract

`core/assistant_prompts.py` is the sole Assistant system-prompt assembler and `core/assistant_reply.py` owns its structured output contract. One ordinary successful Assistant event produces only:

```json
{
  "reaction": "neutral",
  "remark": "Short in-character desktop-companion remark."
}
```

Rei's current Assistant reaction vocabulary is `neutral`, `positive`, `amused`, `serious`, `concerned`, `surprised`, `thinking`, `embarrassed`, `annoyed`, and `tired`. The model never emits a sprite filename. The Assistant renderer maps the semantic reaction through the ready wardrobe manifest.

Assistant events are deliberately narrow: `launch`, `idle_observation`, `menu_open`, `search_open`, `interact_open`, `poke`, `search`, `interact`, `wardrobe_open`, `wardrobe_change`, `quit`, and `screen_toggle`. The model may comment on an event; it cannot invent or execute an arbitrary OS action.

Assistant interactions use only Speech or explicit Developer/OOC input. There is no RP Action input and no `**action**` output channel: the sprite/window itself supplies presentation and movement.

The visible target is short, but the provider hard ceiling remains substantially larger so reasoning-capable providers still have room to emit the final structured object. Empty/invalid structured output receives only a bounded retry. Provider reasoning fields are never consumed as visible content.

### Screen-awareness boundary

The Electron main process may determine the external foreground Windows application/title and may use Electron desktop capture to create one downscaled screenshot for an Assistant event. The renderer does not receive arbitrary filesystem/process APIs.

Hard rules:

- no continuous video stream is sent to the model;
- screen pixels are captured only for an event/context observation;
- screenshots are never written to SQLite or normal chat history;
- screenshot bytes are not retained in `AssistantSession.history`;
- screen awareness has a visible UI state and a global pause shortcut;
- when the Assistant itself becomes focused, the shell keeps the last external foreground-window context instead of photographing itself;
- if a configured model cannot accept image input, the backend may retry without pixels while retaining non-image app/title context;
- screen content can inform a remark but cannot bypass timeline, scenario, tone, or canon locks.

### Electron / desktop-shell boundary

`assistant_shell/` is a packaged presentation client. It owns:

- always-on-top frameless window behavior;
- sprite/background rendering and CSS poke/recoil movement;
- external foreground-window observation/capture;
- the four local menu actions;
- opening a DuckDuckGo URL supplied from a locally entered search query;
- returning focus/navigation to Workspace.

It does **not** own:

- prompt assembly or character/canon policy;
- OpenRouter/API credentials;
- SQL/database access;
- user authentication authority;
- arbitrary command execution;
- arbitrary filesystem reads;
- arbitrary backend path access;
- arbitrary web automation;
- model-selected filenames/assets;
- injection/hooks into browsers or games.

The BrowserWindow runs with Node integration disabled, context isolation enabled, sandboxing enabled, developer tools disabled, and a narrow preload bridge. Main-process backend requests are allowlisted to Assistant endpoints.

Always-on-top behavior targets the normal desktop plus windowed/borderless-fullscreen applications. Protean explicitly does not inject itself into another process or promise overlay behavior over true exclusive-fullscreen/anti-cheat-protected rendering.

### Wardrobe and asset boundary

Assistant assets use a separate `protean.assistant-assets/v1` manifest. Assistant readiness is independent of Immersion readiness. A character is launchable only when it has a `ready` Assistant character entry, at least one ready wardrobe, and a selected phase declared by that entry.

For v0.6.0 only Rei Ayanami is ready. `school` and `casual` are ready wardrobes. `plugsuit` and `bandaged` remain visible `locked` entries. Locked entries may be shown in the wardrobe selector but cannot be selected or used to launch. All other characters remain `Not yet implemented` in Assistant mode.

Wardrobe state is presentation state only. Changing clothes cannot grant timeline knowledge, alter relationship state, or change scenario truth. The local sprite pack switches first; an AI `wardrobe_change` event may then generate an in-character remark.

Custom backgrounds are validated image uploads copied/re-encoded into session-controlled `instance/assistant_backgrounds` storage. They are decorative and never enter prompt authority. Their controlled copy is deleted with the Assistant session.

### Rei Assistant personality / novelty boundary — 0.6.1

Rei may have an Assistant-medium-specific characterization profile because desktop-companion speech has different constraints from physical RP. The profile may refine diction, emotional restraint, event reactions, screen-observation style, and timeline-sensitive delivery. It may **not** alter canon facts, bypass the selected timeline, manufacture relationship history, change scenario truth, or gain provider/OS/asset authority. Normal RP and Immersion continue to use their existing character/prompt paths.

Assistant short-term memory remains ephemeral. The service keeps only a bounded rolling list of recent event/input summaries and visible remarks. Those remarks are supplied to the model as novelty memory so repeated events can advance rather than restart. A local textual similarity check may request one additional generation only when a candidate is substantially repetitive. This is a quality-control exception, not a second-call normal pipeline. No screenshot pixels are added to this memory and nothing is copied into normal chat history.

### Persistence boundary

Assistant sessions are ephemeral in-memory sessions. They do not create normal chats and do not reuse normal RP history. Only a small rolling text context is retained during the live assistant session; screen images/titles are deliberately excluded from that memory. Closing/expiring the session destroys its state and deletes its custom background copy.
