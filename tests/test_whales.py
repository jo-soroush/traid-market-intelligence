from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, localcontext
import inspect
import json
from pathlib import Path
import random

import pytest
from pydantic import BaseModel, ValidationError

import traid.whales.analytics as analytics
import traid.whales.models as models
from traid.domain.models import SourceProvenance
from traid.providers.hyperliquid_accounts import EPOCH, parse_clearinghouse_state, parse_fill
from traid.whales import (
    BtcPosition, Completeness, FillHistory, FillLiquidation, FundingHistory, LifecycleLabel, LifecycleStatus,
    LiquidationAttribution, PositionEffect, PositionSnapshot, ReconciliationStatus, ScoreComponent, ScoreStatus,
    ScoreWeight, Side, SmartMoneyRules, SmartMoneyStatus, SnapshotStatus, WalletEntry, WalletFill, WalletFunding,
    Watchlist, WhaleReport, WhaleRules, analyze_whales,
)

D = Decimal
UTC = timezone.utc
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "hyperliquid_accounts.json").read_text())
# Public Hyperliquid HLP vault accounts (provider userRole "vault"), used only as test identities.
W1 = "0x010461c14e146ac35fe42271bdc1134ee31c703a"
W2 = "0x31ca8395cf837de08b24da3f660e77761dfb974b"
HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
T0 = datetime(2026, 10, 21, 12, tzinfo=UTC)
NOW = T0 + timedelta(seconds=30)   # evaluation time
MIN = timedelta(minutes=1)


def prov(source_id, received, source_time=None):
    return SourceProvenance(source="hyperliquid", source_type="public_info", source_id=source_id,
                            source_timestamp=source_time, received_timestamp=received)


def direction(start, end):
    if start == 0:
        return "Open Long" if end > 0 else "Open Short"
    if (start > 0) != (end > 0) and end != 0:
        return "Long > Short" if start > 0 else "Short > Long"
    if end.copy_abs() > start.copy_abs():
        return "Open Long" if start > 0 else "Open Short"
    return "Close Long" if start > 0 else "Close Short"


def fill(start, size, side, at, tid, *, wallet=W1, dir=None, closed="0", fee="0", liq=None, price="100000",
         oid=None, token="USDC"):
    start, size = D(start), D(size)
    end = start + (size if side == "B" else -size)
    return WalletFill(address=wallet, price=D(price), size=size, side=side, time=at, start_position=start,
                      direction_label=dir or direction(start, end), closed_pnl=D(closed), fee=D(fee), fee_token=token,
                      tid=tid, oid=tid + 1000 if oid is None else oid, transaction_hash="0xabc", crossed=True,
                      liquidation=liq)


def history(fills, *, start=T0 - timedelta(hours=3), received=T0, wallet=W1, reasons=(), total=None):
    return FillHistory(address=wallet, requested_start=start, pages=1, total_record_count=len(fills) if total is None else total,
                       completeness=Completeness.INCOMPLETE if reasons else Completeness.COMPLETE, reasons=tuple(reasons),
                       provenance=prov("userFillsByTime", received), fills=tuple(fills))


def funding(entries, *, start=T0 - timedelta(hours=3), received=T0, wallet=W1, reasons=()):
    return FundingHistory(address=wallet, requested_start=start, pages=1, total_record_count=len(entries),
                          completeness=Completeness.INCOMPLETE if reasons else Completeness.COMPLETE,
                          reasons=tuple(reasons), provenance=prov("userFunding", received), funding=tuple(entries))


def fund(at, usdc, wallet=W1):
    return WalletFunding(address=wallet, time=at, usdc=D(usdc), position_size=D("1"), funding_rate=D("0.0000125"))


def snapshot(size, *, at=T0, received=None, wallet=W1, value=None, entry="100000", upnl="0", liq=None):
    pos = None if D(size) == 0 else BtcPosition(
        size=D(size), entry_price=D(entry), position_value=D(value) if value is not None else D(size).copy_abs() * D("101000"),
        unrealized_pnl=D(upnl), liquidation_price=None if liq is None else D(liq), leverage_type="cross", leverage=10,
        margin_used=D("1"))
    return PositionSnapshot(address=wallet, snapshot_time=at, btc_position=pos, account_value=D("1000000"),
                            provenance=prov("clearinghouseState", received or at + timedelta(seconds=1), at))


def entry(addr, label="wallet", role="vault"):
    return WalletEntry(address=addr, label=label, account_role=role, rationale="public HLP vault used as a test identity",
                       source="hyperliquid vaultDetails childAddresses", added_at=T0 - timedelta(days=1))


def watchlist(*addresses):
    return Watchlist.build("test-watchlist-1", [entry(a) for a in addresses or (W1,)])


def rules(weights=(), min_closing=2, window=timedelta(hours=2), activity=timedelta(hours=1), version="r1"):
    return WhaleRules(rules_version=version, max_snapshot_age=timedelta(minutes=5), max_history_age=timedelta(minutes=5),
                      activity_window=activity, smart_money=SmartMoneyRules(
                          methodology_version="sm-test-1", evaluation_window=window, min_closing_fills=min_closing,
                          weights=tuple(ScoreWeight(component=c, weight=D(w)) for c, w in weights)))


