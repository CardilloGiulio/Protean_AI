import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS credentials (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    secret_blob TEXT NOT NULL,
    masked_key TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, provider)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    library_root TEXT NOT NULL,
    active_character_id TEXT NOT NULL,
    active_phase_id TEXT NOT NULL DEFAULT '',
    tone_id TEXT NOT NULL,
    theme_id TEXT NOT NULL,
    background_id TEXT NOT NULL,
    frame_id TEXT NOT NULL,
    provider_model TEXT NOT NULL,
    temperature REAL NOT NULL,
    target_tokens INTEGER NOT NULL DEFAULT 500,
    max_tokens INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    character_id TEXT NOT NULL,
    phase_id TEXT NOT NULL DEFAULT '',
    scenario_id TEXT NOT NULL DEFAULT '',
    scenario_json TEXT NOT NULL DEFAULT '',
    tone_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id, id);

CREATE TABLE IF NOT EXISTS chat_turn_requests (
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    request_id TEXT NOT NULL,
    user_message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    assistant_message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    reaction TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    location_changed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, request_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_turn_requests_assistant
ON chat_turn_requests(assistant_message_id);

CREATE TABLE IF NOT EXISTS immersion_scene_state (
    chat_id TEXT PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
    location TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(_SCHEMA)
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        """Small additive migrations for local installs; never destructively rewrites user data."""
        preference_columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(user_preferences)").fetchall()
        }
        if "target_tokens" not in preference_columns:
            connection.execute(
                "ALTER TABLE user_preferences ADD COLUMN target_tokens INTEGER NOT NULL DEFAULT 500"
            )
        if "active_phase_id" not in preference_columns:
            connection.execute(
                "ALTER TABLE user_preferences ADD COLUMN active_phase_id TEXT NOT NULL DEFAULT ''"
            )

        chat_columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(chats)").fetchall()
        }
        if "phase_id" not in chat_columns:
            connection.execute("ALTER TABLE chats ADD COLUMN phase_id TEXT NOT NULL DEFAULT ''")
        if "scenario_id" not in chat_columns:
            connection.execute("ALTER TABLE chats ADD COLUMN scenario_id TEXT NOT NULL DEFAULT ''")
        if "scenario_json" not in chat_columns:
            connection.execute("ALTER TABLE chats ADD COLUMN scenario_json TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
