from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import inspect
import itertools
import math
import random
import statistics

import pytest
from pydantic import ValidationError

import traid.derivatives.analytics as module
from traid.derivatives import DerivativesConfig, DerivativesReport, analyze_derivatives
from traid.domain import Candle, FundingSnapshot, SourceProvenance
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.historical.models import CANDLE_OFFSET_SECONDS
from traid.providers import HyperliquidAdapter
from traid.quality import ContinuityStatus, RecoveryStatus, default_quality_policy

D = Decimal
HOUR = timedelta(hours=1)
MS = timedelta(milliseconds=1)
NOW = datetime(2026, 10, 15, 12, 5, tzinfo=timezone.utc)
LAST = datetime(2026, 10, 15, 11, tzinfo=timezone.utc)      # newest closed candle at NOW (closed 12:00)
FUND_LAST = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)  # newest settled funding hour at NOW
SUPPORTED = {c: CapabilityCoverage(c, CapabilityAvailability.SUPPORTED) for c in (Capability.CANDLES, Capability.FUNDING)}


def candle(start, o, h, l, c, v, lag=5, source="fixture", source_type="public_info", end=None, source_id=None, symbol="BTC"):
    """lag: seconds after the candle's close at which it was received."""
    end = end or start + HOUR - MS
    return Candle(
        symbol=symbol, start_timestamp=start, end_timestamp=end, open=D(o), high=D(h), low=D(l), close=D(c), volume=D(v),
        provenance=SourceProvenance(source=source, source_type=source_type, source_id=source_id or str(int(start.timestamp() * 1000)),
                                    source_timestamp=start, received_timestamp=start + HOUR + timedelta(seconds=lag)))


def candles(specs, last=LAST, **kw):
    n = len(specs)
    return tuple(candle(last - (n - 1 - i) * HOUR, *spec, **kw) for i, spec in enumerate(specs))


def closes(values, last=LAST, **kw):
    return candles([(c, c, c, c, 1) for c in values], last, **kw)


def fund(hour, rate, offset=0.035, lag=2, source="fixture", source_type="public_info", symbol="BTC"):
    when = hour + timedelta(seconds=offset)
    return FundingSnapshot(symbol=symbol, funding_rate=D(rate), timestamp=when, provenance=SourceProvenance(
        source=source, source_type=source_type, source_id="fundingHistory", source_timestamp=when,
        received_timestamp=when + timedelta(seconds=lag)))


def rates(values, last=FUND_LAST, **kw):
    n = len(values)
    return tuple(fund(last - (n - 1 - i) * HOUR, r, **kw) for i, r in enumerate(values))


def config(**kw):
    base = dict(symbol="BTC", base_asset="BTC", quote_currency="USD", atr_period=3, volatility_period=2,
                momentum_lookbacks=(1, 2), funding_lookback_hours=4)
    base.update(kw)
    return DerivativesConfig(**base)


def run(cs=(), fs=(), c=None, **kw):
    args = dict(config=c or config(), candle_coverage=SUPPORTED[Capability.CANDLES], funding_coverage=SUPPORTED[Capability.FUNDING],
                evaluation_time=NOW, continuity=ContinuityStatus.PROVEN, recovery=RecoveryStatus.NONE)
    args.update(kw)
    return analyze_derivatives(tuple(cs), tuple(fs), **args)


# (open, high, low, close, volume); true ranges by hand are annotated.
ATR_SERIES = [(9, 10, 8, 9, 1),     # c0
              (9, 11, 9, 10, 1),    # TR1 = max(2, |11-9|=2, |9-9|=0) = 2
              (10, 13, 10, 12, 1),  # TR2 = max(3, |13-10|=3, |10-10|=0) = 3
              (12, 12, 9, 10, 1),   # TR3 = max(3, |12-12|=0, |9-12|=3) = 3   (gap down from previous close)
              (11, 14, 11, 13, 1)]  # TR4 = max(3, |14-10|=4, |11-10|=1) = 4  (gap up from previous close)


def frac(num, den):
    with localcontext() as ctx:
        ctx.prec = 50
        return D(num) / D(den)


# ---------------------------------------------------------------------------------- ATR
@pytest.mark.parametrize("period, expected", [(2, frac(7, 2)), (3, frac(10, 3)), (4, D(3))])
def test_atr_is_the_simple_mean_of_the_last_true_ranges_with_hand_values(period, expected):
    r = run(candles(ATR_SERIES), c=config(atr_period=period))
    assert r.candles.atr.value == expected and r.candles.atr.unit == "USD"
    assert r.candles.trusted_for_current_use


def test_atr_true_range_uses_the_previous_close_not_only_the_candle_range():
    series = [(10, 10, 10, 10, 1), (20, 21, 19, 20, 1)]   # same-candle range 2, gap range from prev close 11
    assert run(candles(series), c=config(atr_period=1)).candles.atr.value == D(11)


# ------------------------------------------------------------------------ realized volatility
def test_realized_volatility_is_the_sample_stdev_of_log_returns_not_annualized():
    r = run(closes([100, 110, 100]), c=config(volatility_period=2))
    assert float(r.candles.realized_volatility.value) == pytest.approx(math.sqrt(2) * math.log(1.1), rel=1e-12)
    prices = [100, 101, 103, 102, 105]
    expected = statistics.stdev(math.log(b / a) for a, b in zip(prices, prices[1:]))
    r = run(closes(prices), c=config(volatility_period=4))
    assert float(r.candles.realized_volatility.value) == pytest.approx(expected, rel=1e-12)
    assert "not annualized" in r.candles.realized_volatility.unit


def test_realized_volatility_of_a_constant_series_is_exactly_zero_not_unavailable():
    value = run(closes([100, 100, 100]), c=config(volatility_period=2)).candles.realized_volatility.value
    assert value == D(0)


