# Protean Workspace - Technology List

**Project:** Protean Workspace  
**Release:** v0.6.1 RC2 - Frozen  
**Certification:** Native Windows/Electron certification passed  
**Repository:** https://github.com/CardilloGiulio/Protean_AI

## Architecture summary

Protean Workspace is a local-first roleplay and desktop-assistant application. A Python/FastAPI backend owns authentication, persistence, prompt construction, provider access, validation, and security boundaries. The browser interface uses self-contained HTML, CSS, and JavaScript, while the optional Virtual Assistant is rendered by a sandboxed Electron desktop shell.

## Principal technologies

| Area | Technology | RC2 version or requirement | Role in Protean Workspace |
|---|---|---:|---|
| Core runtime | Python | 3.11 or later | Application services, domain logic, persistence, validation, provider integration, and lifecycle management. |
| Web API | FastAPI | 0.141.1 | Local HTTP API, authentication routes, chat, character library, Immersion, and Assistant endpoints. |
| ASGI server | Uvicorn | 0.52.4 | Runs the local FastAPI application on `127.0.0.1`. |
| Data validation | Pydantic / Pydantic Settings | 2.13.5 / 2.15.0 | Validates API payloads, configuration, and structured model responses. |
| Local persistence | SQLite through Python `sqlite3` | Python standard library | Stores local users, encrypted provider credentials, chats, messages, and application state without a cloud database. |
| AI provider layer | OpenRouter HTTPS API | Provider/model selectable | Supplies model completions through a bounded backend-owned structured-output contract. |
| HTTP client | HTTPX | 0.28.1 | Performs asynchronous backend-to-provider HTTPS requests. |
| Browser interface | HTML5, CSS3, vanilla JavaScript | Self-contained static runtime | Implements Workspace and Immersion without a frontend framework or browser-side secret ownership. |
| Desktop companion | Electron | 44.2.0 | Provides Rei's always-on-top Virtual Assistant window, controlled screen capture, and constrained native integration. |
| Desktop toolchain | Node.js / npm | Node.js 22.12 or later | Installs and launches the locked Electron runtime. |
| Authentication and security | Argon2-cffi, Cryptography/Fernet, PyJWT | 25.1.0 / 47.0.0 / 2.14.0 | Password hashing, encrypted provider credentials, and signed local authentication tokens. |
| Image processing | Pillow | 12.3.0 | Validates, resizes, and safely re-encodes custom Assistant backgrounds and screen observations. |
| Automated testing | pytest | 9.1.1 | Runs unit, integration, regression, security-boundary, and lifecycle tests. |
| Static analysis | Ruff | 0.16.7 | Performs Python correctness linting and code-quality checks. |
| Packaging and dependency control | venv, pip, Setuptools, `requirements-lock.txt`, `package-lock.json`, `npm ci` | Setuptools 80.9.0 | Provides reproducible Python and Electron installations. |
| Windows automation | Batch and PowerShell | Native Windows tooling | Supplies the two public entry points, `install.bat` and `start.bat`, plus the Windows/Electron soak-certification harness. |
| Version control and delivery | Git and GitHub | Tag `v0.6.1-rc2` | Publishes the frozen source, documentation, tests, dependency locks, and certification evidence. |

## Deliberate technical choices

- **Local-first storage:** SQLite keeps user and conversation data on the local machine.
- **Backend-owned trust boundaries:** provider keys, prompts, validation, persistence, and asset selection are not delegated to the browser or model.
- **Framework-light frontend:** the delivered browser runtime is static HTML/CSS/JavaScript rather than React or another SPA framework.
- **Sandboxed Electron renderer:** `contextIsolation=true`, `nodeIntegration=false`, and `sandbox=true` restrict desktop privileges.
- **Locked dependencies:** Python and Electron dependencies are committed as reproducible lock files.
- **Model portability:** OpenRouter model selection is configurable while the local validation and safety contract remains authoritative.

## RC2 verification

- Complete automated suite: **88 tests passed**.
- Native Windows/Electron soak: **PASS**, 60 minutes and 717 samples.
- Electron memory growth remained below the configured 300 MB limits.
- Full evidence is available in `RC2-RELEASE-STATUS.md` and the repository `artifacts/` directory.

