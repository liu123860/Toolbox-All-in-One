"""管理界面后端：用户增删/恢复、创建受限管理员、审计日志。

安全约定：
- 每个操作二次校验权限（不信任 UI 的按钮禁用状态）
- 不提供任何"修改用户资料"的接口（按需求硬性禁止）
- 所有操作写审计日志
"""
from __future__ import annotations

from typing import List

from app.account import auth
from app.account.auth import AuthError
from app.account.db import Database, User
from app.admin.permissions import can


class AdminError(Exception):
    pass


class AdminManager:
    def __init__(self, db: Database, actor: User):
        self.db = db
        self.actor = actor

    # ------------------------------------------------ 权限
    def _need(self, ability: str) -> None:
        if not can(self.actor, ability):
            raise AdminError(f"当前账号无此权限：{ability}")

    @property
    def can_manage(self) -> bool:
        return can(self.actor, "manage_users")

    @property
    def can_create_admin(self) -> bool:
        return can(self.actor, "create_admin")

    # ------------------------------------------------ 查询
    def users(self) -> List[User]:
        self._need("open_admin_panel")
        return self.db.list_users()

    def deleted_users(self) -> List[User]:
        self._need("open_admin_panel")
        return self.db.list_deleted_users()

    def audit_logs(self, limit: int = 300) -> List[dict]:
        self._need("open_admin_panel")
        return self.db.list_audit(limit)

    # ------------------------------------------------ 创建
    def create_user(self, username: str, phone: str, email: str, password: str) -> User:
        """创建普通用户：复用与注册完全一致的逐项校验。"""
        self._need("manage_users")
        try:
            u = auth.register(self.db, username, phone, email, password)
        except AuthError as e:
            raise AdminError(e.message) from e
        self.db.audit(self.actor.username, "admin_create_user",
                      f"创建普通用户 {u.username}（id={u.id}）")
        return u

    def create_admin(self, username: str, phone: str, email: str, password: str) -> User:
        """仅主管理员；新建的一律是受限管理员 sub_admin（不能管理别的账号）。"""
        self._need("create_admin")
        try:
            auth.check_username(self.db, username)
            auth.check_phone(self.db, phone)
            auth.check_email(self.db, email)
            auth.check_password(password)
        except AuthError as e:
            raise AdminError(e.message) from e
        digest, salt = auth.hash_password(password)
        uid = self.db.create_user(username.strip(), digest, salt, phone.strip(),
                                  email.strip(), role="sub_admin")
        self.db.audit(self.actor.username, "admin_create_admin",
                      f"创建受限管理员 {username.strip()}（id={uid}）")
        return self.db.get_user(uid)

    # ------------------------------------------------ 删除 / 恢复
    def delete_user(self, uid: int) -> None:
        """软删除 30 天可恢复；禁止删自己、主管理员、已删除账号。"""
        self._need("manage_users")
        target = self.db.get_user(uid)
        if not target:
            raise AdminError("账号不存在")
        if target.id == self.actor.id:
            raise AdminError("不能删除自己的账号")
        if target.role == "main_admin":
            raise AdminError("主管理员账号不可删除")
        raw = self.db.raw_user(uid)
        if raw and raw["deleted_at"]:
            raise AdminError("该账号已在回收站中")
        self.db.soft_delete_user(uid)
        self.db.audit(self.actor.username, "admin_delete_user",
                      f"软删除用户 {target.username}（id={uid}，30 天内可恢复）")

    def restore_user(self, uid: int) -> None:
        self._need("manage_users")
        target = self.db.raw_user(uid)
        if not target:
            raise AdminError("账号不存在")
        if target["role"] == "main_admin":
            raise AdminError("主管理员无需恢复")
        self.db.restore_user(uid)
        self.db.audit(self.actor.username, "admin_restore_user",
                      f"恢复用户 {target['username']}（id={uid}）")
