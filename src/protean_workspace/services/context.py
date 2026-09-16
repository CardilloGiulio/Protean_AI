import csv
import re
from pathlib import Path
from typing import Any


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./:-]+")


class ContextRepository:
    """Load shared reference knowledge once and retrieve relevant excerpts per message."""

    def __init__(self, context_dir: Path) -> None:
        self._context_dir = context_dir
        self._raw_text = self._load_text_file("raw_knowledge.txt")
        self._rows = self._load_csv_rows("knowledge.csv")
        self._raw_chunks = self._split_raw_text_into_chunks(self._raw_text)

    def _load_text_file(self, filename: str) -> str:
        path = self._context_dir / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _load_csv_rows(self, filename: str) -> list[dict[str, Any]]:
        path = self._context_dir / filename
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in _TOKEN_PATTERN.findall(text) if len(token) > 2}

    @staticmethod
    def _score_text(query_words: set[str], text: str) -> int:
        lowered = text.lower()
        return sum(1 for word in query_words if word in lowered)

    def _find_relevant_csv_rows(self, user_message: str, *, limit: int = 8) -> list[dict[str, Any]]:
        query_words = self._tokenize(user_message)
        scored: list[tuple[int, dict[str, Any]]] = []
        for row in self._rows:
            text = " ".join(str(value) for value in row.values())
            score = self._score_text(query_words, text)
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:limit]]

    @staticmethod
    def _split_raw_text_into_chunks(text: str, max_chars: int = 1600) -> list[str]:
        if not text.strip():
            return []
        blocks: list[str] = []
        current: list[str] = []
        current_chars = 0
        for line in text.splitlines():
            is_boundary = line.startswith("TOPIC ") or line.startswith("MODULE ") or line.startswith("=" * 70)
            if is_boundary and current:
                blocks.append("\n".join(current).strip())
                current = []
                current_chars = 0
            current.append(line)
            current_chars += len(line)
            if current_chars > max_chars:
                blocks.append("\n".join(current).strip())
                current = []
                current_chars = 0
        if current:
            blocks.append("\n".join(current).strip())
        return [block for block in blocks if block]

    def _find_relevant_text_chunks(self, user_message: str, *, limit: int = 4) -> list[str]:
        query_words = self._tokenize(user_message)
        scored: list[tuple[int, str]] = []
        for chunk in self._raw_chunks:
            score = self._score_text(query_words, chunk)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]

    def build_context(self, user_message: str) -> str:
        relevant_rows = self._find_relevant_csv_rows(user_message)
        relevant_chunks = self._find_relevant_text_chunks(user_message)
        parts: list[str] = []

        if relevant_rows:
            csv_parts = ["CSV KNOWLEDGE:"]
            for row in relevant_rows:
                csv_parts.append(
                    f"Module: {row.get('module', '')}\n"
                    f"Topic: {row.get('topic', '')}\n"
                    f"Concept: {row.get('concept', '')}\n"
                    f"Definition: {row.get('definition', '')}\n"
                    f"MustKnow: {row.get('must_know', '')}\n"
                    f"Example: {row.get('example', '')}\n"
                    f"SecurityNote: {row.get('security_note', '')}\n"
                    f"Command: {row.get('command', '')}\n"
                    f"CommonMistake: {row.get('common_mistake', '')}"
                )
            parts.append("\n\n".join(csv_parts))

        if relevant_chunks:
            text_parts = ["RAW KNOWLEDGE EXCERPTS:"]
            for index, chunk in enumerate(relevant_chunks, start=1):
                text_parts.append(f"Excerpt {index}:\n{chunk}")
            parts.append("\n\n".join(text_parts))

        return "\n\n".join(parts)
