## 0.6.1 RC2

- Made Assistant screen observation opt-in per session and enforced the disabled state server-side.
- Made chat turns atomic, idempotent, and serialized per chat.
- Sanitized provider failures and rejected truncated `finish_reason=length` completions.
- Added prompt/data authority boundaries for scenario, location, reference, conversation, and screen content.
- Corrected pre-reveal Sumire identity handling and removed Rengoku's impossible post–Mugen Train phase.
- Corrected Windows installer branching, added Python/npm locks, and provided a native Windows/Electron soak gate.
- Fixed Assistant busy locking, Electron lifecycle, expired session cleanup, temporary backgrounds, and oversized-image validation.
- Reduced the oversized Hogwarts background and corrected physical-scenario opening cues under a written default medium.
- Added privacy, intellectual-property, limitations, and testing/release documentation.
- Consolidated Windows usage to one verified `install.bat` and one `start.bat`; removed legacy upgrade/development launcher BAT files.
- Made Assistant installation mandatory for installer success, explicitly installed Electron 44's platform binary after `npm ci`, and verified the exact executable used by the runtime.

## 0.6.1

- Strengthened Rei Ayanami's Virtual Assistant-only personality contract with detailed speech rhythm, emotional restraint, desktop-medium behavior, and timeline-sensitive modulation.
- Added explicit originality guidance so Assistant remarks use current screen/event evidence without repeatedly paraphrasing titles or falling back to generic chatbot phrasing.
- Reused the existing ephemeral rolling Assistant context as short-term conversational memory and made its novelty rule explicit to the model.
- Added a local near-duplicate guard over the last three visible remarks; only when a generated line substantially repeats recent wording does Protean request one novelty correction.
- Kept the normal successful Assistant path at one provider call; no changes to screen capture, wardrobe, auth, credentials, normal RP, Immersion, or persistence boundaries.
- No database migration.

## 0.6.0

- Added Virtual Assistant as a separate desktop-companion medium backed by `AssistantService` and a sandboxed packaged Electron shell.
- Added setup locking for Character + Timeline + Scenario + Tone + Wardrobe + Background before desktop launch.
- Added ephemeral opaque desktop-session bearer tokens; the browser never receives the token and Electron never receives the OpenRouter key or normal JWT.
- Added screen-aware idle/interact remarks from the external foreground app/window with optional downscaled screenshot input; screen pixels are never persisted or added to normal RP history.
- Added four Assistant actions: Search online (DuckDuckGo), Interact (Speech/Dev only), Wardrobe, and Quit, plus multi-click poke bursts.
- Added one-call lightweight Assistant structured output (`reaction + remark`) with bounded retry and generous hard token ceiling.
- Added a separate Assistant asset manifest/readiness boundary independent from Immersion.
- Integrated Rei Ayanami School + Casual half-body packs with ten expressions each.
- Added visible locked Rei Plugsuit + Bandaged wardrobe entries for future assets.
- Kept every other character `Not yet implemented` for Assistant mode.
- Added validated session-scoped custom backgrounds and a visible screen-awareness pause state.
- Added Electron hardening: no Node integration in renderer, context isolation, sandbox, narrow preload/IPC allowlist, no arbitrary commands/filesystem/provider authority, and no game/process injection.
- Integrated the Assistant runtime into the release installer; RC2 later consolidated this into the single verified `install.bat` entry point.
- No database migration and no change to normal ChatService/Immersion authority.

## 0.5.0

- Expanded the built-in roster to 40 characters across Harry Potter, Evangelion, Demon Slayer, Persona 5 Royal, and Hunter x Hunter.
- Removed Sherlock Holmes and his reserved Immersion asset/background slots.
- Added phase-specific event-hook scenarios throughout the library while retaining stable scenario IDs for history compatibility.
- Added Hermione's second-year Polyjuice timeline and scenario.
- Added five scenario-constrained tones: Tense, Vulnerable, Rivalry, Melancholic, and Confrontational.
- Replaced the right-panel `Partial library` label with dynamic `Implemented` / `Not yet implemented` Immersion status.
- Added stable `incoming` Immersion sprite slots for every new character phase and expanded the curated background backlog.
- No auth, database schema, provider, structured-generation, or Immersion-engine refactor in this release.

# Changelog

## 0.4.5

- Hardened the local structured parser for weaker/free OpenRouter models without changing the one-call roleplay contract.
- Accept harmless JSON wrappers/fences, common semantic aliases, string-form locations, and missing `location.changed` (defaults safely to `false`).
- Accept common beat field/type aliases and already-delimited Protean beats, while still rejecting arbitrary prose and invalid semantics.
- Lower retry temperature to reduce JSON embellishment and include the local validation reason in controlled errors/logs.
- No auth, database, character/timeline/scenario/tone, provider-authority, or Immersion boundary changes.

