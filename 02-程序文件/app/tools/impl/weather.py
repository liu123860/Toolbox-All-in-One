"""天气：Open-Meteo 免密钥 API（城市搜索 → 当前天气 + 7 日预报），带本地缓存。

合规提示：本软件为开源非商业项目，符合 Open-Meteo 免费档（<1万次/日）使用条件；
若未来转为商业用途，须先切换为商业授权数据源或由用户自备 API。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core.paths import data_dir
from app.tools.impl.common import run_async, subtitle

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_FILE = "weather_cache.json"
CACHE_TTL = 600

WMO = {
    0: ("☀️", "晴"), 1: ("🌤", "大部晴朗"), 2: ("⛅", "局部多云"), 3: ("☁️", "阴"),
    45: ("🌫", "雾"), 48: ("🌫", "雾凇"), 51: ("🌦", "小毛毛雨"), 53: ("🌦", "毛毛雨"),
    55: ("🌧", "大毛毛雨"), 61: ("🌦", "小雨"), 63: ("🌧", "中雨"), 65: ("🌧", "大雨"),
    71: ("🌨", "小雪"), 73: ("🌨", "中雪"), 75: ("❄️", "大雪"), 80: ("🌦", "阵雨"),
    81: ("🌧", "强阵雨"), 82: ("⛈", "暴雨"), 95: ("⛈", "雷阵雨"),
    96: ("⛈", "雷阵雨伴冰雹"), 99: ("⛈", "强雷暴伴冰雹"),
}


def geo_city(name: str):
    r = requests.get(GEO_URL, params={"name": name, "count": 5, "language": "zh"}, timeout=6)
    r.raise_for_status()
    return r.json().get("results", [])


def fetch_weather(lat: float, lon: float) -> dict:
    """主源 Open-Meteo（7 日预报）→ 不可达时自动回退 wttr.in（3 日预报）。"""
    try:
        return _open_meteo(lat, lon)
    except Exception:
        return _wttr(lat, lon)


def _open_meteo(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "weather_code,wind_speed_10m,precipitation",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset",
        "timezone": "auto", "forecast_days": 7,
    }
    for attempt in range(2):                       # 网络波动时重试一次
        try:
            r = requests.get(FORECAST_URL, params=params, timeout=6)
            r.raise_for_status()
            data = r.json()
            data["source"] = "Open-Meteo"
            return data
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 1:
                raise
    return {}


WTTR_TO_WMO = {
    113: 0, 116: 2, 119: 3, 122: 3, 143: 45, 176: 80, 179: 71, 182: 61,
    185: 61, 200: 95, 227: 71, 230: 75, 248: 45, 260: 45, 263: 51, 266: 53,
    293: 61, 296: 61, 299: 63, 302: 65, 305: 65, 308: 65, 311: 55, 314: 55,
    317: 61, 320: 71, 323: 71, 326: 71, 329: 73, 332: 73, 335: 75, 338: 75,
    350: 61, 353: 80, 356: 81, 359: 65, 362: 61, 365: 61, 368: 71, 371: 75,
    374: 51, 377: 51, 386: 95, 389: 95, 392: 95, 395: 75,
}


def _wttr(lat: float, lon: float) -> dict:
    """备用数据源：wttr.in（免密钥），归一化为与 Open-Meteo 相同的结构。"""
    url = f"https://wttr.in/~{lat:.2f},{lon:.2f}?format=j1&lang=zh"
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    d = r.json()
    c = d["current_condition"][0]
    days = d.get("weather", [])
    daily = {
        "time": [x["date"] for x in days],
        "weather_code": [WTTR_TO_WMO.get(int(x["hourly"][4]["weatherCode"]), 3)
                         for x in days],
        "temperature_2m_max": [float(x["maxtempC"]) for x in days],
        "temperature_2m_min": [float(x["mintempC"]) for x in days],
        "precipitation_probability_max": [
            max((int(h["chanceofrain"]) for h in x["hourly"]), default=0) for x in days],
        "sunrise": [x["astronomy"][0]["sunrise"] for x in days],
        "sunset": [x["astronomy"][0]["sunset"] for x in days],
    }
    return {
        "source": "wttr.in（备用源）",
        "current": {
            "temperature_2m": float(c["temp_C"]),
            "apparent_temperature": float(c["FeelsLikeC"]),
            "relative_humidity_2m": int(c["humidity"]),
            "wind_speed_10m": float(c.get("windspeedKmph", 0)),
            "weather_code": WTTR_TO_WMO.get(int(c.get("weatherCode", 119)), 3),
            "precipitation": float(c.get("precipMM", 0)),
        },
        "daily": daily,
    }


def _cache_path() -> Path:
    return data_dir() / CACHE_FILE


def cache_save(payload: dict):
    try:
        _cache_path().write_text(json.dumps({"ts": time.time(), "data": payload},
                                           ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def cache_load():
    try:
        obj = json.loads(_cache_path().read_text(encoding="utf-8"))
        if time.time() - obj["ts"] < CACHE_TTL * 6:
            return obj["data"]
    except Exception:
        pass
    return None


class WeatherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("天气 · 基本工具集齐工具箱")
        self.resize(620, 520)
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        self.ed_city = QLineEdit("北京")
        self.ed_city.setPlaceholderText("输入城市名（中英文均可）")
        btn = QPushButton("查询")
        btn.setObjectName("primary")
        btn.clicked.connect(self._search)
        row.addWidget(self.ed_city)
        row.addWidget(btn)
        lay.addLayout(row)

        self.cmb_city = QComboBox()
        self.cmb_city.currentIndexChanged.connect(self._load_selected)
        lay.addWidget(self.cmb_city)

        self.lbl_now = QLabel("正在使用缓存/等待查询…")
        self.lbl_now.setStyleSheet("font-size: 22px; padding: 12px;")
        self.lbl_now.setWordWrap(True)
        lay.addWidget(self.lbl_now)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "天气", "最高/最低", "降水概率", "日出/日落"])
        self.table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.table)

        self.src_label = subtitle("数据源：Open-Meteo（主）/ wttr.in（备用）。离线时显示上次缓存。")
        lay.addWidget(self.src_label)

        cached = cache_load()
        if cached:
            self._render(cached)

    # ------------------------------------------------------------ 查询
    def _search(self):
        name = self.ed_city.text().strip()
        if len(name) < 2:
            self.lbl_now.setText("请输入至少 2 个字符的城市名")
            return
        self.lbl_now.setText("正在查询城市…")
        run_async(lambda: geo_city(name), self._on_cities,
                  lambda e: self.lbl_now.setText(f"城市查询失败：{e}（显示缓存数据）"))

    def _on_cities(self, results):
        self.cmb_city.blockSignals(True)
        self.cmb_city.clear()
        if not results:
            self.lbl_now.setText("未找到该城市，请换个名称试试")
            self.cmb_city.blockSignals(False)
            return
        for c in results:
            label = " / ".join(x for x in (c.get("name"), c.get("admin1"), c.get("country")) if x)
            self.cmb_city.addItem(label, (c["latitude"], c["longitude"], c.get("name", "")))
        self.cmb_city.blockSignals(False)
        self._load_selected(0)

    def _load_selected(self, idx: int):
        if idx < 0 or self.cmb_city.count() == 0:
            return
        lat, lon, name = self.cmb_city.itemData(idx)
        self.lbl_now.setText(f"正在获取 {name} 的天气…")
        run_async(lambda: fetch_weather(lat, lon),
                  lambda data: self._on_weather(data, name),
                  lambda e: self.lbl_now.setText(f"天气获取失败：{e}\n可稍后重试或查看缓存"))

    # ------------------------------------------------------------ 渲染
    def _on_weather(self, data: dict, city: str):
        cache_save({"city": city, "data": data})
        self._render({"city": city, "data": data})

    def _render(self, payload: dict):
        city, data = payload["city"], payload["data"]
        self.src_label.setText(
            f"数据源：{data.get('source', 'Open-Meteo')}（免密钥）。"
            "免费档仅限非商业用途，正式商业发布前须切换商业授权数据源。"
            "离线时显示上次缓存。")
        cur = data.get("current", {})
        code = int(cur.get("weather_code", 0))
        icon, desc = WMO.get(code, ("•", "未知天气"))
        self.lbl_now.setText(
            f"{icon} {city}  {cur.get('temperature_2m', '--')}°C  {desc}\n"
            f"体感 {cur.get('apparent_temperature', '--')}°C · "
            f"湿度 {cur.get('relative_humidity_2m', '--')}% · "
            f"风速 {cur.get('wind_speed_10m', '--')} km/h")
        daily = data.get("daily", {})
        times = daily.get("time", [])
        self.table.setRowCount(len(times))
        for i, d in enumerate(times):
            ic, ds = WMO.get(int(daily.get("weather_code", [0] * 7)[i]), ("•", "未知"))
            vals = [
                d, f"{ic} {ds}",
                f"{daily.get('temperature_2m_max', ['--'] * 7)[i]}° / "
                f"{daily.get('temperature_2m_min', ['--'] * 7)[i]}°",
                f"{daily.get('precipitation_probability_max', ['--'] * 7)[i]}%",
                f"{str(daily.get('sunrise', ['--'] * 7)[i])[-5:]} / "
                f"{str(daily.get('sunset', ['--'] * 7)[i])[-5:]}",
            ]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))


def create_widget():
    return WeatherWindow()