def run(*, wl=None, r=None, snapshots=(), fills=(), funding_histories=(), at=NOW):
    return analyze_whales(evaluation_time=at, watchlist=wl or watchlist(), rules=r or rules(), snapshots=tuple(snapshots),
                          fill_histories=tuple(fills), funding_histories=tuple(funding_histories))


def one(report):
    (w,) = report.wallets
    return w


def labels(wallet):
    return [(e.position_effect.value, e.label.value) for e in wallet.lifecycle.events]


def t(minutes):
    return T0 - timedelta(minutes=minutes)


# ======================================================================== lifecycle
def test_every_lifecycle_transition_long_and_short():
    fills = [fill("0", "1", "B", t(60), 1),          # OPEN long
             fill("1", "1", "B", t(55), 2),          # INCREASE
             fill("2", "0.5", "A", t(50), 3),        # REDUCE (partial)
             fill("1.5", "1.5", "A", t(45), 4),      # CLOSE
             fill("0", "2", "A", t(40), 5),          # OPEN short
             fill("-2", "1", "A", t(35), 6),         # INCREASE short
             fill("-3", "1", "B", t(30), 7),         # REDUCE short
             fill("-2", "3", "B", t(25), 8),         # FLIP short -> long
             fill("1", "2", "A", t(20), 9),          # FLIP long -> short (zero crossing)
             fill("-1", "1", "B", t(15), 10)]        # CLOSE short
    w = one(run(fills=[history(fills)]))
    assert [e for e, _ in labels(w)] == ["OPEN", "INCREASE", "REDUCE", "CLOSE", "OPEN", "INCREASE", "REDUCE", "FLIP",
                                         "FLIP", "CLOSE"]
    assert all(e == l for e, l in labels(w))
    assert [e.end_position for e in w.lifecycle.events] == list(map(D, ["1", "2", "1.5", "0", "-2", "-3", "-2", "1", "-1", "0"]))
    assert w.lifecycle.status is LifecycleStatus.AVAILABLE and w.lifecycle.continuity_gap_count == 0
    assert all(e.direction_label_check.value == "CONSISTENT" for e in w.lifecycle.events)


def test_unknown_initial_position_is_never_a_confirmed_open():
    w = one(run(fills=[history([fill("0.7", "0.1", "B", t(10), 1)])]))
    (e,) = w.lifecycle.events
    assert e.position_effect is PositionEffect.INCREASE and e.continuity.value == "FIRST_OBSERVED"
    # The provider "Open Long" text on an increase does not make it an OPEN (observed live).
    assert e.provider_direction_label == "Open Long"


def own(method="market"):
    return FillLiquidation(liquidated_user=W1, mark_price=D("99000"), method=method)


@pytest.mark.parametrize("start, size, side, method, effect", [
    ("2", "0.4", "A", "market", "REDUCE"),     # partial liquidation keeps its size effect
    ("2", "2", "A", "backstop", "CLOSE"),
    ("-1", "1", "B", "market", "CLOSE"),
])
def test_liquidation_label_only_from_a_provider_marker_naming_this_wallet(start, size, side, method, effect):
    w = one(run(fills=[history([fill(start, size, side, t(5), 1, liq=own(method))])]))
    (e,) = w.lifecycle.events
    assert (e.position_effect.value, e.label) == (effect, LifecycleLabel.LIQUIDATION)
    assert e.liquidation_attribution is LiquidationAttribution.OWN_ACCOUNT and e.liquidation_method == method


def test_counterparty_and_unattributed_markers_are_not_this_wallets_liquidation():
    counter = FillLiquidation(liquidated_user=W2, mark_price=D("99000"), method="backstop")
    unattributed = FillLiquidation(liquidated_user=None, mark_price=D("99000"), method="market")
    w = one(run(fills=[history([fill("0", "1", "B", t(9), 1, liq=counter), fill("1", "1", "A", t(8), 2, liq=unattributed)])]))
    first, second = w.lifecycle.events
    assert (first.label, first.liquidation_attribution) == (LifecycleLabel.OPEN, LiquidationAttribution.COUNTERPARTY)
    assert (second.label, second.position_effect) == (LifecycleLabel.UNKNOWN, PositionEffect.CLOSE)
    assert any(r.startswith("LIQUIDATION_MARKER_WITHOUT_LIQUIDATED_USER") for r in w.lifecycle.reasons)


def test_crossing_an_estimated_liquidation_price_is_never_a_liquidation():
    snap = snapshot("1", liq="120000")     # estimate above the fill prices
    fills = [fill("2", "1", "A", t(3), 1, price="90000")]
    w = one(run(snapshots=[snap], fills=[history(fills)]))
    assert [e.label for e in w.lifecycle.events] == [LifecycleLabel.REDUCE]
    assert w.exposure.liquidation_price_estimate.unit.endswith("(provider estimate)")


