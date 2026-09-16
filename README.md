# Protean Workspace 0.6.1 RC2

Protean Workspace is a local-first character roleplay workspace with persistent history, bounded character research, encrypted provider credentials, character-aware presentation and multiple diegetic chat surfaces.

RC2 is stabilization-only. See [RC2 scope](RC2-SCOPE.md) and [release status](RC2-RELEASE-STATUS.md), then read [Privacy](PRIVACY.md), [IP Notice](IP-NOTICE.md), [Testing and release gate](TESTING.md), [Known limitations](LIMITATIONS.md), and [Security](SECURITY.md) before distribution.

## Fast Windows start

1. Extract the ZIP completely.
2. Double-click `install.bat` once.
3. Double-click `start.bat` whenever you want to use Protean Workspace.
4. Open `http://127.0.0.1:8000` if the browser does not open automatically.

The release has exactly two Windows entry points: `install.bat` and `start.bat`. The installer prepares and verifies both the Python workspace and the Electron Assistant runtime. Startup reruns that same installer if either runtime is missing.

## Manual install

Run commands from the directory that contains `pyproject.toml`:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --requirement requirements-lock.txt
py -m pip install --no-deps --no-build-isolation -e .
py -m uvicorn protean_workspace.main:app --host 127.0.0.1 --port 8000
```

## First launch

The application asks you to create a local owner username/password. After authentication, paste your OpenRouter key into the right workspace panel. The browser sends it to the backend, which encrypts it before persistence. The plaintext key is never returned to the frontend.

## Immersion highlights

- New dedicated `/immersion` full-screen sub-page.
- Entry modal locks **Timeline + Scenario + Tone** before the scene starts.
- Immersion creates and uses a normal persisted Protean chat; history remains the same system you already use.
- The launch button appears only for characters with at least one fully ready visual timeline.
- Current ready characters: **Tom Riddle** and **Hermione Granger** for the phases backed by supplied sprite/background assets.
- Ann, Makoto, Misato, Gendo, the newly added characters, and unsupported Hermione phases remain intentionally unavailable until their visual packs arrive.
- Sprites switch semantic expressions and apply small interactive movement transforms.
- Backgrounds cross-fade between ready scene assets when the visible scene clearly changes location.
- Diary-imprint Tom uses the diary background/object mode and does not render a physical Tom sprite by default.
- All missing visual slots remain `incoming` in `static/assets/immersion/manifest.json`.

### Using Immersion

1. Select Tom or Hermione in the normal Workspace.
2. Click **Immersion** in the top bar.
3. Choose one of the supported Timeline phases, then Scenario and Tone.
4. Click **Enter scene**. These three values are now locked for that session.
5. Use **Back** to return to the normal Workspace; Protean reloads the same saved chat in history.

If the Immersion button is not shown, that character currently has no complete ready sprite/background combination.

## Virtual Assistant — 0.6.1 RC2

Virtual Assistant is a separate desktop companion mode. The normal Workspace remains the launch/configuration surface; after selecting **Character + Timeline + Scenario + Tone + Wardrobe + Background**, Protean creates a short-lived assistant session, launches the packaged Electron shell, and redirects the browser to `/assistant` as a bridge page.

The first ready Assistant character is **Rei Ayanami**. Her available wardrobes are:

- **School Uniform** — ready;
- **Casual** — ready;
- **Plugsuit** — visible but locked;
- **Bandaged / Wounded** — visible but locked.

Each ready Rei wardrobe has ten semantic expressions: `neutral`, `positive`, `amused`, `serious`, `concerned`, `surprised`, `thinking`, `embarrassed`, `annoyed`, and `tired`. Other characters remain **Not yet implemented** for Virtual Assistant until their assistant-specific visual packs are ready. Assistant readiness is independent from Immersion readiness.

### Rei personality and short-term remark memory

Rei now has an Assistant-specific characterization layer on top of the ordinary character/timeline/scenario/tone contract. It emphasizes sparse literal speech, restrained emotional shifts, understated curiosity, quiet dry humor, phase-sensitive warmth/autonomy, and screen-aware observations that do not turn her into a generic friendly chatbot. This layer refines delivery only; the selected timeline remains the knowledge ceiling.

The live Assistant session already keeps a small rolling text context. v0.6.1 uses that context explicitly as novelty memory: recent remarks are shown to the model with a rule not to repeat the same observation, opening, joke, or conclusion. Protean also checks the last few visible remarks locally; a substantially repeated line triggers one conditional novelty correction. Screenshots are still never stored in this memory and the memory disappears with the Assistant session.

### Assistant interaction model

A single click on the sprite opens four actions: **Search online**, **Interact**, **Wardrobe**, and **Quit**. Multiple rapid clicks are treated as a poke burst. Search opens a normal DuckDuckGo results page after an in-character acknowledgement. Interact accepts only **Speech** or **Developer/OOC** text; there is no action channel because the desktop companion is not a physical roleplay scene. Wardrobe switching is immediate presentation state and then receives an AI-generated in-character remark. Quit also receives a final remark before the companion closes and returns to Workspace.

Screen awareness starts **off** for every Assistant session. Enabling it requires an explicit confirmation describing what will be sent. While enabled, the shell observes the current external foreground application/window and may capture one downscaled screenshot for an idle or interactive remark. Screen evidence is ephemeral and observational only: it is never stored in chat history and never bypasses the selected timeline's knowledge ceiling. Turn the control off before displaying sensitive material.

Assistant replies use a deliberately small structured contract: one semantic `reaction` plus one short `remark`. The backend still owns model prompts, provider credentials, validation, and the generous hard output ceiling needed by reasoning models. The desktop shell never receives the OpenRouter key.

### Assistant desktop runtime

Virtual Assistant requires **Node.js 22.12+ / npm** in addition to the normal Python runtime. The single `install.bat` installs lock-file versions and does not report success until the actual Electron executable is present and runnable.

The assistant is an ordinary always-on-top desktop window intended for normal applications and windowed/borderless-fullscreen games. Protean does not inject into other processes or attempt to defeat exclusive-fullscreen/anti-cheat boundaries.

## Character Research

The user has one assigned character-library root. Research scans only supported `.json`, `.md`, and `.txt` files beneath that root, subject to file-count and file-size limits.

The built-in library is located at:

```text
src/protean_workspace/data/library
```

Built-in cards currently cover Harry Potter, Persona 5 Royal, Neon Genesis Evangelion, Demon Slayer, and Hunter x Hunter.


## Scenario layer

Protean resolves roleplay state in this order:

```text
Character -> Timeline phase -> Scenario -> Tone
```

Each built-in timeline phase includes three stable scenario slots, but their visible names/content are now phase-specific event hooks. The stable IDs preserve old chat/history compatibility while scenes can be things like catching a forbidden spell in progress, discovering a secret potion, being interrupted during a covert mission, or dealing with the aftermath of a timeline-valid crisis.

The custom scene editor uses the same three focal points:

1. **What is happening**
2. **Who it involves**
3. **Character ↔ user dynamic**

A custom scenario can be alternate or unusual. It can place pre-Kamoshida Ann inside the Metaverse, for example, but that does not grant her later terminology or Phantom Thief knowledge. She encounters the situation from what she actually knows in the selected phase and may learn only through what happens in-scene.

Custom drafts are only a browser convenience before chat creation. The backend validates the effective scenario and stores a frozen snapshot with the chat.

## Generation length

Provider settings now have two separate values:

- **Target tokens**: the approximate reply length the model is told to aim for.
- **Hard ceiling**: emergency output cap; it must remain at least 128 tokens above the target.

The model prompt asks for a complete natural ending near the target. If the provider reports that a result ended because of the token ceiling, Protean rejects the incomplete object and makes its one bounded structured retry. An incomplete reply is never persisted as a successful turn.

## External layout editor

Open `tools/layout-editor/index.html` directly in a browser to use the external visual layout tool. It can:

- drag components;
- resize;
- rotate;
- scale;
- toggle grid and snapping;
- import/export `protean.layout/v1` JSON.

It is intentionally an outsider tool. It does not authenticate, call the API, read the database, scan character files, or touch provider credentials. Runtime importing of its layout JSON is deferred until the layout schema is hardened.

## Immersion asset library

The runtime only resolves assets declared `ready` in `static/assets/immersion/manifest.json`. Missing packs remain declared as `incoming` and are simply not offered in the Immersion setup. The model never selects raw asset filenames.

Diary Tom is deliberately diary-first even though his age-16 sprite pack is ready.

## Frontend library direction

The intended frontend migration remains React + TypeScript + Vite, with design tokens, accessible headless primitives, one coherent icon library, purposeful motion, and Moveable for the external editor.

The environment used to assemble the 0.3 visual foundation had no npm registry access, so the delivered runtime is self-contained static HTML/CSS/JS rather than an unverified partially-built dependency bundle. The API and security contracts are deliberately framework-agnostic so the rendering layer can be swapped without moving secrets or business logic into the browser.

## Tests

```bat
.venv\Scripts\python.exe -m pytest
```

The suite covers authentication, protected APIs, encrypted credentials, character research, roleplay locks, structured generation, Immersion, persistent/idempotent chats, logout/session cleanup, and Virtual Assistant security/lifecycle contracts. See `TESTING.md` for the RC2 release gate.


## Generated openings and transcript grammar

The normal Workspace now asks the configured model to generate the first assistant message from the selected **Character + Timeline + Scenario + Tone + medium**. If no provider key is configured, Protean shows a short instruction to add the key and re-click the character.

The backend returns the generated preview with a short-lived opaque token. When the chat is actually persisted, that token lets `ChatService` store the exact opening that was previewed; the browser cannot replace it with arbitrary assistant text.

Roleplay replies are instructed to use Protean syntax consistently:

```text
(Developer / OOC)

