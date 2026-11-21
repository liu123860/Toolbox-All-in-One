"""文本工具组：字数统计 / 文本对比 / 大小写转换 / Base64 / URL编解码 / JSON格式化 / 正则测试 / 编码转换。

全部零第三方依赖（PySide6 + 标准库），纯文本处理无网络。
"""
from __future__ import annotations

import base64
import json
import re
import urllib.parse

from PySide6.QtGui import QColor, QTextCursor, QTextCharFormat
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QPlainTextEdit, QSplitter, QVBoxLayout, QWidget,
)


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


def _editor(placeholder: str = "") -> QPlainTextEdit:
    ed = QPlainTextEdit()
    ed.setPlaceholderText(placeholder)
    ed.setStyleSheet("font-family: Consolas, monospace; font-size: 14px;")
    return ed


# ============================================================ 字数统计
def create_wordcount_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("字数统计 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("把文本粘贴到这里，实时统计")
    out = _out("等待输入")

    def update():
        t = ed.toPlainText()
        if not t:
            out.setText("等待输入")
            return
        chars = len(t)
        chars_no_space = len(re.sub(r"\s", "", t))
        chinese = len(re.findall(r"[\u4e00-\u9fff]", t))
        words = len(re.findall(r"[A-Za-z0-9']+", t))
        lines = t.count("\n") + 1
        paragraphs = len([p for p in re.split(r"\n\s*\n", t) if p.strip()])
        out.setText(
            f"字符数（含空格）：{chars}　　字符数（不含空格）：{chars_no_space}\n"
            f"中文字符：{chinese}　　英文单词：{words}\n"
            f"行数：{lines}　　段落数：{paragraphs}"
        )

    ed.textChanged.connect(update)
    lay.addWidget(ed, stretch=1)
    lay.addWidget(out)
    return w


# ============================================================ 文本对比
def create_textdiff_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("文本对比 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    sp = QSplitter()
    left = _editor("原文本")
    right = _editor("对比文本")
    sp.addWidget(left)
    sp.addWidget(right)
    out = _out()

    def compare():
        a = left.toPlainText().splitlines()
        b = right.toPlainText().splitlines()
        same = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
        diff = max(len(a), len(b)) - same
        only_a = len(a) - same
        only_b = len(b) - same
        out.setText(
            f"行数：左 {len(a)} / 右 {len(b)}　　相同行：{same}　　差异行：{diff}\n"
            f"左侧独有约 {only_a} 行，右侧独有约 {only_b} 行"
        )

    btn = QPushButton("对比")
    btn.clicked.connect(compare)
    lay.addWidget(sp, stretch=1)
    lay.addWidget(btn)
    lay.addWidget(out)
    return w


# ============================================================ 大小写转换
def create_textcase_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("大小写转换 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("输入原文")
    out = _out()

    def to_upper():
        out.setText(ed.toPlainText().upper())

    def to_lower():
        out.setText(ed.toPlainText().lower())

    def to_title():
        out.setText(ed.toPlainText().title())

    def to_camel():
        words = re.split(r"[\s_\-]+", ed.toPlainText().strip())
        if not words:
            out.setText("")
            return
        out.setText(words[0].lower() + "".join(x.capitalize() for x in words[1:]))

    def to_snake():
        words = re.split(r"[\s_\-]+", ed.toPlainText().strip())
        out.setText("_".join(x.lower() for x in words if x))

    def to_rev():
        out.setText(ed.toPlainText()[::-1])

    row = QHBoxLayout()
    for text, fn in [("全部大写", to_upper), ("全部小写", to_lower), ("首字母大写", to_title),
                     ("驼峰 camelCase", to_camel), ("下划线 snake_case", to_snake), ("反转", to_rev)]:
        b = QPushButton(text)
        b.clicked.connect(fn)
        row.addWidget(b)

    lay.addWidget(ed, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ Base64
def create_base64_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("Base64 编解码 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("输入原文（编码）或 Base64 串（解码）")
    out = _out()

    def encode():
        try:
            out.setText(base64.b64encode(ed.toPlainText().encode("utf-8")).decode("ascii"))
        except Exception as e:
            out.setText(f"编码失败：{e}")

    def decode():
        try:
            raw = re.sub(r"\s", "", ed.toPlainText())
            out.setText(base64.b64decode(raw).decode("utf-8"))
        except Exception as e:
            out.setText(f"解码失败：{e}")

    b1 = QPushButton("编码 →")
    b2 = QPushButton("← 解码")
    b1.clicked.connect(encode)
    b2.clicked.connect(decode)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)

    lay.addWidget(ed, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ URL 编解码
def create_url_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("URL 编解码 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("输入原文（编码）或 URL 编码串（解码）")
    out = _out()

    def encode():
        out.setText(urllib.parse.quote(ed.toPlainText(), safe=""))

    def decode():
        try:
            out.setText(urllib.parse.unquote(ed.toPlainText()))
        except Exception as e:
            out.setText(f"解码失败：{e}")

    b1 = QPushButton("编码 →")
    b2 = QPushButton("← 解码")
    b1.clicked.connect(encode)
    b2.clicked.connect(decode)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)

    lay.addWidget(ed, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ JSON 格式化
def create_json_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("JSON 格式化 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("粘贴 JSON")
    out = _out()

    def fmt():
        try:
            obj = json.loads(ed.toPlainText())
            out.setText(json.dumps(obj, ensure_ascii=False, indent=2))
        except Exception as e:
            out.setText(f"JSON 解析失败：{e}")

    def mini():
        try:
            obj = json.loads(ed.toPlainText())
            out.setText(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        except Exception as e:
            out.setText(f"JSON 解析失败：{e}")

    def validate():
        try:
            json.loads(ed.toPlainText())
            out.setText("JSON 合法 ✓")
        except Exception as e:
            out.setText(f"JSON 不合法：{e}")

    row = QHBoxLayout()
    b1 = QPushButton("格式化")
    b2 = QPushButton("压缩")
    b3 = QPushButton("校验")
    b1.clicked.connect(fmt)
    b2.clicked.connect(mini)
    b3.clicked.connect(validate)
    row.addWidget(b1)
    row.addWidget(b2)
    row.addWidget(b3)

    lay.addWidget(ed, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ 正则测试器
def create_regex_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("正则测试器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    pattern = QLineEdit()
    pattern.setPlaceholderText("正则表达式，例如 \\d+")
    ed = _editor("待匹配文本")
    out = _out()

    def test():
        try:
            rx = re.compile(pattern.text())
        except re.error as e:
            out.setText(f"正则语法错误：{e}")
            return
        text = ed.toPlainText()
        matches = list(rx.finditer(text))
        if not matches:
            out.setText("无匹配")
            return
        lines = [f"共 {len(matches)} 处匹配："]
        for i, m in enumerate(matches[:20], 1):
            lines.append(f"  {i}. [{m.start()}:{m.end()}] {m.group()!r}")
        if len(matches) > 20:
            lines.append(f"  ... 还有 {len(matches) - 20} 处")
        out.setText("\n".join(lines))
        # 高亮
        cursor = ed.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        ed.setTextCursor(cursor)
        ed.setExtraSelections([])
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 235, 59, 120))
        from PySide6.QtWidgets import QTextEdit
        sels = []
        for m in matches[:200]:
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(ed.document())
            sel.cursor.setPosition(m.start())
            sel.cursor.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
            sel.format = fmt
            sels.append(sel)
        ed.setExtraSelections(sels)

    row = QHBoxLayout()
    row.addWidget(QLabel("正则："))
    row.addWidget(pattern, stretch=1)
    btn = QPushButton("测试")
    btn.clicked.connect(test)
    row.addWidget(btn)

    lay.addLayout(row)
    lay.addWidget(ed, stretch=1)
    lay.addWidget(out)
    return w


# ============================================================ 编码转换
def create_encodeconv_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("编码转换 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = _editor("输入文本，查看各编码下的字节")
    out = _out()

    def show():
        t = ed.toPlainText()
        if not t:
            out.setText("等待输入")
            return
        lines = []
        for enc in ("utf-8", "gbk", "utf-16-le", "ascii"):
            try:
                raw = t.encode(enc)
                hexs = raw[:64].hex(" ")
                lines.append(f"{enc.upper():<12} {len(raw)} 字节　{hexs}{' ...' if len(raw) > 64 else ''}")
            except Exception as e:
                lines.append(f"{enc.upper():<12} 无法编码：{e}")
        out.setText("\n".join(lines))

    def from_hex():
        try:
            hx = re.sub(r"[\s,]", "", ed.toPlainText())
            raw = bytes.fromhex(hx)
            out.setText("UTF-8 解码：" + raw.decode("utf-8", errors="replace") +
                        "\nGBK 解码：" + raw.decode("gbk", errors="replace"))
        except Exception as e:
            out.setText(f"Hex 解析失败：{e}")

    ed.textChanged.connect(show)
    b = QPushButton("按 Hex 字节解码")
    b.clicked.connect(from_hex)
    lay.addWidget(ed, stretch=1)
    lay.addWidget(b)
    lay.addWidget(out)
    return w
