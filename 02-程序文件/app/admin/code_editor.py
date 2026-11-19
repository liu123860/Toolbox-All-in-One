"""受限代码编辑区（阶段 4）。

需求："小改动可执行、大改动禁止，不能在软件内改大源代码"。
实现：编辑器接受的是**受限配置补丁**（JSON 白名单），系统从不执行用户代码；
校验通过后真实作用于界面/设置，自动备份可回滚，全部写审计日志。

坑（已查证）：Python 的 eval/exec + 限制 builtins 可被 ().__class__.__bases__...
内省绕过，因此本实现完全不执行任何 Python 代码。
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSplitter, QTextBrowser, QVBoxLayout,
)

from app.account.db import Database, User
from app.admin import patch_store
from app.admin.permissions import can, patch_scope, role_label
from app.settings.manager import SettingsManager


class _JsonHighlighter(QSyntaxHighlighter):
    """轻量语法高亮：JSON 字符串 / 数字 / 布尔 / null。"""

    def __init__(self, doc):
        super().__init__(doc)
        self._rules = []
        for pattern, color in ((r'"[^"\\]*(\\.[^"\\]*)*"', "#2E7CF6"),
                               (r"\b(true|false|null)\b", "#B45309"),
                               (r"\b-?\d+(\.\d+)?\b", "#15803D")):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            import re
            self._rules.append((re.compile(pattern), fmt))

    def highlightBlock(self, text):
        import re
        for rx, fmt in self._rules:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class CodeEditorDialog(QDialog):
    patch_applied = Signal(dict)

    def __init__(self, db: Database, actor: Optional[User],
                 settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.actor = actor
        self.settings = settings
        self.scope = patch_scope(actor)
        self.setWindowTitle("受限代码编辑区 · 小改动可执行 / 大改动禁止")
        self.resize(940, 620)

        root = QVBoxLayout(self)
        if not can(actor, "open_code_editor"):
            root.addWidget(QLabel("当前账号无权使用代码编辑区。"))
            return

        head = QLabel(f"操作者：{actor.username}（{role_label(actor.role)}）　"
                      f"可改范围：{'外观 + 行为配置' if self.scope == 'full' else '仅外观配置'}")
        head.setObjectName("title")
        root.addWidget(head)
        warn = QLabel("本编辑区只接受受限配置补丁，不执行任何 Python 代码；"
                      "修改核心源代码、账号模块逻辑等大改动一律拒绝，请在开发环境进行。")
        warn.setObjectName("subtle")
        warn.setWordWrap(True)
        root.addWidget(warn)

        splitter = QSplitter()
        left = QVBoxLayout()
        left.addWidget(QLabel("配置补丁编辑器"))
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(patch_store.example_patch())
        self._hl = _JsonHighlighter(self.editor.document())
        left.addWidget(self.editor, stretch=1)
        left_w = _wrap(left)
        splitter.addWidget(left_w)

        right = QVBoxLayout()
        right.addWidget(QLabel("白名单与规则"))
        self.ref = QTextBrowser()
        self.ref.setPlainText(patch_store.whitelist_text())
        right.addWidget(self.ref, stretch=1)
        splitter.addWidget(_wrap(right))
        splitter.setSizes([560, 380])
        root.addWidget(splitter, stretch=1)

        bar = QHBoxLayout()
        self.btn_example = QPushButton("载入示例")
        self.btn_example.clicked.connect(self._load_example)
        self.btn_validate = QPushButton("校验")
        self.btn_validate.clicked.connect(self._validate)
        self.btn_apply = QPushButton("应用（自动备份）")
        self.btn_apply.setObjectName("primary")
        self.btn_apply.setMinimumHeight(44)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_rollback = QPushButton("回滚上一次")
        self.btn_rollback.clicked.connect(self._rollback)
        self.btn_audit = QPushButton("查看审计日志")
        self.btn_audit.clicked.connect(self._show_audit)
        for b in (self.btn_example, self.btn_validate, self.btn_apply,
                  self.btn_rollback, self.btn_audit):
            bar.addWidget(b)
        bar.addStretch(1)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bar.addWidget(btn_close)
        root.addLayout(bar)

        self.output = QTextBrowser()
        self.output.setMaximumHeight(130)
        root.addWidget(self.output)
        self._log("就绪。请编辑补丁后点「校验」，再点「应用」。")

    def _log(self, msg: str):
        self.output.append(msg)

    def _load_example(self):
        self.editor.setPlainText(patch_store.example_patch())
        self._log("已载入示例补丁。")

    def _validate(self):
        try:
            changes = patch_store.validate_patch(self.editor.toPlainText(), self.scope)
            self._log(f"校验通过 ✓ 共 {len(changes)} 项：" +
                      ", ".join(k for k, _ in changes))
            return changes
        except patch_store.PatchError as e:
            self._log(f"校验失败 ✗ {e}")
            return None

    def _apply(self):
        changes = self._validate()
        if not changes:
            return
        try:
            result = patch_store.save_patch(changes, self.actor.username, self.db)
            # 真实生效：设置类 key 立即写入设置系统（触发热切换信号）
            _SETTING_KEYS = {
                "color.accent", "style.theme", "style.density", "category.grid_size",
                "category.mode", "speed.animation", "effects.shadow", "effects.blur",
                "effects.transition",
            }
            for k, v in changes:
                if k in _SETTING_KEYS:
                    self.settings.set(k, v)
            self._log("已应用 ✓ " + ("；备份：" + result["backup"] if result["backup"]
                                   else "；首次应用，无历史备份"))
            self.patch_applied.emit(result["values"])
            QMessageBox.information(self, "应用成功",
                                    "配置补丁已生效（界面实时更新）。\n"
                                    "如需撤销，点「回滚上一次」。")
        except patch_store.PatchError as e:
            self._log(f"应用失败 ✗ {e}")

    def _rollback(self):
        ok = patch_store.rollback(self.db, self.actor.username)
        if ok:
            self._log("回滚成功 ✓ 已恢复上一次配置。")
            self.patch_applied.emit(patch_store.load_patch().get("values", {}))
        else:
            self._log("没有可回滚的历史补丁。")

    def _show_audit(self):
        rows = self.db.list_audit(50)
        self._log("—— 最近审计日志（50 条）——")
        for r in rows:
            if "code_patch" in r["action"]:
                self._log(f"  [{r['action']}] {r['actor']}: {r['detail']}")


def _wrap(layout) -> "QWidget":
    from PySide6.QtWidgets import QWidget
    w = QWidget()
    w.setLayout(layout)
    return w
