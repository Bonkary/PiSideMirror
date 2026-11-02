import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from CoreWidgets import *
from QModuleCore import QModule
from PySide6.QtCore import QObject, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPalette

from .caldav_logic import CalDavSource, CalendarError, ICLOUD_URL

# Events come from iCloud over CalDAV. In this module's config.json set:
#   "icloud": {"username": "you@icloud.com", "appPassword": "abcd-efgh-ijkl-mnop"}
# The password must be an app-specific password from account.apple.com
# (Sign-In and Security > App-Specific Passwords), not your Apple ID password.
# "calendars" optionally lists calendar names to show (empty shows all).
# "daysAhead" and "maxEvents" limit the list. Set "server" to use another
# CalDAV provider instead of iCloud.
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_DAYS_AHEAD = 14
DEFAULT_MAX_EVENTS = 6
DEFAULT_COLORS = ["#4fa3ff", "#f87171", "#34d399", "#fbbf24", "#a78bfa", "#f472b6"]

REFRESH_MS = 15 * 60 * 1000
REDRAW_MS = 60 * 1000

FONT_FAMILY = "'Helvetica Neue', 'Segoe UI', 'DejaVu Sans', sans-serif"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#8e99a8"
DIM_COLOR = "#4a5361"


class _FetchResults(QObject):
    """Carries results from the worker thread back to the GUI thread."""
    fetched = Signal(list)
    failed = Signal(str)


def _startDate(event: dict) -> date:
    return event["start"] if event["allDay"] else event["start"].date()


class ElidedLabel(QLabel):
    """A label that ends with … instead of growing when its text is too long."""

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(0)
        return hint

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(0)
        return hint

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, rect.width())
        self.style().drawItemText(
            painter, rect, int(self.alignment()), self.palette(), True, text,
            QPalette.ColorRole.WindowText,
        )
        painter.end()


