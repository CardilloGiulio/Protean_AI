# Protean Workspace

### Local-first, character-aware roleplay workspace

**Version:** `0.6.1 RC2`
**Release stage:** Release Candidate — stabilization only

Protean Workspace is a **local-first character roleplay workspace** featuring persistent history, bounded character research, encrypted provider credentials, character-aware presentation, and multiple diegetic interaction modes.

It combines traditional roleplay chat with dedicated **Immersion** and **Virtual Assistant** experiences while keeping character knowledge, scenarios, credentials, and application state under explicit boundaries.

> [!IMPORTANT]
> **RC2 is stabilization-only.**
>
> Before distribution, review:
>
> * [RC2 Scope](RC2-SCOPE.md)
> * [Release Status](RC2-RELEASE-STATUS.md)
> * [Privacy](PRIVACY.md)
> * [IP Notice](IP-NOTICE.md)
> * [Testing & Release Gate](TESTING.md)
> * [Known Limitations](LIMITATIONS.md)
> * [Security](SECURITY.md)

---

## Table of Contents

* [Quick Start](#quick-start)
* [Core Architecture](#core-architecture)
* [First Launch](#first-launch)
* [Roleplay Model](#roleplay-model)
* [Immersion Mode](#immersion-mode)
* [Virtual Assistant](#virtual-assistant)
* [Character Research](#character-research)
* [Scenario System](#scenario-system)
* [Generation Length](#generation-length)
* [Generated Openings](#generated-openings)
* [Transcript Grammar](#transcript-grammar)
* [External Layout Editor](#external-layout-editor)
* [Asset Library](#asset-library)
* [Character Library](#character-library)
* [Frontend Direction](#frontend-direction)
* [Testing](#testing)
* [Current Content Expansion](#current-content-expansion)

---

# Quick Start

## Windows

Protean has exactly **two Windows entry points**:

```text
install.bat
start.bat
```

### Installation

1. Extract the ZIP completely.
2. Double-click `install.bat` once.
3. Double-click `start.bat` whenever you want to use Protean Workspace.
4. If the browser does not open automatically, navigate to:

```text
http://127.0.0.1:8000
```

`install.bat` prepares and verifies both:

* the Python workspace;
* the Electron Virtual Assistant runtime.

`start.bat` verifies the runtime again and automatically invokes the installer if a required environment is missing.

---

## Manual Installation

Run the following commands from the directory containing `pyproject.toml`:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --requirement requirements-lock.txt
py -m pip install --no-deps --no-build-isolation -e .
py -m uvicorn protean_workspace.main:app --host 127.0.0.1 --port 8000
```

---

# Core Architecture

Protean separates **character identity**, **timeline knowledge**, **scenario state**, and **presentation**.

The fundamental roleplay hierarchy is:

```text
Character
    ↓
Timeline Phase
    ↓
Scenario
    ↓
Tone
```

The selected timeline acts as the character's **hard knowledge ceiling**.

A scenario may create unusual circumstances, but it cannot automatically grant knowledge from later points in the source timeline.

---

# First Launch

On first launch, Protean asks you to create a local:

* owner username;
* owner password.

After authentication, paste your **OpenRouter API key** into the right-side Workspace panel.

The browser sends the key to the backend, where it is encrypted before persistence.

> [!NOTE]
> The plaintext provider key is never returned to the frontend.

---

# Roleplay Model

Protean uses a structured roleplay system based on:

```text
Character + Timeline + Scenario + Tone + Medium
```

Each layer controls a different part of the interaction.

| Layer         | Purpose                                           |
| ------------- | ------------------------------------------------- |
| **Character** | Personality, identity and source characterization |
| **Timeline**  | Knowledge and development ceiling                 |
| **Scenario**  | Current event and relationship context            |
| **Tone**      | Style and emotional delivery                      |
| **Medium**    | How communication occurs                          |

The backend owns:

* character prompts;
* model instructions;
* provider credentials;
* generation validation;
* structured output parsing.

The model cannot directly select arbitrary runtime files or visual assets.

---

# Immersion Mode

Protean includes a dedicated full-screen Immersion interface at:

```text
/immersion
```

Immersion combines normal Protean roleplay with character sprites, scene backgrounds, semantic reactions, and location-aware presentation.

## Session Setup

Before an Immersion scene begins, the user locks:

```text
Timeline + Scenario + Tone
```

These values remain fixed for the session.

Immersion uses a **normal persisted Protean chat**, meaning its history remains part of the same chat system used by the standard Workspace.

---

## Current Immersion Features

* Dedicated `/immersion` full-screen page.
* Timeline, Scenario and Tone locked before scene start.
* Persistent normal Protean chat history.
* Semantic character expression switching.
* Small sprite movement transforms.
* Scene background cross-fades.
* Location-aware visual continuity.
* Explicit handling of missing visual assets.
* No raw filename selection by the model.

---

## Current Character Support

The Immersion launch button only appears when the selected character has at least one complete visual route.

### Implemented

* **Tom Riddle**
* **Hermione Granger**

Only timeline phases backed by complete sprite/background packs are enabled.

### Not Yet Implemented

Immersion currently remains unavailable for characters or phases whose visual packs are incomplete, including:

* Ann Takamaki;
* Makoto Niijima;
* Misato Katsuragi;
* Gendo Ikari;
* newly added characters;
* unsupported Hermione phases.

Missing visual slots remain declared as:

```text
incoming
```

inside:

```text
static/assets/immersion/manifest.json
```

---

## Using Immersion

1. Select **Tom Riddle** or **Hermione Granger** in the normal Workspace.
2. Click **Immersion** in the top bar.
3. Select:

   * Timeline;
   * Scenario;
   * Tone.
4. Click **Enter scene**.
5. Continue the roleplay normally.
6. Use **Back** to return to Workspace.

Protean reloads the same saved conversation from history.

> [!NOTE]
> If the Immersion button is absent, that character currently has no complete ready sprite/background route.

---

## Diary Tom

Diary-imprint Tom uses a special presentation mode.

The enchanted diary is treated as the primary communication medium, so the system does **not** render a physical Tom sprite by default even though an age-16 Tom visual pack exists.

---

# Virtual Assistant

## Version `0.6.1 RC2`

Virtual Assistant is Protean's separate desktop companion mode.

The normal Workspace remains the configuration and launch surface.

Before launch, the user selects:

```text
Character
+
Timeline
+
Scenario
+
Tone
+
Wardrobe
+
Background
```

Protean then:

1. creates a short-lived Assistant session;
2. launches the packaged Electron shell;
3. redirects the browser to `/assistant` as a bridge page.

---

## Current Assistant Character

The first implemented Virtual Assistant character is:

### Rei Ayanami

| Wardrobe           | Status    |
| ------------------ | --------- |
| School Uniform     | ✅ Ready   |
| Casual             | ✅ Ready   |
| Plugsuit           | 🔒 Locked |
| Bandaged / Wounded | 🔒 Locked |

Assistant readiness is independent from Immersion readiness.

---

## Semantic Expressions

Each ready Rei wardrobe includes ten semantic expressions:

```text
neutral
positive
amused
serious
concerned
surprised
thinking
embarrassed
annoyed
tired
```

Other characters remain:

```text
Not yet implemented
```

until Assistant-specific visual packs are available.

---

# Rei Characterization

Virtual Assistant includes an Assistant-specific characterization layer on top of the normal:

```text
Character → Timeline → Scenario → Tone
```

contract.

The layer emphasizes:

* sparse, literal speech;
* restrained emotional shifts;
* understated curiosity;
* quiet dry humor;
* phase-sensitive warmth and autonomy;
* screen-aware observations;
* preservation of Rei's characterization rather than conversion into a generic friendly chatbot.

The selected timeline remains the hard knowledge ceiling.

---

# Short-Term Remark Memory

Each live Assistant session maintains a small rolling text context.

In `v0.6.1`, this is explicitly used as **novelty memory**.

Recent remarks are shown to the model with instructions not to repeat:

* the same observation;
* opening;
* joke;
* conclusion.

Protean also checks recent visible remarks locally.

If a response substantially repeats one of them, the system may issue **one bounded novelty correction**.

> [!IMPORTANT]
> Screenshots are never stored in this remark memory.

The memory exists only for the current Assistant session and disappears when that session ends.

---

# Assistant Interaction Model

A single click on the Assistant sprite opens four actions:

```text
Search online
Interact
Wardrobe
Quit
```

Multiple rapid clicks are interpreted as a **poke burst**.

---

## Search Online

Search opens a normal DuckDuckGo results page after an in-character acknowledgement.

---

## Interact

Interact accepts two input modes:

```text
Speech
Developer / OOC
```

There is intentionally **no physical action channel**.

The Virtual Assistant is a desktop companion, not a physical roleplay scene.

---

## Wardrobe

Wardrobe changes are immediate presentation-state changes.

After switching clothing, the Assistant may generate a short in-character remark.

---

## Quit

Quit requests one final character remark before:

1. closing the desktop companion;
2. returning control to Workspace.

---

# Screen Awareness

Screen awareness is **disabled by default** for every Assistant session.

Activating it requires explicit user confirmation describing what information may be sent.

While enabled, the Assistant may observe:

* the current foreground application;
* the active window;
* one downscaled screenshot for an idle or interactive remark.

Screen information is:

* ephemeral;
* observational only;
* not stored in chat history;
* unable to override timeline knowledge restrictions.

> [!WARNING]
> Disable screen awareness before displaying sensitive information.

---

# Assistant Output Contract

Assistant responses intentionally use a very small structured format:

```text
reaction
remark
```

The backend owns:

* model prompts;
* OpenRouter credentials;
* schema validation;
* output limits;
* structured-response handling.

The Electron shell never receives the OpenRouter API key.

---

# Assistant Desktop Runtime

Virtual Assistant requires:

```text
Node.js 22.12+
npm
```

in addition to the normal Python environment.

The single Windows installer installs locked dependency versions and does not report success until the Electron executable exists and can run.

The Assistant is an ordinary **always-on-top desktop window** intended for:

* normal desktop applications;
* windowed games;
* borderless-fullscreen games.

Protean does **not**:

* inject code into other processes;
* bypass exclusive-fullscreen restrictions;
* attempt to defeat anti-cheat systems.

---

# Character Research

Each user has one assigned character-library root.

Research is limited to supported files beneath that root:

```text
.json
.md
.txt
```

Research is subject to:

* file-count limits;
* file-size limits;
* root-directory boundaries.

The built-in library is located at:

```text
src/protean_workspace/data/library
```

---

# Scenario System

Every built-in timeline phase provides exactly **three stable scenario slots**.

Their IDs remain stable for chat/history compatibility, but the actual event hooks are timeline-specific.

Examples include:

* catching a character using forbidden magic;
* discovering a secret potion;
* interrupting a covert mission;
* dealing with the aftermath of a timeline-valid crisis.

---

## Custom Scenarios

The custom scenario editor focuses on three questions:

1. **What is happening?**
2. **Who does it involve?**
3. **What is the Character ↔ User dynamic?**

A custom scenario may deliberately introduce an unusual situation.

For example, pre-Kamoshida Ann could encounter the Metaverse.

That does **not** automatically give her:

* later terminology;
* Phantom Thief knowledge;
* future experience.

She interprets the situation using only what she knows at the selected timeline point and may learn additional information only through events that happen during the scene.

Custom drafts exist in the browser only until chat creation.

The backend validates the effective scenario and stores a frozen snapshot with the created chat.

---

# Generation Length

Protean exposes two independent generation settings.

| Setting           | Purpose                                              |
| ----------------- | ---------------------------------------------------- |
| **Target Tokens** | Approximate response length requested from the model |
| **Hard Ceiling**  | Emergency maximum model output                       |

The hard ceiling must remain at least:

```text
Target Tokens + 128
```

The model is instructed to reach a complete, natural ending near the requested target.

If the provider reports that a structured response terminated because of the hard token ceiling, Protean rejects it and performs its single bounded structured retry.

> [!IMPORTANT]
> Incomplete output is never persisted as a successful roleplay turn.

---

# Generated Openings

The normal Workspace asks the configured model to generate the first assistant message using:

```text
Character
+
Timeline
+
Scenario
+
Tone
+
Medium
```

If no provider key is configured, Protean asks the user to add one before retrying.

The backend returns the generated preview together with a short-lived opaque token.

When the chat is persisted, that token allows `ChatService` to store **the exact opening that was previewed**.

The browser cannot replace the preview with arbitrary assistant text.

---

# Transcript Grammar

Protean roleplay uses the following visible syntax:

```text
(Developer / OOC)

**Action**

"Speech"
```

Distinct narrative beats are separated by blank lines.

The backend renders structured model data into this syntax locally.

---

# Structured Generation

OpenRouter capability negotiation is progressive:

```text
Native strict json_schema
        ↓
json_object
        ↓
JSON-only prompting
```

This allows Protean to continue operating when a provider does not expose a compatible strict structured-output endpoint.

Regardless of provider mode, Protean runs the same local schema validator.

There is no second model-based visible-output gate.

Provider reasoning fields are never rendered as visible character output.

Empty or invalid structured completions receive one bounded retry.

---

# Immersion Structured State

Immersion consumes the structured generation result for two important presentation signals.

### Reaction

Used to select the semantic character expression.

### Location

Used to maintain background continuity.

A background transition occurs only when the structured response explicitly indicates that the character's physical location changed.

---

# Communication Medium

Communication medium remains timeline-aware.

For example:

```text
Living Hogwarts Tom
→ normally communicates in person
```

while:

```text
Diary-imprint Tom
→ communicates through the enchanted diary
```

---

# External Layout Editor

Protean includes an experimental external visual layout tool.

Open:

```text
tools/layout-editor/index.html
```

directly in a browser.

The editor supports:

* dragging;
* resizing;
* rotation;
* scaling;
* grid display;
* snapping;
* JSON import;
* JSON export.

Layout files use:

```text
protean.layout/v1
```

---

## Security Boundary

The layout editor intentionally operates outside the main Protean runtime.

It does **not**:

* authenticate;
* call the Protean API;
* read the database;
* scan character files;
* access provider credentials.

Runtime importing of exported layout JSON remains deferred until the layout schema is sufficiently hardened.

---

# Asset Library

Immersion only resolves visual assets explicitly marked:

```text
ready
```

inside:

```text
static/assets/immersion/manifest.json
```

Missing packs remain:

```text
incoming
```

and are not offered in Immersion setup.

The AI never directly selects raw sprite or background filenames.

---

# Character Library

Protean currently ships **40 built-in characters** across five franchises.

## Harry Potter

Existing and expanded characters include:

* Tom Riddle
* Hermione Granger
* Harry Potter
* Ron Weasley
* Ginny Weasley
* Draco Malfoy
* Luna Lovegood
* Neville Longbottom
* Severus Snape

---

## Neon Genesis Evangelion

* Misato Katsuragi
* Gendo Ikari
* Shinji Ikari
* Rei Ayanami
* Asuka Langley
* Kaworu Nagisa
* Ritsuko Akagi

---

## Demon Slayer

Includes:

* Tanjiro
* Nezuko
* Zenitsu
* Inosuke
* six Hashira

---

## Persona 5 Royal

Includes the existing:

* Ann Takamaki
* Makoto Niijima

along with the remaining playable/core cast included in the expanded library.

---

## Hunter × Hunter

* Gon
* Killua
* Kurapika
* Leorio

---

### Removed

Sherlock Holmes has been removed from the built-in character library.

---

# Event-Driven Character Scenes

Character scenarios are designed as **phase-specific events** rather than generic prompts.

Examples include:

```text
Tom Riddle using forbidden magic
```

```text
Hermione brewing Polyjuice Potion
```

```text
A Persona character interrupted during an arc-specific crisis
```

```text
A mission complication tied to the selected timeline
```

Scenario drama never overrides the selected timeline.

The timeline remains the character's hard knowledge ceiling.

---

# Additional Tones

Protean includes the following additional generic tones:

```text
Tense
Vulnerable
Rivalry
Melancholic
Confrontational
```

Tone affects **delivery**, not factual knowledge or scenario state.

It remains subordinate to the selected scenario's relationship dynamic.

---

# Presentation Status

The right-side Presentation panel reports Immersion readiness as:

```text
Implemented
```

or:

```text
Not yet implemented
```

This status is calculated from available visual routes.

New characters can therefore work normally in standard chat while their Immersion assets remain:

```text
incoming
```

---

# Frontend Direction

The intended frontend migration remains:

```text
React
+
TypeScript
+
Vite
```

with:

* design tokens;
* accessible headless primitives;
* one coherent icon library;
* purposeful motion;
* Moveable integration for the external editor.

The environment used to construct the `0.3` visual foundation had no npm registry access.

For that reason, the delivered runtime uses self-contained:

```text
HTML
CSS
JavaScript
```

instead of shipping an unverified partially-built dependency bundle.

The API and security contracts remain framework-agnostic so the rendering layer can later change without moving credentials or business logic into the browser.

---

# Testing

Run the automated test suite with:

```bat
.venv\Scripts\python.exe -m pytest
```

The suite covers:

* authentication;
* protected APIs;
* encrypted provider credentials;
* character research;
* roleplay locks;
* structured generation;
* Immersion;
* persistent chats;
* idempotent chat operations;
* logout and session cleanup;
* Virtual Assistant security contracts;
* Virtual Assistant lifecycle behavior.

See:

```text
TESTING.md
```

for the complete RC2 release gate.

---

# RC2 Focus

`0.6.1 RC2` is primarily a **stabilization release**.

The objective is not to expand the feature surface further, but to verify that existing systems satisfy the release gates for:

```text
Reliability
Security
Privacy
Data integrity
Clean installation
Character quality
Performance
Regression safety
```

For current readiness and unresolved items, see:

* [RC2 Release Status](RC2-RELEASE-STATUS.md)
* [Testing](TESTING.md)
* [Known Limitations](LIMITATIONS.md)
* [Security](SECURITY.md)

---

# Project Status

```text
Protean Workspace
Version: 0.6.1 RC2
Stage: Release Candidate
Focus: Stabilization / Verification
```

Normal Workspace, character research, persistent chat, structured generation, Immersion, and the initial Virtual Assistant pipeline are implemented.

Visual-mode availability remains intentionally restricted to character/timeline combinations backed by complete asset packs.

---

## Protean Workspace

**Character. Timeline. Scenario. Tone. Medium.**

A local-first workspace designed to keep those boundaries explicit.
