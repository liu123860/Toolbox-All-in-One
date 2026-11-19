"""工具注册：全部内置工具（懒加载工厂，启动只注册元数据，打开时才创建窗口）。

所有工具对所有人开放，无任何付费门槛。
"""
from __future__ import annotations

from app.core.plugin import ToolInfo
from app.tools import registry


# ---- 懒加载工厂（避免启动时导入 Chromium / 多媒体等重模块） ----
def _f(module: str, func: str = "create_widget"):
    def make():
        import importlib
        m = importlib.import_module(f"app.tools.impl.{module}")
        return getattr(m, func)()
    return make


TOOLS = [
    ToolInfo("calc", "计算器", "生活", "科学计算与历史记录（AST 安全求值）", "🧮",
             _f("calculator")),
    ToolInfo("weather", "天气", "生活", "实时天气 + 7 日预报（Open-Meteo）", "🌤",
             _f("weather")),
    ToolInfo("word", "文档编辑", "办公", "txt/md/html/rtf/docx 编辑，LibreOffice 容器增强", "📝",
             _f("office", "create_doc_widget")),
    ToolInfo("pdf", "PDF 阅读", "办公", "QtPdf 内置阅读，SumatraPDF 容器增强", "📄",
             _f("office", "create_pdf_widget")),
    ToolInfo("ai", "AI 助手", "办公", "多模型对话（OpenAI/DeepSeek/通义/本地Ollama）", "🤖",
             _f("ai_chat")),
    ToolInfo("music", "音乐", "媒体", "本地音乐播放与播放列表（QtMultimedia/VLC）", "🎵",
             _f("media", "create_music_widget")),
    ToolInfo("video", "视频", "媒体", "视频播放（QtMultimedia/VLC 全格式增强）", "🎬",
             _f("media", "create_video_widget")),
    ToolInfo("video_pro", "高清转码", "媒体", "FFmpeg 容器 H.264/H.265 转码", "⚡",
             _f("media", "create_transcode_widget")),
    ToolInfo("browser", "浏览器", "系统", "Chromium 内核多标签浏览器", "🌐",
             _f("browser")),
    ToolInfo("cleaner", "垃圾清理", "系统", "只读扫描+回收站可恢复清理（白名单目录）", "🧹",
             _f("cleaner")),
    ToolInfo("antivirus", "病毒扫描", "系统", "ClamAV 引擎 / 轻量启发式降级 + 可恢复隔离", "🛡",
             _f("antivirus")),
    ToolInfo("archive", "压缩解压", "系统", "zip/tar.gz/7z，含 Zip-Slip 防护", "🗜",
             _f("archive")),
    ToolInfo("scan", "扫描打印", "系统", "打印预览/打印 + WIA 扫描仪", "🖨",
             _f("scanprint")),
    ToolInfo("containers", "组件管理", "系统", "开源组件容器状态与降级方案总览", "📦",
             _f("container_status")),
]


def register_defaults() -> None:
    for t in TOOLS:
        registry.register(t)
