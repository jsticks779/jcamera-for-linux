import os
import time
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

from .utils import get_captures_dir, ffmpeg_capture_photo


class PhotoTab(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, camera_thread, settings_getter):
        super().__init__()
        self._camera = camera_thread
        self._get_settings = settings_getter
        self._timer_running = False
        self._timer_count = 0
        self._setup_ui()
        self._connect_signals()

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

        self.timer_btn = QPushButton("Timer: Off")
        self.timer_btn.setCheckable(True)
        self.timer_btn.setFixedHeight(40)
        controls.addWidget(self.timer_btn)

        self.timer_value_btn = QPushButton("3s")
        self.timer_value_btn.setFixedWidth(50)
        self.timer_value_btn.setFixedHeight(40)
        controls.addWidget(self.timer_value_btn)

        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet(
            "font-size: 48px; font-weight: bold; color: #e94560;"
        )
        self.timer_label.setFixedHeight(60)
        self.timer_label.hide()
        controls.addWidget(self.timer_label)

        controls.addStretch()

        self.capture_btn = QPushButton("📷  CAPTURE")
        self.capture_btn.setFixedHeight(48)
        self.capture_btn.setMinimumWidth(200)
        self.capture_btn.setStyleSheet(self._button_style("#e94560"))
        controls.addWidget(self.capture_btn)

        controls.addStretch()

        self.last_photo_label = QLabel()
        self.last_photo_label.setFixedSize(120, 90)
        self.last_photo_label.setStyleSheet(
            "background: #0d0d1a; border: 1px solid #2a2a4a; border-radius: 4px;"
        )
        self.last_photo_label.setAlignment(Qt.AlignCenter)
        controls.addWidget(self.last_photo_label)

        layout.addLayout(controls)

        self._timer = QTimer()
        self._timer.timeout.connect(self._timer_tick)

    def _button_style(self, color):
        return (
            f"QPushButton {{ background: {color}; color: white; font-weight: bold; "
            f"border-radius: 8px; padding: 8px 24px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {color}dd; }}"
            f"QPushButton:pressed {{ background: {color}bb; }}"
        )

    def _connect_signals(self):
        self.capture_btn.clicked.connect(self._on_capture)
        self.timer_btn.clicked.connect(self._toggle_timer)
        self.timer_value_btn.clicked.connect(self._cycle_timer_value)

    def _toggle_timer(self):
        self._timer_running = self.timer_btn.isChecked()
        if self._timer_running:
            self.timer_btn.setText("Timer: On")
        else:
            self.timer_btn.setText("Timer: Off")
            self.timer_label.hide()

    def _cycle_timer_value(self):
        values = ["3s", "5s", "10s", "15s", "30s"]
        current = self.timer_value_btn.text()
        idx = (values.index(current) + 1) % len(values) if current in values else 0
        self.timer_value_btn.setText(values[idx])

    def _get_timer_seconds(self):
        return int(self.timer_value_btn.text().replace("s", ""))

    def _on_capture(self):
        if self._timer_running:
            self._timer_count = self._get_timer_seconds()
            self.timer_label.show()
            self._timer.start(1000)
            return
        self._do_capture()

    def _timer_tick(self):
        self._timer_count -= 1
        if self._timer_count <= 0:
            self._timer.stop()
            self.timer_label.hide()
            self._do_capture()
        else:
            self.timer_label.setText(str(self._timer_count))

    def _do_capture(self):
        settings = self._get_settings()
        timestamp = int(time.time())
        filename = f"photo_{timestamp}.jpg"
        filepath = os.path.join(get_captures_dir(), filename)

        device = f"/dev/video{self._camera.device}" if isinstance(self._camera.device, int) \
                 else self._camera.device

        self.status_message.emit("Capturing photo...")
        ffmpeg_capture_photo(
            device, filepath,
            width=settings["width"],
            height=settings["height"],
            quality=settings["quality"]
        )

        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                self.last_photo_label.setPixmap(
                    pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            self.status_message.emit(f"Photo saved: {filename}")
        else:
            self.status_message.emit("Photo capture failed")

    def set_preview(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.preview_label.width(), self.preview_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
