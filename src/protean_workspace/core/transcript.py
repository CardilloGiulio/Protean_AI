from __future__ import annotations

import re


REACTIONS = (
    "neutral",
    "positive",
    "amused",
    "serious",
    "concerned",
    "surprised",
    "thinking",
)

_REACTION_PATTERN = re.compile(
    r"\[\[\s*PROTEAN_REACTION\s*:\s*(neutral|positive|amused|serious|concerned|surprised|thinking)\s*\]\]",
    re.IGNORECASE,
)
_DRAFT_PATTERN = re.compile(
    r"\[\[\s*PROTEAN_DRAFT\s*\]\]([\s\S]*?)\[\[\s*/\s*PROTEAN_DRAFT\s*\]\]",
    re.IGNORECASE,
)
_DRAFT_TAG_PATTERN = re.compile(r"\[\[\s*/?\s*PROTEAN_DRAFT\s*\]\]", re.IGNORECASE)
_ARTIFACT_LINE_PATTERN = re.compile(
    r"^\s*(?:user\s+safety|assistant\s+safety|safety|policy\s+classification|content\s+safety)\s*:\s*"
    r"(?:safe|unsafe|allowed|disallowed|unknown|pass|passed|ok)\s*$",
    re.IGNORECASE,
)
_TOKEN_PATTERN = re.compile(r'(?:\*\*[\s\S]*?\*\*|"[^"\n]*(?:\n[^"\n]*)*"|\([^()]*\))')
_META_DEV_PREFIX = re.compile(
    r"^\s*(?:analysis|reasoning|thought\s+process|chain[- ]of[- ]thought|user\s+safety|assistant\s+safety|"
    r"policy(?:\s+classification)?|system\s+prompt|developer\s+prompt)\b",
    re.IGNORECASE,
)


def extract_reaction(content: str) -> tuple[str, str | None]:
    """Backward-compatible reaction extraction from a provider completion."""
    text = str(content or "")
    matches = list(_REACTION_PATTERN.finditer(text))
    reaction = matches[0].group(1).lower() if matches else None
    visible = _REACTION_PATTERN.sub("", text).strip()
    return visible, reaction


def extract_private_draft(content: str) -> tuple[str, str | None]:
    """Extract the private draft envelope plus exactly one semantic reaction when present.

    Text outside a valid PROTEAN_DRAFT envelope is ignored when an envelope exists. This
    keeps accidental provider chatter, safety labels, or meta commentary out of the
    material sent to the visible-output gate.
    """

    raw = str(content or "")
    reaction_matches = list(_REACTION_PATTERN.finditer(raw))
    reaction = reaction_matches[0].group(1).lower() if reaction_matches else None
    draft_match = _DRAFT_PATTERN.search(raw)
    if draft_match:
        draft = draft_match.group(1)
    else:
        draft = _REACTION_PATTERN.sub("", _DRAFT_TAG_PATTERN.sub("", raw))
    return strip_provider_artifacts(draft), reaction


def strip_provider_artifacts(content: str) -> str:
    """Remove narrow provider/UI artifacts without rewriting substantive roleplay."""

    text = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _REACTION_PATTERN.sub("", _DRAFT_TAG_PATTERN.sub("", text))
    lines = []
    for line in text.splitlines():
        if _ARTIFACT_LINE_PATTERN.match(line):
            continue
        if line.strip() in {"```", "```text", "```markdown", "```md"}:
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def normalize_visible_transcript(content: str) -> str:
    """Normalize harmless typography while preserving roleplay semantics."""

    text = strip_provider_artifacts(content)
    # Models sometimes use typographic double quotes. Protean's parser deliberately
    # uses ASCII quotes as grammar delimiters.
    text = text.replace("“", '"').replace("”", '"')
    # Collapse excessive blank space, while preserving one blank line between beats.
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    return text.strip()


def is_valid_visible_transcript(content: str) -> bool:
    """Return True only when all visible non-whitespace text uses Protean grammar."""

    text = normalize_visible_transcript(content)
    if not text:
        return False
    position = 0
    found = False
    for match in _TOKEN_PATTERN.finditer(text):
        if text[position : match.start()].strip():
            return False
        token = match.group(0)
        inner = token[2:-2] if token.startswith("**") else token[1:-1]
        if not inner.strip():
            return False
        if token.startswith("(") and _META_DEV_PREFIX.match(inner):
            return False
        found = True
        position = match.end()
    if text[position:].strip():
        return False
    return found
