import os
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QMessageBox,
                             QRubberBand, QApplication)
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont

from .utils import get_videos_dir, ffmpeg_screen_record, list_audio_sources, get_display_resolution


class RegionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowFullScreen)
        self._origin = QPoint()
        self._rubber = QRubberBand(QRubberBand.Rectangle, self)
        self._selected = None

        self.setStyleSheet("background: rgba(0,0,0,100);")

    def mousePressEvent(self, event):
        self._origin = event.pos()
        self._rubber.setGeometry(QRect(self._origin, QPoint()))
        self._rubber.show()

    def mouseMoveEvent(self, event):
        self._rubber.setGeometry(QRect(self._origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        self._rubber.hide()
        rect = QRect(self._origin, event.pos()).normalized()
        if rect.width() > 20 and rect.height() > 20:
            self._selected = {
                "x": rect.x(),
                "y": rect.y(),
                "width": rect.width(),
                "height": rect.height(),
                "size": f"{rect.width()}x{rect.height()}"
            }
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if self._rubber.isVisible():
            geom = self._rubber.geometry()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(geom, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(233, 69, 96), 3)
            painter.setPen(pen)
            painter.drawRect(geom)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._selected = None
            self.close()


class ScreenTab(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, settings_getter):
        super().__init__()
        self._get_settings = settings_getter
        self._recording = False
        self._process = None
        self._elapsed = 0
        self._region = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet(
            "background: #0d0d1a; border: 2px solid #2a2a4a; border-radius: 8px; color: #666;"
        )
        preview.setMinimumSize(640, 480)
        preview.setText(
            "Screen Recording\n\n"
            "Select region or record full screen\n"
            "Audio will be captured from microphone"
        )
        preview.setFont(QFont("Arial", 14))
        layout.addWidget(preview, 1)

        controls = QHBoxLayout()

        self.audio_combo = QComboBox()
        self.audio_combo.setMinimumWidth(200)
        self.audio_combo.setFixedHeight(36)
        controls.addWidget(self.audio_combo)

        self.region_btn = QPushButton("Select Region")
        self.region_btn.setFixedHeight(36)
        self.region_btn.setStyleSheet(
            "QPushButton { background: #533483; color: white; font-weight: bold; "
            "border-radius: 6px; padding: 6px 16px; }"
            "QPushButton:hover { background: #6b44a8; }"
        )
        controls.addWidget(self.region_btn)

        self.region_info = QLabel("Full Screen")
        self.region_info.setStyleSheet("color: #888;")
        controls.addWidget(self.region_info)

        controls.addStretch()

        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #e94560;"
        )
        self.timer_label.setText("00:00")
        self.timer_label.setFixedWidth(100)
        controls.addWidget(self.timer_label)

        self.record_btn = QPushButton("🔴  RECORD SCREEN")
        self.record_btn.setFixedHeight(48)
        self.record_btn.setMinimumWidth(220)
        self.record_btn.setStyleSheet(
            "QPushButton { background: #e94560; color: white; font-weight: bold; "
            "border-radius: 8px; padding: 8px 24px; font-size: 14px; }"
            "QPushButton:hover { background: #e94560dd; }"
        )
        controls.addWidget(self.record_btn)

        controls.addStretch()

        self.last_screen_label = QLabel()
        self.last_screen_label.setFixedSize(120, 90)
        self.last_screen_label.setStyleSheet(
            "background: #0d0d1a; border: 1px solid #2a2a4a; border-radius: 4px;"
        )
        self.last_screen_label.setAlignment(Qt.AlignCenter)
        self.last_screen_label.setText("No record")
        controls.addWidget(self.last_screen_label)

        layout.addLayout(controls)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        self.record_btn.clicked.connect(self._toggle_recording)
        self.region_btn.clicked.connect(self._select_region)
        self._update_audio_sources()

    def _update_audio_sources(self):
        self.audio_combo.clear()
        self.audio_combo.addItem("No audio", None)
        for src in list_audio_sources():
            self.audio_combo.addItem(src, src)

    def _select_region(self):
        self.selector = RegionSelector()
        self.selector.show()
        self.selector._selected = None

        # Wait for selection
        self._timer_check = QTimer()
        self._timer_check.timeout.connect(self._check_region)
        self._timer_check.start(200)

    def _check_region(self):
        if not self.selector.isVisible():
            self._timer_check.stop()
            if self.selector._selected:
                self._region = self.selector._selected
                info = f"{self._region['size']} at ({self._region['x']},{self._region['y']})"
                self.region_info.setText(info)
            else:
                self._region = None
                self.region_info.setText("Full Screen")
            self.selector.deleteLater()

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        settings = self._get_settings()
        timestamp = int(time.time())
        filename = f"screen_{timestamp}.mkv"
        filepath = os.path.join(get_videos_dir(), filename)

        audio = self.audio_combo.currentData() if settings["record_screen_audio"] else None

        self._process = ffmpeg_screen_record(
            filepath,
            region=self._region,
            fps=settings["screen_fps"],
            codec=settings["codec"],
            audio_source=audio
        )

        self._recording = True
        self._elapsed = 0
        self.status_message.emit("Recording screen...")
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
        self.record_btn.setText("🔴  RECORD SCREEN")
        self.status_message.emit("Screen recording saved")
        self.record_btn.setStyleSheet(
            "QPushButton { background: #e94560; color: white; font-weight: bold; "
            "border-radius: 8px; padding: 8px 24px; font-size: 14px; }"
            "QPushButton:hover { background: #e94560dd; }"
        )

    def _update_elapsed(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def stop_recording(self):
        if self._recording:
            self._stop_recording()
