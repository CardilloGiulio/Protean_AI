## 0.6.1 — Rei Assistant personality polish (complete)

- [x] Add a detailed Rei-specific Assistant speech/behavior profile without changing her normal RP card authority.
- [x] Preserve early/mid/late timeline differences inside the Assistant medium.
- [x] Make recent ephemeral Assistant remarks explicit novelty memory.
- [x] Add near-duplicate detection and one conditional novelty-regeneration call.
- [x] Keep ordinary Assistant events on the existing one-call lightweight pipeline.

## 0.6.0 — Virtual Assistant engine (complete)

- [x] Add sibling Virtual Assistant medium without changing normal ChatService or Immersion authority.
- [x] Add sandboxed always-on-top Electron desktop shell.
- [x] Lock Character + Timeline + Scenario + Tone before Assistant launch.
- [x] Add lightweight one-call `reaction + remark` structured Assistant generation.
- [x] Add ephemeral foreground-window/screenshot awareness with no screenshot persistence.
- [x] Add Search / Interact / Wardrobe / Quit actions and poke bursts.
- [x] Restrict Interact input to Speech and Developer/OOC; no physical RP Action channel.
- [x] Add session-scoped custom backgrounds.
- [x] Implement Rei School + Casual 10-expression half-body packs.
- [x] Show Rei Plugsuit + Bandaged wardrobes as visible but locked.
- [x] Keep all other characters `Not yet implemented` until Assistant-specific sprite packs are ready.
- [x] Keep Assistant asset/readiness state independent from Immersion.

Deferred after v0.6.0:

- Assistant sprite/wardrobe packs for additional characters;
- unlocking Rei Plugsuit and Bandaged when their files arrive;
- macOS/Linux foreground-window adapters;
- richer user-configurable screen-observation timing;
- any optional additional desktop companion behaviors that stay within the existing no-injection/no-arbitrary-OS-action boundary.

# Protean Workspace roadmap

The order matters because the architecture boundary is intended to stay stable while presentation and roleplay quality evolve.

## Completed foundation

- [x] Separate API / services / repositories / provider transport.
- [x] Local owner authentication.
- [x] Revocable JWT cookie sessions.
- [x] Backend-encrypted provider credentials configured from the frontend.
- [x] SQLite chats and persistent history.
- [x] Bounded character-library research.
- [x] Character/tone/background/frame preset boundaries.
- [x] OpenRouter behind `ChatProvider`.

## Patch 0.3 — Protean visual foundation

- [x] Rename product to **Protean Workspace**.
- [x] Integrate supplied Protean logo/icon.
- [x] Integrate supplied character portraits.
- [x] Integrate supplied backgrounds and paper/parchment textures.
- [x] Rework visual hierarchy and icon language.
- [x] Character-focused left panel.
- [x] Workspace/provider right panel.
- [x] Independently hideable sidebars.
- [x] Focus mode.
- [x] Notebook / Tablet / Terminal / Manuscript rendering.
- [x] Transcript grammar: `()` Dev, `""` Speech, `**` Action.
- [x] Character medium contract; Tom Riddle now remains diary-aware.
- [x] Target-token generation budget separate from hard token ceiling.
- [x] One continuation recovery when provider explicitly reports a length cutoff.
- [x] External layout editor prototype under `tools/layout-editor/`.
- [x] Write the presentation/editor/sprite boundaries into architecture docs.

## Patch 0.3.1 — Timeline-aware character fix

- [x] Fix scene backgrounds by replacing the negative-z background layer with an explicit isolated stack.
- [x] Apply background changes optimistically before backend persistence.
- [x] Add `CharacterPhase` as a domain object instead of encoding phases as tone text.
- [x] Add a Timeline Phase selector directly below Tone.
- [x] Persist the current phase preference and freeze `phase_id` into every new chat.
- [x] Add additive SQLite migrations for `active_phase_id` and `phase_id`.
- [x] Add hard future-knowledge locks to the prompt assembler.
- [x] Expand all built-in characters with richer story/background information.
- [x] Add canon-aware phase sets for Ann, Makoto, Hermione, Tom, Misato, Gendo and Sherlock.
- [x] Keep Sprite/Stage Mode deferred until this characterization layer is stable.

## Patch 0.3.2 — Scenario layer

- [x] Keep character, timeline, scenario and tone as separate domain concepts.
- [x] Add exactly three preset scenarios to every built-in timeline phase.
- [x] Define every scenario through `what_happening`, `who_involved`, and `dynamic`.
- [x] Add custom scenario authoring without adding arbitrary code/filesystem authority.
- [x] Freeze the effective scenario snapshot into each chat.
- [x] Preserve legacy chats by resolving missing scenarios to the phase default.
- [x] Make timeline knowledge locks outrank custom scenario circumstances.
- [x] Make tone subordinate to the scenario relationship dynamic.
- [x] Keep Sprite/Stage Mode deferred until this state layer is stable.


## Patch 0.4 — Immersion Mode

Status: **implemented with partial visual-library availability**.

- [x] Dedicated `/immersion` full-screen sub-page.
- [x] Lock-in modal for Timeline + Scenario + Tone before entry.
- [x] Reuse the existing persisted `ChatService` chat rather than creating a second conversation system.
- [x] Offer Immersion only for `ready` character/timeline asset combinations.
- [x] Semantic expression state mapped to ready sprite assets.
- [x] Transform-driven interactive movement (`approach`, `retreat`, lateral shift, lean, recoil, turn).
- [x] Ready local background selection and semantic location switching.
- [x] Diary-object mode for diary-imprint Tom.
- [x] Back returns to the normal Workspace and the same saved chat.
- [x] Keep all missing packs/backgrounds declared as `incoming`.
- [x] Never allow model output to select raw filenames/paths.
- [ ] Fill the remaining 18 planned sprite packs.
- [ ] Fill the remaining 19 planned local background slots.
- [ ] Add optional remote `BackgroundResolver` behind a separate provider boundary.
- [ ] Normalize Tom age-17 sprite canvases.
- [ ] Add richer character-specific expression vocabularies after more packs exist.

