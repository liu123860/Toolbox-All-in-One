"""管理员模块：权限矩阵 / 管理逻辑 / 图形化界面 / 受限代码编辑区。

UI 类请显式导入（避免纯逻辑测试时牵连 Qt 窗口模块）：
    from app.admin.ui import AdminDialog
    from app.admin.code_editor import CodeEditorDialog
"""
from app.admin.permissions import can, role_label, abilities, patch_scope, describe
from app.admin.manager import AdminManager, AdminError

__all__ = ["can", "role_label", "abilities", "patch_scope", "describe",
           "AdminManager", "AdminError"]
