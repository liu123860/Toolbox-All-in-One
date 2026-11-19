"""图形化管理界面（阶段 4）。

- 用户列表（搜索/角色筛选）、创建用户、删除（二次确认+软删除）、回收站恢复、审计日志
- 权限按钮按角色启用/禁用，后端 AdminManager 再做一次权限校验
- **没有任何"修改用户资料"的入口**（按需求硬性禁止）
"""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.account.db import Database, User
from app.admin.manager import AdminError, AdminManager
from app.admin.permissions import describe, role_label


class CreateUserDialog(QDialog):
    """创建账号：字段与注册流程完全一致（用户名≤6字符→手机→邮箱→密码）。"""

    def __init__(self, parent=None, is_admin: bool = False):
        super().__init__(parent)
        self.setWindowTitle("创建" + ("受限管理员" if is_admin else "普通用户"))
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        if is_admin:
            hint = QLabel("新建管理员权限更小：不能管理别的账号、不能创建管理员。")
            hint.setObjectName("subtle")
            hint.setWordWrap(True)
            lay.addWidget(hint)
        form = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_name.setMaxLength(6)
        self.ed_phone = QLineEdit()
        self.ed_phone.setPlaceholderText("11 位手机号")
        self.ed_mail = QLineEdit()
        self.ed_pwd = QLineEdit()
        self.ed_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pwd2 = QLineEdit()
        self.ed_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("用户名(≤6字符)", self.ed_name)
        form.addRow("手机号", self.ed_phone)
        form.addRow("邮箱", self.ed_mail)
        form.addRow("密码", self.ed_pwd)
        form.addRow("确认密码", self.ed_pwd2)
        lay.addLayout(form)
        note = QLabel("密码 8-20 位，英文字母+数字，且同时含字母和数字")
        note.setObjectName("subtle")
        note.setWordWrap(True)
        lay.addWidget(note)

        row = QHBoxLayout()
        self.btn_ok = QPushButton("创 建")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.setMinimumHeight(44)
        self.btn_ok.clicked.connect(self._submit)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(self.btn_ok)
        row.addWidget(btn_cancel)
        lay.addLayout(row)

        self.values: Optional[tuple] = None

    def _submit(self):
        if self.ed_pwd.text() != self.ed_pwd2.text():
            QMessageBox.warning(self, "输入有误", "两次输入的密码不一致")
            return
        self.values = (self.ed_name.text(), self.ed_phone.text(),
                       self.ed_mail.text(), self.ed_pwd.text())
        self.accept()


