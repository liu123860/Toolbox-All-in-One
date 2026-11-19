"""路径与运行模式：正式版数据放 APPDATA，便携纯净版数据放程序目录（绿色便携）。

打包注意：PyInstaller onedir 模式下 __file__ 位于 _internal 内，必须用
sys.executable 所在目录作为程序根目录，否则 portable.marker / vendor 会找不到。
TOOLBOX_APP_DIR / TOOLBOX_DATA_DIR 供隔离实测使用（不影响正式运行）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "基本工具集齐工具箱"
APP_VERSION = "1.0.0"

_VENDORS_DIR_NAME = "vendor"


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """程序根目录：frozen 时为 exe 所在目录；源码时为包的上两级目录。"""
    override = os.environ.get("TOOLBOX_APP_DIR")
    if override:
        return Path(override).resolve()
    if _frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def is_portable() -> bool:
    """便携模式：命令行 --portable 或程序目录存在 portable.marker。"""
    if "--portable" in sys.argv:
        return True
    return (app_dir() / "portable.marker").exists()


def data_dir() -> Path:
    """数据目录：便携版在程序目录内，正式版在用户 APPDATA。"""
    override = os.environ.get("TOOLBOX_DATA_DIR")
    if override:
        d = Path(override).resolve()
    elif is_portable():
        d = app_dir() / "data"
    else:
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "toolbox.db"


def vendor_dir() -> Path:
    return app_dir() / _VENDORS_DIR_NAME


def patch_path() -> Path:
    """受限代码编辑区产生的配置补丁（数据文件，绝不写源码）。"""
    return data_dir() / "custom_patch.json"


def backup_dir() -> Path:
    """补丁回滚备份目录。"""
    d = data_dir() / "code_backups"
    d.mkdir(parents=True, exist_ok=True)
    return d