def test_same_millisecond_fills_follow_the_position_chain_not_tid():
    at = t(5)
    fills = [fill("0.5", "0.2", "B", at, 900), fill("0.3", "0.2", "B", at, 100), fill("0.7", "0.1", "A", at, 500)]
    w = one(run(fills=[history(fills)]))
    assert [e.tid for e in w.lifecycle.events] == [100, 900, 500] and w.lifecycle.continuity_gap_count == 0


def test_same_millisecond_ordering_continues_the_previous_chain_first():
    at = t(5)
    fills = [fill("0", "0.3", "B", t(6), 1), fill("0.3", "0.2", "B", at, 900), fill("1", "0.2", "B", at, 100)]
    w = one(run(fills=[history(fills)]))
    # The fill continuing the earlier position comes first; only the unrelated one is a gap.
    assert [e.tid for e in w.lifecycle.events] == [1, 900, 100] and w.lifecycle.continuity_gap_count == 1


def test_real_fixture_chain_has_no_gaps_although_tid_order_would():
    records = FIXTURE["userFillsByTime_btc"][W1]
    fills = [parse_fill(W1, r) for r in records]
    span = (min(f.time for f in fills), max(f.time for f in fills))
    w = one(run(fills=[history(fills, start=span[0], received=span[1] + timedelta(seconds=1))], at=span[1] + timedelta(seconds=2)))
    assert w.lifecycle.continuity_gap_count == 0 and len(w.lifecycle.events) == len(records)
    by_tid = sorted(fills, key=lambda f: (f.time, f.tid))
    assert sum(a.end_position != b.start_position for a, b in zip(by_tid, by_tid[1:])) > 0
    # Live: "Open Long" labels increases of an existing long; lifecycle uses startPosition instead.
    assert {e.position_effect for e in w.lifecycle.events} == {PositionEffect.INCREASE, PositionEffect.REDUCE}


def test_continuity_gaps_are_reported():
    w = one(run(fills=[history([fill("0", "1", "B", t(20), 1), fill("3", "1", "A", t(10), 2)])]))
    assert w.lifecycle.continuity_gap_count == 1 and "CONTINUITY_GAPS:1" in w.lifecycle.reasons
    assert w.lifecycle.events[1].continuity.value == "GAP_BEFORE"


def test_duplicate_fills_count_once_and_conflicts_fail_closed():
    a = fill("0", "1", "B", t(20), 1)
    same = a.model_copy(update={"price": D("100000.000")})       # equal value, other spelling
    w = one(run(fills=[history([a]), history([same], received=T0 - timedelta(seconds=5))]))
    assert w.lifecycle.duplicate_count == 1 and len(w.lifecycle.events) == 1
    conflict = a.model_copy(update={"size": D("2")})
    w = one(run(fills=[history([a]), history([conflict], received=T0 - timedelta(seconds=5))]))
    assert w.lifecycle.status is LifecycleStatus.CONFLICT and w.lifecycle.events == ()
    assert w.smart_money.status is SmartMoneyStatus.UNKNOWN
    assert w.activity.buy_volume.value is None


def test_provider_direction_label_contradiction_and_unrecognized_text():
    w = one(run(fills=[history([fill("0", "1", "B", t(5), 1, dir="Open Short")])]))
    assert w.lifecycle.status is LifecycleStatus.CONTRADICTORY and w.smart_money.status is SmartMoneyStatus.UNKNOWN
    w = one(run(fills=[history([fill("0", "1", "B", t(5), 1, dir="Auto-Deleveraging")])]))
    assert w.lifecycle.status is LifecycleStatus.AVAILABLE and "PROVIDER_DIRECTION_LABEL_UNRECOGNIZED" in w.lifecycle.reasons


# ==================================================================== reconciliation
def test_real_snapshot_reconciles_with_its_real_fill_chain():
    for wallet in (W1, W2):
        data = FIXTURE["clearinghouseState"][wallet]
        snap_time = EPOCH + timedelta(milliseconds=data["time"])
        snap = parse_clearinghouse_state(wallet, data, lambda st: prov("clearinghouseState", snap_time + MIN, st))
        fills = [parse_fill(wallet, r) for r in FIXTURE["userFillsByTime_btc"][wallet]]
        h = history(fills, wallet=wallet, start=min(f.time for f in fills), received=snap_time + MIN)
        w = one(run(wl=watchlist(wallet), snapshots=[snap], fills=[h], at=snap_time + 2 * MIN))
        assert w.reconciliation.status is ReconciliationStatus.RECONCILED
        assert w.reconciliation.implied_before == snap.btc_position.size


