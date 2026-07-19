import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    camera_error = pyqtSignal(str)
    camera_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.device = 0
        self.width = 1280
        self.height = 720
        self.fps = 30
        self._running = False
        self._cap = None
        self._flip_h = False
        self._flip_v = False
        self._apply_filter = None

    def set_device(self, device):
        if isinstance(device, str) and device.startswith("/dev/"):
            try:
                num = int(device.replace("/dev/video", ""))
                self.device = num
            except ValueError:
                self.device = device
        elif isinstance(device, int):
            self.device = device
        else:
            self.device = 0

    def set_resolution(self, width, height):
        self.width = width
        self.height = height

    def set_fps(self, fps):
        self.fps = fps

    def set_flip(self, h=False, v=False):
        self._flip_h = h
        self._flip_v = v

    def set_filter(self, filter_name):
        self._apply_filter = filter_name

    def start_camera(self):
        self._running = True
        self.start()

    def stop_camera(self):
        self._running = False
        self.wait()

    def run(self):
        cap = cv2.VideoCapture(self.device)
        if not cap.isOpened():
            self.camera_error.emit(f"Cannot open camera device {self.device}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.camera_status.emit(f"Camera: {actual_w}x{actual_h} @ {self.fps}fps")

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.msleep(10)
                continue

            if self._flip_h or self._flip_v:
                flip_code = -1 if (self._flip_h and self._flip_v) else (1 if self._flip_h else 0)
                frame = cv2.flip(frame, flip_code)

            if self._apply_filter == "grayscale":
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif self._apply_filter == "negative":
                frame = cv2.bitwise_not(frame)
            elif self._apply_filter == "edge":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            elif self._apply_filter == "sepia":
                sepia = np.array([[0.272, 0.534, 0.131],
                                  [0.349, 0.686, 0.168],
                                  [0.393, 0.769, 0.189]])
                frame = cv2.transform(frame, sepia)
                frame = np.clip(frame, 0, 255).astype(np.uint8)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_ready.emit(qimg.copy())

        cap.release()
