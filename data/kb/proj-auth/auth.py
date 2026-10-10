"""认证核心逻辑（proj-auth）。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from errors import (  # noqa: F401 - 供依赖/符号索引使用
    AUTH_INVALID_CREDENTIALS,
    AUTH_PERMISSION_DENIED,
    AUTH_TOKEN_EXPIRED,
    AUTH_USER_DISABLED,
    AuthError,
)
from models import Session, User, UserStore

_PBKDF2_ROUNDS = 120_000
_SESSION_TTL = timedelta(hours=12)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """返回 (salt, hash)。使用 PBKDF2-HMAC-SHA256。"""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ROUNDS)
    return salt, digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """恒定时间比较口令哈希。"""
    _, actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected_hash)


def verify_login(store: UserStore, username: str, password: str) -> User:
    """校验登录：用户存在 -> 未禁用 -> 口令正确；否则抛带错误码的 AuthError。"""
    user = store.find(username)
    if user is None:
        raise AuthError(AUTH_INVALID_CREDENTIALS, "用户名或密码错误")
    if user.disabled:
        raise AuthError(AUTH_USER_DISABLED, "账户已禁用")
    if not verify_password(password, user.password_hash[:32], user.password_hash[32:]):
        raise AuthError(AUTH_INVALID_CREDENTIALS, "用户名或密码错误")
    return user


def issue_session(user: User, now: datetime | None = None) -> Session:
    now = now or datetime.utcnow()
    return Session(token=secrets.token_urlsafe(24), user_id=user.user_id,
                   issued_at=now, expires_at=now + _SESSION_TTL)


def require_admin(user: User) -> None:
    """权限检查：非管理员抛权限错误。"""
    if not user.is_admin():
        raise AuthError(AUTH_PERMISSION_DENIED, "需要管理员权限")


def check_session(session: Session, now: datetime | None = None) -> None:
    if session.expired(now or datetime.utcnow()):
        raise AuthError(AUTH_TOKEN_EXPIRED, "会话已过期")
