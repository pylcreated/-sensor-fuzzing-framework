"""Simple POC access control with role-based checks."""

from __future__ import annotations

from typing import Dict, Set


class AccessController:
    def __init__(self) -> None:
        # role -> permissions
        self.permissions: Dict[str, Set[str]] = {
            "admin": {"poc_use", "poc_manage"},
            "tester": {"poc_use"},
        }
        self.user_roles: Dict[str, Set[str]] = {}

    def assign_role(self, user: str, role: str) -> None:
        self.user_roles.setdefault(user, set()).add(role)

    def can_use_poc(self, user: str) -> bool:
        return self._has_perm(user, "poc_use")

    def can_manage_poc(self, user: str) -> bool:
        return self._has_perm(user, "poc_manage")

    def _has_perm(self, user: str, perm: str) -> bool:
        roles = self.user_roles.get(user, set())
        for r in roles:
            if perm in self.permissions.get(r, set()):
                return True
        return False
