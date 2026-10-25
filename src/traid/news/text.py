"""Shared normalization N (design §6.6), closed passage grammars and date windows (§5.2).

N is applied identically to a recorded manual passage and to the GovInfo HTML before any
comparison. HTML is reduced to text only by stripping tags and unescaping entities; it is
untrusted data and nothing in it is ever interpreted as an instruction.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import html as htmllib
import re

UTC = timezone.utc
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
MONTH_NUMBER = {m: i for i, m in enumerate(MONTHS, 1)}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SECTION_OF_TYPE = {"Notice": "Notices", "Rule": "Rules", "Proposed Rule": "Proposed Rules"}
PAGE_MARKER = re.compile(r"\[\[Page (\d+)\]\]")
_MARK = "\ue000"   # private-use sentinel for page markers while locating passages


def common(text: str) -> str:
    """Steps shared by both sides: quote forms, en dash, whitespace, line-wrap after a hyphen."""
    t = text.replace("\u2018\u2018", '"').replace("\u2019\u2019", '"').replace("``", '"').replace("''", '"')
    t = t.replace("\u2013", "-")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"-\s+(?=[A-Za-z0-9])", "-", t).strip()


def normalize_passage(text: str) -> str:
    """N for a recorded passage (rendered PDF text as typed by the verifier)."""
    return common(text)


def _html_steps(raw: str, marker) -> str:
    h = htmllib.unescape(re.sub(r"<[^>]+>", " ", raw))
    h = PAGE_MARKER.sub(marker, h)
    h = re.sub(r"\\(\d+)\\", r" \1 ", h)           # footnote marker \87\ renders as a bare 87
    return re.sub(r"-{10,}", " ", h)               # footnote separator runs


def html_text(raw: str) -> str:
    """N for a GovInfo HTML document."""
    return common(_html_steps(raw, " "))


def html_pages(raw: str, first_page: int) -> list[tuple[int, int]]:
    """(offset in html_text, printed page) where each printed page starts, from the [[Page N]] markers."""
    marked = common(_html_steps(raw, lambda m: f" {_MARK}{m.group(1)}{_MARK} "))
    pages, out, pos = [(0, first_page)], [], 0
    for m in re.finditer(rf"{_MARK}(\d+){_MARK}", marked):
        out.append(marked[pos:m.start()])
        pages.append((len(common(" ".join(out))) + 1, int(m.group(1))))
        pos = m.end()
    return pages


def page_at(pages: list[tuple[int, int]], offset: int) -> int:
    return [p for start, p in pages if start <= offset][-1]


# --------------------------------------------------------------------- closed grammars
DATE_TEXT = r"(?P<month>[A-Z][a-z]+) (?P<day>\d{1,2}), (?P<year>\d{4})"
WEEKDAY_DATE = r"(?P<weekday>[A-Z][a-z]+), " + DATE_TEXT
PDF_HEADER = (   # first-page form (page number first) and the odd-page form (page number last)
    re.compile(r"^(?P<page>\d+) Federal Register\s*/\s*Vol\. (?P<vol>\d+), No\. (?P<issue>\d+)\s*/\s*" + WEEKDAY_DATE
               + r"\s*/\s*(?P<section>Notices|Rules|Proposed Rules)$"),
    re.compile(r"^Federal Register\s*/\s*Vol\. (?P<vol>\d+), No\. (?P<issue>\d+)\s*/\s*" + WEEKDAY_DATE
               + r"\s*/\s*(?P<section>Notices|Rules|Proposed Rules) (?P<page>\d+)$"),
)
HTML_HEADER = re.compile(r"\[Federal Register Volume (?P<vol>\d+), Number (?P<issue>\d+) \(" + WEEKDAY_DATE + r"\)\]"
                         r"\s*\[(?P<section>Notices|Rules|Proposed Rules)\]\s*\[Pages? (?P<start>\d+)(?:-(?P<end>\d+))?\]")
HEADING = re.compile(r"^\[Release No\. (?P<release>\d{2}-\d{4,6}); File Nos?\. (?P<files>[^\]]+)\]$")
TERMINATOR = re.compile(r"^\[FR Doc\. (?P<n>\d{4}-\d{5}) Filed (?P<m>\d{1,2})-(?P<d>\d{1,2})-(?P<y>\d{2}); "
                        r"(?P<hh>\d{1,2}):(?P<mm>\d{2}) (?P<ampm>am|pm)\]$")
DATE_LINE_END = re.compile(DATE_TEXT + r"\.$")
FILE_NUMBER = re.compile(r"^SR-[A-Z0-9]+-\d{4}-\d{2,3}$")
HEADING_MARK = "[Release No. "
TERMINATOR_MARK = "[FR Doc. "


def parse_date_text(match) -> date | None:
    if match.group("month") not in MONTH_NUMBER:
        return None
    try:
        return date(int(match.group("year")), MONTH_NUMBER[match.group("month")], int(match.group("day")))
    except ValueError:
        return None


def canonical_file_number(value: str) -> str | None:
    """Uppercase, no whitespace, U+2013/U+2014 as '-': "SR- NYSEArca-2021-90" -> "SR-NYSEARCA-2021-90"."""
    v = re.sub(r"\s+", "", value.replace("\u2013", "-").replace("\u2014", "-")).upper()
    return v if FILE_NUMBER.match(v) else None


def parse_heading(text: str) -> tuple[str, tuple[str, ...]] | None:
    m = HEADING.match(normalize_passage(text))
    if m is None:
        return None
    files = tuple(canonical_file_number(f) for f in m.group("files").split(";"))
    return (m.group("release"), files) if files and all(files) else None


def docket_identifiers(docket_ids: tuple[str, ...]) -> tuple[str | None, tuple[str, ...]]:
    """FR JSON docket_ids, e.g. ("Release No. 34-99306", "File Nos. SR-A-2021-90", "SR-B-2023-44")."""
    release, files = None, []
    for item in docket_ids:
        if item.startswith("Release No. "):
            release = item[len("Release No. "):].strip()
            continue
        files.append(canonical_file_number(re.sub(r"^File Nos?\. ", "", item.strip())) or f"UNPARSEABLE:{item}")
    return release, tuple(files)


def parse_terminator(text: str) -> tuple[str, date, time] | None:
    m = TERMINATOR.match(normalize_passage(text))
    if m is None:
        return None
    try:
        day = date(2000 + int(m.group("y")), int(m.group("m")), int(m.group("d")))
        hour = int(m.group("hh")) % 12 + (12 if m.group("ampm") == "pm" else 0)
        return m.group("n"), day, time(hour, int(m.group("mm")))
    except ValueError:
        return None


def parse_date_line(text: str) -> date | None:
    m = DATE_LINE_END.search(normalize_passage(text))
    return parse_date_text(m) if m else None


def parse_page_header(text: str) -> tuple[int, int, int, str, date | None, str] | None:
    t = normalize_passage(text)
    m = next((m for m in (r.match(t) for r in PDF_HEADER) if m), None)
    if m is None:
        return None
    return int(m.group("page")), int(m.group("vol")), int(m.group("issue")), m.group("weekday"), \
        parse_date_text(m), m.group("section")


def parse_html_header(html_normalized: str):
    m = HTML_HEADER.search(html_normalized)
    if m is None:
        return None
    return dict(volume=int(m.group("vol")), issue=int(m.group("issue")), weekday=m.group("weekday"),
                date=parse_date_text(m), section=m.group("section"), start=int(m.group("start")),
                end=int(m.group("end") or m.group("start")))


# ----------------------------------------------------------------------- date semantics
def parse_date_value(value: str) -> date | datetime | None:
    """An ISO date, a long-form date ("January 10, 2024"), or an aware ISO datetime (stated time and zone)."""
    v = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return date.fromisoformat(v)
        m = re.fullmatch(DATE_TEXT, v)
        if m:
            return parse_date_text(m)
        if "T" in v:
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d.astimezone(UTC) if d.tzinfo is not None and d.utcoffset() is not None else None
    except ValueError:
        return None
    return None


def window(label: date) -> tuple[datetime, datetime]:
    """Every instant a date label can mean in some zone from UTC+14 to UTC-12: [D-1 10:00Z, D+1 12:00Z)."""
    start = datetime.combine(label - timedelta(days=1), time(10), tzinfo=UTC)
    return start, datetime.combine(label + timedelta(days=1), time(12), tzinfo=UTC)


def precedes(a: date, b: date) -> bool:
    """a precedes b only when their windows cannot overlap."""
    return window(a)[1] <= window(b)[0]


def compare_labels(asserted: date, documented: date) -> str:
    """SUPPORTED, DATE_ZONE_AMBIGUOUS (1-2 days, windows overlap) or CONTRADICTED (3+ days)."""
    days = abs((asserted - documented).days)
    return "SUPPORTED" if days == 0 else "DATE_ZONE_AMBIGUOUS" if days <= 2 else "CONTRADICTED"
