"""AI 助手：OpenAI 兼容接口的多模型壳（可切换服务商/本地 Ollama），密钥 DPAPI 加密保存。"""
from __future__ import annotations

import json
from pathlib import Path

import requests
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)

from app.core.paths import data_dir
from app.tools.impl.common import run_async, subtitle
from app.tools.impl.secure_store import protect, unprotect

CONFIG = "ai_config.json"

PRESETS = {
    "OpenAI": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "DeepSeek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "通义千问": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    "月之暗面": ("https://api.moonshot.cn/v1", "moonshot-v1-8k"),
    "本地 Ollama": ("http://localhost:11434/v1", "qwen2.5"),
    "自定义": ("", ""),
}


def load_config() -> dict:
    try:
        return json.loads((data_dir() / CONFIG).read_text(encoding="utf-8"))
    except Exception:
        return {"provider": "DeepSeek", "base": PRESETS["DeepSeek"][0],
                "model": PRESETS["DeepSeek"][1], "key_enc": ""}


def save_config(cfg: dict):
    (data_dir() / CONFIG).write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                                     encoding="utf-8")


def chat_request(cfg: dict, messages: list) -> str:
    key = unprotect(cfg.get("key_enc", ""))
    if not key and "localhost" not in cfg.get("base", ""):
        return ("【演示模式】尚未配置 API 密钥。点击「接口设置」填入密钥后即可与真实模型对话。"
                "当前支持 OpenAI / DeepSeek / 通义千问 / 月之暗面 / 本地 Ollama 及自定义兼容接口。")
    url = cfg["base"].rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    r = requests.post(url, headers=headers,
                      json={"model": cfg["model"], "messages": messages, "temperature": 0.7},
                      timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


class ConfigDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 接口设置")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.cmb = QComboBox()
        self.cmb.addItems(PRESETS.keys())
        self.cmb.setCurrentText(cfg.get("provider", "DeepSeek"))
        self.cmb.currentTextChanged.connect(self._preset)
        form.addRow("服务商", self.cmb)
        self.ed_base = QLineEdit(cfg.get("base", ""))
        self.ed_model = QLineEdit(cfg.get("model", ""))
        self.ed_key = QLineEdit()
        self.ed_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_key.setPlaceholderText("留空则使用演示模式 / 本地 Ollama 可免密钥")
        form.addRow("接口地址", self.ed_base)
        form.addRow("模型名", self.ed_model)
        form.addRow("API Key", self.ed_key)
        lay.addLayout(form)
        lay.addWidget(subtitle("API Key 使用 Windows DPAPI 加密后保存在本机配置中，不会以明文写入任何文件。"))
        b = QPushButton("保存")
        b.setObjectName("primary")
        b.setMinimumHeight(44)
        b.clicked.connect(self.accept)
        lay.addWidget(b)

    def _preset(self, name):
        base, model = PRESETS.get(name, ("", ""))
        self.ed_base.setText(base)
        self.ed_model.setText(model)

    def values(self, old: dict) -> dict:
        return {"provider": self.cmb.currentText(), "base": self.ed_base.text().strip(),
                "model": self.ed_model.text().strip(),
                "key_enc": protect(self.ed_key.text().strip()) if self.ed_key.text().strip()
                else old.get("key_enc", "")}


class AIChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 助手 · 基本工具集齐工具箱")
        self.resize(680, 620)
        lay = QVBoxLayout(self)
        self.cfg = load_config()
        self.messages = []

        bar = QHBoxLayout()
        self.lbl_model = QLabel(f"当前：{self.cfg['provider']} / {self.cfg['model']}")
        bar.addWidget(self.lbl_model)
        bar.addStretch(1)
        b = QPushButton("接口设置")
        b.clicked.connect(self._config)
        bar.addWidget(b)
        b2 = QPushButton("清空对话")
        b2.clicked.connect(self._clear)
        bar.addWidget(b2)
        lay.addLayout(bar)

        self.browser = QTextBrowser()
        self.browser.setHtml(
            "<p style='color:#6b7076'>👋 你好！我是内置 AI 助手。配置接口后即可开始对话；"
            "未配置时运行演示模式。</p>")
        lay.addWidget(self.browser, stretch=1)

        row = QHBoxLayout()
        self.ed = QLineEdit()
        self.ed.setPlaceholderText("输入消息，回车发送")
        self.ed.returnPressed.connect(self._send)
        row.addWidget(self.ed, stretch=1)
        b3 = QPushButton("发送")
        b3.setObjectName("primary")
        b3.setMinimumHeight(40)
        b3.clicked.connect(self._send)
        row.addWidget(b3)
        lay.addLayout(row)
        lay.addWidget(subtitle("多模型可随时切换；密钥仅保存在本机，由用户自行配置。"))

    def _config(self):
        dlg = ConfigDialog(self.cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cfg = dlg.values(self.cfg)
            save_config(self.cfg)
            self.lbl_model.setText(f"当前：{self.cfg['provider']} / {self.cfg['model']}")

    def _clear(self):
        self.messages.clear()
        self.browser.clear()

    def _append(self, who: str, text: str):
        color = "#2E7CF6" if who == "我" else "#1F2329"
        safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\n", "<br>"))
        self.browser.append(f"<p><b style='color:{color}'>{who}：</b><br>{safe}</p>")

    def _send(self):
        text = self.ed.text().strip()
        if not text:
            return
        self.ed.clear()
        self._append("我", text)
        self.messages.append({"role": "user", "content": text})
        self.browser.append("<p style='color:#6b7076'>AI 正在思考…</p>")
        run_async(lambda: chat_request(self.cfg, list(self.messages)),
                  self._on_reply,
                  lambda e: self._append("AI", f"请求失败：{e}"))

    def _on_reply(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self._append("AI", text)


def create_widget():
    return AIChatWindow()
