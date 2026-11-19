"""办公工具：文档编辑（内置富文本 + .docx 读写 + LibreOffice 容器接管）、PDF 阅读（QtPdf + SumatraPDF 容器）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.tools.containers import resolve, spawn
from app.tools.impl.common import subtitle


# ---------------------------------------------------------------- 文档编辑

class DocEditorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文档编辑 · 基本工具集齐工具箱")
        self.resize(820, 640)
        self._path: Path | None = None
        lay = QVBoxLayout(self)

        bar = QHBoxLayout()
        for text, slot in (("新建", self._new), ("打开", self._open),
                           ("保存", self._save), ("另存为", self._save_as)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        b = QPushButton("用 LibreOffice 打开")
        b.setObjectName("accent")
        b.clicked.connect(self._open_in_lo)
        bar.addWidget(b)
        lay.addLayout(bar)

        fmt = QHBoxLayout()
        for text, slot in (("B 加粗", self._bold), ("I 斜体", self._italic),
                           ("U 下划线", self._underline)):
            btn = QPushButton(text)
            btn.setFixedWidth(90)
            btn.setCheckable(True)
            btn.clicked.connect(slot)
            fmt.addWidget(btn)
        self.cmb_size = QComboBox()
        self.cmb_size.addItems([str(s) for s in (10, 11, 12, 14, 16, 18, 20, 24, 28, 36)])
        self.cmb_size.setCurrentText("14")
        self.cmb_size.currentTextChanged.connect(
            lambda s: self.editor.setFontPointSize(float(s)))
        fmt.addWidget(QLabel("字号"))
        fmt.addWidget(self.cmb_size)
        for text, align in (("左对齐", Qt.AlignmentFlag.AlignLeft),
                            ("居中", Qt.AlignmentFlag.AlignCenter),
                            ("右对齐", Qt.AlignmentFlag.AlignRight)):
            b = QPushButton(text)
            b.clicked.connect(lambda checked=False, a=align: self.editor.setAlignment(a))
            fmt.addWidget(b)
        fmt.addStretch(1)
        lay.addLayout(fmt)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Microsoft YaHei", 11))
        lay.addWidget(self.editor, stretch=1)
        self.status = subtitle("支持 txt / md / html / rtf / docx。docx 由 python-docx 读写（基础排版）。"
                               "放入 LibreOffice 便携版后可获得完整 Word 级编辑能力。")
        lay.addWidget(self.status)

    def _bold(self, checked):
        self.editor.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)

    def _italic(self, checked):
        self.editor.setFontItalic(checked)

    def _underline(self, checked):
        self.editor.setFontUnderline(checked)

    def _new(self):
        self.editor.clear()
        self._path = None
        self.status.setText("新建文档")

    def _open(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "打开文档", "", "文档 (*.txt *.md *.html *.htm *.rtf *.docx);;所有文件 (*.*)")
        if not f:
            return
        p = Path(f)
        try:
            if p.suffix.lower() == ".docx":
                import docx
                d = docx.Document(str(p))
                self.editor.setPlainText("\n".join(par.text for par in d.paragraphs))
            elif p.suffix.lower() == ".rtf":
                self.editor.setHtml("<pre>" + p.read_text(encoding="utf-8", errors="replace") + "</pre>")
            elif p.suffix.lower() in (".html", ".htm"):
                self.editor.setHtml(p.read_text(encoding="utf-8", errors="replace"))
            else:
                self.editor.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
            self._path = p
            self.status.setText(f"已打开：{p}")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", str(e))

    def _save(self):
        if not self._path:
            return self._save_as()
        self._write(self._path)

    def _save_as(self):
        f, _ = QFileDialog.getSaveFileName(
            self, "保存文档", "", "Word 文档 (*.docx);;网页 (*.html);;文本 (*.txt);;Markdown (*.md);;RTF (*.rtf)")
        if f:
            self._write(Path(f))

    def _write(self, p: Path):
        try:
            s = p.suffix.lower()
            if s == ".docx":
                import docx
                d = docx.Document()
                for line in self.editor.toPlainText().splitlines():
                    d.add_paragraph(line)
                d.save(str(p))
            elif s in (".html", ".htm"):
                p.write_text(self.editor.toHtml(), encoding="utf-8")
            elif s == ".rtf":
                # 以最小合法 RTF 包装纯文本，保证其他软件可读
                p.write_bytes(self._to_rtf_bytes())
            else:
                p.write_text(self.editor.toPlainText(), encoding="utf-8")
            self._path = p
            self.status.setText(f"已保存：{p}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def _to_rtf_bytes(self) -> bytes:
        # Qt 未直接提供 RTF 写出；以最小合法 RTF 包装纯文本，保证其他软件可读
        text = self.editor.toPlainText().replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        body = "\\par\n".join(text.splitlines())
        return (r"{\rtf1\ansi\deff0{\fonttbl{\f0 Microsoft YaHei;}}\f0\fs22 "
                + body + "}").encode("ascii", errors="replace")

    def _open_in_lo(self):
        if not self._path:
            QMessageBox.information(self, "提示", "请先打开或保存一个文档。")
            return
        if not spawn("libreoffice", [str(self._path)]):
            QMessageBox.information(
                self, "未发现 LibreOffice",
                "把 LibreOffice 便携版放进 vendor/libreoffice/ 即可接管；"
                "当前内置编辑器已可完成日常文档编辑与 docx 读写。")


# ---------------------------------------------------------------- PDF 阅读

class PdfReaderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 阅读 · 基本工具集齐工具箱")
        self.resize(860, 660)
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        b = QPushButton("打开 PDF")
        b.setObjectName("primary")
        b.clicked.connect(self._open)
        bar.addWidget(b)
        self.btn_prev = QPushButton("上一页")
        self.btn_prev.clicked.connect(lambda: self._jump(-1))
        self.btn_next = QPushButton("下一页")
        self.btn_next.clicked.connect(lambda: self._jump(1))
        bar.addWidget(self.btn_prev)
        bar.addWidget(self.btn_next)
        self.lbl_page = QLabel("未打开")
        bar.addWidget(self.lbl_page)
        bar.addStretch(1)
        b2 = QPushButton("用 SumatraPDF 打开")
        b2.clicked.connect(self._open_external)
        bar.addWidget(b2)
        lay.addLayout(bar)

        self._file = None
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
            self._doc = QPdfDocument(self)
            self._view = QPdfView(self)
            self._view.setDocument(self._doc)
            self._view.setPageMode(QPdfView.PageMode.MultiPage)
            self._nav = self._view.pageNavigator()
            self._nav.currentPageChanged.connect(self._update_page)
            lay.addWidget(self._view, stretch=1)
            self._qt_pdf = True
        except Exception as e:
            self._qt_pdf = False
            lay.addWidget(subtitle(f"QtPdf 模块不可用（{e}）；请使用 SumatraPDF 容器或系统 PDF 阅读器。"),
                          stretch=1)
        lay.addWidget(subtitle("内置 PDF 引擎（QtPdf）；vendor/sumatrapdf/ 放入 SumatraPDF 便携版可增强。"))

    def _open(self):
        f, _ = QFileDialog.getOpenFileName(self, "打开 PDF", "", "PDF (*.pdf)")
        if not f:
            return
        self._file = f
        if self._qt_pdf:
            self._doc.load(f)
            self._update_page(0)
        else:
            import os
            os.startfile(f)

    def _jump(self, delta):
        if not self._qt_pdf or not self._file:
            return
        from PySide6.QtCore import QPointF
        page = self._nav.currentPage() + delta
        if 0 <= page < self._doc.pageCount():
            self._nav.jump(page, QPointF(), self._nav.currentZoom())

    def _update_page(self, page):
        if self._qt_pdf and self._doc.pageCount():
            self.lbl_page.setText(f"第 {page + 1} / {self._doc.pageCount()} 页")

    def _open_external(self):
        if not self._file:
            QMessageBox.information(self, "提示", "请先打开一个 PDF。")
            return
        if not spawn("sumatrapdf", [self._file]):
            import os
            os.startfile(self._file)      # 系统默认阅读器兜底


def create_doc_widget():
    return DocEditorWindow()


def create_pdf_widget():
    return PdfReaderWindow()
