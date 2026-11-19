"""工具注册表：插件式注册 + 分类查询 + 使用统计。"""
from __future__ import annotations

import sqlite3
import time
from collections import defaultdict
from typing import Dict, List, Optional

from app.core.plugin import ToolInfo, ToolUseStat
from app.core.paths import db_path

_CONN = None
_TOOLS: Dict[str, ToolInfo] = {}
_STATS: Dict[str, ToolUseStat] = {}


def register(tool: ToolInfo) -> None:
    _TOOLS[tool.id] = tool
    _STATS.setdefault(tool.id, ToolUseStat(tool.id))


def all_tools() -> List[ToolInfo]:
    return list(_TOOLS.values())


def get(tool_id: str) -> Optional[ToolInfo]:
    return _TOOLS.get(tool_id)


def categories() -> List[str]:
    seen, order = set(), []
    for t in _TOOLS.values():
        if t.category not in seen:
            seen.add(t.category)
            order.append(t.category)
    return order


def tools_by_usage() -> Dict[str, List[ToolInfo]]:
    """按用途分类（默认模式）。"""
    grouped: Dict[str, List[ToolInfo]] = defaultdict(list)
    for t in _TOOLS.values():
        grouped[t.category].append(t)
    return dict(grouped)


def tools_by_frequency() -> Dict[str, List[ToolInfo]]:
    """按使用频率分类：常用（score 前 1/3）/ 较少 / 待发现。"""
    ranked = sorted(_TOOLS.values(), key=lambda t: -_STATS.get(t.id, ToolUseStat(t.id)).score)
    n = max(len(ranked), 1)
    cut1, cut2 = max(1, n // 3), max(2, 2 * n // 3)
    groups: Dict[str, List[ToolInfo]] = defaultdict(list)
    for i, t in enumerate(ranked):
        if i < cut1:
            groups["常用"].append(t)
        elif i < cut2:
            groups["较少使用"].append(t)
        else:
            groups["待发现"].append(t)
    return dict(groups)


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(db_path())
        _CONN.execute(
            "CREATE TABLE IF NOT EXISTS tool_use_stats("
            "tool_id TEXT PRIMARY KEY, open_count INTEGER DEFAULT 0,"
            "total_seconds INTEGER DEFAULT 0)"
        )
        _CONN.commit()
    return _CONN


def load_stats() -> None:
    for tool_id, cnt, secs in _conn().execute(
            "SELECT tool_id, open_count, total_seconds FROM tool_use_stats"):
        st = _STATS.setdefault(tool_id, ToolUseStat(tool_id))
        st.open_count, st.total_seconds = cnt, secs


def record_open(tool_id: str) -> None:
    st = _STATS.setdefault(tool_id, ToolUseStat(tool_id))
    st.open_count += 1
    _conn().execute(
        "INSERT INTO tool_use_stats(tool_id, open_count, total_seconds) VALUES(?,?,?)"
        " ON CONFLICT(tool_id) DO UPDATE SET open_count = excluded.open_count",
        (tool_id, st.open_count, st.total_seconds),
    )
    _conn().commit()


def record_seconds(tool_id: str, seconds: int) -> None:
    st = _STATS.setdefault(tool_id, ToolUseStat(tool_id))
    st.total_seconds += int(seconds)
    _conn().execute(
        "UPDATE tool_use_stats SET total_seconds = ? WHERE tool_id = ?",
        (st.total_seconds, tool_id),
    )
    _conn().commit()
