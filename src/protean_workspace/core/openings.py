from protean_workspace.models.domain import CharacterCard, CharacterPhase, CharacterScenario
from protean_workspace.services.presets import TonePreset


def build_opening_message(
    *,
    character: CharacterCard,
    phase: CharacterPhase,
    scenario: CharacterScenario,
    tone: TonePreset,
) -> str:
    """Compile the visible first assistant message from frozen roleplay state.

    This is deliberately deterministic and provider-free. It keeps the opening in
    sync with the same phase/scenario/tone state that will later build the system
    prompt, while avoiding a model call just to preview or create a chat.
    """

    medium = (phase.medium_type or character.medium_type or "chat").lower()
    if _scenario_is_explicitly_physical(scenario, medium):
        medium = "in-person"
    parts = [
        _scenario_cue(character.name, scenario, medium),
        _tone_cue(character.name, scenario, tone.id, medium),
        (scenario.first_message or phase.first_message or character.first_message).strip(),
    ]
    return "\n\n".join(part for part in parts if part)


def _scenario_is_explicitly_physical(scenario: CharacterScenario, medium: str) -> bool:
    """Let a concrete face-to-face scene outrank a card's default written medium."""

    if any(word in medium for word in ("diary", "terminal")):
        return False
    scene = " ".join((scenario.what_happening, scenario.who_involved)).lower()
    physical_markers = (
        "the user finds",
        "the user enters",
        "the user catches",
        "the user is present",
        "the user watches",
        "the user notices",
        "the user interrupts",
        "the user discovers",
        "occupy the same physical",
    )
    return any(marker in scene for marker in physical_markers)


def _scenario_cue(name: str, scenario: CharacterScenario, medium: str) -> str:
    written = any(word in medium for word in ("diary", "written", "correspondence", "message", "terminal"))

    if scenario.id == "first-encounter":
        if written:
            return "**The first response carries the caution reserved for an unfamiliar correspondent.**"
        return f"**{name}'s attention settles on the unfamiliar person before them, measured rather than welcoming.**"

    if scenario.id == "known-acquaintance":
        if written:
            return "**The response comes with recognition already established; this is not a first exchange.**"
        return f"**Recognition is immediate when {name} turns their attention to you.**"

    if scenario.id == "pressure-point":
        if written:
            return "**The reply comes quickly; the immediate problem has displaced whatever ceremony the exchange might have had.**"
        return f"**There is little room for ceremony; {name}'s attention is already fixed on the problem at hand.**"

    if scenario.custom:
        scene = " ".join(scenario.what_happening.replace("**", "").split())
        if len(scene) > 260:
            scene = scene[:257].rstrip() + "…"
        return f"**{scene}**" if scene else (
            "**The exchange begins inside the situation you established, without resetting it to a generic introduction.**"
            if written
            else f"**The scene is already in motion when {name} turns their attention to you.**"
        )

    return ""


def _tone_cue(name: str, scenario: CharacterScenario, tone_id: str, medium: str) -> str:
    if tone_id == "canon":
        return ""

    written = any(word in medium for word in ("diary", "written", "correspondence", "message", "terminal"))
    dynamic = scenario.dynamic.lower()
    strangers = any(marker in dynamic for marker in ("stranger", "no automatic trust", "no special relationship"))

    if tone_id == "immersive":
        return (
            "**The pauses and rhythm of the written exchange are unusually noticeable before the answer settles.**"
            if written
            else f"**For a beat, the surrounding scene seems sharper before {name} answers.**"
        )
    if tone_id == "cinematic":
        return "**The moment tightens around the immediate scene before the response comes.**"
    if tone_id == "intimate":
        if strangers:
            return (
                "**The exchange is quiet and closely observed, but nothing in it assumes familiarity that has not been earned.**"
                if written
                else f"**{name}'s attention stays close and observant, but guarded; the scene does not pretend you already know each other well.**"
            )
        return (
            "**The reply arrives more quietly than usual, with more weight in the pauses between words.**"
            if written
            else f"**{name} answers more quietly than usual, letting the pauses carry part of the meaning.**"
        )
    if tone_id == "cold":
        return (
            "**The wording is controlled and gives away very little.**"
            if written
            else f"**{name} gives away very little before responding.**"
        )
    if tone_id == "playful":
        return (
            "**A trace of amusement slips into the wording without erasing the scene's boundaries.**"
            if written
            else f"**A trace of amusement touches {name}'s expression without dissolving the situation's boundaries.**"
        )
    if tone_id == "narrative":
        return "**The exchange settles into a measured rhythm before the opening response.**"
    return ""
