from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

REACTIONS = (
    "neutral",
    "positive",
    "amused",
    "serious",
    "concerned",
    "surprised",
    "thinking",
)
BEAT_TYPES = ("action", "speech", "dev")

# Safe aliases for weaker JSON-only models. These aliases normalize presentation
# vocabulary only; they never change roleplay state, timeline knowledge, or scenario.
_REACTION_ALIASES = {
    "calm": "neutral",
    "composed": "neutral",
    "none": "neutral",
    "happy": "positive",
    "warm": "positive",
    "smiling": "positive",
    "pleased": "positive",
    "playful": "amused",
    "smirking": "amused",
    "laughing": "amused",
    "stern": "serious",
    "focused": "serious",
    "determined": "serious",
    "cold": "serious",
    "worried": "concerned",
    "anxious": "concerned",
    "empathetic": "concerned",
    "shocked": "surprised",
    "startled": "surprised",
    "astonished": "surprised",
    "confused": "surprised",
    "thoughtful": "thinking",
    "pondering": "thinking",
    "contemplative": "thinking",
}

_BEAT_ALIASES = {
    "action": "action",
    "narration": "action",
    "movement": "action",
    "gesture": "action",
    "expression": "action",
    "speech": "speech",
    "dialogue": "speech",
    "dialog": "speech",
    "spoken": "speech",
    "say": "speech",
    "dev": "dev",
    "developer": "dev",
    "ooc": "dev",
}

ROLEPLAY_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "protean_roleplay_turn",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reaction", "location", "beats"],
            "properties": {
                "reaction": {"type": "string", "enum": list(REACTIONS)},
                "location": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["label", "changed"],
                    "properties": {
                        "label": {"type": "string", "minLength": 1, "maxLength": 240},
                        "changed": {"type": "boolean"},
                    },
                },
                "beats": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 12,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "text"],
                        "properties": {
                            "type": {"type": "string", "enum": list(BEAT_TYPES)},
                            "text": {"type": "string", "minLength": 1, "maxLength": 5000},
                        },
                    },
                },
            },
        },
    },
}


@dataclass(frozen=True)
class StructuredBeat:
    type: str
    text: str


@dataclass(frozen=True)
class StructuredRoleplayReply:
    reaction: str
    location: str
    location_changed: bool
    beats: tuple[StructuredBeat, ...]

    def render(self) -> str:
        rendered: list[str] = []
        for beat in self.beats:
            text = _clean_beat_text(beat.text)
            if beat.type == "action":
                rendered.append(f"**{text}**")
            elif beat.type == "speech":
                # Keep Protean's ASCII quote delimiters deterministic. Inner double
                # quotes become single quotes so the transcript parser cannot split a beat.
                rendered.append(f'"{text.replace(chr(34), chr(39))}"')
            elif beat.type == "dev":
                rendered.append(f"({_clean_dev_text(text)})")
        return "\n\n".join(rendered).strip()


def parse_structured_roleplay(content: str) -> StructuredRoleplayReply:
    """Parse provider JSON while safely normalizing harmless structural variation.

    Native JSON-schema responses should already match exactly. JSON-object/plain JSON
    fallbacks can be weaker, so Protean tolerates wrappers, common field aliases, a
    string-form location, and an omitted `location.changed` flag. The normalization
    is deliberately presentation-only: no character, timeline, scenario, or knowledge
    state can be inferred or modified here.
    """

    data = _load_json_object(content)
    data = _unwrap_common_container(data)

    raw_reaction = str(data.get("reaction") or "neutral").strip().lower()
    reaction = _REACTION_ALIASES.get(raw_reaction, raw_reaction)
    if reaction not in REACTIONS:
        raise ValueError("structured completion contained an invalid reaction")

    location = data.get("location")
    if isinstance(location, str):
        location_label = location.strip()
        location_changed = False
    elif isinstance(location, dict):
        location_label = str(
            location.get("label")
            or location.get("name")
            or location.get("place")
            or location.get("location")
            or ""
        ).strip()
        location_changed = _normalize_bool(
            location.get("changed", location.get("moved", location.get("location_changed", False))),
            field_name="location.changed",
        )
    else:
        raise ValueError("structured completion contained no location object or location string")

    if not location_label or len(location_label) > 240:
        raise ValueError("structured completion contained an invalid location label")

    raw_beats = data.get("beats")
    if raw_beats is None:
        raw_beats = data.get("segments") or data.get("messages")
    if raw_beats is None:
        # Common almost-correct object shape from weaker models.
        compact: list[dict[str, str]] = []
        for field, beat_type in (("action", "action"), ("speech", "speech"), ("dev", "dev"), ("ooc", "dev")):
            value = data.get(field)
            if isinstance(value, str) and value.strip():
                compact.append({"type": beat_type, "text": value})
        raw_beats = compact

    if not isinstance(raw_beats, list) or not raw_beats or len(raw_beats) > 12:
        raise ValueError("structured completion contained an invalid beat list")

    beats: list[StructuredBeat] = []
    for item in raw_beats:
        beat = _normalize_beat(item)
        if beat is None:
            raise ValueError("structured completion contained an invalid beat")
        beats.append(beat)

    return StructuredRoleplayReply(
        reaction=reaction,
        location=location_label,
        location_changed=location_changed,
        beats=tuple(beats),
    )


