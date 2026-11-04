"""U1: the REST funding selection must not depend on response order (controlled fixtures only).

The provider contract recorded in this repository does not guarantee the order of ``fundingHistory``,
so selection is by observation time. Conflicting observations never resolve to a winner.
"""
from datetime import datetime, timezone
from decimal import Decimal
from itertools import permutations

import pytest

from traid.derivatives import DerivativesConfig, analyze_derivatives
from traid.exchange import (
    AdapterError, AdapterErrorCode, Capability, CapabilityAvailability, CapabilityCoverage,
)
from traid.providers import HyperliquidAdapter
from traid.quality import ContinuityStatus, RecoveryStatus
from traid.regime import FundingPolarity, MarketStateRules, classify_market_state

NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
HOUR_MS = 3_600_000
H11 = 1767265200000  # 2026-01-01T11:00:00Z in milliseconds
H10, H09 = H11 - HOUR_MS, H11 - 2 * HOUR_MS


class FixtureAdapter(HyperliquidAdapter):
    def __init__(self, payload):
        super().__init__(clock=lambda: NOW)
        self.payload = payload

    def _post(self, payload, capability):
        return self.payload


def rec(time_ms, rate, coin="BTC"):
    return {"coin": coin, "fundingRate": rate, "premium": "0.0", "time": time_ms}


def funding(records):
    adapter = FixtureAdapter(records)
    adapter.connect()
    return adapter.funding("BTC")


def rejected(records, code=AdapterErrorCode.PROVIDER_DATA):
    with pytest.raises(AdapterError) as error:
        funding(records)
    assert error.value.code is code


T9, T10, T11 = rec(H09 + 35, "0.00001"), rec(H10 + 35, "-0.00002"), rec(H11 + 35, "0.00003")


# ----------------------------------------------------------------- A. non-chronological responses
@pytest.mark.parametrize("order", list(permutations((T9, T10, T11))))
def test_the_latest_settlement_is_selected_by_time_not_array_position(order):
    result = funding(list(order))
    assert result.timestamp == datetime(2026, 1, 1, 11, 0, 0, 35000, tzinfo=timezone.utc)
    assert result.funding_rate == Decimal("0.00003")


def test_the_selected_snapshot_keeps_its_canonical_contract():
    result = funding([T11, T9])
    assert (result.symbol, result.provenance.source, result.provenance.source_type) == ("BTC", "hyperliquid", "public_info")
    assert result.provenance.source_id == "fundingHistory"
    assert result.provenance.source_timestamp == result.timestamp and result.provenance.received_timestamp == NOW


@pytest.mark.parametrize("rate, sign", [("0.00003", 1), ("-0.00003", -1), ("0", 0)])
def test_signed_rates_are_preserved_when_the_latest_record_is_not_last(rate, sign):
    result = funding([rec(H11 + 35, rate), T9, T10])
    assert result.funding_rate == Decimal(rate) and (result.funding_rate > 0) - (result.funding_rate < 0) == sign


# ----------------------------------------------------------------------------- B. exact duplicates
@pytest.mark.parametrize("order", list(permutations((T9, T11, dict(T11)))))
def test_exact_duplicates_select_the_same_observation_in_any_order(order):
    assert funding(list(order)).funding_rate == Decimal("0.00003")


def test_value_equal_duplicates_with_different_spelling_are_order_independent():
    one, two = rec(H11 + 35, "0.00003"), rec(H11 + 35, "0.000030")
    assert str(funding([one, two]).funding_rate) == str(funding([two, one]).funding_rate)


# ------------------------------------------------------------------------ C. same-timestamp conflict
@pytest.mark.parametrize("order", [0, 1])
def test_conflicting_rates_for_one_timestamp_are_rejected_in_either_order(order):
    pair = [rec(H11 + 35, "0.00003"), rec(H11 + 35, "-0.00003")]
    rejected(pair if order == 0 else pair[::-1])


def test_a_conflict_is_rejected_even_when_older_records_surround_it():
    rejected([T9, rec(H11 + 35, "0.00003"), T10, rec(H11 + 35, "-0.00003")])


# --------------------------------------------------------------------------------- D. same hour
@pytest.mark.parametrize("second", [rec(H11 + 1035, "-0.00003"), rec(H11 + 1035, "0.00003")])
@pytest.mark.parametrize("order", [0, 1])
def test_different_observations_in_the_selected_hour_are_rejected_in_either_order(second, order):
    pair = [rec(H11 + 35, "0.00003"), second]
    rejected(pair if order == 0 else pair[::-1])


