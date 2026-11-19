"""媒体工具：音乐 / 视频播放（QtMultimedia 内置引擎，可选 VLC 容器接管）+ 视频转码（FFmpeg 容器）。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton,
    QSlider, QVBoxLayout, QWidget,
)

from app.core.paths import data_dir
from app.tools.containers import resolve, spawn
from app.tools.impl.common import subtitle

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"}
VIDEO_EXT = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


class _PlayerCore:
    """共享播放内核：QtMultimedia（无需任何外部组件，真正免下载）。"""

    def __init__(self, owner: QWidget, video_output=None):
        self.owner = owner
        self.player = QMediaPlayer(owner)
        self.audio = QAudioOutput(owner)
        self.audio.setVolume(0.7)
        self.player.setAudioOutput(self.audio)
        if video_output is not None:
            self.player.setVideoOutput(video_output)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)

        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.sliderMoved.connect(lambda v: self.player.setPosition(v))
        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(70)
        self.vol.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))
        self.lbl_time = QLabel("00:00 / 00:00")

    def _fmt(self, ms: int) -> str:
        s = max(0, ms // 1000)
        return f"{s // 60:02d}:{s % 60:02d}"

    def _on_pos(self, ms):
        self.seek.blockSignals(True)
        self.seek.setValue(ms)
        self.seek.blockSignals(False)
        self.lbl_time.setText(f"{self._fmt(ms)} / {self._fmt(self.player.duration())}")

    def _on_dur(self, ms):
        self.seek.setRange(0, max(ms, 1))

    def open(self, path: Path):
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def control_row(self):
        row = QHBoxLayout()
        for text, slot in (("▶ 播放", self.player.play),
                           ("⏸ 暂停", self.player.pause),
                           ("⏹ 停止", self.player.stop)):
            b = QPushButton(text)
            b.setMinimumHeight(40)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addWidget(QLabel("音量"))
        row.addWidget(self.vol, stretch=1)
        row.addWidget(self.lbl_time)
        return row


class MusicWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音乐 · 基本工具集齐工具箱")
        self.resize(620, 480)
        lay = QVBoxLayout(self)
        self.core = _PlayerCore(self)

        row = QHBoxLayout()
        b = QPushButton("添加歌曲")
        b.clicked.connect(self._add)
        row.addWidget(b)
        b2 = QPushButton("用 VLC 打开当前")
        b2.clicked.connect(self._vlc_open)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)

        self.playlist = QListWidget()
        self.playlist.itemDoubleClicked.connect(
            lambda it: self.core.open(Path(it.data(Qt.ItemDataRole.UserRole))))
        lay.addWidget(self.playlist)
        lay.addLayout(self.core.control_row())
        lay.addWidget(self.core.seek)
        self.lbl = subtitle("内置播放引擎（QtMultimedia），无需下载安装任何播放器。")
        lay.addWidget(self.lbl)

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "", "音频 (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.wma)")
        from PySide6.QtWidgets import QListWidgetItem
        for f in files:
            item = QListWidgetItem(Path(f).name)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.playlist.addItem(item)
        if files:
            self.core.open(Path(files[0]))

    def _vlc_open(self):
        it = self.playlist.currentItem()
        if not it:
            QMessageBox.information(self, "提示", "请先在列表中选择一首歌曲。")
            return
        f = it.data(Qt.ItemDataRole.UserRole)
        if not spawn("vlc", [f]):
            QMessageBox.information(
                self, "未发现 VLC",
                "未发现 VLC 组件。把 VLC 便携版放进 vendor/vlc/ 即可接管；"
                "当前已使用内置播放引擎，功能正常可用。")


class VideoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频 · 基本工具集齐工具箱")
        self.resize(820, 600)
        lay = QVBoxLayout(self)
        self.video = QVideoWidget()
        self.core = _PlayerCore(self, self.video)

        row = QHBoxLayout()
        b = QPushButton("打开视频")
        b.setObjectName("primary")
        b.clicked.connect(self._open)
        row.addWidget(b)
        b2 = QPushButton("用 VLC 打开")
        b2.clicked.connect(self._vlc_open)
        row.addWidget(b2)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addWidget(self.video, stretch=1)
        lay.addLayout(self.core.control_row())
        lay.addWidget(self.core.seek)
        lay.addWidget(subtitle("内置播放引擎（QtMultimedia/WMF），全格式支持可在 vendor/vlc/ 放入 VLC 便携版增强。"))
        self._current = None

    def _open(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "选择视频", "", "视频 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v)")
        if f:
            self._current = f
            self.core.open(Path(f))

    def _vlc_open(self):
        if not self._current:
            QMessageBox.information(self, "提示", "请先打开一个视频。")
            return
        if not spawn("vlc", [self._current]):
            QMessageBox.information(self, "未发现 VLC",
                                    "把 VLC 便携版放进 vendor/vlc/ 即可接管；当前使用内置引擎。")


class TranscodeWindow(QWidget):
    """视频转码工具（FFmpeg 容器/系统安装）。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("高清转码 · 基本工具集齐工具箱")
        self.resize(600, 320)
        lay = QVBoxLayout(self)
        self.lbl = QLabel("高清视频转码 · FFmpeg 容器")
        self.lbl.setObjectName("title")
        lay.addWidget(self.lbl)
        self.info = subtitle("引擎：FFmpeg（vendor/ffmpeg/ 容器或系统安装）。")
        lay.addWidget(self.info)

        from PySide6.QtWidgets import QComboBox, QProgressBar
        self.cmb = QComboBox()
        self.cmb.addItems(["H.264 高清（CRF 20）", "H.264 高压缩（CRF 26）",
                           "H.265 4K（CRF 24）"])
        lay.addWidget(self.cmb)
        self.bar = QProgressBar()
        lay.addWidget(self.bar)

        b = QPushButton("选择视频并转码")
        b.setObjectName("primary")
        b.setMinimumHeight(44)
        b.clicked.connect(self._run)
        lay.addWidget(b)
        lay.addStretch(1)

    def _run(self):
        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QFileDialog
        exe = resolve("ffmpeg")
        if not exe:
            QMessageBox.information(
                self, "缺少转码引擎",
                "未发现 FFmpeg。请把 ffmpeg.exe 放进 vendor/ffmpeg/ 容器目录后重试。"
                "（组件管理方式见「组件管理」工具）")
            return
        src, _ = QFileDialog.getOpenFileName(self, "选择源视频", "", "视频 (*.*)")
        if not src:
            return
        dst, _ = QFileDialog.getSaveFileName(
            self, "保存为", str(Path(src).with_suffix(".transcoded.mp4")), "MP4 (*.mp4)")
        if not dst:
            return
        idx = self.cmb.currentIndex()
        codec = "libx265" if idx == 2 else "libx264"
        crf = {0: "20", 1: "26", 2: "24"}[idx]
        self.bar.setRange(0, 0)
        self.info.setText("转码中，请稍候…")
        self._proc = QProcess(self)
        self._proc.finished.connect(
            lambda: (self.bar.setRange(0, 100), self.bar.setValue(100),
                     self.info.setText(f"转码完成：{dst}")))
        self._proc.start(exe, ["-y", "-i", src, "-c:v", codec, "-crf", crf,
                               "-preset", "fast", "-c:a", "aac", dst])


def create_music_widget():
    return MusicWindow()


def create_video_widget():
    return VideoWindow()


def create_transcode_widget():
    return TranscodeWindow()