def _load_json_object(content: str) -> dict[str, Any]:
    raw = str(content or "").strip()
    if not raw:
        raise ValueError("structured completion was empty")

    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        candidate = _extract_first_json_object(raw)
        if candidate is None:
            raise ValueError("structured completion was not valid JSON")
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError("structured completion was not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("structured completion must be an object")
    return data


def _extract_first_json_object(raw: str) -> str | None:
    """Extract one balanced JSON object from harmless prose/fence wrappers.

    This never interprets the surrounding prose. It only locates a syntactically
    balanced object so provider labels such as `Here is the JSON:` cannot break the
    fallback path.
    """

    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]
    return None


def _unwrap_common_container(data: dict[str, Any]) -> dict[str, Any]:
    # Some JSON-only models wrap the requested object in a harmless response/result
    # key. Accept exactly one nested object when it clearly contains Protean fields.
    if any(key in data for key in ("reaction", "location", "beats", "segments")):
        return data
    for key in ("response", "result", "output", "roleplay"):
        nested = data.get(key)
        if isinstance(nested, dict) and any(
            field in nested for field in ("reaction", "location", "beats", "segments", "action", "speech")
        ):
            return nested
    return data


def _normalize_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0", ""}:
            return False
    if value is None:
        return False
    raise ValueError(f"structured completion contained an invalid {field_name} flag")


def _normalize_beat(item: Any) -> StructuredBeat | None:
    if isinstance(item, str):
        text = item.strip()
        if text.startswith("**") and text.endswith("**") and len(text) >= 4:
            return StructuredBeat(type="action", text=text)
        if text.startswith('"') and text.endswith('"') and len(text) >= 2:
            return StructuredBeat(type="speech", text=text)
        if text.startswith("(") and text.endswith(")") and len(text) >= 2:
            return StructuredBeat(type="dev", text=text)
        return None

    if not isinstance(item, dict):
        return None
    raw_type = str(item.get("type") or item.get("kind") or "").strip().lower()
    beat_type = _BEAT_ALIASES.get(raw_type, raw_type)
    text = str(item.get("text") or item.get("content") or "").strip()
    if beat_type not in BEAT_TYPES or not text or len(text) > 5000:
        return None
    return StructuredBeat(type=beat_type, text=text)


def _clean_beat_text(text: str) -> str:
    clean = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split()).strip()
    # Remove accidental outer Protean delimiters because the renderer owns syntax.
    if clean.startswith("**") and clean.endswith("**") and len(clean) >= 4:
        clean = clean[2:-2].strip()
    if clean.startswith('"') and clean.endswith('"') and len(clean) >= 2:
        clean = clean[1:-1].strip()
    if clean.startswith("(") and clean.endswith(")") and len(clean) >= 2:
        clean = clean[1:-1].strip()
    return clean


def _clean_dev_text(text: str) -> str:
    # Parentheses are structural delimiters in Protean grammar. Flatten nested ones.
    return text.replace("(", "[").replace(")", "]")