def test_a_conflict_in_an_older_hour_does_not_affect_the_selected_latest_hour():
    older = [rec(H09 + 35, "0.00001"), rec(H09 + 35, "-0.00001")]
    for order in (older + [T11], [T11] + older):
        assert funding(order).funding_rate == Decimal("0.00003")


# ---------------------------------------------------------------------- E. empty and malformed input
def test_empty_response_is_unavailable_not_a_value():
    rejected([], AdapterErrorCode.UNAVAILABLE)


@pytest.mark.parametrize("payload", [{}, None, "x", 1])
def test_a_response_that_is_not_a_list_is_rejected(payload):
    rejected(payload)


BAD = [
    "not a mapping", None, 7,
    {"coin": "BTC", "fundingRate": "0.00001"},                       # no time
    {"coin": "BTC", "time": H10 + 35},                               # no rate
    {"coin": "BTC", "fundingRate": "abc", "time": H10 + 35},
    {"coin": "BTC", "fundingRate": "NaN", "time": H10 + 35},
    {"coin": "BTC", "fundingRate": 0.1, "time": H10 + 35},           # float rate
    {"coin": "BTC", "fundingRate": "0.00001", "time": "bad"},
    {"coin": "BTC", "fundingRate": "0.00001", "time": True},
    {"coin": "ETH", "fundingRate": "0.00001", "time": H10 + 35},     # another instrument
    {"fundingRate": "0.00001", "time": H10 + 35},                    # no instrument
]


@pytest.mark.parametrize("bad", BAD, ids=range(len(BAD)))
@pytest.mark.parametrize("where", ["first", "middle", "last"])
def test_one_malformed_record_anywhere_rejects_the_whole_response(bad, where):
    records = {"first": [bad, T10, T11], "middle": [T10, bad, T11], "last": [T10, T11, bad]}[where]
    rejected(records)


# ------------------------------------------------------------------------------ F. future-dated
@pytest.mark.parametrize("order", [0, 1])
def test_a_future_dated_observation_is_rejected_not_selected(order):
    future = rec(int(NOW.timestamp() * 1000) + 1, "-0.00009")
    rejected([T11, future] if order == 0 else [future, T11])


def test_an_observation_at_the_receipt_instant_is_not_future():
    now_ms = int(NOW.timestamp() * 1000)
    assert funding([T10, rec(now_ms, "0.00004")]).funding_rate == Decimal("0.00004")


# ----------------------------------------------------------------------- C09 and C10 compatibility
def polarity(records):
    snapshot = funding(records)
    config = DerivativesConfig(symbol="BTC", base_asset="BTC", quote_currency="USD", atr_period=3,
                               volatility_period=2, momentum_lookbacks=(1,), funding_lookback_hours=1)
    supported = lambda cap: CapabilityCoverage(cap, CapabilityAvailability.SUPPORTED)  # noqa: E731
    report = analyze_derivatives(
        (), (snapshot,), config=config, candle_coverage=supported(Capability.CANDLES),
        funding_coverage=supported(Capability.FUNDING), evaluation_time=NOW,
        continuity=ContinuityStatus.PROVEN, recovery=RecoveryStatus.NONE)
    state = classify_market_state(evaluation_time=NOW, symbol="BTC", rules=MarketStateRules(rules_version="u1-test"),
                                  derivatives=report)
    return report, state.funding


@pytest.mark.parametrize("order", list(permutations((T9, T10, T11))))
def test_downstream_polarity_does_not_depend_on_response_order(order):
    report, result = polarity(list(order))
    assert report.funding.trusted_for_current_use and report.funding.latest_rate.value == Decimal("0.00003")
    assert result.state == FundingPolarity.LONGS_PAY_SHORTS and result.inputs_trusted


def test_a_negative_latest_rate_gives_the_opposite_polarity_regardless_of_order():
    latest = rec(H11 + 35, "-0.00003")
    for order in ([T9, latest], [latest, T9]):
        assert polarity(order)[1].state == FundingPolarity.SHORTS_PAY_LONGS


def test_conflicting_observations_never_reach_c09_or_c10_as_a_trusted_polarity():
    for pair in ([rec(H11 + 35, "0.00003"), rec(H11 + 35, "-0.00003")],
                 [rec(H11 + 35, "-0.00003"), rec(H11 + 35, "0.00003")]):
        with pytest.raises(AdapterError):
            polarity(pair)


@pytest.mark.parametrize("when", [10**30, -10**30, float("inf"), float("nan")])
@pytest.mark.parametrize("where", [0, 1])
def test_an_out_of_range_time_rejects_the_response_with_the_existing_error_mapping(when, where):
    records = [T11, rec(when, "0.1")]
    rejected(records if where == 0 else records[::-1], AdapterErrorCode.PROVIDER_FAILURE)
