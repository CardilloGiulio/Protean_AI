from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

ASSISTANT_REACTIONS = (
    "neutral",
    "positive",
    "amused",
    "serious",
    "concerned",
    "surprised",
    "thinking",
    "embarrassed",
    "annoyed",
    "tired",
)

_REACTION_ALIASES = {
    "calm": "neutral",
    "composed": "neutral",
    "happy": "positive",
    "warm": "positive",
    "pleased": "positive",
    "playful": "amused",
    "smirking": "amused",
    "stern": "serious",
    "focused": "serious",
    "worried": "concerned",
    "anxious": "concerned",
    "shocked": "surprised",
    "startled": "surprised",
    "confused": "surprised",
    "thoughtful": "thinking",
    "contemplative": "thinking",
    "shy": "embarrassed",
    "flustered": "embarrassed",
    "irritated": "annoyed",
    "angry": "annoyed",
    "sleepy": "tired",
    "fatigued": "tired",
}

ASSISTANT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "protean_virtual_assistant_remark",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reaction", "remark"],
            "properties": {
                "reaction": {"type": "string", "enum": list(ASSISTANT_REACTIONS)},
                "remark": {"type": "string", "minLength": 1, "maxLength": 1200},
            },
        },
    },
}


@dataclass(frozen=True)
class AssistantReply:
    reaction: str
    remark: str


def parse_assistant_reply(content: str) -> AssistantReply:
    raw = str(content or "").strip()
    if not raw:
        raise ValueError("assistant completion was empty")
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        candidate = _extract_first_json_object(raw)
        if candidate is None:
            raise ValueError("assistant completion was not valid JSON")
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError("assistant completion was not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("assistant completion must be an object")
    if not any(key in data for key in ("reaction", "remark")):
        for key in ("response", "result", "output", "assistant"):
            nested = data.get(key)
            if isinstance(nested, dict) and any(field in nested for field in ("reaction", "remark")):
                data = nested
                break

    raw_reaction = str(data.get("reaction") or "neutral").strip().lower()
    reaction = _REACTION_ALIASES.get(raw_reaction, raw_reaction)
    if reaction not in ASSISTANT_REACTIONS:
        raise ValueError("assistant completion contained an invalid reaction")

    remark = str(data.get("remark") or data.get("text") or data.get("message") or "").strip()
    if not remark:
        raise ValueError("assistant completion contained no remark")
    if len(remark) > 1200:
        raise ValueError("assistant completion remark was too long")
    # The bubble contains only visible speech/OOC text; reject the RP action grammar.
    if "**" in remark:
        remark = remark.replace("**", "").strip()
    return AssistantReply(reaction=reaction, remark=remark)


def _extract_first_json_object(raw: str) -> str | None:
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
                return raw[start:index + 1]
    return None
