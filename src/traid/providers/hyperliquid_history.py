"""Bounded read-only Hyperliquid history transport and C02 normalization."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.client import IncompleteRead
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from traid.domain import Candle, FundingSnapshot, SourceProvenance


UTC = timezone.utc
INFO_URL = "https://api.hyperliquid.xyz/info"
MAX_RESPONSE_BYTES = 2_000_000
MAX_RECORDS_PER_PAGE = 500
MAX_PAGES = 64
PAGE_SPAN = timedelta(days=1)
HOUR = timedelta(hours=1)


class HistoryProviderError(ValueError):
    """The public history response cannot be trusted for this bounded fetch."""


class HistoryRateLimitError(HistoryProviderError):
    """HTTP 429 is terminal; callers must not silently retry or publish."""


@dataclass(frozen=True, slots=True)
class HistoryFetch:
    candles: tuple[Candle, ...]
    funding: tuple[FundingSnapshot, ...]
    fetched_at: datetime
    candle_pages: int
    funding_pages: int
    source: str = "hyperliquid"
    source_type: str = "public_info"
    source_endpoint: str = INFO_URL


def _timestamp_ms(value: Any) -> datetime:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise HistoryProviderError("provider timestamp must be nonnegative integer milliseconds")
    try:
        return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)
    except (ValueError, OverflowError, OSError) as error:
        raise HistoryProviderError("provider timestamp is out of range") from error


def _decimal(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if not isinstance(value, str):
        raise HistoryProviderError("provider decimal must be source text")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise HistoryProviderError("provider decimal is malformed") from error
    if not result.is_finite() or (positive and result <= 0) or (nonnegative and result < 0):
        raise HistoryProviderError("provider decimal is outside its canonical domain")
    return result


def _record(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HistoryProviderError("provider record must be an object")
    if "openInterest" in value or "open_interest" in value:
        raise HistoryProviderError("historical OI is excluded from C06")
    return value


def _candle(value: Any, received: datetime) -> Candle:
    item = _record(value)
    try:
        if item["s"] != "BTC" or item["i"] != "1h":
            raise HistoryProviderError("unexpected candle instrument or interval")
        start, end = _timestamp_ms(item["t"]), _timestamp_ms(item["T"])
        if end != start + HOUR - timedelta(milliseconds=1):
            raise HistoryProviderError("1h candle boundary is invalid")
        return Candle(
            symbol="BTC", start_timestamp=start, end_timestamp=end,
            open=_decimal(item["o"], positive=True), high=_decimal(item["h"], positive=True),
            low=_decimal(item["l"], positive=True), close=_decimal(item["c"], positive=True),
            volume=_decimal(item["v"], nonnegative=True),
            provenance=SourceProvenance(
                source="hyperliquid", source_type="public_info", source_id=str(item["t"]),
                source_timestamp=start, received_timestamp=received,
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, HistoryProviderError):
            raise
        raise HistoryProviderError("invalid canonical candle response") from error


def _funding(value: Any, received: datetime) -> FundingSnapshot:
    item = _record(value)
    try:
        if item["coin"] != "BTC":
            raise HistoryProviderError("unexpected funding instrument")
        source_time = _timestamp_ms(item["time"])
        return FundingSnapshot(
            symbol="BTC", funding_rate=_decimal(item["fundingRate"]), timestamp=source_time,
            provenance=SourceProvenance(
                source="hyperliquid", source_type="public_info", source_id="fundingHistory",
                source_timestamp=source_time, received_timestamp=received,
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, HistoryProviderError):
            raise
        raise HistoryProviderError("invalid canonical funding response") from error


def _json_response(raw: bytes) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise HistoryProviderError("duplicate source JSON key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise HistoryProviderError(f"nonfinite source JSON value: {value}")

    try:
        return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HistoryProviderError("malformed or truncated provider JSON") from error


class HyperliquidHistoryProvider:
    """Fetch only a caller-bounded BTC 1h window, sequentially and read-only."""

    def __init__(
        self,
        *,
        info_url: str = INFO_URL,
        timeout: float = 10.0,
        clock: Callable[[], datetime] | None = None,
        post: Callable[[Mapping[str, Any]], Any] | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.info_url = info_url
        self.timeout = timeout
        self.clock = clock or (lambda: datetime.now(UTC))
        self.post = post or self._http_post

    def _received(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise HistoryProviderError("clock must provide an aware timestamp")
        return value.astimezone(UTC)

    def _http_post(self, payload: Mapping[str, Any]) -> Any:
        request = Request(
            self.info_url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise HistoryProviderError("provider response exceeds bounded size")
            return _json_response(raw)

    def _request(self, payload: Mapping[str, Any]) -> list[Any]:
        for attempt in range(3):  # Initial request plus at most two connection retries.
            try:
                result = self.post(payload)
                break
            except HTTPError as error:
                if error.code == 429:
                    raise HistoryRateLimitError("provider HTTP 429; fail closed") from error
                raise HistoryProviderError(f"provider HTTP {error.code}") from error
            except (URLError, TimeoutError, ConnectionError, OSError) as error:
                if attempt == 2:
                    raise HistoryProviderError("provider connection failed after two retries") from error
            except IncompleteRead as error:
                raise HistoryProviderError("truncated provider response") from error
        if not isinstance(result, list) or len(result) > MAX_RECORDS_PER_PAGE:
            raise HistoryProviderError("provider page shape or size is invalid")
        return result

    def _fetch_category(self, kind: str, start: datetime, end: datetime) -> tuple[list[Candle | FundingSnapshot], int]:
        output: list[Candle | FundingSnapshot] = []
        pages = 0
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + PAGE_SPAN, end)
            cursor = int(chunk_start.timestamp() * 1000)
            upper = int(chunk_end.timestamp() * 1000)
            while cursor < upper:
                if pages >= MAX_PAGES:
                    raise HistoryProviderError("provider pagination exceeded bounded page count")
                payload: dict[str, Any]
                if kind == "candleSnapshot":
                    payload = {"type": kind, "req": {"coin": "BTC", "interval": "1h", "startTime": cursor, "endTime": upper - 1}}
                else:
                    payload = {"type": kind, "coin": "BTC", "startTime": cursor, "endTime": upper - 1}
                page = self._request(payload)
                pages += 1
                received = self._received()
                time_values: list[int] = []
                for raw in page:
                    item = _record(raw)
                    timestamp = item.get("t" if kind == "candleSnapshot" else "time")
                    _timestamp_ms(timestamp)
                    if timestamp < cursor:
                        raise HistoryProviderError("provider page moved before pagination cursor")
                    time_values.append(timestamp)
                    converted = _candle(item, received) if kind == "candleSnapshot" else _funding(item, received)
                    if timestamp < upper:
                        output.append(converted)
                if len(page) < MAX_RECORDS_PER_PAGE:
                    break
                if not time_values or max(time_values) >= upper - 1:
                    raise HistoryProviderError("full provider page has an unprovable boundary")
                if time_values.count(max(time_values)) > 1:
                    raise HistoryProviderError("pagination boundary has indistinguishable source timestamps")
                # The API documents inclusive startTime. Re-read the final
                # timestamp, then let dataset construction collapse it.
                next_cursor = max(time_values)
                if next_cursor <= cursor:
                    raise HistoryProviderError("provider pagination did not advance")
                cursor = next_cursor
            chunk_start = chunk_end
        return output, pages

    def fetch(self, start: datetime, end: datetime) -> HistoryFetch:
        if start.tzinfo is None or end.tzinfo is None:
            raise HistoryProviderError("fetch window must be timezone-aware")
        start, end = start.astimezone(UTC), end.astimezone(UTC)
        if (start.minute, start.second, start.microsecond, end.minute, end.second, end.microsecond) != (0, 0, 0, 0, 0, 0):
            raise HistoryProviderError("fetch window must align to UTC hours")
        if not timedelta(0) < end - start <= timedelta(hours=168):
            raise HistoryProviderError("fetch window must be 1 to 168 hours")
        if self._received() < end:
            raise HistoryProviderError("fetch window is not fully closed")
        candles, candle_pages = self._fetch_category("candleSnapshot", start, end)
        funding, funding_pages = self._fetch_category("fundingHistory", start, end)
        return HistoryFetch(tuple(candles), tuple(funding), self._received(), candle_pages, funding_pages, source_endpoint=self.info_url)
