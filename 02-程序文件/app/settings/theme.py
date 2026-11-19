"""全局主题样式表（QSS）生成：颜色/密度实时联动，保证可读性。"""
from __future__ import annotations

from PySide6.QtGui import QColor

from app.settings.manager import SettingsManager


def _is_dark(settings: SettingsManager) -> bool:
    mode = str(settings.get("color.mode"))
    if mode == "dark":
        return True
    if mode == "light":
        return False
    # auto：跟随系统（Windows 浅色为默认，深色检测通过注册表）
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return val == 0
    except Exception:
        return False


def palette(settings: SettingsManager) -> dict:
    accent = str(settings.get("color.accent"))
    dark = _is_dark(settings)
    if dark:
        return {
            "accent": accent, "accent_text": "#FFFFFF",
            "bg": "#1E1F24", "panel": "#26272E", "card": "#2D2F37",
            "text": "#E6E7EB", "text_sub": "#A6A8B0", "border": "#3A3C45",
        }
    return {
        "accent": accent, "accent_text": "#FFFFFF",
        "bg": "#F5F6F8", "panel": "#FFFFFF", "card": "#FFFFFF",
        "text": "#1F2329", "text_sub": "#6B7076", "border": "#E2E4E8",
    }


def _contrast_ok(fg: str, bg: str) -> bool:
    """简单对比度校验（WCAG 思路），不足时提亮/加深强调色。"""
    def lum(c: QColor) -> float:
        r, g, b = c.red() / 255, c.green() / 255, c.blue() / 255
        def adj(v):
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * adj(r) + 0.7152 * adj(g) + 0.0722 * adj(b)
    l1, l2 = lum(QColor(fg)), lum(QColor(bg))
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return ratio >= 3.0


def safe_accent(p: dict) -> str:
    accent, text = p["accent"], p["text"]
    tries = 0
    while not _contrast_ok(accent, text) and tries < 8:
        c = QColor(accent)
        if c.lightness() > 128:
            c = c.darker(115)
        else:
            c = c.lighter(115)
        accent = c.name()
        tries += 1
    return accent


def build_qss(settings: SettingsManager) -> str:
    p = palette(settings)
    accent = safe_accent(p)
    f = settings.font_px()
    pad = settings.pad()
    radius = 8 if settings.get("effects.shadow") else 6
    card_shadow = "border: 1px solid {border};".format(**p)
    return f"""
    QWidget {{ font-family: "Microsoft YaHei", "Segoe UI"; font-size: {f}px;
              color: {p['text']}; background: {p['bg']}; }}
    QMainWindow, QDialog {{ background: {p['bg']}; }}
    QFrame#topbar, QFrame#sidebar {{ background: {p['panel']}; border: none; }}
    QLineEdit, QComboBox, QSpinBox {{
        background: {p['bg']}; border: 1px solid {p['border']};
        border-radius: {radius}px; padding: {max(4, pad // 2)}px {pad}px; color: {p['text']};
    }}
    QLineEdit:focus {{ border: 1px solid {accent}; }}
    QPushButton {{
        background: {p['panel']}; border: 1px solid {p['border']};
        border-radius: {radius}px; padding: {pad}px {pad * 2}px; color: {p['text']};
    }}
    QPushButton:hover {{ border-color: {accent}; color: {accent}; }}
    QPushButton:pressed {{ background: {p['card']}; }}
    QPushButton#primary, QPushButton#accent {{
        background: {accent}; border: none; color: {p['accent_text']}; font-weight: 600;
    }}
    QPushButton#primary:hover, QPushButton#accent:hover {{ opacity: 0.9; }}
    QToolButton {{
        background: transparent; border: none; padding: {pad}px; border-radius: {radius}px;
    }}
    QToolButton:hover {{ background: {p['card']}; }}
    QListWidget, QListView {{ background: {p['panel']}; border: none; outline: none; }}
    QListWidget::item {{ padding: {pad + 2}px {pad + 4}px; border-radius: {radius}px; color: {p['text_sub']}; }}
    QListWidget::item:selected {{ background: {accent}; color: {p['accent_text']}; }}
    QScrollArea {{ background: {p['bg']}; border: none; }}
    QGroupBox {{
        border: 1px solid {p['border']}; border-radius: {radius}px;
        margin-top: {f + pad}px; padding-top: {pad}px; font-weight: 600;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: {pad}px; color: {p['text_sub']}; }}
    QTabWidget::pane {{ border: 1px solid {p['border']}; border-radius: {radius}px; background: {p['panel']}; }}
    QTabBar::tab {{ padding: {pad}px {pad * 2}px; color: {p['text_sub']}; border: none; }}
    QTabBar::tab:selected {{ color: {accent}; border-bottom: 2px solid {accent}; }}
    QStatusBar {{ background: {p['panel']}; border-top: 1px solid {p['border']}; color: {p['text_sub']}; }}
    QFrame#card {{ background: {p['card']}; {card_shadow} border-radius: {radius}px; }}
    QLabel#subtle {{ color: {p['text_sub']}; }}
    QLabel#title {{ font-size: {f + 4}px; font-weight: 700; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: {f + 4}px; height: {f + 4}px; }}
    QSlider::groove:horizontal {{ height: 4px; background: {p['border']}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
    QScrollBar:vertical {{ width: 8px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 30px; }}
    QScrollBar:horizontal {{ height: 8px; background: transparent; }}
    QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 4px; min-width: 30px; }}
    """
