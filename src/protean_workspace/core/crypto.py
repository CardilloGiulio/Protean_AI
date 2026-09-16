import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretMaterialError(RuntimeError):
    pass


def _write_private_file(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Windows and some filesystems do not expose POSIX permissions.
        pass


def load_or_create_text_secret(path: Path, configured: str | None, *, bytes_length: int = 48) -> str:
    if configured:
        return configured.strip()
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(bytes_length)
    _write_private_file(path, value)
    return value


def load_or_create_fernet_key(path: Path, configured: str | None) -> bytes:
    if configured:
        key = configured.strip().encode("ascii")
    elif path.exists():
        key = path.read_text(encoding="utf-8").strip().encode("ascii")
    else:
        key = Fernet.generate_key()
        _write_private_file(path, key.decode("ascii"))

    try:
        Fernet(key)
    except (ValueError, TypeError) as exc:
        raise SecretMaterialError("Credential encryption key is not a valid Fernet key") from exc
    return key


class CredentialCipher:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise SecretMaterialError("Stored credential could not be decrypted") from exc