## 0.4.4

- Keep the v0.4.3 single-call semantic JSON generation architecture.
- Add provider capability degradation only for OpenRouter's specific "No endpoints found that can handle the requested parameters" routing error.
- Try native strict `json_schema` first, then `json_object`, then plain JSON-only prompting with the same local validator.
- Cache the working structured mode per selected model for the lifetime of the process, avoiding repeated strict-capability failures on every turn.
- Do not degrade on authentication, rate-limit, network, or unrelated provider errors.
- No auth, database, character, timeline, scenario, tone, Immersion, or asset boundary changes.

## 0.4.3

- Replaced the normal two-call draft/output-gate pipeline with one strict structured JSON provider call.
- Added typed semantic beats (`action`, `speech`, `dev`) and deterministic local rendering to `** **`, `""`, and `()`.
- Added exactly one structured reaction per assistant turn for Immersion sprite selection.
- Added semantic scene location plus `location.changed`; Immersion no longer guesses scene changes by scanning prose for place names.
- When a real location change has no matching ready background, Immersion uses the neutral Protean fallback instead of keeping a false previous room.
- Kept one bounded retry for empty/invalid structured output; no second model cleanup call is used on successful turns.
- No auth, credential, database, character/timeline/scenario, or provider-secret boundary changes.

## 0.4.2

- Added a controlled two-call assistant pipeline without changing the existing roleplay state model or Immersion architecture.
- Call 1 now produces an ephemeral `PROTEAN_DRAFT` plus exactly one semantic reaction; it is never persisted or shown directly.
- Call 2 is a narrow visible-output gate that receives the current user message, selected reaction and private draft, then returns only `()`, `** **`, and `""` Protean transcript grammar.
- Added strict local transcript validation before assistant text can be stored or shown.
- Added bounded retries for genuinely empty provider completions and for malformed/metadata-only visible-gate results.
- Added `EmptyCompletionError` at the provider abstraction and stopped treating provider reasoning/thought fields as fallback visible content.
- Added filtering/retry behavior for standalone provider artifacts such as `User Safety: Safe` and accidental meta chatter.
- Kept substantive refusals intact rather than treating safety filtering as a bypass.
- The first-call reaction remains transient presentation metadata and is passed internally to Immersion sprite selection; normal chat history contains only the validated visible transcript.
- No auth, credential, database, character, timeline, scenario, Immersion-route, asset-manifest, or frontend-structure refactor.

## 0.4.1

- Made roleplay openings provider-generated from the selected Character + Timeline + Scenario + Tone + medium instead of relying on the deterministic preview in the normal UI.
- When no OpenRouter key is configured, the empty chat now tells the user to add the key and re-click the character to generate a fresh opening.
- Added a short-lived opaque opening-preview token so the backend persists the exact generated opening the user previewed; the browser never authors the authoritative first assistant message.
- Strengthened the mandatory Protean transcript grammar: `()` developer/OOC, `**` action, `""` speech, blank lines between semantic beats, and no bare narrative prose.
- Added exactly one machine-only semantic reaction marker per model reply (`neutral`, `positive`, `amused`, `serious`, `concerned`, `surprised`, `thinking`).
- `ChatService` strips reaction metadata before the reply reaches the normal API/history; Immersion receives only the internal semantic reaction and maps it to ready sprite assets.
- Immersion now prefers the model-selected reaction over prose/regex inference, retaining inference only as a compatibility fallback when a model omits the marker.
- Improved Immersion transcript spacing so action/speech/dev beats render as separate readable blocks.
- Immersion entry now uses the same provider-generated opening flow and still delegates all actual generation to `ChatService`.
- No auth, credential, database-schema, character, timeline, scenario, provider-client, or asset-manifest refactor.

## 0.4.0

- Enabled the first **Immersion Mode** runtime as a separate `/immersion` sub-page without refactoring the normal Workspace.
- Added a lock-in entry modal for Timeline + Scenario + Tone. Those values are frozen by the ordinary persisted chat created at entry.
- Added a separate `ImmersionService`/`/api/immersion/*` presentation handler that delegates all actual chat/provider behavior to the existing `ChatService`.
- Immersion availability is derived strictly from `ready` manifest assets; only Tom Riddle and Hermione Granger ready phases are currently offered.
- Added semantic sprite-expression switching and lightweight transform movement based on visible assistant actions/tone/scenario cues.
- Added ready local background selection with automatic cross-fade when the visible scene clearly moves location.
- Added diary-object render mode for Tom's diary imprint: no physical Tom sprite by default.
- Added Back-to-Workspace handoff that returns to the same saved chat.
- Kept every missing sprite/background slot open as `incoming`; no unsupported character is promoted merely because a generic background exists.
- Corrected the stale fifth-year Tom scenario wording from a written exchange to an in-person exchange.
- No auth, credential, provider, prompt, database-schema, character-library, or external-editor refactor was introduced.