def test_realized_volatility_uses_only_the_last_n_returns():
    long = closes([50, 90, 100, 110, 100])
    short = closes([100, 110, 100])
    c = config(volatility_period=2)
    assert run(long, c=c).candles.realized_volatility.value == run(short, c=c).candles.realized_volatility.value


# ----------------------------------------------------------------------------------- VWAP
def session_config(start, **kw):
    return config(session_start=start, **kw)


def test_session_vwap_is_the_volume_weighted_hlc3_candle_approximation():
    # typical prices (h+l+c)/3: 11, 13, 12 with volumes 2, 3, 5 -> (22 + 39 + 60) / 10 = 12.1
    series = [(11, 12, 10, 11, 2), (13, 14, 12, 13, 3), (12, 13, 11, 12, 5)]
    r = run(candles(series), c=session_config(LAST - 2 * HOUR))
    assert r.candles.vwap.value == D("12.1") and r.candles.vwap_session_volume.value == D(10)
    assert r.candles.vwap.unit == "USD" and r.candles.vwap_session_volume.unit == "BTC"
    assert "VWAP_IS_CANDLE_HLC3_APPROXIMATION_NOT_TRADE_VWAP" in r.limitations


def test_vwap_uses_the_typical_price_not_the_close():
    series = [(10, 15, 9, 9, 4), (12, 13, 11, 12, 6)]   # hlc3 = 11 and 12; closes 9 and 12
    r = run(candles(series), c=session_config(LAST - HOUR))
    assert r.candles.vwap.value == D("11.6") != D("10.8")   # (44 + 72) / 10, not (36 + 72) / 10


def test_zero_volume_candles_do_not_move_vwap_and_all_zero_volume_is_unavailable():
    series = [(11, 12, 10, 11, 2), (99, 99, 99, 99, 0), (12, 13, 11, 12, 2)]
    r = run(candles(series), c=session_config(LAST - 2 * HOUR))
    assert r.candles.vwap.value == D("11.5")   # (22 + 24) / 4
    zero = run(candles([(11, 12, 10, 11, 0), (12, 13, 11, 12, 0)]), c=session_config(LAST - HOUR))
    assert zero.candles.vwap.value is None and zero.candles.vwap.reason == "ZERO_SESSION_VOLUME"
    assert zero.candles.vwap_session_volume.value == D(0)


def test_session_must_start_on_a_closed_candle_without_gaps():
    series = [(11, 12, 10, 11, 2), (13, 14, 12, 13, 3), (12, 13, 11, 12, 5)]
    early = run(candles(series), c=session_config(LAST - 5 * HOUR))
    assert early.candles.vwap.reason == "SESSION_START_NOT_COVERED" and "CANDLE_GAP_DETECTED" in early.candles.reasons
    r = run(candles(series)[1:], c=session_config(LAST - 2 * HOUR))
    assert r.candles.vwap.reason == "SESSION_START_NOT_COVERED"   # the session's first hour is absent
    nothing = run(candles(series), c=session_config(LAST + HOUR))
    assert nothing.candles.vwap.reason == "SESSION_HAS_NO_CLOSED_CANDLES"


def test_session_gap_in_the_middle_is_reported_as_a_gap():
    present = candles([(11, 12, 10, 11, 2), (12, 13, 11, 12, 5)], LAST)           # 10:00 and 11:00
    first = candles([(13, 14, 12, 13, 3)], LAST - 3 * HOUR)                         # 08:00
    r = run(first + present, c=session_config(LAST - 3 * HOUR))
    assert r.candles.vwap.reason == "GAP_IN_SESSION" and "CANDLE_GAP_DETECTED" in r.candles.reasons
    assert not r.candles.trusted_for_current_use


def test_session_not_configured_is_explicit_and_not_a_quality_failure():
    r = run(candles(ATR_SERIES))
    assert r.candles.vwap.reason == "SESSION_NOT_CONFIGURED" and r.candles.trusted_for_current_use


# ------------------------------------------------------------------------------ momentum
@pytest.mark.parametrize("prices, k, expected", [
    ([100, 110], 1, D("0.1")), ([100, 90], 1, D("-0.1")), ([100, 100], 1, D(0)),
    ([100, 110, 121], 2, D("0.21")), ([100, 150, 90], 2, D("-0.1")),
])
def test_momentum_is_the_signed_simple_return_over_the_lookback(prices, k, expected):
    metric = next(m for m in run(closes(prices), c=config(momentum_lookbacks=(k,))).candles.momentum if m.lookback_bars == k)
    assert metric.simple_return.value == expected and metric.simple_return.unit == "fraction"


def test_zero_momentum_is_a_value_while_missing_history_is_a_warm_up_state():
    r = run(closes([100, 100]), c=config(momentum_lookbacks=(1, 5)))
    one, five = r.candles.momentum
    assert one.simple_return.value == D(0) and one.simple_return.reason is None
    assert five.simple_return.value is None and five.simple_return.reason == "WARMING_UP_NEED_6_HAVE_2"


# ------------------------------------------------------------------------------- warm-up
def test_warm_up_is_explicit_and_never_zero_filled():
    r = run(candles(ATR_SERIES[:3]), c=config(atr_period=3, volatility_period=3))
    assert r.candles.atr.value is None and r.candles.atr.reason == "WARMING_UP_NEED_4_HAVE_3"
    assert r.candles.realized_volatility.reason == "WARMING_UP_NEED_4_HAVE_3"
    assert r.candles.trusted_for_current_use and r.candles.reasons == ()   # warm-up is not a quality failure


def test_no_candles_or_funding_is_unavailable_not_zero():
    r = run()
    assert r.candles.atr.reason == "NO_CLOSED_CANDLES" and r.candles.reasons == ("NO_CLOSED_CANDLES",)
    assert r.funding.latest_rate.reason == "NO_FUNDING_OBSERVATIONS" and r.funding.provenance is None
    assert not r.candles.trusted_for_current_use and not r.funding.trusted_for_current_use


