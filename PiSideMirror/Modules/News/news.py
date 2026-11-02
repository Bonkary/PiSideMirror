import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from CoreWidgets import *
from QModuleCore import QModule
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Headlines come from the outlets' RSS feeds (no API keys). Choose outlets in
# this module's config.json under "outlets", using names from OUTLETS below,
# or add any other feed as {"name": "Local Paper", "url": "https://…/rss"}.
# "maxStories" caps how many headlines rotate; "secondsPerPage" sets the pace.
CONFIG_PATH = Path(__file__).parent / "config.json"

# CNN, Reuters, AP, WSJ and the Washington Post have no working public feed
OUTLETS = {
    "BBC": "https://feeds.bbci.co.uk/news/rss.xml",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Fox News": "https://moxie.foxnews.com/google-publisher/latest.xml",
    "ABC News": "https://abcnews.go.com/abcnews/topstories",
    "CBS News": "https://www.cbsnews.com/latest/rss/main",
    "NBC News": "https://feeds.nbcnews.com/nbcnews/public/news",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Hacker News": "https://hnrss.org/frontpage",
}
DEFAULT_OUTLETS = ["BBC", "NPR", "The Guardian"]
DEFAULT_MAX_STORIES = 12
DEFAULT_SECONDS_PER_PAGE = 15

REFRESH_MS = 10 * 60 * 1000
REDRAW_MS = 60 * 1000

FONT_FAMILY = "'Helvetica Neue', 'Segoe UI', 'DejaVu Sans', sans-serif"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#8e99a8"
OUTLET_COLORS = ["#4fa3ff", "#f87171", "#34d399", "#fbbf24", "#a78bfa", "#f472b6"]

ATOM = "{http://www.w3.org/2005/Atom}"
DUBLIN_CORE = "{http://purl.org/dc/elements/1.1/}"


