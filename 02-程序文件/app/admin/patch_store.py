"""受限配置补丁存储（阶段 4 代码编辑区的数据层）。

安全设计（对应"小改动可执行、大改动禁止"）：
- 管理员在编辑器里写的不是 Python 代码，而是受限 JSON 配置补丁
- 系统**从不执行**用户提交的代码：不 eval / 不 exec / 不 import / 不写源码
- 只允许白名单 key + 类型/取值校验，写入的是独立数据文件 custom_patch.json
- 每次应用前自动备份，可一键回滚；全部操作写审计日志
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple

from app.core.paths import backup_dir, patch_path

# key -> (类型, 允许值或最大值, 范围 scope, 说明)
SPEC: Dict[str, dict] = {
    "ui.welcome_text":     {"type": "str", "max": 40, "scope": "appearance", "desc": "顶栏欢迎文案"},
    "ui.footer_text":      {"type": "str", "max": 60, "scope": "appearance", "desc": "状态栏文案"},
    "color.accent":        {"type": "color", "scope": "appearance", "desc": "主题色 #RRGGBB"},
    "style.theme":         {"type": "enum", "choices": ["simple_white", "business_dark",
                                                         "eye_green", "warm_orange"],
                            "scope": "appearance", "desc": "主题包"},
    "style.density":       {"type": "enum", "choices": ["compact", "standard", "loose"],
                            "scope": "appearance", "desc": "界面密度"},
    "category.grid_size":  {"type": "enum", "choices": ["small", "medium", "large"],
                            "scope": "appearance", "desc": "工具宫格大小"},
    "category.mode":       {"type": "enum", "choices": ["usage", "frequency"],
                            "scope": "appearance", "desc": "分类方式"},
    "speed.animation":     {"type": "enum", "choices": ["fast", "standard", "slow", "off"],
                            "scope": "appearance", "desc": "动画节奏"},
    "effects.shadow":      {"type": "bool", "scope": "appearance", "desc": "阴影效果"},
    "effects.blur":        {"type": "bool", "scope": "appearance", "desc": "毛玻璃效果"},
    "effects.transition":  {"type": "bool", "scope": "appearance", "desc": "转场效果"},
}

# 大改动特征：出现即硬拒绝
BIG_CHANGE_PATTERNS = [
    r"\bimport\s+\w", r"\bfrom\s+\w+\s+import\b", r"\bexec\s*\(", r"\beval\s*\(",
    r"\bcompile\s*\(", r"\bopen\s*\(", r"__\w+__", r"\bos\.", r"\bsys\.",
    r"\bsubprocess\b", r"\bshutil\b", r"\bctypes\b", r"\bglobals\s*\(",
    r"\blocals\s*\(", r"\bgetattr\s*\(", r"\bsetattr\s*\(", r"\bdelattr\s*\(",
    r"\.py\b", r"core/", r"account/", r"admin/", r"\.db\b",
    r"while\s+True", r"\blambda\b", r"\bclass\s+\w", r"\bdef\s+\w",
]

MAX_TEXT = 4000
MAX_CHANGES = 10


class PatchError(Exception):
    pass


def example_patch() -> str:
    return json.dumps({
        "type": "toolbox_patch_v1",
        "changes": [
            {"key": "ui.welcome_text", "value": "欢迎使用工具箱"},
            {"key": "color.accent", "value": "#E8734A"}
        ]
    }, ensure_ascii=False, indent=2)


def whitelist_text() -> str:
    lines = ["允许的 key（" + str(len(SPEC)) + " 项）："]
    for k, v in SPEC.items():
        extra = ""
        if v["type"] == "enum":
            extra = " = " + " / ".join(v["choices"])
        elif v["type"] == "str":
            extra = f"（文本 ≤{v['max']} 字）"
        elif v["type"] == "bool":
            extra = "（true / false）"
        elif v["type"] == "color":
            extra = "（#RRGGBB）"
        lines.append(f"  {k}{extra}  — {v['desc']} [{v['scope']}]")
    lines.append("\n禁止：任何 Python 代码、import、文件/数据库操作、修改源代码。")
    return "\n".join(lines)


def validate_patch(text: str, scope: str = "full") -> List[Tuple[str, object]]:
    """校验补丁，返回 [(key, value)]；任何不合规抛 PatchError。"""
    if scope not in ("full", "appearance"):
        raise PatchError("当前账号无权使用代码编辑区")
    if len(text) > MAX_TEXT:
        raise PatchError(f"内容过长（>{MAX_TEXT} 字符），大改动请在开发环境进行")

    for pat in BIG_CHANGE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            raise PatchError("检测到代码/文件/数据库级改动 —— 大改动禁止在软件内修改，"
                             "请在开发环境进行")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PatchError("不是合法的 JSON 配置补丁：" + e.msg) from e
    if not isinstance(data, dict) or set(data.keys()) != {"type", "changes"}:
        raise PatchError("补丁格式必须是 {\"type\": \"toolbox_patch_v1\", \"changes\": [...]}")
    if data["type"] != "toolbox_patch_v1":
        raise PatchError("补丁 type 不正确")
    changes = data["changes"]
    if not isinstance(changes, list) or not changes:
        raise PatchError("changes 必须是非空数组")
    if len(changes) > MAX_CHANGES:
        raise PatchError(f"单次最多改 {MAX_CHANGES} 项（大改动请在开发环境进行）")

    out: List[Tuple[str, object]] = []
    seen = set()
    for i, ch in enumerate(changes, 1):
        if not isinstance(ch, dict) or set(ch.keys()) != {"key", "value"}:
            raise PatchError(f"第 {i} 项只能包含 key 和 value")
        key, val = ch["key"], ch["value"]
        if key in seen:
            raise PatchError(f"第 {i} 项 key 重复：{key}")
        seen.add(key)
        spec = SPEC.get(key)
        if not spec:
            raise PatchError(f"第 {i} 项 key 不在白名单：{key}")
        if spec["scope"] == "behavior" and scope != "full":
            raise PatchError(f"第 {i} 项「{key}」属于行为类配置，受限管理员无权修改")
        t = spec["type"]
        if t == "str":
            if not isinstance(val, str) or len(val) > spec["max"]:
                raise PatchError(f"第 {i} 项必须是 ≤{spec['max']} 字的文本")
        elif t == "bool":
            if not isinstance(val, bool):
                raise PatchError(f"第 {i} 项必须是 true / false")
        elif t == "enum":
            if val not in spec["choices"]:
                raise PatchError(f"第 {i} 项取值须为：{' / '.join(spec['choices'])}")
        elif t == "color":
            if not isinstance(val, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", val):
                raise PatchError(f"第 {i} 项必须是 #RRGGBB 颜色")
        out.append((key, val))
    return out


def load_patch() -> dict:
    p = patch_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def patch_value(key: str, default=None):
    return load_patch().get("values", {}).get(key, default)


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def list_backups() -> List[Path]:
    return sorted(backup_dir().glob("custom_patch_*.json"), reverse=True)


def save_patch(changes: List[Tuple[str, object]], actor: str, db=None) -> dict:
    """应用补丁：先备份 → 合并写入 → 审计。返回本次结果。"""
    cur = load_patch()
    backup = ""
    if cur:
        name = f"custom_patch_{time.strftime('%Y%m%d_%H%M%S')}_{len(list_backups()) + 1}.json"
        dest = backup_dir() / name
        shutil.copy2(patch_path(), dest)
        backup = str(dest)
    values = dict(cur.get("values", {}))
    for k, v in changes:
        values[k] = v
    _atomic_write(patch_path(), {
        "type": "toolbox_patch_v1",
        "updated_at": time.time(),
        "updated_by": actor,
        "values": values,
    })
    if db is not None:
        db.audit(actor, "code_patch_apply",
                 "应用配置补丁：" + ", ".join(f"{k}={v}" for k, v in changes))
    return {"applied": changes, "backup": backup, "values": values}


def rollback(db=None, actor: str = "") -> bool:
    """回滚到最近一次备份；无备份时删除补丁（恢复默认）。"""
    backups = list_backups()
    if backups:
        shutil.copy2(backups[0], patch_path())
    elif patch_path().exists():
        patch_path().unlink()
    else:
        return False
    if db is not None:
        db.audit(actor, "code_patch_rollback", "回滚配置补丁")
    return True
