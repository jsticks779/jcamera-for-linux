#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from jcamera.main_window import MainWindow, STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JCamera")
    app.setApplicationDisplayName("JCamera")
    app.setDesktopFileName("jcamera")
    app.setStyleSheet(STYLESHEET)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
