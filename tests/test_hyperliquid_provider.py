import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from traid.domain import DataQualityState
from traid.exchange import AdapterError, AdapterErrorCode, AdapterRateLimitError, AdapterUnavailableError, Capability
import traid.providers.hyperliquid as hyperliquid_module
from traid.providers import HyperliquidAdapter


NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


class FixtureAdapter(HyperliquidAdapter):
    def __init__(self, payloads):
        super().__init__(clock=lambda: NOW)
        self.payloads = payloads

    def _post(self, payload, capability):
        return self.payloads[capability]


def adapter(payloads):
    value = FixtureAdapter(payloads)
    value.connect()
    return value


def test_rest_capabilities_map_to_canonical_models_and_preserve_decimal_precision():
    value = adapter({
        Capability.TRADES: [{"coin": "BTC", "side": "B", "px": "100.123456789", "sz": "0.00010", "time": 1767265200000, "tid": 7}],
        Capability.ORDER_BOOK: {"coin": "BTC", "time": 1767265200000, "levels": [[{"px": "99.1", "sz": "2.50", "n": 3}], []]},
        Capability.CANDLES: [{"t": 1767261600000, "T": 1767265200000, "s": "BTC", "i": "1h", "o": "99", "c": "100", "h": "101", "l": "98", "v": "3.25", "n": 4}],
        Capability.FUNDING: [{"coin": "BTC", "fundingRate": "0.00125", "time": 1767265200000}],
        Capability.MARKET_CONTEXT: [{"universe": [{"name": "BTC"}]}, [{"markPx": "100", "openInterest": "10"}]],
    })
    assert value.trades("BTC")[0].price == Decimal("100.123456789")
    assert value.order_book("BTC").bids[0].quantity == Decimal("2.50")
    assert value.candles("BTC")[0].volume == Decimal("3.25")
    assert value.funding("BTC").funding_rate == Decimal("0.00125")
    assert value.market_context("BTC").data_quality is DataQualityState.LIVE
    assert value.market_context("BTC").provenance[0].source_timestamp is None
    assert value.market_context("BTC").provenance[0].received_timestamp == NOW


def test_open_interest_is_explicitly_unavailable_and_never_zero_filled():
    value = HyperliquidAdapter(clock=lambda: NOW)
    assert Capability.OPEN_INTEREST in value.capabilities()
    coverage = next(item for item in value.coverage() if item.capability is Capability.OPEN_INTEREST)
    assert coverage.availability.value == "UNAVAILABLE"
    assert "unverified" in coverage.limitation
    with pytest.raises(AdapterUnavailableError) as error:
        value.open_interest("BTC")
    assert error.value.code is AdapterErrorCode.UNAVAILABLE


def test_invalid_provider_numeric_fails_closed():
    value = adapter({Capability.TRADES: [{"coin": "BTC", "side": "B", "px": "not-a-number", "sz": "1", "time": 1767265200000, "tid": 7}]})
    with pytest.raises(Exception):
        value.trades("BTC")


def test_websocket_envelopes_are_canonicalized_without_raw_payload_leakage():
    value = HyperliquidAdapter(clock=lambda: NOW)
    result = value.normalize_ws_message({"channel": "trades", "data": [{"coin": "BTC", "side": "A", "px": "100", "sz": "1", "time": 1767265200000, "tid": 8}]})
    assert result[0].symbol == "BTC"
    assert result[0].provenance.source_type == "public_websocket"


class FakeSocket:
    def __init__(self, messages=(), failure=None):
        self.messages = list(messages)
        self.failure = failure
        self.sent = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def send(self, message):
        self.sent.append(message)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.failure is not None:
            failure, self.failure = self.failure, None
            raise failure
        if not self.messages:
            raise StopAsyncIteration
        message = self.messages.pop(0)
        return message if isinstance(message, str) else json.dumps(message)


def test_stream_reconnects_and_resubscribes_after_unexpected_disconnect():
    first = FakeSocket(failure=ConnectionError("dropped"))
    second = FakeSocket(messages=[{"channel": "trades", "data": [{"coin": "BTC", "side": "B", "px": "100", "sz": "1", "time": 1767265200000, "tid": 9}]}])
    sockets = [first, second]

    def connect(*_args, **_kwargs):
        return sockets.pop(0)

    value = HyperliquidAdapter(clock=lambda: NOW, websocket_connect=connect, reconnect_backoff=0)
    result = asyncio.run(consume_one(value.stream(({"type": "trades", "coin": "BTC"},))))
    assert result[0].symbol == "BTC"
    assert len(sockets) == 0
    assert len(first.sent) == 1
    assert len(second.sent) == 1
    assert first.sent[0] == second.sent[0]


async def consume_one(stream):
    async for item in stream:
        if not isinstance(item, dict):
            return item
    raise AssertionError("stream ended before canonical data")


