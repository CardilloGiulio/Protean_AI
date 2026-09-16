import json

import pytest

from protean_workspace.clients.openrouter import OpenRouterClient
from protean_workspace.clients.provider import EmptyCompletionError
from protean_workspace.core.structured_reply import (
    ROLEPLAY_RESPONSE_SCHEMA,
    parse_structured_roleplay,
)


def test_openrouter_does_not_fall_back_to_reasoning_when_visible_content_is_empty() -> None:
    with pytest.raises(EmptyCompletionError):
        OpenRouterClient._extract_completion(
            {
                "choices": [
                    {
                        "message": {"content": "", "reasoning": "private reasoning must not be surfaced"},
                        "finish_reason": "stop",
                    }
                ]
            }
        )


def test_openrouter_accepts_visible_text_content_blocks() -> None:
    result = OpenRouterClient._extract_completion(
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"reaction":"neutral",'},
                            {"type": "text", "text": '"location":{"label":"hall","changed":false},"beats":[{"type":"speech","text":"Yes."}]}'},
                        ]
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    )
    assert result.content.startswith('{"reaction":"neutral"')


def test_structured_reply_renders_protean_syntax_locally() -> None:
    reply = parse_structured_roleplay(
        json.dumps(
            {
                "reaction": "amused",
                "location": {"label": "Hogwarts grounds beneath the moonlight", "changed": False},
                "beats": [
                    {"type": "action", "text": "Hermione raises an eyebrow."},
                    {"type": "speech", "text": "That is your explanation?"},
                    {"type": "dev", "text": "A visible OOC note."},
                ],
            }
        )
    )
    assert reply.reaction == "amused"
    assert reply.location == "Hogwarts grounds beneath the moonlight"
    assert reply.location_changed is False
    assert reply.render() == (
        '**Hermione raises an eyebrow.**\n\n'
        '"That is your explanation?"\n\n'
        '(A visible OOC note.)'
    )


def test_structured_reply_rejects_non_json_and_invalid_reaction() -> None:
    with pytest.raises(ValueError):
        parse_structured_roleplay("User Safety: Safe")
    with pytest.raises(ValueError):
        parse_structured_roleplay(
            json.dumps(
                {
                    "reaction": "furious",
                    "location": {"label": "hall", "changed": False},
                    "beats": [{"type": "speech", "text": "No."}],
                }
            )
        )


def test_schema_requires_reaction_location_and_beats() -> None:
    schema = ROLEPLAY_RESPONSE_SCHEMA["json_schema"]["schema"]
    assert set(schema["required"]) == {"reaction", "location", "beats"}
    assert schema["properties"]["location"]["required"] == ["label", "changed"]



def _structured_success_payload(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ]
    }


