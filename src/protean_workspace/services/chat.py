from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from weakref import WeakValueDictionary

from protean_workspace.clients.provider import (
    ChatProvider,
    EmptyCompletionError,
    LengthCutoffError,
    ProviderError,
)
from protean_workspace.core.config import Settings
from protean_workspace.core.generation import STRUCTURED_OUTPUT_INSTRUCTION
from protean_workspace.core.openings import build_opening_message
from protean_workspace.core.prompts import build_system_prompt
from protean_workspace.core.structured_reply import ROLEPLAY_RESPONSE_SCHEMA, parse_structured_roleplay
from protean_workspace.db.repositories import ChatRepository, PreferencesRepository
from protean_workspace.models.domain import CharacterPhase, CharacterScenario
from protean_workspace.services.characters import CharacterLibrary
from protean_workspace.services.context import ContextRepository
from protean_workspace.services.credentials import CredentialService
from protean_workspace.services.presets import get_tone

logger = logging.getLogger(__name__)


class ChatServiceError(RuntimeError):
    pass


class ChatRequestConflictError(ChatServiceError):
    pass


class ProviderNotConfiguredError(ChatServiceError):
    pass


class CharacterNotFoundError(ChatServiceError):
    pass


class CharacterPhaseNotFoundError(ChatServiceError):
    pass


class CharacterScenarioNotFoundError(ChatServiceError):
    pass


