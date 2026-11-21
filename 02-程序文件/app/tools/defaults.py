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

    # ---- 生活计算（daily.py）----
    ToolInfo("unit_conv", "单位换算", "生活", "长度/重量/温度/面积/体积/速度/数据换算", "📐",
             _f("daily", "create_unit_widget")),
    ToolInfo("base_conv", "进制转换", "生活", "二/八/十/十六进制互转", "🔢",
             _f("daily", "create_base_widget")),
    ToolInfo("mortgage", "房贷计算器", "生活", "等额本息/等额本金月供与总利息", "🏠",
             _f("daily", "create_mortgage_widget")),
    ToolInfo("tax", "个税计算器", "生活", "月薪个税与税后收入（起征点 5000）", "💰",
             _f("daily", "create_tax_widget")),
    ToolInfo("bmi", "BMI 计算器", "生活", "身高体重算 BMI 与健康范围", "⚖",
             _f("daily", "create_bmi_widget")),
    ToolInfo("timestamp", "时间戳转换", "生活", "Unix 时间戳 ↔ 可读日期时间", "⏱",
             _f("daily", "create_timestamp_widget")),
    ToolInfo("datecalc", "日期计算器", "生活", "日期差计算与日期加减天数", "📅",
             _f("daily", "create_datecalc_widget")),

    # ---- 生活实用（life_tools.py）----
    ToolInfo("timer", "倒计时秒表", "生活", "倒计时 + 秒表双模式", "⏲",
             _f("life_tools", "create_timer_widget")),
    ToolInfo("random", "随机数抽签", "生活", "随机数生成与名单抽签", "🎲",
             _f("life_tools", "create_random_widget")),
    ToolInfo("password", "密码生成器", "生活", "密码学安全随机密码生成", "🔐",
             _f("life_tools", "create_password_widget")),
    ToolInfo("relative", "亲戚称呼", "生活", "亲戚称呼计算器", "👪",
             _f("life_tools", "create_relative_widget")),

    # ---- 文本工具（text_tools.py）----
    ToolInfo("wordcount", "字数统计", "办公", "字符/中文/单词/行/段统计", "🔢",
             _f("text_tools", "create_wordcount_widget")),
    ToolInfo("textdiff", "文本对比", "办公", "两段文本逐行对比", "🔍",
             _f("text_tools", "create_textdiff_widget")),
    ToolInfo("textcase", "大小写转换", "办公", "大小写/驼峰/下划线/反转", "Aa",
             _f("text_tools", "create_textcase_widget")),
    ToolInfo("base64", "Base64 编解码", "办公", "文本 Base64 编码解码", "🔡",
             _f("text_tools", "create_base64_widget")),
    ToolInfo("urltool", "URL 编解码", "办公", "URL 百分号编码解码", "🔗",
             _f("text_tools", "create_url_widget")),
    ToolInfo("jsonformat", "JSON 格式化", "办公", "JSON 格式化/压缩/校验", "📋",
             _f("text_tools", "create_json_widget")),
    ToolInfo("regexlab", "正则测试器", "办公", "正则表达式测试与高亮", "🧩",
             _f("text_tools", "create_regex_widget")),
    ToolInfo("encodeconv", "编码转换", "办公", "UTF-8/GBK/UTF-16/ASCII 编码查看", "🔤",
             _f("text_tools", "create_encodeconv_widget")),

    # ---- 办公工具（office_tools.py）----
    ToolInfo("notepad", "记事本", "办公", "文本编辑与打开/保存 txt", "📝",
             _f("office_tools", "create_notepad_widget")),
    ToolInfo("todo", "待办清单", "办公", "待办事项管理（本地持久化）", "✅",
             _f("office_tools", "create_todo_widget")),
    ToolInfo("markdown", "Markdown 预览", "办公", "Markdown 实时预览", "📖",
             _f("office_tools", "create_markdown_widget")),
    ToolInfo("paint", "画图板", "办公", "简单画图与保存 PNG", "🎨",
             _f("office_tools", "create_paint_widget")),
    ToolInfo("pomodoro", "番茄钟", "办公", "工作/休息番茄计时", "🍅",
             _f("office_tools", "create_pomodoro_widget")),

    # ---- 图片工具（image_tools.py）----
    ToolInfo("imageview", "图片查看", "媒体", "图片查看与缩放", "🖼",
             _f("image_tools", "create_imageview_widget")),
    ToolInfo("imageconv", "图片格式转换", "媒体", "PNG/JPG/BMP/WEBP 互转", "🔄",
             _f("image_tools", "create_imageconv_widget")),
    ToolInfo("imagezip", "图片压缩", "媒体", "缩放 + 质量压缩图片", "🗜",
             _f("image_tools", "create_imagezip_widget")),
    ToolInfo("eyedropper", "屏幕取色", "媒体", "取屏幕任意位置颜色", "💧",
             _f("image_tools", "create_eyedropper_widget")),
    ToolInfo("colorpicker", "颜色选择器", "媒体", "调色板与 HEX/RGB/HSV", "🎨",
             _f("image_tools", "create_colorpicker_widget")),
    ToolInfo("screenshot", "屏幕截图", "媒体", "全屏截图与保存", "📷",
             _f("image_tools", "create_screenshot_widget")),

    # ---- 系统工具（system_tools.py）----
    ToolInfo("filehash", "文件哈希", "系统", "MD5/SHA1/SHA256 校验", "🔑",
             _f("system_tools", "create_filehash_widget")),
    ToolInfo("batchrename", "批量重命名", "系统", "文件批量重命名", "✏",
             _f("system_tools", "create_batchrename_widget")),
    ToolInfo("filesplit", "文件分割合并", "系统", "大文件分割与合并", "✂",
             _f("system_tools", "create_filesplit_widget")),
    ToolInfo("diskusage", "磁盘空间", "系统", "各磁盘容量分析", "💾",
             _f("system_tools", "create_diskusage_widget")),
    ToolInfo("sysinfo", "系统信息", "系统", "系统/硬件/Python 信息", "ℹ",
             _f("system_tools", "create_sysinfo_widget")),
    ToolInfo("procman", "进程管理", "系统", "进程查看与结束", "⚙",
             _f("system_tools", "create_procman_widget")),
]


def register_defaults() -> None:
    for t in TOOLS:
        registry.register(t)
