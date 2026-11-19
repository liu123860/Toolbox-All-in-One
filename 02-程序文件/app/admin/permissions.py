"""管理员权限矩阵（阶段 4）。

依据 03-账号与权限系统设计.md：
- 只有主管理员能创建管理员账号
- 主管理员创建的管理员为 sub_admin（权限更小：不能管理别的账号）
- 任何角色都不能修改用户资料（界面无入口、后端无接口）
"""
from __future__ import annotations

from typing import Dict, Optional

from app.account.db import User

ROLE_LABELS = {
    "guest": "游客",
    "user": "普通用户",
    "admin": "管理员",
    "sub_admin": "受限管理员",
    "main_admin": "主管理员",
}

# ability -> 允许的角色
_MATRIX: Dict[str, tuple] = {
    "open_admin_panel": ("main_admin", "admin", "sub_admin"),
    "manage_users": ("main_admin", "admin"),          # 用户增删/恢复
    "create_admin": ("main_admin",),                  # 唯一
    "open_code_editor": ("main_admin", "admin", "sub_admin"),
    "patch_behavior": ("main_admin", "admin"),        # 行为类配置
    "edit_user_info": (),                             # 永远禁止
}


def role_label(role: Optional[str]) -> str:
    return ROLE_LABELS.get(role or "", "未知")


def can(user: Optional[User], ability: str) -> bool:
    if not user:
        return False
    return user.role in _MATRIX.get(ability, ())


def abilities(user: Optional[User]) -> Dict[str, bool]:
    return {k: can(user, k) for k in _MATRIX}


def patch_scope(user: Optional[User]) -> str:
    """代码编辑区可修改范围：full / appearance / none。"""
    if not can(user, "open_code_editor"):
        return "none"
    return "full" if user.role in ("main_admin", "admin") else "appearance"


def describe(user: Optional[User]) -> str:
    if not user:
        return "未登录"
    a = abilities(user)
    caps = []
    if a["manage_users"]:
        caps.append("用户增删/恢复")
    if a["create_admin"]:
        caps.append("创建管理员")
    if a["open_code_editor"]:
        caps.append("代码编辑区（" + ("外观+行为" if a["patch_behavior"] else "仅外观") + "）")
    if not caps:
        caps.append("只读查看")
    return "、".join(caps)