# ------------------------------------------------------------------------------- funding
def test_funding_preserves_sign_hourly_unit_and_sums_without_annualizing():
    values = ["0.0000125", "-0.00002", "0.0001", "-0.0000125"]
    r = run(fs=rates(values))
    assert r.funding.latest_rate.value == D("-0.0000125")
    assert r.funding.cumulative_funding.value == D("0.00008")        # 0.0000125 - 0.00002 + 0.0001 - 0.0000125
    assert r.funding.mean_hourly_funding.value == D("0.00002")       # 0.00008 / 4
    assert "1h" in r.funding.latest_rate.unit and "longs pay shorts" in r.funding.latest_rate.unit
    assert r.funding.latest_start == FUND_LAST and r.funding.trusted_for_current_use
    assert not any("annual" in key.lower() for key in r.funding.model_dump())
    assert "FUNDING_NOT_ANNUALIZED_NOT_PROJECTED" in r.limitations


def test_funding_positive_negative_and_zero_are_all_valid_values():
    for value in ("0.0001", "-0.0001", "0"):
        assert run(fs=rates([value])).funding.latest_rate.value == D(value)


def test_funding_lookback_warm_up_and_gaps():
    short = run(fs=rates(["0.0000125", "0.0000125"]))
    assert short.funding.latest_rate.value == D("0.0000125")
    assert short.funding.cumulative_funding.reason == "WARMING_UP_NEED_4_HAVE_2" and short.funding.trusted_for_current_use
    three = rates(["0.0000125"] * 3)
    assert run(fs=three).funding.cumulative_funding.reason == "WARMING_UP_NEED_4_HAVE_3"
    five = rates(["0.00001"] * 5)
    five = (five[0], five[1], five[3], five[4])  # missing the middle hour inside the 4h lookback
    g = run(fs=five)
    assert g.funding.cumulative_funding.reason == "GAP_IN_LOOKBACK" and "FUNDING_GAP_DETECTED" in g.funding.reasons
    assert not g.funding.trusted_for_current_use and g.funding.latest_rate.value == D("0.00001")


@pytest.mark.parametrize("record, reason", [
    (lambda: fund(FUND_LAST - HOUR, "0.00001", offset=1800), "FUNDING_TIMESTAMP_OFF_HOURLY_SCHEDULE"),
    (lambda: fund(FUND_LAST, "0.00001", offset=-1), "FUNDING_TIMESTAMP_OFF_HOURLY_SCHEDULE"),
    (lambda: fund(FUND_LAST, "0.0400001"), "FUNDING_RATE_EXCEEDS_DOCUMENTED_CAP"),
    (lambda: fund(FUND_LAST, "-0.05"), "FUNDING_RATE_EXCEEDS_DOCUMENTED_CAP"),
])
def test_funding_off_schedule_or_beyond_the_documented_cap_is_unavailable(record, reason):
    r = run(fs=(record(),))
    assert r.funding.reasons == (reason,) and r.funding.latest_rate.value is None


def test_funding_at_exactly_the_documented_cap_is_accepted():
    assert run(fs=(fund(FUND_LAST, "0.04"),)).funding.latest_rate.value == D("0.04")


def test_funding_duplicate_conflict_and_mixed_sources():
    base = rates(["0.00001", "0.00002", "0.00003", "0.00004"])
    again = fund(FUND_LAST, "0.00004", lag=1, source_type="public_websocket")
    r = run(fs=base + (again,))
    assert r.funding.duplicate_count == 1 and r.funding.cumulative_funding.value == D("0.0001")
    conflict = run(fs=base + (fund(FUND_LAST, "0.00005"),))
    assert conflict.funding.reasons == ("FUNDING_CONFLICT",) and conflict.funding.latest_rate.value is None
    mixed = run(fs=base + (fund(FUND_LAST - 9 * HOUR, "0.00001", source="other"),))
    assert mixed.funding.reasons == ("MIXED_FUNDING_SOURCES",)


# ------------------------------------------------------------------- timing and boundaries
def test_incomplete_candle_observed_before_it_closed_is_excluded_not_consumed():
    partial = candle(FUND_LAST, 1000, 1000, 1, 1000, 1, lag=-3300)       # 12:00 candle seen at 12:05, closes 13:00
    r = run(candles(ATR_SERIES) + (partial,))
    assert r.candles.incomplete_count == 1 and r.candles.latest_start == LAST
    assert r.candles.atr.value == frac(10, 3) and r.candles.trusted_for_current_use


def test_candle_received_exactly_at_close_counts_and_one_millisecond_earlier_does_not():
    exact = candle(LAST, 5, 5, 5, 5, 1).model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="t", source_id="x", source_timestamp=LAST, received_timestamp=LAST + HOUR)})
    early = exact.model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="t", source_id="x", source_timestamp=LAST, received_timestamp=LAST + HOUR - MS)})
    assert run((exact,)).candles.retained_count == 1 and run((exact,)).candles.incomplete_count == 0
    r = run((early,))
    assert r.candles.retained_count == 0 and r.candles.incomplete_count == 1


def test_a_partial_snapshot_followed_by_the_final_candle_is_not_a_conflict():
    partial = candle(LAST, 9, 10, 8, 9, 1, lag=-1800)   # seen halfway through the hour
    final = candle(LAST, 9, 12, 8, 11, 7, lag=5)
    r = run(candles(ATR_SERIES[:-1], LAST - HOUR) + (partial, final))
    assert r.candles.incomplete_count == 1 and r.candles.reasons == ()
    one_bar = [m for m in r.candles.momentum if m.lookback_bars == 1][0].simple_return.value
    assert one_bar == D("0.1")   # final close 11 versus previous close 10; the partial 9 never counts


