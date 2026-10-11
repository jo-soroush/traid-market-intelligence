"""C06 bounded provider requests, failures, and C04 differential mapping."""

from datetime import datetime, timedelta, timezone
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError

import pytest

from traid.exchange import ProviderDataError
from traid.providers.hyperliquid import HyperliquidAdapter
from traid.providers.hyperliquid_history import (
    HistoryProviderError,
    HistoryRateLimitError,
    HyperliquidHistoryProvider,
    _json_response,
)


BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)
NOW = BASE + timedelta(days=2)


def candle_payload(hour=0, *, interval="1h", close="2.00"):
    start = int((BASE + timedelta(hours=hour)).timestamp() * 1000)
    return {"t": start, "T": start + 3_599_999, "s": "BTC", "i": interval, "o": "1.00", "h": "2.00", "l": "1.00", "c": close, "v": "3.000"}


def funding_payload(hour=0, *, rate="-0.000125"):
    stamp = int((BASE + timedelta(hours=hour)).timestamp() * 1000) + 51
    return {"coin": "BTC", "time": stamp, "fundingRate": rate, "premium": "0.0"}


def provider(post):
    return HyperliquidHistoryProvider(clock=lambda: NOW, post=post)


def test_bounded_sequential_requests_and_closed_window():
    calls = []
    def post(payload):
        calls.append(payload)
        return [candle_payload()] if payload["type"] == "candleSnapshot" else [funding_payload()]
    result = provider(post).fetch(BASE, BASE + timedelta(hours=1))
    assert [call["type"] for call in calls] == ["candleSnapshot", "fundingHistory"]
    assert result.candle_pages == result.funding_pages == 1
    assert all("endTime" in (call.get("req") or call) for call in calls)
    assert result.candles[0].symbol == result.funding[0].symbol == "BTC"
    assert str(result.funding[0].funding_rate) == "-0.000125"


def test_page_window_is_split_and_boundary_is_not_repeated():
    calls = []
    def post(payload):
        calls.append(payload)
        if payload["type"] == "candleSnapshot":
            return [candle_payload(0)] if len(calls) == 1 else [candle_payload(24)]
        return []
    result = provider(post).fetch(BASE, BASE + timedelta(hours=25))
    assert result.candle_pages == 2
    assert result.funding_pages == 2
    assert {item.start_timestamp for item in result.candles} == {BASE, BASE + timedelta(hours=24)}


def test_full_funding_page_advances_cursor_without_losing_boundary():
    calls = []
    def post(payload):
        calls.append(payload)
        if payload["type"] == "candleSnapshot":
            return []
        if len([call for call in calls if call["type"] == "fundingHistory"]) == 1:
            first = int(BASE.timestamp() * 1000) + 51
            return [{"coin": "BTC", "time": first + i * 1000, "fundingRate": "0.01"} for i in range(500)]
        return [{"coin": "BTC", "time": int(BASE.timestamp() * 1000) + 500_051, "fundingRate": "0.01"}]
    result = provider(post).fetch(BASE, BASE + timedelta(hours=1))
    assert result.funding_pages == 2
    assert len(result.funding) == 501
    funding_calls = [call for call in calls if call["type"] == "fundingHistory"]
    assert funding_calls[1]["startTime"] == funding_calls[0]["startTime"] + 499_051


def test_full_page_at_unprovable_boundary_fails_closed():
    last = int((BASE + timedelta(hours=1)).timestamp() * 1000) - 1
    def post(payload):
        if payload["type"] == "candleSnapshot":
            return []
        return [{"coin": "BTC", "time": last - i, "fundingRate": "0.01"} for i in range(500)]
    with pytest.raises(HistoryProviderError, match="unprovable boundary"):
        provider(post).fetch(BASE, BASE + timedelta(hours=1))