def test_stream_retry_exhaustion_is_normalized_and_bounded():
    calls = 0

    def connect(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise ConnectionError("unavailable")

    value = HyperliquidAdapter(clock=lambda: NOW, websocket_connect=connect, reconnect_backoff=0)
    with pytest.raises(AdapterError) as error:
        asyncio.run(consume_one(value.stream(({"type": "trades", "coin": "BTC"},))))
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE
    assert calls == 3


def test_stream_malformed_message_fails_closed_without_reconnect():
    sockets = [FakeSocket(messages=["not-json"]), FakeSocket()]

    def connect(*_args, **_kwargs):
        return sockets.pop(0)

    value = HyperliquidAdapter(clock=lambda: NOW, websocket_connect=connect)
    with pytest.raises(AdapterError) as error:
        asyncio.run(consume_one(value.stream(({"type": "trades", "coin": "BTC"},))))
    assert error.value.code is AdapterErrorCode.PROVIDER_DATA
    assert len(sockets) == 1


def test_subscription_ack_is_not_market_data():
    value = HyperliquidAdapter(clock=lambda: NOW)
    ack = value.normalize_ws_message({"channel": "subscriptionResponse", "data": {"method": "subscribe"}})
    assert isinstance(ack, dict)


def test_rest_rate_limit_is_normalized_without_retry(monkeypatch):
    def rate_limited(*_args, **_kwargs):
        from urllib.error import HTTPError
        raise HTTPError("https://api.hyperliquid.xyz/info", 429, "rate", {}, None)

    monkeypatch.setattr(hyperliquid_module, "urlopen", rate_limited)
    value = HyperliquidAdapter(clock=lambda: NOW)
    value.connect()
    with pytest.raises(AdapterRateLimitError) as error:
        value.trades("BTC")
    assert error.value.code is AdapterErrorCode.RATE_LIMITED


def test_rest_timeout_and_invalid_json_fail_closed(monkeypatch):
    from urllib.error import URLError

    monkeypatch.setattr(hyperliquid_module, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("timeout")))
    value = HyperliquidAdapter(clock=lambda: NOW)
    value.connect()
    with pytest.raises(AdapterError) as error:
        value.trades("BTC")
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return b"not-json"

    monkeypatch.setattr(hyperliquid_module, "urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(AdapterError) as error:
        value.trades("BTC")
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE


@pytest.mark.parametrize(
    "record",
    [
        {"coin": "BTC", "side": "B", "px": "100", "sz": "1", "tid": 1},
        {"coin": "BTC", "side": "B", "px": "100", "sz": "1", "time": "bad", "tid": 1},
    ],
)
def test_missing_or_malformed_trade_fields_fail_closed(record):
    value = adapter({Capability.TRADES: [record]})
    with pytest.raises(AdapterError) as error:
        value.trades("BTC")
    assert error.value.code in {AdapterErrorCode.PROVIDER_FAILURE, AdapterErrorCode.PROVIDER_DATA}


def test_canonical_validation_and_unsupported_websocket_shape_fail_closed():
    value = adapter({Capability.CANDLES: [{"t": 1767261600000, "T": 1767265200000, "s": "BTC", "i": "1h", "o": "99", "c": "100", "h": "98", "l": "97", "v": "1", "n": 1}]})
    with pytest.raises(AdapterError) as error:
        value.candles("BTC")
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE
    with pytest.raises(AdapterError) as error:
        value.normalize_ws_message({"channel": "unknown", "data": {}})
    assert error.value.code is AdapterErrorCode.PROVIDER_DATA


def test_normal_stream_end_does_not_reconnect():
    calls = 0

    def connect(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeSocket()

    async def drain():
        async for _ in HyperliquidAdapter(websocket_connect=connect).stream(({"type": "trades", "coin": "BTC"},)):
            pass

    asyncio.run(drain())
    assert calls == 1


def test_cancellation_stops_reconnect_backoff():
    def connect(*_args, **_kwargs):
        raise ConnectionError("unavailable")

    async def cancel():
        task = asyncio.create_task(consume_one(HyperliquidAdapter(websocket_connect=connect).stream(({"type": "trades", "coin": "BTC"},))))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())


def _record(**changes):
    # Shape observed from the live info and websocket APIs (extra fields are ignored).
    record = {"coin": "BTC", "side": "B", "px": "100", "sz": "1", "time": 1767265200000, "tid": 7,
              "hash": "0x" + "0" * 64, "users": ["0xaaa", "0xbbb"]}
    record.update(changes)
    return {key: value for key, value in record.items() if value is not None}


def test_trade_side_maps_buy_and_sell_aggressor_on_http_and_websocket():
    from traid.domain import AggressorSide
    rest = adapter({Capability.TRADES: [_record(side="B", tid=1), _record(side="A", tid=2)]}).trades("BTC")
    assert [t.side for t in rest] == [AggressorSide.BUY, AggressorSide.SELL]
    value = HyperliquidAdapter(clock=lambda: NOW)
    ws = value.normalize_ws_message({"channel": "trades", "data": [_record(side="B", tid=1), _record(side="A", tid=2)]})
    assert [t.side for t in ws] == [AggressorSide.BUY, AggressorSide.SELL]
    assert [t.provenance.source_id for t in ws] == ["1", "2"]
    assert ws[0].provenance.source_timestamp == ws[0].timestamp == rest[0].timestamp


@pytest.mark.parametrize("side", [None, "", "b", "a", "BUY", "SELL", "X", "BA", 1, True, ["B"]])
def test_invalid_or_missing_trade_side_is_rejected_on_both_paths(side):
    record = _record(side=side)
    if side is None:
        assert "side" not in record
    with pytest.raises(AdapterError) as error:
        adapter({Capability.TRADES: [record]}).trades("BTC")
    assert error.value.code in {AdapterErrorCode.PROVIDER_FAILURE, AdapterErrorCode.PROVIDER_DATA}
    with pytest.raises(AdapterError) as error:
        HyperliquidAdapter(clock=lambda: NOW).normalize_ws_message({"channel": "trades", "data": [record]})
    assert error.value.code in {AdapterErrorCode.PROVIDER_FAILURE, AdapterErrorCode.PROVIDER_DATA}


def test_one_malformed_side_rejects_the_whole_trade_batch():
    with pytest.raises(AdapterError):
        adapter({Capability.TRADES: [_record(tid=1), _record(side="?", tid=2)]}).trades("BTC")


@pytest.mark.parametrize("tid", [None, True, False, 1.5, 7.0, -1, "7", "", [7], {"a": 7}, 2**50, 10**30, float("nan")])
def test_invalid_trade_id_is_rejected_before_canonicalization_on_both_paths(tid):
    record = _record(tid=tid)
    if tid is None:
        assert "tid" not in record
    with pytest.raises(AdapterError) as error:
        adapter({Capability.TRADES: [record]}).trades("BTC")
    assert error.value.code in {AdapterErrorCode.PROVIDER_FAILURE, AdapterErrorCode.PROVIDER_DATA}
    with pytest.raises(AdapterError) as error:
        HyperliquidAdapter(clock=lambda: NOW).normalize_ws_message({"channel": "trades", "data": [record]})
    assert error.value.code in {AdapterErrorCode.PROVIDER_FAILURE, AdapterErrorCode.PROVIDER_DATA}


@pytest.mark.parametrize("tid", [0, 7, 891572595353560, 2**50 - 1])
def test_valid_trade_ids_become_exact_decimal_source_ids_on_both_paths(tid):
    rest = adapter({Capability.TRADES: [_record(tid=tid)]}).trades("BTC")
    ws = HyperliquidAdapter(clock=lambda: NOW).normalize_ws_message({"channel": "trades", "data": [_record(tid=tid)]})
    assert rest[0].provenance.source_id == ws[0].provenance.source_id == str(tid)


def _funding_record(rate):
    return {"coin": "BTC", "fundingRate": rate, "premium": "0.0", "time": 1767265200035}


@pytest.mark.parametrize("rate", ["0.0000125", "0", "0.0", "-0.0000125", "-0.00022196", "-0.04"])
def test_funding_rate_is_signed_positive_zero_and_negative_are_preserved(rate):
    result = adapter({Capability.FUNDING: [_funding_record(rate)]}).funding("BTC")
    assert result.funding_rate == Decimal(rate) and str(result.funding_rate) == str(Decimal(rate))


@pytest.mark.parametrize("rate", ["NaN", "Infinity", "-Infinity", "abc", "", None, True, 1.5, [], {}])
def test_funding_rate_that_is_not_a_finite_decimal_is_rejected(rate):
    with pytest.raises(AdapterError):
        adapter({Capability.FUNDING: [_funding_record(rate)]}).funding("BTC")


def test_signed_validation_is_scoped_to_funding_other_fields_stay_nonnegative():
    negative_size = _record(sz="-1")
    with pytest.raises(AdapterError):
        adapter({Capability.TRADES: [negative_size]}).trades("BTC")
    with pytest.raises(AdapterError):
        HyperliquidAdapter(clock=lambda: NOW).normalize_ws_message({"channel": "trades", "data": [negative_size]})
    candle = {"t": 1767261600000, "T": 1767265199999, "s": "BTC", "i": "1h", "o": "99", "c": "100", "h": "101", "l": "98", "v": "-3", "n": 4}
    with pytest.raises(AdapterError):
        adapter({Capability.CANDLES: [candle]}).candles("BTC")
    book = {"coin": "BTC", "time": 1767265200000, "levels": [[{"px": "99", "sz": "-2", "n": 1}], []]}
    with pytest.raises(AdapterError):
        adapter({Capability.ORDER_BOOK: book}).order_book("BTC")
