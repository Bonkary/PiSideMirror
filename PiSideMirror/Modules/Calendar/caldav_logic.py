from datetime import datetime

import caldav
import recurring_ical_events
from caldav.elements import ical
from caldav.lib.error import AuthorizationError

ICLOUD_URL = "https://caldav.icloud.com"
TIMEOUT_SECONDS = 30


class CalendarError(Exception):
    """A failure with a message short enough to show on the mirror."""


def expandEvents(calendar, start: datetime, end: datetime, color: str) -> list[dict]:
    """Expands an icalendar.Calendar (including recurring events) into events between start and end."""
    events = []
    for event in recurring_ical_events.of(calendar).between(start, end):
        begin = event.get("DTSTART").dt
        finish = event.get("DTEND").dt if event.get("DTEND") else begin
        allDay = not isinstance(begin, datetime)

        if not allDay:
            # Floating times (no timezone) are already local
            begin = begin.astimezone().replace(tzinfo=None) if begin.tzinfo else begin
            finish = finish.astimezone().replace(tzinfo=None) if getattr(finish, "tzinfo", None) else finish

        events.append({
            "title": str(event.get("SUMMARY") or "Untitled"),
            "start": begin,
            "end": finish,
            "allDay": allDay,
            "color": color,
        })
    return events


class CalDavSource:
    """Signs in to a CalDAV account and fetches events from its calendars.

    fetch() blocks on the network, so call it from a worker thread.
    """

    def __init__(self, username: str, password: str, include: list[str],
                 defaultColors: list[str], url: str = ICLOUD_URL):
        self.url = url
        self.username = username
        self.password = password
        self.include = {name.strip().lower() for name in include if name.strip()}
        self.defaultColors = defaultColors
        self._calendars: list[tuple[caldav.Calendar, str]] | None = None

    def fetch(self, start: datetime, end: datetime) -> list[dict]:
        try:
            if self._calendars is None:
                self._calendars = self._discoverCalendars()

            # Aware times so the server doesn't guess the timezone
            start, end = start.astimezone(), end.astimezone()
            events = []
            for calendar, color in self._calendars:
                for item in calendar.search(start=start, end=end, event=True, expand=False):
                    events.extend(expandEvents(item.icalendar_instance, start, end, color))
            return events
        except AuthorizationError:
            self._calendars = None
            raise CalendarError("iCloud sign-in failed")
        except CalendarError:
            raise
        except Exception as error:
            # Rediscover next time in case calendars were added or removed
            self._calendars = None
            raise CalendarError("Calendar unavailable") from error

    def _discoverCalendars(self) -> list[tuple[caldav.Calendar, str]]:
        client = caldav.DAVClient(url=self.url, username=self.username,
                                  password=self.password, timeout=TIMEOUT_SECONDS)
        found = []
        for calendar in client.principal().calendars():
            if not self._holdsEvents(calendar):
                continue
            name = calendar.get_display_name() or ""
            if self.include and name.strip().lower() not in self.include:
                continue
            color = self._serverColor(calendar) or self.defaultColors[len(found) % len(self.defaultColors)]
            found.append((calendar, color))

        if not found:
            raise CalendarError("No matching calendars found")
        return found

    @staticmethod
    def _holdsEvents(calendar: caldav.Calendar) -> bool:
        # iCloud lists Reminders as calendars too; they only hold tasks
        try:
            return "VEVENT" in calendar.get_supported_components()
        except Exception:
            return True

    @staticmethod
    def _serverColor(calendar: caldav.Calendar) -> str | None:
        # Apple stores the calendar's color as #RRGGBBAA
        try:
            color = calendar.get_property(ical.CalendarColor())
        except Exception:
            return None
        if color and color.startswith("#") and len(color) >= 7:
            return color[:7]
        return None