def test_openrouter_structured_falls_back_to_json_object_and_caches_mode(tmp_path) -> None:
    import asyncio
    import httpx

    from protean_workspace.core.config import Settings

    calls: list[dict] = []
    valid = json.dumps(
        {
            "reaction": "neutral",
            "location": {"label": "Hogwarts corridor", "changed": False},
            "beats": [{"type": "speech", "text": "Hello."}],
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        calls.append(payload)
        response_format = payload.get("response_format")
        if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
            return httpx.Response(
                400,
                request=request,
                json={"error": {"message": "No endpoints found that can handle the requested parameters."}},
            )
        return httpx.Response(200, request=request, json=_structured_success_payload(valid))

    async def run() -> None:
        settings = Settings(instance_dir=tmp_path / "instance", _env_file=None)
        client = OpenRouterClient(settings)
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="https://openrouter.test/api/v1",
            transport=httpx.MockTransport(handler),
        )
        try:
            first = await client.complete_structured(
                api_key="sk-test",
                model="openrouter/free",
                messages=[{"role": "system", "content": "Return JSON."}],
                temperature=0.5,
                max_tokens=256,
                response_format=ROLEPLAY_RESPONSE_SCHEMA,
            )
            assert parse_structured_roleplay(first.content).location == "Hogwarts corridor"
            assert client.structured_mode_for_model("openrouter/free") == "json_object"

            second = await client.complete_structured(
                api_key="sk-test",
                model="openrouter/free",
                messages=[{"role": "system", "content": "Return JSON."}],
                temperature=0.5,
                max_tokens=256,
                response_format=ROLEPLAY_RESPONSE_SCHEMA,
            )
            assert parse_structured_roleplay(second.content).reaction == "neutral"
        finally:
            await client.close()

    asyncio.run(run())
    assert [call.get("response_format", {}).get("type") for call in calls] == [
        "json_schema",
        "json_object",
        "json_object",
    ]
    assert calls[0]["provider"] == {"require_parameters": True}
    assert "provider" not in calls[1]


def test_openrouter_structured_can_degrade_to_plain_json(tmp_path) -> None:
    import asyncio
    import httpx

    from protean_workspace.core.config import Settings

    calls: list[dict] = []
    valid = json.dumps(
        {
            "reaction": "thinking",
            "location": {"label": "the current room", "changed": False},
            "beats": [{"type": "action", "text": "The character pauses."}],
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        calls.append(payload)
        if "response_format" in payload:
            return httpx.Response(
                400,
                request=request,
                json={"error": {"message": "No endpoints found that can handle the requested parameters."}},
            )
        return httpx.Response(200, request=request, json=_structured_success_payload(valid))

    async def run() -> None:
        settings = Settings(instance_dir=tmp_path / "instance", _env_file=None)
        client = OpenRouterClient(settings)
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="https://openrouter.test/api/v1",
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await client.complete_structured(
                api_key="sk-test",
                model="openrouter/free",
                messages=[{"role": "system", "content": "Return JSON."}],
                temperature=0.5,
                max_tokens=256,
                response_format=ROLEPLAY_RESPONSE_SCHEMA,
            )
            assert parse_structured_roleplay(result.content).reaction == "thinking"
            assert client.structured_mode_for_model("openrouter/free") == "plain_json"
        finally:
            await client.close()

    asyncio.run(run())
    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[1]["response_format"]["type"] == "json_object"
    assert "response_format" not in calls[2]


def test_openrouter_does_not_hide_unrelated_structured_errors(tmp_path) -> None:
    import asyncio
    import httpx

    from protean_workspace.clients.openrouter import OpenRouterError
    from protean_workspace.core.config import Settings

    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            request=request,
            json={"error": {"message": "Invalid API key"}},
        )

    async def run() -> None:
        settings = Settings(instance_dir=tmp_path / "instance", _env_file=None)
        client = OpenRouterClient(settings)
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="https://openrouter.test/api/v1",
            transport=httpx.MockTransport(handler),
        )
        try:
            with pytest.raises(OpenRouterError, match=r"authentication failed \(HTTP 401\)"):
                await client.complete_structured(
                    api_key="bad",
                    model="openrouter/free",
                    messages=[{"role": "system", "content": "Return JSON."}],
                    temperature=0.5,
                    max_tokens=256,
                    response_format=ROLEPLAY_RESPONSE_SCHEMA,
                )
        finally:
            await client.close()

    asyncio.run(run())
    assert calls == 1


def test_structured_reply_normalizes_harmless_json_only_variants() -> None:
    reply = parse_structured_roleplay(
        'Here is the JSON you requested:\n' + json.dumps(
            {
                "reaction": "startled",
                "location": "Hogwarts grounds beneath the moonlight",
                "beats": [
                    {"kind": "narration", "content": "Hermione looks up sharply."},
                    {"type": "dialogue", "text": "Did you hear that?"},
                ],
            }
        )
    )
    assert reply.reaction == "surprised"
    assert reply.location == "Hogwarts grounds beneath the moonlight"
    assert reply.location_changed is False
    assert reply.render() == '**Hermione looks up sharply.**\n\n"Did you hear that?"'


def test_structured_reply_accepts_missing_changed_and_common_object_wrapper() -> None:
    reply = parse_structured_roleplay(
        json.dumps(
            {
                "response": {
                    "reaction": "thoughtful",
                    "location": {"name": "Hogwarts Library"},
                    "action": "**Hermione traces a line on the page.**",
                    "speech": '"This part matters."',
                }
            }
        )
    )
    assert reply.reaction == "thinking"
    assert reply.location == "Hogwarts Library"
    assert reply.location_changed is False
    assert reply.render() == '**Hermione traces a line on the page.**\n\n"This part matters."'


def test_structured_reply_accepts_preformatted_beat_strings_but_not_plain_prose() -> None:
    reply = parse_structured_roleplay(
        json.dumps(
            {
                "reaction": "neutral",
                "location": {"label": "corridor", "changed": "false"},
                "beats": ["**Tom closes the book.**", '"Continue."'],
            }
        )
    )
    assert reply.location_changed is False
    assert reply.render() == '**Tom closes the book.**\n\n"Continue."'

    with pytest.raises(ValueError):
        parse_structured_roleplay(
            json.dumps(
                {
                    "reaction": "neutral",
                    "location": "corridor",
                    "beats": ["Tom closes the book."],
                }
            )
        )