**Action**

"Speech"
```

Distinct beats are separated by blank lines. In v0.4.5, each assistant turn still uses one normal structured generation call, but OpenRouter capability negotiation is progressive: native strict `json_schema` first, then `json_object`, then JSON-only prompting if the router has no compatible strict endpoint. Protean always runs the same local schema validator and locally renders `**action**`, `"speech"`, and `(developer/OOC)`; there is no second model-based visible-output gate.

Immersion consumes the same structured reaction for sprite choice and the same semantic location for background continuity. A background change is allowed only when the structured response explicitly marks that the physical location changed. Empty or invalid structured completions receive one bounded retry; provider reasoning fields are never consumed as visible content.

Communication medium remains phase-aware: living Hogwarts Tom speaks in person by default, while the diary imprint writes through the enchanted diary.


## 0.5.0 content expansion

Protean now ships 40 built-in characters across Harry Potter, Neon Genesis Evangelion, Demon Slayer, Persona 5 Royal, and Hunter x Hunter. Sherlock Holmes was removed from the built-in library. Existing Tom Riddle / Hermione / Ann / Makoto / Misato / Gendo cards remain, while the expanded roster adds Harry, Ron, Ginny, Draco, Luna, Neville, Snape; Shinji, Rei, Asuka, Kaworu, Ritsuko; Tanjiro, Nezuko, Zenitsu, Inosuke and six Hashira; the remaining Persona 5 Royal playable/core cast; and Gon, Killua, Kurapika and Leorio.

Character scenes are now event-driven rather than generic. Each phase still exposes exactly three stable scenario IDs for history compatibility, but their names and contents are phase-specific hooks such as catching Tom Riddle using forbidden magic, discovering Hermione brewing Polyjuice Potion, interrupting a Persona character during an arc-specific problem, or being pulled into a mission complication. The timeline remains the hard knowledge ceiling; a dramatic scenario never grants future knowledge.

Five additional generic tones are available: `Tense`, `Vulnerable`, `Rivalry`, `Melancholic`, and `Confrontational`. They affect delivery only and remain constrained by the selected scenario's relationship dynamic.

The right Presentation panel now reports Immersion status for the selected character as either `Implemented` or `Not yet implemented`. This is derived from ready visual routes only. New character sprite/background slots are declared as `incoming`, so normal chat works immediately while Immersion remains limited to visual packs that actually exist.
#   P r o t e a n _ A I  
 