from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, localcontext
import inspect
import random

import pytest
from pydantic import ValidationError

import traid.regime.engine as engine
from traid.derivatives import DerivativesConfig, analyze_derivatives
from traid.domain import Candle, FundingSnapshot, LiquidationEvent, SourceProvenance
from traid.domain.models import AggressorSide, MarketTrade, OrderBookLevel, OrderBookSnapshot
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.flow import FlowConfig, analyze_flow
from traid.liquidity import LiquidityConfig, analyze_book
from traid.quality import ContinuityStatus, RecoveryStatus, default_quality_policy
from traid.regime import (
    CrowdingState, DirectionRules, DirectionState, FlowRules, FlowState, FundingPolarity,
    LiquidationLabel, LiquidationRules, LiquidityRules, LiquidityState, MarketStateReport,
    MarketStateRules, RegimeState, VerifiedLiquidationSource, VolatilityRules, VolatilityState,
    WindowKind, classify_market_state, rules_digest,
)

D = Decimal
UTC = timezone.utc
HOUR = timedelta(hours=1)
MS = timedelta(milliseconds=1)
NOW = datetime(2026, 10, 15, 12, 5, tzinfo=UTC)
LAST = datetime(2026, 10, 15, 11, tzinfo=UTC)       # newest closed candle at NOW
FUND_LAST = datetime(2026, 10, 15, 12, tzinfo=UTC)  # newest settled funding hour at NOW
BUY, SELL = AggressorSide.BUY, AggressorSide.SELL
PROVEN = dict(continuity=ContinuityStatus.PROVEN, recovery=RecoveryStatus.NONE)
VERIFIED = VerifiedLiquidationSource(source="verified-feed", source_type="public_websocket")


# ------------------------------------------------------------------ real C07-C09 builders
def candle(start, close, lag=5, symbol="BTC"):
    return Candle(symbol=symbol, start_timestamp=start, end_timestamp=start + HOUR - MS, open=D(close), high=D(close),
                  low=D(close), close=D(close), volume=D(1), provenance=SourceProvenance(
                      source="fixture", source_type="public_info", source_id=str(int(start.timestamp())),
                      source_timestamp=start, received_timestamp=start + HOUR + timedelta(seconds=lag)))


def closes(values, last=LAST, **kw):
    return tuple(candle(last - (len(values) - 1 - i) * HOUR, v, **kw) for i, v in enumerate(values))


def fund(hour, rate):
    when = hour + timedelta(milliseconds=35)
    return FundingSnapshot(symbol="BTC", funding_rate=D(rate), timestamp=when, provenance=SourceProvenance(
        source="fixture", source_type="public_info", source_id="fundingHistory", source_timestamp=when,
        received_timestamp=when + timedelta(seconds=2)))


def rates(values, last=FUND_LAST):
    return tuple(fund(last - (len(values) - 1 - i) * HOUR, r) for i, r in enumerate(values))


CLOSES = (100, 101, 103, 104)  # momentum(1) = 104/103 - 1, momentum(2) = 104/101 - 1, both up


def derivatives(cs=None, fs=None, at=NOW, lookbacks=(1, 2), quote="USD", **kw):
    config = DerivativesConfig(symbol="BTC", base_asset="BTC", quote_currency=quote, atr_period=3,
                               volatility_period=2, momentum_lookbacks=lookbacks, funding_lookback_hours=4)
    args = dict(config=config, candle_coverage=CapabilityCoverage(Capability.CANDLES, CapabilityAvailability.SUPPORTED),
                funding_coverage=CapabilityCoverage(Capability.FUNDING, CapabilityAvailability.SUPPORTED),
                evaluation_time=at, **PROVEN)
    args.update(kw)
    return analyze_derivatives(
        closes(CLOSES) if cs is None else tuple(cs), rates(["0.0001"] * 4) if fs is None else tuple(fs), **args)


TIGHT_BIDS = (("100", "2"), ("99.9", "3"))
TIGHT_ASKS = (("100.1", "2"), ("100.2", "3"))


def liquidity(bids=TIGHT_BIDS, asks=TIGHT_ASKS, age=0, at=NOW, quote="USD", **kw):
    when = at - timedelta(seconds=age)
    book = OrderBookSnapshot(symbol="BTC", timestamp=when, provenance=SourceProvenance(
        source="fixture", source_type="public_websocket", source_timestamp=when, received_timestamp=when),
        bids=tuple(OrderBookLevel(price=D(p), quantity=D(q)) for p, q in bids),
        asks=tuple(OrderBookLevel(price=D(p), quantity=D(q)) for p, q in asks))
    config = LiquidityConfig(symbol="BTC", base_asset="BTC", quote_currency=quote, bands_bps=(D(100), D(200)))
    args = dict(config=config, coverage=CapabilityCoverage(Capability.ORDER_BOOK, CapabilityAvailability.SUPPORTED),
                evaluation_time=at, policy=default_quality_policy(), **PROVEN)
    args.update(kw)
    return analyze_book(book, **args)


def trade(tid, side, qty, ago=1.0, lag=0.0):
    when = NOW - timedelta(seconds=ago)
    return MarketTrade(symbol="BTC", price=D(100), quantity=D(qty), side=side, timestamp=when,
                       provenance=SourceProvenance(source="fixture", source_type="public_websocket", source_id=tid,
                                                   source_timestamp=when, received_timestamp=when + timedelta(seconds=lag)))


BALANCE_3_TO_1 = (trade("t1", BUY, "2", ago=30), trade("t2", SELL, "1", ago=20), trade("t3", BUY, "1", ago=1))


def flow(trades=BALANCE_3_TO_1, at=NOW, base="BTC", **kw):
    config = FlowConfig(symbol="BTC", base_asset=base, window=timedelta(seconds=60), session_start=NOW - timedelta(seconds=300),
                        late_tolerance=timedelta(seconds=5))
    args = dict(config=config, coverage=CapabilityCoverage(Capability.TRADES, CapabilityAvailability.SUPPORTED),
                evaluation_time=at, policy=default_quality_policy(), **PROVEN)
    args.update(kw)
    return analyze_flow(tuple(trades), **args)


def liq(sid="L1", ago=10, lag=1, source="verified-feed", source_type="public_websocket", price="100", qty="1",
        source_ts=True, symbol="BTC"):
    when = NOW - timedelta(seconds=ago)
    return LiquidationEvent(symbol=symbol, price=D(price), quantity=D(qty), timestamp=when, provenance=SourceProvenance(
        source=source, source_type=source_type, source_id=sid, source_timestamp=when if source_ts else None,
        received_timestamp=when + timedelta(seconds=lag)))


def rules(version="test-1", **over):
    parts = dict(
        direction=DirectionRules(momentum_lookbacks=(1, 2), trend_min_abs_return=D("0.005"), range_max_abs_return=D("0.002")),
        volatility=VolatilityRules(high_min_realized_volatility=D("0.05")),
        liquidity=LiquidityRules(thin_min_spread_bps=D(50), depth_band_bps=D(100), thin_max_band_quote_depth=D(100),
                                 depth_quote_currency="USD"),
        flow=FlowRules(dominant_min_net_share=D("0.5")),
        liquidation=LiquidationRules(verified_sources=(VERIFIED,), window=timedelta(minutes=5)))
    parts.update(over)
    return MarketStateRules(rules_version=version, **parts)


def classify(r=None, *, liq_events=(), at=NOW, symbol="BTC", **reports):
    inputs = dict(liquidity=liquidity(), flow=flow(), derivatives=derivatives())
    inputs.update(reports)
    return classify_market_state(evaluation_time=at, symbol=symbol, rules=r or rules(), liquidations=tuple(liq_events), **inputs)


def fact(dimension, field):
    return next(f for f in dimension.facts if f.field == field)


