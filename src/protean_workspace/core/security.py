from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt.exceptions import InvalidTokenError


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    username: str
    jti: str
    expires_at: datetime


def create_access_token(
    *,
    user_id: int,
    username: str,
    secret_key: str,
    algorithm: str,
    lifetime_minutes: int,
) -> tuple[str, TokenPayload]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=lifetime_minutes)
    jti = uuid4().hex
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token, TokenPayload(user_id=user_id, username=username, jti=jti, expires_at=expires_at)


def decode_access_token(token: str, *, secret_key: str, algorithm: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        if payload.get("type") != "access":
            raise InvalidTokenError("Unexpected token type")
        user_id = int(payload["sub"])
        username = str(payload["username"])
        jti = str(payload["jti"])
        expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=UTC)
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Invalid access token") from exc
    return TokenPayload(user_id=user_id, username=username, jti=jti, expires_at=expires_at)