def test_429_is_terminal_without_retry():
    attempts = 0
    def post(_):
        nonlocal attempts
        attempts += 1
        raise HTTPError("https://api.hyperliquid.xyz/info", 429, "rate limited", {}, None)
    with pytest.raises(HistoryRateLimitError, match="429"):
        provider(post).fetch(BASE, BASE + timedelta(hours=1))
    assert attempts == 1


def test_transient_connection_loss_has_at_most_two_retries():
    attempts = 0
    def post(payload):
        nonlocal attempts
        if payload["type"] == "candleSnapshot":
            attempts += 1
            if attempts <= 2:
                raise URLError("connection lost")
        return []
    assert provider(post).fetch(BASE, BASE + timedelta(hours=1)).candle_pages == 1
    assert attempts == 3
    exhausted_attempts = 0
    def always_drop(_):
        nonlocal exhausted_attempts
        exhausted_attempts += 1
        raise URLError("connection lost")
    with pytest.raises(HistoryProviderError, match="two retries"):
        provider(always_drop).fetch(BASE, BASE + timedelta(hours=1))
    assert exhausted_attempts == 3


@pytest.mark.parametrize("result", [{"error": "bad"}, [None], [candle_payload(close="NaN")], [dict(candle_payload(), openInterest="1")], [candle_payload(interval="1m")]])
def test_invalid_source_shapes_values_or_oi_fail_closed(result):
    with pytest.raises(HistoryProviderError):
        provider(lambda _: result).fetch(BASE, BASE + timedelta(hours=1))


def test_truncated_or_duplicate_key_json_rejected():
    with pytest.raises(HistoryProviderError, match="truncated"):
        _json_response(b'[{"t": 1}')
    with pytest.raises(HistoryProviderError, match="duplicate"):
        _json_response(b'{"a":1,"a":2}')


def test_incomplete_read_fails_without_publishing():
    with pytest.raises(HistoryProviderError, match="truncated"):
        provider(lambda _: (_ for _ in ()).throw(IncompleteRead(b"{", 20))).fetch(BASE, BASE + timedelta(hours=1))


def test_c04_differential_candle_mapping_for_equivalent_payload(monkeypatch):
    raw = candle_payload()
    reference = HyperliquidAdapter(clock=lambda: NOW)
    monkeypatch.setattr(reference, "_post", lambda *_: [raw])
    old = reference._candles("BTC")[0]
    new = provider(lambda payload: [raw] if payload["type"] == "candleSnapshot" else []).fetch(BASE, BASE + timedelta(hours=1)).candles[0]
    assert new == old


def test_c04_differential_positive_funding_mapping(monkeypatch):
    raw = funding_payload(rate="0.000125")
    reference = HyperliquidAdapter(clock=lambda: NOW)
    monkeypatch.setattr(reference, "_post", lambda *_: [raw])
    old = reference._funding("BTC")
    new = provider(lambda payload: [raw] if payload["type"] == "fundingHistory" else []).fetch(BASE, BASE + timedelta(hours=1)).funding[0]
    assert new == old


def test_negative_funding_is_preserved_in_c06_but_c04_differential_does_not_apply(monkeypatch):
    raw = funding_payload(rate="-0.000125")
    reference = HyperliquidAdapter(clock=lambda: NOW)
    monkeypatch.setattr(reference, "_post", lambda *_: [raw])
    with pytest.raises(ProviderDataError, match="outside the canonical domain"):
        reference._funding("BTC")
    historical = provider(lambda payload: [raw] if payload["type"] == "fundingHistory" else []).fetch(BASE, BASE + timedelta(hours=1))
    assert str(historical.funding[0].funding_rate) == "-0.000125"


def test_historical_layer_has_no_provider_imports_or_new_dependency():
    from pathlib import Path
    package = Path(__file__).resolve().parents[1] / "src/traid/historical"
    assert all("traid.providers" not in path.read_text() for path in package.glob("*.py"))
    project = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert "hypothesis" not in project and "mutmut" not in project