# ------------------------------------------------------------------------ fact extraction
def test_all_dimensions_classify_from_trusted_reports_with_configured_rules():
    r = classify()
    assert (r.direction.state, r.volatility.state, r.liquidity.state, r.flow.state, r.funding.state) == (
        DirectionState.TRENDING_UP, VolatilityState.NOT_HIGH, LiquidityState.NOT_THIN, FlowState.BUY_DOMINANT,
        FundingPolarity.LONGS_PAY_SHORTS)
    assert r.regime.state == RegimeState.TRENDING_UP and r.regime.inputs_trusted
    assert r.crowding.state == CrowdingState.UNKNOWN
    assert r.liquidation.label == LiquidationLabel.UNKNOWN
    for dim in (r.direction, r.volatility, r.liquidity, r.flow, r.funding):
        assert dim.inputs_trusted and dim.reasons == ()


def test_facts_are_the_upstream_metrics_verbatim_with_their_real_windows():
    der, book, fl = derivatives(), liquidity(), flow()
    r = classify(derivatives=der, liquidity=book, flow=fl)
    for i, m in enumerate(der.candles.momentum):
        f = fact(r.direction, f"candles.momentum[{i}].simple_return")
        assert f.metric == m.simple_return and f.source == "C09.candles"
        # The k-bar return runs from the close of candle (latest - k) to the latest close.
        assert (f.window_kind, f.window_start, f.window_end) == (
            WindowKind.CLOSED_1H_CANDLES, LAST - (m.lookback_bars - 1) * HOUR, LAST + HOUR)
    assert fact(r.volatility, "candles.realized_volatility").metric == der.candles.realized_volatility
    assert fact(r.volatility, "candles.atr").metric == der.candles.atr
    spread = fact(r.liquidity, "spread_bps")
    assert spread.metric == book.spread_bps and spread.window_start == spread.window_end == book.snapshot_timestamp
    assert spread.window_kind == WindowKind.BOOK_SNAPSHOT
    assert fact(r.liquidity, "bands[0].bid_quote").metric == book.bands[0].bid_quote
    assert fact(r.liquidity, "bands[1].imbalance").metric == book.bands[1].imbalance
    net = fact(r.flow, "window_net_delta")
    assert net.metric == fl.window_net_delta and (net.window_start, net.window_end) == (fl.window_start, NOW)
    cvd = fact(r.flow, "session_cvd")
    assert cvd.window_kind == WindowKind.TRADE_SESSION and cvd.window_start == fl.session_start
    share = fact(r.flow, "window_net_delta / (window_buy_volume + window_sell_volume)")
    assert share.source == "C10.derived" and share.metric.value == D("0.5")
    latest = fact(r.funding, "funding.latest_rate")
    assert latest.metric == der.funding.latest_rate and latest.window_start == latest.window_end == FUND_LAST
    cumulative = fact(r.funding, "funding.cumulative_funding")
    assert (cumulative.window_start, cumulative.window_end) == (FUND_LAST - 3 * HOUR, FUND_LAST)
    assert r.funding.interval == "1h"


def test_source_references_keep_upstream_versions_quality_digests_and_reasons():
    der, book, fl = derivatives(), liquidity(), flow()
    r = classify(derivatives=der, liquidity=book, flow=fl)
    (candles,) = r.direction.sources
    assert candles.formula_version == "c09-derivatives-1"
    assert candles.input_digest == der.candles.provenance.input_digest
    assert candles.quality_policy_version == der.candles.quality.policy_version == "c09-hourly-freshness-1"
    assert candles.newest_provenance == der.candles.provenance.newest_record_provenance
    (funding,) = r.funding.sources
    assert funding.source == "C09.funding" and funding.input_digest == der.funding.provenance.input_digest
    (b,) = r.liquidity.sources
    assert (b.formula_version, b.newest_provenance, b.input_digest) == ("c07-liquidity-1", book.provenance, None)
    assert b.quality_state == book.quality.state and b.quality_policy_version == book.quality.policy_version
    (f,) = r.flow.sources
    assert f.input_digest == fl.provenance.input_digest and f.digest_algorithm == fl.provenance.digest_algorithm


# ---------------------------------------------------------------------- classifications
@pytest.mark.parametrize("values, state", [
    ((100, 101, 103, 104), DirectionState.TRENDING_UP),
    ((104, 103, 101, 100), DirectionState.TRENDING_DOWN),
    ((100, 100.1, 100, 100.1), DirectionState.RANGING),   # |returns| 0.001 and 0 are within the 0.002 band
])
def test_direction_states_from_momentum(values, state):
    r = classify(derivatives=derivatives(closes(values)))
    assert r.direction.state == state and r.regime.state == RegimeState(state.value)


def test_contradictory_momentum_is_unknown_and_both_facts_are_kept():
    r = classify(derivatives=derivatives(closes((100, 100, 110, 105))))  # 1 bar down, 2 bars up
    assert r.direction.state == DirectionState.UNKNOWN and r.direction.reasons == ("CONTRADICTORY_MOMENTUM",)
    signs = [fact(r.direction, f"candles.momentum[{i}].simple_return").metric.value for i in (0, 1)]
    assert signs[0] < 0 < signs[1]
    assert r.regime.state == RegimeState.UNKNOWN and "DIRECTION_UNKNOWN" in r.regime.reasons


def test_small_moves_of_either_sign_are_ranging_not_contradictory():
    r = classify(derivatives=derivatives(closes((100, 100, 100.1, 100.05))))  # -0.0005, +0.0005
    assert r.direction.state == DirectionState.RANGING


def test_between_the_range_band_and_trend_threshold_no_rule_matches():
    r = classify(derivatives=derivatives(closes((100, 100, 100, 100.3))))  # 0.003: neither band nor trend
    assert r.direction.state == DirectionState.UNKNOWN and r.direction.reasons == ("NO_DIRECTION_RULE_MATCHED",)


def test_a_zero_return_never_counts_as_trend():
    r = classify(derivatives=derivatives(closes((100, 101, 102, 102))))  # 0 then +0.0099
    assert r.direction.state == DirectionState.UNKNOWN and "NO_DIRECTION_RULE_MATCHED" in r.direction.reasons


def test_volatility_high_overrides_direction_in_the_composite_only():
    calm = rules(volatility=VolatilityRules(high_min_realized_volatility=D("0.001")))
    r = classify(calm)
    assert r.volatility.state == VolatilityState.HIGH and r.regime.state == RegimeState.HIGH_VOLATILITY
    assert r.direction.state == DirectionState.TRENDING_UP and r.regime.direction == DirectionState.TRENDING_UP


def test_liquidity_thin_by_wide_spread_or_shallow_band():
    wide = liquidity(bids=(("100", "2"), ("99.9", "3")), asks=(("101", "2"), ("101.1", "3")))  # ~99.5 bps
    assert classify(liquidity=wide).liquidity.state == LiquidityState.THIN
    shallow = liquidity(bids=(("100", "0.5"),), asks=(("100.1", "5"),))  # bid side 50 USD in band
    assert classify(liquidity=shallow).liquidity.state == LiquidityState.THIN
    assert classify().liquidity.state == LiquidityState.NOT_THIN


@pytest.mark.parametrize("trades, state", [
    (BALANCE_3_TO_1, FlowState.BUY_DOMINANT),
    ((trade("a", SELL, "3", ago=5), trade("b", BUY, "1", ago=1)), FlowState.SELL_DOMINANT),
    ((trade("a", SELL, "1", ago=5), trade("b", BUY, "1", ago=1)), FlowState.BALANCED),
])
def test_flow_states(trades, state):
    assert classify(flow=flow(trades)).flow.state == state


@pytest.mark.parametrize("rate, polarity", [("0.0001", FundingPolarity.LONGS_PAY_SHORTS),
                                            ("-0.0001", FundingPolarity.SHORTS_PAY_LONGS),
                                            ("0", FundingPolarity.ZERO)])
def test_funding_polarity_follows_the_documented_sign_with_no_threshold(rate, polarity):
    r = classify(derivatives=derivatives(fs=rates([rate] * 4)))
    assert r.funding.state == polarity and r.funding.thresholds == ()


# ----------------------------------------------------------------------------- boundaries
def _with(**kw):
    return rules(**kw)


def nudge(value, delta):
    with localcontext() as ctx:
        ctx.prec = 200
        return value + delta