def _parseDate(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _cleanTitle(text: str | None) -> str:
    # Some feeds put HTML tags or entities in titles
    text = re.sub(r"<[^>]+>", "", html.unescape(text or ""))
    return " ".join(text.split())


def parseFeed(data: bytes) -> list[tuple[str, datetime | None]]:
    """Returns (headline, published) pairs from an RSS or Atom feed."""
    root = ET.fromstring(data)
    stories = []
    for item in root.iter("item"):
        published = item.findtext("pubDate") or item.findtext(f"{DUBLIN_CORE}date")
        stories.append((_cleanTitle(item.findtext("title")), _parseDate(published)))
    for entry in root.iter(f"{ATOM}entry"):
        published = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")
        stories.append((_cleanTitle(entry.findtext(f"{ATOM}title")), _parseDate(published)))
    return [story for story in stories if story[0]]


def _timeAgo(moment: datetime | None) -> str:
    if moment is None:
        return ""
    minutes = int((datetime.now(timezone.utc) - moment).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    if minutes < 24 * 60:
        return f"{minutes // 60}h ago"
    return f"{minutes // (24 * 60)}d ago"


class HeadlineLabel(QLabel):
    """Wraps to at most two lines and ends with … if the headline is longer."""

    MAX_LINES = 2

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        policy = self.sizePolicy()
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def _lines(self, width: int) -> list[str]:
        self.ensurePolished()
        metrics = self.fontMetrics()
        words = self.text().split()
        lines = []
        current = ""
        for i, word in enumerate(words):
            candidate = f"{current} {word}" if current else word
            if current and metrics.horizontalAdvance(candidate) > width:
                lines.append(current)
                current = word
                if len(lines) == self.MAX_LINES - 1:
                    # The last line takes the rest of the text and gets elided
                    current = " ".join(words[i:])
                    break
            else:
                current = candidate
        if current:
            lines.append(current)
        return [metrics.elidedText(line, Qt.TextElideMode.ElideRight, width) for line in lines]

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int) -> int:
        return max(1, len(self._lines(width))) * self.fontMetrics().lineSpacing()

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(0)
        hint.setHeight(self.heightForWidth(max(1, self.width())))
        return hint

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        lineHeight = self.fontMetrics().lineSpacing()
        for i, line in enumerate(self._lines(self.width())):
            rect = self.rect().adjusted(0, i * lineHeight, 0, 0)
            rect.setHeight(lineHeight)
            self.style().drawItemText(
                painter, rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.palette(), True, line, QPalette.ColorRole.WindowText,
            )
        painter.end()


class News(QModule):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.gridSize = (1, 1)
        self.setBackgroundColor('black')

        self.outlets, self.maxStories, secondsPerPage = self._loadSettings()
        self.storiesByOutlet: dict[str, list[tuple[str, datetime | None]]] = {}
        self.failed: set[str] = set()
        self.pageStart = 0
        self.shownCount = 0
        self.unit = 1.0

        self.titleLabel = QLabel("NEWS", self)
        self.stories = CoreVBoxLayout()
        self.stories.setAlignment(Qt.AlignmentFlag.AlignTop)
        storiesWidget = QWidget(self)
        storiesWidget.setLayout(self.stories)

        self.layoutMain = CoreVBoxLayout()
        # The Core layouts center (and shrink) their contents; fill the cell instead
        self.layoutMain.setAlignment(Qt.AlignmentFlag(0))
        self.layoutMain.addWidget(self.titleLabel)
        self.layoutMain.addWidget(storiesWidget, 1)
        self.setLayout(self.layoutMain)

        self._applySizes()
        self._render()

        self.network = QNetworkAccessManager(self)
        self.refreshTimer = QTimer(self)
        self.refreshTimer.timeout.connect(self.refresh)
        self.refreshTimer.start(REFRESH_MS)
        QTimer.singleShot(0, self.refresh)

        self.pageTimer = QTimer(self)
        self.pageTimer.timeout.connect(self._nextPage)
        self.pageTimer.start(secondsPerPage * 1000)

        # Keeps the "12m ago" times current
        self.redrawTimer = QTimer(self)
        self.redrawTimer.timeout.connect(self._render)
        self.redrawTimer.start(REDRAW_MS)

    # ----- setup -----

    @staticmethod
    def _loadSettings() -> tuple[list[dict], int, int]:
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except (OSError, ValueError):
            data = {}

        knownByLowerName = {name.lower(): name for name in OUTLETS}
        outlets = []
        for item in data.get("outlets") or DEFAULT_OUTLETS:
            if isinstance(item, str) and item.strip().lower() in knownByLowerName:
                name = knownByLowerName[item.strip().lower()]
                outlets.append({"name": name, "url": OUTLETS[name]})
            elif isinstance(item, dict) and item.get("url"):
                outlets.append({"name": str(item.get("name") or "News"), "url": str(item["url"])})

        for i, outlet in enumerate(outlets):
            outlet["color"] = OUTLET_COLORS[i % len(OUTLET_COLORS)]

        def number(key, default):
            try:
                return max(1, int(data.get(key, default)))
            except (TypeError, ValueError):
                return default

        return (outlets, number("maxStories", DEFAULT_MAX_STORIES),
                number("secondsPerPage", DEFAULT_SECONDS_PER_PAGE))

    def _applySizes(self):
        # Scale against the module's design size (a 480x340 grid cell)
        self.unit = max(0.5, min(self.width() / 480, self.height() / 340))
        u = self.unit
        margin = int(28 * u)
        self.layoutMain.setContentsMargins(margin, int(16 * u), margin, int(12 * u))
        self.stories.setSpacing(int(14 * u))

        self.titleLabel.setStyleSheet(
            f"color: {MUTED_COLOR}; font-family: {FONT_FAMILY}; font-weight: 400; "
            f"font-size: {int(15 * u)}px; letter-spacing: 4px; background: transparent; "
            f"padding-bottom: {int(12 * u)}px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._applySizes()
        self._render()

    # ----- networking -----

    def refresh(self):
        for outlet in self.outlets:
            request = QNetworkRequest(QUrl(outlet["url"]))
            request.setRawHeader(b"User-Agent", b"Mozilla/5.0 (X11; Linux aarch64) PiSideMirror")
            reply = self.network.get(request)
            reply.finished.connect(lambda reply=reply, outlet=outlet: self._onReply(reply, outlet))

    def _onReply(self, reply: QNetworkReply, outlet: dict):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            self.storiesByOutlet[outlet["name"]] = parseFeed(bytes(reply.readAll()))
            self.failed.discard(outlet["name"])
        except (ValueError, ET.ParseError):
            # Keep the last good headlines if a refresh fails
            self.failed.add(outlet["name"])
        finally:
            reply.deleteLater()
            self._render()

    # ----- drawing -----

    def _allStories(self) -> list[dict]:
        # Take turns between outlets so one busy feed can't fill the screen
        queues = []
        for outlet in self.outlets:
            stories = sorted(
                self.storiesByOutlet.get(outlet["name"], []),
                key=lambda story: story[1] or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            queues.append([{"outlet": outlet, "title": title, "published": published}
                           for title, published in stories])

        merged = []
        while len(merged) < self.maxStories and any(queues):
            for queue in queues:
                if queue and len(merged) < self.maxStories:
                    merged.append(queue.pop(0))
        return merged

    def _nextPage(self):
        self.pageStart += self.shownCount
        self._render()

    def _render(self):
        self._clearStories()

        if not self.outlets:
            self._addMessage("Choose news outlets\nin News/config.json")
            return

        stories = self._allStories()
        if not stories:
            if self.failed and len(self.failed) == len(self.outlets):
                self._addMessage("News unavailable")
            else:
                self._addMessage("Loading headlines…")
            return

        if self.pageStart >= len(stories):
            self.pageStart = 0

        # Fill the page with as many stories as fit, starting where the last page ended
        margins = self.layoutMain.contentsMargins()
        innerWidth = self.width() - margins.left() - margins.right()
        self.titleLabel.ensurePolished()
        budget = (self.height() - margins.top() - margins.bottom()
                  - self.titleLabel.sizeHint().height())

        self.shownCount = 0
        for story in stories[self.pageStart:]:
            widget, height = self._makeStory(story, innerWidth)
            if height > budget and self.shownCount > 0:
                widget.hide()
                widget.deleteLater()
                break
            self.stories.addWidget(widget)
            budget -= height + self.stories.spacing()
            self.shownCount += 1

    def _clearStories(self):
        while self.stories.count():
            item = self.stories.takeAt(0)
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
        self.stories.addWidget(label)

    def _makeStory(self, story: dict, width: int) -> tuple[QWidget, int]:
        u = self.unit
        widget = QWidget(self)
        layout = CoreVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag(0))
        layout.setSpacing(int(4 * u))
        widget.setLayout(layout)

        meta = QLabel(widget)
        meta.setTextFormat(Qt.TextFormat.RichText)
        age = _timeAgo(story["published"])
        meta.setText(
            f"<span style='color:{story['outlet']['color']}; font-weight:600;'>"
            f"{html.escape(story['outlet']['name'].upper())}</span>"
            + (f"<span style='color:{MUTED_COLOR};'>&nbsp;&nbsp;·&nbsp;&nbsp;{age}</span>" if age else "")
        )
        meta.setStyleSheet(
            f"font-family: {FONT_FAMILY}; font-size: {int(12 * u)}px; "
            f"letter-spacing: 1px; background: transparent;")

        headline = HeadlineLabel(story["title"], widget)
        headline.setStyleSheet(
            f"color: {TEXT_COLOR}; font-family: {FONT_FAMILY}; font-weight: 400; "
            f"font-size: {int(19 * u)}px; background: transparent;")

        layout.addWidget(meta)
        layout.addWidget(headline)

        meta.ensurePolished()
        height = meta.sizeHint().height() + layout.spacing() + headline.heightForWidth(width)
        return widget, height
