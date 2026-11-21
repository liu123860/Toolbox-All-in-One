"""办公工具组：记事本 / 待办清单 / Markdown 预览 / 画图板 / 番茄钟。

全部零第三方依赖（PySide6 + 标准库）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QColorDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QPlainTextEdit,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from app.core.paths import data_dir


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


# ============================================================ 记事本
def create_notepad_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("记事本 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ed = QPlainTextEdit()
    ed.setPlaceholderText("在这里记录内容，可打开/保存 txt 文件")
    path_lab = QLabel("未保存")
    out = _out()

    def open_file():
        p, _ = QFileDialog.getOpenFileName(w, "打开文本", "", "文本文件 (*.txt *.md *.log);;所有文件 (*.*)")
        if not p:
            return
        try:
            ed.setPlainText(Path(p).read_text(encoding="utf-8", errors="replace"))
            path_lab.setText(p)
            out.setText("已打开")
        except Exception as e:
            out.setText(f"打开失败：{e}")

    def save_file():
        p = path_lab.text()
        if p == "未保存":
            p, _ = QFileDialog.getSaveFileName(w, "保存文本", "note.txt", "文本文件 (*.txt)")
        if not p:
            return
        try:
            Path(p).write_text(ed.toPlainText(), encoding="utf-8")
            path_lab.setText(p)
            out.setText(f"已保存到 {p}")
        except Exception as e:
            out.setText(f"保存失败：{e}")

    def save_as():
        p, _ = QFileDialog.getSaveFileName(w, "另存为", "note.txt", "文本文件 (*.txt)")
        if p:
            path_lab.setText(p)
            save_file()

    row = QHBoxLayout()
    for text, fn in [("打开", open_file), ("保存", save_file), ("另存为", save_as)]:
        b = QPushButton(text)
        b.clicked.connect(fn)
        row.addWidget(b)
    row.addStretch(1)

    lay.addWidget(path_lab)
    lay.addWidget(ed, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ 待办清单
def _todo_path() -> Path:
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "todo.json"


def create_todo_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("待办清单 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    lst = QListWidget()
    inp = QLineEdit()
    inp.setPlaceholderText("输入待办事项，回车添加")
    out = _out()

    def load():
        p = _todo_path()
        if not p.exists():
            return
        try:
            items = json.loads(p.read_text(encoding="utf-8"))
            for it in items:
                item = QListWidgetItem(("✓ " if it.get("done") else "□ ") + it.get("text", ""))
                item.setData(Qt.ItemDataRole.UserRole, bool(it.get("done")))
                lst.addItem(item)
        except Exception:
            pass

    def save():
        items = []
        for i in range(lst.count()):
            it = lst.item(i)
            items.append({"text": it.text()[2:], "done": bool(it.data(Qt.ItemDataRole.UserRole))})
        _todo_path().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add():
        t = inp.text().strip()
        if not t:
            return
        item = QListWidgetItem("□ " + t)
        item.setData(Qt.ItemDataRole.UserRole, False)
        lst.addItem(item)
        inp.clear()
        save()

    def toggle():
        it = lst.currentItem()
        if not it:
            return
        done = not bool(it.data(Qt.ItemDataRole.UserRole))
        it.setData(Qt.ItemDataRole.UserRole, done)
        it.setText(("✓ " if done else "□ ") + it.text()[2:])
        save()

    def remove():
        it = lst.currentItem()
        if it:
            lst.takeItem(lst.row(it))
            save()

    inp.returnPressed.connect(add)
    lst.itemDoubleClicked.connect(toggle)
    b1 = QPushButton("添加")
    b2 = QPushButton("切换完成")
    b3 = QPushButton("删除")
    b1.clicked.connect(add)
    b2.clicked.connect(toggle)
    b3.clicked.connect(remove)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addWidget(b3)

    load()
    lay.addWidget(QLabel("双击条目切换完成状态"))
    lay.addWidget(lst, stretch=1)
    lay.addWidget(inp)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ Markdown 预览
def _md_to_html(text: str) -> str:
    lines = text.splitlines()
    html = []
    in_code = False
    in_list = False
    for ln in lines:
        if ln.strip().startswith("```"):
            if in_code:
                html.append("</pre>")
            else:
                html.append("<pre style='background:rgba(120,120,120,24);padding:8px;border-radius:6px;'>")
            in_code = not in_code
            continue
        if in_code:
            html.append(ln.replace("&", "&amp;").replace("<", "&lt;"))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            lv = len(m.group(1))
            html.append(f"<h{lv}>{m.group(2)}</h{lv}>")
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            if not in_list:
                html.append("<ul>")
                in_list = True
            content = re.sub(r"^\s*[-*]\s+", "", ln)
            html.append(f"<li>{content}</li>")
            continue
        if in_list:
            html.append("</ul>")
            in_list = False
        if not ln.strip():
            continue
        ln = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ln)
        ln = re.sub(r"\*(.+?)\*", r"<i>\1</i>", ln)
        ln = re.sub(r"`(.+?)`", r"<code>\1</code>", ln)
        html.append(f"<p>{ln}</p>")
    if in_list:
        html.append("</ul>")
    if in_code:
        html.append("</pre>")
    return "\n".join(html)


def create_markdown_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("Markdown 预览 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    sp = QSplitter()
    ed = QPlainTextEdit()
    ed.setPlaceholderText("# 标题\n支持标题/加粗/斜体/行内代码/代码块/列表")
    from PySide6.QtWidgets import QTextBrowser
    view = QTextBrowser()
    sp.addWidget(ed)
    sp.addWidget(view)

    def update():
        view.setHtml(_md_to_html(ed.toPlainText()))

    ed.textChanged.connect(update)
    lay.addWidget(sp, stretch=1)
    return w


# ============================================================ 画图板
class _PaintCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage(800, 600, QImage.Format.Format_RGB32)
        self.image.fill(QColor("white"))
        self.color = QColor("black")
        self.width = 3
        self.erase = False
        self._last = QPoint()

    def mousePressEvent(self, e):
        self._last = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        p = QPainter(self.image)
        pen = QPen(QColor("white") if self.erase else self.color, self.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawLine(self._last, e.position().toPoint())
        self._last = e.position().toPoint()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawImage(0, 0, self.image)

    def clear(self):
        self.image.fill(QColor("white"))
        self.update()


def create_paint_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("画图板 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    canvas = _PaintCanvas()
    canvas.setMinimumSize(800, 600)

    def pick_color():
        c = QColorDialog.getColor(canvas.color, w)
        if c.isValid():
            canvas.color = c
            canvas.erase = False

    def save():
        p, _ = QFileDialog.getSaveFileName(w, "保存图片", "drawing.png", "PNG (*.png);;JPEG (*.jpg)")
        if p:
            canvas.image.save(p)
            out.setText(f"已保存到 {p}")

    b1 = QPushButton("颜色")
    b2 = QPushButton("橡皮")
    b3 = QPushButton("清空")
    b4 = QPushButton("保存")
    b1.clicked.connect(pick_color)
    b2.clicked.connect(lambda: setattr(canvas, "erase", True))
    b3.clicked.connect(canvas.clear)
    b4.clicked.connect(save)
    width_spin = QSpinBox()
    width_spin.setRange(1, 40)
    width_spin.setValue(3)
    width_spin.valueChanged.connect(lambda v: setattr(canvas, "width", v))

    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addWidget(QLabel("笔宽"))
    row.addWidget(width_spin)
    row.addWidget(b3)
    row.addWidget(b4)

    out = _out()
    lay.addWidget(canvas, stretch=1)
    lay.addLayout(row)
    lay.addWidget(out)
    return w


# ============================================================ 番茄钟
def create_pomodoro_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("番茄钟 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    status = QLabel("就绪")
    status.setStyleSheet("font-size: 30px; font-weight: bold; padding: 20px;")
    status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    work_spin = QSpinBox()
    work_spin.setRange(1, 120)
    work_spin.setValue(25)
    break_spin = QSpinBox()
    break_spin.setRange(1, 60)
    break_spin.setValue(5)
    out = _out("已完成 0 个番茄")

    timer = QTimer()
    timer.setInterval(1000)
    state = {"left": 0, "mode": "工作", "done": 0, "running": False}

    def tick():
        state["left"] -= 1
        if state["left"] <= 0:
            timer.stop()
            state["running"] = False
            if state["mode"] == "工作":
                state["done"] += 1
                state["mode"] = "休息"
                state["left"] = break_spin.value() * 60
            else:
                state["mode"] = "工作"
                state["left"] = work_spin.value() * 60
            out.setText(f"已完成 {state['done']} 个番茄")
            status.setText(f"{state['mode']}：{state['left'] // 60:02d}:{state['left'] % 60:02d}")
            timer.start()
            state["running"] = True
            return
        status.setText(f"{state['mode']}：{state['left'] // 60:02d}:{state['left'] % 60:02d}")

    def start():
        if state["running"]:
            return
        state["mode"] = "工作"
        state["left"] = work_spin.value() * 60
        state["running"] = True
        timer.start()
        status.setText(f"工作：{state['left'] // 60:02d}:{state['left'] % 60:02d}")

    def pause():
        timer.stop()
        state["running"] = False
        status.setText("已暂停")

    def reset():
        timer.stop()
        state.update({"left": 0, "mode": "工作", "done": 0, "running": False})
        status.setText("就绪")
        out.setText("已完成 0 个番茄")

    timer.timeout.connect(tick)
    b1 = QPushButton("开始")
    b2 = QPushButton("暂停")
    b3 = QPushButton("重置")
    b1.clicked.connect(start)
    b2.clicked.connect(pause)
    b3.clicked.connect(reset)
    row = QHBoxLayout()
    row.addWidget(b1)
    row.addWidget(b2)
    row.addWidget(b3)
    cfg = QHBoxLayout()
    cfg.addWidget(QLabel("工作(分钟)"))
    cfg.addWidget(work_spin)
    cfg.addWidget(QLabel("休息(分钟)"))
    cfg.addWidget(break_spin)
    cfg.addStretch(1)

    lay.addLayout(cfg)
    lay.addWidget(status)
    lay.addLayout(row)
    lay.addWidget(out)
    lay.addStretch(1)
    return w
