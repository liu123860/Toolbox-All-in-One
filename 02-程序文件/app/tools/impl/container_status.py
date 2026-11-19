"""组件管理：查看各开源专业组件是「容器内置 / 系统已安装 / 未安装」，未安装时说明降级方案。"""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.paths import vendor_dir
from app.tools import containers
from app.tools.impl.common import subtitle

FALLBACK = {
    "libreoffice": "内置富文本编辑器 + docx 读写",
    "vlc": "QtMultimedia 内置播放引擎",
    "clamav": "轻量启发式扫描（明确标注非完整引擎）",
    "7zip": "zip/tar/7z 原生 Python 库",
    "sumatrapdf": "QtPdf 内置 PDF 阅读器",
    "ffmpeg": "提示放入容器后可用",
}


class ContainerStatusWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("组件管理 · 基本工具集齐工具箱")
        self.resize(760, 420)
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        b = QPushButton("打开 vendor 容器目录")
        b.setObjectName("primary")
        b.clicked.connect(self._open_vendor)
        row.addWidget(b)
        b2 = QPushButton("刷新状态")
        b2.clicked.connect(self._refresh)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["组件", "状态", "路径", "许可证", "未安装时的降级方案"])
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 210)
        lay.addWidget(self.table)
        lay.addWidget(subtitle(
            "把开源组件的便携版放进 vendor/<组件>/ 目录即被自动接管（详见 vendor/README.md）。"
            "GPL 组件全部以子进程隔离方式调用，避免许可证传染；每个容器必须附 LICENSE 原文。"))
        self._refresh()

    def _refresh(self):
        items = containers.status_all()
        self.table.setRowCount(len(items))
        for i, s in enumerate(items):
            vals = [s.label, s.source, s.path or "—", s.license, FALLBACK.get(s.key, "—")]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))

    def _open_vendor(self):
        d = vendor_dir()
        d.mkdir(exist_ok=True)
        os.startfile(str(d))


def create_widget():
    return ContainerStatusWindow()
