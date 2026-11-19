"""SQLite 数据库层：用户 / 会话 / 审计日志。

安全约定：只存 PBKDF2 加盐哈希，绝不存明文密码。
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import List, Optional

from app.core.paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',       -- user / admin / main_admin / guest
    created_at REAL NOT NULL,
    deleted_at REAL DEFAULT 0                -- 软删除，30 天可恢复
);
CREATE TABLE IF NOT EXISTS sessions(
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    ts REAL NOT NULL
);
"""

SOFT_DELETE_DAYS = 30


@dataclass
class User:
    id: int
    username: str
    phone: Optional[str]
    email: Optional[str]
    role: str
    created_at: float


class Database:
    def __init__(self, path: Optional[str] = None):
        self._conn = sqlite3.connect(path or str(db_path()))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ------------------------------------------------ 用户
    def create_user(self, username: str, password_hash: str, salt: str,
                    phone: Optional[str], email: Optional[str], role: str = "user") -> int:
        cur = self._conn.execute(
            "INSERT INTO users(username, phone, email, password_hash, salt, role, created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (username, phone, email, password_hash, salt, role, time.time()))
        self._conn.commit()
        return cur.lastrowid

    def find_user_by(self, username: Optional[str] = None, phone: Optional[str] = None,
                     email: Optional[str] = None, include_deleted: bool = False) -> Optional[User]:
        for key, val in (("username", username), ("phone", phone), ("email", email)):
            if val:
                row = self._conn.execute(
                    f"SELECT * FROM users WHERE {key} = ?", (val,)).fetchone()
                if row and (include_deleted or row["deleted_at"] == 0):
                    return self._row_to_user(row)
        return None

    def get_user(self, uid: int) -> Optional[User]:
        row = self._conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return self._row_to_user(row) if row else None

    def list_users(self) -> List[User]:
        rows = self._conn.execute(
            "SELECT * FROM users WHERE deleted_at = 0 ORDER BY created_at").fetchall()
        return [self._row_to_user(r) for r in rows]

    def update_password(self, uid: int, password_hash: str, salt: str) -> None:
        self._conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (password_hash, salt, uid))
        self._conn.commit()

    def soft_delete_user(self, uid: int) -> None:
        self._conn.execute("UPDATE users SET deleted_at = ? WHERE id = ?", (time.time(), uid))
        self._conn.commit()

    # ------------------------------------------------ 管理界面所需（阶段 4）
    def list_deleted_users(self) -> List[User]:
        rows = self._conn.execute(
            "SELECT * FROM users WHERE deleted_at > 0 ORDER BY deleted_at DESC").fetchall()
        return [self._row_to_user(r) for r in rows]

    def restore_user(self, uid: int) -> None:
        self._conn.execute("UPDATE users SET deleted_at = 0 WHERE id = ?", (uid,))
        self._conn.commit()

    def list_audit(self, limit: int = 300) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def raw_user(self, uid: int) -> Optional[dict]:
        """仅供管理界面做角色/状态判断，不对外提供任何修改用户资料的接口。"""
        row = self._conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self._conn.close()

    def has_admin(self) -> bool:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE role IN ('admin','main_admin')"
            " AND deleted_at = 0").fetchone()
        return row["c"] > 0

    # ------------------------------------------------ 会话（15 天免登录）
    def save_session(self, token: str, user_id: int, days: float) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions(token, user_id, expires_at) VALUES(?,?,?)",
            (token, user_id, time.time() + days * 86400))
        self._conn.commit()

    def load_session(self, token: str) -> Optional[User]:
        row = self._conn.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        return self.get_user(row["user_id"])

    def clear_session(self, token: str) -> None:
        self._conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self._conn.commit()

    # ------------------------------------------------ 审计
    def audit(self, actor: str, action: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO audit_log(actor, action, detail, ts) VALUES(?,?,?,?)",
            (actor, action, detail, time.time()))
        self._conn.commit()

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(row["id"], row["username"], row["phone"], row["email"],
                    row["role"], row["created_at"])