class AdminDialog(QDialog):
    def __init__(self, db: Database, actor: User, parent=None):
        super().__init__(parent)
        self.db = db
        self.actor = actor
        self.mgr = AdminManager(db, actor)
        self.setWindowTitle("图形化管理界面")
        self.resize(860, 600)

        root = QVBoxLayout(self)
        head = QLabel(f"当前管理员：{actor.username}（{role_label(actor.role)}）")
        head.setObjectName("title")
        root.addWidget(head)
        cap = QLabel("权限：" + describe(actor) + "　｜　不可修改任何用户资料")
        cap.setObjectName("subtle")
        cap.setWordWrap(True)
        root.addWidget(cap)

        # ---- 工具栏
        bar = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("搜索用户名 / 手机 / 邮箱")
        self.ed_search.textChanged.connect(self._refresh_users)
        bar.addWidget(self.ed_search, stretch=1)
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["全部角色", "普通用户", "游客", "管理员", "受限管理员", "主管理员"])
        self.cmb_role.currentTextChanged.connect(self._refresh_users)
        bar.addWidget(self.cmb_role)
        self.btn_new_user = QPushButton("创建用户")
        self.btn_new_user.clicked.connect(self._create_user)
        bar.addWidget(self.btn_new_user)
        self.btn_new_admin = QPushButton("创建管理员")
        self.btn_new_admin.clicked.connect(self._create_admin)
        self.btn_new_admin.setEnabled(self.mgr.can_create_admin)
        bar.addWidget(self.btn_new_admin)
        self.btn_del = QPushButton("删除选中")
        self.btn_del.clicked.connect(self._delete_user)
        bar.addWidget(self.btn_del)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._refresh_all)
        bar.addWidget(self.btn_refresh)
        root.addLayout(bar)

        # ---- 三个页签
        self.tabs = QTabWidget()
        self.tbl_users = self._make_table(["ID", "用户名", "手机", "邮箱", "角色", "注册时间"])
        self.tbl_deleted = self._make_table(["ID", "用户名", "角色", "删除时间"])
        self.tbl_audit = self._make_table(["ID", "操作人", "动作", "详情", "时间"])
        self.tabs.addTab(self.tbl_users, "用户列表")
        self.tabs.addTab(self.tbl_deleted, "回收站（30 天内可恢复）")
        self.tabs.addTab(self.tbl_audit, "审计日志")
        root.addWidget(self.tabs, stretch=1)

        bottom = QHBoxLayout()
        self.btn_restore = QPushButton("恢复选中账号")
        self.btn_restore.clicked.connect(self._restore_user)
        bottom.addWidget(self.btn_restore)
        bottom.addStretch(1)
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtle")
        bottom.addWidget(self.lbl_status)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._apply_permissions()
        self._refresh_all()

    @staticmethod
    def _make_table(headers) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)   # 只读
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return t

    def _apply_permissions(self):
        allowed = self.mgr.can_manage
        self.btn_new_user.setEnabled(allowed)
        self.btn_del.setEnabled(allowed)
        self.btn_restore.setEnabled(allowed)

    def _fill(self, table: QTableWidget, rows):
        table.setRowCount(0)
        for r, cells in enumerate(rows):
            table.insertRow(r)
            for c, val in enumerate(cells):
                table.setItem(r, c, QTableWidgetItem(str(val)))

    @staticmethod
    def _ts(t: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "-"

    def _refresh_users(self):
        kw = self.ed_search.text().strip().lower()
        role_filter = {"普通用户": "user", "游客": "guest", "管理员": "admin",
                       "受限管理员": "sub_admin", "主管理员": "main_admin"}.get(
                           self.cmb_role.currentText())
        rows = []
        for u in self.mgr.users():
            if role_filter and u.role != role_filter:
                continue
            if kw and not any(kw in (x or "").lower() for x in
                              (u.username, u.phone, u.email)):
                continue
            rows.append((u.id, u.username, u.phone or "-", u.email or "-",
                         role_label(u.role), self._ts(u.created_at)))
        self._fill(self.tbl_users, rows)
        self.lbl_status.setText(f"共 {len(rows)} 个账号")

    def _refresh_deleted(self):
        rows = [(u.id, u.username, role_label(u.role), "-") for u in self.mgr.deleted_users()]
        self._fill(self.tbl_deleted, rows)

    def _refresh_audit(self):
        rows = [(a["id"], a["actor"], a["action"], a["detail"], self._ts(a["ts"]))
                for a in self.mgr.audit_logs()]
        self._fill(self.tbl_audit, rows)

    def _refresh_all(self):
        self._refresh_users()
        self._refresh_deleted()
        self._refresh_audit()

    # ------------------------------------------------ 动作
    def _selected_id(self, table: QTableWidget) -> Optional[int]:
        r = table.currentRow()
        if r < 0 or not table.item(r, 0):
            QMessageBox.information(self, "提示", "请先选中一行")
            return None
        return int(table.item(r, 0).text())

    def _create_user(self):
        dlg = CreateUserDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.values:
            try:
                u = self.mgr.create_user(*dlg.values)
                QMessageBox.information(self, "创建成功", f"用户 {u.username} 已创建")
            except AdminError as e:
                QMessageBox.warning(self, "创建失败", str(e))
            self._refresh_all()

    def _create_admin(self):
        dlg = CreateUserDialog(self, is_admin=True)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.values:
            try:
                u = self.mgr.create_admin(*dlg.values)
                QMessageBox.information(self, "创建成功",
                                        f"受限管理员 {u.username} 已创建（不能管理别的账号）")
            except AdminError as e:
                QMessageBox.warning(self, "创建失败", str(e))
            self._refresh_all()

    def _delete_user(self):
        uid = self._selected_id(self.tbl_users)
        if uid is None:
            return
        ret = QMessageBox.question(
            self, "确认删除",
            f"确定删除账号 id={uid} 吗？\n将移入回收站（30 天内可恢复，不会真正抹除数据）。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        try:
            self.mgr.delete_user(uid)
            QMessageBox.information(self, "已移入回收站", "账号已软删除，可在「回收站」页恢复")
        except AdminError as e:
            QMessageBox.warning(self, "删除失败", str(e))
        self._refresh_all()

    def _restore_user(self):
        uid = self._selected_id(self.tbl_deleted)
        if uid is None:
            return
        try:
            self.mgr.restore_user(uid)
            QMessageBox.information(self, "恢复成功", "账号已恢复")
        except AdminError as e:
            QMessageBox.warning(self, "恢复失败", str(e))
        self._refresh_all()
