from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = 'HS256'
PASSWORD_ALGORITHM = 'pbkdf2_sha256'
PASSWORD_ITERATIONS = 260000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode('ascii')
    digest_text = base64.urlsafe_b64encode(digest).decode('ascii')
    return f'{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_text}${digest_text}'


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split('$', 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode('ascii'))
        expected = base64.urlsafe_b64decode(digest_text.encode('ascii'))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_access_token(subject: str, extra: dict[str, Any] | None = None, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {'sub': subject, 'exp': expires_at}
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError('登录状态无效或已过期') from exc


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