def test_trend_threshold_boundary_is_inclusive():
    der = derivatives()
    smallest = min(m.simple_return.value for m in der.candles.momentum)
    tiny = D("1e-40")
    for t, state in ((nudge(smallest, -tiny), DirectionState.TRENDING_UP), (smallest, DirectionState.TRENDING_UP),
                     (nudge(smallest, tiny), DirectionState.UNKNOWN)):
        r = classify(_with(direction=DirectionRules(momentum_lookbacks=(1, 2), trend_min_abs_return=t)), derivatives=der)
        assert r.direction.state == state


def test_range_bound_boundary_is_inclusive():
    der = derivatives(closes((100, 100, 100.1, 100.15)))
    largest = max(m.simple_return.value.copy_abs() for m in der.candles.momentum)
    tiny = D("1e-40")
    for band, state in ((nudge(largest, tiny), DirectionState.RANGING), (largest, DirectionState.RANGING),
                        (nudge(largest, -tiny), DirectionState.UNKNOWN)):
        r = classify(_with(direction=DirectionRules(momentum_lookbacks=(1, 2), range_max_abs_return=band)), derivatives=der)
        assert r.direction.state == state


def test_volatility_threshold_boundary_is_inclusive():
    der = derivatives()
    rv = der.candles.realized_volatility.value
    tiny = D("1e-45")
    for t, state in ((nudge(rv, -tiny), VolatilityState.HIGH), (rv, VolatilityState.HIGH), (nudge(rv, tiny), VolatilityState.NOT_HIGH)):
        assert classify(_with(volatility=VolatilityRules(high_min_realized_volatility=t)), derivatives=der).volatility.state == state


def test_spread_and_depth_boundaries_are_inclusive():
    book = liquidity()
    spread = book.spread_bps.value
    tiny = D("1e-40")
    for t, state in ((nudge(spread, -tiny), LiquidityState.THIN), (spread, LiquidityState.THIN), (nudge(spread, tiny), LiquidityState.NOT_THIN)):
        assert classify(_with(liquidity=LiquidityRules(thin_min_spread_bps=t)), liquidity=book).liquidity.state == state
    depth = min(book.bands[0].bid_quote.value, book.bands[0].ask_quote.value)  # 499.7 USD on the bid side
    for t, state in ((nudge(depth, tiny), LiquidityState.THIN), (depth, LiquidityState.THIN), (nudge(depth, -tiny), LiquidityState.NOT_THIN)):
        lr = LiquidityRules(depth_band_bps=D(100), thin_max_band_quote_depth=t, depth_quote_currency="USD")
        assert classify(_with(liquidity=lr), liquidity=book).liquidity.state == state


def test_flow_share_boundary_is_exact_and_inclusive():
    tiny = D("1e-40")
    for share, state in ((nudge(D("0.5"), -tiny), FlowState.BUY_DOMINANT), (D("0.5"), FlowState.BUY_DOMINANT),
                         (nudge(D("0.5"), tiny), FlowState.BALANCED)):
        assert classify(_with(flow=FlowRules(dominant_min_net_share=share))).flow.state == state


# ------------------------------------------------------------------ unconfigured / missing
def test_without_thresholds_every_rule_is_unknown_but_facts_are_kept():
    r = classify(MarketStateRules(rules_version="facts-only"))
    for dim, name in ((r.direction, "direction"), (r.volatility, "volatility"), (r.liquidity, "liquidity"), (r.flow, "flow")):
        assert dim.state == "UNKNOWN" and f"THRESHOLD_NOT_CONFIGURED:{name}" in dim.reasons
        assert dim.inputs_trusted and dim.facts and dim.thresholds == ()
        assert all(f.metric.value is not None for f in dim.facts)
    assert r.funding.state == FundingPolarity.LONGS_PAY_SHORTS  # factual polarity needs no threshold
    assert r.regime.state == RegimeState.UNKNOWN
    assert "THRESHOLD_NOT_CONFIGURED:liquidation_window" in r.liquidation.reasons


def test_missing_reports_are_unknown_never_neutral():
    r = classify_market_state(evaluation_time=NOW, symbol="BTC", rules=rules())
    for dim, reason in ((r.direction, "C09_REPORT_NOT_PROVIDED"), (r.volatility, "C09_REPORT_NOT_PROVIDED"),
                        (r.liquidity, "C07_REPORT_NOT_PROVIDED"), (r.flow, "C08_REPORT_NOT_PROVIDED"),
                        (r.funding, "C09_REPORT_NOT_PROVIDED")):
        assert dim.state == "UNKNOWN" and dim.reasons == (reason,) and not dim.inputs_trusted and dim.facts == ()
    assert r.crowding.reasons[0] == "C09_REPORT_NOT_PROVIDED"
    assert r.regime.state == RegimeState.UNKNOWN and set(r.regime.reasons) == {"DIRECTION_UNKNOWN", "VOLATILITY_UNKNOWN"}
    assert not r.regime.inputs_trusted


def test_warming_up_and_unreported_lookbacks_are_unknown_with_upstream_reason():
    short = derivatives(closes((100, 101)), lookbacks=(1, 2))
    r = classify(derivatives=short)
    assert r.direction.state == DirectionState.UNKNOWN
    assert any(x.startswith("METRIC_UNAVAILABLE:momentum(lookback_bars=2):") for x in r.direction.reasons)
    assert fact(r.direction, "candles.momentum[1].simple_return").metric == short.candles.momentum[1].simple_return
    other = _with(direction=DirectionRules(momentum_lookbacks=(1, 3), trend_min_abs_return=D("0.005")))
    assert "MOMENTUM_LOOKBACK_NOT_IN_REPORT:lookback_bars=3" in classify(other).direction.reasons


# ------------------------------------------------------------- staleness and independent trust
def test_stale_candles_make_direction_volatility_and_regime_unknown_only():
    stale = derivatives(at=NOW + 3 * HOUR, fs=rates(["0.0001"] * 4, last=FUND_LAST + 3 * HOUR))
    late_book = liquidity(at=NOW + 3 * HOUR)
    late_flow = flow(at=NOW + 3 * HOUR, trades=(trade("x", BUY, "1", ago=-3 * 3600 + 1),))
    r = classify(at=NOW + 3 * HOUR, derivatives=stale, liquidity=late_book, flow=late_flow)
    assert not stale.candles.trusted_for_current_use and stale.funding.trusted_for_current_use
    assert r.direction.state == DirectionState.UNKNOWN and "C09.candles:NOT_TRUSTED" in r.direction.reasons
    assert r.direction.sources[0].upstream_reasons == stale.candles.reasons and not r.direction.inputs_trusted
    assert r.volatility.state == VolatilityState.UNKNOWN and r.regime.state == RegimeState.UNKNOWN
    # Other dimensions keep their own trust; nothing is borrowed in either direction.
    assert r.funding.state == FundingPolarity.LONGS_PAY_SHORTS and r.funding.inputs_trusted
    assert r.liquidity.inputs_trusted and r.flow.inputs_trusted and r.flow.state == FlowState.BUY_DOMINANT


def test_stale_book_withholds_liquidity_but_not_flow_or_direction():
    r = classify(liquidity=liquidity(age=60))
    assert r.liquidity.state == LiquidityState.UNKNOWN and "C07.book:NOT_TRUSTED" in r.liquidity.reasons
    assert r.liquidity.sources[0].quality_state.value == "STALE"
    assert fact(r.liquidity, "spread_bps").metric.value is None
    assert r.flow.state == FlowState.BUY_DOMINANT and r.direction.state == DirectionState.TRENDING_UP


def test_untrusted_flow_keeps_observable_facts_but_does_not_classify():
    late = (trade("t1", BUY, "3", ago=30, lag=20), trade("t2", SELL, "1", ago=1))  # retained late trade
    fl = flow(late)
    assert not fl.trusted_for_current_use and fl.window_net_delta.value is not None
    r = classify(flow=fl)
    assert r.flow.state == FlowState.UNKNOWN and "C08.flow:NOT_TRUSTED" in r.flow.reasons
    assert fact(r.flow, "window_net_delta").metric == fl.window_net_delta
    assert r.flow.sources[0].upstream_reasons == fl.reasons


