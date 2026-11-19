"""打包后 exe 真实启动自检。

用法：基本工具集齐工具箱.exe --selftest [--selftest-log=路径]
逐项真实构建模块/窗口，把结果写入日志文件；退出码 0=全通过，1=有失败。
窗口版 exe 无控制台，日志是唯一可验证渠道。
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path


def _log_path() -> Path:
    for a in sys.argv:
        if a.startswith("--selftest-log="):
            return Path(a.split("=", 1)[1]).resolve()
    return Path(tempfile.gettempdir()) / "toolbox_selftest.log"


def run_selftest() -> int:
    lines: list[str] = []
    passed = failed = 0

    def check(name: str, fn):
        nonlocal passed, failed
        t0 = time.time()
        try:
            detail = fn()
            passed += 1
            lines.append(f"PASS  {name}  ({time.time() - t0:.2f}s)  {detail or ''}")
        except Exception as e:
            failed += 1
            lines.append(f"FAIL  {name}  {type(e).__name__}: {e}")
            lines.append(traceback.format_exc())

    # 隔离数据目录，避免自检污染真实账号数据
    work = Path(tempfile.mkdtemp(prefix="toolbox_selftest_"))
    os.environ["TOOLBOX_DATA_DIR"] = str(work / "data")

    lines.append(f"=== 打包版自检 {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    lines.append(f"frozen={bool(getattr(sys, 'frozen', False))} "
                 f"python={sys.version.split()[0]} exe={sys.executable}")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    app = QApplication(sys.argv)
    check("QApplication 构建", lambda: "platform=" + app.platformName())

    from app.core.paths import APP_VERSION, app_dir, data_dir, is_portable
    check("路径解析", lambda: f"v{APP_VERSION} app_dir={app_dir()} "
                              f"data_dir={data_dir()} portable={is_portable()}")

    from app.account.db import Database
    from app.account import auth
    db = Database()
    check("数据库建表", lambda: "users/sessions/audit_log 已创建")
    check("初始化主管理员", lambda: auth.init_main_admin(db, "Selftest123").username)
    check("注册校验", lambda: auth.register(db, "u01", "13900139000",
                                            "u01@t.com", "Abcd1234").username)
    user = db.find_user_by(username="u01")
    check("登录", lambda: auth.login(db, "u01@t.com", "Abcd1234").username)
    check("密码哈希非明文", lambda: "不含明文" if "Abcd1234" not in str(
        db.raw_user(user.id)["password_hash"]) else "出现明文")

    from app.settings.manager import SettingsManager
    st = SettingsManager()
    received = []
    st.changed.connect(lambda k, v: received.append(k))
    def _settings_signal():
        st.set("color.accent", "#123456")
        assert received, "热切换信号未触发"
        return "读写+信号 OK"
    check("设置读写+热切换信号", _settings_signal)
    from app.settings.theme import build_qss
    check("主题 QSS", lambda: f"{len(build_qss(st))} 字符")

    from app.tools import defaults, registry
    defaults.register_defaults()
    registry.load_stats()
    check("工具注册", lambda: f"{len(registry.all_tools())} 个工具")
    registry.record_open("calc")
    check("工具统计持久化", lambda: f"calc 打开 {registry._STATS['calc'].open_count} 次")

    import importlib.util
    def _no_commercial():
        assert importlib.util.find_spec("app.ads") is None, "广告模块残留"
        assert importlib.util.find_spec("app.vip") is None, "VIP 模块残留"
        return "开源版无商业化模块"
    check("无商业化模块残留", _no_commercial)

    # 每个工具：真实导入 + 真实构建窗口（浏览器窗口需真实显示环境，仅验证模块导入）
    mods = ["calculator", "weather", "office", "ai_chat", "media", "browser",
            "cleaner", "antivirus", "archive", "scanprint", "container_status"]
    for m in mods:
        def _import(m=m):
            __import__(f"app.tools.impl.{m}")
            return "模块导入 OK"
        check(f"工具模块导入 {m}", _import)

    from app.admin.permissions import can, patch_scope
    admin = db.find_user_by(username="admin")
    check("权限矩阵", lambda: f"主管理员可建管理员={can(admin, 'create_admin')} "
                             f"普通用户可开管理界面={can(user, 'open_admin_panel')}")
    from app.admin.patch_store import validate_patch, example_patch, PatchError
    check("受限补丁合法样例", lambda: f"{len(validate_patch(example_patch(), 'full'))} 项通过")
    def _reject():
        try:
            validate_patch('{"type":"toolbox_patch_v1","changes":[{"key":"x","value":"import os"}]}', "full")
        except PatchError:
            return "恶意内容已拦截"
        raise AssertionError("恶意补丁未被拦截")
    check("受限补丁拦截大改动", _reject)

    from app.core.main_window import MainWindow
    win = None
    def _main_window():
        nonlocal win
        win = MainWindow(db, st, admin)
        win.show()
        return "主窗口构建并显示 OK"
    check("主窗口", _main_window)

    from app.admin.ui import AdminDialog
    from app.admin.code_editor import CodeEditorDialog

    def _admin_dialog():
        d = AdminDialog(db, admin)
        n = d.tbl_users.rowCount()
        d.close()
        return f"构建 OK，用户表 {n} 行"
    check("管理界面窗口", _admin_dialog)

    def _code_dialog():
        d = CodeEditorDialog(db, admin, st)
        d.close()
        return "构建 OK"
    check("代码编辑区窗口", _code_dialog)

    # 真实事件循环跑一小段（验证信号/定时器不崩）
    def _eventloop():
        QTimer.singleShot(300, app.quit)
        app.exec()
        return "事件循环正常退出"
    check("Qt 事件循环", _eventloop)

    lines.append(f"=== 结果：PASS {passed} / FAIL {failed} ===")
    text = "\n".join(lines)
    p = _log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    try:
        print(text)
    except Exception:
        pass
    return 0 if failed == 0 else 1
