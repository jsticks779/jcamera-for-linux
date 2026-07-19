from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QSpinBox, QCheckBox, QPushButton,
                             QTabWidget, QWidget, QFormLayout, QGroupBox,
                             QSlider, QDialogButtonBox)
from PyQt5.QtCore import Qt


RESOLUTIONS = [
    "640x480", "800x600", "1024x768",
    "1280x720", "1920x1080", "2560x1440"
]

FPS_OPTIONS = [15, 24, 30, 60]
CODEC_OPTIONS = ["libx264", "libx265", "libvpx", "mpeg4"]
FILTER_OPTIONS = ["None", "grayscale", "negative", "edge", "sepia"]


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JCamera Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._setup_ui()
        self._load_defaults()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        camera_tab = QWidget()
        tabs.addTab(camera_tab, "Camera")
        cam_layout = QFormLayout(camera_tab)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(RESOLUTIONS)
        cam_layout.addRow("Resolution:", self.resolution_combo)

        self.fps_combo = QComboBox()
        self.fps_combo.addItems([str(f) for f in FPS_OPTIONS])
        cam_layout.addRow("FPS:", self.fps_combo)

        self.flip_h = QCheckBox("Flip horizontally")
        self.flip_v = QCheckBox("Flip vertically")
        cam_layout.addRow(self.flip_h)
        cam_layout.addRow(self.flip_v)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(FILTER_OPTIONS)
        cam_layout.addRow("Filter:", self.filter_combo)

        recording_tab = QWidget()
        tabs.addTab(recording_tab, "Recording")
        rec_layout = QFormLayout(recording_tab)

        self.codec_combo = QComboBox()
        self.codec_combo.addItems(CODEC_OPTIONS)
        rec_layout.addRow("Video Codec:", self.codec_combo)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        self.quality_label = QLabel("95")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(str(v))
        )
        qh = QHBoxLayout()
        qh.addWidget(self.quality_slider)
        qh.addWidget(self.quality_label)
        rec_layout.addRow("Quality:", qh)

        self.audio_check = QCheckBox("Record audio")
        self.audio_check.setChecked(True)
        rec_layout.addRow(self.audio_check)

        screen_tab = QWidget()
        tabs.addTab(screen_tab, "Screen")
        screen_layout = QFormLayout(screen_tab)

        self.screen_fps = QComboBox()
        self.screen_fps.addItems([str(f) for f in FPS_OPTIONS])
        screen_layout.addRow("Screen FPS:", self.screen_fps)

        self.audio_screen_check = QCheckBox("Record audio")
        self.audio_screen_check.setChecked(True)
        screen_layout.addRow(self.audio_screen_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_defaults(self):
        self.resolution_combo.setCurrentText("1280x720")
        self.fps_combo.setCurrentText("30")
        self.screen_fps.setCurrentText("30")
        self.codec_combo.setCurrentText("libx264")

    def get_settings(self):
        res = self.resolution_combo.currentText().split("x")
        return {
            "width": int(res[0]),
            "height": int(res[1]),
            "fps": int(self.fps_combo.currentText()),
            "codec": self.codec_combo.currentText(),
            "quality": self.quality_slider.value(),
            "record_audio": self.audio_check.isChecked(),
            "flip_h": self.flip_h.isChecked(),
            "flip_v": self.flip_v.isChecked(),
            "filter": self.filter_combo.currentText(),
            "screen_fps": int(self.screen_fps.currentText()),
            "record_screen_audio": self.audio_screen_check.isChecked(),
        }