def test_untrusted_funding_does_not_affect_candle_dimensions():
    der = derivatives(fs=rates(["0.0001"] * 4, last=FUND_LAST - 3 * HOUR))
    r = classify(derivatives=der)
    assert r.funding.state == FundingPolarity.UNKNOWN and "C09.funding:NOT_TRUSTED" in r.funding.reasons
    assert r.direction.state == DirectionState.TRENDING_UP and r.direction.inputs_trusted


# ------------------------------------------------------------------ point-in-time correctness
@pytest.mark.parametrize("which", ["liquidity", "flow", "derivatives"])
@pytest.mark.parametrize("shift", [timedelta(seconds=-1), timedelta(seconds=1)])
def test_reports_evaluated_at_another_time_are_rejected(which, shift):
    build = {"liquidity": liquidity, "flow": flow, "derivatives": derivatives}[which]
    with pytest.raises(ValueError, match="EVALUATION_TIME_MISMATCH"):
        classify(**{which: build(at=NOW + shift)})


def test_future_book_evidence_is_excluded_not_read():
    book = liquidity()
    future = book.model_copy(update={"snapshot_timestamp": NOW + MS})
    r = classify(liquidity=future)
    assert r.liquidity.state == LiquidityState.UNKNOWN and r.liquidity.reasons[0] == "C07.book:FUTURE_EVIDENCE_EXCLUDED"
    assert r.liquidity.facts == () and not r.liquidity.sources[0].trusted_for_current_use
    late_receipt = book.model_copy(update={"provenance": book.provenance.model_copy(update={"received_timestamp": NOW + MS})})
    assert classify(liquidity=late_receipt).liquidity.facts == ()


def test_future_trades_and_candles_are_excluded_not_read():
    fl = flow()
    tampered = fl.model_copy(update={"provenance": fl.provenance.model_copy(update={"latest_event_time": NOW + MS})})
    r = classify(flow=tampered)
    assert r.flow.state == FlowState.UNKNOWN and r.flow.facts == ()
    der = derivatives()
    unclosed = der.model_copy(update={"candles": der.candles.model_copy(update={"latest_start": LAST + HOUR})})
    r = classify(derivatives=unclosed)
    assert r.direction.facts == () and r.volatility.facts == ()
    assert r.direction.reasons[0] == "C09.candles:FUTURE_EVIDENCE_EXCLUDED"
    assert r.funding.state == FundingPolarity.LONGS_PAY_SHORTS  # the funding section stands on its own


def test_upstream_future_exclusion_carries_through_unchanged():
    future_trade = trade("f", SELL, "100", ago=-10)  # executes after NOW: C08 counts it, never reads it
    with_future = flow(BALANCE_3_TO_1 + (future_trade,))
    assert with_future.not_yet_received_count == 1
    assert classify(flow=with_future).flow.facts == classify(flow=flow()).flow.facts
    future_candle = closes(CLOSES + (50,), last=LAST + HOUR)  # the 12:00 candle closes after NOW
    assert classify(derivatives=derivatives(future_candle)).direction.facts == classify().direction.facts


def test_snapshot_age_is_graded_by_upstream_quality_not_shifted():
    r = classify(liquidity=liquidity(age=3))
    assert r.liquidity.inputs_trusted
    assert fact(r.liquidity, "spread_bps").window_start == NOW - timedelta(seconds=3)


# -------------------------------------------------------------- identity, units and versions
def test_symbol_mismatch_is_rejected():
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        classify(symbol="ETH")
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        classify(liq_events=(liq(symbol="ETH"),))


def test_conflicting_asserted_units_across_reports_are_rejected():
    with pytest.raises(ValueError, match="UNIT_IDENTITY_MISMATCH"):
        classify(liquidity=liquidity(quote="USDC"))
    with pytest.raises(ValueError, match="UNIT_IDENTITY_MISMATCH"):
        classify(flow=flow(base="XBT"))


def test_metric_unit_mismatch_is_unknown():
    lr = LiquidityRules(depth_band_bps=D(100), thin_max_band_quote_depth=D(100), depth_quote_currency="USDT")
    r = classify(_with(liquidity=lr))
    assert r.liquidity.state == LiquidityState.UNKNOWN
    assert {"UNIT_MISMATCH:band.bid_quote", "UNIT_MISMATCH:band.ask_quote"} <= set(r.liquidity.reasons)
    missing = LiquidityRules(depth_band_bps=D(150), thin_max_band_quote_depth=D(100), depth_quote_currency="USD")
    assert "BAND_NOT_IN_REPORT:150" in classify(_with(liquidity=missing)).liquidity.reasons


def test_unexpected_c09_metric_units_are_unknown_not_reinterpreted():
    der = derivatives()
    c = der.candles
    momentum = tuple(m.model_copy(update={"simple_return": m.simple_return.model_copy(update={"unit": "percent"})})
                     for m in c.momentum)
    vol = c.realized_volatility.model_copy(update={"unit": "annualized"})
    rate = der.funding.latest_rate.model_copy(update={"unit": "fraction per 8h"})
    tampered = der.model_copy(update={"candles": c.model_copy(update={"momentum": momentum, "realized_volatility": vol}),
                                      "funding": der.funding.model_copy(update={"latest_rate": rate})})
    r = classify(derivatives=tampered)
    assert r.direction.reasons == ("UNIT_MISMATCH:momentum(lookback_bars=1)", "UNIT_MISMATCH:momentum(lookback_bars=2)")
    assert r.volatility.reasons == ("UNIT_MISMATCH:realized_volatility",)
    assert r.funding.reasons == ("UNIT_MISMATCH:funding.latest_rate",)


@pytest.mark.parametrize("which, build", [("liquidity", liquidity), ("flow", flow), ("derivatives", derivatives)])
def test_unsupported_formula_versions_are_rejected(which, build):
    with pytest.raises(ValueError, match="UNSUPPORTED_FORMULA_VERSION"):
        classify(**{which: build().model_copy(update={"formula_version": "future-2"})})


def test_validation_bypassed_reports_and_wrong_types_are_rejected():
    der = derivatives()
    forged = der.model_copy(update={"open_interest": der.open_interest.model_copy(update={"value": D(1)})})
    with pytest.raises(ValidationError):
        classify(derivatives=forged)
    with pytest.raises(ValueError):
        classify(derivatives=liquidity())
    with pytest.raises(ValueError):
        classify_market_state(evaluation_time=NOW, symbol="BTC", rules=rules().model_dump())
    with pytest.raises(ValueError):
        classify_market_state(evaluation_time=NOW.replace(tzinfo=None), symbol="BTC", rules=rules())
    with pytest.raises(ValueError):
        classify_market_state(evaluation_time=NOW, symbol="BTC", rules=rules(), liquidations=[liq()])


@pytest.mark.parametrize("build", [
    lambda: DirectionRules(momentum_lookbacks=(1, 2), trend_min_abs_return=D("0.01"), range_max_abs_return=D("0.01")),
    lambda: DirectionRules(trend_min_abs_return=D("0.01")),
    lambda: DirectionRules(momentum_lookbacks=(2, 1), trend_min_abs_return=D("0.01")),
    lambda: DirectionRules(momentum_lookbacks=(1,), trend_min_abs_return=D(0)),
    lambda: VolatilityRules(high_min_realized_volatility=D("-0.1")),
    lambda: VolatilityRules(high_min_realized_volatility=D("NaN")),
    lambda: LiquidityRules(depth_band_bps=D(100)),
    lambda: FlowRules(dominant_min_net_share=D("1.5")),
    lambda: LiquidationRules(window=timedelta(0)),
    lambda: LiquidationRules(verified_sources=(VERIFIED, VERIFIED)),
    lambda: MarketStateRules(rules_version=""),
    lambda: MarketStateRules(rules_version="v1", calibration_status="CALIBRATED"),
])
def test_invalid_rules_are_rejected_not_defaulted(build):
    with pytest.raises(ValidationError):
        build()


