"""压缩解压：zip / tar.gz / 7z 创建与解压；容器 7-Zip 接管；含 Zip-Slip 路径穿越防护。"""
from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app.tools.containers import launch, resolve
from app.tools.impl.common import fmt_size, subtitle


def _safe_member(dest: Path, name: str) -> Path | None:
    """防 Zip-Slip：拒绝 .. / 绝对路径 / 盘符路径。"""
    name = name.replace("\\", "/")
    p = (dest / name).resolve()
    try:
        p.relative_to(dest.resolve())
        return p
    except ValueError:
        return None


def list_archive(path: Path):
    s = path.suffix.lower()
    if s == ".zip":
        with zipfile.ZipFile(path) as z:
            return [(i.filename, i.file_size) for i in z.infolist()]
    if s in (".7z",):
        import py7zr
        with py7zr.SevenZipFile(path, "r") as z:
            return [(n, 0) for n in z.getnames()]
    if s in (".gz", ".tgz", ".bz2", ".xz", ".tar"):
        with tarfile.open(path) as t:
            return [(m.name, m.size) for m in t.getmembers()]
    raise ValueError(f"不支持的格式：{s}")


def extract_archive(path: Path, dest: Path) -> tuple:
    """返回 (成功数, 跳过数)。逐项校验路径，绝不写出目标目录之外。"""
    dest.mkdir(parents=True, exist_ok=True)
    ok = skipped = 0
    s = path.suffix.lower()
    if s == ".zip":
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                target = _safe_member(dest, info.filename)
                if target is None:
                    skipped += 1
                    continue
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    out.write(src.read())
                ok += 1
    elif s in (".7z",):
        if resolve("7zip"):
            r = launch("7zip", ["x", "-y", f"-o{dest}", str(path)], timeout=300)
            if not r.get("ok"):
                raise RuntimeError(r.get("error") or r.get("stderr", "解压失败"))
            return (1, 0)
        import py7zr
        with py7zr.SevenZipFile(path, "r") as z:
            names = z.getnames()
            safe = [n for n in names if _safe_member(dest, n.replace("\\", "/")) is not None]
            skipped = len(names) - len(safe)
            z.extract(path=str(dest), targets=safe)
            ok = len(safe)
    elif s in (".gz", ".tgz", ".bz2", ".xz", ".tar"):
        with tarfile.open(path) as t:
            for m in t.getmembers():
                target = _safe_member(dest, m.name)
                if target is None:
                    skipped += 1
                    continue
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                f = t.extractfile(m)
                if f:
                    with open(target, "wb") as out:
                        out.write(f.read())
                    ok += 1
    else:
        raise ValueError(f"不支持的格式：{s}")
    return ok, skipped


class ArchiveWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("压缩解压 · 基本工具集齐工具箱")
        self.resize(720, 520)
        lay = QVBoxLayout(self)
        self._files: list[Path] = []

        row = QHBoxLayout()
        b = QPushButton("添加文件")
        b.clicked.connect(self._add)
        row.addWidget(b)
        b2 = QPushButton("清空列表")
        b2.clicked.connect(self._clear)
        row.addWidget(b2)
        row.addStretch(1)
        row.addWidget(QLabel("格式"))
        self.cmb = QComboBox()
        self.cmb.addItems(["zip", "tar.gz", "7z"])
        row.addWidget(self.cmb)
        b3 = QPushButton("打包为压缩包")
        b3.setObjectName("primary")
        b3.clicked.connect(self._pack)
        row.addWidget(b3)
        lay.addLayout(row)

        self.list = QListWidget()
        lay.addWidget(self.list)
        self.lbl = subtitle("")
        lay.addWidget(self.lbl)

        row2 = QHBoxLayout()
        b4 = QPushButton("打开压缩包并查看内容")
        b4.clicked.connect(self._inspect)
        row2.addWidget(b4)
        b5 = QPushButton("解压到…")
        b5.clicked.connect(self._extract)
        row2.addWidget(b5)
        row2.addStretch(1)
        lay.addLayout(row2)
        self._archive: Path | None = None

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要压缩的文件")
        for f in files:
            p = Path(f)
            self._files.append(p)
            self.list.addItem(f"{p.name}  ({fmt_size(p.stat().st_size)})  —  {p}")

    def _clear(self):
        self._files.clear()
        self.list.clear()

    def _pack(self):
        if not self._files:
            QMessageBox.information(self, "提示", "请先添加文件。")
            return
        fmt = self.cmb.currentText()
        ext = {"zip": ".zip", "tar.gz": ".tar.gz", "7z": ".7z"}[fmt]
        dst, _ = QFileDialog.getSaveFileName(self, "保存压缩包", "archive" + ext, f"*{ext}")
        if not dst:
            return
        try:
            if fmt == "zip":
                with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
                    for f in self._files:
                        z.write(f, f.name)
            elif fmt == "tar.gz":
                with tarfile.open(dst, "w:gz") as t:
                    for f in self._files:
                        t.add(f, f.name)
            else:
                if resolve("7zip"):
                    r = launch("7zip", ["a", dst, *[str(f) for f in self._files]], timeout=300)
                    if not r.get("ok"):
                        raise RuntimeError(r.get("error") or r.get("stderr", ""))
                else:
                    import py7zr
                    with py7zr.SevenZipFile(dst, "w") as z:
                        for f in self._files:
                            z.write(f, f.name)
            self.lbl.setText(f"打包完成：{dst}")
        except Exception as e:
            QMessageBox.warning(self, "打包失败", str(e))

    def _inspect(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "打开压缩包", "", "压缩包 (*.zip *.7z *.tar.gz *.tgz *.tar *.bz2 *.xz)")
        if not f:
            return
        self._archive = Path(f)
        try:
            items = list_archive(self._archive)
            self.list.clear()
            for name, size in items:
                self.list.addItem(f"{name}  ({fmt_size(size)})")
            self.lbl.setText(f"{self._archive.name}：{len(items)} 项")
        except Exception as e:
            QMessageBox.warning(self, "读取失败", str(e))

    def _extract(self):
        if not self._archive:
            f, _ = QFileDialog.getOpenFileName(self, "选择压缩包", "", "压缩包 (*.*)")
            if not f:
                return
            self._archive = Path(f)
        dest = QFileDialog.getExistingDirectory(self, "选择解压目标文件夹")
        if not dest:
            return
        try:
            ok, skipped = extract_archive(self._archive, Path(dest))
            note = f"，已拦截 {skipped} 个路径穿越项" if skipped else ""
            self.lbl.setText(f"解压完成：{ok} 个文件{note} → {dest}")
        except Exception as e:
            QMessageBox.warning(self, "解压失败", str(e))


def create_widget():
    return ArchiveWindow()
