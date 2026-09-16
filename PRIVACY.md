# Privacy

Protean Workspace is local-first, but AI generation is not offline. This document describes the RC2 data boundary.

## Data stored locally

- Accounts, chats, settings, selected roleplay state, and login records are stored in the local SQLite database under the configured Protean instance directory.
- Provider API keys are encrypted at rest with the local application encryption key and decrypted only for a provider request.
- Imported reference material and custom Assistant backgrounds remain local unless their contents are deliberately included in a generation request.
- Assistant screenshots are not written to the database, logs, chat history, or background folders. Screen observation starts off for every Assistant session.

## Data sent to the AI provider

Normal and Immersion generation sends the selected Character → Timeline → Scenario → Tone → Medium instructions, relevant chat history, the current user message, and selected reference context to the configured provider.

Virtual Assistant sends its selected state and current event. Only after the user explicitly enables screen observation does an event also send the active application name, window/page title, and one downscaled screenshot. The control can be turned off at any time; later events then carry no screen data.

Protean cannot control provider processing or retention after a request leaves the computer. Review the configured provider's terms before adding a key or enabling screen observation. Do not display passwords, private keys, financial data, health records, or other sensitive material while it is enabled.

## Errors, retention, and deletion

- Provider response bodies are not exposed through user-facing errors or Protean logs. Failures are reduced to application-owned status messages.
- Logging out revokes the login record and closes that user's live Assistant session.
- Expired/revoked login records are purged during startup and normal authentication activity.
- Temporary Assistant background copies are removed when a session closes; stale controlled copies are removed at startup/shutdown.
- Delete chats through the application. For a complete reset, stop Protean and remove its configured instance directory. This permanently removes local accounts, chats, settings, encrypted credentials, and imports; back it up first if needed.

## Security boundary

Prompt-boundary instructions reduce the chance that scenario, location, reference, conversation, or screen text is treated as model authority. They are not a guarantee against every model behavior. File, database, operating-system, renderer, and asset capabilities remain enforced by code rather than granted to the model.
