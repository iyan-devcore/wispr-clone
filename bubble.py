from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush
import numpy as np
import math


class RecordingBubble(QWidget):
    def __init__(self):
        super().__init__()

        self.idle_w = 48
        self.idle_h = 12
        self.active_w = 120
        self.active_h = 28

        self.state = "idle"   # idle | recording | processing
        self.level = 0.0
        self.spinner_angle = 0

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.screen = QApplication.primaryScreen().availableGeometry()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(140)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.rotate_spinner)

        self.move_idle()
        self.show()

    # ---------- positioning ----------

    def idle_rect(self):
        x = (self.screen.width() - self.idle_w) // 2
        y = self.screen.height() - self.idle_h - 18
        return QRect(x, y, self.idle_w, self.idle_h)

    def active_rect(self):
        x = (self.screen.width() - self.active_w) // 2
        y = self.screen.height() - self.active_h - 18
        return QRect(x, y, self.active_w, self.active_h)

    def move_idle(self):
        r = self.idle_rect()
        self.setGeometry(r)
        self.setFixedSize(self.idle_w, self.idle_h)

    # ---------- state control ----------

    def set_recording(self):
        if self.state != "recording":
            self.state = "recording"
            self.expand()

    def set_processing(self):
        self.state = "processing"
        self.spinner_angle = 0
        self.spinner_timer.start(16)  # smooth spinner
        self.update()

    def set_idle(self):
        self.state = "idle"
        self.level = 0
        self.spinner_timer.stop()
        self.shrink()

    # ---------- animation ----------

    def expand(self):
        start = self.geometry()
        end = self.active_rect()

        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()

        self.setFixedSize(self.active_w, self.active_h)

    def shrink(self):
        start = self.geometry()
        end = self.idle_rect()

        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()

        self.setFixedSize(self.idle_w, self.idle_h)
        self.update()

    # ---------- audio ----------

    def update_level(self, audio_chunk):
        if self.state != "recording":
            return

        rms = np.sqrt(np.mean(audio_chunk**2))
        self.level = min(rms * 40, 1.0)
        self.update()

    # ---------- spinner ----------

    def rotate_spinner(self):
        self.spinner_angle += 10
        self.update()

    # ---------- drawing ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QBrush(QColor(5, 5, 5, 245)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), self.height()/2, self.height()/2)

        if self.state == "idle":
            return

        if self.state == "recording":
            base_x = 24
            max_height = self.height() - 10

            for i in range(5):
                h = 4 + (self.level * max_height)
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawRoundedRect(
                    base_x + i * 12,
                    (self.height() - h) / 2,
                    4,
                    h,
                    2,
                    2
                )

        if self.state == "processing":
            painter.setPen(QColor(255, 255, 255))
            radius = 6
            center_x = self.width() // 2
            center_y = self.height() // 2

            for i in range(8):
                angle = math.radians(self.spinner_angle + i * 45)
                opacity = int(255 * (i / 8))
                painter.setPen(QColor(255, 255, 255, opacity))

                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                painter.drawPoint(int(x), int(y))