class WeekStrip(QWidget):
    """The current week, with today circled and dots under days that have events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.weekStart = date.today()
        self.today = date.today()
        self.dots: dict[date, list[str]] = {}
        self.unit = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setData(self, weekStart: date, today: date, dots: dict[date, list[str]]):
        self.weekStart = weekStart
        self.today = today
        self.dots = dots
        self.update()

    def setUnit(self, unit: float):
        self.unit = unit
        self.setFixedHeight(int(78 * unit))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        u = self.unit
        columnWidth = self.width() / 7
        letterFont = QFont("DejaVu Sans")
        letterFont.setPixelSize(max(8, int(12 * u)))
        numberFont = QFont("DejaVu Sans")
        numberFont.setPixelSize(max(9, int(20 * u)))

        for i in range(7):
            day = self.weekStart + timedelta(days=i)
            cx = columnWidth * (i + 0.5)
            isToday = day == self.today
            isPast = day < self.today

            painter.setFont(letterFont)
            painter.setPen(QColor(TEXT_COLOR if isToday else MUTED_COLOR))
            painter.drawText(QRectF(cx - columnWidth / 2, 0, columnWidth, 18 * u),
                             Qt.AlignmentFlag.AlignCenter, "SMTWTFS"[i])

            circleY = 38 * u
            radius = 17 * u
            if isToday:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(TEXT_COLOR))
                painter.drawEllipse(QPointF(cx, circleY), radius, radius)

            painter.setFont(numberFont)
            painter.setPen(QColor("#000000" if isToday else DIM_COLOR if isPast else TEXT_COLOR))
            painter.drawText(QRectF(cx - radius, circleY - radius, radius * 2, radius * 2),
                             Qt.AlignmentFlag.AlignCenter, str(day.day))

            colors = self.dots.get(day, [])[:3]
            dotRadius = 2.6 * u
            spacing = dotRadius * 3
            x = cx - spacing * (len(colors) - 1) / 2
            painter.setPen(Qt.PenStyle.NoPen)
            for color in colors:
                painter.setBrush(QColor(color))
                painter.drawEllipse(QPointF(x, 68 * u), dotRadius, dotRadius)
                x += spacing

        painter.end()


class Calendar(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 1)
        self.setBackgroundColor('black')

        self.source, self.daysAhead, self.maxEvents = self._loadSettings()
        self.events: list[dict] | None = None
        self.error: str | None = None
        self.fetching = False
        self.unit = 1.0

        self.results = _FetchResults(self)
        self.results.fetched.connect(self._onFetched)
        self.results.failed.connect(self._onFailed)

        self.monthLabel = QLabel(self)
        self.weekStrip = WeekStrip(self)

        self.agenda = CoreVBoxLayout()
        self.agenda.setAlignment(Qt.AlignmentFlag.AlignTop)
        agendaWidget = QWidget(self)
        agendaWidget.setLayout(self.agenda)

        self.layoutMain = CoreVBoxLayout()
        # The Core layouts center their contents, which shrinks everything to
        # its minimum size; the calendar should fill its whole cell instead
        self.layoutMain.setAlignment(Qt.AlignmentFlag(0))
        self.layoutMain.addWidget(self.monthLabel)
        self.layoutMain.addWidget(self.weekStrip)
        self.layoutMain.addWidget(agendaWidget, 1)
        self.setLayout(self.layoutMain)

        self._applySizes()
        self._render()

        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.start(REFRESH_MS)
        QTimer.singleShot(0, self.refresh)

        # Redraw every minute so finished events drop off and the day rolls over
        self.redrawTimer = QTimer(self)
        self.redrawTimer.timeout.connect(self._render)
        self.redrawTimer.start(REDRAW_MS)

    # ----- setup -----

    @staticmethod
    def _loadSettings() -> tuple[CalDavSource | None, int, int]:
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except (OSError, ValueError):
            data = {}

        account = data.get("icloud") if isinstance(data.get("icloud"), dict) else {}
        username = str(account.get("username") or "").strip()
        password = str(account.get("appPassword") or "").strip()
        include = [str(name) for name in data.get("calendars") or [] if isinstance(name, str)]

        source = None
        if username and password:
            source = CalDavSource(username, password, include, DEFAULT_COLORS,
                                  url=str(data.get("server") or ICLOUD_URL))

        def number(key, default):
            try:
                return max(1, int(data.get(key, default)))
            except (TypeError, ValueError):
                return default

        return source, number("daysAhead", DEFAULT_DAYS_AHEAD), number("maxEvents", DEFAULT_MAX_EVENTS)

    def _applySizes(self):
        # Scale against the module's design size (a 480x340 grid cell)
        self.unit = max(0.5, min(self.width() / 480, self.height() / 340))
        u = self.unit
        margin = int(28 * u)
        self.layoutMain.setContentsMargins(margin, int(16 * u), margin, int(12 * u))
        self.agenda.setSpacing(int(4 * u))

        self.monthLabel.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 400; "
            f"font-size: {int(15 * u)}px; letter-spacing: 4px; background: transparent; "
            f"padding-bottom: {int(8 * u)}px;")
        self.weekStrip.setUnit(u)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._applySizes()
        self._render()

    # ----- networking -----

    def refresh(self):
        if self.source is None or self.fetching:
            return
        self.fetching = True

        today = datetime.combine(date.today(), datetime.min.time())
        end = today + timedelta(days=self.daysAhead)

        # CalDAV calls block, so run them off the GUI thread. A daemon thread
        # never holds up quitting the app.
        def work():
            try:
                self.results.fetched.emit(self.source.fetch(today, end))
            except CalendarError as error:
                self.results.failed.emit(str(error))
            except Exception:
                self.results.failed.emit("Calendar unavailable")

        threading.Thread(target=work, daemon=True).start()

    def _onFetched(self, events: list):
        self.fetching = False
        self.events = events
        self.error = None
        self._render()

    def _onFailed(self, message: str):
        # Keep showing the last good copy if a refresh fails
        self.fetching = False
        self.error = message
        self._render()

    # ----- drawing -----

    def _upcomingEvents(self) -> list[dict]:
        now = datetime.now()
        today = now.date()
        events = []
        for event in self.events or []:
            if event["allDay"]:
                # All-day DTEND is exclusive (the day after it ends)
                if event["end"] <= today and event["end"] != event["start"]:
                    continue
            elif event["end"] <= now:
                continue
            events.append(event)

        events.sort(key=lambda e: (max(_startDate(e), today), not e["allDay"],
                                   e["start"] if not e["allDay"] else datetime.min))
        return events

    def _render(self):
        today = date.today()
        weekStart = today - timedelta(days=(today.weekday() + 1) % 7)
        self.monthLabel.setText(today.strftime("%B %Y").upper())

        events = self._upcomingEvents()

        dots: dict[date, list[str]] = {}
        for event in events:
            dots.setdefault(max(_startDate(event), today), []).append(event["color"])
        self.weekStrip.setData(weekStart, today, dots)

        self._clearAgenda()

        if self.source is None:
            self._addMessage("Add your iCloud login\nin Calendar/config.json")
            return
        if self.events is None:
            self._addMessage(self.error or "Loading calendar…")
            return
        if not events:
            self._addMessage("Nothing coming up")
            return

        # Only add rows while they fit, so a busy week never overflows the cell
        margins = self.layoutMain.contentsMargins()
        self.monthLabel.ensurePolished()
        budget = (self.height() - margins.top() - margins.bottom()
                  - self.monthLabel.sizeHint().height() - self.weekStrip.height())

        def fits(*widgets):
            nonlocal budget
            needed = 0
            for widget in widgets:
                widget.ensurePolished()
                needed += widget.sizeHint().height() + self.agenda.spacing()
            if needed > budget:
                for widget in widgets:
                    widget.hide()
                    widget.deleteLater()
                return False
            budget -= needed
            return True

        lastDay = None
        for event in events[:self.maxEvents]:
            day = max(_startDate(event), today)
            row = self._makeEvent(event)
            if day != lastDay:
                header = self._makeDayHeader(day, today, first=lastDay is None)
                if not fits(header, row):
                    break
                self.agenda.addWidget(header)
                lastDay = day
            elif not fits(row):
                break
            self.agenda.addWidget(row)

    def _clearAgenda(self):
        while self.agenda.count():
            item = self.agenda.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def _addMessage(self, text: str):
        u = self.unit
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 300; "
            f"font-size: {int(18 * u)}px; background: transparent; padding-top: {int(24 * u)}px;")
        self.agenda.addWidget(label)

    def _makeDayHeader(self, day: date, today: date, first: bool) -> QLabel:
        u = self.unit
        if day == today:
            text = "TODAY"
        elif day == today + timedelta(days=1):
            text = "TOMORROW"
        else:
            text = f"{day.strftime('%a, %b')} {day.day}".upper()

        label = QLabel(text, self)
        label.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 500; "
            f"font-size: {int(12 * u)}px; letter-spacing: 2px; background: transparent; "
            f"padding-top: {int((10 if first else 14) * u)}px; padding-bottom: {int(2 * u)}px;")
        return label

    def _makeEvent(self, event: dict) -> QWidget:
        u = self.unit
        row = QWidget(self)
        rowLayout = CoreHBoxLayout()
        rowLayout.setAlignment(Qt.AlignmentFlag(0))
        rowLayout.setSpacing(int(12 * u))
        row.setLayout(rowLayout)

        bar = QWidget(row)
        bar.setFixedSize(max(2, int(4 * u)), int(22 * u))
        bar.setStyleSheet(f"background: {event['color']}; border-radius: {max(1, int(2 * u))}px;")

        if event["allDay"]:
            timeText = "All day"
        else:
            timeText = event["start"].strftime("%I:%M %p").lstrip("0")
        timeLabel = QLabel(timeText, row)
        timeLabel.setFixedWidth(int(84 * u))
        timeLabel.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 300; "
            f"font-size: {int(16 * u)}px; background: transparent;")

        titleLabel = ElidedLabel(event["title"], row)
        titleLabel.setStyleSheet(
            f"color: {TEXT_COLOR}; font-family: {FONT_FAMILY}; font-weight: 400; "
            f"font-size: {int(18 * u)}px; background: transparent;")

        rowLayout.addWidget(bar)
        rowLayout.addWidget(timeLabel)
        rowLayout.addWidget(titleLabel, 1)
        return row
