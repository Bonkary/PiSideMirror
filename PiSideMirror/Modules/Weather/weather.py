import json
import math
from pathlib import Path

from CoreWidgets import *
from QModuleCore import QModule
from PySide6.QtWidgets import QSpacerItem
from PySide6.QtCore import QTimer, QUrl, QPointF, QRectF, QDate
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QPolygonF
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Weather data comes from Open-Meteo (free, no API key).
# Set "location" (a city name) and "units" ("imperial" or "metric") in this
# module's config.json.
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_LOCATION = "New York"
DEFAULT_UNITS = "imperial"

REFRESH_MS = 15 * 60 * 1000
RETRY_MS = 60 * 1000
FORECAST_DAYS = 5

FONT_FAMILY = "'Helvetica Neue', 'Segoe UI', 'DejaVu Sans', sans-serif"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#8e99a8"
DIVIDER_COLOR = "#232a33"

SUN = QColor("#ffc83d")
MOON = QColor("#e8eaf6")
CLOUD = QColor("#d5dce6")
CLOUD_DARK = QColor("#8d98a8")
RAIN = QColor("#4fa3ff")
SNOW = QColor("#ffffff")
BOLT = QColor("#ffd54a")
FOG = QColor("#9aa6b5")

# WMO weather code -> (icon kind, description)
CONDITIONS = {
    0: ("clear", "Clear sky"),
    1: ("clear", "Mostly clear"),
    2: ("partly", "Partly cloudy"),
    3: ("cloudy", "Overcast"),
    45: ("fog", "Fog"),
    48: ("fog", "Freezing fog"),
    51: ("rain", "Light drizzle"),
    53: ("rain", "Drizzle"),
    55: ("rain", "Heavy drizzle"),
    56: ("rain", "Freezing drizzle"),
    57: ("rain", "Freezing drizzle"),
    61: ("rain", "Light rain"),
    63: ("rain", "Rain"),
    65: ("rain", "Heavy rain"),
    66: ("rain", "Freezing rain"),
    67: ("rain", "Freezing rain"),
    71: ("snow", "Light snow"),
    73: ("snow", "Snow"),
    75: ("snow", "Heavy snow"),
    77: ("snow", "Snow grains"),
    80: ("rain", "Light showers"),
    81: ("rain", "Showers"),
    82: ("rain", "Heavy showers"),
    85: ("snow", "Snow showers"),
    86: ("snow", "Heavy snow showers"),
    95: ("storm", "Thunderstorm"),
    96: ("storm", "Thunderstorm, hail"),
    99: ("storm", "Thunderstorm, hail"),
}


def _condition(code: int) -> tuple[str, str]:
    return CONDITIONS.get(code, ("cloudy", "Unknown"))


