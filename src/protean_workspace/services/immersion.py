from __future__ import annotations

import json
import re
from pathlib import Path

from protean_workspace.core.config import Settings
from protean_workspace.db.repositories import PreferencesRepository
from protean_workspace.services.characters import CharacterLibrary
from protean_workspace.services.chat import ChatService
from protean_workspace.services.presets import get_tone


class ImmersionUnavailableError(RuntimeError):
    """Raised when the requested character/phase has no complete ready visual route."""


class ImmersionService:
    """Presentation-only adapter for the full-screen Immersion route.

    This service may validate visual availability and select ready asset IDs. It delegates all
    roleplay/chat behavior to ChatService and has no provider, credential, auth, or database
    write authority of its own.
    """

    _DEFAULT_BACKGROUNDS = {
        ("tom-riddle", "fifth-year-chamber"): "bg-hp-hogwarts-corridor-1940s",
        ("tom-riddle", "diary-imprint"): "bg-hp-diary-desk",
        ("tom-riddle", "sixth-year-horcrux"): "bg-hp-hogwarts-library-night",
        ("hermione-granger", "first-year-arrival"): "bg-hp-hogwarts-corridor-day",
        ("hermione-granger", "first-year-post-troll"): "bg-hp-hogwarts-library",
        ("hermione-granger", "fifth-year-da"): "bg-hp-room-of-requirement",
    }

    # The list is deliberately semantic. Asset filenames never enter the model prompt.
    _LOCATION_CUES = (
        (r"\b(?:room of requirement|dumbledore(?:'s|’s) army room|d\.a\. room)\b", "bg-hp-room-of-requirement"),
        (r"\b(?:chamber of secrets|the chamber)\b", "bg-hp-chamber-of-secrets"),
        (r"\b(?:battle-damaged hogwarts|ruined hogwarts|battle of hogwarts)\b", "bg-hp-hogwarts-battle"),
        (r"\b(?:forest camp|campsite|camping tent|inside the tent|in the tent)\b", "bg-hp-forest-camp"),
        (r"\b(?:common room|gryffindor common room)\b", "bg-hp-common-room-winter"),
        (r"\b(?:rainy library|library.*rain|rain.*library)\b", "bg-hp-hogwarts-library-rain"),
        (r"\b(?:library)\b", "__library__"),
        (r"\b(?:corridor|hallway|stone hall)\b", "__corridor__"),
        (r"\b(?:open diary|riddle(?:'s|’s) diary|diary on the desk|writing in the diary)\b", "bg-hp-diary-desk"),
    )

    _TRANSITION_VERBS = re.compile(
        r"\b(?:enter|enters|entered|walk|walks|walked|step|steps|stepped|head|heads|headed|"
        r"move|moves|moved|arrive|arrives|arrived|return|returns|returned|appear|appears|appeared|"
        r"find myself|find ourselves|we are now|we're now|inside|into|through)\b",
        re.IGNORECASE,
    )
    _INITIAL_LOCATION_CUES = (
        (r"\b(?:inside|within|in|at|into|enters?|entered|scene opens inside|scene opens in) (?:the )?(?:room of requirement|dumbledore(?:'s|’s) army room|d\.a\. room)\b", "bg-hp-room-of-requirement"),
        (r"\b(?:inside|within|in|at|into|enters?|entered|scene opens inside|scene opens in) (?:the )?(?:chamber of secrets|chamber)\b", "bg-hp-chamber-of-secrets"),
        (r"\b(?:inside|within|in|at|into|enters?|entered) (?:the )?(?:common room|gryffindor common room)\b", "bg-hp-common-room-winter"),
        (r"\b(?:inside|within|in|at|into|enters?|entered) (?:the )?(?:library)\b", "__library__"),
        (r"\b(?:inside|within|in|at|into|enters?|entered) (?:the )?(?:corridor|hallway|stone hall)\b", "__corridor__"),
        (r"\b(?:inside|within|in|at|into|enters?|entered) (?:the )?(?:forest camp|campsite|camping tent|tent)\b", "bg-hp-forest-camp"),
        (r"\b(?:inside|within|in|at|into|enters?|entered) (?:a |the )?(?:ruined hogwarts|battle-damaged hogwarts)\b", "bg-hp-hogwarts-battle"),
        (r"\b(?:open diary|riddle(?:'s|’s) diary|diary on the desk|writing in the diary)\b", "bg-hp-diary-desk"),
    )


    _EXPRESSION_RULES = (
        ("surprised", re.compile(r"\b(?:eyes widen|wide-eyed|startled|stunned|surprised|blinks? sharply|shock)\b", re.I)),
        ("amused", re.compile(r"\b(?:smirk|smirks|amused|chuckle|chuckles|laugh|laughs|grin|grins|wry)\b", re.I)),
        ("positive", re.compile(r"\b(?:smile|smiles|softens|warmly|brightens|relieved|approval)\b", re.I)),
        ("concerned", re.compile(r"\b(?:concern|worried|worry|uneasy|frown|frowns|brow furrows|troubled|anxious)\b", re.I)),
        ("serious", re.compile(r"\b(?:serious|stern|firmly|coldly|narrows? (?:his|her|their) eyes|determined|hardens)\b", re.I)),
        ("thinking", re.compile(r"\b(?:considers?|thinking|thinks|studies|ponders?|calculates?|recalls?|pauses? thoughtfully|tilts? (?:his|her|their) head)\b", re.I)),
    )

    _MOVEMENT_RULES = (
        ("approach", re.compile(r"\b(?:steps? closer|moves? closer|approaches?|leans? closer|comes? closer)\b", re.I)),
        ("retreat", re.compile(r"\b(?:steps? back|moves? back|backs? away|retreats?|draws? back)\b", re.I)),
        ("left", re.compile(r"\b(?:moves?|steps?|walks?) (?:to |toward |towards )?(?:the )?left\b", re.I)),
        ("right", re.compile(r"\b(?:moves?|steps?|walks?) (?:to |toward |towards )?(?:the )?right\b", re.I)),
        ("recoil", re.compile(r"\b(?:recoils?|flinches?|jerks? back|startles?)\b", re.I)),
        ("lean", re.compile(r"\b(?:leans?|bends?) (?:in|forward|closer)\b", re.I)),
        ("turn", re.compile(r"\b(?:turns? aside|turns? away|glances? aside|looks? away)\b", re.I)),
    )

    def __init__(
        self,
        *,
        settings: Settings,
        preferences: PreferencesRepository,
        characters: CharacterLibrary,
        chat_service: ChatService,
    ) -> None:
        self._settings = settings
        self._preferences = preferences
        self._characters = characters
        self._chat_service = chat_service
        self._manifest_path = settings.static_dir / "assets" / "immersion" / "manifest.json"
        self._manifest = self._load_manifest(self._manifest_path)
        self._packs = {item["id"]: item for item in self._manifest.get("sprite_packs", [])}
        self._backgrounds = {item["id"]: item for item in self._manifest.get("backgrounds", [])}

    @staticmethod
    def _load_manifest(path: Path) -> dict[str, object]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("Immersion asset manifest must be a JSON object")
        return data

    def availability(self, user_id: int) -> dict[str, object]:
        prefs = self._preferences.get(user_id)
        result: list[dict[str, object]] = []
        ready_character_ids = sorted(
            {
                str(pack.get("character_id") or "")
                for pack in self._packs.values()
                if pack.get("status") == "ready"
            }
        )
        for character_id in ready_character_ids:
            card = self._characters.get(prefs.library_root, character_id)
            if card is None:
                continue
            phases: list[dict[str, object]] = []
            for phase in card.phases:
                pack = self._ready_pack(character_id, phase.id)
                background = self._ready_background(self._DEFAULT_BACKGROUNDS.get((character_id, phase.id), ""))
                if pack is None or background is None:
                    continue
                phases.append(
                    {
                        "id": phase.id,
                        "name": phase.name,
                        "period": phase.period,
                        "render_mode": self._render_mode(character_id, phase.id),
                        "sprite_pack_id": str(pack.get("id") or ""),
                        "default_background_id": str(background.get("id") or ""),
                        "default_background_path": str(background.get("path") or ""),
                    }
                )
            if phases:
                result.append(
                    {
                        "character_id": card.id,
                        "name": card.name,
                        "portrait": card.portrait,
                        "phases": phases,
                    }
                )
        return {"enabled": bool(result), "characters": result}

    def assert_available(self, user_id: int, character_id: str, phase_id: str) -> tuple[object, object, dict[str, object]]:
        prefs = self._preferences.get(user_id)
        card = self._characters.get(prefs.library_root, character_id)
        if card is None:
            raise ImmersionUnavailableError(f"Character '{character_id}' is not available")
        if not card.has_phase(phase_id):
            raise ImmersionUnavailableError(f"Timeline phase '{phase_id}' is not available for {card.name}")
        phase = card.phase(phase_id)
        pack = self._ready_pack(card.id, phase.id)
        background = self._ready_background(self._DEFAULT_BACKGROUNDS.get((card.id, phase.id), ""))
        if pack is None or background is None:
            raise ImmersionUnavailableError(
                f"Immersion assets for {card.name} — {phase.name} are still incoming"
            )
        return card, phase, pack

    async def start(
        self,
        user_id: int,
        *,
        character_id: str,
        phase_id: str,
        scenario_id: str | None,
        custom_scenario: dict[str, str] | None,
        tone_id: str,
    ) -> dict[str, object]:
        card, phase, _ = self.assert_available(user_id, character_id, phase_id)
        preview = await self._chat_service.preview_opening(
            user_id,
            character_id=character_id,
            phase_id=phase_id,
            scenario_id=scenario_id,
            custom_scenario=custom_scenario,
            tone_id=tone_id,
        )
        opening_token = str(preview["opening_token"])
        opening_reaction = self._chat_service.opening_reaction(opening_token)
        opening_location, opening_location_changed = self._chat_service.opening_scene_state(opening_token)
        created = self._chat_service.create_chat(
            user_id,
            character_id=character_id,
            phase_id=phase_id,
            scenario_id=scenario_id,
            custom_scenario=custom_scenario,
            tone_id=tone_id,
            title=f"Immersion · {card.name} — {phase.name}",
            opening_token=opening_token,
        )
        detail = self._chat_service.get_chat(user_id, str(created["id"]))
        messages = list(detail.get("messages") or [])
        opening = str(messages[-1].get("content") or "") if messages else ""
        trusted_location = opening_location or phase.scenario or phase.name
        self._chat_service.set_scene_location(user_id, str(created["id"]), trusted_location)
        presentation = self.presentation(
            character_id=card.id,
            phase_id=phase.id,
            reply=opening,
            location=trusted_location,
            location_changed=opening_location_changed,
            current_background_id=None,
            initial=True,
            tone_id=str(created["tone_id"]),
            scenario_id=str(created["scenario_id"]),
            reaction=opening_reaction,
        )
        tone = get_tone(str(created["tone_id"]))
        return {
            "chat": created,
            "character_name": card.name,
            "phase_name": phase.name,
            "scenario_name": str(detail.get("scenario_name") or "Open scene"),
            "tone_name": tone.name,
            "opening": opening,
            "presentation": presentation,
        }

    async def send_message(
        self,
        user_id: int,
        chat_id: str,
        *,
        message: str,
        request_id: str,
        current_background_id: str | None,
        current_location: str | None = None,
    ) -> dict[str, object]:
        detail = self._chat_service.get_chat(user_id, chat_id)
        character_id = str(detail["character_id"])
        phase_id = str(detail["phase_id"])
        self.assert_available(user_id, character_id, phase_id)

        # Browser presentation state is not prompt authority. Continuity comes
        # only from the last location accepted and held by the backend.
        trusted_location = self._chat_service.get_scene_location(user_id, chat_id)
        response = await self._chat_service.send_message(
            user_id,
            chat_id,
            message,
            request_id=request_id,
            current_location=trusted_location,
        )
        next_location = str(response.get("location") or trusted_location or "scene")
        self._chat_service.set_scene_location(user_id, chat_id, next_location)
        presentation = self.presentation(
            character_id=character_id,
            phase_id=phase_id,
            reply=str(response["reply"]),
            location=next_location,
            location_changed=bool(response.get("location_changed")),
            current_background_id=current_background_id,
            initial=False,
            tone_id=str(detail.get("tone_id") or "canon"),
            scenario_id=str(detail.get("scenario_id") or ""),
            reaction=str(response.get("reaction") or "") or None,
        )
        return {**response, "presentation": presentation}

    def presentation(
        self,
        *,
        character_id: str,
        phase_id: str,
        reply: str,
        location: str,
        location_changed: bool,
        current_background_id: str | None,
        initial: bool,
        tone_id: str = "canon",
        scenario_id: str = "",
        reaction: str | None = None,
    ) -> dict[str, object]:
        pack = self._ready_pack(character_id, phase_id)
        if pack is None:
            raise ImmersionUnavailableError("The selected phase does not have a ready sprite pack")

        render_mode = self._render_mode(character_id, phase_id)
        expression = (reaction or "").strip().lower()
        if expression not in {"neutral", "positive", "amused", "serious", "concerned", "surprised", "thinking"}:
            expression = self._infer_expression(reply)
            if expression == "neutral":
                expression = self._fallback_expression(tone_id=tone_id, scenario_id=scenario_id)
        sprite_path: str | None = None
        if render_mode == "sprite":
            sprite_path = self._expression_path(pack, expression)
            if sprite_path is None:
                expression = "neutral"
                sprite_path = self._expression_path(pack, "neutral") or str(pack.get("fallback") or "") or None

        background = self._resolve_background(
            character_id=character_id,
            phase_id=phase_id,
            location=location,
            location_changed=location_changed,
            current_background_id=current_background_id,
            initial=initial,
        )
        movement = "idle" if render_mode == "diary" else self._infer_movement(reply, expression)
        return {
            "render_mode": render_mode,
            "sprite_pack_id": str(pack.get("id") or ""),
            "expression": expression,
            "sprite_path": sprite_path,
            "movement": movement,
            "location": location,
            "location_changed": location_changed,
            "background_id": str(background.get("id") or ""),
            "background_path": str(background.get("path") or ""),
        }

    def _ready_pack(self, character_id: str, phase_id: str) -> dict[str, object] | None:
        for pack in self._packs.values():
            if pack.get("status") != "ready":
                continue
            if pack.get("character_id") != character_id:
                continue
            if phase_id in (pack.get("phase_ids") or []):
                return pack
        return None

    def _ready_background(self, background_id: str) -> dict[str, object] | None:
        item = self._backgrounds.get(background_id)
        if not item or item.get("status") != "ready" or not item.get("path"):
            return None
        return item

    @staticmethod
    def _render_mode(character_id: str, phase_id: str) -> str:
        if character_id == "tom-riddle" and phase_id == "diary-imprint":
            return "diary"
        return "sprite"

    @staticmethod
    def _expression_path(pack: dict[str, object], expression: str) -> str | None:
        expressions = pack.get("expressions")
        if not isinstance(expressions, dict):
            return None
        entry = expressions.get(expression)
        if not isinstance(entry, dict) or entry.get("status") != "ready":
            return None
        path = entry.get("path")
        return str(path) if path else None

    def _resolve_background(
        self,
        *,
        character_id: str,
        phase_id: str,
        location: str,
        location_changed: bool,
        current_background_id: str | None,
        initial: bool,
    ) -> dict[str, object]:
        default_id = self._DEFAULT_BACKGROUNDS.get((character_id, phase_id), "bg-protean-default")
        default = self._ready_background(default_id) or self._ready_background("bg-protean-default")
        neutral = self._ready_background("bg-protean-default") or default
        if default is None or neutral is None:
            raise ImmersionUnavailableError("No ready Immersion background is available")

        # Diary Tom remains diary-first; location metadata cannot materialize him or
        # replace the diary presentation without a future explicit design change.
        if self._render_mode(character_id, phase_id) == "diary":
            return default

        current = self._ready_background(current_background_id or "")
        semantic_location = str(location or "").strip()

        # After the opening, the model's explicit `changed` flag is the sole authority
        # for a physical scene transition. Mentioning a place in dialogue/action never
        # changes the background by itself.
        if not initial and not location_changed:
            return current or default

        candidate_id = self._background_id_from_cues(
            character_id=character_id,
            cue_text=semantic_location,
            cues=self._LOCATION_CUES,
        )
        candidate = self._ready_background(candidate_id or "")
        if candidate is not None:
            return candidate

        if initial:
            # Keep the phase default only when the semantic location is generic/empty.
            # A concrete unmatched location gets a neutral fallback rather than a false room.
            if not semantic_location or semantic_location.lower() in {"scene", "current scene"}:
                return default
            return neutral

        # The scene genuinely moved but we have no matching ready background yet.
        # Do not lie by keeping the old physical room on screen.
        return neutral

    @staticmethod
    def _resolve_contextual_background_id(character_id: str, background_id: str) -> str:
        if background_id == "__library__":
            return "bg-hp-hogwarts-library-night" if character_id == "tom-riddle" else "bg-hp-hogwarts-library"
        if background_id == "__corridor__":
            return "bg-hp-hogwarts-corridor-1940s" if character_id == "tom-riddle" else "bg-hp-hogwarts-corridor-day"
        return background_id

    def _background_id_from_cues(
        self,
        *,
        character_id: str,
        cue_text: str,
        cues: tuple[tuple[str, str], ...],
    ) -> str | None:
        if not cue_text.strip():
            return None
        for pattern, background_id in cues:
            if re.search(pattern, cue_text, flags=re.IGNORECASE):
                return self._resolve_contextual_background_id(character_id, background_id)
        return None

    def _location_cue_text(self, text: str) -> str:
        actions = " ".join(re.findall(r"\*\*([\s\S]*?)\*\*", text))
        lines = [line for line in text.splitlines() if self._TRANSITION_VERBS.search(line)]
        return " ".join([actions, *lines]).strip()

    def _infer_expression(self, reply: str) -> str:
        action_text = " ".join(re.findall(r"\*\*([\s\S]*?)\*\*", reply))
        source = action_text or reply
        for expression, pattern in self._EXPRESSION_RULES:
            if pattern.search(source):
                return expression
        return "neutral"


    @staticmethod
    def _fallback_expression(*, tone_id: str, scenario_id: str) -> str:
        if scenario_id == "pressure-point":
            return "serious"
        return {
            "playful": "amused",
            "intimate": "positive",
            "cold": "serious",
        }.get(tone_id, "neutral")

    def _infer_movement(self, reply: str, expression: str) -> str:
        action_text = " ".join(re.findall(r"\*\*([\s\S]*?)\*\*", reply))
        source = action_text or reply
        for movement, pattern in self._MOVEMENT_RULES:
            if pattern.search(source):
                return movement
        if expression == "surprised":
            return "recoil"
        if expression in {"serious", "concerned"}:
            return "approach"
        if expression == "thinking":
            return "lean"
        if expression == "amused":
            return "shift"
        return "idle"
