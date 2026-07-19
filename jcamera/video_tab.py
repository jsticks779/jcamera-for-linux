import os
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from .utils import get_videos_dir, ffmpeg_record_video, list_audio_sources


class VideoTab(QWidget):
    def __init__(self, camera_thread, settings_getter):
        super().__init__()
        self._camera = camera_thread
        self._get_settings = settings_getter
        self._recording = False
        self._process = None
        self._elapsed = 0
        self._setup_ui()
        self._update_audio_sources()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background: #0d0d1a; border: 2px solid #2a2a4a; border-radius: 8px;"
        )
        self.preview_label.setMinimumSize(640, 480)
        layout.addWidget(self.preview_label, 1)

        controls = QHBoxLayout()

        self.audio_combo = QComboBox()
        self.audio_combo.setMinimumWidth(200)
        self.audio_combo.setFixedHeight(36)
        controls.addWidget(self.audio_combo)

        controls.addStretch()

        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #e94560;"
        )
        self.timer_label.setText("00:00")
        self.timer_label.setFixedWidth(100)
        controls.addWidget(self.timer_label)

        self.record_btn = QPushButton("🔴  RECORD")
        self.record_btn.setFixedHeight(48)
        self.record_btn.setMinimumWidth(200)
        controls.addWidget(self.record_btn)

        controls.addStretch()

        self.last_video_label = QLabel()
        self.last_video_label.setFixedSize(120, 90)
        self.last_video_label.setStyleSheet(
            "background: #0d0d1a; border: 1px solid #2a2a4a; border-radius: 4px;"
        )
        self.last_video_label.setAlignment(Qt.AlignCenter)
        self.last_video_label.setText("No video")
        controls.addWidget(self.last_video_label)

        layout.addLayout(controls)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        self.record_btn.clicked.connect(self._toggle_recording)

    def _update_audio_sources(self):
        self.audio_combo.clear()
        self.audio_combo.addItem("No audio", None)
        for src in list_audio_sources():
            self.audio_combo.addItem(src, src)

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        settings = self._get_settings()
        timestamp = int(time.time())
        filename = f"video_{timestamp}.mkv"
        filepath = os.path.join(get_videos_dir(), filename)

        device = f"/dev/video{self._camera.device}" if isinstance(self._camera.device, int) \
                 else self._camera.device

        audio = self.audio_combo.currentData() if settings["record_audio"] else None

        self._process = ffmpeg_record_video(
            device, filepath,
            width=settings["width"],
            height=settings["height"],
            fps=settings["fps"],
            codec=settings["codec"],
            audio_source=audio
        )

        self._recording = True
        self._elapsed = 0
        self.record_btn.setText("⏹  STOP")
        self.record_btn.setStyleSheet(
            "QPushButton { background: #ff4444; color: white; font-weight: bold; "
            "border-radius: 8px; padding: 8px 24px; font-size: 14px; }"
            "QPushButton:hover { background: #cc0000; }"
        )
        self._elapsed_timer.start(1000)

    def _stop_recording(self):
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None

        self._recording = False
        self._elapsed_timer.stop()
        self.timer_label.setText("00:00")
        self.record_btn.setText("🔴  RECORD")
        self.record_btn.setStyleSheet(
            "QPushButton { background: #e94560; color: white; font-weight: bold; "
            "border-radius: 8px; padding: 8px 24px; font-size: 14px; }"
            "QPushButton:hover { background: #e94560dd; }"
        )

    def _update_elapsed(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def set_preview(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.preview_label.width(), self.preview_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def stop_recording(self):
        if self._recording:
            self._stop_recording()