def test_freshness_is_hourly_aware_and_independent_of_the_c05_thresholds():
    # C05 stays untouched: a 90 s candle limit would call every closed hourly candle stale.
    assert default_quality_policy().threshold_for(Capability.CANDLES).live_max_age == timedelta(seconds=90)
    assert CANDLE_OFFSET_SECONDS == 60 and module.CANDLE_OFFSET == timedelta(seconds=60)
    series = candles(ATR_SERIES)
    live = run(series, evaluation_time=LAST + 2 * HOUR + timedelta(seconds=59, milliseconds=999))
    assert live.candles.quality.state.value == "LIVE" and live.candles.bars_behind == 0
    behind = run(series, evaluation_time=LAST + 2 * HOUR + timedelta(seconds=60))
    assert behind.candles.quality.state.value == "DELAYED" and behind.candles.bars_behind == 1
    assert behind.candles.atr.reason == "DATA_QUALITY_NOT_TRUSTED" and not behind.candles.trusted_for_current_use
    assert "ONE_INTERVAL_BEHIND" in behind.candles.reasons and behind.candles.provenance is not None
    stale = run(series, evaluation_time=LAST + 3 * HOUR + timedelta(seconds=60))
    assert stale.candles.quality.state.value == "STALE" and stale.candles.bars_behind == 2
    assert stale.candles.quality.source_age == timedelta(hours=2, minutes=1)


def test_candle_just_closed_but_before_the_availability_offset_is_not_stale_or_early():
    series = candles(ATR_SERIES, LAST + HOUR, lag=2)    # newest candle (12:00) closed 13:00, received 13:00:02
    r = run(series, evaluation_time=LAST + 2 * HOUR + timedelta(seconds=30))   # 13:00:30, before 13:01
    assert r.candles.bars_behind == 0 and r.candles.quality.state.value == "LIVE"


def test_funding_freshness_boundary_matches_the_hourly_schedule():
    series = rates(["0.00001"] * 4)
    live = run(fs=series, evaluation_time=FUND_LAST + HOUR + timedelta(seconds=59, milliseconds=999))
    assert live.funding.quality.state.value == "LIVE" and live.funding.bars_behind == 0
    behind = run(fs=series, evaluation_time=FUND_LAST + HOUR + timedelta(seconds=60))
    assert behind.funding.quality.state.value == "DELAYED" and behind.funding.latest_rate.reason == "DATA_QUALITY_NOT_TRUSTED"
    assert run(fs=series, evaluation_time=FUND_LAST + 2 * HOUR + timedelta(seconds=60)).funding.quality.state.value == "STALE"


@pytest.mark.parametrize("override, reason", [
    (dict(continuity=ContinuityStatus.UNKNOWN), "CONTINUITY_NOT_PROVEN"),
    (dict(continuity=ContinuityStatus.GAP_RISK), "GAP_OR_CONTINUITY_RISK"),
    (dict(recovery=RecoveryStatus.RECOVERING), "RECOVERY_IN_PROGRESS_NO_REPLAY_CLAIM"),
    (dict(recovery=RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF), "RECOVERY_OBSERVED_REPLAY_NOT_PROVEN"),
])
def test_continuity_and_recovery_propagate_to_both_sections_and_withhold_numbers(override, reason):
    r = run(candles(ATR_SERIES), rates(["0.00001"] * 4), **override)
    for section, metric in ((r.candles, r.candles.atr), (r.funding, r.funding.latest_rate)):
        assert metric.value is None and reason in section.reasons and not section.trusted_for_current_use


@pytest.mark.parametrize("availability", [CapabilityAvailability.UNAVAILABLE, CapabilityAvailability.LIMITED])
def test_unavailable_or_limited_coverage_withholds_numbers(availability):
    cov = CapabilityCoverage(Capability.CANDLES, availability, "provider limitation")
    fcov = CapabilityCoverage(Capability.FUNDING, availability, "provider limitation")
    r = run(candles(ATR_SERIES), rates(["0.00001"] * 4), candle_coverage=cov, funding_coverage=fcov)
    assert r.candles.atr.value is None and r.funding.latest_rate.value is None
    assert "provider limitation" in r.candles.reasons and "provider limitation" in r.funding.reasons


def test_coverage_for_the_wrong_capability_is_rejected():
    with pytest.raises(ValueError, match="coverage capability"):
        run(candles(ATR_SERIES), candle_coverage=SUPPORTED[Capability.FUNDING])


# ------------------------------------------------- lookahead and historical point in time
def stable(section):
    data = section.model_dump(mode="json")
    for key in ("input_count", "not_yet_received_count"):
        data.pop(key)
    return data


FUTURE = {
    "conflicting duplicate": lambda: (candle(LAST, 1, 99, 1, 50, 9, lag=7200),),
    "different source": lambda: (candle(LAST + HOUR, 1, 2, 1, 2, 1, source="other"),),
    "bad interval": lambda: (candle(LAST + HOUR, 1, 2, 1, 2, 1, end=LAST + 3 * HOUR),),
    "wrong symbol": lambda: (candle(LAST + HOUR, 1, 2, 1, 2, 1, symbol="ETH"),),
    "huge number": lambda: (candle(LAST + HOUR, 1, 10 ** 60, 1, 2, 1),),
}


@pytest.mark.parametrize("name", FUTURE)
def test_candles_received_after_evaluation_cannot_change_an_earlier_evaluation(name):
    base = run(candles(ATR_SERIES))
    extra = FUTURE[name]()
    with_future = run(candles(ATR_SERIES) + extra)
    assert stable(with_future.candles) == stable(base.candles)
    assert with_future.candles.not_yet_received_count == len(extra)


