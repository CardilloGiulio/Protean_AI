# RC2 Testing and Release Gate

RC2 is a stabilization release cut from the supplied RC1 archive. It adds no product features and preserves the existing Normal, Immersion, and Virtual Assistant boundaries.

## Automated regression gate

From the project root:

```bat
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check --select E9,F src tests
```

The targeted RC2 tests cover screen consent, atomic/idempotent chat turns, provider sanitization, length cutoffs, prompt authority, Sumire/Rengoku canon, installer branches, dependency locks, Assistant lifecycle and cleanup, image limits, opening medium, and Electron security settings.

## Windows/Electron release gate

Automated Linux tests cannot certify native Windows process behavior. On the final Windows target:

1. Extract RC2 into a clean path without reusing RC1's `.venv` or `node_modules`.
2. Run `install.bat`. Continue only if it reports both `Python workspace: READY` and `Virtual Assistant: READY`, then run `start.bat`.
3. Sign in, configure the provider, and exercise Rei's screen off/on/off, wardrobe switching, custom background, chat submission, window close, relaunch, logout, and server shutdown. Confirm no Electron process remains.
4. Start the app and Assistant again, close other Electron applications, then run `powershell -ExecutionPolicy Bypass -File scripts\windows-electron-soak.ps1` in a second terminal. Keep the Assistant open and use screen/interact/wardrobe periodically for the full run.
5. Keep its CSV and summary text with the release evidence.

The gate passes only when automated tests pass, the soak summary says `PASS`, no screenshots/secrets appear in logs or database files, Electron closes on logout/server loss, and repeated launch/close leaves no orphan Electron process.

Until the native run is complete, label RC2 **code-complete, Windows certification pending**. Do not freeze it as the final Windows-certified build.
