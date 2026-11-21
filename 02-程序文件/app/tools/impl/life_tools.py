"""生活工具组：倒计时/秒表 / 随机数抽签 / 密码生成器 / 亲戚称呼计算器。

全部零第三方依赖（PySide6 + 标准库）。
"""
from __future__ import annotations

import random
import secrets
import string

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


# ============================================================ 倒计时 / 秒表
def create_timer_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("倒计时秒表 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    display = QLabel("00:00:00")
    display.setStyleSheet("font-size: 44px; font-weight: bold; padding: 18px;")
    display.setAlignment(Qt.AlignmentFlag.AlignCenter)

    h_spin = QSpinBox()
    h_spin.setRange(0, 23)
    m_spin = QSpinBox()
    m_spin.setRange(0, 59)
    m_spin.setValue(5)
    s_spin = QSpinBox()
    s_spin.setRange(0, 59)

    timer = QTimer()
    timer.setInterval(1000)
    state = {"mode": "countdown", "left": 0, "ms": 0, "running": False}

    def fmt(sec: int) -> str:
        return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"

    def tick():
        if state["mode"] == "countdown":
            state["left"] -= 1
            if state["left"] <= 0:
                timer.stop()
                state["running"] = False
                display.setText("时间到！")
                return
            display.setText(fmt(state["left"]))
        else:
            state["left"] += 1
            display.setText(fmt(state["left"]))

    def start_countdown():
        state["mode"] = "countdown"
        state["left"] = h_spin.value() * 3600 + m_spin.value() * 60 + s_spin.value()
        if state["left"] <= 0:
            display.setText("请设置大于 0 的时间")
            return
        state["running"] = True
        timer.start()
        display.setText(fmt(state["left"]))

    def start_watch():
        state["mode"] = "watch"
        state["left"] = 0
        state["running"] = True
        timer.start()
        display.setText("00:00:00")

    def stop():
        timer.stop()
        state["running"] = False

    def reset():
        timer.stop()
        state["running"] = False
        state["left"] = 0
        display.setText("00:00:00")

    timer.timeout.connect(tick)
    cfg = QHBoxLayout()
    cfg.addWidget(QLabel("时"))
    cfg.addWidget(h_spin)
    cfg.addWidget(QLabel("分"))
    cfg.addWidget(m_spin)
    cfg.addWidget(QLabel("秒"))
    cfg.addWidget(s_spin)
    cfg.addStretch(1)

    b1 = QPushButton("开始倒计时")
    b2 = QPushButton("开始秒表")
    b3 = QPushButton("停止")
    b4 = QPushButton("重置")
    b1.clicked.connect(start_countdown)
    b2.clicked.connect(start_watch)
    b3.clicked.connect(stop)
    b4.clicked.connect(reset)
    row = QHBoxLayout()
    for b in (b1, b2, b3, b4):
        row.addWidget(b)

    lay.addWidget(display)
    lay.addLayout(cfg)
    lay.addLayout(row)
    lay.addStretch(1)
    return w


# ============================================================ 随机数 / 抽签
def create_random_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("随机数抽签 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    lo = QSpinBox()
    lo.setRange(-10 ** 9, 10 ** 9)
    lo.setValue(1)
    hi = QSpinBox()
    hi.setRange(-10 ** 9, 10 ** 9)
    hi.setValue(100)
    count = QSpinBox()
    count.setRange(1, 50)
    count.setValue(1)
    out = _out()

    def gen():
        a, b = lo.value(), hi.value()
        if a > b:
            a, b = b, a
        n = count.value()
        vals = [random.randint(a, b) for _ in range(n)]
        if n > 1:
            out.setText(f"随机数 {n} 个：{vals}　　和={sum(vals)}")
        else:
            out.setText(f"随机数：{vals[0]}")

    names = QPlainTextEdit()
    names.setPlaceholderText("抽签名单，每行一个名字")
    pick_count = QSpinBox()
    pick_count.setRange(1, 20)
    pick_count.setValue(1)
    out2 = _out()

    def pick():
        lines = [x.strip() for x in names.toPlainText().splitlines() if x.strip()]
        if not lines:
            out2.setText("请先输入名单（每行一个）")
            return
        k = min(pick_count.value(), len(lines))
        chosen = random.sample(lines, k)
        out2.setText(f"抽中 {k} 个：{'、'.join(chosen)}")

    b1 = QPushButton("生成随机数")
    b2 = QPushButton("抽签")
    b1.clicked.connect(gen)
    b2.clicked.connect(pick)
    cfg = QHBoxLayout()
    cfg.addWidget(QLabel("最小"))
    cfg.addWidget(lo)
    cfg.addWidget(QLabel("最大"))
    cfg.addWidget(hi)
    cfg.addWidget(QLabel("个数"))
    cfg.addWidget(count)
    cfg.addStretch(1)

    cfg2 = QHBoxLayout()
    cfg2.addWidget(QLabel("抽几个"))
    cfg2.addWidget(pick_count)
    cfg2.addStretch(1)

    lay.addWidget(QLabel("— 随机数 —"))
    lay.addLayout(cfg)
    lay.addWidget(b1)
    lay.addWidget(out)
    lay.addWidget(QLabel("— 随机抽签 —"))
    lay.addWidget(names, stretch=1)
    lay.addLayout(cfg2)
    lay.addWidget(b2)
    lay.addWidget(out2)
    return w


# ============================================================ 密码生成器
def create_password_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("密码生成器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    length = QSpinBox()
    length.setRange(4, 128)
    length.setValue(16)
    use_upper = QCheckBox("大写字母 A-Z")
    use_lower = QCheckBox("小写字母 a-z")
    use_digit = QCheckBox("数字 0-9")
    use_symbol = QCheckBox("符号 !@#$...")
    use_upper.setChecked(True)
    use_lower.setChecked(True)
    use_digit.setChecked(True)
    use_symbol.setChecked(True)
    result = QLineEdit()
    result.setReadOnly(True)
    out = _out()

    def gen():
        pool = ""
        if use_upper.isChecked():
            pool += string.ascii_uppercase
        if use_lower.isChecked():
            pool += string.ascii_lowercase
        if use_digit.isChecked():
            pool += string.digits
        if use_symbol.isChecked():
            pool += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        if not pool:
            out.setText("至少勾选一种字符类型")
            return
        pwd = "".join(secrets.choice(pool) for _ in range(length.value()))
        result.setText(pwd)
        out.setText(f"已生成 {length.value()} 位密码（使用密码学安全随机源）")

    def copy():
        from PySide6.QtWidgets import QApplication
        if result.text():
            QApplication.clipboard().setText(result.text())
            out.setText("已复制到剪贴板")

    b1 = QPushButton("生成密码")
    b2 = QPushButton("复制")
    b1.clicked.connect(gen)
    b2.clicked.connect(copy)
    cfg = QHBoxLayout()
    cfg.addWidget(QLabel("长度"))
    cfg.addWidget(length)
    cfg.addStretch(1)

    lay.addWidget(QLabel("随机密码生成"))
    lay.addLayout(cfg)
    lay.addWidget(use_upper)
    lay.addWidget(use_lower)
    lay.addWidget(use_digit)
    lay.addWidget(use_symbol)
    lay.addWidget(result)
    lay.addWidget(b1)
    lay.addWidget(b2)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 亲戚称呼计算器
def create_relative_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("亲戚称呼计算器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    rel = QComboBox()
    rel.addItems([
        "父亲", "母亲", "哥哥", "姐姐", "弟弟", "妹妹",
        "儿子", "女儿", "爷爷", "奶奶", "外公", "外婆",
        "伯父", "叔叔", "姑姑", "舅舅", "姨妈",
        "堂兄", "堂弟", "表哥", "表弟",
        "侄子", "外甥", "孙子", "外孙",
    ])
    side = QComboBox()
    side.addItems(["男方（父系）", "女方（母系）"])
    out = _out("选择亲属关系，计算对方怎么称呼你 / 你怎么称呼对方")

    TABLE = {
        "父亲": ("你是儿子/女儿", "爸爸"),
        "母亲": ("你是儿子/女儿", "妈妈"),
        "哥哥": ("你是弟弟/妹妹", "哥哥"),
        "姐姐": ("你是弟弟/妹妹", "姐姐"),
        "弟弟": ("你是哥哥/姐姐", "弟弟"),
        "妹妹": ("你是哥哥/姐姐", "妹妹"),
        "儿子": ("你是父亲/母亲", "儿子"),
        "女儿": ("你是父亲/母亲", "女儿"),
        "爷爷": ("你是孙子/孙女", "爷爷"),
        "奶奶": ("你是孙子/孙女", "奶奶"),
        "外公": ("你是外孙/外孙女", "外公（姥爷）"),
        "外婆": ("你是外孙/外孙女", "外婆（姥姥）"),
        "伯父": ("你是侄子/侄女", "伯父（大爷）"),
        "叔叔": ("你是侄子/侄女", "叔叔"),
        "姑姑": ("你是侄子/侄女", "姑姑"),
        "舅舅": ("你是外甥/外甥女", "舅舅"),
        "姨妈": ("你是外甥/外甥女", "姨妈"),
        "堂兄": ("你是堂弟/堂妹", "堂哥"),
        "堂弟": ("你是堂兄/堂姐", "堂弟"),
        "表哥": ("你是表弟/表妹", "表哥"),
        "表弟": ("你是表兄/表姐", "表弟"),
        "侄子": ("你是伯父/叔叔/姑姑", "侄子"),
        "外甥": ("你是舅舅/姨妈", "外甥"),
        "孙子": ("你是爷爷/奶奶", "孙子"),
        "外孙": ("你是外公/外婆", "外孙"),
    }

    def calc():
        name = rel.currentText()
        you, call = TABLE.get(name, ("", ""))
        out.setText(f"对方是你的「{name}」\n你称呼对方：{call}　　对方称呼你：{you}")

    btn = QPushButton("计算称呼")
    btn.clicked.connect(calc)
    lay.addWidget(QLabel("这位亲属是："))
    lay.addWidget(rel)
    lay.addWidget(side)
    lay.addWidget(btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w