# -------------------------------------------------------------------- crowding and funding
@pytest.mark.parametrize("rate", ["0.04", "-0.04", "0.0001", "0"])
def test_funding_polarity_never_produces_a_crowding_label(rate):
    r = classify(derivatives=derivatives(fs=rates([rate] * 4)))
    assert r.crowding.state == CrowdingState.UNKNOWN and not r.crowding.inputs_trusted
    assert set(r.crowding.reasons) == {"OPEN_INTEREST_UNAVAILABLE", "BASIS_UNAVAILABLE",
                                       "FUNDING_POLARITY_IS_NOT_POSITIONING_EVIDENCE"}
    oi = fact(r.crowding, "open_interest").metric
    assert oi.value is None and oi.reason == "OPEN_INTEREST_UNVERIFIED_UNIT_AGGREGATION_AND_TIMING"
    assert [s.value for s in CrowdingState] == ["UNKNOWN"]


# ------------------------------------------------------------------------- liquidation truth
def heuristic_extremes():
    dump = tuple(trade(f"s{i}", SELL, "50", ago=5 - i) for i in range(5))   # one-sided aggressive selling
    thin = liquidity(bids=(("99.6", "0.01"),), asks=(("100.4", "0.01"),))  # 80 bps wide, 1 USD deep
    return dict(flow=flow(dump), liquidity=thin)


def test_heuristic_pressure_inputs_never_produce_an_authoritative_label():
    r = classify(**heuristic_extremes())
    assert r.flow.state == FlowState.SELL_DOMINANT and r.liquidity.state == LiquidityState.THIN
    assert r.liquidation.label == LiquidationLabel.UNKNOWN and r.liquidation.authoritative_events == ()
    assert r.liquidation.heuristic_pressure == "NOT_ACTIVATED"
    assert "HEURISTIC_LIQUIDATION_PRESSURE_NOT_ACTIVATED" in r.liquidation.reasons
    assert "NO_VERIFIED_LIQUIDATION_EVENT_ABSENCE_NOT_PROVEN" in r.liquidation.reasons


def test_verified_events_are_authoritative_and_independent_of_flow_and_liquidity():
    events = (liq("L2", ago=20), liq("L1", ago=10))
    plain = classify(liq_events=events)
    extreme = classify(liq_events=events, **heuristic_extremes())
    absent = classify_market_state(evaluation_time=NOW, symbol="BTC", rules=rules(), liquidations=events)
    assert plain.liquidation == extreme.liquidation == absent.liquidation
    assert plain.liquidation.label == LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT
    assert [e.provenance.source_id for e in plain.liquidation.authoritative_events] == ["L2", "L1"]
    assert plain.liquidation.window_start == NOW - timedelta(minutes=5)


@pytest.mark.parametrize("event, reason", [
    (liq(source="some-feed"), "LIQUIDATION_SOURCE_NOT_VERIFIED:1"),
    (liq(source_type="public_info"), "LIQUIDATION_SOURCE_NOT_VERIFIED:1"),
    (liq(sid=None), "LIQUIDATION_POINT_IN_TIME_PROVENANCE_INCOMPLETE:1"),
    (liq(source_ts=False), "LIQUIDATION_POINT_IN_TIME_PROVENANCE_INCOMPLETE:1"),
    (liq(ago=300), "LIQUIDATION_OUTSIDE_WINDOW:1"),
])
def test_unverifiable_or_out_of_window_events_fail_closed(event, reason):
    r = classify(liq_events=(event,))
    assert r.liquidation.label == LiquidationLabel.UNKNOWN and reason in r.liquidation.reasons


def test_window_boundary_and_future_receipt():
    inside = classify(liq_events=(liq(ago=299.999),)).liquidation
    assert inside.label == LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT
    later = classify(liq_events=(liq(ago=1, lag=2),)).liquidation  # received 1 s after NOW
    assert later.label == LiquidationLabel.UNKNOWN and later.not_yet_received_count == 1
    assert later.supplied_count == 1 and later.authoritative_events == ()


def test_no_window_configured_accepts_nothing():
    r = classify(_with(liquidation=LiquidationRules(verified_sources=(VERIFIED,))), liq_events=(liq(),))
    assert r.liquidation.label == LiquidationLabel.UNKNOWN and r.liquidation.window_start is None
    assert "THRESHOLD_NOT_CONFIGURED:liquidation_window" in r.liquidation.reasons


def test_duplicate_events_count_once_and_conflicts_fail_closed():
    a, b = liq("L1", lag=1), liq("L1", lag=3)
    ctx = classify(liq_events=(b, a)).liquidation
    assert ctx.duplicate_count == 1 and ctx.authoritative_events == (a,)
    conflict = classify(liq_events=(liq("L1"), liq("L1", qty="2"), liq("L9"))).liquidation
    assert conflict.label == LiquidationLabel.UNKNOWN and "CONFLICTING_LIQUIDATION_IDENTITY" in conflict.reasons


def test_report_cannot_carry_an_unearned_liquidation_label():
    r = classify()
    for label in (LiquidationLabel.HEURISTIC_LIQUIDATION_PRESSURE, LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT):
        data = r.model_dump()
        data["liquidation"]["label"] = label
        with pytest.raises(ValidationError):
            MarketStateReport.model_validate(data)


# ------------------------------------------------------------------------------ composite
def test_composite_is_unknown_whenever_a_component_is_unknown():
    no_vol = classify(_with(volatility=VolatilityRules()))
    assert no_vol.direction.state == DirectionState.TRENDING_UP
    assert no_vol.regime.state == RegimeState.UNKNOWN and no_vol.regime.reasons == ("VOLATILITY_UNKNOWN",)
    contradictory = classify(_with(volatility=VolatilityRules(high_min_realized_volatility=D("0.0001"))),
                             derivatives=derivatives(closes((100, 100, 110, 105))))
    assert contradictory.volatility.state == VolatilityState.HIGH
    assert contradictory.regime.state == RegimeState.UNKNOWN  # high volatility does not conceal contradiction


def test_composite_ignores_liquidity_flow_and_funding():
    base = classify()
    other = classify(**heuristic_extremes(), derivatives=derivatives(fs=rates(["-0.04"] * 4)))
    assert base.regime == other.regime


def test_report_rejects_inconsistent_composite_or_dimension_claims():
    r = classify()
    data = r.model_dump()
    data["regime"]["state"] = RegimeState.RANGING
    with pytest.raises(ValidationError):
        MarketStateReport.model_validate(data)
    data = classify(liquidity=liquidity(age=60)).model_dump()
    data["liquidity"]["state"], data["liquidity"]["reasons"] = LiquidityState.NOT_THIN, ()
    with pytest.raises(ValidationError):
        MarketStateReport.model_validate(data)   # untrusted input cannot carry a classification
    data = r.model_dump()
    data["flow"]["sources"][0]["trusted_for_current_use"] = True
    data["flow"]["sources"][0]["upstream_trusted"] = False
    with pytest.raises(ValidationError):
        MarketStateReport.model_validate(data)


# --------------------------------------------------------------------- versioning / digests
def test_rules_identity_tracks_version_and_every_threshold():
    base = rules()
    assert rules_digest(base) == rules_digest(rules()) == classify(base).rules_digest
    assert rules_digest(rules(version="test-2")) != rules_digest(base)
    changed = rules(flow=FlowRules(dominant_min_net_share=D("0.6")))
    assert rules_digest(changed) != rules_digest(base)
    window = rules(liquidation=LiquidationRules(verified_sources=(VERIFIED,), window=timedelta(minutes=6)))
    assert rules_digest(window) != rules_digest(base)
    same_value = rules(flow=FlowRules(dominant_min_net_share=D("0.50")))
    assert rules_digest(same_value) == rules_digest(base)


def test_report_is_bound_to_its_rules_and_versions():
    r = classify()
    assert r.engine_version == "c10-market-state-1" and r.rules.calibration_status == "UNCALIBRATED"
    assert "THRESHOLDS_UNCALIBRATED_CALLER_CONFIGURED" in r.limitations
    data = r.model_dump()
    data["rules"]["rules_version"] = "other"
    with pytest.raises(ValidationError):
        MarketStateReport.model_validate(data)


