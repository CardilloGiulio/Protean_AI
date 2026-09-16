# RC2 Stabilization Scope

## Provenance

RC2 is derived from the supplied `protean-workspace-v0.6.1(20260913-012934).zip` whose SHA-256 is:

```text
2c89cb5ff612696c6a38879b9979777ccdca3a32ff47dbade0e465ea21c2c236
```

The archive was independently re-extracted and compared against the RC2 working tree. Two unrelated altered image copies found during work were restored byte-for-byte from that verified base before RC2 changes continued.

## Invariants preserved

- Normal, Immersion, and Virtual Assistant remain separate surfaces and service boundaries.
- Roleplay generation remains one structured provider request on the successful path, with one bounded retry.
- Character → Timeline → Scenario → Tone → Medium remains the authority hierarchy.
- FastAPI keeps prompts, provider credentials, validation, persistence, and Assistant sessions.
- Renderers keep presentation/input only and never receive the provider key.
- Models emit semantic reaction/location data; local code owns sprites, backgrounds, filenames, paths, transcript rendering, files, database, and OS behavior.
- Database evolution is additive and preserves existing chats.
- Existing character, phase, scenario, asset, and route identifiers remain stable except the canonically impossible Rengoku phase/manifest entry.
- Virtual Assistant remains Rei-only; locked Rei wardrobes remain visible but unavailable.
- Electron retains `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, disabled developer tools, and a narrow IPC/backend allowlist.

## Explicitly out of scope

- No streaming, new provider, model-selection redesign, or prompt framework.
- No React/frontend migration, plugin system, database replacement, or new service architecture.
- No new character, scenario, tone, wardrobe, sprite, or background feature.
- No expansion of Assistant filesystem, OS, action, provider, or renderer authority.
- No unrelated visual redesign or asset replacement. The existing oversized Hogwarts corridor background was only resized and correctly re-encoded as WebP.
- No cleanup/refactor unrelated to a named blocker, major, test, installer, or required release document.

## Minimal RC2 changes

The delta is limited to the seven release blockers and the approved high-value majors: consent, atomic/idempotent turns, safe errors, prompt boundaries, two canon corrections, Windows install/process stability, Assistant lifecycle/busy state, cleanup, dependency locks, one oversized background, truncated completion handling, opening-medium consistency, regression tests, and release/privacy/IP documentation.