def test_funding_received_after_evaluation_cannot_change_an_earlier_evaluation():
    base = run(fs=rates(["0.00001"] * 4))
    future = (fund(FUND_LAST, "0.09", lag=7200), fund(FUND_LAST + HOUR, "0.5", source="other"), fund(FUND_LAST + HOUR, "0.0001", offset=1800))
    r = run(fs=rates(["0.00001"] * 4) + future)
    assert stable(r.funding) == stable(base.funding) and r.funding.not_yet_received_count == 3


def test_replay_at_an_earlier_time_equals_analysis_of_only_the_data_known_then():
    full = closes([100, 101, 103, 102, 105, 104, 108, 107])               # newest start 11:00
    earlier = NOW - 3 * HOUR                                             # 09:05: newest known closed candle starts 08:00
    visible = tuple(c for c in full if c.provenance.received_timestamp <= earlier)
    assert len(visible) == 5
    a = run(full, evaluation_time=earlier, c=config(volatility_period=4))
    b = run(visible, evaluation_time=earlier, c=config(volatility_period=4))
    assert stable(a.candles) == stable(b.candles) and a.candles.not_yet_received_count == 3
    assert a.candles.latest_start == LAST - 3 * HOUR and a.candles.quality.state.value == "LIVE"
    later = run(full, c=config(volatility_period=4))
    assert later.candles.latest_start == LAST and later.candles.provenance.input_digest != a.candles.provenance.input_digest


def test_future_received_records_are_never_validated_but_apply_once_time_reaches_them():
    wrong = candle(LAST + HOUR, 1, 2, 1, 2, 1, symbol="ETH")
    assert run(candles(ATR_SERIES) + (wrong,)).candles.not_yet_received_count == 1
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        run(candles(ATR_SERIES) + (wrong,), evaluation_time=NOW + 2 * HOUR)


# ------------------------------------------------------------- integrity and identity
def test_duplicate_candles_count_once_and_conflicts_make_the_section_unavailable():
    series = candles(ATR_SERIES)
    again = candle(series[-1].start_timestamp, *(series[-1].open, series[-1].high, series[-1].low, series[-1].close, series[-1].volume),
                   lag=9, source_type="public_websocket")
    r = run(series + (again,) + series[:2])
    assert r.candles.duplicate_count == 3 and r.candles.atr.value == frac(10, 3)
    for changed in (candle(series[-1].start_timestamp, 11, 14, 11, 13, 2),   # volume
                    candle(series[-1].start_timestamp, 11, 15, 11, 13, 1)):  # high
        c = run(series + (changed,))
        assert c.candles.reasons == ("CANDLE_CONFLICT",) and c.candles.atr.value is None and c.candles.provenance is None


def test_mixed_sources_misaligned_intervals_and_provenance_mismatch_fail_closed():
    series = candles(ATR_SERIES)
    assert run(series + (candle(LAST - 9 * HOUR, 1, 2, 1, 2, 1, source="other"),)).candles.reasons == ("MIXED_CANDLE_SOURCES",)
    wrong_end = candle(LAST - HOUR, 9, 10, 8, 9, 1, end=LAST + HOUR - MS, lag=3600)
    assert "CANDLE_INTERVAL_INVALID" in run((wrong_end,)).candles.reasons
    misaligned = candle(LAST - HOUR + timedelta(minutes=30), 9, 10, 8, 9, 1)
    assert "CANDLE_INTERVAL_INVALID" in run((misaligned,)).candles.reasons
    bad = series[-1].model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="t", source_id="1", source_timestamp=LAST - MS, received_timestamp=LAST + HOUR)})
    assert "CANDLE_TIMESTAMP_PROVENANCE_MISMATCH" in run((bad,)).candles.reasons
    nosrc = series[-1].model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="t", received_timestamp=LAST + HOUR)})
    assert "CANDLE_TIMESTAMP_PROVENANCE_MISMATCH" in run((nosrc,)).candles.reasons
    assert run((candle(LAST, 1, 10 ** 60, 1, 2, 1),)).candles.reasons == ("NUMERIC_RANGE_UNSUPPORTED",)


def test_gaps_inside_a_lookback_make_that_metric_unavailable_but_old_gaps_do_not():
    series = candles(ATR_SERIES)
    gapped = (series[0], series[1], series[3], series[4])             # missing the 09:00 candle
    r = run(gapped)
    assert r.candles.atr.reason == "GAP_IN_LOOKBACK" and "CANDLE_GAP_DETECTED" in r.candles.reasons
    assert not r.candles.trusted_for_current_use
    older = candles([(5, 6, 4, 5, 1)], LAST - 9 * HOUR) + series        # a hole far before the ATR window
    assert run(older).candles.atr.value == frac(10, 3) and run(older).candles.reasons == ()


def test_input_order_does_not_change_the_report():
    items = list(candles(closes_to_specs([100, 101, 103, 102, 105, 104, 108]))) + list(rates(["0.00001", "0.00002", "0.00003", "0.00004"]))
    expected = None
    rng = random.Random(11)
    for _ in range(15):
        rng.shuffle(items)
        cs = tuple(i for i in items if isinstance(i, Candle))
        fs = tuple(i for i in items if isinstance(i, FundingSnapshot))
        dumped = run(cs, fs, c=config(volatility_period=4)).model_dump_json()
        expected = expected or dumped
        assert dumped == expected


def closes_to_specs(values):
    return [(c, c, c, c, 1) for c in values]


# ------------------------------------------------------------------- provenance and digest
def test_sections_preserve_compact_provenance_that_round_trips():
    r = run(candles(ATR_SERIES), rates(["0.00001"] * 4))
    cp, fp = r.candles.provenance, r.funding.provenance
    assert (cp.source, cp.source_types, cp.contributing_count) == ("fixture", ("public_info",), 5)
    assert cp.earliest_time == LAST - 4 * HOUR and cp.latest_time == LAST
    assert cp.newest_record_provenance == candles(ATR_SERIES)[-1].provenance and cp.digest_algorithm.endswith("candles-v1")
    assert (fp.contributing_count, fp.earliest_time, fp.digest_algorithm) == (4, FUND_LAST - 3 * HOUR + timedelta(seconds=0.035), "sha256-canonical-funding-v1")
    assert DerivativesReport.model_validate_json(r.model_dump_json()) == r
    assert r.candles.quality.capability is Capability.CANDLES and r.funding.quality.capability is Capability.FUNDING