# --------------------------------------------------------------------------- determinism
def test_ordering_ambient_decimal_context_and_serialization_are_stable():
    events = [liq(f"L{i}", ago=10 + i) for i in range(6)] + [liq("L0", lag=4)]
    baseline = classify(liq_events=tuple(events)).model_dump_json()
    rng = random.Random(10)
    for _ in range(5):
        rng.shuffle(events)
        assert classify(liq_events=tuple(events)).model_dump_json() == baseline
    reports = dict(liquidity=liquidity(), flow=flow(), derivatives=derivatives())
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 3, ROUND_DOWN
        assert classify(liq_events=tuple(events), **reports).model_dump_json() == baseline
    restored = MarketStateReport.model_validate_json(baseline)
    assert restored.model_dump_json() == baseline
    with pytest.raises(ValidationError):
        restored.symbol = "ETH"


def test_engine_has_no_clock_network_or_randomness():
    source = inspect.getsource(engine)
    for banned in ("datetime.now", "utcnow", "time.time", "random", "requests", "urllib", "socket", "httpx"):
        assert banned not in source


# ---------------------------------------------------------------------------- transitions
def test_sequential_evaluations_transition_from_point_in_time_evidence_only():
    # Hourly closes; every evaluation sees the same full input and C09 drops what is not yet known.
    first = datetime(2026, 10, 15, 0, tzinfo=UTC)
    series = (100, 100.1, 100, 100.1, 101, 102, 101, 99, 100.5)
    cs = tuple(candle(first + i * HOUR, v) for i, v in enumerate(series))
    fs = tuple(fund(first + i * HOUR, "0.0001") for i in range(len(series) + 1))
    expected = {3: DirectionState.RANGING, 5: DirectionState.TRENDING_UP, 6: DirectionState.UNKNOWN,
                7: DirectionState.TRENDING_DOWN, 8: DirectionState.UNKNOWN}
    seen = []
    for i, state in expected.items():
        at = first + (i + 1) * HOUR + timedelta(minutes=5)
        der = derivatives(cs, fs, at=at)
        r = classify_market_state(evaluation_time=at, symbol="BTC", rules=rules(), derivatives=der)
        assert r.direction.state == state, (i, r.direction.reasons)
        assert r.regime.state == (RegimeState(state.value) if state != DirectionState.UNKNOWN else RegimeState.UNKNOWN)
        seen.append(r.direction.reasons)
    assert seen[2] == ("NO_DIRECTION_RULE_MATCHED",) and seen[4] == ("CONTRADICTORY_MOMENTUM",)


# =============================================== audit regressions: internal timestamp consistency
INCONSISTENT = "INTERNALLY_INCONSISTENT:"


def excluded(dim, source, problem=None):
    """The dimension read nothing from an internally inconsistent source."""
    (ref,) = dim.sources
    assert ref.source == source and ref.excluded_reason.startswith(INCONSISTENT), ref.excluded_reason
    if problem is not None:
        assert ref.excluded_reason == INCONSISTENT + problem
    assert dim.state == "UNKNOWN" and dim.facts == () and not dim.inputs_trusted and not ref.trusted_for_current_use
    assert dim.reasons[0] == f"{source}:{ref.excluded_reason}"
    return ref


def consistent(dim):
    assert all(s.excluded_reason is None for s in dim.sources), [s.excluded_reason for s in dim.sources]


def _old(prov, when):
    return prov.model_copy(update={"source_timestamp": when, "received_timestamp": when})


def test_ten_day_old_book_presented_as_live_is_excluded():
    book = liquidity()
    old = NOW - timedelta(days=10)
    forged = book.model_copy(update={"snapshot_timestamp": old, "provenance": _old(book.provenance, old)})
    assert forged.quality.trusted_for_current_use and forged.spread_bps.value is not None
    r = classify(liquidity=forged)
    excluded(r.liquidity, "C07.book", "QUALITY_CONTRADICTS_EVIDENCE")
    assert r.liquidity.state == LiquidityState.UNKNOWN
    assert r.flow.state == FlowState.BUY_DOMINANT  # only the inconsistent report is withheld


@pytest.mark.parametrize("forge, problem", [
    (lambda b: b.model_copy(update={"snapshot_timestamp": NOW - timedelta(days=10)}),
     "SNAPSHOT_TIME_NOT_PROVENANCE_SOURCE_TIME"),
    (lambda b: b.model_copy(update={"provenance": _old(b.provenance, NOW - timedelta(seconds=6)),
                                    "snapshot_timestamp": NOW - timedelta(seconds=6)}),
     "QUALITY_CONTRADICTS_EVIDENCE"),   # 6 s is DELAYED under C05, yet LIVE is claimed
    (lambda b: b.model_copy(update={"quality": b.quality.model_copy(update={"capability": Capability.TRADES})}),
     "QUALITY_CAPABILITY_MISMATCH"),
    (lambda b: b.model_copy(update={"quality": b.quality.model_copy(update={"policy_version": "other"})}),
     "QUALITY_POLICY_NOT_REPRODUCIBLE"),
])
def test_book_contradictions_fail_closed(forge, problem):
    excluded(classify(liquidity=forge(liquidity())).liquidity, "C07.book", problem)


def test_degraded_book_with_numbers_restored_is_excluded():
    stale, good = liquidity(age=60), liquidity()
    forged = stale.model_copy(update={"spread_bps": good.spread_bps})
    excluded(classify(liquidity=forged).liquidity, "C07.book", "VALUES_PRESENT_WITHOUT_TRUSTED_QUALITY")
    forged = stale.model_copy(update={"quality": good.quality})  # fresh label on stale evidence
    excluded(classify(liquidity=forged).liquidity, "C07.book", "QUALITY_CONTRADICTS_EVIDENCE")


@pytest.mark.parametrize("age", [0, 3, 5, 6, 15, 16, 60])
@pytest.mark.parametrize("status", [dict(), dict(continuity=ContinuityStatus.UNKNOWN),
                                    dict(recovery=RecoveryStatus.RECOVERING),
                                    dict(coverage=CapabilityCoverage(Capability.ORDER_BOOK, CapabilityAvailability.LIMITED, "partial"))])
def test_legitimate_books_of_any_age_and_status_are_consistent(age, status):
    book = liquidity(age=age, **status)
    r = classify(liquidity=book)
    consistent(r.liquidity)
    assert r.liquidity.inputs_trusted == book.quality.trusted_for_current_use
    assert (r.liquidity.state != LiquidityState.UNKNOWN) == book.quality.trusted_for_current_use


def test_custom_c05_policy_must_be_supplied_to_be_reproduced():
    from traid.quality import FreshnessThreshold, QualityPolicy
    custom = QualityPolicy(policy_version="custom-1", thresholds=tuple(
        FreshnessThreshold(capability=c, live_max_age=timedelta(seconds=60), delayed_max_age=timedelta(seconds=120))
        for c in (Capability.ORDER_BOOK, Capability.TRADES)))
    book, fl = liquidity(age=30, policy=custom), flow(policy=custom)
    r = classify(liquidity=book, flow=fl)
    excluded(r.liquidity, "C07.book", "QUALITY_POLICY_NOT_REPRODUCIBLE")
    excluded(r.flow, "C08.flow", "QUALITY_POLICY_NOT_REPRODUCIBLE")
    r = classify(liquidity=book, flow=fl, quality_policy=custom)
    consistent(r.liquidity)
    assert r.liquidity.state == LiquidityState.NOT_THIN and r.flow.state == FlowState.BUY_DOMINANT
    same_version = custom.model_copy(update={"policy_version": default_quality_policy().policy_version})
    forged = liquidity(age=30, policy=same_version)  # LIVE only under the undisclosed thresholds
    excluded(classify(liquidity=forged).liquidity, "C07.book", "QUALITY_CONTRADICTS_EVIDENCE")
    with pytest.raises(ValueError):
        classify(quality_policy=custom.model_dump())


