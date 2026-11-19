"""工具公共基础设施：异步工作线程、回收站安全删除、通用小组件。"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QLabel, QWidget

# ---------------------------------------------------------------- 异步任务

class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    """线程池任务：func() → result，结果通过信号回主线程。"""

    def __init__(self, func: Callable):
        super().__init__()
        self.func = func
        self.signals = _Signals()

    @Slot()
    def run(self):
        try:
            self.signals.finished.emit(self.func())
        except Exception as e:
            self.signals.failed.emit(str(e))


def run_async(func: Callable, on_done: Callable = None, on_error: Callable = None):
    w = Worker(func)
    if on_done:
        w.signals.finished.connect(on_done)
    if on_error:
        w.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(w)
    return w


# ---------------------------------------------------------------- 回收站删除

FO_DELETE = 0x0003
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def send_to_recycle_bin(paths: list) -> tuple:
    """安全删除：送入 Windows 回收站（可恢复），绝不直接 rm。

    返回 (成功列表, 失败列表)。调用方必须已做白名单校验 + 用户明确确认。
    """
    ok, failed = [], []
    for i in range(0, len(paths), 10):          # 小批次：每批最多 10 个
        batch = [str(p) for p in paths[i:i + 10]]
        buf = "\0".join(batch) + "\0\0"
        op = _SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = buf
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        op.fAnyOperationsAborted = False
        op.hNameMappings = None
        op.lpszProgressTitle = None
        try:
            ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if ret == 0 and not op.fAnyOperationsAborted:
                ok.extend(batch)
            else:
                failed.extend(batch)
        except Exception:
            failed.extend(batch)
    return ok, failed


# ---------------------------------------------------------------- 小组件

def subtitle(text: str, parent: QWidget = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setObjectName("subtle")
    lbl.setWordWrap(True)
    return lbl


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"
