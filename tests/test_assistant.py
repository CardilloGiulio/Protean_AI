import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from protean_workspace.core.config import Settings
from protean_workspace.main import create_app
from protean_workspace.clients.provider import CompletionResult


PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "protean_workspace"


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(
        instance_dir=tmp_path / "instance",
        static_dir=PACKAGE_DIR / "static",
        context_dir=PACKAGE_DIR / "data" / "context",
        default_library_root=PACKAGE_DIR / "data" / "library",
        secure_cookies=False,
        _env_file=None,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client, settings


class FakeAssistantLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, *, base_url: str, session_token: str) -> None:
        self.calls.append((base_url, session_token))


class AssistantProvider:
    def __init__(self):
        self.calls = []

    async def complete_structured(self, **kwargs):
        self.calls.append(kwargs)
        joined = "\n".join(
            item["content"] if isinstance(item.get("content"), str) else "[vision-content]"
            for item in kwargs["messages"]
        )
        if "ASSISTANT EVENT: wardrobe_change" in joined:
            return CompletionResult(json.dumps({"reaction": "embarrassed", "remark": "You changed it."}), "stop")
        if "ASSISTANT EVENT: poke" in joined:
            return CompletionResult(json.dumps({"reaction": "annoyed", "remark": "Why are you doing that?"}), "stop")
        return CompletionResult(json.dumps({"reaction": "thinking", "remark": "I can see what you are looking at."}), "stop")

    async def complete(self, **kwargs):
        return CompletionResult("unused", "stop")

    async def validate_key(self, api_key: str):
        return {}


def setup_owner(http):
    response = http.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert response.status_code == 201


def configure_assistant(http):
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-assistant-test-key", "max_tokens": 2048})
    provider = AssistantProvider()
    launcher = FakeAssistantLauncher()
    http.app.state.assistant_service._provider = provider
    http.app.state.assistant_desktop_launcher = launcher
    return provider, launcher


def test_assistant_manifest_rei_has_ready_and_locked_wardrobes():
    manifest = json.loads((PACKAGE_DIR / "static/assets/assistant/manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "protean.assistant-assets/v1"
    assert manifest["assistant_mode_enabled"] is True
    assert [item["character_id"] for item in manifest["characters"]] == ["rei-ayanami"]
    rei = manifest["characters"][0]
    assert set(rei["expressions"]) == {
        "neutral", "positive", "amused", "serious", "concerned",
        "surprised", "thinking", "embarrassed", "annoyed", "tired",
    }
    wardrobes = {item["id"]: item for item in rei["wardrobes"]}
    assert wardrobes["school"]["status"] == "ready"
    assert wardrobes["casual"]["status"] == "ready"
    assert wardrobes["plugsuit"]["status"] == "locked"
    assert wardrobes["bandaged"]["status"] == "locked"
    for wardrobe_id in ("school", "casual"):
        for expression in rei["expressions"]:
            path = wardrobes[wardrobe_id]["expressions"][expression]["path"]
            assert path.startswith("/static/assets/assistant/sprites/rei/")
            assert (PACKAGE_DIR / "static" / path.removeprefix("/static/")).exists()


def test_assistant_availability_only_exposes_rei_and_locked_skins(client):
    http, _ = client
    setup_owner(http)
    response = http.get("/api/assistant/availability")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert [item["character_id"] for item in body["characters"]] == ["rei-ayanami"]
    rei = body["characters"][0]
    assert {phase["id"] for phase in rei["phases"]} == {"early-rei", "middle-rei", "rei-iii"}
    wardrobes = {item["id"]: item["status"] for item in rei["wardrobes"]}
    assert wardrobes == {
        "school": "ready",
        "casual": "ready",
        "plugsuit": "locked",
        "bandaged": "locked",
    }


def test_assistant_start_rejects_other_characters_and_locked_rei_skin(client):
    http, _ = client
    setup_owner(http)
    configure_assistant(http)
    unsupported = http.post(
        "/api/assistant/start",
        json={
            "character_id": "asuka-langley-soryu",
            "phase_id": "arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "school",
            "background_mode": "transparent",
        },
    )
    assert unsupported.status_code == 409
    locked = http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "early-rei",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "plugsuit",
            "background_mode": "transparent",
        },
    )
    assert locked.status_code == 409
    assert "locked" in locked.json()["detail"].lower()


