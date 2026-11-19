"""登录 / 注册 / 忘记密码 / 首次部署管理员初始化 的界面。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app.account import auth
from app.account.auth import AuthError
from app.account.db import Database, User


def _err(parent: QWidget, e: AuthError) -> None:
    QMessageBox.warning(parent, "输入有误", e.message)


# ---------------------------------------------------------------- 登录窗口

class LoginDialog(QDialog):
    """登录窗口：登录 / 注册 / 忘记密码 / 15 天免费登录 按钮齐全。"""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.user: Optional[User] = None
        self.setWindowTitle("登录 · 基本工具集齐工具箱")
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        title = QLabel("欢迎回来")
        title.setObjectName("title")
        lay.addWidget(title)
        hint = QLabel("支持用户名 / 手机号 / 邮箱登录")
        hint.setObjectName("subtle")
        lay.addWidget(hint)

        form = QFormLayout()
        self.ed_id = QLineEdit()
        self.ed_id.setPlaceholderText("用户名 / 手机号 / 邮箱")
        self.ed_pwd = QLineEdit()
        self.ed_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pwd.setPlaceholderText("密码")
        form.addRow("账号", self.ed_id)
        form.addRow("密码", self.ed_pwd)
        lay.addLayout(form)

        self.chk_keep = QPushButton("登录后 15 天免登录")
        self.chk_keep.setCheckable(True)
        self.chk_keep.setToolTip("勾选后 15 天内启动软件不再弹出登录窗口")
        lay.addWidget(self.chk_keep)

        btn_login = QPushButton("登 录")
        btn_login.setObjectName("primary")
        btn_login.setMinimumHeight(44)          # 关闭/主按钮热区 ≥44px 铁律
        btn_login.clicked.connect(self._login)
        lay.addWidget(btn_login)

        row = QHBoxLayout()
        for text, slot in (("注册账号", self._register),
                           ("忘记密码", self._forgot),
                           ("15 天免费登录", self._guest)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)

    def _login(self):
        try:
            self.user = auth.login(self.db, self.ed_id.text(), self.ed_pwd.text(),
                                   keep=self.chk_keep.isChecked())
            self.accept()
        except AuthError as e:
            _err(self, e)

    def _register(self):
        dlg = RegisterDialog(self.db, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.user:
            QMessageBox.information(self, "注册成功",
                                    f"注册成功，欢迎 {dlg.user.username}！即将自动登录。")
            self.user = dlg.user
            auth.login(self.db, dlg.user.username, dlg._pwd, keep=False)  # 已验证，补会话记录
            self.accept()

    def _forgot(self):
        ForgotPasswordDialog(self.db, self).exec()

    def _guest(self):
        self.user = auth.guest_login(self.db)
        self.accept()


# ---------------------------------------------------------------- 注册窗口

class RegisterDialog(QDialog):
    """注册流程：用户名（≤6 字符）→ 手机号 → 邮箱 → 密码（字母+数字）。"""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.user: Optional[User] = None
        self._pwd = ""
        self.setWindowTitle("注册账号")
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_name.setMaxLength(6)             # 最多 6 个字符，输入层直接限制
        self.ed_phone = QLineEdit()
        self.ed_phone.setPlaceholderText("11 位手机号")
        self.ed_mail = QLineEdit()
        self.ed_mail.setPlaceholderText("example@mail.com")
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

        hint = QLabel("密码需 8-20 位，由英文字母和数字组成，且同时包含字母和数字")
        hint.setObjectName("subtle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        ok = QPushButton("注 册")
        ok.setObjectName("primary")
        ok.setMinimumHeight(44)
        ok.clicked.connect(self._submit)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(ok)
        row.addWidget(cancel)
        lay.addLayout(row)

    def _submit(self):
        try:
            if self.ed_pwd.text() != self.ed_pwd2.text():
                raise AuthError("password", "两次输入的密码不一致")
            self.user = auth.register(self.db, self.ed_name.text(), self.ed_phone.text(),
                                      self.ed_mail.text(), self.ed_pwd.text())
            self._pwd = self.ed_pwd.text()
            self.accept()
        except AuthError as e:
            _err(self, e)


# ---------------------------------------------------------------- 忘记密码

class ForgotPasswordDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("忘记密码")
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        hint = QLabel("请输入账号信息验证身份后设置新密码。\n（当前为演示验证：三项匹配即可重置；正式版将接入短信/邮箱验证码）")
        hint.setObjectName("subtle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        form = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_phone = QLineEdit()
        self.ed_mail = QLineEdit()
        self.ed_pwd = QLineEdit()
        self.ed_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pwd.setPlaceholderText("8-20 位字母+数字")
        form.addRow("用户名", self.ed_name)
        form.addRow("绑定手机号", self.ed_phone)
        form.addRow("绑定邮箱", self.ed_mail)
        form.addRow("新密码", self.ed_pwd)
        lay.addLayout(form)

        ok = QPushButton("重置密码")
        ok.setObjectName("primary")
        ok.setMinimumHeight(44)
        ok.clicked.connect(self._submit)
        lay.addWidget(ok)

    def _submit(self):
        try:
            auth.reset_password(self.db, self.ed_name.text(), self.ed_phone.text(),
                                self.ed_mail.text(), self.ed_pwd.text())
            QMessageBox.information(self, "重置成功", "密码已重置，请使用新密码登录。")
            self.accept()
        except AuthError as e:
            _err(self, e)


# ---------------------------------------------------------------- 首次部署

class AdminInitDialog(QDialog):
    """首次启动：初始化主管理员。密码只录入这一次，系统仅存哈希。"""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.user: Optional[User] = None
        self.setWindowTitle("初始化主管理员")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        title = QLabel("首次使用 · 设置主管理员密码")
        title.setObjectName("title")
        lay.addWidget(title)
        info = QLabel(
            "主管理员账号：admin\n邮箱：admin@example.com\n手机：13800000000\n\n"
            "请设置登录密码（8-20 位字母+数字）。\n"
            "密码只存加密哈希，请牢记；忘记后可通过手机/邮箱验证重置。")
        info.setObjectName("subtle")
        info.setWordWrap(True)
        lay.addWidget(info)

        form = QFormLayout()
        self.ed_pwd = QLineEdit()
        self.ed_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pwd2 = QLineEdit()
        self.ed_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("设置密码", self.ed_pwd)
        form.addRow("确认密码", self.ed_pwd2)
        lay.addLayout(form)

        ok = QPushButton("完成初始化")
        ok.setObjectName("primary")
        ok.setMinimumHeight(44)
        ok.clicked.connect(self._submit)
        lay.addWidget(ok)

    def _submit(self):
        try:
            if self.ed_pwd.text() != self.ed_pwd2.text():
                raise AuthError("password", "两次输入的密码不一致")
            self.user = auth.init_main_admin(self.db, self.ed_pwd.text())
            QMessageBox.information(
                self, "初始化完成", "主管理员账号创建成功！\n登录后可使用管理界面与代码编辑区。")
            self.accept()
        except AuthError as e:
            _err(self, e)
