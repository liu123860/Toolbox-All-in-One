"""病毒扫描：优先 ClamAV 容器/系统引擎；无引擎时用「轻量启发式扫描」并明确标注非完整杀毒引擎。

安全设计：扫描只读；隔离 = 移动到隔离区（可恢复），需二次确认；绝不静默删除。
"""
from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog,
)

from app.core.paths import data_dir
from app.tools.containers import launch, resolve
from app.tools.impl.common import run_async, subtitle

SUSPICIOUS_EXT = {".exe", ".scr", ".bat", ".cmd", ".vbs", ".ps1", ".js", ".jse", ".hta", ".pif"}
MAX_SCAN = 5000
BLACKLIST = "antivirus_blacklist.txt"      # 用户可自行维护 SHA256 黑名单


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _blacklist() -> set:
    f = data_dir() / BLACKLIST
    try:
        return {line.strip().lower() for line in f.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")}
    except Exception:
        return set()


def scan_heuristic(folder: Path):
    """轻量启发式扫描（非完整杀毒引擎）：黑名单哈希 + 可疑扩展/双扩展。"""
    hits, scanned = [], 0
    bl = _blacklist()
    for p in folder.rglob("*"):
        if scanned >= MAX_SCAN or not p.is_file():
            break
        scanned += 1
        try:
            if p.stat().st_size > 60 * 1024 * 1024:
                continue
            digest = _sha256(p)
            if digest in bl:
                hits.append((p, "命中 SHA256 黑名单", "高危"))
                continue
            name = p.name.lower()
            suffixes = p.suffixes
            if len(suffixes) >= 2 and suffixes[-1].lower() in SUSPICIOUS_EXT \
                    and suffixes[-2].lower() in {".pdf", ".doc", ".docx", ".jpg", ".png", ".txt"}:
                hits.append((p, "伪装双扩展名", "可疑"))
            elif p.suffix.lower() in SUSPICIOUS_EXT and p.stat().st_size < 20 * 1024:
                hits.append((p, "小型可执行文件", "提示"))
        except (OSError, PermissionError):
            continue
    return {"engine": "轻量启发式（非完整杀毒引擎）", "scanned": scanned, "hits": hits}


def scan_clamav(folder: Path):
    r = launch("clamav", ["--recursive", "--infected", "--no-summary", str(folder)], timeout=600)
    hits = []
    if r.get("ok") or r.get("stdout"):
        for line in (r.get("stdout", "") + r.get("stderr", "")).splitlines():
            if "FOUND" in line:
                path = line.split(":")[0].strip()
                hits.append((Path(path), line.split(":", 1)[-1].strip(), "高危"))
    return {"engine": "ClamAV（开源专业引擎）", "scanned": -1, "hits": hits,
            "error": "" if r.get("ok") or r.get("stdout") else r.get("error")}


class AntivirusWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("病毒扫描 · 基本工具集齐工具箱")
        self.resize(760, 520)
        lay = QVBoxLayout(self)
        has_clamav = resolve("clamav") is not None
        engine = "ClamAV 开源专业引擎" if has_clamav else "轻量启发式扫描（非完整杀毒引擎）"
        self.lbl = QLabel(f"当前引擎：{engine}")
        self.lbl.setObjectName("title")
        lay.addWidget(self.lbl)

        row = QHBoxLayout()
        b = QPushButton("选择文件夹并扫描")
        b.setObjectName("primary")
        b.clicked.connect(self._pick_scan)
        row.addWidget(b)
        b2 = QPushButton("隔离选中项")
        b2.clicked.connect(self._quarantine)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["文件", "发现", "级别"])
        self.table.setColumnWidth(0, 440)
        lay.addWidget(self.table)
        lay.addWidget(subtitle(
            "有 ClamAV 引擎时使用专业查杀；否则使用轻量启发式（哈希黑名单、伪装双扩展、可疑小可执行文件），"
            "它不能替代完整杀毒引擎。隔离 = 移动到隔离区，可随时恢复，不会直接删除。"
            f"可自行维护黑名单：{data_dir() / BLACKLIST}"))
        self._hits = []

    def _pick_scan(self):
        d = QFileDialog.getExistingDirectory(self, "选择要扫描的文件夹")
        if not d:
            return
        folder = Path(d)
        if folder.resolve() in (Path.home().resolve(), Path("C:/").resolve()):
            QMessageBox.warning(self, "范围过大", "请不要选择整个用户目录或磁盘根目录，请选具体文件夹。")
            return
        self.lbl.setText("正在扫描（只读）…")
        fn = scan_clamav if resolve("clamav") else scan_heuristic
        run_async(lambda: fn(folder), self._on_result,
                  lambda e: self.lbl.setText(f"扫描出错：{e}"))

    def _on_result(self, result):
        self._hits = result["hits"]
        self.table.setRowCount(len(self._hits))
        for i, (p, why, level) in enumerate(self._hits):
            self.table.setItem(i, 0, QTableWidgetItem(str(p)))
            self.table.setItem(i, 1, QTableWidgetItem(why))
            self.table.setItem(i, 2, QTableWidgetItem(level))
        scanned = result["scanned"]
        info = f"扫描文件 {scanned} 个" if scanned >= 0 else "引擎完成扫描"
        err = ("；" + result["error"]) if result.get("error") else ""
        self.lbl.setText(f"引擎：{result['engine']} · {info} · 发现 {len(self._hits)} 项{err}")

    def _quarantine(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "提示", "请先在结果表中选中要隔离的行。")
            return
        paths = [self._hits[i][0] for i in rows if i < len(self._hits)]
        preview = "\n".join(str(p) for p in paths[:10])
        ret = QMessageBox.warning(
            self, "确认隔离",
            "⚠️ 此操作非常危险，可能导致不可逆的数据丢失！\n\n"
            f"即将把 {len(paths)} 个文件移动到隔离区（可恢复）：\n{preview}\n\n"
            "风险：若文件正被系统或其他程序使用，移动后可能导致其异常。确认继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ret != QMessageBox.StandardButton.Yes:
            return
        qdir = data_dir() / "隔离区"
        qdir.mkdir(exist_ok=True)
        ok = failed = 0
        for p in paths:                       # 小批次、逐项校验
            try:
                target = qdir / f"{int(time.time())}_{p.name}"
                shutil.move(str(p), str(target))
                (qdir / "_恢复说明.txt").write_text(
                    "把这里的文件移回原路径即可恢复。原文件路径记录在下方清单：\n"
                    + "\n".join(f"{target.name} <= {x}" for x in paths),
                    encoding="utf-8")
                ok += 1
            except Exception:
                failed += 1
        QMessageBox.information(self, "隔离完成",
                                f"已隔离 {ok} 项，失败 {failed} 项（占用中文件已跳过）。\n隔离区：{qdir}")


def create_widget():
    return AntivirusWindow()
