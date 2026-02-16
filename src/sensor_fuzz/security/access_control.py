"""访问控制模块：基于角色进行 POC 能力授权校验。"""

from __future__ import annotations

from typing import Dict, Set


class AccessController:
    """访问控制器：维护角色权限与用户角色映射。"""
    def __init__(self) -> None:
        # role -> permissions
        """初始化默认角色权限和用户角色容器。"""
        self.permissions: Dict[str, Set[str]] = {
            "admin": {"poc_use", "poc_manage"},
            "tester": {"poc_use"},
        }
        self.user_roles: Dict[str, Set[str]] = {}

    def assign_role(self, user: str, role: str) -> None:
        """为指定用户分配角色。"""
        self.user_roles.setdefault(user, set()).add(role)

    def can_use_poc(self, user: str) -> bool:
        """判断用户是否具备使用 POC 的权限。"""
        return self._has_perm(user, "poc_use")

    def can_manage_poc(self, user: str) -> bool:
        """判断用户是否具备管理 POC 的权限。"""
        return self._has_perm(user, "poc_manage")

    def _has_perm(self, user: str, perm: str) -> bool:
        """检查用户在其角色集合中是否拥有指定权限。"""
        roles = self.user_roles.get(user, set())
        for r in roles:
            if perm in self.permissions.get(r, set()):
                return True
        return False