def test_reconciliation_states():
    fills = [fill("0", "1", "B", t(20), 1), fill("1", "1", "B", t(5), 2)]
    assert one(run(snapshots=[snapshot("1", at=t(10))], fills=[history(fills)])).reconciliation.status is ReconciliationStatus.RECONCILED
    w = one(run(snapshots=[snapshot("1.5", at=t(10))], fills=[history(fills)]))
    assert w.reconciliation.status is ReconciliationStatus.UNRECONCILED
    assert w.smart_money.status is SmartMoneyStatus.UNKNOWN
    outside = one(run(snapshots=[snapshot("1", at=t(10))], fills=[history(fills[1:], start=t(9))])).reconciliation
    assert outside.reasons == ("SNAPSHOT_OUTSIDE_COMPLETE_FILL_COVERAGE",)
    same_ms = one(run(snapshots=[snapshot("1", at=t(20))], fills=[history(fills)])).reconciliation
    assert same_ms.reasons == ("FILL_AT_SNAPSHOT_MILLISECOND_ORDER_UNKNOWN",)
    incomplete = one(run(snapshots=[snapshot("1", at=t(10))], fills=[history(fills, reasons=("CLIENT_PAGE_LIMIT_REACHED",))]))
    assert incomplete.reconciliation.status is ReconciliationStatus.NOT_CHECKABLE


# =================================================================== exposure / activity
def test_exposure_is_the_fresh_snapshot_and_not_recent_fills():
    snap = snapshot("2", at=t(1), value="202000", upnl="350")
    fills = [fill("0", "5", "B", t(30), 1)]   # activity says a 5 BTC buy; exposure is what the provider reports now
    w = one(run(snapshots=[snap], fills=[history(fills)]))
    e = w.exposure
    assert (e.status, e.side, e.size.value) == (SnapshotStatus.FRESH, Side.LONG, D("2"))
    assert e.provider_notional.value == D("202000") and e.entry_notional.value == D("200000")
    assert "C11-derived" in e.entry_notional.unit and "C11" not in e.provider_notional.unit
    assert e.unrealized_pnl.value == D("350") and w.performance.unrealized_as_of == t(1)
    assert w.activity.buy_volume.value == D("5")


def test_stale_missing_and_conflicting_snapshots_withhold_exposure():
    stale = one(run(snapshots=[snapshot("1", at=T0 - timedelta(minutes=6))]))
    assert stale.exposure.status is SnapshotStatus.STALE and stale.exposure.size.value is None
    assert stale.snapshot is not None   # the observation stays visible, with its time
    missing = one(run())
    assert missing.exposure.status is SnapshotStatus.MISSING and missing.snapshot is None
    conflict = one(run(snapshots=[snapshot("1", at=t(1)), snapshot("2", at=t(1))]))
    assert conflict.exposure.status is SnapshotStatus.CONFLICT and conflict.snapshot is None
    boundary = one(run(snapshots=[snapshot("1", at=NOW - timedelta(minutes=5))]))
    assert boundary.exposure.status is SnapshotStatus.FRESH


def test_aggregate_is_capital_weighted_sample_exposure_not_wallet_counts():
    wl = watchlist(W1, W2, HLP)
    snaps = [snapshot("0.1", wallet=W1, value="10000", at=t(1)), snapshot("0.2", wallet=HLP, value="30000", at=t(1)),
             snapshot("-3", wallet=W2, value="300000", at=t(2))]
    agg = run(wl=wl, snapshots=snaps).aggregate
    assert (agg.long_wallets, agg.short_wallets) == (2, 1)
    assert (agg.long_notional.value, agg.short_notional.value) == (D(40000), D(300000))
    assert (agg.gross_notional.value, agg.net_notional.value) == (D(340000), D(-260000))   # net short despite 2 of 3 long
    assert (agg.long_size.value, agg.short_size.value) == (D("0.3"), D("-3"))
    with localcontext() as c:
        c.prec = 60
        shares = [D(10000) / D(340000), D(30000) / D(340000), D(300000) / D(340000)]
        assert abs(agg.largest_wallet_share.value - max(shares)) < D("1e-48")
        assert abs(agg.concentration_hhi.value - sum(s * s for s in shares)) < D("1e-48")
    assert agg.scope == "CURATED_WATCHLIST_SAMPLE" and agg.coverage == "COMPLETE"


def test_partial_and_empty_coverage():
    wl = watchlist(W1, W2)
    agg = run(wl=wl, snapshots=[snapshot("1", wallet=W1, at=t(1)), snapshot("1", wallet=W2, at=t(30))]).aggregate
    assert (agg.coverage, agg.wallets_available, agg.wallets_stale) == ("PARTIAL", 1, 1)
    assert "PARTIAL_WATCHLIST_COVERAGE" in agg.reasons
    agg = run(wl=wl).aggregate
    assert agg.coverage == "NONE" and agg.gross_notional.value is None and agg.wallets_missing == 2
    flat = run(wl=wl, snapshots=[snapshot("0", wallet=W1, at=t(1)), snapshot("0", wallet=W2, at=t(1))]).aggregate
    assert flat.gross_notional.value == 0 and flat.largest_wallet_share.reason == "NO_GROSS_EXPOSURE_IN_SAMPLE"
    assert flat.flat_wallets == 2


