"""认证逻辑：PBKDF2 加盐哈希、注册校验、登录、15 天免登录会话、忘记密码。

按需求：
- 注册：用户名最多 6 个字符 → 手机号 → 邮箱 → 密码（英文字母和数字组成，含字母且含数字）
- 本地管理员账号由首次部署时创建，密码只存哈希
"""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple

from app.account.db import Database, User

PBKDF2_ITERATIONS = 600_000
SESSION_DAYS = 15.0
LOCAL_TOKEN = "local-device"          # 本机免登录令牌

MAIN_ADMIN = {"username": "admin", "phone": "13800000000", "email": "admin@example.com"}


# ---------------------------------------------------------------- 密码哈希

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest, _ = hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


# ---------------------------------------------------------------- 校验规则

USERNAME_MAX = 6
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


class AuthError(Exception):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


def check_username(db: Database, username: str) -> None:
    username = (username or "").strip()
    if not username:
        raise AuthError("username", "请输入用户名")
    if len(username) > USERNAME_MAX:
        raise AuthError("username", f"用户名最多 {USERNAME_MAX} 个字符（当前 {len(username)} 个）")
    if db.find_user_by(username=username):
        raise AuthError("username", "该用户名已被注册")


def check_phone(db: Database, phone: str) -> None:
    phone = (phone or "").strip()
    if not PHONE_RE.match(phone):
        raise AuthError("phone", "手机号格式不正确（11 位大陆手机号）")
    if db.find_user_by(phone=phone):
        raise AuthError("phone", "该手机号已被注册")


def check_email(db: Database, email: str) -> None:
    email = (email or "").strip()
    if not EMAIL_RE.match(email):
        raise AuthError("email", "邮箱格式不正确")
    if db.find_user_by(email=email):
        raise AuthError("email", "该邮箱已被注册")


def check_password(password: str) -> None:
    if not password:
        raise AuthError("password", "请输入密码")
    if not (8 <= len(password) <= 20):
        raise AuthError("password", "密码长度需为 8-20 位")
    if not password.isalnum():
        raise AuthError("password", "密码只能由英文字母和数字组成")
    if password.isdigit() or password.isalpha():
        raise AuthError("password", "密码必须同时包含英文字母和数字")


# ---------------------------------------------------------------- 注册 / 登录

def register(db: Database, username: str, phone: str, email: str, password: str) -> User:
    check_username(db, username)
    check_phone(db, phone)
    check_email(db, email)
    check_password(password)
    digest, salt = hash_password(password)
    uid = db.create_user(username.strip(), digest, salt, phone.strip(), email.strip())
    db.audit(username.strip(), "register", "新用户注册")
    return db.get_user(uid)


def init_main_admin(db: Database, password: str) -> User:
    """首次部署：主管理员账号由用户本人录入密码（系统只存哈希）。"""
    check_password(password)
    if db.find_user_by(username=MAIN_ADMIN["username"]):
        raise AuthError("username", "主管理员已存在")
    digest, salt = hash_password(password)
    uid = db.create_user(MAIN_ADMIN["username"], digest, salt,
                         MAIN_ADMIN["phone"], MAIN_ADMIN["email"], role="main_admin")
    db.audit(MAIN_ADMIN["username"], "init_main_admin", "初始化主管理员")
    return db.get_user(uid)


@dataclass
class AuthSession:
    user: Optional[User]
    keep_days: float = 0.0      # >0 表示记住 N 天（免登录）


def login(db: Database, identifier: str, password: str, keep: bool = False) -> User:
    identifier = (identifier or "").strip()
    user = db.find_user_by(username=identifier, phone=identifier, email=identifier,
                           include_deleted=True)
    if not user:
        raise AuthError("identifier", "账号不存在")
    row = db.find_user_by(username=user.username, include_deleted=True)
    # （find_user_by 返回的 User 不含哈希，直接用底层查询校验）
    import sqlite3  # noqa
    raw = db._conn.execute("SELECT * FROM users WHERE id = ?", (user.id,)).fetchone()
    if raw["deleted_at"]:
        raise AuthError("identifier", "账号已被删除")
    if not verify_password(password, raw["password_hash"], raw["salt"]):
        raise AuthError("password", "密码错误")
    db.audit(user.username, "login", "登录成功" + ("（记住 15 天）" if keep else ""))
    if keep:
        db.save_session(LOCAL_TOKEN, user.id, SESSION_DAYS)
    return user


def guest_login(db: Database) -> User:
    """15 天免登录（游客模式：不注册账号，数据本地保存，15 天内不再弹登录窗）。"""
    token_row = db.load_session(LOCAL_TOKEN)
    if token_row is not None and token_row.role == "guest":
        return token_row
    uid = db.create_user(f"游客_{secrets.token_hex(3)}", "", "", "", "", role="guest")
    db.save_session(LOCAL_TOKEN, uid, SESSION_DAYS)
    return db.get_user(uid)


def restore_session(db: Database) -> Optional[User]:
    """启动时恢复 15 天免登录会话（普通用户或游客）。"""
    user = db.load_session(LOCAL_TOKEN)
    if user and user.role in ("guest", "user", "admin", "main_admin"):
        return user
    return None


def logout(db: Database) -> None:
    db.clear_session(LOCAL_TOKEN)
    db.audit("local", "logout", "退出登录（清除本机会话）")


# ---------------------------------------------------------------- 忘记密码

def reset_password(db: Database, username: str, phone: str, email: str,
                   new_password: str) -> None:
    """演示版校验：用户名 + 手机 + 邮箱三项匹配即允许重置（后续接短信/邮件验证码）。"""
    check_password(new_password)
    user = db.find_user_by(username=username)
    if not user:
        raise AuthError("username", "用户名不存在")
    if (user.phone or "") != phone.strip() or (user.email or "").strip() != email.strip():
        raise AuthError("phone", "手机号或邮箱与账号不匹配")
    digest, salt = hash_password(new_password)
    db.update_password(user.id, digest, salt)
    db.audit(user.username, "reset_password", "通过身份验证重置密码")

