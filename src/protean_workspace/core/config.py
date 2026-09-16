from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = PACKAGE_DIR.parents[1]


class Settings(BaseSettings):
    """Runtime settings. Secrets may come from env in deployments, but local mode self-bootstraps."""

    app_name: str = "Protean Workspace"
    app_version: str = "0.6.1-rc2"
    debug: bool = False

    instance_dir: Path = PROJECT_DIR / "instance"
    static_dir: Path = PACKAGE_DIR / "static"
    context_dir: Path = PACKAGE_DIR / "data" / "context"
    default_library_root: Path = PACKAGE_DIR / "data" / "library"

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openrouter/free"
    openrouter_timeout_seconds: float = 45.0
    openrouter_http_referer: str = "http://127.0.0.1:8000"

    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    secure_cookies: bool = False
    jwt_secret_key: str | None = None
    credential_encryption_key: str | None = None

    max_character_file_bytes: int = 1_000_000
    max_character_scan_files: int = 500
    max_chat_history_messages: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def assistant_shell_dir(self) -> Path:
        return PACKAGE_DIR / "assistant_shell"

    @property
    def database_path(self) -> Path:
        current = self.instance_dir / "protean_workspace.db"
        legacy = self.instance_dir / "riddle_studio.db"
        if not current.exists() and legacy.exists():
            return legacy
        return current

    @property
    def jwt_key_path(self) -> Path:
        return self.instance_dir / "jwt.key"

    @property
    def encryption_key_path(self) -> Path:
        return self.instance_dir / "credentials.key"

    @property
    def session_cookie_name(self) -> str:
        return "__Host-protean_session" if self.secure_cookies else "protean_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()
