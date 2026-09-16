from dataclasses import dataclass

from jwt.exceptions import InvalidTokenError

from protean_workspace.core.config import Settings
from protean_workspace.core.security import (
    TokenPayload,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from protean_workspace.db.repositories import PreferencesRepository, SessionRepository, UserRepository
from protean_workspace.models.domain import User, UserPreferences


class AuthenticationError(RuntimeError):
    pass


class SetupUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    token: str
    token_payload: TokenPayload


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        preferences: PreferencesRepository,
        settings: Settings,
        jwt_secret: str,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._preferences = preferences
        self._settings = settings
        self._jwt_secret = jwt_secret

    def is_initialized(self) -> bool:
        return self._users.count() > 0

    def setup_owner(self, username: str, password: str) -> AuthenticatedSession:
        if self.is_initialized():
            raise SetupUnavailableError("Application setup has already been completed")
        user = self._users.create(username.strip(), hash_password(password))
        self._ensure_preferences(user.id)
        return self._issue(user)

    def login(self, username: str, password: str) -> AuthenticatedSession:
        user = self._users.get_by_username(username.strip())
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        self._ensure_preferences(user.id)
        return self._issue(user)

    def authenticate(self, token: str | None) -> tuple[User, TokenPayload]:
        if not token:
            raise AuthenticationError("Authentication required")
        try:
            payload = decode_access_token(
                token,
                secret_key=self._jwt_secret,
                algorithm=self._settings.jwt_algorithm,
            )
        except InvalidTokenError as exc:
            raise AuthenticationError("Invalid or expired session") from exc
        if not self._sessions.is_active(payload.jti, payload.user_id):
            raise AuthenticationError("Session is no longer active")
        user = self._users.get(payload.user_id)
        if user is None:
            raise AuthenticationError("User no longer exists")
        return user, payload

    def logout(self, token: str | None) -> int | None:
        if not token:
            return None
        try:
            payload = decode_access_token(
                token,
                secret_key=self._jwt_secret,
                algorithm=self._settings.jwt_algorithm,
            )
        except InvalidTokenError:
            return None
        self._sessions.revoke(payload.jti)
        self._sessions.purge_inactive()
        return payload.user_id

    def _issue(self, user: User) -> AuthenticatedSession:
        self._sessions.purge_inactive()
        token, payload = create_access_token(
            user_id=user.id,
            username=user.username,
            secret_key=self._jwt_secret,
            algorithm=self._settings.jwt_algorithm,
            lifetime_minutes=self._settings.access_token_minutes,
        )
        self._sessions.create(payload.jti, user.id, payload.expires_at)
        return AuthenticatedSession(user=user, token=token, token_payload=payload)

    def _ensure_preferences(self, user_id: int) -> None:
        self._preferences.ensure(
            UserPreferences(
                user_id=user_id,
                library_root=str(self._settings.default_library_root.resolve()),
                active_character_id="tom-riddle",
                active_phase_id="diary-imprint",
                tone_id="canon",
                theme_id="obsidian",
                background_id="protean",
                frame_id="notebook",
                provider_model=self._settings.openrouter_default_model,
                temperature=0.85,
                target_tokens=500,
                max_tokens=900,
            )
        )
