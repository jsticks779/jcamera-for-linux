import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget,
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont

from .camera_thread import CameraThread
from .settings_dialog import SettingsDialog
from .photo_tab import PhotoTab
from .video_tab import VideoTab
from .screen_tab import ScreenTab
from .utils import get_resource_path, list_cameras


STYLESHEET = """
QMainWindow { background: #0d0d1a; }
QWidget { background: #0d0d1a; color: #e0e0e0; font-family: 'Segoe UI', 'Ubuntu', sans-serif; }
QPushButton { background: #2a2a4a; color: #e0e0e0; border: none; border-radius: 6px;
              padding: 8px 16px; font-size: 13px; font-weight: bold; }
QPushButton:hover { background: #3a3a5a; }
QPushButton:pressed { background: #1a1a3a; }
QPushButton:checked { background: #e94560; color: white; }
QComboBox { background: #1a1a2e; color: #e0e0e0; border: 1px solid #2a2a4a;
            border-radius: 6px; padding: 4px 8px; font-size: 13px; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #1a1a2e; color: #e0e0e0; selection-background-color: #e94560; }
QTabWidget::pane { background: #0d0d1a; border: none; }
QTabBar::tab { background: #1a1a2e; color: #666; padding: 10px 24px; margin-right: 2px;
               border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; }
QTabBar::tab:selected { background: #2a2a4a; color: #e94560; }
QTabBar::tab:hover:!selected { color: #aaa; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JCamera")
        self.setMinimumSize(960, 720)
        self.resize(1280, 800)

        logo_path = get_resource_path("logo.svg")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        # Auto-detect first camera
        detected = list_cameras()
        if detected:
            cam_dev = detected[0][0]
        else:
            cam_dev = "/dev/video0"

        self._camera = CameraThread()
        self._camera.set_device(cam_dev)
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.camera_error.connect(self._on_camera_error)
        self._camera.camera_status.connect(self._on_camera_status)

        self._cached_device = cam_dev
        self._settings_cache = {}
        self._setup_ui()

        self._camera.start_camera()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        title = QLabel("📷  JCamera")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #e94560; padding: 4px 0;"
        )
        header.addWidget(title)

        header.addStretch()

        self.device_label = QLabel(f"Device: {self._cached_device}")
        self.device_label.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.device_label)

        self.status_label = QLabel("Starting camera...")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.status_label)

        self.settings_btn = QPushButton("⚙  Settings")
        self.settings_btn.setFixedHeight(36)
        self.settings_btn.setStyleSheet(
            "QPushButton { background: #533483; color: white; font-weight: bold; "
            "border-radius: 6px; padding: 6px 16px; }"
            "QPushButton:hover { background: #6b44a8; }"
        )
        self.settings_btn.clicked.connect(self._open_settings)
        header.addWidget(self.settings_btn)

        layout.addLayout(header)

        self.tabs = QStackedWidget()
        layout.addWidget(self.tabs, 1)

        self.photo_tab = PhotoTab(self._camera, self._get_photo_settings)
        self.video_tab = VideoTab(self._camera, self._get_video_settings)
        self.screen_tab = ScreenTab(self._get_screen_settings)

        self.tabs.addWidget(self.photo_tab)
        self.tabs.addWidget(self.video_tab)
        self.tabs.addWidget(self.screen_tab)

        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)

        self.photo_tab_btn = QPushButton("📷  Photo")
        self.photo_tab_btn.setCheckable(True)
        self.photo_tab_btn.setChecked(True)
        self.photo_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        tab_bar.addWidget(self.photo_tab_btn)

        self.video_tab_btn = QPushButton("🎥  Video")
        self.video_tab_btn.setCheckable(True)
        self.video_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_bar.addWidget(self.video_tab_btn)

        self.screen_tab_btn = QPushButton("🖥  Screen")
        self.screen_tab_btn.setCheckable(True)
        self.screen_tab_btn.clicked.connect(lambda: self._switch_tab(2))
        tab_bar.addWidget(self.screen_tab_btn)

        tab_style = (
            "QPushButton { background: #1a1a2e; color: #666; padding: 10px 0; "
            "font-size: 14px; font-weight: bold; border: none; }"
            "QPushButton:checked { background: #2a2a4a; color: #e94560; }"
            "QPushButton:hover:!checked { color: #aaa; }"
        )
        self.photo_tab_btn.setStyleSheet(tab_style)
        self.video_tab_btn.setStyleSheet(tab_style)
        self.screen_tab_btn.setStyleSheet(tab_style)

        layout.addLayout(tab_bar)

    def _switch_tab(self, idx):
        if idx == 2 and self._camera.isRunning():
            self.video_tab.stop_recording()
        if idx != 2 and self.screen_tab._recording:
            self.screen_tab.stop_recording()

        self.tabs.setCurrentIndex(idx)
        self.photo_tab_btn.setChecked(idx == 0)
        self.video_tab_btn.setChecked(idx == 1)
        self.screen_tab_btn.setChecked(idx == 2)

    def _get_photo_settings(self):
        return {
            "width": 1280, "height": 720, "quality": 95,
            **self._settings_cache
        }

    def _get_video_settings(self):
        return {
            "width": 1280, "height": 720, "fps": 30,
            "codec": "libx264", "record_audio": True,
            **self._settings_cache
        }

    def _get_screen_settings(self):
        return {
            "screen_fps": 30, "codec": "libx264",
            "record_screen_audio": True,
            **self._settings_cache
        }

    def _open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self._settings_cache = dialog.get_settings()
            s = self._settings_cache
            self._camera.set_resolution(s["width"], s["height"])
            self._camera.set_fps(s["fps"])
            self._camera.set_flip(s["flip_h"], s["flip_v"])
            self._camera.set_filter(
                s["filter"] if s["filter"] != "None" else None
            )

    def _on_frame(self, qimage):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.photo_tab.set_preview(qimage)
        elif idx == 1:
            self.video_tab.set_preview(qimage)

    def _on_camera_error(self, msg):
        self.status_label.setText(f"Error: {msg}")
        self.status_label.setStyleSheet("color: #e94560; font-size: 12px;")

    def _on_camera_status(self, msg):
        self.status_label.setText(msg)

    def closeEvent(self, event):
        self.video_tab.stop_recording()
        self.screen_tab.stop_recording()
        self._camera.stop_camera()
        event.accept()