def test_activity_window_bounds_and_coverage():
    fills = [fill("0", "1", "B", NOW - timedelta(hours=1), 1),            # exactly at window start: excluded
             fill("1", "2", "B", NOW - timedelta(hours=1) + timedelta(milliseconds=1), 2),
             fill("3", "1", "A", t(1), 3)]
    w = one(run(fills=[history(fills)]))
    counts = {c.label: c.count for c in w.activity.observed_event_counts}
    assert counts[LifecycleLabel.INCREASE] == 1 and counts[LifecycleLabel.REDUCE] == 1 and counts[LifecycleLabel.OPEN] == 0
    assert (w.activity.buy_volume.value, w.activity.sell_volume.value) == (D(2), D(1))
    assert w.activity.traded_notional.value == D(300000) and w.activity.coverage.value == "COMPLETE"
    late_start = one(run(fills=[history([f for f in fills if f.time >= t(30)], start=t(30))]))
    assert late_start.activity.coverage.value == "INCOMPLETE" and late_start.activity.buy_volume.value is None
    assert {c.label: c.count for c in late_start.activity.observed_event_counts}[LifecycleLabel.REDUCE] == 1


@pytest.mark.parametrize("make", [
    lambda f: history(f, reasons=("PROVIDER_FILL_HISTORY_CAP_REACHED",)),
    lambda f: history(f, reasons=("CLIENT_PAGE_LIMIT_REACHED",)),
    lambda f: history(f, received=T0 - timedelta(minutes=6)),            # stale history
])
def test_incomplete_or_stale_history_withholds_totals_and_eligibility(make):
    fills = [fill("0", "1", "B", t(50), 1), fill("1", "1", "A", t(40), 2, closed="10"),
             fill("0", "1", "B", t(30), 3), fill("1", "1", "A", t(20), 4, closed="5")]
    w = one(run(fills=[make(fills)]))
    assert w.activity.coverage.value == "INCOMPLETE" and w.performance.closed_pnl.value is None
    assert w.performance.closing_fill_count is None
    assert w.smart_money.status is SmartMoneyStatus.INSUFFICIENT_EVIDENCE
    assert len(w.lifecycle.events) == 4   # observed events stay visible


def test_snapshot_alone_never_creates_history():
    w = one(run(snapshots=[snapshot("5", at=t(1))]))
    assert w.lifecycle.status is LifecycleStatus.NO_HISTORY and w.lifecycle.events == ()
    assert w.activity.coverage.value == "INCOMPLETE"
    assert w.reconciliation.status is ReconciliationStatus.NOT_CHECKABLE


# ================================================================== realized / unrealized
def test_realized_components_stay_separate_and_net_is_never_formed():
    fills = [fill("0", "1", "B", t(90), 1, fee="1.5"), fill("1", "0.5", "A", t(60), 2, closed="40", fee="0.5"),
             fill("0.5", "0.5", "A", t(30), 3, closed="-15", fee="-0.25")]
    w = one(run(snapshots=[snapshot("0", at=t(1))], fills=[history(fills)],
                funding_histories=[funding([fund(t(130), "-9"), fund(t(70), "-1.25"), fund(t(10), "-0.5")])]))
    p = w.performance
    assert (p.closed_pnl.value, p.fees.value, p.funding.value) == (D(25), D("1.75"), D("-1.75"))  # t(130) is outside 2h
    assert p.combined_net_pnl.value is None and p.combined_net_pnl.reason == "ACCOUNTING_COMPOSITION_UNVERIFIED"
    assert (p.closing_fill_count, p.winning_closing_fills, p.losing_closing_fills) == (2, 1, 1)
    assert (p.positive_closed_pnl.value, p.negative_closed_pnl.value) == (D(40), D(-15))
    assert p.unrealized_pnl.value == D(0)


def test_fee_tokens_funding_coverage_and_conflicts():
    fills = [fill("0", "1", "B", t(30), 1, fee="1", token="HYPE"), fill("1", "1", "A", t(20), 2, closed="3")]
    p = one(run(fills=[history(fills)])).performance
    assert p.fees.reason == "MIXED_OR_NON_USDC_FEE_TOKENS" and p.funding.reason == "FUNDING_HISTORY_DOES_NOT_COVER_WINDOW"
    late = one(run(fills=[history(fills)], funding_histories=[funding([], start=t(30))])).performance
    assert late.funding_coverage.value == "INCOMPLETE"
    conflict = one(run(fills=[history(fills)], funding_histories=[
        funding([fund(t(10), "-1")]), funding([fund(t(10), "-2")], received=T0 - timedelta(seconds=1))])).performance
    assert conflict.funding.reason == "CONFLICTING_FUNDING_ENTRIES"


# ===================================================================== Smart Money
def round_trips(n, wallet=W1, closed=("10", "-4")):
    fills, tid = [], 1
    for i in range(n):
        base = 100 - 5 * i
        fills.append(fill("0", "1", "B", t(base), tid, wallet=wallet))
        fills.append(fill("1", "1", "A", t(base - 1), tid + 1, wallet=wallet, closed=closed[i % len(closed)]))
        tid += 2
    return fills