def _shift_flow(fl, when):
    p = fl.provenance
    newest = p.newest_trade_provenance.model_copy(update={"source_timestamp": when, "received_timestamp": when})
    return p.model_copy(update={"earliest_event_time": when, "latest_event_time": when, "newest_trade_provenance": newest})


@pytest.mark.parametrize("forge, problem", [
    # trades an hour before the declared 60 s window still reported as a dominant current window
    (lambda f: f.model_copy(update={"provenance": _shift_flow(f, NOW - HOUR)}), "TRADES_OUTSIDE_REPORTED_RANGE"),
    (lambda f: f.model_copy(update={"provenance": f.provenance.model_copy(update={"latest_trade_id": "t1"})}),
     "NEWEST_TRADE_PROVENANCE_MISMATCH"),
    (lambda f: f.model_copy(update={"provenance": f.provenance.model_copy(update={"latest_event_time": NOW - timedelta(seconds=120)})}),
     "TRADES_OUTSIDE_REPORTED_RANGE"),   # newest before earliest
    (lambda f: f.model_copy(update={"provenance": _shift_flow(f, NOW - timedelta(seconds=120))}),
     "AGGREGATES_WITHOUT_TRADES_IN_THEIR_WINDOW"),   # inside the session, outside the window
    (lambda f: f.model_copy(update={"window_start": NOW - HOUR}), "WINDOW_START_NOT_EVALUATION_MINUS_WINDOW"),
    (lambda f: f.model_copy(update={"session_start": NOW - HOUR}), "SESSION_START_NOT_CONFIGURED_SESSION"),
    (lambda f: f.model_copy(update={"window_trade_count": 0}), "AGGREGATES_WITHOUT_TRADES_IN_THEIR_WINDOW"),
    (lambda f: f.model_copy(update={"window_trade_count": 99}), "AGGREGATES_WITHOUT_TRADES_IN_THEIR_WINDOW"),
    (lambda f: f.model_copy(update={"provenance": _shift_flow(f, NOW - timedelta(seconds=10))}),
     "QUALITY_CONTRADICTS_EVIDENCE"),   # newest trade 10 s old is not LIVE, yet LIVE is claimed
    (lambda f: f.model_copy(update={"provenance": None, "trusted_for_current_use": False, "reasons": ("X",),
                                    **{k: getattr(f, k).model_copy(update={"value": None, "reason": "X"}) for k in (
                                        "window_buy_volume", "window_sell_volume", "window_net_delta",
                                        "session_buy_volume", "session_sell_volume", "session_cvd")}}),
     "QUALITY_PROVENANCE_PRESENCE_MISMATCH"),   # an assessment with no record behind it
])
def test_flow_contradictions_fail_closed(forge, problem):
    fl = flow()
    assert classify(flow=fl).flow.state == FlowState.BUY_DOMINANT
    r = classify(flow=forge(fl))
    excluded(r.flow, "C08.flow", problem)
    assert r.flow.state == FlowState.UNKNOWN


def test_stale_flow_relabelled_trusted_is_excluded():
    stale, good = flow((trade("a", BUY, "3", ago=40), trade("b", SELL, "1", ago=30))), flow()
    assert not stale.trusted_for_current_use
    forged = stale.model_copy(update={k: getattr(good, k) for k in (
        "quality", "trusted_for_current_use", "reasons", "window_buy_volume", "window_sell_volume", "window_net_delta",
        "session_buy_volume", "session_sell_volume", "session_cvd", "window_trade_count", "session_trade_count")})
    excluded(classify(flow=forged).flow, "C08.flow")


@pytest.mark.parametrize("trades", [
    BALANCE_3_TO_1,
    (trade("t1", BUY, "3", ago=30, lag=20), trade("t2", SELL, "1", ago=1)),     # late trade retained
    (trade("t1", BUY, "3", ago=200), trade("t2", SELL, "1", ago=100)),          # stale, session only
    (trade("t1", BUY, "3", ago=2), trade("t2", SELL, "1", ago=1)),
    (trade("t1", BUY, "3", ago=8),),                                             # DELAYED newest trade
    (),                                                                          # no trades at all
    (trade("t1", None, "3", ago=1),),                                            # blocking: side unknown
])
@pytest.mark.parametrize("status", [dict(), dict(continuity=ContinuityStatus.UNKNOWN),
                                    dict(recovery=RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF)])
def test_legitimate_flow_reports_are_consistent(trades, status):
    fl = flow(trades, **status)
    r = classify(flow=fl)
    consistent(r.flow)
    assert r.flow.inputs_trusted == fl.trusted_for_current_use


def _shift_section(section, **update):
    return section.model_copy(update=update)


def test_stale_candles_presented_as_current_are_excluded():
    stale, good = derivatives(closes(CLOSES, last=LAST - 5 * HOUR)), derivatives()
    assert not stale.candles.trusted_for_current_use and good.candles.trusted_for_current_use
    fresh_claims = {k: getattr(good.candles, k) for k in (
        "quality", "trusted_for_current_use", "reasons", "bars_behind", "atr", "realized_volatility", "vwap",
        "vwap_session_volume", "momentum")}
    forged = stale.model_copy(update={"candles": _shift_section(stale.candles, latest_start=LAST, **fresh_claims)})
    r = classify(derivatives=forged)
    excluded(r.direction, "C09.candles", "LATEST_START_NOT_PROVENANCE_TIME")
    excluded(r.volatility, "C09.candles", "LATEST_START_NOT_PROVENANCE_TIME")
    assert r.regime.state == RegimeState.UNKNOWN
    p = stale.candles.provenance
    forged_p = p.model_copy(update={"latest_time": LAST})   # receipt still five hours old
    forged = stale.model_copy(update={"candles": _shift_section(stale.candles, latest_start=LAST, provenance=forged_p, **fresh_claims)})
    excluded(classify(derivatives=forged).direction, "C09.candles", "LATEST_CANDLE_NOT_CLOSED_AT_RECEIPT")
    forged = stale.model_copy(update={"candles": _shift_section(stale.candles, **fresh_claims)})
    excluded(classify(derivatives=forged).direction, "C09.candles", "INTERVALS_BEHIND_CONTRADICT_EVIDENCE")
    claims = dict(fresh_claims, bars_behind=stale.candles.bars_behind)
    forged = stale.model_copy(update={"candles": _shift_section(stale.candles, **claims)})
    excluded(classify(derivatives=forged).direction, "C09.candles", "QUALITY_CONTRADICTS_EVIDENCE")


def test_stale_funding_presented_as_current_is_excluded():
    stale, good = derivatives(fs=rates(["0.0001"] * 4, last=FUND_LAST - 3 * HOUR)), derivatives()
    claims = {k: getattr(good.funding, k) for k in (
        "quality", "trusted_for_current_use", "reasons", "bars_behind", "latest_rate", "cumulative_funding",
        "mean_hourly_funding")}
    forged = stale.model_copy(update={"funding": _shift_section(stale.funding, latest_start=FUND_LAST, **claims)})
    r = classify(derivatives=forged)
    excluded(r.funding, "C09.funding", "LATEST_START_NOT_PROVENANCE_TIME")
    assert r.direction.state == DirectionState.TRENDING_UP   # the candle section is consistent on its own
    claims["bars_behind"] = stale.funding.bars_behind
    forged = stale.model_copy(update={"funding": _shift_section(stale.funding, **claims)})
    excluded(classify(derivatives=forged).funding, "C09.funding", "QUALITY_CONTRADICTS_EVIDENCE")
    forged = good.model_copy(update={"funding": _shift_section(good.funding, latest_start=FUND_LAST + timedelta(minutes=1))})
    assert classify(derivatives=forged).funding.sources[0].excluded_reason is not None


def test_c09_values_without_trusted_quality_are_excluded():
    stale, good = derivatives(closes(CLOSES, last=LAST - 5 * HOUR)), derivatives()
    forged = stale.model_copy(update={"candles": _shift_section(stale.candles, atr=good.candles.atr)})
    excluded(classify(derivatives=forged).volatility, "C09.candles", "VALUES_PRESENT_WITHOUT_TRUSTED_QUALITY")


