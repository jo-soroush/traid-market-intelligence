"""Read-only BLS Public Data API v2 adapter for the verified C12 series.

One POST to ``https://api.bls.gov/publicAPI/v2/timeseries/data/`` returns current
published values for up to 25 series over up to 10 years without a key (50 series,
20 years with a registration key; BLS API FAQ). The response is validated strictly:
``status`` must be ``REQUEST_SUCCEEDED``; monthly periods ``M01``..``M12`` only (the
``M13`` annual average is not a release value and is rejected); ``-`` is an
unavailable value kept with its footnote, never zero; footnote ``P`` marks a
preliminary value. The registration key, when supplied, is sent only in the request
body and never stored in provenance. Receipt time comes from an injectable clock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from traid.domain.models import SourceProvenance
from traid.exchange.errors import AdapterError, AdapterErrorCode, AdapterRateLimitError, ProviderDataError
from traid.macro.models import BLS_SERIES, Footnote, SeriesCapture, SeriesValue

API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
UNREGISTERED_LIMITS = (25, 10)   # series per query, years per query
REGISTERED_LIMITS = (50, 20)
UTC = timezone.utc


def _list(value) -> list:
    if not isinstance(value, list):
        raise ProviderDataError("BLS response shape is invalid")
    return value


def _mapping(value) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderDataError("BLS record shape is invalid")
    return value


def _text(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderDataError("BLS field must be non-empty text")
    return value.strip()


class BlsClient:
    def __init__(self, *, registration_key: str | None = None, timeout: float = 15.0,
                 clock: Callable[[], datetime] | None = None,
                 transport: Callable[[Mapping[str, Any]], Any] | None = None) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if registration_key is not None and not registration_key.strip():
            raise ValueError("registration key must be non-empty when supplied")
        self._key = registration_key
        self.timeout = timeout
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._transport = transport or self._http

    def _http(self, body: Mapping[str, Any]) -> Any:
        request = Request(API_URL, data=json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if error.code == 429:
                raise AdapterRateLimitError() from error
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "BLS HTTP request failed") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "BLS request failed") from error

    def series(self, series_ids: tuple[str, ...], start_year: int, end_year: int) -> tuple[SeriesCapture, ...]:
        max_series, max_years = REGISTERED_LIMITS if self._key else UNREGISTERED_LIMITS
        if not series_ids or len(set(series_ids)) != len(series_ids) or len(series_ids) > max_series:
            raise ValueError("series ids must be unique and within the documented per-query limit")
        if any(s not in BLS_SERIES for s in series_ids):
            raise ValueError("only verified registry series may be requested")
        if not 1900 < start_year <= end_year or end_year - start_year + 1 > max_years:
            raise ValueError("year range must be ordered and within the documented per-query limit")
        body = {"seriesid": list(series_ids), "startyear": str(start_year), "endyear": str(end_year)}
        if self._key:
            body["registrationkey"] = self._key
        payload = self._transport(body)
        received = self._clock()
        if not isinstance(received, datetime) or received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("clock must return an aware datetime")
        return parse_bls_response(payload, tuple(series_ids), received.astimezone(UTC))


def parse_bls_response(payload: Any, requested: tuple[str, ...], received: datetime) -> tuple[SeriesCapture, ...]:
    payload = _mapping(payload)
    status = payload.get("status")
    messages = tuple(_text(m) for m in _list(payload.get("message", [])))
    if status != "REQUEST_SUCCEEDED":
        if any("threshold" in m.lower() for m in messages):
            raise AdapterRateLimitError("BLS daily query threshold reached")
        raise AdapterError(AdapterErrorCode.UNAVAILABLE, "BLS request was not processed")
    series = _list(_mapping(payload.get("Results")).get("series"))
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in series:
        item = _mapping(item)
        sid = _text(item.get("seriesID"))
        if sid in by_id or sid not in requested:
            raise ProviderDataError("BLS returned an unexpected or repeated series")
        by_id[sid] = item
    if set(by_id) != set(requested):
        raise ProviderDataError("BLS did not return every requested series")
    captures = []
    for sid in sorted(by_id):
        values = []
        for raw in _list(by_id[sid].get("data")):
            values.append(_value(_mapping(raw)))
        related = tuple(m for m in messages if sid in m)
        try:
            captures.append(SeriesCapture(
                series_id=sid, values=tuple(sorted(values, key=lambda v: v.reference_period)),
                provider_messages=related,
                provenance=SourceProvenance(source="bls", source_type="public_api_v2", source_id=sid,
                                            source_timestamp=None, received_timestamp=received)))
        except ValidationError as error:
            raise ProviderDataError("BLS series payload is inconsistent") from error
    return tuple(captures)


def _value(raw: Mapping[str, Any]) -> SeriesValue:
    year, period = _text(raw.get("year")), _text(raw.get("period"))
    if not year.isdigit() or len(year) != 4 or not (len(period) == 3 and period[0] == "M" and period[1:].isdigit()
                                                    and 1 <= int(period[1:]) <= 12):
        raise ProviderDataError("only monthly BLS periods M01..M12 are release values")
    text = _text(raw.get("value"))
    footnotes = tuple(Footnote(code=f.get("code"), text=_text(f.get("text")))
                      for f in (_mapping(x) for x in _list(raw.get("footnotes", []))) if f)
    if text == "-":
        number = None
    else:
        try:
            number = Decimal(text)
        except InvalidOperation as error:
            raise ProviderDataError("BLS value is not a decimal") from error
        if not number.is_finite():
            raise ProviderDataError("BLS value must be finite")
    latest = raw.get("latest", "false")
    if latest not in ("true", "false"):
        raise ProviderDataError("BLS latest flag must be 'true' or 'false'")
    try:
        return SeriesValue(reference_period=f"{year}-{period[1:]}", raw_value=text, value=number,
                           preliminary=any(f.code == "P" for f in footnotes), footnotes=footnotes,
                           latest=latest == "true")
    except ValidationError as error:
        raise ProviderDataError("BLS value is inconsistent") from error
