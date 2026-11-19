"""基本工具集齐·免下载工具箱（开源版）— 程序入口。

启动流程：初始化数据 → 首次部署创建本地管理员 → 恢复 15 天免登录会话 → 主窗口。
便携版：--portable 或程序目录 portable.marker → 数据存程序目录、省资源。
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.account import auth
from app.account.db import Database
from app.account.ui import AdminInitDialog
from app.core.main_window import MainWindow
from app.core.paths import APP_NAME, APP_VERSION, is_portable
from app.settings.manager import SettingsManager
from app.settings.theme import build_qss
from app.tools import defaults, registry


def main() -> int:
    # 打包后真实启动自检
    if "--selftest" in sys.argv:
        from app.core.selftest import run_selftest
        return run_selftest()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # ---- 数据与账号
    db = Database()
    if not db.has_admin():
        dlg = AdminInitDialog(db)
        if dlg.exec() != AdminInitDialog.DialogCode.Accepted:
            return 0

    settings = SettingsManager(portable=is_portable())
    user = auth.restore_session(db)

    # ---- 工具注册 + 使用统计
    defaults.register_defaults()
    registry.load_stats()

    # ---- 便携版：省资源策略（无广告概念）
    if is_portable():
        settings.set("speed.preload", "lazy")
        settings.set("effects.blur", False)
        settings.set("effects.transition", False)

    app.setStyleSheet(build_qss(settings))

    win = MainWindow(db, settings, user)
    win.show()
    db.audit("system", "app_start", f"启动 v{APP_VERSION}"
             + ("（便携版）" if is_portable() else ""))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