@pytest.mark.parametrize("build", [
    lambda: derivatives(),
    lambda: derivatives(at=NOW + HOUR, fs=rates(["0.0001"] * 4, last=FUND_LAST + HOUR)),   # candles DELAYED
    lambda: derivatives(closes(CLOSES, last=LAST - 5 * HOUR)),                            # candles STALE
    lambda: derivatives(closes((100, 101))),                                              # warming up
    lambda: derivatives(closes((100, 101, 102)) + (candle(LAST - 4 * HOUR, 99),)),       # gap in lookback
    lambda: derivatives(closes(CLOSES), ()),                                              # no funding
    lambda: derivatives(at=NOW + timedelta(minutes=50)),                                  # late in the hour
    lambda: derivatives(continuity=ContinuityStatus.UNKNOWN),
    lambda: derivatives(recovery=RecoveryStatus.RECOVERING),
    lambda: derivatives(candle_coverage=CapabilityCoverage(Capability.CANDLES, CapabilityAvailability.LIMITED, "partial")),
    lambda: derivatives(closes(CLOSES) + (candle(LAST, 999),)),                           # conflicting duplicate
])
def test_legitimate_derivatives_reports_are_consistent(build):
    der = build()
    at = der.evaluation_time
    r = classify_market_state(evaluation_time=at, symbol="BTC", rules=rules(), derivatives=der)
    consistent(r.direction)
    consistent(r.funding)
    assert r.direction.inputs_trusted == der.candles.trusted_for_current_use
    assert r.funding.inputs_trusted == der.funding.trusted_for_current_use


# ==================================================== audit regressions: deterministic deduplication
WS_AND_INFO = (VerifiedLiquidationSource(source="verified-feed", source_type="public_info"), VERIFIED)


def test_equal_values_in_different_decimal_spellings_serialize_identically_in_any_order():
    import itertools
    variants = [liq("L1", price="100"), liq("L1", price="100.0"), liq("L1", price="1E+2"),
                liq("L1", price="100.00", source_type="public_info"),   # tied receipt, other transport
                liq("L1", price="100", lag=3),                           # later receipt
                liq("L2", ago=20, qty="2"), liq("L2", ago=20, qty="2.000")]
    r = rules(liquidation=LiquidationRules(verified_sources=WS_AND_INFO, window=timedelta(minutes=5)))
    outputs = {classify_market_state(evaluation_time=NOW, symbol="BTC", rules=r, liquidations=perm).model_dump_json()
               for perm in itertools.permutations(variants)}
    assert len(outputs) == 1
    ctx = MarketStateReport.model_validate_json(outputs.pop()).liquidation
    assert ctx.label == LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT and ctx.duplicate_count == 5
    assert [e.provenance.source_id for e in ctx.authoritative_events] == ["L2", "L1"]
    with localcontext() as c:
        c.prec, c.rounding = 2, ROUND_DOWN
        again = classify_market_state(evaluation_time=NOW, symbol="BTC", rules=r, liquidations=tuple(reversed(variants)))
    assert again.liquidation == ctx


def test_distinct_events_are_not_merged_and_real_conflicts_still_fail_closed():
    same_content = classify(liq_events=(liq("A"), liq("B"))).liquidation
    assert len(same_content.authoritative_events) == 2 and same_content.duplicate_count == 0
    spelling = classify(liq_events=(liq("A", qty="1"), liq("A", qty="1.00"))).liquidation
    assert spelling.label == LiquidationLabel.AUTHORITATIVE_LIQUIDATION_EVENT and spelling.duplicate_count == 1
    conflict = classify(liq_events=(liq("A", qty="1"), liq("A", qty="1.01"))).liquidation
    assert conflict.label == LiquidationLabel.UNKNOWN and "CONFLICTING_LIQUIDATION_IDENTITY" in conflict.reasons


# ======================================================== audit regressions: future events first
def _without_counters(report):
    data = report.model_dump(mode="json")
    data["liquidation"].pop("supplied_count")
    data["liquidation"].pop("not_yet_received_count")
    return data


def _future(**fields):
    """A record received after NOW; its content may be invalid or for another market."""
    when = NOW + timedelta(seconds=5)
    values = dict(symbol="BTC", price=D(100), quantity=D(1), timestamp=when, schema_version="1.0",
                  provenance=SourceProvenance(source="verified-feed", source_type="public_websocket", source_id="F",
                                              source_timestamp=when, received_timestamp=when))
    values.update(fields)
    return LiquidationEvent.model_construct(**values)


@pytest.mark.parametrize("known", [(), (liq("L1"),)])
def test_future_received_events_cannot_change_an_earlier_report(known):
    baseline = classify(liq_events=known)
    unknowable = (_future(symbol="ETH"), _future(quantity=D(-5)), _future(price=D(0)),
                  _future(), _future(), _future(quantity=D(7)),          # duplicate and conflicting
                  _future(source_id="L1", quantity=D(9)))                # would conflict with a known event
    r = classify(liq_events=known + unknowable)
    assert _without_counters(r) == _without_counters(baseline)
    assert r.liquidation.supplied_count == len(known) + 7 and r.liquidation.not_yet_received_count == 7


def test_once_received_the_same_records_are_fully_validated():
    later = NOW + timedelta(seconds=5)
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        classify_market_state(evaluation_time=later, symbol="BTC", rules=rules(), liquidations=(_future(symbol="ETH"),))
    with pytest.raises(ValidationError):
        classify_market_state(evaluation_time=later, symbol="BTC", rules=rules(), liquidations=(_future(quantity=D(-5)),))
    ctx = classify_market_state(evaluation_time=later, symbol="BTC", rules=rules(),
                                liquidations=(_future(), _future(quantity=D(7)))).liquidation
    assert "CONFLICTING_LIQUIDATION_IDENTITY" in ctx.reasons and ctx.label == LiquidationLabel.UNKNOWN


@pytest.mark.parametrize("provenance", [
    None,
    {"received_timestamp": NOW},
    SourceProvenance.model_construct(source="verified-feed", source_type="public_websocket", source_id="F",
                                     source_timestamp=None, received_timestamp=NOW.replace(tzinfo=None)),
    SourceProvenance.model_construct(source="verified-feed", source_type="public_websocket", source_id="F",
                                     source_timestamp=None, received_timestamp="2026-10-15T12:05:00Z"),
    SourceProvenance.model_construct(source="verified-feed", source_type="public_websocket", source_id="F"),
])
def test_malformed_or_missing_receipt_times_are_rejected_not_skipped(provenance):
    with pytest.raises(ValueError):
        classify(liq_events=(_future(provenance=provenance),))


# ============================================================ audit regressions: evidence selectors
def resolve(root, path):
    obj = root
    for part in path.split("."):
        name, _, index = part.partition("[")
        obj = getattr(obj, name)
        if index:
            obj = obj[int(index.rstrip("]"))]
    return obj


@pytest.mark.parametrize("lookbacks", [(1, 2), (1, 3, 6), (2, 5)])
def test_every_fact_selector_resolves_to_its_original_metric(lookbacks):
    cs = closes((100, 101, 103, 104, 102, 105, 106, 108))
    der, book, fl = derivatives(cs, lookbacks=lookbacks), liquidity(), flow()
    roots = {"C07.book": book, "C08.flow": fl, "C09.candles": der, "C09.funding": der, "C09": der}
    r = classify(_with(direction=DirectionRules(momentum_lookbacks=lookbacks, trend_min_abs_return=D("0.001"))),
                 derivatives=der, liquidity=book, flow=fl)
    checked = 0
    for dim in (r.direction, r.volatility, r.liquidity, r.flow, r.funding, r.crowding):
        for f in dim.facts:
            if f.source == "C10.derived":
                continue
            assert resolve(roots[f.source], f.field) == f.metric, f.field
            checked += 1
    assert checked == len(lookbacks) + 2 + (1 + 3 * len(book.bands)) + 4 + 3 + 2
    for i, k in enumerate(lookbacks):
        f = fact(r.direction, f"candles.momentum[{i}].simple_return")
        assert resolve(der, f"candles.momentum[{i}]").lookback_bars == k
        assert f.window_start == LAST - (k - 1) * HOUR
