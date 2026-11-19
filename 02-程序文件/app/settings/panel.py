"""设置界面：样式 / 分类 / 颜色 / 速度 / 效果 五个页签，改动实时生效。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider, QTabWidget, QVBoxLayout,
)

from app.settings.manager import SettingsManager, THEMES


def _combo(items: dict, current: str) -> QComboBox:
    """items: {value: 显示文案}"""
    box = QComboBox()
    for val, label in items.items():
        box.addItem(label, val)
    idx = list(items.keys()).index(current) if current in items else 0
    box.setCurrentIndex(idx)
    return box


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("设置")
        self.setMinimumSize(520, 480)

        lay = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._tab_style(), "样式")
        tabs.addTab(self._tab_category(), "分类")
        tabs.addTab(self._tab_color(), "颜色")
        tabs.addTab(self._tab_speed(), "速度")
        tabs.addTab(self._tab_effects(), "效果")
        lay.addWidget(tabs)

        bottom = QHBoxLayout()
        btn_export = QPushButton("导出设置")
        btn_export.clicked.connect(self._export)
        btn_import = QPushButton("导入设置")
        btn_import.clicked.connect(self._import)
        btn_reset = QPushButton("全部恢复默认")
        btn_reset.clicked.connect(self._reset_all)
        for b in (btn_export, btn_import, btn_reset):
            bottom.addWidget(b)
        lay.addLayout(bottom)

    # ------------------------------------------------------------ 样式
    def _tab_style(self):
        w = QTabWidget()
        form = QFormLayout(w)
        self.cmb_theme = _combo(
            {k: v["label"] for k, v in THEMES.items()},
            str(self.settings.get("style.theme")))
        self.cmb_theme.currentIndexChanged.connect(
            lambda i: self.settings.apply_theme(self.cmb_theme.itemData(i)))
        form.addRow("主题包", self.cmb_theme)

        self.cmb_density = _combo(
            {"compact": "紧凑", "standard": "标准", "loose": "宽松"},
            str(self.settings.get("style.density")))
        self.cmb_density.currentIndexChanged.connect(
            lambda i: self.settings.set("style.density", self.cmb_density.itemData(i)))
        form.addRow("布局密度", self.cmb_density)

        self.cmb_icon = _combo(
            {"line": "线性", "fill": "填充", "dual": "双色"},
            str(self.settings.get("style.icon_style")))
        self.cmb_icon.currentIndexChanged.connect(
            lambda i: self.settings.set("style.icon_style", self.cmb_icon.itemData(i)))
        form.addRow("图标风格", self.cmb_icon)
        return w

    # ------------------------------------------------------------ 分类
    def _tab_category(self):
        w = QTabWidget()
        form = QFormLayout(w)
        self.cmb_catmode = _combo(
            {"usage": "按用途分组", "frequency": "按使用频率", "custom": "自定义（后续开放拖拽）"},
            str(self.settings.get("category.mode")))
        self.cmb_catmode.currentIndexChanged.connect(
            lambda i: self.settings.set("category.mode", self.cmb_catmode.itemData(i)))
        form.addRow("分类模式", self.cmb_catmode)

        self.cmb_grid = _combo(
            {"small": "小图标", "medium": "中图标", "large": "大图标"},
            str(self.settings.get("category.grid_size")))
        self.cmb_grid.currentIndexChanged.connect(
            lambda i: self.settings.set("category.grid_size", self.cmb_grid.itemData(i)))
        form.addRow("宫格大小", self.cmb_grid)

        hint = QLabel("分类模式下，工具宫格会立即按新方式重新分组。")
        hint.setObjectName("subtle")
        hint.setWordWrap(True)
        form.addRow(hint)
        return w

    # ------------------------------------------------------------ 颜色
    def _tab_color(self):
        w = QTabWidget()
        form = QFormLayout(w)
        self.cmb_mode = _combo(
            {"auto": "跟随系统", "light": "浅色", "dark": "深色"},
            str(self.settings.get("color.mode")))
        self.cmb_mode.currentIndexChanged.connect(
            lambda i: self.settings.set("color.mode", self.cmb_mode.itemData(i)))
        form.addRow("明暗模式", self.cmb_mode)

        row = QHBoxLayout()
        self.lbl_accent = QLabel(str(self.settings.get("color.accent")))
        self.lbl_accent.setMinimumWidth(60)
        btn_accent = QPushButton("选择主题色")
        btn_accent.clicked.connect(self._pick_accent)
        row.addWidget(self.lbl_accent)
        row.addWidget(btn_accent)
        row.addStretch(1)
        form.addRow("主题色", row)
        return w

    def _pick_accent(self):
        from PySide6.QtGui import QColor
        color = QColorDialog.getColor(QColor(str(self.settings.get("color.accent"))), self, "选择主题色")
        if color.isValid():
            self.settings.set("color.accent", color.name())
            self.lbl_accent.setText(color.name())
            self.lbl_accent.setStyleSheet(f"background: {color.name()}; color: white; padding: 4px;")

    # ------------------------------------------------------------ 速度
    def _tab_speed(self):
        w = QTabWidget()
        form = QFormLayout(w)
        self.cmb_anim = _combo(
            {"fast": "快（0.1s）", "standard": "标准（0.25s）", "slow": "慢（0.4s）", "off": "关闭动画"},
            str(self.settings.get("speed.animation")))
        self.cmb_anim.currentIndexChanged.connect(
            lambda i: self.settings.set("speed.animation", self.cmb_anim.itemData(i)))
        form.addRow("动画节奏", self.cmb_anim)

        self.cmb_preload = _combo(
            {"lazy": "懒加载（省内存）", "eager": "预加载（开得快）"},
            str(self.settings.get("speed.preload")))
        self.cmb_preload.currentIndexChanged.connect(
            lambda i: self.settings.set("speed.preload", self.cmb_preload.itemData(i)))
        form.addRow("工具加载策略", self.cmb_preload)
        return w

    # ------------------------------------------------------------ 效果
    def _tab_effects(self):
        w = QTabWidget()
        form = QFormLayout(w)
        for key, label in (("effects.shadow", "窗口阴影"),
                           ("effects.blur", "毛玻璃效果"),
                           ("effects.transition", "转场动效")):
            box = QCheckBox()
            box.setChecked(bool(self.settings.get(key)))
            box.stateChanged.connect(
                lambda state, k=key: self.settings.set(k, state == Qt.CheckState.Checked.value))
            form.addRow(label, box)
        return w

    # ------------------------------------------------------------ 导入导出
    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出设置", "toolbox-settings.json", "JSON (*.json)")
        if path:
            self.settings.export_to(path)

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入设置", "", "JSON (*.json)")
        if path:
            self.settings.import_from(path)

    def _reset_all(self):
        self.settings.reset_all()
