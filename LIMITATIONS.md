# Known Limitations

- AI generation needs network access and a user-supplied provider credential; local-first does not mean offline inference.
- Prompt-injection defenses are layered safeguards, not a mathematical guarantee of model compliance.
- Screen observation is available only through the Windows Electron Assistant and must be enabled for each session.
- Screen capture is not an operating-system data-loss-prevention boundary. Keep sensitive windows off screen while observation is enabled.
- Protean is designed as a local single-user workspace, not an internet-exposed multi-tenant service.
- Character and timeline fidelity depends on curated card data and the configured model; generated text can still be inaccurate.
- Users remain responsible for privacy, copyright, and provider-policy compliance for custom/imported material.
- Native Windows/Electron stability is certified only after the soak in `TESTING.md` is completed on the target Windows build.
