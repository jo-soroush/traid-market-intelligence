"""C12 canonical macro observations: sources, release schedules, BLS series, FOMC records.

Observed source facts keep their source meaning; nothing here interprets them.
Source capabilities below were verified on 2026-10-21 against official sources:

* BLS Public Data API v2 (https://api.bls.gov/publicAPI/v2/timeseries/data/): live
  without a key at the unregistered limits documented in the BLS API FAQ
  (https://www.bls.gov/developers/api_faqs.htm). The API returns the values BLS
  currently publishes (later revisions included); it carries no publication
  timestamp and no vintage history. Missing values are published as "-" with a
  footnote. Without a key the series catalog (titles, units) is disabled, so units
  follow the BLS series-identifier definitions recorded in ``BLS_SERIES``. BLS
  release schedules are not fetched: bls.gov rejects automated schedule retrieval
  under its usage policy, so schedules are caller-supplied with their own source.
* Federal Reserve Board (public domain, https://www.federalreserve.gov/disclaimer.htm):
  the monetary-policy press RSS feed carries GMT publication times; each FOMC
  statement page states its release time with an explicit EST/EDT zone and the
  target-range decision (a change size only when the statement states one); the FOMC
  calendar page lists meetings by their Board (Washington, America/New_York) dates.
* BEA (PCE, GDP): the API requires a registered UserID that is not configured.
* FRED/ALFRED: requires an API key and was in maintenance during verification.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Context, Decimal, ROUND_HALF_EVEN
from enum import StrEnum
import hashlib
import json
import re
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from traid.domain.models import CanonicalModel, SourceProvenance

UTC = timezone.utc
CANONICAL = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
PERIOD = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def utc(value, name: str = "timestamp") -> datetime:
    if isinstance(value, str):  # JSON round trip
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def canonical_json(value) -> str:
    def convert(v):
        if isinstance(v, dict):
            return {k: convert(v[k]) for k in sorted(v)}
        if isinstance(v, (list, tuple)):
            return [convert(x) for x in v]
        if isinstance(v, Decimal):
            return format(v.normalize(CANONICAL), "f")
        if isinstance(v, (datetime, date, time)):
            return v.isoformat()
        if isinstance(v, timedelta):
            return f"{v // timedelta(microseconds=1)}us"
        return v
    return json.dumps(convert(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(model: CanonicalModel) -> str:
    return hashlib.sha256(canonical_json(model.model_dump(mode="python")).encode()).hexdigest()


def rank(model: CanonicalModel):
    """Total order over records: value identity first, then the exact spelling."""
    return canonical_json(model.model_dump(mode="python")), json.dumps(model.model_dump(mode="json"), sort_keys=True)


def next_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    return f"{year + 1}-01" if month == 12 else f"{year}-{month + 1:02d}"


def previous_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


class MacroModel(CanonicalModel):
    @field_validator("retrieved_at", "published_at", "evaluation_time", "scheduled_at", "captured_at",
                     "first_observed_at", "next_scheduled_at", "observed_through", "as_of",
                     "expected_announcement_at", "available_at",
                     mode="before", check_fields=False)
    @classmethod
    def aware(cls, value):
        return None if value is None else utc(value)


# --------------------------------------------------------------------------- sources
class MacroSource(StrEnum):
    BLS = "BLS"
    FEDERAL_RESERVE = "FEDERAL_RESERVE"
    BEA = "BEA"
    FRED_ALFRED = "FRED_ALFRED"


class MacroEventType(StrEnum):
    CPI = "CPI"
    EMPLOYMENT_SITUATION = "EMPLOYMENT_SITUATION"   # nonfarm payrolls and unemployment rate
    PCE = "PCE"
    GDP_ADVANCE = "GDP_ADVANCE"
    FOMC_DECISION = "FOMC_DECISION"


class SupportState(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNAVAILABLE = "UNAVAILABLE"


class SourceCapability(MacroModel):
    source: MacroSource
    state: SupportState
    reason: str
    documentation_url: str
    verified_on: date


SOURCE_CAPABILITIES = (
    SourceCapability(source=MacroSource.BLS, state=SupportState.SUPPORTED,
                     reason="PUBLIC_API_V2_VERIFIED_LIVE_WITHOUT_KEY_LATEST_PUBLISHED_VALUES_ONLY",
                     documentation_url="https://www.bls.gov/developers/api_faqs.htm", verified_on=date(2026, 10, 21)),
    SourceCapability(source=MacroSource.FEDERAL_RESERVE, state=SupportState.SUPPORTED,
                     reason="PUBLIC_DOMAIN_RSS_STATEMENTS_AND_CALENDAR_VERIFIED_LIVE",
                     documentation_url="https://www.federalreserve.gov/feeds/feeds.htm", verified_on=date(2026, 10, 21)),
    SourceCapability(source=MacroSource.BEA, state=SupportState.UNAVAILABLE,
                     reason="BEA_API_REQUIRES_REGISTERED_USERID_NOT_CONFIGURED",
                     documentation_url="https://apps.bea.gov/api/signup/", verified_on=date(2026, 10, 21)),
    SourceCapability(source=MacroSource.FRED_ALFRED, state=SupportState.UNAVAILABLE,
                     reason="FRED_API_REQUIRES_KEY_AND_WAS_IN_MAINTENANCE_DURING_VERIFICATION",
                     documentation_url="https://fred.stlouisfed.org/docs/api/fred/", verified_on=date(2026, 10, 21)),
)
EVENT_SOURCES = {
    MacroEventType.CPI: MacroSource.BLS,
    MacroEventType.EMPLOYMENT_SITUATION: MacroSource.BLS,
    MacroEventType.PCE: MacroSource.BEA,
    MacroEventType.GDP_ADVANCE: MacroSource.BEA,
    MacroEventType.FOMC_DECISION: MacroSource.FEDERAL_RESERVE,
}


def capability(source: MacroSource) -> SourceCapability:
    return next(c for c in SOURCE_CAPABILITIES if c.source is source)


# -------------------------------------------------------------------------- schedule
class ScheduledRelease(MacroModel):
    """A caller-curated schedule entry. Local time and zone must both be stated with evidence;
    a zone is never assumed. Without both, the release time is unknown, not midnight or UTC."""
    event_type: MacroEventType
    reference_period: str = Field(pattern=PERIOD.pattern)
    release_date: date
    release_time: time | None = None
    timezone: str | None = None
    timezone_evidence: str | None = Field(default=None, min_length=1)
    source_url: str = Field(min_length=1)
    retrieved_at: datetime

    @model_validator(mode="after")
    def unambiguous(self):
        if self.release_time is not None and self.release_time.tzinfo is not None:
            raise ValueError("release_time is a local wall-clock time; state its zone in timezone")
        if (self.timezone is None) != (self.timezone_evidence is None):
            raise ValueError("a timezone requires its evidence, and evidence requires a timezone")
        if self.timezone is not None:
            try:
                zone = ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ValueError("timezone must be an IANA zone name") from error
            if self.release_time is not None:
                naive = datetime.combine(self.release_date, self.release_time)
                early, late = naive.replace(tzinfo=zone, fold=0), naive.replace(tzinfo=zone, fold=1)
                if early.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != naive:
                    raise ValueError("local release time does not exist at a daylight-saving change")
                if early.utcoffset() != late.utcoffset():
                    raise ValueError("local release time is ambiguous at a daylight-saving change")
        return self

    def scheduled_at(self) -> datetime | None:
        if self.release_time is None or self.timezone is None:
            return None
        naive = datetime.combine(self.release_date, self.release_time)
        return naive.replace(tzinfo=ZoneInfo(self.timezone)).astimezone(UTC)


# ------------------------------------------------------------------------------- BLS
class SeriesSpec(MacroModel):
    series_id: str
    event_type: MacroEventType
    description: str
    unit: str
    measure: Literal["LEVEL", "RATE"]       # the published level or rate itself; no change is derived
    seasonal_adjustment: Literal["SA", "NSA"]
    unit_basis: Literal["BLS_SERIES_ID_DEFINITION"] = "BLS_SERIES_ID_DEFINITION"


BLS_SERIES = {s.series_id: s for s in (
    SeriesSpec(series_id="CUUR0000SA0", event_type=MacroEventType.CPI, seasonal_adjustment="NSA",
               description="CPI-U, all items, U.S. city average", unit="index, 1982-84=100", measure="LEVEL"),
    SeriesSpec(series_id="CUSR0000SA0", event_type=MacroEventType.CPI, seasonal_adjustment="SA",
               description="CPI-U, all items, U.S. city average", unit="index, 1982-84=100", measure="LEVEL"),
    SeriesSpec(series_id="CES0000000001", event_type=MacroEventType.EMPLOYMENT_SITUATION, seasonal_adjustment="SA",
               # CES counts payroll jobs, not persons: a multiple jobholder is counted once per job.
               description="All employees, total nonfarm (employment level, not the monthly change)",
               unit="thousands of payroll jobs", measure="LEVEL"),
    SeriesSpec(series_id="LNS14000000", event_type=MacroEventType.EMPLOYMENT_SITUATION, seasonal_adjustment="SA",
               description="Unemployment rate, 16 years and over", unit="percent", measure="RATE"),
)}


class Footnote(MacroModel):
    code: str | None
    text: str


class SeriesValue(MacroModel):
    """One monthly value as BLS currently publishes it; "-" is an explicitly unavailable value."""
    reference_period: str = Field(pattern=PERIOD.pattern)
    raw_value: str = Field(min_length=1)
    value: Decimal | None
    preliminary: bool
    footnotes: tuple[Footnote, ...]
    latest: bool

    @model_validator(mode="after")
    def consistent(self):
        if self.raw_value == "-":
            if self.value is not None or not self.footnotes:
                raise ValueError("an unavailable value has no number and must carry its footnote")
        elif self.value is None or Decimal(self.raw_value) != self.value:
            raise ValueError("value must be the exact decimal of the published text")
        if self.preliminary != any(f.code == "P" for f in self.footnotes):
            raise ValueError("preliminary exactly when BLS marks footnote P")
        return self

    @property
    def unavailable_reason(self) -> str | None:
        return None if self.value is not None else "; ".join(f.text for f in self.footnotes)


class SeriesCapture(MacroModel):
    """One API response for one series, as received by TraID at provenance.received_timestamp."""
    series_id: str
    values: tuple[SeriesValue, ...]
    provider_messages: tuple[str, ...]
    provenance: SourceProvenance

    @model_validator(mode="after")
    def known_series(self):
        if self.series_id not in BLS_SERIES:
            raise ValueError("series is not in the verified BLS registry")
        periods = [v.reference_period for v in self.values]
        if periods != sorted(set(periods)):
            raise ValueError("values must be unique and ordered by reference period")
        if self.provenance.source != "bls" or self.provenance.source_id != self.series_id:
            raise ValueError("capture provenance must name BLS and the series")
        if sum(v.latest for v in self.values) > 1:
            raise ValueError("at most one value can be marked latest")
        return self

    def value(self, period: str) -> SeriesValue | None:
        return next((v for v in self.values if v.reference_period == period), None)


# ------------------------------------------------------------------------------ FOMC
class FomcMeeting(MacroModel):
    start_date: date
    end_date: date
    projections: bool        # calendar marks a Summary of Economic Projections meeting
    notation_vote: bool      # an action taken by notation vote, not a scheduled meeting

    @model_validator(mode="after")
    def ordered(self):
        if not self.start_date <= self.end_date or (self.end_date - self.start_date).days > 3:
            raise ValueError("meeting dates must be ordered and span at most a few days")
        return self


class FomcCalendar(MacroModel):
    meetings: tuple[FomcMeeting, ...]
    source_url: str
    provenance: SourceProvenance

    @model_validator(mode="after")
    def ordered(self):
        keys = [(m.start_date, m.end_date) for m in self.meetings]
        if keys != sorted(set(keys)):
            raise ValueError("meetings must be unique and ordered")
        return self


class PolicyAction(StrEnum):
    MAINTAIN = "MAINTAIN"
    RAISE = "RAISE"
    LOWER = "LOWER"


class FomcStatement(MacroModel):
    """A published FOMC statement: the decision as stated, at its verified publication time.

    ``stated_change_percentage_points`` is the change size only when the statement states it
    ("by 1/4 percentage point"); statements that only announce the new range ("decided to raise
    the target range ... to 5-1/4 to 5-1/2 percent") leave it None. A change derived from an
    earlier statement is evidence, not a statement fact."""
    statement_date: date
    url: str
    published_at: datetime          # feed GMT time, cross-checked with the page's EST/EDT release time
    release_time_text: str
    action: PolicyAction
    stated_change_percentage_points: Decimal | None
    target_lower_percent: Decimal = Field(ge=0)
    target_upper_percent: Decimal = Field(ge=0)
    decision_text: str
    provenance: SourceProvenance

    @model_validator(mode="after")
    def coherent(self):
        if not self.target_lower_percent < self.target_upper_percent:
            raise ValueError("target range lower bound must be below the upper bound")
        if self.action is PolicyAction.MAINTAIN and self.stated_change_percentage_points is not None:
            raise ValueError("a maintained range has no change size")
        if self.stated_change_percentage_points is not None and self.stated_change_percentage_points <= 0:
            raise ValueError("change size must be positive")
        if self.provenance.received_timestamp < self.published_at:
            raise ValueError("a statement cannot be received before its publication")
        return self
