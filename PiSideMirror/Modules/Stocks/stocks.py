import json
from pathlib import Path

from CoreWidgets import *
from QModuleCore import QModule
from PySide6.QtCore import QTimer, QUrl, QPointF, QTime
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QLinearGradient
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Quotes come from Yahoo Finance's public chart endpoint (no API key, but
# unofficial, so it can change without notice).
# List the stocks in this module's config.json under "symbols". Each entry is
# either a ticker ("AAPL") or {"symbol": "^GSPC", "name": "S&P 500"} to show a
# friendlier name. "rowsPerPage" sets how many show at once; extra rows page.
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
DEFAULT_ROWS_PER_PAGE = 5

REFRESH_MS = 5 * 60 * 1000
PAGE_MS = 10 * 1000
QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=1d&interval=5m"

FONT_FAMILY = "'Helvetica Neue', 'Segoe UI', 'DejaVu Sans', sans-serif"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#8e99a8"
UP_COLOR = QColor("#34d399")
DOWN_COLOR = QColor("#f87171")
FLAT_COLOR = QColor("#8e99a8")

class Sparkline(QWidget):
    """Intraday price line with a dashed marker at the previous close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: list[float] = []
        self.baseline: float | None = None
        self.color = FLAT_COLOR
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def setData(self, points: list[float], baseline: float | None, color: QColor):
        self.points = points
        self.baseline = baseline
        self.color = color
        self.update()

    def paintEvent(self, event):
        if len(self.points) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        values = self.points + ([self.baseline] if self.baseline else [])
        low, high = min(values), max(values)
        span = (high - low) or 1
        pad = self.height() * 0.12
        w, h = self.width(), self.height() - pad * 2

        def toY(value):
            return pad + h - (value - low) / span * h

        step = w / (len(self.points) - 1)
        line = QPainterPath(QPointF(0, toY(self.points[0])))
        for i, value in enumerate(self.points[1:], start=1):
            line.lineTo(QPointF(i * step, toY(value)))

        # Soft fade under the line
        fill = QPainterPath(line)
        fill.lineTo(QPointF(w, self.height()))
        fill.lineTo(QPointF(0, self.height()))
        fill.closeSubpath()
        gradient = QLinearGradient(0, 0, 0, self.height())
        top = QColor(self.color)
        top.setAlpha(70)
        bottom = QColor(self.color)
        bottom.setAlpha(0)
        gradient.setColorAt(0, top)
        gradient.setColorAt(1, bottom)
        painter.fillPath(fill, gradient)

        if self.baseline:
            dash = QPen(QColor("#3a4350"), 1, Qt.PenStyle.DashLine)
            painter.setPen(dash)
            y = toY(self.baseline)
            painter.drawLine(QPointF(0, y), QPointF(w, y))

        pen = QPen(self.color, max(1.5, self.height() * 0.04))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(line)
        painter.end()


class StockRow(QWidget):
    def __init__(self, symbol: str, name: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol

        self.nameLabel = QLabel(name, self)
        self.sparkline = Sparkline(self)
        self.priceLabel = QLabel("—", self)
        self.changeLabel = QLabel("", self)

        self.priceLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.changeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = CoreHBoxLayout()
        layout.addWidget(self.nameLabel)
        layout.addWidget(self.sparkline, 1)
        layout.addWidget(self.priceLabel)
        layout.addWidget(self.changeLabel)
        self.setLayout(layout)

        self.color = FLAT_COLOR
        self.applySizes(400, 60)

    def applySizes(self, width: int, height: int):
        px = int(height * 0.4)
        gap = int(width * 0.03)

        self.layout().setSpacing(gap)
        self.nameLabel.setFixedWidth(int(width * 0.2))
        self.priceLabel.setFixedWidth(int(width * 0.2))
        self.changeLabel.setFixedWidth(int(width * 0.17))
        self.sparkline.setFixedHeight(int(height * 0.7))

        self.nameLabel.setStyleSheet(
            f"color: {TEXT_COLOR}; font-family: {FONT_FAMILY}; font-weight: 600; "
            f"font-size: {px}px; letter-spacing: 1px; background: transparent;")
        self.priceLabel.setStyleSheet(
            f"color: {TEXT_COLOR}; font-family: {FONT_FAMILY}; font-weight: 300; "
            f"font-size: {px}px; background: transparent;")
        self._styleChange(px)

    def _styleChange(self, px: int | None = None):
        if px is not None:
            self._px = px
        tint = QColor(self.color)
        tint.setAlpha(40)
        self.changeLabel.setStyleSheet(
            f"color: {self.color.name()}; font-family: {FONT_FAMILY}; font-weight: 500; "
            f"font-size: {int(self._px * 0.8)}px; "
            f"background: rgba({tint.red()}, {tint.green()}, {tint.blue()}, {tint.alpha()}); "
            f"border-radius: {int(self._px * 0.35)}px; padding: {int(self._px * 0.15)}px 0px;")

    def setQuote(self, price: float, previousClose: float | None, points: list[float]):
        self.priceLabel.setText(f"{price:,.2f}")

        if previousClose:
            change = price - previousClose
            percent = change / previousClose * 100
            self.color = UP_COLOR if change > 0 else DOWN_COLOR if change < 0 else FLAT_COLOR
            arrow = "▲" if change > 0 else "▼" if change < 0 else "•"
            self.changeLabel.setText(f"{arrow} {abs(percent):.2f}%")
        else:
            self.color = FLAT_COLOR
            self.changeLabel.setText("")

        self._styleChange()
        self.sparkline.setData(points, previousClose, self.color)

    def setUnavailable(self):
        self.priceLabel.setText("—")
        self.changeLabel.setText("")
        self.color = FLAT_COLOR
        self._styleChange()
        self.sparkline.setData([], None, FLAT_COLOR)


class Stocks(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 2)
        self.setBackgroundColor('black')

        entries, self.rowsPerPage = self._loadSettings()
        self.page = 0

        self.titleLabel = QLabel("MARKETS", self)
        self.updatedLabel = QLabel("", self)
        self.updatedLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header = CoreHBoxLayout()
        header.addWidget(self.titleLabel)
        header.addStretch(1)
        header.addWidget(self.updatedLabel)

        self.rows = [StockRow(symbol, name, self) for symbol, name in entries]

        layout = CoreVBoxLayout()
        layout.addStretch(1)
        layout.addLayout(header)
        for row in self.rows:
            layout.addWidget(row)
        layout.addStretch(1)
        self.setLayout(layout)

        self._showPage()
        self._applySizes()

        self.network = QNetworkAccessManager(self)
        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.start(REFRESH_MS)
        QTimer.singleShot(0, self.refresh)

        self.pageTimer = QTimer(self)
        self.pageTimer.timeout.connect(self._nextPage)
        if len(self.rows) > self.rowsPerPage:
            self.pageTimer.start(PAGE_MS)

    # ----- setup -----

    @staticmethod
    def _loadSettings() -> tuple[list[tuple[str, str]], int]:
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except (OSError, ValueError):
            data = {}

        entries = []
        for item in data.get("symbols") or DEFAULT_SYMBOLS:
            if isinstance(item, dict) and item.get("symbol"):
                symbol = str(item["symbol"]).upper()
                entries.append((symbol, str(item.get("name") or symbol)))
            elif isinstance(item, str) and item.strip():
                symbol = item.strip().upper()
                entries.append((symbol, symbol))

        try:
            rowsPerPage = max(1, int(data.get("rowsPerPage", DEFAULT_ROWS_PER_PAGE)))
        except (TypeError, ValueError):
            rowsPerPage = DEFAULT_ROWS_PER_PAGE

        return entries, rowsPerPage

    def _applySizes(self):
        # Rows share the module height; text scales with the row height
        width = max(self.width(), 400)
        rowHeight = max(self.height(), 200) / (self.rowsPerPage + 1.6)
        margin = int(width * 0.05)

        self.layout().setContentsMargins(margin, 0, margin, 0)
        innerWidth = width - margin * 2

        headerPx = int(rowHeight * 0.28)
        self.titleLabel.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 400; "
            f"font-size: {headerPx}px; letter-spacing: 4px; background: transparent; "
            f"padding-bottom: {int(rowHeight * 0.2)}px;")
        self.updatedLabel.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 300; "
            f"font-size: {headerPx}px; background: transparent; "
            f"padding-bottom: {int(rowHeight * 0.2)}px;")

        for row in self.rows:
            row.setFixedHeight(int(rowHeight))
            row.applySizes(innerWidth, int(rowHeight))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._applySizes()

    # ----- paging -----

    def _showPage(self):
        start = self.page * self.rowsPerPage
        for i, row in enumerate(self.rows):
            row.setVisible(start <= i < start + self.rowsPerPage)

    def _nextPage(self):
        pages = (len(self.rows) + self.rowsPerPage - 1) // self.rowsPerPage
        self.page = (self.page + 1) % pages
        self._showPage()

    # ----- networking -----

    def refresh(self):
        for row in self.rows:
            symbol = QUrl.toPercentEncoding(row.symbol).data().decode()
            request = QNetworkRequest(QUrl(QUOTE_URL.format(symbol)))
            # Yahoo rejects requests without a browser-like user agent
            request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (X11; Linux aarch64)")
            reply = self.network.get(request)
            reply.finished.connect(lambda reply=reply, row=row: self._onReply(reply, row))

    def _onReply(self, reply: QNetworkReply, row: StockRow):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())

            result = json.loads(bytes(reply.readAll()).decode())["chart"]["result"][0]
            meta = result["meta"]
            closes = result["indicators"]["quote"][0].get("close") or []

            row.setQuote(
                meta["regularMarketPrice"],
                meta.get("chartPreviousClose") or meta.get("previousClose"),
                [c for c in closes if c is not None],
            )
            self.updatedLabel.setText(f"Updated {QTime.currentTime().toString('h:mm AP')}")
        except (ValueError, KeyError, IndexError, TypeError):
            row.setUnavailable()
        finally:
            reply.deleteLater()