def test_minimum_evidence_boundary_and_unscored_methodology():
    below = one(run(r=rules(min_closing=3), fills=[history(round_trips(2))]))
    assert below.smart_money.status is SmartMoneyStatus.INSUFFICIENT_EVIDENCE
    assert below.smart_money.reasons == ("CLOSING_FILLS_BELOW_MINIMUM:2<3",) and below.smart_money.components == ()
    at = one(run(r=rules(min_closing=2), fills=[history(round_trips(2))])).smart_money
    assert at.status is SmartMoneyStatus.ELIGIBLE and at.score_status is ScoreStatus.NOT_CONFIGURED and at.score.value is None
    values = {c.component: c.value for c in at.components}
    assert set(values) == set(ScoreComponent) and values[ScoreComponent.CLOSING_FILL_WIN_RATE] == D("0.5")
    with localcontext() as c:
        c.prec = 50
        assert values[ScoreComponent.CLOSED_PNL_GAIN_SHARE] == D(10) / D(14)
    assert at.interpretation.endswith("NOT_PREDICTIVE_SKILL") and at.methodology_version == "sm-test-1"
    assert all(c.normalization for c in at.components)


def test_configured_weights_produce_an_inspectable_score():
    r = rules(weights=[(ScoreComponent.CLOSED_PNL_GAIN_SHARE, "3"), (ScoreComponent.CLOSING_FILL_WIN_RATE, "1")])
    sm = one(run(r=r, fills=[history(round_trips(4))])).smart_money
    with localcontext() as c:
        c.prec = 50
        expected = (D(3) * (D(20) / D(28)) + D(1) * D("0.5")) / D(4)
    assert sm.score_status is ScoreStatus.SCORED and abs(sm.score.value - expected) < D("1e-48")
    assert {c.component: c.weight for c in sm.components} == {ScoreComponent.CLOSED_PNL_GAIN_SHARE: D(3),
                                                              ScoreComponent.CLOSING_FILL_WIN_RATE: D(1)}
    assert "not truth" in sm.score.unit


def test_size_and_notional_never_change_the_smart_money_judgment():
    small = one(run(snapshots=[snapshot("0.01", at=t(1))], fills=[history(round_trips(3))])).smart_money
    huge_fills = [f.model_copy(update={"size": f.size * 1000, "start_position": f.start_position * 1000})
                  for f in round_trips(3)]
    huge = one(run(snapshots=[snapshot("5000", at=t(1), value="500000000")], fills=[history(huge_fills)])).smart_money
    assert small.components == huge.components and small.status == huge.status
    whale_without_evidence = one(run(snapshots=[snapshot("10000", at=t(1), value="1000000000")],
                                     fills=[history([])])).smart_money
    assert whale_without_evidence.status is SmartMoneyStatus.INSUFFICIENT_EVIDENCE
    assert set(ScoreComponent) == {ScoreComponent.CLOSING_FILL_WIN_RATE, ScoreComponent.CLOSED_PNL_GAIN_SHARE}


def test_closing_fills_without_decided_outcomes_are_insufficient():
    sm = one(run(fills=[history(round_trips(3, closed=("0",)))])).smart_money
    assert sm.reasons == ("NO_CLOSING_FILL_WITH_NONZERO_CLOSED_PNL",)


def test_methodology_and_rules_are_versioned_and_digested():
    a = run(r=rules())
    b = run(r=rules(weights=[(ScoreComponent.CLOSING_FILL_WIN_RATE, "1")]))
    c = run(r=rules(version="r2"))
    assert len({a.rules_digest, b.rules_digest, c.rules_digest}) == 3
    assert run(r=rules(weights=[(ScoreComponent.CLOSING_FILL_WIN_RATE, "1.0")])).rules_digest == b.rules_digest
    assert a.rules.calibration_status == "UNCALIBRATED" and "THRESHOLDS_AND_WEIGHTS_UNCALIBRATED_CALLER_CONFIGURED" in a.limitations
    data = a.model_dump()
    data["rules"]["rules_version"] = "tampered"
    with pytest.raises(ValidationError):
        WhaleReport.model_validate(data)


@pytest.mark.parametrize("build", [
    lambda: SmartMoneyRules(methodology_version="m", evaluation_window=timedelta(hours=1), min_closing_fills=0),
    lambda: SmartMoneyRules(methodology_version="m", evaluation_window=timedelta(0), min_closing_fills=1),
    lambda: SmartMoneyRules(methodology_version="m", evaluation_window=timedelta(hours=1), min_closing_fills=1,
                            weights=(ScoreWeight(component="CLOSING_FILL_WIN_RATE", weight=D(1)),) * 2),
    lambda: ScoreWeight(component="CLOSING_FILL_WIN_RATE", weight=D(0)),
    lambda: ScoreWeight(component="POSITION_SIZE", weight=D(1)),
    lambda: SmartMoneyRules(methodology_version="m", evaluation_window=timedelta(hours=1)),   # no default minimum
    lambda: WhaleRules(rules_version="r", max_snapshot_age=timedelta(minutes=1), max_history_age=timedelta(minutes=1),
                       activity_window=timedelta(hours=1)),                                      # no default methodology
    lambda: WhaleRules(rules_version="r", calibration_status="CALIBRATED", max_snapshot_age=timedelta(minutes=1),
                       max_history_age=timedelta(minutes=1), activity_window=timedelta(hours=1),
                       smart_money=rules().smart_money),
])
def test_invalid_or_defaulted_methodology_is_rejected(build):
    with pytest.raises(ValidationError):
        build()


