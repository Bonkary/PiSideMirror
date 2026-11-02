from CoreWidgets import *
from QModuleCore import QModule
from PySide6.QtCore import QTimer, QDateTime

USE_24_HOUR = False

FONT_FAMILY = "'Helvetica Neue', 'Segoe UI', 'DejaVu Sans', sans-serif"
TIME_COLOR = "#ffffff"
SECONDS_COLOR = "#7a7a7a"
DATE_COLOR = "#b0b0b0"

class Clock(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 1)
        self.setBackgroundColor('black')

        self.timeLabel = QLabel(self)
        self.timeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timeLabel.setTextFormat(Qt.TextFormat.RichText)

        self.dateLabel = QLabel(self)
        self.dateLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = CoreVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.timeLabel)
        layout.addWidget(self.dateLabel)
        layout.addStretch(1)
        self.setLayout(layout)

        self._applyFontSizes()
        self._tick()

        # Align to the system second so the display never lags behind
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(250)

    def _applyFontSizes(self):
        # Everything scales with the module width so it fits any screen size
        base = max(self.width(), 200)
        timePx = int(base * 0.26)
        datePx = int(base * 0.058)

        self._timePx = timePx
        self.timeLabel.setStyleSheet(
            f"color: {TIME_COLOR}; font-family: {FONT_FAMILY}; "
            f"font-weight: 200; font-size: {timePx}px; background: transparent;"
        )
        self.dateLabel.setStyleSheet(
            f"color: {DATE_COLOR}; font-family: {FONT_FAMILY}; "
            f"font-weight: 300; font-size: {datePx}px; letter-spacing: 3px; "
            f"background: transparent; padding-top: {int(datePx * 0.4)}px;"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._applyFontSizes()
        self._tick()

    def _tick(self):
        now = QDateTime.currentDateTime()
        time = now.time()

        hour = time.hour()
        if not USE_24_HOUR:
            hour = hour % 12 or 12
        hours = f"{hour:02d}" if USE_24_HOUR else str(hour)

        secondsPx = int(self._timePx * 0.32)
        meridiem = "" if USE_24_HOUR else f"&nbsp;{'AM' if time.hour() < 12 else 'PM'}"

        self.timeLabel.setText(
            f"{hours}:{time.minute():02d}"
            f"<span style='color:{SECONDS_COLOR}; font-size:{secondsPx}px;'>"
            f"&nbsp;{time.second():02d}{meridiem}</span>"
        )

        self.dateLabel.setText(now.toString("dddd, MMMM d").upper())
