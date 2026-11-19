"""工具插件模型：每个内置工具实现统一接口，新增工具零改动主框架。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ToolInfo:
    id: str
    name: str
    category: str                 # 用途分类：办公/媒体/系统/生活 等
    desc: str = ""
    icon: str = "🧰"              # 首版用字符图标，后续换图标资源
    factory: Optional[Callable] = None   # create_widget() -> QWidget

    def create_widget(self):
        if self.factory is None:
            return None
        return self.factory()


@dataclass
class ToolUseStat:
    """使用统计，用于「按频率」分类模式。"""
    tool_id: str
    open_count: int = 0
    total_seconds: int = 0

    @property
    def score(self) -> float:
        return self.open_count + self.total_seconds / 60.0