def test_digests_are_order_independent_and_bind_content_receipt_source_and_transport():
    series = candles(ATR_SERIES)
    digest = run(series).candles.provenance.input_digest
    shuffled = list(series)
    random.Random(2).shuffle(shuffled)
    assert run(shuffled).candles.provenance.input_digest == digest
    assert run(series + series).candles.provenance.input_digest == digest
    for variant in (
        candles(ATR_SERIES, lag=6),                                       # receipt time
        candles(ATR_SERIES, source="other"),                              # source
        candles(ATR_SERIES, source_type="public_websocket"),              # transport
        candles(ATR_SERIES[:-1] + [(11, 14, 11, 13, 2)]),                 # content
    ):
        assert run(variant).candles.provenance.input_digest != digest
    fd = run(fs=rates(["0.00001"] * 4)).funding.provenance.input_digest
    assert run(fs=rates(["0.00001"] * 4, lag=3)).funding.provenance.input_digest != fd
    assert run(fs=rates(["0.00001"] * 3 + ["0.000011"])).funding.provenance.input_digest != fd


def test_provenance_stays_bounded_for_large_inputs():
    many = closes([100 + (i % 7) for i in range(3000)])
    small, large = run(closes([100, 101, 102, 103, 104])), run(many)
    assert large.candles.provenance.contributing_count == 3000
    assert len(large.model_dump_json()) < 3 * len(small.model_dump_json())


def test_available_metrics_require_provenance_and_trust_requires_quality():
    r = run(candles(ATR_SERIES))
    data = r.candles.model_dump()
    with pytest.raises(ValidationError, match="provenance"):
        type(r.candles).model_validate({**data, "provenance": None})
    with pytest.raises(ValidationError, match="trusted"):
        type(r.candles).model_validate({**data, "quality": None})


# ------------------------------------------------------------------------- OI and basis
def test_open_interest_and_basis_are_explicitly_unavailable_never_numeric():
    r = run(candles(ATR_SERIES), rates(["0.00001"] * 4))
    for metric, reason in ((r.open_interest, module.OI_REASON), (r.basis, module.BASIS_REASON)):
        assert metric.value is None and metric.reason == reason and metric.unit == "UNVERIFIED"
    assert "OPEN_INTEREST_UNVERIFIED" in r.open_interest.reason and "BASIS" in r.basis.reason
    data = r.model_dump()
    for field in ("open_interest", "basis"):
        with pytest.raises(ValidationError, match="unavailable"):
            DerivativesReport.model_validate({**data, field: {**data[field], "value": "0", "reason": None}})
        with pytest.raises(ValidationError):
            DerivativesReport.model_validate({**data, field: {**data[field], "value": "5", "reason": None}})


# ---------------------------------------------------------------------- caller contracts
def test_invalid_callers_are_rejected_not_defaulted():
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        run(candles(ATR_SERIES) + (candle(LAST - 9 * HOUR, 1, 2, 1, 2, 1, symbol="ETH"),))
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        run(fs=(fund(FUND_LAST, "0.00001", symbol="ETH"),))
    with pytest.raises(ValueError, match="SESSION_START_AFTER_EVALUATION"):
        run(candles(ATR_SERIES), c=session_config(datetime(2026, 10, 15, 13, tzinfo=timezone.utc)))
    with pytest.raises(ValueError, match="timezone-aware"):
        run(candles(ATR_SERIES), evaluation_time=datetime(2026, 10, 15, 12))
    with pytest.raises(ValueError):
        analyze_derivatives(list(candles(ATR_SERIES)), (), config=config(), candle_coverage=SUPPORTED[Capability.CANDLES],
                            funding_coverage=SUPPORTED[Capability.FUNDING], evaluation_time=NOW,
                            continuity=ContinuityStatus.PROVEN, recovery=RecoveryStatus.NONE)
    with pytest.raises(ValueError):
        run(("not a candle",))


def test_validation_bypass_and_oversize_are_rejected(monkeypatch):
    good = candles(ATR_SERIES)[0]
    bad = Candle.model_construct(**{**dict(good), "close": D("-1")})
    with pytest.raises(ValidationError):
        run((bad,))
    monkeypatch.setattr(module, "MAX_RECORDS", 2)
    with pytest.raises(ValueError, match="too many records"):
        run(candles(ATR_SERIES))


@pytest.mark.parametrize("kwargs", [
    dict(atr_period=0), dict(atr_period=201), dict(volatility_period=1), dict(momentum_lookbacks=()),
    dict(momentum_lookbacks=(2, 1)), dict(momentum_lookbacks=(1, 1)), dict(momentum_lookbacks=(0,)),
    dict(momentum_lookbacks=tuple(range(1, 10))), dict(funding_lookback_hours=0), dict(base_asset=" "),
    dict(session_start=LAST + timedelta(minutes=30)), dict(session_start=datetime(2026, 1, 1)),
])
def test_config_rejects_invalid_values(kwargs):
    with pytest.raises(ValidationError):
        config(**kwargs)


def test_module_has_no_hidden_clock_network_ai_or_io():
    source = inspect.getsource(module)
    for forbidden in ("datetime.now", "time.time", "utcnow", "urllib", "socket", "requests", "random", "open(", "os.environ"):
        assert forbidden not in source


