# RC2 Release Status

Status: **CODE-COMPLETE — NATIVE WINDOWS CERTIFICATION PENDING**

Date: 2026-09-14

## Completed gates

- Exact RC1 source archive SHA-256 recorded and clean extraction compared.
- RC2-targeted regressions: **17 passed**.
- Complete inherited + RC2 suite: **88 passed**.
- Full suite repeated under a fresh environment installed from `requirements-lock.txt`: **88 passed**.
- Correctness lint (`E9`, `F`) across the Python package and RC2 tests: passed.
- Electron lock reproduction: full `npm ci` passed; the installed Linux binary reported `v44.2.0` in the non-UI version check.
- JSON character/asset manifests: parsed successfully.
- Windows entry points consolidated to exactly `install.bat` and `start.bat`; the installer explicitly fetches Electron 44's platform binary after `npm ci`, success requires the exact executable used by the runtime, and startup reruns the same installer when either runtime is missing.
- Oversized background corrected from an 8,070,311-byte, 8686×5790 JPEG mislabeled `.webp` to a 475,200-byte, 2160×1440 WebP.
- Local service/resource stress check: 900 requests (500 health, 300 duplicate chat sends, 100 Assistant start/close cycles); one provider call for all duplicate sends, three expected chat messages, zero live Assistant sessions, about 195 KiB retained and 562 KiB peak Python allocations after collection.

Two deprecation warnings originate in FastAPI/Starlette's test compatibility layer; they do not represent failed Protean tests.

## Open release gate

This build environment is Linux and cannot execute or certify native Windows `install.bat`, `electron.exe`, foreground-window capture, process-tree shutdown, or Windows memory behavior. The installer/runtime path contract is covered by regression tests, while `scripts/windows-electron-soak.ps1` and the manual lifecycle procedure in `TESTING.md` remain required on the target Windows machine.

RC2 must not be frozen, tagged as Windows-certified, or promoted to Phase B until that native run passes and its CSV/summary evidence is added to the release record.
