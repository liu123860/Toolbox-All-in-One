"""系统工具组：文件哈希 / 批量重命名 / 文件分割合并 / 磁盘空间 / 系统信息 / 进程管理。

全部零第三方依赖（PySide6 + 标准库）。进程管理用 tasklist/taskkill 子进程调用。
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


def _uptime() -> float:
    """返回系统已运行秒数（Windows）。"""
    try:
        import ctypes
        return ctypes.windll.kernel32.GetTickCount64() / 1000.0
    except Exception:
        return 0.0


# ============================================================ 文件哈希
def create_filehash_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("文件哈希校验 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    path_lab = QLabel("未选择文件")
    out = _out()
    state = {"path": ""}

    def pick():
        p, _ = QFileDialog.getOpenFileName(w, "选择文件")
        if p:
            state["path"] = p
            path_lab.setText(f"{p}　{Path(p).stat().st_size / 1024:.1f} KB")

    def calc():
        if not state["path"]:
            out.setText("请先选择文件")
            return
        try:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha256 = hashlib.sha256()
            with open(state["path"], "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
            out.setText(f"MD5：{md5.hexdigest()}\nSHA1：{sha1.hexdigest()}\nSHA256：{sha256.hexdigest()}")
        except Exception as e:
            out.setText(f"计算失败：{e}")

    b1 = QPushButton("选择文件")
    b2 = QPushButton("计算哈希")
    b1.clicked.connect(pick)
    b2.clicked.connect(calc)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addStretch(1)

    lay.addWidget(path_lab)
    lay.addLayout(row)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 批量重命名
def create_batchrename_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("批量重命名 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    dir_lab = QLabel("未选择目录")
    mode = QComboBox()
    mode.addItems(["添加前缀", "添加后缀", "按序号重命名", "替换文字"])
    prefix = QLineEdit()
    prefix.setPlaceholderText("前缀 / 后缀 / 新名前缀 / 被替换文字")
    suffix = QLineEdit()
    suffix.setPlaceholderText("替换为（模式4用）")
    out = _out()
    state = {"dir": ""}

    def pick_dir():
        d = QFileDialog.getExistingDirectory(w, "选择目录")
        if d:
            state["dir"] = d
            n = len([x for x in Path(d).iterdir() if x.is_file()])
            dir_lab.setText(f"{d}　{n} 个文件")

    def run():
        d = state["dir"]
        if not d:
            out.setText("请先选择目录")
            return
        files = sorted([x for x in Path(d).iterdir() if x.is_file()])
        if not files:
            out.setText("目录里没有文件")
            return
        m = mode.currentIndex()
        try:
            changed = 0
            for i, f in enumerate(files, 1):
                old = f.name
                if m == 0:
                    new = prefix.text() + old
                elif m == 1:
                    new = f.stem + prefix.text() + f.suffix
                elif m == 2:
                    new = f"{prefix.text() or 'file'}_{i:03d}{f.suffix}"
                else:
                    new = old.replace(prefix.text(), suffix.text())
                if new != old:
                    f.rename(f.with_name(new))
                    changed += 1
            out.setText(f"完成：{changed} 个文件已重命名（共 {len(files)} 个）")
        except Exception as e:
            out.setText(f"重命名失败：{e}")

    b1 = QPushButton("选择目录")
    b2 = QPushButton("执行重命名")
    b1.clicked.connect(pick_dir)
    b2.clicked.connect(run)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(mode)
    row.addWidget(b2)

    lay.addWidget(dir_lab)
    lay.addWidget(prefix)
    lay.addWidget(suffix)
    lay.addLayout(row)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 文件分割合并
def create_filesplit_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("文件分割合并 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    path_lab = QLabel("未选择文件")
    size_spin = QSpinBox()
    size_spin.setRange(1, 1024)
    size_spin.setValue(10)
    size_spin.setSuffix(" MB")
    out = _out()
    state = {"path": ""}

    def pick():
        p, _ = QFileDialog.getOpenFileName(w, "选择要分割的文件")
        if p:
            state["path"] = p
            path_lab.setText(f"{p}　{Path(p).stat().st_size / 1024 / 1024:.1f} MB")

    def split():
        if not state["path"]:
            out.setText("请先选择文件")
            return
        try:
            chunk = size_spin.value() * 1024 * 1024
            src = Path(state["path"])
            d = QFileDialog.getExistingDirectory(w, "选择分割文件保存目录")
            if not d:
                return
            out_dir = Path(d)
            n = 0
            with open(src, "rb") as f:
                while True:
                    data = f.read(chunk)
                    if not data:
                        break
                    n += 1
                    (out_dir / f"{src.name}.part{n:03d}").write_bytes(data)
            out.setText(f"分割完成：{n} 个分卷，保存在 {d}")
        except Exception as e:
            out.setText(f"分割失败：{e}")

    def merge():
        paths, _ = QFileDialog.getOpenFileNames(w, "选择所有分卷（按顺序）")
        if not paths:
            return
        try:
            paths = sorted(paths)
            save, _ = QFileDialog.getSaveFileName(w, "合并保存为", "merged.bin")
            if not save:
                return
            with open(save, "wb") as out_f:
                for p in paths:
                    out_f.write(Path(p).read_bytes())
            out.setText(f"合并完成：{len(paths)} 个分卷 → {save}")
        except Exception as e:
            out.setText(f"合并失败：{e}")

    b1 = QPushButton("选择文件")
    b2 = QPushButton("分割")
    b3 = QPushButton("合并")
    b1.clicked.connect(pick)
    b2.clicked.connect(split)
    b3.clicked.connect(merge)
    cfg = QHBoxLayout()
    cfg.addWidget(b1)
    cfg.addWidget(QLabel("分卷大小"))
    cfg.addWidget(size_spin)
    cfg.addWidget(b2)
    cfg.addWidget(b3)
    cfg.addStretch(1)

    lay.addWidget(path_lab)
    lay.addLayout(cfg)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 磁盘空间
def create_diskusage_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("磁盘空间分析 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    lst = QListWidget()
    out = _out()

    def scan():
        lst.clear()
        total_all = used_all = free_all = 0
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if not os.path.exists(drive):
                continue
            try:
                total, used, free = shutil.disk_usage(drive)
                total_all += total
                used_all += used
                free_all += free
                pct = used / total * 100 if total else 0
                item = QListWidgetItem(
                    f"{drive}　总计 {total / 1024 ** 3:.1f} GB　已用 {used / 1024 ** 3:.1f} GB"
                    f"　剩余 {free / 1024 ** 3:.1f} GB　占用 {pct:.1f}%"
                )
                if pct > 90:
                    item.setForeground(Qt.GlobalColor.red)
                lst.addItem(item)
            except Exception:
                continue
        out.setText(
            f"全部磁盘：总计 {total_all / 1024 ** 4:.2f} TB　"
            f"已用 {used_all / 1024 ** 4:.2f} TB　剩余 {free_all / 1024 ** 4:.2f} TB"
        )

    b = QPushButton("扫描磁盘")
    b.clicked.connect(scan)
    lay.addWidget(lst, stretch=1)
    lay.addWidget(b)
    lay.addWidget(out)
    return w


# ============================================================ 系统信息
def create_sysinfo_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("系统信息 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    out = _out("点击按钮查看系统信息")

    def show_info():
        try:
            boot = datetime.fromtimestamp(time.time() - _uptime()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            boot = "未知"
        lines = [
            f"操作系统：{platform.system()} {platform.release()}（{platform.version()}）",
            f"计算机名：{platform.node()}",
            f"处理器：{platform.processor() or '未知'}",
            f"架构：{platform.machine()}　Python 位数：{platform.architecture()[0]}",
            f"Python 版本：{platform.python_version()}　实现：{platform.python_implementation()}",
            f"系统启动时间：{boot}",
        ]
        try:
            import ctypes
            class _MEM(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _MEM()
            m.dwLength = ctypes.sizeof(_MEM)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                lines.append(f"物理内存：总计 {m.ullTotalPhys / 1024 ** 3:.1f} GB　可用 {m.ullAvailPhys / 1024 ** 3:.1f} GB")
        except Exception:
            pass
        out.setText("\n".join(lines))

    b = QPushButton("查看系统信息")
    b.clicked.connect(show_info)
    lay.addWidget(b)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 进程管理
def create_procman_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("进程管理 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    lst = QListWidget()
    out = _out()

    def refresh():
        lst.clear()
        try:
            r = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000,
            )
            for line in r.stdout.splitlines()[:300]:
                parts = line.split('","')
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    pid = parts[1].strip('"')
                    lst.addItem(QListWidgetItem(f"{name}　PID {pid}"))
            out.setText(f"共 {lst.count()} 个进程（显示前 300 个）")
        except Exception as e:
            out.setText(f"获取进程失败：{e}")

    def kill():
        it = lst.currentItem()
        if not it:
            out.setText("请先选择一个进程")
            return
        pid = it.text().rsplit(" ", 1)[-1].strip()
        if not pid.isdigit():
            out.setText("无法解析 PID")
            return
        try:
            r = subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000,
            )
            out.setText(r.stdout.strip() or r.stderr.strip() or "已发送结束命令")
            refresh()
        except Exception as e:
            out.setText(f"结束进程失败：{e}")

    b1 = QPushButton("刷新进程")
    b2 = QPushButton("结束选中进程")
    b1.clicked.connect(refresh)
    b2.clicked.connect(kill)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addStretch(1)

    lay.addWidget(lst, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w