### Availability in 0.4.0

Ready Immersion timelines:

- Tom Riddle — Fifth Year / Diary Imprint / Sixth Year;
- Hermione Granger — First Year (two phases) / Fifth Year D.A.

Characters or phases whose packs remain `incoming` are intentionally absent from the Immersion launch options. A generic background alone is never enough to make a character launchable.

## Generation-quality pipeline

- [x] Soft target length + hard ceiling.
- [x] Prompt explicitly instructs the model to finish naturally inside the target.
- [x] Detect explicit provider length cutoff.
- [x] One concise continuation recovery.
- [ ] Provider streaming.
- [ ] Streaming-safe transcript parser.
- [ ] Better continuation stitch strategy for rare mid-word cutoff cases.
- [ ] Conversation summarization/token budgeting for very long chats.

## Character depth

- [x] Character card boundary.
- [x] Medium-awareness contract.
- [x] Richer scenario/state metadata.
- [x] Three timeline-dependent scenarios per phase.
- [x] Custom scenario editor with frozen chat snapshots.
- [x] Scenario-aware relationship constraints on tone.
- [x] Timeline phases with story-so-far and future-knowledge locks.
- [ ] Lore/world-book attachments per character/chat.
- [ ] Character-specific expression vocabulary.
- [ ] Optional relationship/state modules behind separate service boundaries.

## Retrieval

- [x] Knowledge-only context separated from personality.
- [ ] Metadata-aware chunks.
- [ ] Better ranking diagnostics.
- [ ] BM25 or hybrid retrieval.
- [ ] Optional embeddings behind `ContextRepository`; no vector DB requirement until justified.

## Frontend library migration

The design target remains:

- React + TypeScript;
- Vite;
- Tailwind design tokens for structural styling;
- shadcn/Base UI primitives where appropriate;
- one coherent icon library (Lucide);
- Motion for purposeful transitions;
- Zustand only for browser presentation state where it earns its complexity;
- Moveable in the external editor.

The 0.3 runtime is dependency-neutral static HTML/CSS/JS because the build environment used for this patch had no npm registry access. The backend/browser contracts were kept framework-agnostic so this migration can replace the rendering implementation without altering security or service boundaries.

## Production quality

- [x] Security headers.
- [x] Same-origin write guard.
- [x] Additive local database migrations through 0.3.2.
- [ ] Structured logging.
- [ ] Rate limiting for network deployments.
- [ ] CI.
- [ ] Container/deployment profile.
- [ ] OS/secret-manager-backed encryption key for hosted mode.

### v0.3.3 opening coherence — complete

- phase/scenario/tone-aware first message;
- backend-authoritative opening preview;
- persisted opening in chat history;
- phase-specific medium coherence for Tom Riddle;
- no Sprite/Stage implementation yet.



## Completed in 0.4.3

- Single-call structured roleplay generation with strict JSON Schema preferred and Protean-validated compatibility fallback.
- Deterministic local transcript renderer for `()` / `** **` / `""`.
- Structured one-reaction presentation metadata.
- Structured semantic scene location and explicit physical-location-change flag for Immersion backgrounds.
- Removed the normal serial visible-output model gate from the success path.

## Completed in 0.4.2

- Two-call controlled generation: private roleplay draft -> visible-output gate.
- Exactly one first-call semantic reaction feeds Immersion presentation; the second call receives that reaction and the current user message.
- Bounded retries for empty provider completions.
- Provider reasoning/thought fields are never surfaced as fallback output.
- Final local grammar gate blocks bare meta text and malformed roleplay from history/UI.
- Standalone provider artifacts such as `User Safety: Safe` are filtered/retried before display.
- No auth, database, character/timeline/scenario, Immersion routing, or asset-manifest refactor.

## Completed in 0.4.1

- Provider-generated first-message previews bound to Character + Timeline + Scenario + Tone + medium.
- Missing-key opening state with explicit re-click workflow.
- Strict Protean roleplay grammar instruction.
- One hidden semantic reaction per model message, stripped before persistence/UI.
- Model reaction drives Immersion expression selection with deterministic fallback only for malformed/legacy outputs.
- Readable block spacing between Immersion transcript beats.

Still deferred: additional sprite/background packs, remote background resolver, streaming, and broader Immersion availability.


## Completed in 0.4.4

- Progressive OpenRouter structured-output negotiation without changing the one-call roleplay architecture.
- Native strict schema remains preferred; JSON-object/plain JSON are compatibility fallbacks only.
- Per-model in-process capability cache prevents repeated strict-routing failures.
- Local Protean validation remains mandatory in every mode.


## Completed in 0.5.0

- Expanded normal-mode character library to 40 built-ins.
- Removed Sherlock Holmes.
- Converted built-in scenarios toward phase-specific event hooks while preserving stable scenario IDs.
- Added Polyjuice-era Hermione and five additional scene-aware tones.
- Added dynamic `Implemented` / `Not yet implemented` Immersion status in Presentation controls.
- Reserved incoming sprite slots for new character phases and incoming curated background IDs for the expanded franchises.

Still intentionally deferred: supplying those new sprite/background files and enabling Immersion for characters whose visual routes remain incomplete.