def test_report_rejects_an_unearned_score():
    data = run(fills=[history(round_trips(3))]).model_dump()
    sm = data["wallets"][0]["smart_money"]
    sm["score"] = {"value": D("0.9"), "unit": "x", "reason": None}
    with pytest.raises(ValidationError):
        WhaleReport.model_validate(data)
    data = run().model_dump()
    data["wallets"][0]["smart_money"]["status"] = SmartMoneyStatus.ELIGIBLE
    with pytest.raises(ValidationError):
        WhaleReport.model_validate(data)


# ================================================================ point-in-time
def test_observations_received_after_evaluation_are_counted_and_never_read():
    base = run(snapshots=[snapshot("1", at=t(2))], fills=[history([fill("0", "1", "B", t(20), 1)])])
    future_snap = snapshot("9", at=t(1), received=NOW + timedelta(seconds=1))
    future_hist = history([fill("0", "9", "B", t(15), 2)], received=NOW + timedelta(seconds=1))
    later = run(snapshots=[snapshot("1", at=t(2)), future_snap],
                fills=[history([fill("0", "1", "B", t(20), 1)]), future_hist])
    assert later.excluded_after_evaluation.snapshots == 1 and later.excluded_after_evaluation.fill_histories == 1
    a, b = base.model_dump(mode="json"), later.model_dump(mode="json")
    a.pop("excluded_after_evaluation"), b.pop("excluded_after_evaluation")
    assert a == b


@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings")  # dumping the deliberately malformed record
def test_future_records_are_not_validated_until_knowable():
    stranger = "0x" + "ab" * 20
    unknowable = PositionSnapshot.model_construct(
        address=stranger, snapshot_time=NOW, btc_position=None, account_value=None, schema_version="1.0",
        provenance=prov("clearinghouseState", NOW + MIN, NOW))
    report = run(snapshots=[unknowable])
    assert report.excluded_after_evaluation.snapshots == 1
    with pytest.raises(ValueError, match="WALLET_NOT_IN_WATCHLIST"):
        run(snapshots=[unknowable], at=NOW + 2 * MIN)
    # Content that is invalid is not even validated while it is unknowable.
    invalid = PositionSnapshot.model_construct(
        address="not-an-address", snapshot_time="garbage", btc_position={"size": "0"}, account_value=None,
        schema_version="1.0", provenance=prov("clearinghouseState", NOW + MIN, NOW))
    assert run(snapshots=[invalid]).excluded_after_evaluation.snapshots == 1
    with pytest.raises(ValidationError):
        run(snapshots=[invalid], at=NOW + 2 * MIN)
    for bad in (PositionSnapshot.model_construct(address=W1, snapshot_time=NOW, btc_position=None, account_value=None,
                                                 provenance=None),
                PositionSnapshot.model_construct(address=W1, snapshot_time=NOW, btc_position=None, account_value=None,
                                                 provenance=SourceProvenance.model_construct(received_timestamp=NOW.replace(tzinfo=None)))):
        with pytest.raises(ValueError):
            run(snapshots=[bad])


def test_newly_fetched_snapshots_are_not_backdated():
    early = snapshot("1", at=t(3), received=t(2))
    fetched_later = snapshot("4", at=t(1), received=NOW + timedelta(seconds=5))
    w = one(run(snapshots=[early, fetched_later]))
    assert w.exposure.size.value == D(1) and w.snapshot.snapshot_time == t(3)


@pytest.mark.parametrize("build", [
    lambda: PositionSnapshot(address=W1, snapshot_time=t(1), btc_position=None, account_value=None,
                             provenance=prov("clearinghouseState", t(0), t(2))),           # provider time mismatch
    lambda: history([fill("0", "1", "B", t(1), 1)], received=t(2)),                        # fill after receipt
    lambda: history([fill("0", "1", "B", t(200), 1)]),                                     # before requested start
    lambda: history([fill("0", "1", "B", t(1), 1, wallet=W2)]),                            # foreign wallet
    lambda: FillHistory(address=W1, requested_start=t(10), pages=1, total_record_count=0, completeness="COMPLETE",
                        reasons=("X",), provenance=prov("userFillsByTime", T0), fills=()),
    lambda: history([fill("0", "1", "B", t(1), 1)], total=0),
    lambda: BtcPosition(size=D(0), entry_price=D(1), position_value=D(0), unrealized_pnl=D(0), liquidation_price=None,
                        leverage_type="cross", leverage=1, margin_used=D(0)),
])
def test_internally_inconsistent_observations_are_rejected(build):
    with pytest.raises(ValidationError):
        build()


def test_unwatched_wallet_data_is_rejected():
    with pytest.raises(ValueError, match="WALLET_NOT_IN_WATCHLIST"):
        run(snapshots=[snapshot("1", wallet=W2, at=t(1))])


