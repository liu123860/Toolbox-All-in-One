"""容器式组件管理器（用户确认的兜底方案）。

优先级：vendor/<组件>/ 容器 → 系统已安装程序 → 程序自带 Qt 实现（降级）。
GPL 组件一律以子进程方式启动，不与主程序链接，避免许可证传染。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.paths import vendor_dir

# 组件: (显示名, 可执行文件名, vendor 内相对路径, 常见系统安装路径, 许可证)
ENGINE_SPEC: Dict[str, tuple] = {
    "libreoffice": ("LibreOffice", "soffice.exe",
                    "libreoffice/program/soffice.exe",
                    [r"C:\Program Files\LibreOffice\program\soffice.exe",
                     r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"], "MPL 2.0"),
    "vlc": ("VLC", "vlc.exe",
            "vlc/vlc.exe",
            [r"C:\Program Files\VideoLAN\VLC\vlc.exe",
             r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"], "GPL（进程隔离）"),
    "clamav": ("ClamAV", "clamscan.exe",
               "clamav/clamscan.exe",
               [r"C:\Program Files\ClamAV\clamscan.exe"], "GPL（进程隔离）"),
    "7zip": ("7-Zip", "7z.exe",
             "7zip/7z.exe",
             [r"C:\Program Files\7-Zip\7z.exe",
              r"C:\Program Files (x86)\7-Zip\7z.exe"], "LGPL/公有域"),
    "sumatrapdf": ("SumatraPDF", "SumatraPDF.exe",
                   "sumatrapdf/SumatraPDF.exe",
                   [r"C:\Program Files\SumatraPDF\SumatraPDF.exe"], "GPLv3（进程隔离）"),
    "ffmpeg": ("FFmpeg", "ffmpeg.exe",
               "ffmpeg/ffmpeg.exe",
               [], "GPL/LGPL（进程隔离）"),
}


@dataclass
class EngineStatus:
    key: str
    label: str
    path: Optional[str]
    source: str               # 容器 / 系统 / 未安装
    license: str

    @property
    def installed(self) -> bool:
        return self.path is not None


def resolve(key: str) -> Optional[str]:
    spec = ENGINE_SPEC.get(key)
    if not spec:
        return None
    _label, _exe, vendor_rel, sys_paths, _lic = spec
    # 1) vendor 容器
    p = vendor_dir() / vendor_rel
    if p.exists():
        return str(p)
    # 2) 系统安装
    for sys_path in sys_paths:
        if Path(sys_path).exists():
            return sys_path
    found = shutil.which(_exe)
    if found:
        return found
    return None


def status_all() -> List[EngineStatus]:
    out = []
    for key, (label, _exe, vendor_rel, sys_paths, lic) in ENGINE_SPEC.items():
        p = resolve(key)
        if p and str(vendor_dir()) in p:
            source = "容器内置"
        elif p:
            source = "系统已安装"
        else:
            source = "未安装（自动使用内置降级方案）"
        out.append(EngineStatus(key, label, p, source, lic))
    return out


def launch(key: str, args: List[str], timeout: int = 60) -> dict:
    """以子进程方式启动组件（进程隔离，绝不链接库）。"""
    exe = resolve(key)
    if not exe:
        return {"ok": False, "error": f"{ENGINE_SPEC[key][0]} 未安装，请使用内置降级方案"}
    try:
        cp = subprocess.run([exe, *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": cp.returncode == 0, "code": cp.returncode,
                "stdout": cp.stdout or "", "stderr": cp.stderr or ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "组件执行超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def spawn(key: str, args: List[str]) -> Optional[subprocess.Popen]:
    """独立进程启动 GUI 组件（不阻塞主程序）。"""
    exe = resolve(key)
    if not exe:
        return None
    return subprocess.Popen([exe, *args], cwd=str(Path(exe).parent),
                            creationflags=0x00000008 if os.name == "nt" else 0)
