from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from protean_workspace.core.config import Settings
from protean_workspace.main import create_app


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


def setup_owner(client: TestClient) -> None:
    response = client.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert response.status_code == 201


def make_structured_completion(
    *,
    action: str = "The character remains attentive.",
    speech: str = "Understood.",
    reaction: str = "neutral",
    location: str = "current scene",
    changed: bool = False,
):
    import json
    from protean_workspace.clients.provider import CompletionResult

    return CompletionResult(
        json.dumps({
            "reaction": reaction,
            "location": {"label": location, "changed": changed},
            "beats": [
                {"type": "action", "text": action},
                {"type": "speech", "text": speech},
            ],
        }),
        "stop",
    )


class GeneratedOpeningProvider:
    async def complete(self, **kwargs):
        from protean_workspace.clients.provider import CompletionResult
        import re

        messages = kwargs["messages"]
        system = messages[0]["content"]
        last = messages[-1]["content"]
        if "Protean Workspace visible-output gate" in system:
            match = re.search(r"PRIVATE DRAFT \(source material to filter\):\n([\s\S]*?)\n\nReturn only", last)
            draft = match.group(1).strip() if match else '**The character remains attentive.**\n\n"Understood."'
            return CompletionResult(draft, "stop")
        if "Generate the first assistant message" in last:
            scenario = "scene"
            marker = "Name: "
            if "SELECTED SCENARIO" in system and marker in system:
                tail = system.split("SELECTED SCENARIO", 1)[1]
                scenario = tail.split(marker, 1)[1].splitlines()[0].strip()
            what = ""
            if "What is happening: " in system:
                what = system.split("What is happening: ", 1)[1].splitlines()[0].strip()
            tone = "intimate" if "TONE PRESET — Intimate" in system else "canon"
            if "MEDIUM: enchanted diary" in system:
                visible = f'**Ink gathers across the page for {scenario}.**\n\n"{what or "You have my attention."}"'
                reaction = "thinking"
            else:
                visible = f'**The {scenario.lower()} begins with a {tone} bearing.**\n\n"{what or "Hello."}"'
                reaction = "neutral"
            return CompletionResult(
                f"[[PROTEAN_DRAFT]]\n{visible}\n[[/PROTEAN_DRAFT]]\n[[PROTEAN_REACTION:{reaction}]]",
                "stop",
            )
        return CompletionResult(
            '[[PROTEAN_DRAFT]]\n**The character remains attentive.**\n\n"Understood."\n[[/PROTEAN_DRAFT]]\n[[PROTEAN_REACTION:neutral]]',
            "stop",
        )

    async def complete_structured(self, **kwargs):
        messages = kwargs["messages"]
        system = messages[0]["content"]
        joined = "\n".join(item["content"] for item in messages)
        scenario = "scene"
        if "SELECTED SCENARIO" in system and "Name: " in system:
            tail = system.split("SELECTED SCENARIO", 1)[1]
            scenario = tail.split("Name: ", 1)[1].splitlines()[0].strip()
        what = ""
        if "What is happening: " in system:
            what = system.split("What is happening: ", 1)[1].splitlines()[0].strip()
        tone = "intimate" if "TONE PRESET — Intimate" in system else "canon"
        location = "Hogwarts corridor"
        if "Chamber of Secrets" in what:
            location = "the Chamber of Secrets"
        elif "moon" in what.lower():
            location = "Hogwarts grounds beneath the moonlight"
        elif "MEDIUM: enchanted diary" in system:
            location = "Tom Riddle's diary on a desk"
        elif "library" in what.lower():
            location = "Hogwarts library"
        if "Generate the first assistant message" in joined:
            if "MEDIUM: enchanted diary" in system:
                return make_structured_completion(
                    action=f"Ink gathers across the page for {scenario}.",
                    speech=what or "You have my attention.",
                    reaction="thinking",
                    location=location,
                )
            return make_structured_completion(
                action=f"The {scenario.lower()} begins with a {tone} bearing.",
                speech=what or "Hello.",
                reaction="neutral",
                location=location,
            )
        return make_structured_completion(location=location)

    async def validate_key(self, api_key: str):
        return {}