def test_assistant_launch_token_stays_out_of_browser_response_and_drives_ephemeral_events(client):
    http, _ = client
    setup_owner(http)
    provider, launcher = configure_assistant(http)
    start = http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "early-rei",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "school",
            "background_mode": "protean",
        },
    )
    assert start.status_code == 201
    body = start.json()
    assert body["launched"] is True
    assert "token" not in json.dumps(body).lower()
    assert len(launcher.calls) == 1
    token = launcher.calls[0][1]

    session = http.get("/api/assistant/session", headers={"Authorization": f"Bearer {token}"})
    assert session.status_code == 200
    state = session.json()
    assert state["character_id"] == "rei-ayanami"
    assert state["wardrobe_id"] == "school"
    assert state["background_mode"] == "protean"
    assert state["sprite_paths"]["embarrassed"].endswith("/rei/school/embarrassed.webp")

    event = http.post(
        "/api/assistant/session/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "idle_observation",
            "screen": {"application": "chrome", "window_title": "Dog photo - Browser", "image_data_url": ""},
        },
    )
    assert event.status_code == 200
    assert event.json()["reaction"] == "thinking"
    assert event.json()["remark"] == "I can see what you are looking at."
    assert provider.calls
    # Assistant mode never creates/persists a normal RP chat.
    assert http.get("/api/chats").json() == []


def test_assistant_wardrobe_switch_is_immediate_then_ai_remark_uses_new_skin(client):
    http, _ = client
    setup_owner(http)
    _, launcher = configure_assistant(http)
    http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "middle-rei",
            "scenario_id": "known-acquaintance",
            "tone_id": "intimate",
            "wardrobe_id": "school",
            "background_mode": "transparent",
        },
    )
    token = launcher.calls[0][1]
    changed = http.post(
        "/api/assistant/session/wardrobe",
        headers={"Authorization": f"Bearer {token}"},
        json={"wardrobe_id": "casual"},
    )
    assert changed.status_code == 200
    assert changed.json()["wardrobe_id"] == "casual"
    assert changed.json()["sprite_paths"]["neutral"].endswith("/rei/casual/neutral.webp")

    remark = http.post(
        "/api/assistant/session/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "wardrobe_change",
            "old_wardrobe_id": "school",
            "new_wardrobe_id": "casual",
        },
    )
    assert remark.status_code == 200
    assert remark.json()["reaction"] == "embarrassed"
    assert remark.json()["wardrobe_id"] == "casual"
    assert remark.json()["sprite_paths"]["embarrassed"].endswith("/rei/casual/embarrassed.webp")


def test_assistant_workspace_ui_and_bridge_keep_mode_separate(client):
    http, _ = client
    html = http.get("/").text
    assert 'id="assistantStatusBadge"' in html
    assert 'id="assistantButton"' in html
    assert "Plugsuit" not in html  # Wardrobe contents are manifest-driven, not hard-coded.
    assert "Virtual Assistant" in html
    bridge = http.get("/assistant")
    assert bridge.status_code == 200
    assert "Desktop companion launched" in bridge.text
    js = http.get("/static/js/app.js").text
    assert '"/api/assistant/availability"' in js
    assert 'window.location.assign(result.bridge_url || "/assistant")' in js


def test_assistant_shell_security_and_interaction_contract():
    main = (PACKAGE_DIR / "assistant_shell/main.js").read_text(encoding="utf-8")
    preload = (PACKAGE_DIR / "assistant_shell/preload.js").read_text(encoding="utf-8")
    renderer = (PACKAGE_DIR / "assistant_shell/renderer.js").read_text(encoding="utf-8")
    html = (PACKAGE_DIR / "assistant_shell/assistant.html").read_text(encoding="utf-8")
    assert "nodeIntegration: false" in main
    assert "contextIsolation: true" in main
    assert "sandbox: true" in main
    assert 'setAlwaysOnTop(true, "pop-up-menu")' in main
    assert "desktopCapturer" in main
    assert "duckduckgo.com/?q=" in main
    assert "contextBridge.exposeInMainWorld" in preload
    assert 'data-action="search"' in html
    assert 'data-action="interact"' in html
    assert 'data-action="wardrobe"' in html
    assert 'data-action="quit"' in html
    assert 'data-input-type="speech"' in html
    assert 'data-input-type="dev"' in html
    assert "idle_observation" in renderer
    assert "poke_count" in renderer


