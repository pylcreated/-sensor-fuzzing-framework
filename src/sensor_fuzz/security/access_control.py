"""Simple POC access control with role-based checks."""

from __future__ import annotations

from typing import Dict, Set


class AccessController:
    """类说明：封装 AccessController 的相关行为。"""
    def __init__(self) -> None:
        # role -> permissions
        """方法说明：执行   init   相关逻辑。"""
        self.permissions: Dict[str, Set[str]] = {
            "admin": {"poc_use", "poc_manage"},
            "tester": {"poc_use"},
        }
        self.user_roles: Dict[str, Set[str]] = {}

    def assign_role(self, user: str, role: str) -> None:
        """方法说明：执行 assign role 相关逻辑。"""
        self.user_roles.setdefault(user, set()).add(role)

    def can_use_poc(self, user: str) -> bool:
        """方法说明：执行 can use poc 相关逻辑。"""
        return self._has_perm(user, "poc_use")

    def can_manage_poc(self, user: str) -> bool:
        """方法说明：执行 can manage poc 相关逻辑。"""
        return self._has_perm(user, "poc_manage")

    def _has_perm(self, user: str, perm: str) -> bool:
        """方法说明：执行  has perm 相关逻辑。"""
        roles = self.user_roles.get(user, set())
        for r in roles:
            if perm in self.permissions.get(r, set()):
                return True
        return False
