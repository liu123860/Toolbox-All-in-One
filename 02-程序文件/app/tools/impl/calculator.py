"""计算器：科学计算 + 历史记录（自研，零依赖，AST 安全求值不执行任意代码）。"""
from __future__ import annotations

import ast
import math
import operator
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLineEdit, QListWidget, QPushButton,
    QVBoxLayout, QWidget,
)

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log10, "ln": math.log, "abs": abs, "round": round,
    "pi": math.pi, "e": math.e,
}


def safe_eval(expr: str) -> str:
    """只允许数字、四则运算和少量数学函数；拒绝任何名称/属性/调用黑名单。"""
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    expr = expr.replace("π", "pi").replace("√", "sqrt")

    def _walk(node):
        if isinstance(node, ast.Expression):
            return _walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_walk(node.left), _walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_walk(node.operand))
        if isinstance(node, ast.Name) and node.id in _FUNCS and not callable(_FUNCS[node.id]):
            return _FUNCS[node.id]                     # 常量 pi / e
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = _FUNCS.get(node.func.id)
            if callable(fn) and len(node.args) == 1:
                return fn(_walk(node.args[0]))
        raise ValueError("表达式含不支持的内容")

    try:
        val = _walk(ast.parse(expr, mode="eval"))
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise ValueError("结果无效")
        return f"{val:.10g}" if isinstance(val, float) else str(val)
    except ZeroDivisionError:
        return "错误：除数不能为 0"
    except Exception as e:
        return f"错误：{e}"


class CalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算器 · 基本工具集齐工具箱")
        self.resize(420, 480)
        lay = QVBoxLayout(self)

        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setStyleSheet("font-size: 26px; padding: 10px;")
        lay.addWidget(self.display)
        self.hint = QLineEdit("")
        self.hint.setReadOnly(True)
        self.hint.setPlaceholderText("支持 + - * / ^ % 及 sqrt() sin() log() π")
        lay.addWidget(self.hint)

        grid = QGridLayout()
        buttons = [
            ["C", "⌫", "(", ")", "%"],
            ["7", "8", "9", "÷", "sqrt("],
            ["4", "5", "6", "×", "x²"],
            ["1", "2", "3", "−", "1/x"],
            ["0", ".", "π", "+", "="],
        ]
        for r, row in enumerate(buttons):
            for c, text in enumerate(row):
                b = QPushButton(text)
                b.setMinimumHeight(44)
                b.clicked.connect(lambda checked=False, t=text: self._press(t))
                if text == "=":
                    b.setObjectName("primary")
                grid.addWidget(b, r, c)
        lay.addLayout(grid)

        lay.addWidget(QPushButton("清空历史", clicked=self._clear_history))
        self.history = QListWidget()
        self.history.setMaximumHeight(120)
        self.history.itemDoubleClicked.connect(
            lambda item: self.display.setText(item.text().split(" = ")[-1]))
        lay.addWidget(self.history)

    def _expr(self) -> str:
        return self.display.text()

    def _press(self, t: str):
        cur = self._expr()
        if t == "C":
            self.display.setText("0")
        elif t == "⌫":
            self.display.setText(cur[:-1] or "0")
        elif t in ("+", "−", "×", "÷", "(", ")", ".", "%"):
            self.display.setText((cur if cur != "0" else "") + t)
        elif t.isdigit() or t == "π":
            self.display.setText((cur if cur != "0" else "") + t)
        elif t == "sqrt(":
            self.display.setText((cur if cur != "0" else "") + "sqrt(")
        elif t == "x²":
            self.display.setText(f"({cur})**2")
        elif t == "1/x":
            self.display.setText(f"1/({cur})")
        elif t == "=":
            expr = cur
            res = safe_eval(expr)
            self.display.setText(res)
            self.history.insertItem(0, f"{expr} = {res}   [{datetime.now():%H:%M}]")
            self.hint.setText(expr)

    def _clear_history(self):
        self.history.clear()


def create_widget():
    return CalculatorWindow()
