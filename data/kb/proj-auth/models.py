"""用户与会话模型（proj-auth）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    roles: list[str] = field(default_factory=list)
    disabled: bool = False

    def is_admin(self) -> bool:
        return "admin" in self.roles


@dataclass
class Session:
    token: str
    user_id: str
    issued_at: datetime
    expires_at: datetime

    def expired(self, now: datetime) -> bool:
        return now >= self.expires_at


class UserStore:
    """内存用户表；真实实现应替换为数据库访问。"""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.username] = user

    def find(self, username: str) -> User | None:
        return self._users.get(username)
