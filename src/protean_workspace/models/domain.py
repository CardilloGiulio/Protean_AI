from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    created_at: datetime


@dataclass(frozen=True)
class CharacterScenario:
    id: str
    name: str
    what_happening: str
    who_involved: str
    dynamic: str
    first_message: str = ""
    custom: bool = False


@dataclass(frozen=True)
class CharacterPhase:
    id: str
    name: str
    period: str
    summary: str
    story_so_far: str
    personality: str
    scenario: str
    system_prompt: str
    first_message: str
    known_events: tuple[str, ...] = ()
    future_locks: tuple[str, ...] = ()
    medium_type: str = ""
    medium_context: str = ""
    medium_rules: tuple[str, ...] = ()
    default_scenario_id: str = ""
    scenarios: tuple[CharacterScenario, ...] = ()
    identity_name: str = ""

    def scene(self, scenario_id: str | None = None) -> CharacterScenario | None:
        if not self.scenarios:
            return None
        requested = (scenario_id or "").strip()
        if requested:
            match = next((scene for scene in self.scenarios if scene.id == requested), None)
            if match is not None:
                return match
        if self.default_scenario_id:
            default = next((scene for scene in self.scenarios if scene.id == self.default_scenario_id), None)
            if default is not None:
                return default
        return self.scenarios[0]

    def has_scenario(self, scenario_id: str) -> bool:
        return any(scene.id == scenario_id for scene in self.scenarios)


@dataclass(frozen=True)
class CharacterCard:
    id: str
    name: str
    franchise: str
    description: str
    personality: str
    scenario: str
    system_prompt: str
    first_message: str
    tags: tuple[str, ...]
    source: str
    portrait: str = ""
    medium_type: str = "chat"
    medium_context: str = ""
    medium_rules: tuple[str, ...] = ()
    story: str = ""
    default_phase_id: str = "default"
    phases: tuple[CharacterPhase, ...] = ()

    def phase(self, phase_id: str | None = None) -> CharacterPhase:
        requested = (phase_id or "").strip()
        if self.phases:
            if requested:
                match = next((phase for phase in self.phases if phase.id == requested), None)
                if match is not None:
                    return match
            default = next((phase for phase in self.phases if phase.id == self.default_phase_id), None)
            return default or self.phases[0]
        return CharacterPhase(
            id="default",
            name="Default",
            period="Unspecified",
            summary=self.description,
            story_so_far=self.story or self.description,
            personality=self.personality,
            scenario=self.scenario,
            system_prompt=self.system_prompt,
            first_message=self.first_message,
            medium_type=self.medium_type,
            medium_context=self.medium_context,
            medium_rules=self.medium_rules,
        )

    def has_phase(self, phase_id: str) -> bool:
        if not self.phases:
            return phase_id in {"", "default"}
        return any(phase.id == phase_id for phase in self.phases)


@dataclass(frozen=True)
class UserPreferences:
    user_id: int
    library_root: str
    active_character_id: str
    active_phase_id: str
    tone_id: str
    theme_id: str
    background_id: str
    frame_id: str
    provider_model: str
    temperature: float
    target_tokens: int
    max_tokens: int
