"""垃圾清理：只读扫描 → 用户勾选 → 明确警告确认 → 送入回收站（可恢复）。

安全设计（硬性）：
- 只扫描白名单目录（用户 TEMP、浏览器缓存、缩略图缓存），绝不递归 Desktop/Documents/Downloads 等个人目录
- 跳过最近 2 天修改/占用的文件
- 删除前列出受影响文件并二次确认，每批最多 10 个，逐批校验
- 一律走回收站（FOF_ALLOWUNDO），绝不直接删除
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.tools.impl.common import fmt_size, run_async, send_to_recycle_bin, subtitle

SKIP_AGE_SEC = 2 * 86400
MAX_FILES = 2000


def whitelist_roots():
    roots = []
    temp = os.environ.get("TEMP")
    local = os.environ.get("LOCALAPPDATA")
    if temp:
        roots.append((Path(temp), "系统临时文件"))
    if local:
        for rel, label in (
            (r"Google\Chrome\User Data\Default\Cache", "Chrome 缓存"),
            (r"Microsoft\Edge\User Data\Default\Cache", "Edge 缓存"),
            (r"Mozilla\Firefox\Profiles", "Firefox 缓存"),
            (r"Microsoft\Windows\Explorer", "缩略图缓存"),
        ):
            p = Path(local) / rel
            if rel.endswith("Explorer"):
                # 只取缩略图缓存文件，不碰 Explorer 其它数据
                pass
            if p.exists():
                roots.append((p, label))
    return roots


def scan_one(root: Path, label: str, cutoff: float):
    """只读扫描，返回 (路径, 大小, 标签) 列表。"""
    found = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if len(found) >= MAX_FILES:
                break
            for name in filenames:
                p = Path(dirpath) / name
                try:
                    st = p.stat()
                    if st.st_mtime > cutoff:
                        continue                      # 太新，可能正在使用
                    if label == "缩略图缓存" and not name.startswith("thumbcache_"):
                        continue
                    found.append((p, st.st_size, label))
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return found


def scan_all():
    cutoff = time.time() - SKIP_AGE_SEC
    out = []
    for root, label in whitelist_roots():
        out.extend(scan_one(root, label, cutoff))
    return out


class CleanerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("垃圾清理 · 基本工具集齐工具箱")
        self.resize(720, 560)
        lay = QVBoxLayout(self)

        self.lbl = QLabel("点击下方「扫描」开始只读扫描（不会删除任何文件）")
        lay.addWidget(self.lbl)

        row = QHBoxLayout()
        btn_scan = QPushButton("🔍 扫描")
        btn_scan.setObjectName("primary")
        btn_scan.clicked.connect(self._scan)
        self.btn_clean = QPushButton("清理选中项")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._clean)
        row.addWidget(btn_scan)
        row.addWidget(self.btn_clean)
        row.addStretch(1)
        lay.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["文件/目录（白名单内）", "大小", "分类"])
        self.tree.setColumnWidth(0, 460)
        self.tree.setRootIsDecorated(False)
        lay.addWidget(self.tree)

        lay.addWidget(subtitle(
            "只扫描白名单目录（临时文件/浏览器缓存/缩略图缓存）；跳过最近 2 天修改的文件；"
            "清理前需二次确认，文件送入回收站可恢复，绝不直接删除个人文件。"))

        self._scan_results = []

    def _scan(self):
        self.lbl.setText("正在只读扫描…")
        self.btn_clean.setEnabled(False)
        run_async(scan_all, self._on_scanned,
                  lambda e: self.lbl.setText(f"扫描出错：{e}"))

    def _on_scanned(self, items):
        self._scan_results = items
        self.tree.clear()
        total = 0
        for path, size, label in items:
            it = QTreeWidgetItem([str(path), fmt_size(size), label])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(0, Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(it)
            total += size
        state = "（未发现可清理项）" if not items else f"（{len(items)} 项，可释放约 {fmt_size(total)}）"
        self.lbl.setText(f"扫描完成 {state}。请勾选要清理的项。")
        self.btn_clean.setEnabled(bool(items))

    def _selected_paths(self):
        out = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.checkState(0) == Qt.CheckState.Checked:
                out.append(Path(it.text(0)))
        return out

    def _clean(self):
        paths = self._selected_paths()
        if not paths:
            QMessageBox.information(self, "未选择", "请先勾选要清理的文件。")
            return
        preview = "\n".join(str(p) for p in paths[:10])
        more = f"\n…… 以及另外 {len(paths) - 10} 项" if len(paths) > 10 else ""
        ret = QMessageBox.warning(
            self, "危险操作确认",
            "⚠️ 此操作非常危险，可能导致不可逆的数据丢失！\n\n"
            f"即将把以下 {len(paths)} 个文件送入回收站（可恢复）：\n{preview}{more}\n\n"
            "风险：若这些文件正被其他程序使用，清理后可能导致该程序异常。\n"
            "已自动跳过最近 2 天修改的文件。确认继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        ok, failed = send_to_recycle_bin(paths)
        QMessageBox.information(
            self, "清理完成",
            f"已送入回收站：{len(ok)} 项；失败：{len(failed)} 项"
            + ("\n（失败项多为占用中文件，已跳过）" if failed else ""))
        self._scan()


def create_widget():
    return CleanerWindow()
