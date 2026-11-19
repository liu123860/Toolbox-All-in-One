"""设置系统：默认值 → 主题包 → 用户设置 三层覆盖，改动实时生效（热切换）。

五大维度：样式 / 分类 / 颜色 / 速度 / 效果。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from app.core.paths import db_path

# ---------------------------------------------------------------- 默认值层

DEFAULTS: Dict[str, object] = {
    # 样式
    "style.density": "standard",        # compact / standard / loose
    "style.icon_style": "line",         # line / fill / dual
    "style.theme": "simple_white",      # 主题包：见 THEMES
    # 分类
    "category.mode": "usage",           # usage / frequency / custom
    "category.grid_size": "medium",     # small / medium / large
    # 颜色
    "color.accent": "#2E7CF6",
    "color.mode": "auto",               # auto / light / dark
    # 速度
    "speed.animation": "standard",      # fast / standard / slow / off
    "speed.preload": "lazy",            # lazy / eager（便携版默认 lazy）
    # 效果
    "effects.shadow": True,
    "effects.blur": True,
    "effects.transition": True,
}

# ---------------------------------------------------------------- 主题包层

THEMES: Dict[str, Dict[str, object]] = {
    "simple_white": {"label": "简约白", "color.mode": "light", "color.accent": "#2E7CF6",
                     "style.icon_style": "line"},
    "business_dark": {"label": "商务深", "color.mode": "dark", "color.accent": "#4F9CF9",
                      "style.icon_style": "fill"},
    "eye_green": {"label": "护眼绿", "color.mode": "light", "color.accent": "#2E8B57",
                  "style.icon_style": "line"},
    "warm_orange": {"label": "暖橙", "color.mode": "light", "color.accent": "#E8734A",
                    "style.icon_style": "dual"},
}

DENSITY_FONT = {"compact": 12, "standard": 14, "loose": 16}
DENSITY_PAD = {"compact": 4, "standard": 8, "loose": 12}

ANIM_MS = {"fast": 100, "standard": 250, "slow": 400, "off": 0}

GRID_CELL = {"small": 92, "medium": 116, "large": 148}


def effective(key: str, layers: List[Dict[str, object]]) -> object:
    """从后往前覆盖：默认 ← 主题 ← 用户。"""
    val = DEFAULTS.get(key)
    for layer in layers:
        if key in layer:
            val = layer[key]
    return val


class SettingsManager(QObject):
    """用户设置持久化 + 变更通知。"""

    changed = Signal(str, object)   # (key, value) 热切换信号

    def __init__(self, conn: Optional[sqlite3.Connection] = None, portable: bool = False):
        super().__init__()
        self._conn = conn or sqlite3.connect(db_path())
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
        self._conn.commit()
        self._user: Dict[str, object] = {
            k: json.loads(v) for k, v in self._conn.execute("SELECT key, value FROM settings")
        }
        self._portable = portable
        if portable:  # 便携版：性能优先省资源
            self._user.setdefault("speed.preload", "lazy")

    # ---- 读取
    def theme_layer(self) -> Dict[str, object]:
        theme = str(self._user.get("style.theme", DEFAULTS["style.theme"]))
        return THEMES.get(theme, {})

    def get(self, key: str):
        return effective(key, [self.theme_layer(), self._user])

    def get_int(self, key: str) -> int:
        v = self.get(key)
        return int(v) if v is not None else 0

    def all_user_settings(self) -> Dict[str, object]:
        return dict(self._user)

    # ---- 写入（实时生效）
    def set(self, key: str, value) -> None:
        self._user[key] = value
        self._conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)))
        self._conn.commit()
        self.changed.emit(key, value)

    def apply_theme(self, theme: str) -> None:
        self.set("style.theme", theme)

    def reset_default(self, key: str) -> None:
        self._user.pop(key, None)
        self._conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        self._conn.commit()
        self.changed.emit(key, DEFAULTS.get(key))

    def reset_all(self) -> None:
        for key in list(self._user.keys()):
            self.reset_default(key)

    def export_to(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._user, f, ensure_ascii=False, indent=2)

    def import_from(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in DEFAULTS:
                self.set(k, v)

    # ---- 派生值（供 UI 使用）
    def font_px(self) -> int:
        return DENSITY_FONT.get(str(self.get("style.density")), 14)

    def pad(self) -> int:
        return DENSITY_PAD.get(str(self.get("style.density")), 8)

    def anim_ms(self) -> int:
        return ANIM_MS.get(str(self.get("speed.animation")), 250)

    def grid_cell(self) -> int:
        return GRID_CELL.get(str(self.get("category.grid_size")), 116)
