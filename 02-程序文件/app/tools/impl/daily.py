"""生活计算工具组：单位换算 / 进制转换 / 房贷 / 个税 / BMI / 时间戳 / 日期计算。

全部零第三方依赖（PySide6 + 标准库），纯计算无网络。
"""
from __future__ import annotations

import time
from datetime import date, datetime

from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


def _row(label: str, widget) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lab = QLabel(label)
    lab.setMinimumWidth(96)
    lay.addWidget(lab)
    lay.addWidget(widget, stretch=1)
    return w


def _out(text: str = "") -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size: 15px; padding: 8px; background: rgba(120,120,120,24); border-radius: 6px;")
    return lab


# ============================================================ 单位换算
_CATS = {
    "长度": {"毫米": 0.001, "厘米": 0.01, "米": 1.0, "千米": 1000.0,
             "英寸": 0.0254, "英尺": 0.3048, "英里": 1609.344, "海里": 1852.0},
    "重量": {"毫克": 1e-6, "克": 0.001, "千克": 1.0, "吨": 1000.0,
             "盎司": 0.0283495, "磅": 0.453592},
    "面积": {"平方厘米": 1e-4, "平方米": 1.0, "公顷": 1e4,
             "平方千米": 1e6, "亩": 666.6667, "英亩": 4046.856},
    "体积": {"毫升": 1e-6, "升": 1e-3, "立方米": 1.0, "加仑(美)": 0.00378541},
    "速度": {"米/秒": 1.0, "千米/时": 1 / 3.6, "英里/时": 0.44704, "节": 0.514444},
    "数据": {"字节": 1.0, "KB": 1024.0, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4},
}
_TEMP = {"摄氏度": "C", "华氏度": "F", "开尔文": "K"}


