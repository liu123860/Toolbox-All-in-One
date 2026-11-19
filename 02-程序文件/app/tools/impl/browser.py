"""内置浏览器：QtWebEngine（Chromium 内核）多标签页，免单独安装浏览器。

阶段5 打包注意：PyInstaller 需手动带上 QtWebEngineProcess.exe 与 resources/webview 插件，
否则打包后网页空白（已记入 06 文档打包检查清单）。
"""
from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.tools.impl.common import subtitle

HOME_HTML = """
<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>工具箱起始页</title>
<style>
body{margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;
justify-content:center;background:linear-gradient(160deg,#f5f7fb,#e8eefc);
font-family:'Microsoft YaHei',sans-serif;color:#1f2329}
h1{font-size:34px;margin:0 0 10px}p{color:#6b7076;margin:6px}
.box{margin-top:24px;background:#fff;border-radius:14px;padding:22px 34px;
box-shadow:0 8px 30px rgba(46,124,246,.12)}
a{color:#2e7cf6;text-decoration:none;margin:0 12px}
</style></head><body>
<h1>🧰 基本工具集齐工具箱</h1>
<p>内置浏览器 · 无需下载安装 · 开箱即用</p>
<div class="box">
<a href="https://www.baidu.com">百度</a>
<a href="https://www.bing.com">必应</a>
<a href="https://open-meteo.com">Open-Meteo</a>
<a href="https://www.python.org">Python</a>
</div><p style="margin-top:20px;font-size:12px">在上方地址栏输入网址开始浏览</p>
</body></html>
"""


def _normalize(text: str) -> QUrl:
    text = text.strip()
    if not text:
        return QUrl("about:blank")
    if text.startswith(("http://", "https://", "file://", "about:")):
        return QUrl(text)
    if "." in text and " " not in text:
        return QUrl("https://" + text)
    return QUrl("https://www.baidu.com/s?wd=" + QUrl.toPercentEncoding(text).data().decode())


class BrowserWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("浏览器 · 基本工具集齐工具箱")
        self.resize(1000, 700)
        lay = QVBoxLayout(self)

        nav = QHBoxLayout()
        for text, slot in (("←", self._back), ("→", self._forward),
                           ("⟳", self._reload), ("⌂", self._home)):
            b = QPushButton(text)
            b.setFixedWidth(42)
            b.setMinimumHeight(36)
            b.clicked.connect(slot)
            nav.addWidget(b)
        self.addr = QLineEdit()
        self.addr.setPlaceholderText("输入网址或搜索内容，回车访问")
        self.addr.returnPressed.connect(self._go)
        nav.addWidget(self.addr, stretch=1)
        b = QPushButton("前往")
        b.setObjectName("primary")
        b.clicked.connect(self._go)
        nav.addWidget(b)
        b2 = QPushButton("＋ 新标签")
        b2.clicked.connect(self._new_tab)
        nav.addWidget(b2)
        lay.addLayout(nav)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._sync_addr)
        lay.addWidget(self.tabs, stretch=1)
        lay.addWidget(subtitle("基于 QtWebEngine（Chromium）的多标签浏览器。"))
        self._new_tab()

    def _view(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def _new_tab(self):
        v = QWebEngineView()
        v.setHtml(HOME_HTML)
        v.urlChanged.connect(lambda url: self._on_url_changed(v, url))
        v.titleChanged.connect(lambda t: self.tabs.setTabText(self.tabs.indexOf(v), t[:14] or "起始页"))
        i = self.tabs.addTab(v, "起始页")
        self.tabs.setCurrentIndex(i)

    def _on_url_changed(self, view, url: QUrl):
        if view is self._view():
            self.addr.setText(url.toString())
        if self.tabs.indexOf(view) >= 0 and url.toString() != "about:blank":
            host = url.host() or "起始页"
            self.tabs.setTabText(self.tabs.indexOf(view), host[:16])

    def _sync_addr(self, idx):
        if idx >= 0 and self.tabs.widget(idx):
            url = self.tabs.widget(idx).url().toString()
            self.addr.setText("" if url in ("about:blank", "") else url)

    def _go(self):
        self._view().load(_normalize(self.addr.text()))

    def _back(self):
        self._view().back()

    def _forward(self):
        self._view().forward()

    def _reload(self):
        self._view().reload()

    def _home(self):
        self._view().setHtml(HOME_HTML)

    def _close_tab(self, idx):
        if self.tabs.count() > 1:
            w = self.tabs.widget(idx)
            self.tabs.removeTab(idx)
            w.deleteLater()


def create_widget():
    return BrowserWindow()
