import cv2
import numpy as np
import os
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtGui import QImage


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    camera_error = pyqtSignal(str)
    camera_status = pyqtSignal(str)
    photo_saved = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.device = 0
        self.width = 1280
        self.height = 720
        self.fps = 30
        self._running = False
        self._flip_h = False
        self._flip_v = False
        self._apply_filter = None
        self._latest_frame = None
        self._mutex = QMutex()
        self._capture_requested = False
        self._capture_path = ""

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

    def request_photo(self, filepath):
        with QMutexLocker(self._mutex):
            self._capture_requested = True
            self._capture_path = filepath

    def start_camera(self):
        self._running = True
        self.start()

    def stop_camera(self):
        self._running = False
        if not self.wait(3000):
            self.camera_error.emit("Camera stop timed out")

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

            with QMutexLocker(self._mutex):
                self._latest_frame = frame.copy()
                if self._capture_requested:
                    self._capture_requested = False
                    self._save_photo(self._latest_frame, self._capture_path)

            display_frame = frame.copy()

            if self._flip_h or self._flip_v:
                flip_code = -1 if (self._flip_h and self._flip_v) else (1 if self._flip_h else 0)
                display_frame = cv2.flip(display_frame, flip_code)

            if self._apply_filter:
                display_frame = self._apply_filter_to(display_frame)

            rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            data = rgb.tobytes()
            qimg = QImage(data, w, h, ch * w, QImage.Format_RGB888)
            self.frame_ready.emit(qimg)

        cap.release()

    def _save_photo(self, frame, path):
        try:
            if self._apply_filter:
                frame = self._apply_filter_to(frame)
            cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                self.photo_saved.emit(os.path.basename(path))
            else:
                self.camera_error.emit("Photo save failed")
        except Exception as e:
            self.camera_error.emit(f"Photo save error: {e}")

    def _apply_filter_to(self, frame):
        if self._apply_filter == "grayscale":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        elif self._apply_filter == "negative":
            return cv2.bitwise_not(frame)
        elif self._apply_filter == "edge":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        elif self._apply_filter == "sepia":
            sepia = np.array([[0.272, 0.534, 0.131],
                              [0.349, 0.686, 0.168],
                              [0.393, 0.769, 0.189]])
            result = cv2.transform(frame, sepia)
            return np.clip(result, 0, 255).astype(np.uint8)
        return frame

    @property
    def device_path(self):
        return f"/dev/video{self.device}"
