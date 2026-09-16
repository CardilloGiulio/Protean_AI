from protean_workspace.core.prompts import build_system_prompt
from protean_workspace.models.domain import CharacterCard
from protean_workspace.services.presets import get_tone


def test_prompt_contains_transcript_budget_and_medium_contract() -> None:
    card = CharacterCard(
        id="test",
        name="Test",
        franchise="Test",
        description="",
        personality="",
        scenario="",
        system_prompt="",
        first_message="",
        tags=(),
        source="test.json",
        medium_type="enchanted diary",
        medium_context="Ink is the shared medium.",
        medium_rules=("Do not pretend to share a room.",),
    )
    prompt = build_system_prompt(character=card, tone=get_tone("canon"), context="", target_tokens=420)
    assert "enchanted diary" in prompt
    assert "Do not pretend to share a room." in prompt
    assert "roughly 420 tokens" in prompt
    assert "Protean Workspace owns the visible syntax" in prompt
    assert 'Double quotes ""' in prompt
    assert "Double asterisks ** **" in prompt


def test_phase_prompt_locks_future_character_growth() -> None:
    from protean_workspace.models.domain import CharacterPhase

    card = CharacterCard(
        id="ann-test",
        name="Ann",
        franchise="Persona 5",
        description="Core",
        personality="Base personality",
        scenario="Base scenario",
        system_prompt="Base instruction",
        first_message="",
        tags=(),
        source="test.json",
    )
    phase = CharacterPhase(
        id="pre-kamoshida",
        name="Before Kamoshida",
        period="April",
        summary="Before the arc resolves",
        story_so_far="Shiho is her closest friend; Ann is not a Phantom Thief yet.",
        personality="Withdrawn and pressured",
        scenario="Early Shujin",
        system_prompt="Do not use Phantom Thief confidence.",
        first_message="",
        known_events=("Kamoshida is pressuring Ann.",),
        future_locks=("Ann has not awakened Carmen.",),
    )
    prompt = build_system_prompt(
        character=card,
        phase=phase,
        tone=get_tone("canon"),
        context="",
        target_tokens=320,
    )
    assert "TIMELINE DISCIPLINE" in prompt
    assert "Ann has not awakened Carmen." in prompt
    assert "Withdrawn and pressured" in prompt


def test_prompt_requires_structured_semantics_and_location_discipline() -> None:
    from protean_workspace.core.prompts import BASE_INSTRUCTION

    assert "Protean structured JSON" in BASE_INSTRUCTION
    assert "one dominant reaction" in BASE_INSTRUCTION
    assert "physical scene location" in BASE_INSTRUCTION
    assert "Merely mentioning another place must not change location" in BASE_INSTRUCTION
    assert "Never output asset filenames" in BASE_INSTRUCTION