def test_assistant_custom_background_is_controlled_and_deleted_on_close(client):
    import base64
    import io

    from PIL import Image

    http, settings = client
    setup_owner(http)
    _, launcher = configure_assistant(http)
    buffer = io.BytesIO()
    Image.new("RGB", (320, 180), (24, 36, 52)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    start = http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "early-rei",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "school",
            "background_mode": "custom",
            "custom_background_data_url": f"data:image/png;base64,{encoded}",
            "custom_background_name": "my-background.png",
        },
    )
    assert start.status_code == 201
    token = launcher.calls[0][1]
    background = http.get(
        "/api/assistant/session/background",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert background.status_code == 200
    assert background.headers["content-type"].startswith("image/webp")
    stored = list((settings.instance_dir / "assistant_backgrounds").rglob("*.webp"))
    assert len(stored) == 1

    closed = http.post(
        "/api/assistant/session/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert closed.status_code == 200
    assert not stored[0].exists()


def test_rei_assistant_prompt_enforces_sparse_speech_and_originality(client):
    http, _ = client
    setup_owner(http)
    provider, launcher = configure_assistant(http)
    http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "early-rei",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "school",
            "background_mode": "transparent",
        },
    )
    token = launcher.calls[0][1]
    event = http.post(
        "/api/assistant/session/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "idle_observation", "screen": {"application": "chrome", "window_title": "A quiet page"}},
    )
    assert event.status_code == 200
    prompt = "\n".join(
        str(message.get("content") or "")
        for message in provider.calls[0]["messages"]
        if isinstance(message.get("content"), str)
    )
    assert "REI AYANAMI — VIRTUAL ASSISTANT CHARACTER DISCIPLINE" in prompt
    assert "short precise sentence" in prompt
    assert "Do not repeatedly start remarks with 'I see'" in prompt
    assert "Never repeat the same remark twice in a row" in prompt
    assert "Early Rei is the most minimal" in prompt


def test_assistant_recent_history_rejects_duplicate_remark_and_requests_novelty(client):
    class RepeatingThenNovelProvider:
        def __init__(self):
            self.calls = []

        async def complete_structured(self, **kwargs):
            self.calls.append(kwargs)
            joined = "\n".join(
                item["content"] if isinstance(item.get("content"), str) else "[vision-content]"
                for item in kwargs["messages"]
            )
            if "NOVELTY CORRECTION" in joined:
                return CompletionResult(json.dumps({"reaction": "thinking", "remark": "You have not changed the page. Are you waiting for something?"}), "stop")
            return CompletionResult(json.dumps({"reaction": "thinking", "remark": "You are still looking at the same page."}), "stop")

        async def complete(self, **kwargs):
            return CompletionResult("unused", "stop")

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-assistant-test-key", "max_tokens": 2048})
    provider = RepeatingThenNovelProvider()
    launcher = FakeAssistantLauncher()
    http.app.state.assistant_service._provider = provider
    http.app.state.assistant_desktop_launcher = launcher
    http.post(
        "/api/assistant/start",
        json={
            "character_id": "rei-ayanami",
            "phase_id": "early-rei",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
            "wardrobe_id": "school",
            "background_mode": "transparent",
        },
    )
    token = launcher.calls[0][1]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"event_type": "idle_observation", "screen": {"application": "chrome", "window_title": "Same page"}}

    first = http.post("/api/assistant/session/events", headers=headers, json=payload)
    second = http.post("/api/assistant/session/events", headers=headers, json=payload)

    assert first.status_code == 200
    assert first.json()["remark"] == "You are still looking at the same page."
    assert second.status_code == 200
    assert second.json()["remark"] == "You have not changed the page. Are you waiting for something?"
    assert len(provider.calls) == 3
    history_prompt = "\n".join(
        str(message.get("content") or "")
        for message in provider.calls[1]["messages"]
        if isinstance(message.get("content"), str)
    )
    assert "NOVELTY RULE" in history_prompt
    assert "You are still looking at the same page." in history_prompt
    novelty_prompt = "\n".join(
        str(message.get("content") or "")
        for message in provider.calls[2]["messages"]
        if isinstance(message.get("content"), str)
    )
    assert "NOVELTY CORRECTION" in novelty_prompt