# ======================================================================== watchlist
def test_watchlist_is_ordered_deduplicated_and_digested():
    a, b = entry(W2), entry(W1.upper().replace("0X", "0x"))
    wl = Watchlist.build("v1", [a, b, a])
    assert [e.address for e in wl.entries] == [W1, W2]
    assert wl.digest() == Watchlist.build("v1", [b, a]).digest()
    changed = Watchlist.build("v1", [a, b.model_copy(update={"rationale": "different reason"})])
    assert changed.digest() != wl.digest()
    with pytest.raises(ValueError):
        Watchlist.build("v1", [a, a.model_copy(update={"label": "other"})])
    with pytest.raises(ValidationError):
        Watchlist(watchlist_version="v1", entries=(entry(W2), entry(W1)))
    assert "INCLUSION_IS_NOT_SKILL_OR_SMART_MONEY" in wl.limitations


@pytest.mark.parametrize("kw", [dict(address="0x123"), dict(address="0x" + "g" * 40), dict(account_role="agent"),
                                dict(account_role="missing"), dict(rationale=""), dict(source=""),
                                dict(added_at=datetime(2026, 1, 1))])
def test_invalid_watchlist_entries_are_rejected(kw):
    base = dict(address=W1, label="x", rationale="r", source="s", added_at=T0)
    base.update(kw)
    with pytest.raises(ValidationError):
        WalletEntry(**base)


# ======================================================================= determinism
def scenario():
    wl = watchlist(W1, W2)
    snaps = [snapshot("1", wallet=W1, at=t(2)), snapshot("-2", wallet=W2, at=t(3), value="200000")]
    hists = [history(round_trips(3), wallet=W1), history(round_trips(2, wallet=W2), wallet=W2),
             history(round_trips(3)[:2], wallet=W1, received=T0 - timedelta(seconds=9))]
    funds = [funding([fund(t(10), "-1")]), funding([fund(t(10), "-1"), fund(t(70), "2")], received=T0 - timedelta(seconds=3))]
    return wl, snaps, hists, funds


def test_input_order_ambient_context_and_serialization_are_stable():
    wl, snaps, hists, funds = scenario()
    r = rules(weights=[(ScoreComponent.CLOSING_FILL_WIN_RATE, "2")])
    baseline = analyze_whales(evaluation_time=NOW, watchlist=wl, rules=r, snapshots=tuple(snaps),
                              fill_histories=tuple(hists), funding_histories=tuple(funds)).model_dump_json()
    rng = random.Random(11)
    for _ in range(6):
        rng.shuffle(snaps), rng.shuffle(hists), rng.shuffle(funds)
        shuffled_fills = [h.model_copy(update={"fills": tuple(rng.sample(h.fills, len(h.fills)))}) for h in hists]
        with localcontext() as c:
            c.prec, c.rounding = 3, ROUND_DOWN
            out = analyze_whales(evaluation_time=NOW, watchlist=wl, rules=r, snapshots=tuple(snaps),
                                 fill_histories=tuple(shuffled_fills), funding_histories=tuple(funds)).model_dump_json()
        assert out == baseline
    restored = WhaleReport.model_validate_json(baseline)
    assert restored.model_dump_json() == baseline
    with pytest.raises(ValidationError):
        restored.evaluation_time = T0


def test_decimal_precision_is_exact():
    fills = [fill("0", "0.00000001", "B", t(30), 1, price="123456.789"),
             fill("0.00000001", "0.00000002", "B", t(20), 2, price="0.000001")]
    w = one(run(fills=[history(fills)]))
    assert w.activity.buy_volume.value == D("0.00000003")
    assert w.activity.traded_notional.value == D("0.00123456789") + D("0.00000000000002")


def test_sequential_evaluations_replay_point_in_time():
    fills = [fill("0", "1", "B", t(50), 1), fill("1", "1", "A", t(10), 2, closed="7")]
    h_early = history(fills[:1], received=t(40))
    h_late = history(fills, received=T0)
    early = one(run(fills=[h_early, h_late], at=t(39)))
    late = one(run(fills=[h_early, h_late], at=NOW))
    assert [e.label for e in early.lifecycle.events] == [LifecycleLabel.OPEN]
    assert [e.label for e in late.lifecycle.events] == [LifecycleLabel.OPEN, LifecycleLabel.CLOSE]
    assert early == one(run(fills=[h_early, h_late], at=t(39)))


# ================================================================ no trade authority
def test_no_output_can_authorize_or_route_a_trade():
    banned = ("order", "signal", "authorize", "execute", "trade_action", "copy", "recommend", "buy_now", "sell_now")
    seen = set()

    def walk(cls):
        if cls in seen or not (isinstance(cls, type) and issubclass(cls, BaseModel)):
            return
        seen.add(cls)
        for name, field in cls.model_fields.items():
            assert not any(b in name.lower() for b in banned), (cls.__name__, name)
            for arg in getattr(field.annotation, "__args__", ()) + (field.annotation,):
                walk(arg)
    walk(WhaleReport)
    assert "NOT_TRADE_AUTHORIZATION_OR_SIGNAL" in WhaleReport.model_fields["limitations"].default
    for mod in (analytics, models):
        source = inspect.getsource(mod)
        assert "traid.exchange" not in source and "urllib" not in source and "datetime.now" not in source
        assert "import random" not in source and "from random" not in source
