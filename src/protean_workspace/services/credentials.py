from protean_workspace.core.crypto import CredentialCipher
from protean_workspace.db.repositories import CredentialRepository


class CredentialService:
    def __init__(self, repository: CredentialRepository, cipher: CredentialCipher) -> None:
        self._repository = repository
        self._cipher = cipher

    @staticmethod
    def _mask(secret: str) -> str:
        if len(secret) <= 10:
            return "••••••••"
        return f"{secret[:8]}…{secret[-4:]}"

    def set(self, user_id: int, provider: str, secret: str) -> str:
        normalized = secret.strip()
        encrypted = self._cipher.encrypt(normalized)
        masked = self._mask(normalized)
        self._repository.upsert(user_id, provider, encrypted, masked)
        return masked

    def get(self, user_id: int, provider: str) -> str | None:
        stored = self._repository.get(user_id, provider)
        if stored is None:
            return None
        encrypted, _ = stored
        return self._cipher.decrypt(encrypted)

    def masked(self, user_id: int, provider: str) -> str | None:
        stored = self._repository.get(user_id, provider)
        return stored[1] if stored else None

    def delete(self, user_id: int, provider: str) -> None:
        self._repository.delete(user_id, provider)
