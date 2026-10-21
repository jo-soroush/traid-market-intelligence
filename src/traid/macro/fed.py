"""Read-only Federal Reserve Board adapter for FOMC statements and the meeting calendar.

Board website content is public domain (https://www.federalreserve.gov/disclaimer.htm).
Three official paths, verified live on 2026-10-21:

* ``/feeds/press_monetary.xml``: RSS items with ``pubDate`` in GMT; FOMC statements are
  the items titled "Federal Reserve issues FOMC statement".
* ``/newsevents/pressreleases/monetaryYYYYMMDDa.htm``: the statement page states its
  date ("September 16, 2026"), its release time with an explicit zone ("For release at
  2:00 p.m. EDT") and the decision in one of three verified forms (hyphens may be U+2011):
  "decided to maintain the target range for the federal funds rate at 3-1/2 to 3-3/4
  percent"; "decided to raise|lower ... by 1/4 percentage point to 3-3/4 to 4 percent";
  or the target-only form "decided to raise ... to 5-1/4 to 5-1/2 percent" (July 26, 2023)
  / "decided to lower ... to 0 to 1/4 percent" (March 15, 2020, released 5:00 p.m. EDT).
  A change size is recorded only when stated; it is never inferred here.
* ``/monetarypolicy/fomccalendars.htm``: per-year sections "YYYY FOMC Meetings" with
  month labels ("April", "Apr/May") and dates ("28-29", "30-1", "17-18*",
  "22 (notation vote)").

A statement is accepted only when its stated EST/EDT zone matches America/New_York on
that date and its release time equals the feed's GMT ``pubDate``; anything else fails
closed. Pages are parsed by fixed patterns, never by inference.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from fractions import Fraction
import html
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, ValidationError

from traid.domain.models import SourceProvenance
from traid.exchange.errors import AdapterError, AdapterErrorCode, AdapterRateLimitError, ProviderDataError
from traid.macro.models import FomcCalendar, FomcMeeting, FomcStatement, PolicyAction

BASE = "https://www.federalreserve.gov"
FEED_URL = f"{BASE}/feeds/press_monetary.xml"
CALENDAR_URL = f"{BASE}/monetarypolicy/fomccalendars.htm"
STATEMENT_URL = re.compile(r"^https://www\.federalreserve\.gov/newsevents/pressreleases/monetary(\d{8})a\.htm$")
STATEMENT_TITLE = "Federal Reserve issues FOMC statement"
NEW_YORK = ZoneInfo("America/New_York")
ZONES = {"EST": timedelta(hours=-5), "EDT": timedelta(hours=-4)}
MAX_DOCUMENT = 2_000_000
UTC = timezone.utc
MONTHS = {name: i for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}
MONTHS.update({name[:3]: i for name, i in list(MONTHS.items())})


class FeedItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str
    url: str
    published_at: datetime


def _text(fragment: str) -> str:
    text = re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = text.replace("‑", "-").replace("‐", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _bounded(document: Any) -> str:
    if not isinstance(document, str) or len(document) > MAX_DOCUMENT:
        raise ProviderDataError("Federal Reserve document must be bounded text")
    return document


# ------------------------------------------------------------------------------ feed
def parse_monetary_feed(document: str) -> tuple[FeedItem, ...]:
    document = _bounded(document).lstrip("﻿")
    if "<!DOCTYPE" in document or "<!ENTITY" in document:
        raise ProviderDataError("feed must not declare a DTD or entities")
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise ProviderDataError("feed is not well-formed XML") from error
    items = []
    for item in root.iter("item"):
        title, link, pub = (item.findtext(k) for k in ("title", "link", "pubDate"))
        if not title or not link or not pub:
            raise ProviderDataError("feed item lacks title, link or pubDate")
        try:
            published = parsedate_to_datetime(pub.strip())
        except (TypeError, ValueError) as error:
            raise ProviderDataError("feed pubDate is malformed") from error
        if published.tzinfo is None or published.utcoffset() is None:
            raise ProviderDataError("feed pubDate must carry a zone")
        items.append(FeedItem(title=html.unescape(title.strip()), url=link.strip(), published_at=published.astimezone(UTC)))
    return tuple(items)


def statement_items(items: tuple[FeedItem, ...]) -> tuple[FeedItem, ...]:
    return tuple(sorted((i for i in items if i.title == STATEMENT_TITLE), key=lambda i: (i.published_at, i.url)))


# ------------------------------------------------------------------------- statement
_NUMBER = r"(\d+(?:-\d/\d)?|\d/\d)"
_DECISION = re.compile(
    r"decided to (maintain|raise|lower) the target range for the federal funds rate "
    rf"(at|(?:by {_NUMBER} percentage points? )?to) {_NUMBER} to {_NUMBER} percent")
_RELEASE = re.compile(r"For release at (\d{1,2}):(\d{2}) ([ap])\.m\. (EST|EDT)")
_DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) "
                   r"(\d{1,2}), (\d{4}) Federal Reserve issues FOMC statement")


def _fraction(text: str) -> Decimal:
    whole, _, part = text.rpartition("-") if "-" in text else ("", "", text)
    if "/" in part:
        num, den = part.split("/")
        if den not in ("2", "4", "8"):
            raise ProviderDataError("unexpected fraction in a rate")
        value = Fraction(int(num), int(den)) + (int(whole) if whole else 0)
    else:
        if whole:
            raise ProviderDataError("malformed rate")
        value = Fraction(int(part))
    # Halves, quarters and eighths are exact in thousandths; build from text so no ambient
    # Decimal context can round the result.
    thousandths = value.numerator * (1000 // value.denominator)
    return Decimal(f"{thousandths // 1000}.{thousandths % 1000:03d}")


def parse_fomc_statement(document: str, *, item: FeedItem, received: datetime) -> FomcStatement:
    match = STATEMENT_URL.match(item.url)
    if item.title != STATEMENT_TITLE or not match:
        raise ProviderDataError("not an FOMC statement feed item")
    text = _text(_bounded(document))
    dates = set(_DATE.findall(text))
    releases = set(_RELEASE.findall(text))
    decisions = set(_DECISION.findall(text))
    if len(dates) != 1 or len(releases) != 1 or len(decisions) != 1:
        raise ProviderDataError("statement date, release time or decision is missing or ambiguous")
    (month, day, year), = dates
    statement_date = date(int(year), MONTHS[month.lower()], int(day))
    if match.group(1) != statement_date.strftime("%Y%m%d"):
        raise ProviderDataError("statement URL date and page date disagree")
    (hour, minute, meridiem, zone), = releases
    hour = int(hour) % 12 + (12 if meridiem == "p" else 0)
    local = datetime(statement_date.year, statement_date.month, statement_date.day, hour, int(minute))
    if local.replace(tzinfo=NEW_YORK).tzname() != zone:
        raise ProviderDataError("stated EST/EDT zone contradicts America/New_York on that date")
    published = (local - ZONES[zone]).replace(tzinfo=UTC)
    if published != item.published_at:
        raise ProviderDataError("page release time and feed publication time disagree")
    (verb, preposition, change, lower, upper), = decisions
    action = {"maintain": PolicyAction.MAINTAIN, "raise": PolicyAction.RAISE, "lower": PolicyAction.LOWER}[verb]
    if (action is PolicyAction.MAINTAIN) != (preposition == "at"):
        raise ProviderDataError("decision verb and wording disagree")
    received = received.astimezone(UTC)
    try:
        return FomcStatement(
            statement_date=statement_date, url=item.url, published_at=published,
            release_time_text=f"{int(hour) % 12 or 12}:{minute} {meridiem}.m. {zone}",
            action=action, stated_change_percentage_points=None if change == "" else _fraction(change),
            target_lower_percent=_fraction(lower), target_upper_percent=_fraction(upper),
            decision_text=_DECISION.search(text).group(0),
            provenance=SourceProvenance(source="federal_reserve_board", source_type="public_website",
                                        source_id=item.url, source_timestamp=published, received_timestamp=received))
    except ValidationError as error:
        raise ProviderDataError("statement decision is inconsistent") from error


# -------------------------------------------------------------------------- calendar
_HEADING = re.compile(r"(\d{4}) FOMC Meetings")
_MEETING = re.compile(r'fomc-meeting__month[^>]*>(.*?)</div>.*?fomc-meeting__date[^>]*>(.*?)</div>', re.S)
_DAYS = re.compile(r"^(\d{1,2})(?:-(\d{1,2}))?(\*)?(?: \((notation vote)\))?$")


def parse_fomc_calendar(document: str, *, received: datetime) -> FomcCalendar:
    document = _bounded(document)
    heads = [(m.start(), int(m.group(1))) for m in _HEADING.finditer(document)]
    if not heads:
        raise ProviderDataError("calendar has no year sections")
    meetings = []
    for k, (start, year) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(document)
        for month_html, day_html in _MEETING.findall(document[start:end]):
            meetings.append(_meeting(year, _text(month_html), _text(day_html)))
    if not meetings:
        raise ProviderDataError("calendar lists no meetings")
    unique = sorted(set(meetings), key=lambda m: (m.start_date, m.end_date))
    try:
        return FomcCalendar(meetings=tuple(unique), source_url=CALENDAR_URL, provenance=SourceProvenance(
            source="federal_reserve_board", source_type="public_website", source_id=CALENDAR_URL,
            source_timestamp=None, received_timestamp=received.astimezone(UTC)))
    except ValidationError as error:
        raise ProviderDataError("calendar is inconsistent") from error


def _meeting(year: int, month_label: str, day_label: str) -> FomcMeeting:
    months = [MONTHS.get(part.strip().lower()) for part in month_label.split("/")]
    match = _DAYS.match(day_label)
    if not match or None in months or len(months) > 2 or (len(months) == 2 and match.group(2) is None):
        raise ProviderDataError(f"unrecognized calendar entry: {month_label} {day_label}")
    first, last = int(match.group(1)), int(match.group(2) or match.group(1))
    try:
        start = date(year, months[0], first)
        end = date(year, months[-1], last)
        return FomcMeeting(start_date=start, end_date=end, projections=bool(match.group(3)),
                           notation_vote=bool(match.group(4)))
    except (ValueError, ValidationError) as error:
        raise ProviderDataError(f"invalid calendar dates: {month_label} {day_label}") from error


# ---------------------------------------------------------------------------- client
class FederalReserveClient:
    """Fetches only the feed, statement pages and the calendar; parsing is above."""

    def __init__(self, *, timeout: float = 15.0, clock: Callable[[], datetime] | None = None,
                 transport: Callable[[str], str] | None = None) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._transport = transport or self._http

    def _http(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "TraID macro evidence (read-only)"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read(MAX_DOCUMENT + 1).decode("utf-8")
        except HTTPError as error:
            if error.code == 429:
                raise AdapterRateLimitError() from error
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "Federal Reserve HTTP request failed") from error
        except (URLError, TimeoutError, OSError, UnicodeDecodeError) as error:
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "Federal Reserve request failed") from error

    def _get(self, url: str) -> tuple[str, datetime]:
        if url not in (FEED_URL, CALENDAR_URL) and not STATEMENT_URL.match(url):
            raise AdapterError(AdapterErrorCode.CONTRACT, "URL is outside the verified Federal Reserve paths")
        document = self._transport(url)
        received = self._clock()
        if not isinstance(received, datetime) or received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("clock must return an aware datetime")
        return document, received.astimezone(UTC)

    def feed(self) -> tuple[FeedItem, ...]:
        return parse_monetary_feed(self._get(FEED_URL)[0])

    def statement(self, item: FeedItem) -> FomcStatement:
        document, received = self._get(item.url)
        return parse_fomc_statement(document, item=item, received=received)

    def calendar(self) -> FomcCalendar:
        document, received = self._get(CALENDAR_URL)
        return parse_fomc_calendar(document, received=received)