# --------------------------------------------------------------- compatibility with C04
class FixtureAdapter(HyperliquidAdapter):
    def __init__(self, payloads):
        super().__init__(clock=lambda: NOW)
        self.payloads = payloads

    def _post(self, payload, capability):
        return self.payloads[capability]


def test_provider_normalized_candles_and_funding_flow_through_the_analytics():
    def raw(start, c):
        return {"t": int(start.timestamp() * 1000), "T": int((start + HOUR).timestamp() * 1000) - 1, "s": "BTC", "i": "1h",
                "o": str(c), "c": str(c), "h": str(c), "l": str(c), "v": "1", "n": 1}
    funding = {"coin": "BTC", "fundingRate": "0.0000125", "premium": "-0.0001", "time": int((FUND_LAST + timedelta(seconds=0.035)).timestamp() * 1000)}
    adapter = FixtureAdapter({Capability.CANDLES: [raw(LAST - (2 - i) * HOUR, c) for i, c in enumerate((100, 110, 121))],
                              Capability.FUNDING: [funding]})
    adapter.connect()
    provider_candles, provider_funding = adapter.candles("BTC"), (adapter.funding("BTC"),)
    r = run(provider_candles, provider_funding, c=config(momentum_lookbacks=(2,), funding_lookback_hours=1))
    assert r.candles.momentum[0].simple_return.value == D("0.21") and r.candles.trusted_for_current_use
    assert r.funding.latest_rate.value == D("0.0000125") and r.funding.trusted_for_current_use
    assert r.candles.provenance.source == "hyperliquid" and r.funding.provenance.source_types == ("public_info",)


def test_funding_schedule_tolerance_boundary_is_the_c06_availability_offset():
    assert run(fs=(fund(FUND_LAST, "0.00001", offset=59.999),)).funding.latest_rate.value == D("0.00001")
    assert run(fs=(fund(FUND_LAST, "0.00001", offset=60),)).funding.reasons == ("FUNDING_TIMESTAMP_OFF_HOURLY_SCHEDULE",)


def test_atr_true_range_covers_a_gap_down_through_the_low_and_only_the_last_periods_count():
    gap_down = [(20, 20, 20, 20, 1), (11, 12, 10, 11, 1)]   # range 2; |high-prev|=8; |low-prev|=10
    assert run(candles(gap_down), c=config(atr_period=1)).candles.atr.value == D(10)
    older = [(1, 100, 1, 50, 1)] + ATR_SERIES                   # a huge old range must not enter a 3-period ATR
    assert run(candles(older), c=config(atr_period=3)).candles.atr.value == frac(10, 3)


def test_funding_cumulative_uses_only_the_lookback_hours():
    values = ["0.00009", "0.00008", "0.00001", "0.00002", "0.00003", "0.00004"]
    r = run(fs=rates(values))   # lookback 4 -> last four only
    assert r.funding.cumulative_funding.value == D("0.0001") and r.funding.mean_hourly_funding.value == D("0.000025")


# ------------------------------------------------- signed funding through the provider
@pytest.mark.parametrize("rate", ["0.0000125", "0", "-0.0000125", "-0.00022196"])
def test_provider_normalized_signed_funding_reaches_the_analytics(rate):
    when = FUND_LAST + timedelta(seconds=0.035)
    raw = {"coin": "BTC", "fundingRate": rate, "premium": "0.0", "time": int(when.timestamp() * 1000)}
    adapter = FixtureAdapter({Capability.FUNDING: [raw]})
    adapter.connect()
    r = run(fs=(adapter.funding("BTC"),), c=config(funding_lookback_hours=1))
    assert r.funding.latest_rate.value == D(rate) and r.funding.cumulative_funding.value == D(rate)
    assert r.funding.trusted_for_current_use and r.funding.reasons == ()


# ----------------------------------------------- deterministic duplicate representative
def with_ids(spec, ids, lag=5, **kw):
    return [candle(LAST, *spec, lag=lag, source_id=i, **kw) for i in ids]


def test_equivalent_candles_with_different_source_ids_are_one_deterministic_observation():
    base = candles(ATR_SERIES[:-1], LAST - HOUR)
    copies = with_ids(ATR_SERIES[-1], ["B", "C", "A"])                 # equal receipt times and transports
    results = {run(base + tuple(p)).model_dump_json() for p in itertools.permutations(copies)}
    assert len(results) == 1
    r = run(base + tuple(copies))
    assert r.candles.duplicate_count == 2 and r.candles.retained_count == 5
    assert r.candles.provenance.newest_record_provenance.source_id == "A"      # smallest id wins the tie
    assert r.candles.reasons == () and r.candles.atr.value == frac(10, 3)


def test_the_earliest_received_equivalent_candle_represents_the_observation_regardless_of_order():
    base = candles(ATR_SERIES[:-1], LAST - HOUR)
    copies = (with_ids(ATR_SERIES[-1], ["Z"], lag=5) + with_ids(ATR_SERIES[-1], ["A"], lag=9)
              + with_ids(ATR_SERIES[-1], ["M"], lag=7, source_type="public_websocket"))
    results = {run(base + tuple(p)).model_dump_json() for p in itertools.permutations(copies)}
    assert len(results) == 1
    kept = run(base + tuple(copies)).candles.provenance
    assert kept.newest_record_provenance.source_id == "Z" and kept.source_types == ("public_info",)


def test_a_missing_source_id_sorts_deterministically_and_digests_do_not_depend_on_order():
    base = candles(ATR_SERIES[:-1], LAST - HOUR)
    copies = [candle(LAST, *ATR_SERIES[-1], source_id=None).model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="public_info", source_timestamp=LAST, received_timestamp=LAST + HOUR + timedelta(seconds=5))})]
    copies += with_ids(ATR_SERIES[-1], ["A", "B"])
    reports = [run(base + tuple(p)) for p in itertools.permutations(copies)]
    assert len({r.model_dump_json() for r in reports}) == 1
    assert reports[0].candles.provenance.newest_record_provenance.source_id is None