class ChatService:
    """Authoritative chat/prompt service.

    Opening previews are provider-generated and cached briefly behind an opaque token.
    The browser can display the preview and return the token, but cannot author the
    opening that is persisted into history.
    """

    _OPENING_PREVIEW_TTL_SECONDS = 15 * 60
    _OPENING_PREVIEW_LIMIT = 128

    def __init__(
        self,
        *,
        settings: Settings,
        chats: ChatRepository,
        preferences: PreferencesRepository,
        credentials: CredentialService,
        characters: CharacterLibrary,
        context: ContextRepository,
        provider: ChatProvider,
    ) -> None:
        self._settings = settings
        self._chats = chats
        self._preferences = preferences
        self._credentials = credentials
        self._characters = characters
        self._context = context
        self._provider = provider
        self._opening_previews: dict[str, dict[str, object]] = {}
        self._turn_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    def create_chat(
        self,
        user_id: int,
        *,
        character_id: str | None,
        phase_id: str | None,
        scenario_id: str | None,
        custom_scenario: dict[str, str] | None,
        tone_id: str | None,
        title: str | None,
        opening_token: str | None = None,
    ):
        prefs = self._preferences.get(user_id)
        chosen_character = character_id or prefs.active_character_id
        chosen_tone = tone_id or prefs.tone_id
        card = self._characters.get(prefs.library_root, chosen_character)
        if card is None:
            raise CharacterNotFoundError(
                f"Character '{chosen_character}' was not found in the configured library"
            )
        if phase_id is not None:
            requested_phase = phase_id
        elif chosen_character == prefs.active_character_id:
            requested_phase = prefs.active_phase_id
        else:
            requested_phase = card.default_phase_id
        phase = card.phase(requested_phase)
        if requested_phase and requested_phase != phase.id and card.phases:
            raise CharacterPhaseNotFoundError(
                f"Timeline phase '{requested_phase}' is not available for {card.name}"
            )
        scenario = self._resolve_scenario(
            character_name=card.name,
            phase=phase,
            scenario_id=scenario_id,
            custom_scenario=custom_scenario,
        )
        tone = get_tone(chosen_tone)

        preview = self._consume_opening_preview(
            user_id=user_id,
            token=opening_token,
            character_id=card.id,
            phase_id=phase.id,
            scenario=scenario,
            tone_id=tone.id,
        )
        # Compatibility fallback for direct API/test clients that do not use the UI preview flow.
        # Protean's normal UI and Immersion route always provide a provider-generated preview token.
        opening = str(preview.get("message") or "") if preview else build_opening_message(
            character=card,
            phase=phase,
            scenario=scenario,
            tone=tone,
        )

        chat_title = (title or f"{card.name} — {phase.name} · {scenario.name}").strip()[:160] or card.name
        created = self._chats.create(
            user_id,
            chat_title,
            card.id,
            phase.id,
            scenario.id,
            self._scenario_snapshot(scenario),
            tone.id,
        )
        if opening:
            self._chats.add_message(user_id, str(created["id"]), "assistant", opening)
        return created

    async def preview_opening(
        self,
        user_id: int,
        *,
        character_id: str | None,
        phase_id: str | None,
        scenario_id: str | None,
        custom_scenario: dict[str, str] | None,
        tone_id: str | None,
    ) -> dict[str, str]:
        prefs = self._preferences.get(user_id)
        chosen_character = character_id or prefs.active_character_id
        chosen_tone = tone_id or prefs.tone_id
        card = self._characters.get(prefs.library_root, chosen_character)
        if card is None:
            raise CharacterNotFoundError(
                f"Character '{chosen_character}' was not found in the configured library"
            )
        requested_phase = phase_id or (
            prefs.active_phase_id if chosen_character == prefs.active_character_id else card.default_phase_id
        )
        phase = card.phase(requested_phase)
        if requested_phase and requested_phase != phase.id and card.phases:
            raise CharacterPhaseNotFoundError(
                f"Timeline phase '{requested_phase}' is not available for {card.name}"
            )
        scenario = self._resolve_scenario(
            character_name=card.name,
            phase=phase,
            scenario_id=scenario_id,
            custom_scenario=custom_scenario,
        )
        tone = get_tone(chosen_tone)
        api_key = self._credentials.get(user_id, "openrouter")
        if not api_key:
            raise ProviderNotConfiguredError(
                "Add your OpenRouter API key first, then re-click the character to generate a new opening"
            )

        system_prompt = build_system_prompt(
            character=card,
            phase=phase,
            scenario=scenario,
            tone=tone,
            context="",
            target_tokens=min(prefs.target_tokens, 420),
        )
        seed = (scenario.first_message or phase.first_message or card.first_message).strip()
        opening_instruction = (
            "Generate the first assistant message for this exact scene now. The user has not spoken yet. "
            "Begin inside the selected timeline, scenario, relationship dynamic, tone, and medium. Do not ask setup "
            "questions and do not mention that you are generating an opener. Return only the structured roleplay object "
            "required by the response schema, including one dominant reaction and the concrete physical scene location."
        )
        if seed:
            opening_instruction += (
                " Treat this existing character-card opening only as inspiration; rewrite it so it fits the selected "
                f"state rather than copying it mechanically: {seed!r}."
            )
        provider_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": opening_instruction},
        ]
        try:
            message, reaction, location, location_changed = await self._generate_controlled_reply(
                api_key=api_key,
                model=prefs.provider_model,
                provider_messages=provider_messages,
                user_message="",
                temperature=prefs.temperature,
                target_tokens=min(prefs.target_tokens, 420),
                hard_max_tokens=min(prefs.max_tokens, max(320, min(640, prefs.target_tokens + 128))),
                stage_name="opening",
            )
        except ProviderError as exc:
            logger.warning("Provider opening generation failed: %s", exc)
            raise ChatServiceError(str(exc)) from exc
        token = self._store_opening_preview(
            user_id=user_id,
            character_id=card.id,
            phase_id=phase.id,
            scenario=scenario,
            tone_id=tone.id,
            message=message,
            reaction=reaction or "neutral",
            location=location,
            location_changed=location_changed,
        )
        return {
            "message": message,
            "opening_token": token,
            "character_id": card.id,
            "phase_id": phase.id,
            "scenario_id": scenario.id,
            "tone_id": tone.id,
            "medium_type": phase.medium_type or card.medium_type or "chat",
            "location": location,
            "location_changed": location_changed,
        }

    def list_chats(self, user_id: int):
        return self._chats.list_chats(user_id)

    def get_chat(self, user_id: int, chat_id: str):
        summary = self._chats.get_summary(user_id, chat_id)
        return {**summary, "messages": self._chats.get_messages(user_id, chat_id)}

    async def send_message(
        self,
        user_id: int,
        chat_id: str,
        message: str,
        *,
        request_id: str,
        current_location: str | None = None,
    ) -> dict[str, object]:
        lock = self._turn_locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            return await self._send_message_locked(
                user_id,
                chat_id,
                message,
                request_id=request_id,
                current_location=current_location,
            )

    async def _send_message_locked(
        self,
        user_id: int,
        chat_id: str,
        message: str,
        *,
        request_id: str,
        current_location: str | None,
    ) -> dict[str, object]:
        text = message.strip()
        if not text:
            raise ChatServiceError("Message cannot be blank")

        prefs = self._preferences.get(user_id)
        summary = self._chats.get_summary(user_id, chat_id)
        existing = self._chats.get_turn(user_id, chat_id, request_id)
        if existing is not None:
            if existing["request_message"] != text:
                raise ChatRequestConflictError("request_id was already used for a different message")
            return {
                "chat_id": chat_id,
                "request_id": existing["request_id"],
                "reply": existing["reply"],
                "reaction": existing["reaction"],
                "location": existing["location"],
                "location_changed": existing["location_changed"],
                "character_id": str(summary["character_id"]),
                "phase_id": str(summary.get("phase_id") or ""),
                "scenario_id": str(summary.get("scenario_id") or ""),
                "tone_id": str(summary["tone_id"]),
            }
        character = self._characters.get(prefs.library_root, str(summary["character_id"]))
        if character is None:
            raise CharacterNotFoundError("The chat's character is no longer available in the library")

        stored_phase_id = str(summary.get("phase_id") or "")
        phase = character.phase(stored_phase_id)
        if stored_phase_id and stored_phase_id != phase.id and character.phases:
            raise CharacterPhaseNotFoundError(
                f"This chat uses timeline phase '{stored_phase_id}', which is no longer available"
            )

        scenario = self._scenario_from_summary(summary)
        if scenario is None:
            scenario = self._resolve_scenario(
                character_name=character.name,
                phase=phase,
                scenario_id=None,
                custom_scenario=None,
            )

        api_key = self._credentials.get(user_id, "openrouter")
        if not api_key:
            raise ProviderNotConfiguredError("Add your OpenRouter API key in Connection settings first")

        tone = get_tone(str(summary["tone_id"]))
        context = self._context.build_context(text)
        system_prompt = build_system_prompt(
            character=character,
            phase=phase,
            scenario=scenario,
            tone=tone,
            context=context,
            target_tokens=prefs.target_tokens,
            current_location=current_location,
        )
        history = self._chats.get_messages(
            user_id,
            chat_id,
            limit=self._settings.max_chat_history_messages,
        )
        provider_messages = [{"role": "system", "content": system_prompt}]
        provider_messages.extend(
            {"role": str(item["role"]), "content": str(item["content"])} for item in history
        )
        provider_messages.append({"role": "user", "content": text})

        try:
            reply, reaction, location, location_changed = await self._generate_controlled_reply(
                api_key=api_key,
                model=prefs.provider_model,
                provider_messages=provider_messages,
                user_message=text,
                temperature=prefs.temperature,
                target_tokens=prefs.target_tokens,
                hard_max_tokens=prefs.max_tokens,
                stage_name="reply",
            )
        except ProviderError as exc:
            logger.warning("Provider completion failed: %s", exc)
            raise ChatServiceError(str(exc)) from exc

        persisted = self._chats.commit_turn(
            user_id,
            chat_id,
            request_id,
            text,
            reply,
            reaction=reaction or "",
            location=location,
            location_changed=location_changed,
        )
        return {
            "chat_id": chat_id,
            "request_id": persisted["request_id"],
            "reply": persisted["reply"],
            "reaction": persisted["reaction"],
            "location": persisted["location"],
            "location_changed": persisted["location_changed"],
            "character_id": character.id,
            "phase_id": phase.id,
            "scenario_id": scenario.id,
            "tone_id": tone.id,
        }

    def set_scene_location(self, user_id: int, chat_id: str, location: str) -> None:
        self._chats.set_scene_location(user_id, chat_id, location)

    def get_scene_location(self, user_id: int, chat_id: str) -> str | None:
        return self._chats.get_scene_location(user_id, chat_id)

    def opening_reaction(self, token: str | None) -> str | None:
        if not token:
            return None
        self._prune_opening_previews()
        item = self._opening_previews.get(token)
        if not item:
            return None
        reaction = str(item.get("reaction") or "").strip().lower()
        return reaction or None

    def opening_scene_state(self, token: str | None) -> tuple[str | None, bool]:
        if not token:
            return None, False
        self._prune_opening_previews()
        item = self._opening_previews.get(token)
        if not item:
            return None, False
        location = str(item.get("location") or "").strip() or None
        return location, bool(item.get("location_changed"))

    def _store_opening_preview(
        self,
        *,
        user_id: int,
        character_id: str,
        phase_id: str,
        scenario: CharacterScenario,
        tone_id: str,
        message: str,
        reaction: str,
        location: str,
        location_changed: bool,
    ) -> str:
        self._prune_opening_previews()
        while len(self._opening_previews) >= self._OPENING_PREVIEW_LIMIT:
            self._opening_previews.pop(next(iter(self._opening_previews)))
        token = secrets.token_urlsafe(24)
        self._opening_previews[token] = {
            "expires_at": time.monotonic() + self._OPENING_PREVIEW_TTL_SECONDS,
            "user_id": user_id,
            "character_id": character_id,
            "phase_id": phase_id,
            "scenario": self._scenario_fingerprint(scenario),
            "tone_id": tone_id,
            "message": message,
            "reaction": reaction,
            "location": location,
            "location_changed": location_changed,
        }
        return token

    def _consume_opening_preview(
        self,
        *,
        user_id: int,
        token: str | None,
        character_id: str,
        phase_id: str,
        scenario: CharacterScenario,
        tone_id: str,
    ) -> dict[str, object] | None:
        if not token:
            return None
        self._prune_opening_previews()
        item = self._opening_previews.get(token)
        if item is None:
            raise ChatServiceError("Opening preview expired; re-select the character to generate a fresh opening")
        expected = (
            user_id,
            character_id,
            phase_id,
            self._scenario_fingerprint(scenario),
            tone_id,
        )
        actual = (
            int(item.get("user_id") or 0),
            str(item.get("character_id") or ""),
            str(item.get("phase_id") or ""),
            str(item.get("scenario") or ""),
            str(item.get("tone_id") or ""),
        )
        if actual != expected:
            raise ChatServiceError("Opening preview no longer matches the selected timeline, scenario, or tone")
        return self._opening_previews.pop(token)

    def _prune_opening_previews(self) -> None:
        now = time.monotonic()
        expired = [token for token, item in self._opening_previews.items() if float(item.get("expires_at") or 0) <= now]
        for token in expired:
            self._opening_previews.pop(token, None)

    @classmethod
    def _scenario_fingerprint(cls, scenario: CharacterScenario) -> str:
        return json.dumps(cls._scenario_snapshot(scenario), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _scenario_snapshot(scenario: CharacterScenario) -> dict[str, object]:
        return {
            "id": scenario.id,
            "name": scenario.name,
            "what_happening": scenario.what_happening,
            "who_involved": scenario.who_involved,
            "dynamic": scenario.dynamic,
            "first_message": scenario.first_message,
            "custom": scenario.custom,
        }

    @staticmethod
    def _scenario_from_summary(summary: dict[str, object]) -> CharacterScenario | None:
        raw = summary.get("scenario")
        if not isinstance(raw, dict):
            return None
        required = ("what_happening", "who_involved", "dynamic")
        if not all(str(raw.get(key) or "").strip() for key in required):
            return None
        return CharacterScenario(
            id=str(raw.get("id") or summary.get("scenario_id") or "open-scene").strip(),
            name=str(raw.get("name") or "Open scene").strip(),
            what_happening=str(raw.get("what_happening") or "").strip(),
            who_involved=str(raw.get("who_involved") or "").strip(),
            dynamic=str(raw.get("dynamic") or "").strip(),
            first_message=str(raw.get("first_message") or "").strip(),
            custom=bool(raw.get("custom")),
        )

    @staticmethod
    def _resolve_scenario(
        *,
        character_name: str,
        phase: CharacterPhase,
        scenario_id: str | None,
        custom_scenario: dict[str, str] | None,
    ) -> CharacterScenario:
        if custom_scenario is not None:
            values = {
                key: str(custom_scenario.get(key) or "").strip()
                for key in ("name", "what_happening", "who_involved", "dynamic")
            }
            if not values["what_happening"] or not values["who_involved"] or not values["dynamic"]:
                raise CharacterScenarioNotFoundError(
                    "A custom scenario needs what is happening, who is involved, and the character-user dynamic"
                )
            return CharacterScenario(
                id="custom",
                name=values["name"] or "Custom scene",
                what_happening=values["what_happening"],
                who_involved=values["who_involved"],
                dynamic=values["dynamic"],
                custom=True,
            )

        requested = (scenario_id or "").strip()
        scene = phase.scene(requested)
        if requested and scene is None:
            raise CharacterScenarioNotFoundError(
                f"Scenario '{requested}' is not available in timeline phase '{phase.name}'"
            )
        if requested and scene is not None and scene.id != requested:
            raise CharacterScenarioNotFoundError(
                f"Scenario '{requested}' is not available in timeline phase '{phase.name}'"
            )
        if scene is not None:
            return scene

        return CharacterScenario(
            id="open-scene",
            name="Open scene",
            what_happening=phase.scenario or f"A roleplay scene during {phase.name}.",
            who_involved=f"{character_name} and the user; no additional participant is assumed.",
            dynamic=(
                "No special relationship is assumed. Familiarity, trust, conflict, or intimacy must be "
                "established by the user or developed naturally in the conversation."
            ),
        )

    async def _generate_controlled_reply(
        self,
        *,
        api_key: str,
        model: str,
        provider_messages: list[dict[str, str]],
        user_message: str,
        temperature: float,
        target_tokens: int,
        hard_max_tokens: int,
        stage_name: str,
    ) -> tuple[str, str, str, bool]:
        """Single structured generation call with bounded retry on unusable output.

        The model owns semantic beats, one reaction, and a semantic physical location.
        Protean validates the JSON and renders the visible () / ** / "" transcript locally.
        There is no second model-based visible-output gate.
        """

        messages = [
            *provider_messages,
            {"role": "system", "content": STRUCTURED_OUTPUT_INSTRUCTION},
        ]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                # The retry is intentionally calmer. Free/weaker JSON-only models
                # usually fail because they embellish or vary the object shape, not
                # because they need more creativity.
                attempt_temperature = temperature if attempt == 0 else min(temperature, 0.2)
                completion = await self._provider.complete_structured(
                    api_key=api_key,
                    model=model,
                    messages=messages,
                    temperature=attempt_temperature,
                    max_tokens=hard_max_tokens,
                    response_format=ROLEPLAY_RESPONSE_SCHEMA,
                )
                structured = parse_structured_roleplay(completion.content)
                visible = structured.render()
                if not visible:
                    raise ValueError("structured response rendered to an empty transcript")
                return (
                    visible,
                    structured.reaction,
                    structured.location,
                    structured.location_changed,
                )
            except (EmptyCompletionError, LengthCutoffError) as exc:
                last_error = exc
            except ValueError as exc:
                last_error = exc
            if attempt == 0:
                reason = str(last_error or "unknown validation error")
                logger.info("Retrying invalid/empty structured %s completion once: %s", stage_name, reason)
                messages = [
                    *provider_messages,
                    {"role": "system", "content": STRUCTURED_OUTPUT_INSTRUCTION},
                    {
                        "role": "system",
                        "content": (
                            "CONTROL RETRY: The previous result was empty, incomplete, or failed Protean's local JSON validation. "
                            f"Validation issue: {reason}. "
                            "Return exactly one valid structured roleplay object and nothing else. "
                            "Do not explain the correction."
                        ),
                    },
                ]

        reason = str(last_error or "unknown validation error")
        raise ChatServiceError(
            f"Protean could not obtain a valid structured {stage_name} from the provider. "
            f"Last local validation issue: {reason}. Try again or choose a model that reliably returns Protean-compatible JSON."
        ) from last_error
