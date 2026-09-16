from __future__ import annotations


STRUCTURED_OUTPUT_INSTRUCTION = """PROTEAN STRUCTURED OUTPUT CONTRACT — MANDATORY:
- Return exactly one JSON object and nothing else. When the provider supplies a JSON schema, match it exactly; when native schema mode is unavailable, follow the Protean object contract below exactly. Do not return prose, Markdown fences, labels, safety classifications, hidden reasoning, analysis, or chain-of-thought.
- Required top-level shape: {"reaction": <allowed reaction>, "location": {"label": <non-empty string>, "changed": <boolean>}, "beats": [{"type": <action|speech|dev>, "text": <non-empty string>}, ...]}. Do not add extra top-level or beat fields.
- `beats` contains only user-visible semantic roleplay beats. The allowed types are:
  - `action`: physical action, posture, facial expression, or scene action.
  - `speech`: words spoken aloud by the character.
  - `dev`: a genuinely user-visible developer/OOC note. Use rarely.
- Do NOT place Protean punctuation such as **, double-quote wrappers, or parentheses around beat text. Protean Workspace renders those deterministically after validation.
- `reaction` is exactly ONE dominant visible reaction for the whole assistant turn: neutral, positive, amused, serious, concerned, surprised, or thinking.
- `location.label` is the concrete place where the scene is physically happening at the END of this turn. Prefer a concise human description, for example `Hogwarts grounds beneath the moonlight`, `the Room of Requirement`, or `Tom Riddle's diary on a desk`.
- `location.changed` is true ONLY if the scene physically moves to a different place during this turn. Mentioning, remembering, seeing, or talking about another place does not count as moving there.
- Location is scene state, not character knowledge. An earlier timeline character may occupy an unfamiliar place without magically knowing its future/canon name. In that case describe the location neutrally from what is physically observable.
- Never output asset filenames, background IDs, sprite IDs, or implementation details.
"""