def test_materially_conflicting_candles_are_never_resolved_by_any_input_order():
    base = candles(ATR_SERIES[:-1], LAST - HOUR)
    variants = [candle(LAST, *ATR_SERIES[-1], source_id="A"), candle(LAST, 11, 14, 11, 13, 2, source_id="B"),
                candle(LAST, *ATR_SERIES[-1], source_id="C")]
    for p in itertools.permutations(variants):
        r = run(base + tuple(p))
        assert r.candles.reasons == ("CANDLE_CONFLICT",) and r.candles.atr.value is None and r.candles.provenance is None


def test_equivalent_funding_with_different_source_ids_is_deterministic_and_conflicts_still_fail():
    def f(rate, source_id, lag=2):
        when = FUND_LAST + timedelta(seconds=0.035)
        return FundingSnapshot(symbol="BTC", funding_rate=D(rate), timestamp=when, provenance=SourceProvenance(
            source="fixture", source_type="public_info", source_id=source_id, source_timestamp=when,
            received_timestamp=when + timedelta(seconds=lag)))
    base = rates(["0.00001", "0.00002", "0.00003"], FUND_LAST - HOUR)
    same = [f("0.00004", "B"), f("0.00004", "A"), f("0.00004", None)]
    assert len({run(fs=base + tuple(p)).model_dump_json() for p in itertools.permutations(same)}) == 1
    assert run(fs=base + tuple(same)).funding.duplicate_count == 2
    for p in itertools.permutations([f("0.00004", "A"), f("0.00005", "B")]):
        assert run(fs=base + tuple(p)).funding.reasons == ("FUNDING_CONFLICT",)


# ---------------------------------------------------- independence from ambient Decimal state
CAP_CASES = [("0.04", True), ("0.0400000000000000000001", False), ("0.0399999999999999999999", True),
             ("-0.04", True), ("-0.0400000000000000000001", False), ("-0.0399999999999999999999", True),
             ("0.04000000000000000000000000000001", False), ("0.0400001", False)]


@pytest.mark.parametrize("precision", [1, 2, 3, 5, 10, 28, 50, 100])
@pytest.mark.parametrize("rounding", ["ROUND_HALF_EVEN", "ROUND_UP", "ROUND_DOWN", "ROUND_CEILING", "ROUND_FLOOR"])
def test_the_funding_cap_decision_is_exact_under_any_ambient_decimal_context(precision, rounding):
    import decimal
    for rate, accepted in CAP_CASES:
        record = fund(FUND_LAST, rate)
        with decimal.localcontext() as ctx:
            ctx.prec, ctx.rounding = precision, getattr(decimal, rounding)
            r = run(fs=(record,), c=config(funding_lookback_hours=1))
        assert (r.funding.latest_rate.value is not None) is accepted, (rate, precision, rounding)
        if not accepted:
            assert r.funding.reasons == ("FUNDING_RATE_EXCEEDS_DOCUMENTED_CAP",)


def test_the_whole_report_is_identical_under_different_ambient_contexts():
    import decimal
    items = (candles(closes_to_specs(["100", "101.5", "103.25", "102", "105", "104", "108"]), LAST), rates(["0.0000125", "-0.00002", "0.0001", "-0.0000125"]))
    c = config(volatility_period=4, session_start=LAST - 3 * HOUR)
    expected = run(*items, c=c).model_dump_json()
    for precision, rounding in ((1, decimal.ROUND_UP), (3, decimal.ROUND_DOWN), (7, decimal.ROUND_CEILING), (200, decimal.ROUND_HALF_EVEN)):
        with decimal.localcontext() as ctx:
            ctx.prec, ctx.rounding = precision, rounding
            assert run(*items, c=c).model_dump_json() == expected


# ------------------------------------------------------------------ C06 replay interoperability
def test_c06_replayed_history_is_never_consumed_before_its_actual_receipt_and_is_stale_after():
    """C06 releases records by modeled availability; C09 trusts only actual receipt timestamps.

    Receipt timestamps are not rewritten, so history fetched after the evaluation time is
    excluded (no lookahead) and, once fetched, the old bars are far behind the evaluation
    time. Historical C09 analysis therefore needs an explicit modeled-availability input
    contract; that extension is deliberately not made here.
    """
    from test_historical_dataset import BASE, FETCHED, candle as c06_candle, dataset, funding as c06_funding
    from traid.historical import replay
    from traid.historical.models import Category
    ds = dataset([c06_candle(i) for i in range(3)], [c06_funding(i) for i in range(3)])
    as_of = BASE + timedelta(hours=3, seconds=120)
    events = tuple(replay(ds, as_of=as_of))
    assert sum(e.category is Category.CANDLE for e in events) == 3          # C06 models all three as available
    cs = tuple(e.value for e in events if e.category is Category.CANDLE)
    fs = tuple(e.value for e in events if e.category is Category.FUNDING_SNAPSHOT)
    assert all(v.provenance.received_timestamp == FETCHED > as_of for v in (*cs, *fs))   # receipts untouched
    c = config(atr_period=2, volatility_period=2, momentum_lookbacks=(1,), funding_lookback_hours=3)
    early = run(cs, fs, c=c, evaluation_time=as_of)
    assert early.candles.not_yet_received_count == 3 and early.candles.reasons == ("NO_CLOSED_CANDLES",)
    assert early.funding.not_yet_received_count == 3 and early.funding.reasons == ("NO_FUNDING_OBSERVATIONS",)
    late = run(cs, fs, c=c, evaluation_time=FETCHED)
    assert late.candles.not_yet_received_count == 0 and late.candles.quality.state.value == "STALE"
    assert late.candles.atr.reason == late.funding.latest_rate.reason == "DATA_QUALITY_NOT_TRUSTED"
