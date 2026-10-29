from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    username: str
    role: str


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, session: Session) -> str:
        token = secrets.token_hex(16)
        self._sessions[token] = session
        return token

    def get(self, token: str | None) -> Session | None:
        if not token:
            return None
        return self._sessions.get(token)

    def remove(self, token: str) -> None:
        self._sessions.pop(token, None)


# Local demo accounts. They are not real credentials.
DEMO_USERS: dict[str, dict[str, str]] = {
    "demo.manager": {"password": "ChangeMe123!", "role": "Manager"},
    "demo.director": {"password": "ChangeMe123!", "role": "Director"},
    "demo.director2": {"password": "ChangeMe123!", "role": "Director"},
    "demo.approver": {"password": "ChangeMe123!", "role": "Approver"},
    "demo.admin": {"password": "ChangeMe123!", "role": "Admin"},
}

# Roles that may open the approval screen. The domain still decides the limit.
APPROVAL_ACTORS = {"Manager", "Director", "Approver", "Admin"}
