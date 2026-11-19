"""扫描打印：QPrinter 打印/打印预览（文本与图片）+ Windows WIA 扫描仪（PowerShell COM，带超时）。"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.core.paths import data_dir
from app.tools.impl.common import subtitle

WIA_PS = r"""
$ErrorActionPreference = 'Stop'
try {
  $cd = New-Object -ComObject WIA.CommonDialog
  $img = $cd.ShowAcquireImage()
  if ($img -ne $null) { $img.SaveFile('{out}'); Write-Output 'OK' }
  else { Write-Output 'CANCEL' }
} catch { Write-Output ('ERR:' + $_.Exception.Message) }
"""


class ScanPrintWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("扫描打印 · 基本工具集齐工具箱")
        self.resize(700, 560)
        lay = QVBoxLayout(self)

        bar = QHBoxLayout()
        b = QPushButton("打开文本/图片")
        b.clicked.connect(self._open)
        bar.addWidget(b)
        b2 = QPushButton("打印预览")
        b2.clicked.connect(self._preview)
        bar.addWidget(b2)
        b3 = QPushButton("打印…")
        b3.setObjectName("primary")
        b3.clicked.connect(self._print)
        bar.addWidget(b3)
        b4 = QPushButton("扫描仪扫描")
        b4.clicked.connect(self._scan)
        bar.addWidget(b4)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.lbl = QLabel("可输入文字直接打印，或打开图片/文本；扫描需连接 WIA 兼容扫描仪。")
        self.lbl.setObjectName("subtle")
        lay.addWidget(self.lbl)

        self.editor = QTextEdit()
        lay.addWidget(self.editor, stretch=1)
        lay.addWidget(subtitle("打印走 Windows 打印系统（支持打印成 PDF）；扫描件保存在数据目录「扫描件」文件夹。"))
        self._image: QPixmap | None = None

    def _open(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", "文本/图片 (*.txt *.md *.html *.png *.jpg *.jpeg *.bmp)")
        if not f:
            return
        p = Path(f)
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
            self._image = QPixmap(f)
            self.editor.setHtml(f'<img src="{p.as_uri()}" width="500">')
            self.lbl.setText(f"已载入图片：{p.name}")
        else:
            self._image = None
            self.editor.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
            self.lbl.setText(f"已载入文本：{p.name}")

    def _draw(self, printer: QPrinter):
        with QPainter(printer) as painter:
            rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            if self._image and not self._image.isNull():
                img = self._image.scaled(rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(0, 0, img)
            else:
                doc = QTextDocument()
                doc.setHtml(self.editor.toHtml())
                doc.setPageSize(rect.size())
                doc.drawContents(painter)

    def _preview(self):
        dlg = QPrintPreviewDialog(self)
        dlg.paintRequested.connect(self._draw)
        dlg.exec()

    def _print(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.DialogCode.Accepted:
            self._draw(printer)
            self.lbl.setText("已发送到打印机")

    def _scan(self):
        outdir = data_dir() / "扫描件"
        outdir.mkdir(exist_ok=True)
        out = outdir / f"扫描_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        self.lbl.setText("正在调用扫描仪（最长等待 45 秒）…")
        script = WIA_PS.replace("{out}", str(out).replace("'", "''"))
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=45)
            text = (r.stdout or "").strip()
            if "OK" in text and out.exists():
                self._image = QPixmap(str(out))
                self.editor.setHtml(f'<img src="{out.as_uri()}" width="500">')
                self.lbl.setText(f"扫描完成：{out}")
            elif "CANCEL" in text:
                self.lbl.setText("已取消扫描")
            else:
                self.lbl.setText("未检测到可用扫描仪或 WIA 调用失败：" + text[:120])
        except subprocess.TimeoutExpired:
            self.lbl.setText("扫描等待超时（扫描仪无响应），已自动取消。")
        except Exception as e:
            self.lbl.setText(f"扫描失败：{e}")


def create_widget():
    return ScanPrintWindow()
