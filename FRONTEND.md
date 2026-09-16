# Protean Workspace frontend direction

## Runtime boundary

The frontend is a replaceable presentation client. It communicates only with same-origin `/api/*` endpoints and must not absorb backend authority.

See `ARCHITECTURE.md` for the hard boundary.

## Target library stack

The planned library migration remains:

- React + TypeScript for component architecture;
- Vite for development/build;
- Tailwind primarily for structural utilities and design-token plumbing, not for generic visual identity;
- shadcn/Base UI-style accessible headless primitives where useful;
- one coherent icon set such as Lucide;
- Motion for purposeful transitions/drawers/layout changes;
- Zustand only for presentation state that benefits from a small client store;
- Moveable in the external layout editor.

## Why 0.3 is self-contained

The build environment used to assemble this patch could not reach the npm registry. Instead of shipping an unverified dependency tree or a non-running React bundle, 0.3 ships a self-contained HTML/CSS/JS runtime that implements the visual design and keeps all contracts framework-neutral.

That is intentional technical debt, not a boundary change. A later React migration should replace the rendering implementation, not rewrite auth, credentials, chat persistence, prompt assembly, filesystem access, or provider services.

## Current visual component model

```text
AppShell
  Topbar
  LeftCharacterPanel
    CharacterHero
    Research
    CharacterList
    TonePreset
    TimelinePhase
    CharacterLibraryRoot
    History
  Scene
    PhysicalFrame
      Transcript
      Composer
  RightWorkspacePanel
    Appearance
    ImmersionAvailabilityNotice
    ProviderConnection
    BoundarySummary
  ImmersionEntryDialog
  /immersion
    FullScreenBackground
    CharacterStage / DiaryObjectMode
    ImmersionTranscript
    Composer
    MinimalHUD
```

## Presentation state

Local/presentation-only state may include:

- sidebar visibility;
- focus mode;
- temporary editor selections;
- non-secret scene UI state.

It may not include JWTs, API keys, decrypted credentials, hidden prompt material, or arbitrary filesystem data.

## Background stack fix (0.3.1)

The scene background is now part of an explicit isolated stacking context at `z-index: 0`; application chrome is above it. Do not reintroduce negative z-index scene layers, because they can fall behind the document/body paint layer in browsers. Background selection is applied optimistically in the presentation client and then persisted through `/api/settings/preferences`.

## Timeline selector

Timeline is roleplay state, not presentation-only state. The UI may select/display it, but the server validates it against the selected character and the chat persists it. A later React migration must preserve this API/domain boundary.


## v0.3.2 scenario controls

The left character panel keeps the minimal state order:

```text
Tone
Timeline phase
Scenario
```

Scenario presets are data returned with the selected phase. The UI only renders/selects them. `+ Custom scene…` reveals three inputs: What, Who, Dynamic. The browser may cache an unsaved draft per character/phase, but the backend is authoritative once a chat is created.

Changing character, phase, scenario or tone starts a fresh chat because all four are part of the roleplay state frozen at chat creation. The visual layer does not assemble the resulting system prompt.

## v0.4 Immersion sub-page

`/immersion` is now a separate full-screen rendering surface. Normal Workspace HTML/CSS/JS remains intact. The route receives a frozen chat setup created by the backend and exposes no controls for changing timeline, scenario, or tone after entry.

Entry flow:

```text
Workspace -> Immersion button -> lock modal -> /api/immersion/start -> /immersion
```

The normal page shows the Immersion button only for selected characters that have at least one ready visual timeline. The modal itself lists only ready phases.

Immersion layer order:

```text
background -> sprite (or diary object mode) -> translucent transcript -> minimal HUD
```

`immersion.js` owns only presentation state: current ready background ID, sprite expression/path supplied by the server, and temporary transform offsets. It never receives provider credentials or constructs prompts.

Scene changes cross-fade between declared ready local backgrounds. Sprite changes cross-fade between declared expression assets and apply small transform animations for visible movement cues. The browser cannot request an arbitrary file path.

The manifest continues to keep all unavailable packs/backgrounds as `incoming`, so later patches can add files without changing domain IDs.


## 0.4.1 transcript / opening UI rule

- Empty-chat opening text is model-generated only when the backend reports a configured provider key.
- Without a key, the normal Workspace shows a setup note and waits for the user to re-click the character after saving the key.
- The browser may hold only an opaque `opening_token`; it never sends authoritative assistant opening text back to the server.
- Immersion renders action/speech/dev transcript segments as separate block beats with preserved semantic spacing.
- Hidden reaction metadata is never rendered by either normal Workspace or Immersion.


## 0.5.0 Immersion availability label

The right Presentation panel shows `Implemented` only when `/api/immersion/availability` reports at least one ready phase for the currently selected character. Otherwise it shows `Not yet implemented`. The label is presentation-only; it does not infer support from portraits, generic backgrounds, or `incoming` manifest entries.


## Virtual Assistant surface — 0.6.0

The normal Workspace remains the configuration surface. The **Assistant** button is visible only when `/api/assistant/availability` reports the selected character as ready. The Presentation panel displays `Implemented` for ready Assistant characters and `Not yet implemented` otherwise.

Before launch, the browser modal locks Timeline, Scenario, Tone, Wardrobe and Assistant background. Wardrobes are rendered from the Assistant manifest/API, not hard-coded into the HTML. In v0.6.0 Rei exposes School and Casual as selectable, while Plugsuit and Bandaged remain visible but disabled/locked.

`POST /api/assistant/start` launches the local desktop shell and returns only bridge/navigation state to the browser. The browser then redirects to `/assistant`; it never receives the Electron bearer token.

The desktop UI keeps four primary click actions: Search online, Interact, Wardrobe and Quit. Search/Interact open temporary small input panels. Interact exposes only Speech and Developer/OOC modes. Multiple clicks are grouped as a poke burst and animate locally before one AI event is requested. Wardrobe swaps the ready sprite family immediately and then requests the in-character remark.

The Assistant renderer consumes only semantic `reaction + remark`. It never renders RP action beats or receives model-selected asset paths. Transparent pixels outside interactive UI can pass mouse input through to the application underneath; text entry temporarily makes the window focusable.