def create_unit_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("单位换算 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)

    cat = QComboBox()
    cat.addItems(list(_CATS.keys()) + ["温度"])
    unit_from = QComboBox()
    unit_to = QComboBox()
    value = QLineEdit()
    value.setPlaceholderText("输入数值")
    out = _out("换算结果将显示在这里")

    def refresh_units():
        unit_from.clear()
        unit_to.clear()
        items = list(_TEMP.keys()) if cat.currentText() == "温度" else list(_CATS[cat.currentText()].keys())
        unit_from.addItems(items)
        unit_to.addItems(items)
        if len(items) > 1:
            unit_to.setCurrentIndex(1)

    def convert():
        try:
            v = float(value.text().strip())
        except ValueError:
            out.setText("请输入合法数字")
            return
        c = cat.currentText()
        if c == "温度":
            f, t = unit_from.currentText(), unit_to.currentText()
            # 先归一到摄氏度
            if f == "摄氏度":
                cels = v
            elif f == "华氏度":
                cels = (v - 32) * 5 / 9
            else:
                cels = v - 273.15
            r = {"摄氏度": cels, "华氏度": cels * 9 / 5 + 32, "开尔文": cels + 273.15}[t]
            out.setText(f"{v} {f} = {r:.6g} {t}")
        else:
            table = _CATS[c]
            base = v * table[unit_from.currentText()]
            r = base / table[unit_to.currentText()]
            out.setText(f"{v} {unit_from.currentText()} = {r:.10g} {unit_to.currentText()}")

    btn = QPushButton("换算")
    btn.clicked.connect(convert)
    value.returnPressed.connect(convert)
    cat.currentTextChanged.connect(refresh_units)
    refresh_units()

    lay.addWidget(_row("换算类别", cat))
    lay.addWidget(_row("输入数值", value))
    lay.addWidget(_row("从", unit_from))
    lay.addWidget(_row("到", unit_to))
    lay.addWidget(btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 进制转换
def create_base_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("进制转换 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    lab = QLabel("输入十进制数，实时显示二/八/十六进制；也可直接输入 0x/0o/0b 前缀")
    lab.setWordWrap(True)
    src = QLineEdit()
    src.setPlaceholderText("例如 255 或 0xFF 或 0b1111")
    outs = {}
    grid = QGridLayout()
    for i, name in enumerate(["二进制", "八进制", "十进制", "十六进制"]):
        lab2 = QLabel(name)
        val = QLineEdit()
        val.setReadOnly(True)
        outs[name] = val
        grid.addWidget(lab2, i, 0)
        grid.addWidget(val, i, 1)

    def update():
        t = src.text().strip()
        if not t:
            for v in outs.values():
                v.clear()
            return
        try:
            n = int(t, 0) if t[:2].lower() in ("0x", "0o", "0b") else int(t, 10)
        except ValueError:
            outs["十进制"].setText("无法解析")
            return
        outs["二进制"].setText(bin(n))
        outs["八进制"].setText(oct(n))
        outs["十进制"].setText(str(n))
        outs["十六进制"].setText(hex(n))

    src.textChanged.connect(update)
    lay.addWidget(lab)
    lay.addWidget(_row("输入", src))
    lay.addLayout(grid)
    lay.addStretch(1)
    return w


# ============================================================ 房贷计算
def create_mortgage_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("房贷计算器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    amount = QLineEdit("100")
    amount.setPlaceholderText("贷款金额（万元）")
    years = QLineEdit("30")
    rate = QLineEdit("3.60")
    rate.setPlaceholderText("年利率 %")
    out = _out()

    def calc():
        try:
            p = float(amount.text()) * 10000
            y = float(years.text())
            r = float(rate.text()) / 100 / 12
            n = int(y * 12)
            if p <= 0 or n <= 0:
                raise ValueError
        except ValueError:
            out.setText("请输入合法的贷款金额 / 年限 / 利率")
            return
        if r == 0:
            m1 = p / n
            total1 = p
        else:
            m1 = p * r * (1 + r) ** n / ((1 + r) ** n - 1)
            total1 = m1 * n
        # 等额本金
        princ = p / n
        total2 = 0.0
        for i in range(n):
            total2 += (p - princ * i) * r + princ
        m2_first = p / n + p * r
        m2_last = p / n + (p / n) * r
        out.setText(
            f"等额本息：月供 {m1:,.2f} 元，总利息 {total1 - p:,.2f} 元，还款总额 {total1:,.2f} 元\n"
            f"等额本金：首月 {m2_first:,.2f} 元，末月 {m2_last:,.2f} 元，"
            f"总利息 {total2 - p:,.2f} 元，还款总额 {total2:,.2f} 元"
        )

    btn = QPushButton("计算")
    btn.clicked.connect(calc)
    lay.addWidget(_row("贷款金额(万)", amount))
    lay.addWidget(_row("贷款年限", years))
    lay.addWidget(_row("年利率(%)", rate))
    lay.addWidget(btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 个税计算
_BRACKETS = [
    (36000, 0.03, 0), (144000, 0.10, 2520), (300000, 0.20, 16920),
    (420000, 0.25, 31920), (660000, 0.30, 52920), (960000, 0.35, 85920),
    (float("inf"), 0.45, 181920),
]


def create_tax_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("个税计算器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    salary = QLineEdit()
    salary.setPlaceholderText("税前月薪（元）")
    insurance = QLineEdit("0")
    insurance.setPlaceholderText("个人五险一金（元）")
    special = QLineEdit("0")
    special.setPlaceholderText("专项附加扣除（元）")
    out = _out()

    def calc():
        try:
            s = float(salary.text())
            ins = float(insurance.text() or 0)
            sp = float(special.text() or 0)
        except ValueError:
            out.setText("请输入合法数字")
            return
        taxable = max(0.0, s - ins - sp - 5000)
        tax = 0.0
        for cap, rate, deduct in _BRACKETS:
            if taxable <= cap:
                tax = taxable * rate - deduct
                break
        tax = max(0.0, tax)
        out.setText(
            f"应纳税所得额：{taxable:,.2f} 元/月\n"
            f"应缴个税：{tax:,.2f} 元/月\n"
            f"税后收入：{s - ins - tax:,.2f} 元/月"
        )

    btn = QPushButton("计算")
    btn.clicked.connect(calc)
    lay.addWidget(_row("税前月薪", salary))
    lay.addWidget(_row("五险一金", insurance))
    lay.addWidget(_row("专项附加", special))
    lay.addWidget(btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ BMI
def create_bmi_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("BMI 计算器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    height = QLineEdit()
    height.setPlaceholderText("身高（厘米）")
    weight = QLineEdit()
    weight.setPlaceholderText("体重（千克）")
    out = _out()

    def calc():
        try:
            h = float(height.text()) / 100
            wt = float(weight.text())
            if h <= 0 or wt <= 0:
                raise ValueError
            bmi = wt / (h * h)
        except ValueError:
            out.setText("请输入合法的身高和体重")
            return
        if bmi < 18.5:
            level = "偏瘦"
        elif bmi < 24:
            level = "正常"
        elif bmi < 28:
            level = "偏胖"
        else:
            level = "肥胖"
        ideal_lo, ideal_hi = 18.5 * h * h, 23.9 * h * h
        out.setText(
            f"BMI = {bmi:.1f}（{level}）\n"
            f"健康体重参考范围：{ideal_lo:.1f} ~ {ideal_hi:.1f} 千克"
        )

    btn = QPushButton("计算")
    btn.clicked.connect(calc)
    lay.addWidget(_row("身高(cm)", height))
    lay.addWidget(_row("体重(kg)", weight))
    lay.addWidget(btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 时间戳
def create_timestamp_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("时间戳转换 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    ts_in = QLineEdit()
    ts_in.setPlaceholderText("Unix 时间戳（秒，支持小数）")
    date_in = QLineEdit()
    date_in.setPlaceholderText("日期时间 例如 2026-01-01 12:00:00")
    out = _out()
    now_btn = QPushButton("填入当前时间")

    def to_date():
        t = ts_in.text().strip()
        if not t:
            return
        try:
            sec = float(t)
            dt = datetime.fromtimestamp(sec)
            out.setText(f"时间戳 {t} → {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            out.setText(f"转换失败：{e}")

    def to_ts():
        t = date_in.text().strip()
        if not t:
            return
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
            try:
                dt = datetime.strptime(t, fmt)
                out.setText(f"{t} → 时间戳 {dt.timestamp():.0f}")
                return
            except ValueError:
                continue
        out.setText("日期格式无法识别，请用 2026-01-01 12:00:00 格式")

    def fill_now():
        now = time.time()
        ts_in.setText(f"{now:.0f}")
        date_in.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        out.setText(f"当前时间戳：{now:.0f}")

    b1 = QPushButton("时间戳 → 日期")
    b2 = QPushButton("日期 → 时间戳")
    b1.clicked.connect(to_date)
    b2.clicked.connect(to_ts)
    now_btn.clicked.connect(fill_now)

    lay.addWidget(_row("时间戳", ts_in))
    lay.addWidget(b1)
    lay.addWidget(_row("日期时间", date_in))
    lay.addWidget(b2)
    lay.addWidget(now_btn)
    lay.addWidget(out)
    lay.addStretch(1)
    return w


# ============================================================ 日期计算器
def create_datecalc_widget() -> QWidget:
    w = QWidget()
    w.setWindowTitle("日期计算器 · 基本工具集齐工具箱")
    lay = QVBoxLayout(w)
    d1 = QLineEdit()
    d1.setPlaceholderText("起始日期 2026-01-01")
    d2 = QLineEdit()
    d2.setPlaceholderText("结束日期 2026-06-01")
    days = QLineEdit("30")
    days.setPlaceholderText("加减天数")
    out = _out()

    def parse(s: str) -> date:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()

    def diff():
        try:
            a, b = parse(d1.text()), parse(d2.text())
            delta = (b - a).days
            out.setText(f"{a} 到 {b} 相差 {delta} 天（约 {abs(delta) / 30.44:.1f} 个月）")
        except Exception:
            out.setText("日期格式请用 2026-01-01")

    def add():
        try:
            a = parse(d1.text())
            n = int(days.text())
            r = a.fromordinal(a.toordinal() + n)
            out.setText(f"{a} {'+' if n >= 0 else '-'} {abs(n)} 天 = {r}（星期{'一二三四五六日'[r.weekday()]}）")
        except Exception:
            out.setText("起始日期或天数不合法")

    b1 = QPushButton("计算日期差")
    b2 = QPushButton("起始日期加减天数")
    b1.clicked.connect(diff)
    b2.clicked.connect(add)

    lay.addWidget(_row("起始日期", d1))
    lay.addWidget(_row("结束日期", d2))
    lay.addWidget(b1)
    lay.addWidget(_row("加减天数", days))
    lay.addWidget(b2)
    lay.addWidget(out)
    lay.addStretch(1)
    return w
