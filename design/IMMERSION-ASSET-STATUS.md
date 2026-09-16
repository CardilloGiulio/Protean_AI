# Immersion asset status — v0.5.0

Immersion runtime is now enabled **only for character/timeline combinations backed by ready assets**. Missing packs/backgrounds remain open as `incoming` and are not offered in the entry modal.

## Ready sprite packs

- `hermione-year1` — 7/7 expressions
- `hermione-year5` — 7/7 expressions
- `tom-student-16` — 7/7 expressions
- `tom-student-17` — 7/7 expressions; supplied canvas sizes vary, so normalization remains open

Every ready pack includes:

- neutral
- positive
- amused
- serious
- concerned
- surprised
- thinking

## Launchable timelines

- Tom Riddle — `fifth-year-chamber`
- Tom Riddle — `diary-imprint` (diary-object mode; physical sprite hidden by default)
- Tom Riddle — `sixth-year-horcrux`
- Hermione Granger — `first-year-arrival`
- Hermione Granger — `first-year-post-troll`
- Hermione Granger — `fifth-year-da`

Ann, Makoto, Misato, Gendo, all newly added characters, and unsupported Hermione phases remain unavailable until their sprite/background routes are complete.

## Backgrounds

17 local backgrounds are ready. Immersion uses declared ready backgrounds only and changes location from structured semantic scene state, never by scanning dialogue for place names.

The expanded v0.5.0 manifest keeps the remaining curated background slots as `incoming`.

## Boundary

The manifest and Immersion presentation handler may decide only visual availability and declared asset IDs. They cannot alter Character, Timeline, Scenario, Tone, knowledge locks, authentication, provider credentials, persistence, prompt authority, or filesystem access.
