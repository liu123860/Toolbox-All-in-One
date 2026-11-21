"""图片工具组：图片查看 / 格式转换 / 图片压缩 / 屏幕取色 / 颜色选择器 / 屏幕截图。

全部零第三方依赖（PySide6 内置 QImage/QPixmap）。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage, QCursor
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


# ============================================================ 图片查看器
def create_imageview_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("图片查看器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    path_lab = QLabel("未打开图片")
    img_lab = QLabel("点击「打开图片」查看")
    img_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
    img_lab.setMinimumSize(600, 420)
    out = _out()
    pixmap = {}

    def open_img():
        p, _ = QFileDialog.getOpenFileName(
            w, "打开图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if not p:
            return
        from PySide6.QtGui import QPixmap
        pm = QPixmap(p)
        if pm.isNull():
            out.setText("无法加载该图片")
            return
        pixmap["pm"] = pm
        path_lab.setText(f"{p}　{pm.width()}×{pm.height()}")
        img_lab.setPixmap(pm.scaled(img_lab.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))
        out.setText("已加载")

    def fit():
        if "pm" in pixmap:
            img_lab.setPixmap(pixmap["pm"].scaled(img_lab.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))

    b = QPushButton("打开图片")
    b.clicked.connect(open_img)
    row = QHBoxLayout()
    row.addWidget(b)
    row.addStretch(1)

    lay.addWidget(path_lab)
    lay.addWidget(img_lab, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ 图片格式转换
def create_imageconv_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("图片格式转换 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    src_lab = QLabel("未选择图片")
    fmt = QComboBox()
    fmt.addItems(["PNG", "JPG", "BMP", "WEBP"])
    out = _out()
    state = {"img": QImage()}

    def pick():
        p, _ = QFileDialog.getOpenFileName(
            w, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if not p:
            return
        img = QImage(p)
        if img.isNull():
            out.setText("无法加载图片")
            return
        state["img"] = img
        src_lab.setText(f"{p}　{img.width()}×{img.height()}")

    def convert():
        if state["img"].isNull():
            out.setText("请先选择图片")
            return
        ext = fmt.currentText().lower()
        p, _ = QFileDialog.getSaveFileName(w, "保存为", f"converted.{ext}", f"{fmt.currentText()} (*.{ext})")
        if not p:
            return
        img = state["img"]
        if ext == "jpg" and img.hasAlphaChannel():
            img = img.convertToFormat(QImage.Format.Format_RGB32)
        ok = img.save(p)
        out.setText(f"已保存到 {p}" if ok else "保存失败，格式可能不受支持")

    b1 = QPushButton("选择图片")
    b2 = QPushButton("转换保存")
    b1.clicked.connect(pick)
    b2.clicked.connect(convert)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(QLabel("目标格式"))
    row.addWidget(fmt)
    row.addWidget(b2)
    row.addStretch(1)

    lay.addWidget(src_lab)
    lay.addLayout(row)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 图片压缩
def create_imagezip_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("图片压缩 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    src_lab = QLabel("未选择图片")
    scale = QSpinBox()
    scale.setRange(5, 200)
    scale.setValue(80)
    scale.setSuffix(" %")
    quality = QSpinBox()
    quality.setRange(1, 100)
    quality.setValue(80)
    out = _out()
    state = {"img": QImage(), "path": ""}

    def pick():
        p, _ = QFileDialog.getOpenFileName(
            w, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not p:
            return
        img = QImage(p)
        if img.isNull():
            out.setText("无法加载图片")
            return
        state["img"] = img
        state["path"] = p
        src_lab.setText(f"{p}　{img.width()}×{img.height()}　{Path(p).stat().st_size / 1024:.0f} KB")

    def compress():
        if state["img"].isNull():
            out.setText("请先选择图片")
            return
        p, _ = QFileDialog.getSaveFileName(w, "保存压缩图", "compressed.jpg", "JPEG (*.jpg)")
        if not p:
            return
        img = state["img"]
        w2 = max(1, int(img.width() * scale.value() / 100))
        h2 = max(1, int(img.height() * scale.value() / 100))
        small = img.scaled(w2, h2, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        if small.hasAlphaChannel():
            small = small.convertToFormat(QImage.Format.Format_RGB32)
        ok = small.save(p, "JPG", quality.value())
        if ok:
            out.setText(
                f"原图 {Path(state['path']).stat().st_size / 1024:.0f} KB → "
                f"压缩后 {Path(p).stat().st_size / 1024:.0f} KB　{w2}×{h2}"
            )
        else:
            out.setText("保存失败")

    b1 = QPushButton("选择图片")
    b2 = QPushButton("压缩保存")
    b1.clicked.connect(pick)
    b2.clicked.connect(compress)
    cfg = QHBoxLayout()
    cfg.addWidget(b1)
    cfg.addWidget(QLabel("缩放"))
    cfg.addWidget(scale)
    cfg.addWidget(QLabel("质量"))
    cfg.addWidget(quality)
    cfg.addWidget(b2)
    cfg.addStretch(1)

    lay.addWidget(src_lab)
    lay.addLayout(cfg)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 屏幕取色器
def create_eyedropper_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("屏幕取色器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    swatch = QLabel()
    swatch.setFixedHeight(80)
    swatch.setStyleSheet("background: #888888; border-radius: 6px;")
    out = _out("点击「取色」后取鼠标当前位置颜色")

    def grab():
        screen = QApplication.primaryScreen()
        if not screen:
            out.setText("无法获取屏幕")
            return
        pix = screen.grabWindow(0)
        gp = QCursor.pos()
        img = pix.toImage()
        g = screen.geometry()
        x, y = gp.x() - g.x(), gp.y() - g.y()
        if 0 <= x < img.width() and 0 <= y < img.height():
            c = QColor(img.pixel(x, y))
            hexs = c.name()
            swatch.setStyleSheet(f"background: {hexs}; border-radius: 6px;")
            out.setText(f"HEX：{hexs}　RGB：({c.red()}, {c.green()}, {c.blue()})　坐标：({x}, {y})")
        else:
            out.setText("鼠标不在屏幕范围内")

    b = QPushButton("取当前鼠标位置颜色")
    b.clicked.connect(grab)
    lay.addWidget(swatch)
    lay.addWidget(b)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 颜色选择器
def create_colorpicker_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("颜色选择器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    swatch = QLabel()
    swatch.setFixedHeight(80)
    swatch.setStyleSheet("background: #3498db; border-radius: 6px;")
    hex_in = QLineEdit()
    hex_in.setPlaceholderText("十六进制，如 #3498db")
    out = _out()

    def show_color(c: QColor):
        if not c.isValid():
            return
        hexs = c.name()
        swatch.setStyleSheet(f"background: {hexs}; border-radius: 6px;")
        out.setText(f"HEX：{hexs}　RGB：({c.red()}, {c.green()}, {c.blue()})　HSV：({c.hue()}, {c.saturation()}, {c.value()})")

    def pick():
        c = QColorDialog.getColor(QColor(hex_in.text() or "#3498db"), w)
        if c.isValid():
            hex_in.setText(c.name())
            show_color(c)

    def from_hex():
        c = QColor(hex_in.text())
        if c.isValid():
            show_color(c)
        else:
            out.setText("颜色值无法识别")

    def copy():
        if out.text():
            QApplication.clipboard().setText(out.text())
            out.setText(out.text() + "　（已复制）")

    b1 = QPushButton("选择颜色")
    b2 = QPushButton("按 HEX 解析")
    b3 = QPushButton("复制")
    b1.clicked.connect(pick)
    b2.clicked.connect(from_hex)
    b3.clicked.connect(copy)

    lay.addWidget(swatch)
    lay.addWidget(hex_in)
    lay.addWidget(b1)
    lay.addWidget(b2)
    lay.addWidget(b3)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 屏幕截图
def create_screenshot_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("屏幕截图 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    preview = QLabel("截图预览")
    preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    preview.setMinimumSize(600, 380)
    out = _out()
    state = {"img": QImage()}

    def shoot():
        screen = QApplication.primaryScreen()
        if not screen:
            out.setText("无法获取屏幕")
            return
        pix = screen.grabWindow(0)
        state["img"] = pix.toImage()
        preview.setPixmap(pix.scaled(preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        out.setText(f"已截取全屏 {pix.width()}×{pix.height()}")

    def save():
        if state["img"].isNull():
            out.setText("请先截图")
            return
        p, _ = QFileDialog.getSaveFileName(w, "保存截图", "screenshot.png", "PNG (*.png)")
        if p:
            state["img"].save(p)
            out.setText(f"已保存到 {p}")

    b1 = QPushButton("截取全屏")
    b2 = QPushButton("保存截图")
    b1.clicked.connect(shoot)
    b2.clicked.connect(save)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addStretch(1)

    lay.addWidget(preview, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w