def configure_generated_openings(http: TestClient) -> GeneratedOpeningProvider:
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-generated-opening-test"})
    provider = GeneratedOpeningProvider()
    http.app.state.chat_service._provider = provider
    return provider


def test_first_run_setup_and_cookie_security(client) -> None:
    http, _ = client
    status_response = http.get("/api/auth/status")
    assert status_response.json() == {
        "initialized": False,
        "authenticated": False,
        "username": None,
    }

    response = http.post(
        "/api/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert response.status_code == 201
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie

    status_response = http.get("/api/auth/status")
    assert status_response.json()["authenticated"] is True
    assert status_response.json()["username"] == "owner"


def test_protected_api_requires_authentication(client) -> None:
    http, _ = client
    response = http.get("/api/settings/preferences")
    assert response.status_code == 401


def test_provider_key_is_encrypted_at_rest(client) -> None:
    http, settings = client
    setup_owner(http)
    secret = "sk-or-v1-super-secret-test-value"
    response = http.put(
        "/api/settings/provider",
        json={"api_key": secret, "model": "openrouter/free", "temperature": 0.7, "max_tokens": 512},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert secret not in str(body)
    assert body["masked_key"].startswith("sk-or-v1")

    database_bytes = settings.database_path.read_bytes()
    assert secret.encode("utf-8") not in database_bytes


def test_character_research_finds_built_in_franchises(client) -> None:
    http, _ = client
    setup_owner(http)

    persona = http.post("/api/characters/research", json={"query": "Makoto"})
    assert persona.status_code == 200
    assert any(item["id"] == "makoto-niijima" for item in persona.json()["characters"])

    evangelion = http.post("/api/characters/research", json={"query": "Evangelion"})
    assert evangelion.status_code == 200
    assert {item["franchise"] for item in evangelion.json()["characters"]} == {"Neon Genesis Evangelion"}


def test_library_root_must_exist(client, tmp_path: Path) -> None:
    http, _ = client
    setup_owner(http)
    missing = tmp_path / "not-here"
    response = http.put("/api/settings/preferences", json={"library_root": str(missing)})
    assert response.status_code == 400


def test_chat_persists_and_missing_key_is_clean_error(client) -> None:
    http, _ = client
    setup_owner(http)

    created = http.post("/api/chats", json={"character_id": "tom-riddle", "tone_id": "canon"})
    assert created.status_code == 201
    chat_id = created.json()["id"]

    response = http.post(f"/api/chats/{chat_id}/messages", json={"message": "Hello"})
    assert response.status_code == 409
    assert "OpenRouter" in response.json()["detail"]

    detail = http.get(f"/api/chats/{chat_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"]


def test_logout_revokes_server_side_session(client) -> None:
    http, _ = client
    setup_owner(http)
    assert http.get("/api/settings/preferences").status_code == 200
    assert http.post("/api/auth/logout").status_code == 204
    assert http.get("/api/settings/preferences").status_code == 401


def test_cross_origin_write_is_rejected(client) -> None:
    http, _ = client
    response = http.post(
        "/api/auth/setup",
        headers={"Origin": "https://evil.example"},
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert response.status_code == 403


def test_character_response_exposes_medium_and_portrait(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post("/api/characters/research", json={"query": "Tom Riddle"})
    assert response.status_code == 200
    tom = next(item for item in response.json()["characters"] if item["id"] == "tom-riddle")
    assert tom["medium_type"] == "enchanted diary"
    assert tom["portrait"].endswith("char-tom-riddle.webp")


def test_target_tokens_and_hard_ceiling_are_separate(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.put(
        "/api/settings/provider",
        json={"target_tokens": 420, "max_tokens": 800},
    )
    assert response.status_code == 200
    assert response.json()["target_tokens"] == 420
    assert response.json()["max_tokens"] == 800

    rejected = http.put(
        "/api/settings/provider",
        json={"target_tokens": 700, "max_tokens": 760},
    )
    assert rejected.status_code == 400


def test_structured_generation_uses_one_provider_call_on_success(client) -> None:
    class OneCallProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_structured(self, **kwargs):
            self.calls += 1
            assert kwargs["response_format"]["type"] == "json_schema"
            return make_structured_completion(
                action="Hermione closes the book.",
                speech="All right.",
                reaction="neutral",
                location="Hogwarts corridor",
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-one-call-test"})
    provider = OneCallProvider()
    http.app.state.chat_service._provider = provider
    created = http.post(
        "/api/chats",
        json={"character_id": "hermione-granger", "phase_id": "first-year-arrival", "tone_id": "canon"},
    )
    response = http.post(f'/api/chats/{created.json()["id"]}/messages', json={"message": '"Continue."'})
    assert response.status_code == 200
    assert provider.calls == 1
    assert response.json()["reply"] == '**Hermione closes the book.**\n\n"All right."'

def test_character_timeline_phases_are_exposed(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post("/api/characters/research", json={"query": "Hermione"})
    assert response.status_code == 200
    hermione = next(item for item in response.json()["characters"] if item["id"] == "hermione-granger")
    phase_ids = {phase["id"] for phase in hermione["phases"]}
    assert "first-year-arrival" in phase_ids
    assert "horcrux-hunt" in phase_ids
    assert hermione["default_phase_id"] == "fifth-year-da"


def test_phase_selection_is_validated_and_persisted(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.put(
        "/api/settings/preferences",
        json={"active_character_id": "ann-takamaki", "active_phase_id": "okumura-arc"},
    )
    assert response.status_code == 200
    assert response.json()["active_phase_id"] == "okumura-arc"

    rejected = http.put(
        "/api/settings/preferences",
        json={"active_phase_id": "battle-of-hogwarts"},
    )
    assert rejected.status_code == 400


def test_chat_freezes_timeline_phase(client) -> None:
    http, _ = client
    setup_owner(http)
    created = http.post(
        "/api/chats",
        json={"character_id": "ann-takamaki", "phase_id": "pre-kamoshida", "tone_id": "canon"},
    )
    assert created.status_code == 201
    assert created.json()["phase_id"] == "pre-kamoshida"
    chat_id = created.json()["id"]
    detail = http.get(f"/api/chats/{chat_id}")
    assert detail.json()["phase_id"] == "pre-kamoshida"


def test_background_layer_uses_explicit_non_negative_stack(client) -> None:
    http, _ = client
    css = http.get("/static/css/app.css")
    assert css.status_code == 200
    body = css.text
    ambient = body.split(".ambient-layer {", 1)[1].split("}", 1)[0]
    assert "z-index: 0" in ambient
    assert "z-index: -" not in ambient
    assert "isolation: isolate" in body


def test_selected_phase_reaches_system_prompt(client) -> None:
    from protean_workspace.clients.provider import CompletionResult

    class CapturingProvider:
        def __init__(self) -> None:
            self.messages = None

        async def complete(self, **kwargs):
            import re

            messages = kwargs["messages"]
            if "Protean Workspace visible-output gate" in messages[0]["content"]:
                match = re.search(r"PRIVATE DRAFT \(source material to filter\):\n([\s\S]*?)\n\nReturn only", messages[-1]["content"] )
                return CompletionResult(match.group(1).strip(), "stop")
            self.messages = messages
            return CompletionResult(
                '[[PROTEAN_DRAFT]]\n"Understood."\n[[/PROTEAN_DRAFT]]\n[[PROTEAN_REACTION:neutral]]',
                "stop",
            )

        async def complete_structured(self, **kwargs):
            self.messages = kwargs["messages"]
            return make_structured_completion(speech="Understood.", location="Hogwarts corridor")

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-phase-test-value"})
    provider = CapturingProvider()
    http.app.state.chat_service._provider = provider

    created = http.post(
        "/api/chats",
        json={"character_id": "hermione-granger", "phase_id": "first-year-arrival", "tone_id": "canon"},
    )
    chat_id = created.json()["id"]
    response = http.post(f"/api/chats/{chat_id}/messages", json={"message": '"Hello."'})
    assert response.status_code == 200
    system_prompt = provider.messages[0]["content"]
    assert "First Year — New at Hogwarts" in system_prompt
    assert "Harry and Ron are classmates, not yet close friends" in system_prompt
    assert "Do not assume the troll friendship" in system_prompt


def test_every_builtin_timeline_phase_exposes_three_scenarios(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post("/api/characters/research", json={"query": ""})
    assert response.status_code == 200
    characters = response.json()["characters"]
    assert characters
    phase_count = 0
    for character in characters:
        for phase in character["phases"]:
            phase_count += 1
            assert len(phase["scenarios"]) == 3
            assert phase["default_scenario_id"] in {scene["id"] for scene in phase["scenarios"]}
            for scene in phase["scenarios"]:
                assert scene["what_happening"]
                assert scene["who_involved"]
                assert scene["dynamic"]
    assert phase_count == 128


def test_custom_scenario_is_frozen_in_chat(client) -> None:
    http, _ = client
    setup_owner(http)
    custom = {
        "name": "Wrong place, wrong time",
        "what_happening": "Ann unexpectedly falls into an unfamiliar cognitive world before Kamoshida's Palace operation.",
        "who_involved": "Ann and the user.",
        "dynamic": "Complete strangers forced to cooperate for immediate safety.",
    }
    created = http.post(
        "/api/chats",
        json={
            "character_id": "ann-takamaki",
            "phase_id": "pre-kamoshida",
            "scenario_id": "custom",
            "custom_scenario": custom,
            "tone_id": "intimate",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["scenario_id"] == "custom"
    assert body["scenario_name"] == custom["name"]

    detail = http.get(f"/api/chats/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["scenario"]["custom"] is True
    assert detail.json()["scenario"]["what_happening"] == custom["what_happening"]
    assert detail.json()["scenario"]["dynamic"] == custom["dynamic"]


def test_custom_future_scene_keeps_timeline_knowledge_ceiling_and_social_dynamic(client) -> None:
    from protean_workspace.clients.provider import CompletionResult

    class CapturingProvider:
        def __init__(self) -> None:
            self.messages = None

        async def complete(self, **kwargs):
            import re

            messages = kwargs["messages"]
            if "Protean Workspace visible-output gate" in messages[0]["content"]:
                match = re.search(r"PRIVATE DRAFT \(source material to filter\):\n([\s\S]*?)\n\nReturn only", messages[-1]["content"] )
                return CompletionResult(match.group(1).strip(), "stop")
            self.messages = messages
            return CompletionResult(
                '[[PROTEAN_DRAFT]]\n"Where are we?"\n[[/PROTEAN_DRAFT]]\n[[PROTEAN_REACTION:surprised]]',
                "stop",
            )

        async def complete_structured(self, **kwargs):
            self.messages = kwargs["messages"]
            return make_structured_completion(
                speech="Where are we?", reaction="surprised", location="an unfamiliar cognitive world"
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-scenario-test-value"})
    provider = CapturingProvider()
    http.app.state.chat_service._provider = provider

    created = http.post(
        "/api/chats",
        json={
            "character_id": "ann-takamaki",
            "phase_id": "pre-kamoshida",
            "tone_id": "intimate",
            "scenario_id": "custom",
            "custom_scenario": {
                "name": "Impossible Metaverse encounter",
                "what_happening": "Ann and the user suddenly land inside the Metaverse.",
                "who_involved": "Ann and the user only.",
                "dynamic": "They are complete strangers and neither trusts the other yet.",
            },
        },
    )
    assert created.status_code == 201
    response = http.post(f"/api/chats/{created.json()['id']}/messages", json={"message": '"What is this place?"'})
    assert response.status_code == 200
    prompt = provider.messages[0]["content"]
    assert "Scenario and tone can never override it" in prompt
    assert "pre-Kamoshida Ann" in prompt
    assert "does not automatically know the words Metaverse" in prompt
    assert "They are complete strangers" in prompt
    assert "Intimate tone with strangers" in prompt
    assert "Do not assume Shiho's suicide attempt" in prompt


def test_unknown_scenario_is_rejected_for_phase(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post(
        "/api/chats",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "future-war-council",
            "tone_id": "canon",
        },
    )
    assert response.status_code == 400
    assert "Scenario" in response.json()["detail"]


def test_opening_preview_changes_with_scenario_and_tone(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)

    first = http.post(
        "/api/chats/opening-preview",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    known = http.post(
        "/api/chats/opening-preview",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "known-acquaintance",
            "tone_id": "intimate",
        },
    )

    assert first.status_code == 200
    assert known.status_code == 200
    assert first.json()["message"] != known.json()["message"]
    assert "PROTEAN_REACTION" not in first.json()["message"]
    assert first.json()["opening_token"]
    assert first.json()["scenario_id"] == "first-encounter"
    assert known.json()["tone_id"] == "intimate"


def test_living_tom_uses_in_person_medium_but_diary_imprint_does_not(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)

    living = http.post(
        "/api/chats/opening-preview",
        json={
            "character_id": "tom-riddle",
            "phase_id": "fifth-year-chamber",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    diary = http.post(
        "/api/chats/opening-preview",
        json={
            "character_id": "tom-riddle",
            "phase_id": "diary-imprint",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )

    assert living.status_code == 200
    assert diary.status_code == 200
    assert living.json()["medium_type"] == "in-person conversation"
    assert "ink" not in living.json()["message"].lower()
    assert diary.json()["medium_type"] == "enchanted diary"
    assert "page" in diary.json()["message"].lower() or "ink" in diary.json()["message"].lower()
    assert "PROTEAN_REACTION" not in diary.json()["message"]


def test_custom_opening_preview_uses_custom_scene_text(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)
    payload = {
        "character_id": "ann-takamaki",
        "phase_id": "pre-kamoshida",
        "scenario_id": "custom",
        "tone_id": "canon",
        "custom_scenario": {
            "name": "Impossible arrival",
            "what_happening": "Ann and the user suddenly fall into an unfamiliar red castle.",
            "who_involved": "Ann and the user.",
            "dynamic": "They are complete strangers.",
        },
    }
    first = http.post("/api/chats/opening-preview", json=payload)
    payload["custom_scenario"]["what_happening"] = "Ann and the user are trapped alone in a stopped subway car."
    second = http.post("/api/chats/opening-preview", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert "red castle" in first.json()["message"]
    assert "stopped subway car" in second.json()["message"]
    assert first.json()["message"] != second.json()["message"]


def test_immersion_page_is_separate_subpage(client) -> None:
    http, _ = client
    response = http.get("/immersion")
    assert response.status_code == 200
    assert "Immersion · Protean Workspace" in response.text
    assert "/static/js/immersion.js" in response.text


def test_immersion_availability_only_exposes_ready_character_phases(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.get("/api/immersion/availability")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    available = {item["character_id"]: {phase["id"] for phase in item["phases"]} for item in body["characters"]}
    assert set(available) == {"tom-riddle", "hermione-granger"}
    assert available["tom-riddle"] == {"fifth-year-chamber", "diary-imprint", "sixth-year-horcrux"}
    assert available["hermione-granger"] == {"first-year-arrival", "first-year-post-troll", "fifth-year-da"}
    assert "ann-takamaki" not in available
    assert "misato-katsuragi" not in available


def test_immersion_rejects_character_without_ready_sprite_pack(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post(
        "/api/immersion/start",
        json={
            "character_id": "ann-takamaki",
            "phase_id": "pre-kamoshida",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert response.status_code == 409
    assert "incoming" in response.json()["detail"]


def test_diary_tom_immersion_is_diary_first_without_physical_sprite(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)
    response = http.post(
        "/api/immersion/start",
        json={
            "character_id": "tom-riddle",
            "phase_id": "diary-imprint",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["presentation"]["render_mode"] == "diary"
    assert body["presentation"]["sprite_path"] is None
    assert body["presentation"]["background_id"] == "bg-hp-diary-desk"
    detail = http.get(f'/api/chats/{body["chat"]["id"]}').json()
    assert detail["phase_id"] == "diary-imprint"
    assert detail["scenario_id"] == "first-encounter"


def test_hermione_immersion_starts_with_ready_sprite_and_background(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)
    response = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["presentation"]["render_mode"] == "sprite"
    assert body["presentation"]["sprite_pack_id"] == "hermione-year1"
    assert body["presentation"]["sprite_path"].endswith("hermione-year1-neutral.webp")
    assert body["presentation"]["background_id"] == "bg-hp-hogwarts-corridor-day"


def test_immersion_rejects_incoming_timeline_even_for_supported_character(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "third-year",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert response.status_code == 409


def test_immersion_reply_changes_sprite_expression_movement_and_scene(client) -> None:
    from protean_workspace.clients.provider import CompletionResult

    class ImmersionProvider:
        async def complete(self, **kwargs):
            import re

            messages = kwargs["messages"]
            if "Protean Workspace visible-output gate" in messages[0]["content"]:
                match = re.search(r"PRIVATE DRAFT \(source material to filter\):\n([\s\S]*?)\n\nReturn only", messages[-1]["content"] )
                return CompletionResult(match.group(1).strip(), "stop")
            return CompletionResult(
                '[[PROTEAN_DRAFT]]\n**Hermione smiles, steps closer, and enters the library.**\n\n"We can talk here."\n[[/PROTEAN_DRAFT]]\n[[PROTEAN_REACTION:positive]]',
                "stop",
            )

        async def complete_structured(self, **kwargs):
            joined = "\n".join(item["content"] for item in kwargs["messages"])
            if "Generate the first assistant message" in joined:
                return make_structured_completion(location="Hogwarts corridor")
            return make_structured_completion(
                action="Hermione smiles, steps closer, and enters the library.",
                speech="We can talk here.",
                reaction="positive",
                location="Hogwarts library",
                changed=True,
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-immersion-test-value"})
    http.app.state.chat_service._provider = ImmersionProvider()

    started = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    ).json()
    chat_id = started["chat"]["id"]
    response = http.post(
        f"/api/immersion/{chat_id}/messages",
        json={
            "message": '**We walk into the library.** "Maybe it is quieter here."',
            "current_background_id": started["presentation"]["background_id"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["presentation"]["expression"] == "positive"
    assert body["presentation"]["movement"] == "approach"
    assert body["presentation"]["background_id"] == "bg-hp-hogwarts-library"
    assert body["presentation"]["sprite_path"].endswith("hermione-year1-positive.webp")


def test_immersion_initial_background_uses_location_not_incidental_canon_mentions(client) -> None:
    http, _ = client
    setup_owner(http)
    configure_generated_openings(http)
    normal = http.post(
        "/api/immersion/start",
        json={
            "character_id": "tom-riddle",
            "phase_id": "fifth-year-chamber",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert normal.status_code == 201
    assert normal.json()["presentation"]["background_id"] == "bg-hp-hogwarts-corridor-1940s"

    alternate = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "custom",
            "custom_scenario": {
                "name": "Impossible chamber",
                "what_happening": "The scene opens inside the Chamber of Secrets, a place Hermione has never encountered or learned about.",
                "who_involved": "Hermione and the user.",
                "dynamic": "They are strangers forced to understand an unfamiliar location together.",
            },
            "tone_id": "canon",
        },
    )
    assert alternate.status_code == 201
    assert alternate.json()["presentation"]["background_id"] == "bg-hp-chamber-of-secrets"


def test_opening_preview_requires_key_and_generated_preview_is_persisted(client) -> None:
    http, _ = client
    setup_owner(http)
    payload = {
        "character_id": "hermione-granger",
        "phase_id": "first-year-arrival",
        "scenario_id": "first-encounter",
        "tone_id": "canon",
    }

    missing = http.post("/api/chats/opening-preview", json=payload)
    assert missing.status_code == 409
    assert "re-click the character" in missing.json()["detail"]

    configure_generated_openings(http)
    preview = http.post("/api/chats/opening-preview", json=payload)
    assert preview.status_code == 200
    visible = preview.json()["message"]
    assert "PROTEAN_REACTION" not in visible

    created = http.post(
        "/api/chats",
        json={**payload, "opening_token": preview.json()["opening_token"]},
    )
    assert created.status_code == 201
    detail = http.get(f'/api/chats/{created.json()["id"]}').json()
    assert detail["messages"][0]["content"] == visible


def test_hidden_model_reaction_is_stripped_and_drives_immersion_sprite(client) -> None:
    from protean_workspace.clients.provider import CompletionResult

    class ReactionProvider:
        async def complete(self, **kwargs):
            last = kwargs["messages"][-1]["content"]
            if "Generate the first assistant message" in last:
                return CompletionResult(
                    '**Hermione looks up from her book.**\n\n"Hello."\n\n[[PROTEAN_REACTION:neutral]]',
                    "stop",
                )
            return CompletionResult(
                '**Hermione keeps perfectly still.**\n\n"I did not expect that."\n\n[[PROTEAN_REACTION:surprised]]',
                "stop",
            )

        async def complete_structured(self, **kwargs):
            joined = "\n".join(item["content"] for item in kwargs["messages"])
            if "Generate the first assistant message" in joined:
                return make_structured_completion(
                    action="Hermione looks up from her book.", speech="Hello.", location="Hogwarts corridor"
                )
            return make_structured_completion(
                action="Hermione keeps perfectly still.",
                speech="I did not expect that.",
                reaction="surprised",
                location="Hogwarts corridor",
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-reaction-test"})
    http.app.state.chat_service._provider = ReactionProvider()

    started = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    ).json()
    response = http.post(
        f'/api/immersion/{started["chat"]["id"]}/messages',
        json={"message": '"Boo."', "current_background_id": started["presentation"]["background_id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["presentation"]["expression"] == "surprised"
    assert body["presentation"]["sprite_path"].endswith("hermione-year1-surprised.webp")
    assert "PROTEAN_REACTION" not in body["reply"]

    detail = http.get(f'/api/chats/{started["chat"]["id"]}').json()
    assert all("PROTEAN_REACTION" not in item["content"] for item in detail["messages"])


def test_immersion_transcript_segments_are_block_spaced(client) -> None:
    http, _ = client
    css = http.get("/static/css/immersion.css")
    assert css.status_code == 200
    segment = css.text.split(".transcript-segment {", 1)[1].split("}", 1)[0]
    assert "display: block" in segment
    assert "margin: 0 0 .62em" in segment


def test_empty_structured_completion_is_retried_once(client) -> None:
    from protean_workspace.clients.provider import EmptyCompletionError

    class EmptyThenValidProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_structured(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise EmptyCompletionError("empty")
            return make_structured_completion(
                action="Hermione raises an eyebrow.",
                speech="Second try.",
                reaction="amused",
                location="Hogwarts corridor",
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-empty-retry-test"})
    provider = EmptyThenValidProvider()
    http.app.state.chat_service._provider = provider
    created = http.post(
        "/api/chats",
        json={"character_id": "hermione-granger", "phase_id": "first-year-arrival", "tone_id": "canon"},
    )
    response = http.post(f'/api/chats/{created.json()["id"]}/messages', json={"message": '"Hello."'})
    assert response.status_code == 200
    assert provider.calls == 2
    assert response.json()["reply"] == '**Hermione raises an eyebrow.**\n\n"Second try."'

def test_structured_renderer_never_exposes_provider_metadata_fields(client) -> None:
    class StructuredProvider:
        async def complete_structured(self, **kwargs):
            return make_structured_completion(
                action="Hermione blinks once.",
                speech="That was unexpected.",
                reaction="surprised",
                location="Hogwarts corridor",
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-structured-test"})
    http.app.state.chat_service._provider = StructuredProvider()
    created = http.post(
        "/api/chats",
        json={"character_id": "hermione-granger", "phase_id": "first-year-arrival", "tone_id": "canon"},
    )
    response = http.post(f'/api/chats/{created.json()["id"]}/messages', json={"message": '"Boo."'})
    assert response.status_code == 200
    assert response.json()["reply"] == '**Hermione blinks once.**\n\n"That was unexpected."'

def test_immersion_location_is_explicit_scene_state_not_transcript_guessing(client) -> None:
    class LocationProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_structured(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return make_structured_completion(
                    action="Moonlight catches Hermione's hair.",
                    speech="It is quiet out here.",
                    reaction="thinking",
                    location="Hogwarts grounds beneath the moonlight",
                    changed=False,
                )
            return make_structured_completion(
                action="Hermione mentions the library but stays where she is.",
                speech="I left the book in the library.",
                reaction="neutral",
                location="Hogwarts grounds beneath the moonlight",
                changed=False,
            )

        async def validate_key(self, api_key: str):
            return {}

    http, _ = client
    setup_owner(http)
    http.put("/api/settings/provider", json={"api_key": "sk-or-v1-location-test"})
    http.app.state.chat_service._provider = LocationProvider()
    started = http.post(
        "/api/immersion/start",
        json={
            "character_id": "hermione-granger",
            "phase_id": "first-year-arrival",
            "scenario_id": "first-encounter",
            "tone_id": "canon",
        },
    )
    assert started.status_code == 201
    body = started.json()
    assert body["presentation"]["location"] == "Hogwarts grounds beneath the moonlight"
    # No matching outdoor asset exists yet, so use the neutral fallback rather than lying with a library/corridor.
    assert body["presentation"]["background_id"] == "bg-protean-default"
    reply = http.post(
        f'/api/immersion/{body["chat"]["id"]}/messages',
        json={
            "message": '"What about the library?"',
            "current_background_id": body["presentation"]["background_id"],
            "current_location": body["presentation"]["location"],
        },
    )
    assert reply.status_code == 200
    assert reply.json()["presentation"]["location_changed"] is False
    assert reply.json()["presentation"]["background_id"] == "bg-protean-default"



def test_content_expansion_roster_and_sherlock_removal(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post("/api/characters/research", json={"query": ""})
    assert response.status_code == 200
    characters = response.json()["characters"]
    ids = {character["id"] for character in characters}
    assert len(ids) == 40
    assert "sherlock-holmes" not in ids
    for expected in {
        "harry-potter", "ron-weasley", "ginny-weasley", "draco-malfoy", "luna-lovegood",
        "neville-longbottom", "severus-snape", "shinji-ikari", "rei-ayanami",
        "asuka-langley-soryu", "kaworu-nagisa", "ritsuko-akagi", "tanjiro-kamado",
        "nezuko-kamado", "zenitsu-agatsuma", "inosuke-hashibira", "giyu-tomioka",
        "shinobu-kocho", "kyojuro-rengoku", "tengen-uzui", "mitsuri-kanroji",
        "muichiro-tokito", "ren-amamiya", "ryuji-sakamoto", "morgana", "yusuke-kitagawa",
        "futaba-sakura", "haru-okumura", "goro-akechi", "sumire-yoshizawa",
        "gon-freecss", "killua-zoldyck", "kurapika", "leorio-paradinight",
    }:
        assert expected in ids


def test_dynamic_scenario_hooks_include_forbidden_spell_and_polyjuice(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.post("/api/characters/research", json={"query": ""})
    assert response.status_code == 200
    by_id = {character["id"]: character for character in response.json()["characters"]}
    tom = by_id["tom-riddle"]
    chamber = next(phase for phase in tom["phases"] if phase["id"] == "fifth-year-chamber")
    assert "forbidden spell" in chamber["scenarios"][0]["what_happening"].lower()
    hermione = by_id["hermione-granger"]
    polyjuice = next(phase for phase in hermione["phases"] if phase["id"] == "second-year-polyjuice")
    assert "polyjuice" in polyjuice["scenarios"][0]["what_happening"].lower()
    assert "bathroom" in polyjuice["scenarios"][0]["what_happening"].lower()


def test_new_tone_presets_are_available(client) -> None:
    http, _ = client
    setup_owner(http)
    response = http.get("/api/ui/presets")
    assert response.status_code == 200
    ids = {tone["id"] for tone in response.json()["tones"]}
    assert {"tense", "vulnerable", "rivalry", "melancholic", "confrontational"} <= ids