class WeatherIcon(QWidget):
    """A small vector weather icon, drawn in a unit square so it scales cleanly."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.kind = "cloudy"
        self.isDay = True
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setCondition(self, kind: str, isDay: bool = True):
        self.kind = kind
        self.isDay = isDay
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        painter.translate((self.width() - side) / 2, (self.height() - side) / 2)
        painter.scale(side, side)
        painter.setPen(Qt.PenStyle.NoPen)

        kind = self.kind
        if kind == "clear":
            if self.isDay:
                self._sun(painter, 0.5, 0.5, 0.19)
            else:
                self._moon(painter, 0.5, 0.5, 0.3)
        elif kind == "partly":
            if self.isDay:
                self._sun(painter, 0.37, 0.36, 0.14)
            else:
                self._moon(painter, 0.37, 0.36, 0.2)
            self._cloud(painter, 0.56, 0.54, 0.62, CLOUD)
        elif kind == "cloudy":
            self._cloud(painter, 0.62, 0.4, 0.5, CLOUD_DARK)
            self._cloud(painter, 0.46, 0.55, 0.72, CLOUD)
        elif kind == "fog":
            self._cloud(painter, 0.5, 0.36, 0.6, CLOUD)
            self._bars(painter, FOG, [(0.2, 0.8, 0.62), (0.3, 0.7, 0.74), (0.22, 0.78, 0.86)])
        elif kind == "rain":
            self._cloud(painter, 0.5, 0.4, 0.72, CLOUD_DARK)
            self._drops(painter)
        elif kind == "snow":
            self._cloud(painter, 0.5, 0.4, 0.72, CLOUD_DARK)
            painter.setBrush(SNOW)
            for x, y in [(0.3, 0.72), (0.5, 0.82), (0.7, 0.72)]:
                painter.drawEllipse(QPointF(x, y), 0.04, 0.04)
        elif kind == "storm":
            self._cloud(painter, 0.5, 0.38, 0.72, CLOUD_DARK)
            painter.setBrush(BOLT)
            painter.drawPolygon(QPolygonF([
                QPointF(0.54, 0.56), QPointF(0.4, 0.78), QPointF(0.5, 0.78),
                QPointF(0.44, 0.96), QPointF(0.62, 0.7), QPointF(0.52, 0.7),
            ]))

        painter.end()

    @staticmethod
    def _sun(p: QPainter, cx, cy, r):
        p.setBrush(SUN)
        p.drawEllipse(QPointF(cx, cy), r, r)

        pen = QPen(SUN, r * 0.28)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i in range(8):
            angle = i * math.pi / 4
            p.drawLine(
                QPointF(cx + math.cos(angle) * r * 1.45, cy + math.sin(angle) * r * 1.45),
                QPointF(cx + math.cos(angle) * r * 1.85, cy + math.sin(angle) * r * 1.85),
            )
        p.setPen(Qt.PenStyle.NoPen)

    @staticmethod
    def _moon(p: QPainter, cx, cy, r):
        disc = QPainterPath()
        disc.addEllipse(QPointF(cx, cy), r, r)
        bite = QPainterPath()
        bite.addEllipse(QPointF(cx + r * 0.55, cy - r * 0.25), r * 0.85, r * 0.85)
        p.setBrush(MOON)
        p.drawPath(disc.subtracted(bite))

    @staticmethod
    def _cloud(p: QPainter, cx, cy, w, color: QColor):
        base = QPainterPath()
        base.addRoundedRect(QRectF(cx - w * 0.5, cy + w * 0.02, w, w * 0.3), w * 0.15, w * 0.15)
        big = QPainterPath()
        big.addEllipse(QPointF(cx + w * 0.05, cy + w * 0.02), w * 0.28, w * 0.28)
        small = QPainterPath()
        small.addEllipse(QPointF(cx - w * 0.24, cy + w * 0.1), w * 0.19, w * 0.19)
        p.setBrush(color)
        p.drawPath(base.united(big).united(small))

    @staticmethod
    def _bars(p: QPainter, color: QColor, bars):
        pen = QPen(color, 0.05)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for x1, x2, y in bars:
            p.drawLine(QPointF(x1, y), QPointF(x2, y))
        p.setPen(Qt.PenStyle.NoPen)

    @staticmethod
    def _drops(p: QPainter):
        pen = QPen(RAIN, 0.05)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for x in (0.32, 0.5, 0.68):
            p.drawLine(QPointF(x, 0.68), QPointF(x - 0.05, 0.84))
        p.setPen(Qt.PenStyle.NoPen)


class Weather(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 1)
        self.setBackgroundColor('black')

        self.location, self.units = self._loadSettings()
        self._coords: tuple[float, float] | None = None
        self._city = self.location

        self._buildUi()
        self._applySizes()
        self._showMessage("Loading weather…")

        self.network = QNetworkAccessManager(self)
        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.start(REFRESH_MS)
        QTimer.singleShot(0, self.refresh)

    # ----- setup -----

    @staticmethod
    def _loadSettings() -> tuple[str, str]:
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except (OSError, ValueError):
            data = {}
        location = str(data.get("location") or DEFAULT_LOCATION)
        units = str(data.get("units") or DEFAULT_UNITS).lower()
        return location, "metric" if units == "metric" else "imperial"

    def _buildUi(self):
        self.cityLabel = QLabel(self)
        self.cityLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = WeatherIcon(self)
        self.tempLabel = QLabel(self)
        self.conditionLabel = QLabel(self)
        self.tempLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conditionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        textColumn = CoreVBoxLayout()
        textColumn.addWidget(self.tempLabel)
        textColumn.addWidget(self.conditionLabel)

        currentRow = CoreHBoxLayout()
        currentRow.addStretch(1)
        currentRow.addWidget(self.icon)
        currentRow.addLayout(textColumn)
        currentRow.addStretch(1)

        self.detailsLabel = QLabel(self)
        self.detailsLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.divider = QWidget(self)

        forecastRow = CoreHBoxLayout()
        self.days = []
        for _ in range(FORECAST_DAYS):
            dayName = QLabel(self)
            dayIcon = WeatherIcon(self)
            dayTemps = QLabel(self)
            dayName.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dayTemps.setAlignment(Qt.AlignmentFlag.AlignCenter)

            column = CoreVBoxLayout()
            column.addWidget(dayName)
            column.addWidget(dayIcon, 0, Qt.AlignmentFlag.AlignCenter)
            column.addWidget(dayTemps)
            forecastRow.addLayout(column, 1)
            self.days.append((dayName, dayIcon, dayTemps))

        self.messageLabel = QLabel(self)
        self.messageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = CoreVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.cityLabel)
        layout.addLayout(currentRow)
        layout.addWidget(self.detailsLabel)
        # Gaps around the divider are sized in _applySizes so they scale too
        self.gapAboveDivider = QSpacerItem(0, 0)
        self.gapBelowDivider = QSpacerItem(0, 0)
        layout.addItem(self.gapAboveDivider)
        layout.addWidget(self.divider)
        layout.addItem(self.gapBelowDivider)
        layout.addLayout(forecastRow)
        layout.addWidget(self.messageLabel)
        layout.addStretch(1)
        self.setLayout(layout)

    def _applySizes(self):
        # Everything scales with the module width so it fits any screen size
        base = max(self.width(), 300)

        def style(color, weight, px, extra=""):
            return (f"color: {color}; font-family: {FONT_FAMILY}; font-weight: {weight}; "
                    f"font-size: {int(px)}px; background: transparent; {extra}")

        self.cityLabel.setStyleSheet(style(MUTED_COLOR, 400, base * 0.04, "letter-spacing: 4px;"))
        self.tempLabel.setStyleSheet(style(TEXT_COLOR, 200, base * 0.2))
        self.conditionLabel.setStyleSheet(style(TEXT_COLOR, 300, base * 0.05))
        self.detailsLabel.setStyleSheet(
            style(MUTED_COLOR, 300, base * 0.036, f"padding-top: {int(base * 0.02)}px;"))
        self.messageLabel.setStyleSheet(style(MUTED_COLOR, 300, base * 0.045))

        self.icon.setFixedSize(int(base * 0.34), int(base * 0.34))

        margin = int(base * 0.06)
        self.divider.setFixedHeight(1)
        self.divider.setStyleSheet(f"background: {DIVIDER_COLOR}; margin: 0px {margin}px;")

        gap = int(base * 0.06)
        self.gapAboveDivider.changeSize(0, gap)
        self.gapBelowDivider.changeSize(0, gap)
        if self.layout():
            self.layout().invalidate()

        for dayName, dayIcon, dayTemps in self.days:
            dayName.setStyleSheet(style(MUTED_COLOR, 400, base * 0.032, "letter-spacing: 2px;"))
            dayTemps.setStyleSheet(style(TEXT_COLOR, 300, base * 0.038))
            dayIcon.setFixedSize(int(base * 0.12), int(base * 0.12))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._applySizes()

    # ----- networking -----

    def refresh(self):
        if self._coords is None:
            query = QUrl.toPercentEncoding(self.location).data().decode()
            self._get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1",
                self._onGeocode,
            )
        else:
            self._fetchForecast()

    def _fetchForecast(self):
        lat, lon = self._coords
        temperature = "fahrenheit" if self.units == "imperial" else "celsius"
        wind = "mph" if self.units == "imperial" else "kmh"
        self._get(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min"
            f"&temperature_unit={temperature}&wind_speed_unit={wind}"
            f"&timezone=auto&forecast_days={FORECAST_DAYS}",
            self._onForecast,
        )

    def _get(self, url: str, callback):
        reply = self.network.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self._onReply(reply, callback))

    def _onReply(self, reply: QNetworkReply, callback):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            callback(json.loads(bytes(reply.readAll()).decode()))
        except (ValueError, KeyError, IndexError, TypeError):
            self._showMessage("Weather unavailable")
            QTimer.singleShot(RETRY_MS, self.refresh)
        finally:
            reply.deleteLater()

    def _onGeocode(self, data: dict):
        result = data["results"][0]
        self._coords = (result["latitude"], result["longitude"])
        self._city = result.get("name", self.location)
        self._fetchForecast()

    def _onForecast(self, data: dict):
        current = data["current"]
        daily = data["daily"]
        degree = "°"

        kind, description = _condition(current["weather_code"])
        windUnit = "mph" if self.units == "imperial" else "km/h"

        self.cityLabel.setText(self._city.upper())
        self.icon.setCondition(kind, bool(current["is_day"]))
        self.tempLabel.setText(f"{round(current['temperature_2m'])}{degree}")
        self.conditionLabel.setText(description)
        self.detailsLabel.setText(
            f"Feels like {round(current['apparent_temperature'])}{degree}"
            f"   ·   Humidity {round(current['relative_humidity_2m'])}%"
            f"   ·   Wind {round(current['wind_speed_10m'])} {windUnit}"
        )

        for i, (dayName, dayIcon, dayTemps) in enumerate(self.days):
            if i >= len(daily["time"]):
                break
            date = QDate.fromString(daily["time"][i], "yyyy-MM-dd")
            dayName.setText("TODAY" if i == 0 else date.toString("ddd").upper())
            dayIcon.setCondition(_condition(daily["weather_code"][i])[0], True)
            dayTemps.setText(
                f"{round(daily['temperature_2m_max'][i])}{degree}"
                f" <span style='color:{MUTED_COLOR}'>{round(daily['temperature_2m_min'][i])}{degree}</span>"
            )

        self._showMessage("")

    def _showMessage(self, text: str):
        self.messageLabel.setText(text)
        self.messageLabel.setVisible(bool(text))
