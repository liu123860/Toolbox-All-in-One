"""主窗口：顶栏（搜索/账号/设置/管理入口）+ 侧栏分类 + 工具宫格 + 状态栏。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from app.account.auth import logout
from app.account.db import Database, User
from app.account.ui import LoginDialog
from app.admin.permissions import can
from app.core.paths import APP_VERSION
from app.core.plugin import ToolInfo
from app.settings.manager import SettingsManager
from app.settings.panel import SettingsDialog
from app.settings.theme import build_qss
from app.tools import registry


class FlowLayout(QLayout):
    """流式布局：子项从左到右等距排列，靠左对齐，排满一行自动换行。

    替换原先固定 5 列的 QGridLayout —— 后者在栏目工具少时列宽拉伸、
    按钮居中且空隙巨大。本布局保持按钮固定尺寸，空隙恒定等距，右侧留白。
    参考 Qt 官方 FlowLayout 示例，spacing 固定为 12px。
    """

    def __init__(self, parent=None, spacing=12):
        super().__init__(parent)
        self._spacing = spacing
        self._items = []
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        x = rect.x() + left
        y = rect.y() + top
        line_height = 0
        space = self._spacing

        for item in self._items:
            size = item.sizeHint()
            next_x = x + size.width() + space
            if next_x - space > rect.right() - right and line_height > 0:
                x = rect.x() + left
                y += line_height + space
                next_x = x + size.width() + space
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), size))
            x = next_x
            line_height = max(line_height, size.height())

        return y + line_height + bottom - rect.y()


class PlaceholderToolWindow(QWidget):
    """工具未实现时的占位窗口（当前 50 个工具均有真实实现）。"""

    def __init__(self, tool: ToolInfo):
        super().__init__()
        self.setWindowTitle(f"{tool.name} · 基本工具集齐工具箱")
        self.resize(520, 380)
        lay = QVBoxLayout(self)
        title = QLabel(f"{tool.icon}  {tool.name}")
        title.setObjectName("title")
        lay.addWidget(title)
        desc = QLabel(f"{tool.desc}\n\n分类：{tool.category}")
        desc.setObjectName("subtle")
        desc.setWordWrap(True)
        lay.addWidget(desc)
        lay.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self, db: Database, settings: SettingsManager,
                 user: Optional[User]):
        super().__init__()
        self.db = db
        self.settings = settings
        self.user = user
        self.setWindowTitle(f"基本工具集齐工具箱 v{APP_VERSION}")
        self.resize(1080, 700)

        self._open_windows = {}
        self._build_ui()
        self._bind_settings()
        self._apply_theme()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 顶栏
        top = QFrame()
        top.setObjectName("topbar")
        toplay = QHBoxLayout(top)
        toplay.setContentsMargins(16, 10, 16, 10)

        self.lbl_logo = QLabel("🧰 工具箱")
        self.lbl_logo.setObjectName("title")
        toplay.addWidget(self.lbl_logo)

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("搜索工具…")
        self.ed_search.setFixedWidth(240)
        self.ed_search.textChanged.connect(self._refresh_grid)
        toplay.addWidget(self.ed_search)
        toplay.addStretch(1)

        self.btn_admin = QToolButton()
        self.btn_admin.setText("管理")
        self.btn_admin.setToolTip("图形化管理界面")
        self.btn_admin.clicked.connect(self._show_admin)
        self.btn_admin.hide()
        toplay.addWidget(self.btn_admin)

        self.btn_code = QToolButton()
        self.btn_code.setText("代码区")
        self.btn_code.setToolTip("受限代码编辑区（小改动可执行 / 大改动禁止）")
        self.btn_code.clicked.connect(self._show_code_editor)
        self.btn_code.hide()
        toplay.addWidget(self.btn_code)

        self.btn_account = QPushButton("登录")
        self.btn_account.setObjectName("accent")
        self.btn_account.clicked.connect(self._account_clicked)
        toplay.addWidget(self.btn_account)

        btn_settings = QToolButton()
        btn_settings.setText("⚙ 设置")
        btn_settings.clicked.connect(self._show_settings)
        toplay.addWidget(btn_settings)

        root.addWidget(top)

        # ---- 主体：侧栏 + 内容
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)

        self.lst_cat = QListWidget()
        self.lst_cat.setObjectName("sidebar")
        self.lst_cat.setFixedWidth(160)
        self.lst_cat.currentRowChanged.connect(lambda _: self._refresh_grid())
        body.addWidget(self.lst_cat)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid_lay = QVBoxLayout(self.grid_host)
        self.scroll.setWidget(self.grid_host)
        body.addWidget(self.scroll, stretch=1)

        root.addLayout(body, stretch=1)

        # ---- 状态栏
        self.statusBar().addPermanentWidget(QLabel(f"v{APP_VERSION}"))
        self.lbl_footer = QLabel("")
        self.lbl_footer.setObjectName("subtle")
        self.statusBar().addWidget(self.lbl_footer)

        self.setCentralWidget(central)
        self._refresh_sidebar()
        self._refresh_grid()
        self._refresh_account()
        self._apply_patch_text()

    # ---------------------------------------------------------------- 数据刷新
    def _grouped_tools(self):
        mode = str(self.settings.get("category.mode"))
        if mode == "frequency":
            return registry.tools_by_frequency()
        return registry.tools_by_usage()

    def _refresh_sidebar(self):
        # 阻断 currentRowChanged：避免初始化/主题切换时重复触发 _refresh_grid
        from PySide6.QtCore import QSignalBlocker
        _blocker = QSignalBlocker(self.lst_cat)
        self.lst_cat.clear()
        item = QListWidgetItem("全部")
        self.lst_cat.addItem(item)
        for cat in self._grouped_tools().keys():
            self.lst_cat.addItem(QListWidgetItem(cat))
        self.lst_cat.setCurrentRow(0)

    def _refresh_grid(self):
        while self.grid_lay.count():
            item = self.grid_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        kw = self.ed_search.text().strip().lower()
        cat_row = self.lst_cat.currentRow()
        cat_name = self.lst_cat.item(cat_row).text() if cat_row >= 0 else "全部"

        grouped = self._grouped_tools()
        cell = self.settings.grid_cell()

        for group, tools in grouped.items():
            if cat_name not in ("全部", group):
                continue
            visible = [t for t in tools
                       if not kw or kw in t.name.lower() or kw in t.desc.lower()]
            if not visible:
                continue
            header = QLabel(group)
            header.setObjectName("subtle")
            self.grid_lay.addWidget(header)

            row = QFrame()
            row.setObjectName("card")
            grid = FlowLayout(row, spacing=12)  # 靠左对齐、等距空隙、自动换行
            grid.setContentsMargins(8, 8, 8, 8)
            for i, t in enumerate(visible):
                btn = QPushButton(f"{t.icon}\n{t.name}")
                btn.setFixedSize(cell, cell)
                btn.setToolTip(t.desc)
                btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                btn.clicked.connect(lambda checked=False, tool=t: self._open_tool(tool))
                grid.addWidget(btn)
            self.grid_lay.addWidget(row)

        self.grid_lay.addStretch(1)

    def _refresh_account(self):
        if self.user:
            self.btn_account.setText(self.user.username)
            if self.user.role in ("admin", "main_admin"):
                self.btn_admin.show()
                self.btn_code.show()
        else:
            self.btn_account.setText("登录")
            self.btn_admin.hide()
            self.btn_code.hide()

    # ---------------------------------------------------------------- 动作
    def _open_tool(self, tool: ToolInfo):
        registry.record_open(tool.id)
        if tool.id in self._open_windows:
            win = self._open_windows[tool.id]
            win.show()
            win.raise_()
            win.activateWindow()
            return

        widget = tool.create_widget() if tool.factory else None
        if widget is None:
            widget = PlaceholderToolWindow(tool)
        widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._open_windows[tool.id] = widget
        widget.destroyed.connect(lambda *_: self._open_windows.pop(tool.id, None))
        widget.show()

    def _account_clicked(self):
        if self.user:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            menu.addAction("退出登录", self._logout)
            menu.exec(self.mapToGlobal(self.btn_account.pos()))
        else:
            dlg = LoginDialog(self.db, self)
            if dlg.exec() == LoginDialog.DialogCode.Accepted and dlg.user:
                self.user = dlg.user
                self.db.audit(self.user.username, "auto_session", "登录后进入主界面")
        self._refresh_account()

    def _logout(self):
        logout(self.db)
        self.user = None
        self._refresh_account()

    def _show_settings(self):
        SettingsDialog(self.settings, self).exec()

    def _show_admin(self):
        if not can(self.user, "open_admin_panel"):
            QMessageBox.warning(self, "无权限", "当前账号无权打开管理界面。")
            return
        from app.admin.ui import AdminDialog
        AdminDialog(self.db, self.user, self).exec()
        self._refresh_account()

    def _show_code_editor(self):
        if not can(self.user, "open_code_editor"):
            QMessageBox.warning(self, "无权限", "当前账号无权使用代码编辑区。")
            return
        from app.admin.code_editor import CodeEditorDialog
        dlg = CodeEditorDialog(self.db, self.user, self.settings, self)
        dlg.patch_applied.connect(self._on_patch_applied)
        dlg.exec()

    def _on_patch_applied(self, values: dict):
        self._apply_patch_text()
        self._apply_theme()
        self._refresh_sidebar()
        self._refresh_grid()
        self._refresh_account()

    def _apply_patch_text(self):
        """读取受限补丁里的界面文案（数据文件，不是源码）。"""
        from app.admin.patch_store import patch_value
        self.lbl_logo.setText(str(patch_value("ui.welcome_text", "🧰 工具箱")))
        self.lbl_footer.setText(str(patch_value("ui.footer_text", "")))

    # ---------------------------------------------------------------- 热切换
    def _bind_settings(self):
        self.settings.changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value):
        if key.startswith(("color.", "style.density", "effects.", "style.theme")):
            self._apply_theme()
        if key.startswith(("category.", "style.theme")):
            self._refresh_sidebar()
            self._refresh_grid()

    def _apply_theme(self):
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            qapp.setStyleSheet(build_qss(self.settings))