## 0.3.4

- Added an assets-only Immersion intake without enabling Immersion/Sprite Mode.
- Integrated 28 supplied expression sprites: complete packs for Hermione Year 1, Hermione Year 5, Tom age 16 and Tom age 17.
- Integrated 12 supplied Immersion backgrounds.
- Added `protean.immersion-assets/v1` manifest with stable `ready` / `incoming` slots for all planned sprite packs and local backgrounds.
- Kept every missing slot open so future patches can drop in assets without changing character/timeline/scenario IDs.
- Added fallback rules: missing sprites fall back to neutral/primary portrait; missing backgrounds fall back to a compatible ready background or Protean default.
- Preserved the presentation boundary: assets cannot change timeline knowledge, scenario, tone, auth, provider, persistence or model authority.
- Kept Tom's diary phase diary-first even though the age-16 physical pack exists.
- Flagged the supplied Tom age-17 pack for later canvas normalization without rejecting it.


## 0.3.2

- Added a separate scenario layer: `Character -> Timeline phase -> Scenario -> Tone`.
- Added exactly three timeline-dependent preset scenarios to all 33 built-in phases (99 presets total).
- Scenario presets define `what_happening`, `who_involved`, and the character-user `dynamic`.
- Added `+ Custom scene…` authoring using the same three fields.
- Added additive chat columns for `scenario_id` and frozen `scenario_json`.
- Existing/legacy chats without scenario data fall back to the phase default.
- Timeline knowledge is now explicitly stronger than scenario circumstances: alternate scenes do not grant future terminology, memories, powers or affiliations.
- Tone is explicitly subordinate to the selected relationship dynamic; `Intimate` no longer implies pre-existing closeness with a stranger.
- Custom drafts may be cached client-side, but the effective chat scenario is backend-validated and persisted.
- Sprite/Stage Mode remains intentionally deferred.
- Expanded automated coverage to 24 tests.

## 0.3.1

- Fixed scene backgrounds by removing the negative-z stacking bug and applying scene changes optimistically.
- Added `CharacterPhase` domain model and timeline selector under Tone.
- Added additive database migrations for `active_phase_id` and chat `phase_id`.
- Chats now freeze their timeline phase.
- Expanded all built-in character histories and added canon-aware phase data.
- Added future-knowledge locks to prevent early-phase characters from importing later development.
- Kept Variable Sprite / Stage Mode deferred for the next patch.
- Expanded automated coverage to timeline persistence, validation, prompt locking and background stacking.

## 0.3.0 — Protean visual foundation

### Identity

- Renamed the product and Python distribution to **Protean Workspace**.
- Renamed the import package to `protean_workspace`.
- Added Protean branding and favicon.
- Preserves a legacy `instance/riddle_studio.db` when upgrading from the earlier local build.

### Visual workspace

- Integrated supplied character portraits, backgrounds and textures.
- Rebuilt the shell around character / scene / workspace regions.
- Added independent left/right panel hiding and focus mode.
- Reworked Notebook, Tablet, Terminal and Manuscript frames.
- Replaced mismatched glyph controls with one internally consistent SVG icon language.
- Added responsive/mobile panel behavior.

### Roleplay transcript

- Added Protean grammar renderer:
  - `()` Developer/OOC;
  - `""` Speech;
  - `**` Action.
- Added medium contracts to built-in character cards.
- Tom Riddle explicitly remains aware that he is communicating through an enchanted diary.

### Generation quality

- Split reply length into `target_tokens` and hard `max_tokens` ceiling.
- Added 128-token minimum headroom policy.
- Added one continuation recovery when a provider reports a length cutoff.
- Provider protocol now returns a transport-neutral completion result with finish reason.

### Tooling

- Added external `tools/layout-editor/` prototype with drag, resize, rotate, scale, grid, snap and JSON import/export.
- Added `protean.layout/v1` schema.
- Declared Variable Sprite Mode as deferred presentation work for the next patch.

### Documentation

- Rewrote `ARCHITECTURE.md` as a hard boundary document.
- Updated `SECURITY.md`, `ROADMAP.md`, `README.md`.
- Added `FRONTEND.md` and design asset audit/reference material.

## 0.3.3

- Opening messages are now compiled from the selected **timeline phase + scenario + tone** instead of falling back to one static character greeting.
- The opening compiler is deterministic and provider-free; the same backend result powers the empty-chat preview and is frozen as the first assistant message when a chat is created.
- Tom Riddle's living Hogwarts phases now default to **in-person conversation**. Only the diary-imprint phase defaults to enchanted-diary mechanics.
- Custom scenarios may explicitly establish another plausible communication channel without granting future timeline knowledge.
- No authentication, provider, persistence authority, filesystem boundary, or sprite-mode architecture was refactored.
