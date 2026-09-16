import json
import re
from pathlib import Path

from protean_workspace.core.config import Settings
from protean_workspace.models.domain import CharacterCard, CharacterPhase, CharacterScenario

_SUPPORTED_EXTENSIONS = {".json", ".md", ".txt"}
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


class CharacterLibraryError(RuntimeError):
    pass


class CharacterLibrary:
    """Read-only character discovery inside one authenticated user's configured root."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cards_by_root: dict[str, list[CharacterCard]] = {}

    def validate_root(self, value: str) -> Path:
        root = Path(value).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise CharacterLibraryError("Character library folder does not exist or is not a directory")
        return root

    def research(self, root_value: str, query: str = "") -> list[CharacterCard]:
        root = self.validate_root(root_value)
        query_tokens = self._tokens(query)
        scored: list[tuple[int, CharacterCard]] = []
        scanned = 0

        for path in root.rglob("*"):
            if scanned >= self._settings.max_character_scan_files:
                break
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            scanned += 1
            try:
                if path.stat().st_size > self._settings.max_character_file_bytes:
                    continue
                card = self._load_card(root, path)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
                continue
            score = self._score(card, query_tokens, query)
            if not query_tokens or score > 0:
                scored.append((score, card))

        scored.sort(key=lambda item: (-item[0], item[1].franchise.lower(), item[1].name.lower()))
        result = [card for _, card in scored[:80]]
        if not query_tokens:
            self._cards_by_root[str(root)] = result
        return result

    def get(self, root_value: str, character_id: str) -> CharacterCard | None:
        root = self.validate_root(root_value)
        cards = self._cards_by_root.get(str(root))
        if cards is None:
            cards = self.research(str(root))
        return next((card for card in cards if card.id == character_id), None)

    def _load_card(self, root: Path, path: Path) -> CharacterCard:
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Character JSON must be an object")
            name = str(data.get("name") or path.stem).strip()
            franchise = str(data.get("franchise") or self._franchise_from_path(path)).strip()
            card_id = str(data.get("id") or self._slug(name)).strip()
            tags_raw = data.get("tags") or []
            tags = tuple(str(tag) for tag in tags_raw) if isinstance(tags_raw, list) else ()
            medium_type, medium_context, medium_rules = self._parse_medium(data.get("medium"))
            phases = self._parse_phases(data.get("phases"), medium_type, medium_context, medium_rules)
            default_phase_id = str(data.get("default_phase_id") or (phases[0].id if phases else "default")).strip()
            if phases and not any(phase.id == default_phase_id for phase in phases):
                default_phase_id = phases[0].id
            return CharacterCard(
                id=card_id,
                name=name,
                franchise=franchise,
                description=str(data.get("description") or "").strip(),
                personality=str(data.get("personality") or "").strip(),
                scenario=str(data.get("scenario") or "").strip(),
                system_prompt=str(data.get("system_prompt") or "").strip(),
                first_message=str(data.get("first_message") or "").strip(),
                tags=tags,
                source=relative,
                portrait=str(data.get("portrait") or "").strip(),
                medium_type=medium_type,
                medium_context=medium_context,
                medium_rules=medium_rules,
                story=str(data.get("story") or "").strip(),
                default_phase_id=default_phase_id,
                phases=phases,
            )

        content = path.read_text(encoding="utf-8").strip()
        return CharacterCard(
            id=self._slug(path.stem),
            name=path.stem.replace("_", " ").replace("-", " ").title(),
            franchise=self._franchise_from_path(path),
            description=content[:800],
            personality="",
            scenario="",
            system_prompt=content,
            first_message="",
            tags=(),
            source=relative,
            story=content,
        )

    def _parse_phases(
        self,
        raw: object,
        base_medium_type: str,
        base_medium_context: str,
        base_medium_rules: tuple[str, ...],
    ) -> tuple[CharacterPhase, ...]:
        if not isinstance(raw, list):
            return ()
        phases: list[CharacterPhase] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            phase_id = str(item.get("id") or "").strip()
            if not phase_id or phase_id in seen:
                continue
            seen.add(phase_id)
            phase_medium_type, phase_medium_context, phase_medium_rules = self._parse_medium(
                item.get("medium"),
                fallback=(base_medium_type, base_medium_context, base_medium_rules),
            )
            known_events = self._string_tuple(item.get("known_events"))
            future_locks = self._string_tuple(item.get("future_locks"))
            scenarios = self._parse_scenarios(item.get("scenarios"))
            default_scenario_id = str(
                item.get("default_scenario_id") or (scenarios[0].id if scenarios else "")
            ).strip()
            if scenarios and not any(scene.id == default_scenario_id for scene in scenarios):
                default_scenario_id = scenarios[0].id
            phases.append(
                CharacterPhase(
                    id=phase_id,
                    name=str(item.get("name") or phase_id).strip(),
                    period=str(item.get("period") or "").strip(),
                    summary=str(item.get("summary") or "").strip(),
                    story_so_far=str(item.get("story_so_far") or "").strip(),
                    personality=str(item.get("personality") or "").strip(),
                    scenario=str(item.get("scenario") or "").strip(),
                    system_prompt=str(item.get("system_prompt") or "").strip(),
                    first_message=str(item.get("first_message") or "").strip(),
                    known_events=known_events,
                    future_locks=future_locks,
                    medium_type=phase_medium_type,
                    medium_context=phase_medium_context,
                    medium_rules=phase_medium_rules,
                    default_scenario_id=default_scenario_id,
                    scenarios=scenarios,
                    identity_name=str(item.get("identity_name") or "").strip(),
                )
            )
        return tuple(phases)


    def _parse_scenarios(self, raw: object) -> tuple[CharacterScenario, ...]:
        if not isinstance(raw, list):
            return ()
        scenarios: list[CharacterScenario] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            scenario_id = str(item.get("id") or "").strip()
            if not scenario_id or scenario_id in seen:
                continue
            seen.add(scenario_id)
            what_happening = str(item.get("what_happening") or "").strip()
            who_involved = str(item.get("who_involved") or "").strip()
            dynamic = str(item.get("dynamic") or "").strip()
            if not (what_happening and who_involved and dynamic):
                continue
            scenarios.append(
                CharacterScenario(
                    id=scenario_id,
                    name=str(item.get("name") or scenario_id).strip(),
                    what_happening=what_happening,
                    who_involved=who_involved,
                    dynamic=dynamic,
                    first_message=str(item.get("first_message") or "").strip(),
                )
            )
        return tuple(scenarios)

    @staticmethod
    def _parse_medium(
        raw: object,
        fallback: tuple[str, str, tuple[str, ...]] | None = None,
    ) -> tuple[str, str, tuple[str, ...]]:
        fallback_type, fallback_context, fallback_rules = fallback or ("chat", "", ())
        if not isinstance(raw, dict):
            return fallback_type, fallback_context, fallback_rules
        rules_raw = raw.get("rules")
        rules = CharacterLibrary._string_tuple(rules_raw) if rules_raw is not None else fallback_rules
        return (
            str(raw.get("type") or fallback_type).strip(),
            str(raw.get("context") or fallback_context).strip(),
            rules,
        )

    @staticmethod
    def _string_tuple(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token.lower() for token in _TOKEN_PATTERN.findall(text) if len(token) > 1}

    def _score(self, card: CharacterCard, query_tokens: set[str], raw_query: str) -> int:
        if not query_tokens:
            return 0
        phase_text = " ".join(
            " ".join(
                [
                    phase.name, phase.period, phase.summary, phase.story_so_far, phase.personality, phase.scenario,
                    " ".join(
                        f"{scene.name} {scene.what_happening} {scene.who_involved} {scene.dynamic}"
                        for scene in phase.scenarios
                    ),
                ]
            )
            for phase in card.phases
        )
        haystack = " ".join(
            [
                card.name,
                card.franchise,
                card.description,
                card.personality,
                card.scenario,
                card.story,
                " ".join(card.tags),
                phase_text,
            ]
        ).lower()
        score = sum(2 for token in query_tokens if token in haystack)
        if raw_query.strip().lower() in card.name.lower():
            score += 12
        if raw_query.strip().lower() in card.franchise.lower():
            score += 5
        return score

    @staticmethod
    def _franchise_from_path(path: Path) -> str:
        parent = path.parent.name.replace("-", " ").replace("_", " ").strip()
        return parent.title() if parent else "Other"

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "character"
