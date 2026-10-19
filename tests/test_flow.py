from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import random

import pytest
from pydantic import ValidationError

import traid.flow.analytics as flow_module
from traid.domain.models import AggressorSide, MarketTrade, SourceProvenance
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.flow import FlowConfig, FlowReport, analyze_flow
from traid.quality import ContinuityStatus, RecoveryStatus, default_quality_policy

D = Decimal
NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
BUY, SELL = AggressorSide.BUY, AggressorSide.SELL


def trade(tid, side, qty, ago=1.0, lag=0.0, price="100", source_type="public_websocket", symbol="BTC", source="fixture"):
    """A trade `ago` seconds before NOW, received `lag` seconds after its event time."""
    when = NOW - timedelta(seconds=ago)
    return MarketTrade(
        symbol=symbol, price=D(price), quantity=D(qty), side=side, timestamp=when,
        provenance=SourceProvenance(source=source, source_type=source_type, source_id=tid,
                                    source_timestamp=when, received_timestamp=when + timedelta(seconds=lag)))


def config(window=60, session=300, tolerance=5):
    return FlowConfig(symbol="BTC", base_asset="BTC", window=timedelta(seconds=window),
                      session_start=NOW - timedelta(seconds=session), late_tolerance=timedelta(seconds=tolerance))


def run(trades, c=None, **kwargs):
    args = dict(config=c or config(), coverage=CapabilityCoverage(Capability.TRADES, CapabilityAvailability.SUPPORTED),
                evaluation_time=NOW, policy=default_quality_policy(), continuity=ContinuityStatus.PROVEN,
                recovery=RecoveryStatus.NONE)
    args.update(kwargs)
    return analyze_flow(tuple(trades), **args)


def known():
    return [
        trade("t0", BUY, "9", ago=400),   # before the session: ignored
        trade("t1", BUY, "2", ago=200),
        trade("t2", SELL, "1", ago=100),
        trade("t3", BUY, "3", ago=50),
        trade("t4", SELL, "0.5", ago=10),
        trade("t5", BUY, "1", ago=2),
    ]


def values(r):
    return [m.value for m in (r.window_buy_volume, r.window_sell_volume, r.window_net_delta,
                              r.session_buy_volume, r.session_sell_volume, r.session_cvd)]


def test_known_sequence_window_delta_and_session_cvd_are_distinct():
    r = run(known())
    assert values(r) == [D("4"), D("0.5"), D("3.5"), D("6"), D("1.5"), D("4.5")]
    assert (r.window_trade_count, r.session_trade_count, r.input_trade_count) == (3, 5, 6)
    assert r.trusted_for_current_use and r.reasons == () and r.quality.trusted_for_current_use
    assert r.window_net_delta.unit == "BTC" and r.session_cvd.unit == "BTC"
    assert r.window_start == NOW - timedelta(seconds=60) and r.formula_version == "c08-trade-flow-1"
    assert r.units_provider_verified is False
    assert "UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED" in r.limitations


def test_window_and_session_boundaries_are_inclusive_and_exclusive_just_outside():
    micro = 1e-6
    edge = [trade("w_in", BUY, "1", ago=60), trade("w_out", BUY, "10", ago=60 + micro),
            trade("s_in", SELL, "2", ago=300), trade("s_out", SELL, "20", ago=300 + micro),
            trade("e_in", BUY, "4", ago=0), trade("fresh", BUY, "0.25", ago=1)]
    r = run(edge)
    assert values(r)[:3] == [D("5.25"), D("0"), D("5.25")]
    assert values(r)[3:] == [D("15.25"), D("2"), D("13.25")]


def test_session_reset_excludes_everything_before_session_start():
    r = run(known(), config(session=30))
    assert (r.session_buy_volume.value, r.session_sell_volume.value, r.session_cvd.value) == (D(1), D("0.5"), D("0.5"))
    assert r.session_trade_count == 2


def test_decimal_precision_is_exact_not_float():
    r = run([trade("a", BUY, "0.1"), trade("b", BUY, "0.2"), trade("c", SELL, "0.3", ago=2)])
    assert r.window_buy_volume.value == D("0.3") and r.window_net_delta.value == D("0")
    assert isinstance(r.session_cvd.value, Decimal)


def test_window_with_no_trades_is_unavailable_not_zero():
    r = run(known(), config(window=1))
    assert r.window_buy_volume.value is None and r.window_buy_volume.reason == "NO_TRADES_IN_WINDOW"
    assert r.window_trade_count == 0
    assert r.session_cvd.value == D("4.5") and not r.trusted_for_current_use


def test_empty_or_out_of_range_input_is_unavailable_not_zero():
    for items in ([], [trade("old", BUY, "1", ago=900)]):
        r = run(items)
        assert r.session_cvd.value is None and r.session_cvd.reason == "NO_TRADES_IN_RANGE"
        assert not r.trusted_for_current_use and r.quality is None


def test_missing_side_makes_report_unavailable():
    r = run(known() + [trade("x", None, "1")])
    assert r.session_cvd.value is None and r.session_cvd.reason == "AGGRESSOR_SIDE_UNKNOWN"
    assert "AGGRESSOR_SIDE_UNKNOWN" in r.reasons and not r.trusted_for_current_use


def test_identical_duplicate_delivery_counts_once_across_transports():
    http = trade("t3", BUY, "3", ago=50, lag=0.5, source_type="public_info")
    r = run(known() + [http, known()[3]])
    assert values(r) == values(run(known())) and r.duplicate_count == 2
    assert r.input_trade_count == 8 and r.trusted_for_current_use


@pytest.mark.parametrize("dup", [
    lambda: trade("t3", BUY, "3.1", ago=50),
    lambda: trade("t3", SELL, "3", ago=50),
    lambda: trade("t3", BUY, "3", ago=49),
    lambda: trade("t3", BUY, "3", ago=50, price="101"),
])
def test_conflicting_duplicate_identity_is_unavailable(dup):
    r = run(known() + [dup()])
    assert r.window_net_delta.value is None and r.session_cvd.value is None
    assert r.reasons == ("TRADE_IDENTITY_CONFLICT",) and not r.trusted_for_current_use


def test_same_time_different_tid_are_distinct_trades():
    r = run([trade("a", BUY, "1", ago=10), trade("b", BUY, "1", ago=10), trade("c", SELL, "1", ago=2)])
    assert r.window_buy_volume.value == D(2) and r.duplicate_count == 0


def test_input_order_and_equal_timestamps_do_not_change_the_report():
    items = known() + [trade("e1", BUY, "1", ago=1), trade("e2", SELL, "2", ago=1)]
    expected = run(items).model_dump_json()
    rng = random.Random(8)
    for _ in range(20):
        rng.shuffle(items)
        assert run(items).model_dump_json() == expected


def test_replay_is_byte_identical_and_uses_only_explicit_time():
    assert run(known()).model_dump_json() == run(known()).model_dump_json()
    source = inspect.getsource(flow_module)
    for forbidden in ("datetime.now", "time.time", "utcnow", "urllib", "socket", "requests", "random", "open("):
        assert forbidden not in source


def test_late_trade_is_retained_in_its_event_window_but_not_trusted():
    items = known() + [trade("late", BUY, "7", ago=30, lag=20)]
    r = run(items)
    assert r.window_buy_volume.value == D("11") and r.late_count == 1
    assert r.reasons == ("LATE_TRADES_PRESENT",) and not r.trusted_for_current_use
    assert r.quality.trusted_for_current_use


def test_lateness_within_tolerance_is_trusted():
    r = run(known() + [trade("ok", BUY, "7", ago=30, lag=5)])
    assert r.late_count == 0 and r.trusted_for_current_use and r.window_buy_volume.value == D("11")


def test_future_dated_trade_is_counted_but_never_read():
    r = run(known() + [trade("future", BUY, "100", ago=-30)])  # event and receipt after evaluation
    assert r.not_yet_received_count == 1 and r.window_buy_volume.value == D("4")
    assert r.reasons == () and r.trusted_for_current_use


def test_trade_not_yet_received_at_evaluation_is_excluded_without_lookahead():
    delayed = trade("later", BUY, "100", ago=1, lag=3)  # received after NOW
    before = run(known() + [delayed])
    assert before.not_yet_received_count == 1 and values(before) == values(run(known()))
    assert before.trusted_for_current_use
    after = run(known() + [delayed], evaluation_time=NOW + timedelta(seconds=3),
                c=config(window=60 + 3, session=303))
    assert after.not_yet_received_count == 0 and after.session_buy_volume.value == D("106")


@pytest.mark.parametrize("age", [10, 40])
def test_delayed_or_stale_newest_trade_withholds_numbers(age):
    r = run([trade("a", BUY, "1", ago=age), trade("b", SELL, "1", ago=age + 5)])
    assert r.session_cvd.value is None and r.session_cvd.reason == "DATA_QUALITY_NOT_TRUSTED"
    assert not r.trusted_for_current_use and not r.quality.trusted_for_current_use
    assert r.quality.provenance_quality.value == "COMPLETE" and r.quality.source_age == timedelta(seconds=age)


@pytest.mark.parametrize("override", [
    dict(continuity=ContinuityStatus.GAP_RISK), dict(continuity=ContinuityStatus.UNKNOWN),
    dict(recovery=RecoveryStatus.RECOVERING), dict(recovery=RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF),
    dict(coverage=CapabilityCoverage(Capability.TRADES, CapabilityAvailability.UNAVAILABLE, "not available")),
    dict(coverage=CapabilityCoverage(Capability.TRADES, CapabilityAvailability.LIMITED, "limited")),
])
def test_incomplete_continuity_recovery_or_coverage_propagates_and_withholds_numbers(override):
    r = run(known(), **override)
    assert r.session_cvd.value is None and not r.trusted_for_current_use
    assert r.quality is not None and r.quality.reasons[0] in r.reasons


def test_quality_is_assessed_on_the_newest_retained_trade_and_all_provenance_is_checked():
    r = run(known())
    assert r.quality.capability is Capability.TRADES and r.quality.source_age == timedelta(seconds=2)
    broken = trade("nosrc", BUY, "1")
    broken = broken.model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="x", source_id="nosrc", received_timestamp=NOW)})
    r = run(known() + [broken])
    assert "TRADE_TIMESTAMP_PROVENANCE_MISMATCH" in r.reasons and r.session_cvd.value is None
    noid = trade("a", BUY, "1").model_copy(update={"provenance": SourceProvenance(
        source="fixture", source_type="x", source_timestamp=NOW - timedelta(seconds=1), received_timestamp=NOW)})
    assert "TRADE_ID_MISSING" in run([noid]).reasons


def test_unsupported_numeric_range_is_unavailable():
    huge = trade("big", BUY, "1" + "0" * 60)
    r = run(known() + [huge])
    assert r.session_cvd.value is None and r.reasons == ("NUMERIC_RANGE_UNSUPPORTED",)


def test_invalid_callers_are_rejected_not_defaulted():
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        run(known() + [trade("eth", BUY, "1", symbol="ETH")])
    with pytest.raises(ValueError, match="SESSION_START_AFTER_EVALUATION"):
        run(known(), evaluation_time=NOW - timedelta(days=1))
    with pytest.raises(ValueError, match="timezone-aware"):
        run(known(), evaluation_time=datetime(2026, 10, 15, 12))
    with pytest.raises(ValueError):
        analyze_flow(list(known()), config=config(), coverage=None, evaluation_time=NOW,
                     policy=default_quality_policy(), continuity=ContinuityStatus.PROVEN, recovery=RecoveryStatus.NONE)


def test_validation_bypass_and_oversize_are_rejected(monkeypatch):
    good = trade("a", BUY, "1")
    bad = MarketTrade.model_construct(**{**dict(good), "quantity": D("-1")})
    with pytest.raises(ValidationError):
        run([bad])
    monkeypatch.setattr(flow_module, "MAX_TRADES", 2)
    with pytest.raises(ValueError, match="too many trades"):
        run(known())


@pytest.mark.parametrize("kwargs", [dict(window=0), dict(window=-1), dict(tolerance=-1)])
def test_config_rejects_invalid_durations(kwargs):
    with pytest.raises(ValidationError):
        config(**kwargs)
    with pytest.raises(ValidationError):
        FlowConfig(symbol="BTC", base_asset=" ", window=timedelta(seconds=1), session_start=NOW, late_tolerance=timedelta(0))
    with pytest.raises(ValidationError, match="timezone-aware"):
        FlowConfig(symbol="BTC", base_asset="BTC", window=timedelta(seconds=1),
                   session_start=datetime(2026, 1, 1), late_tolerance=timedelta(0))


def test_report_is_immutable_round_trips_and_cannot_claim_unearned_trust():
    r = run(known())
    assert FlowReport.model_validate_json(r.model_dump_json()) == r
    with pytest.raises(ValidationError):
        r.reasons = ("x",)
    with pytest.raises(ValidationError):
        FlowReport.model_validate({**r.model_dump(), "quality": None})
    with pytest.raises(ValidationError):
        FlowReport.model_validate({**r.model_dump(), "units_provider_verified": True})


def stable(report):
    """Everything a historical evaluation reports except the future-record tally."""
    data = report.model_dump(mode="json")
    for key in ("input_trade_count", "not_yet_received_count"):
        data.pop(key)
    return data


FUTURE_RECORDS = {
    "conflicting duplicate": lambda: [trade("t3", SELL, "99", ago=50, lag=50 + 3),
                                       trade("t3", BUY, "3", ago=50, lag=50 + 4)],
    "unknown side": lambda: [trade("later", None, "1", ago=1, lag=3)],
    "different source": lambda: [trade("other", BUY, "1", ago=1, lag=3, source="other")],
    "future dated": lambda: [trade("f", BUY, "5", ago=-30)],
    "huge number": lambda: [trade("huge", BUY, "1" + "0" * 60, ago=1, lag=3)],
    "missing identity": lambda: [trade("t3", BUY, "3", ago=50, lag=60).model_copy(update={
        "provenance": SourceProvenance(source="fixture", source_type="x", received_timestamp=NOW + timedelta(seconds=1))})],
}


@pytest.mark.parametrize("name", FUTURE_RECORDS)
def test_records_received_after_evaluation_cannot_change_an_earlier_evaluation(name):
    baseline = run(known())
    with_future = run(known() + FUTURE_RECORDS[name]())
    assert stable(with_future) == stable(baseline)
    assert with_future.not_yet_received_count == len(FUTURE_RECORDS[name]())
    assert with_future.trusted_for_current_use and with_future.reasons == ()


def test_future_received_records_are_not_validated_so_cannot_raise_for_an_earlier_evaluation():
    wrong_symbol = trade("eth", BUY, "1", ago=1, lag=3, symbol="ETH")
    assert run(known() + [wrong_symbol]).not_yet_received_count == 1
    with pytest.raises(ValueError, match="INSTRUMENT_IDENTITY_MISMATCH"):
        run(known() + [wrong_symbol], evaluation_time=NOW + timedelta(seconds=3), c=config(window=63, session=303))


def test_the_same_future_records_do_apply_once_the_evaluation_time_reaches_them():
    items = known() + FUTURE_RECORDS["unknown side"]()
    later = run(items, evaluation_time=NOW + timedelta(seconds=3), c=config(window=63, session=303))
    assert later.not_yet_received_count == 0 and later.reasons == ("AGGRESSOR_SIDE_UNKNOWN",)
    conflict = FUTURE_RECORDS["conflicting duplicate"]()
    later = run(known() + conflict, evaluation_time=NOW + timedelta(seconds=60), c=config(window=120, session=360))
    assert later.reasons == ("TRADE_IDENTITY_CONFLICT",)


def test_trades_from_different_sources_never_collapse_into_one_identity():
    for other in (trade("t3", BUY, "3", ago=50, source="other"),      # same tid, identical content
                  trade("t3", SELL, "8", ago=49, source="other"),     # same tid, different content
                  trade("zz", BUY, "1", ago=5, source="other")):      # no collision at all
        r = run(known() + [other])
        assert r.reasons == ("MIXED_TRADE_SOURCES",) and r.session_cvd.value is None
        assert r.provenance is None and not r.trusted_for_current_use and r.duplicate_count == 0


def test_same_provider_redelivery_over_either_transport_still_deduplicates():
    redelivered = [trade(t.provenance.source_id, t.side, str(t.quantity), ago=(NOW - t.timestamp).total_seconds(),
                         lag=0.5, source_type="public_info") for t in known()]
    r = run(known() + redelivered)
    assert values(r) == values(run(known())) and r.duplicate_count == 6
    assert r.provenance.source == "fixture" and r.provenance.source_types == ("public_websocket",)


def test_report_preserves_compact_reproducible_provenance_when_serialized():
    r = run(known())
    data = FlowReport.model_validate_json(r.model_dump_json()).provenance
    assert data == r.provenance
    assert (data.source, data.source_types, data.contributing_trade_count) == ("fixture", ("public_websocket",), 5)
    assert (data.earliest_trade_id, data.latest_trade_id) == ("t1", "t5")
    assert data.earliest_event_time == NOW - timedelta(seconds=200) and data.latest_event_time == NOW - timedelta(seconds=2)
    assert data.newest_trade_provenance == known()[-1].provenance and data.digest_algorithm.startswith("sha256")
    assert '"input_digest":"' + data.input_digest + '"' in r.model_dump_json()


def test_input_digest_is_deterministic_and_tracks_contributing_content_only():
    digest = run(known()).provenance.input_digest
    shuffled = known()
    random.Random(3).shuffle(shuffled)
    assert run(shuffled).provenance.input_digest == digest
    assert run(known() + known()).provenance.input_digest == digest                # duplicates
    assert run(known() + [trade("old", BUY, "5", ago=900)]).provenance.input_digest == digest  # outside range
    assert run(known() + FUTURE_RECORDS["unknown side"]()).provenance.input_digest == digest   # not yet received
    formatted = [trade(t.provenance.source_id, t.side, str(t.quantity) + ("0" if "." in str(t.quantity) else ".0"), ago=(NOW - t.timestamp).total_seconds())
                 for t in known()]
    assert run(formatted).provenance.input_digest == digest                          # 1 vs 1.0
    changed = known()
    changed[3] = trade("t3", BUY, "3.1", ago=50)
    assert run(changed).provenance.input_digest != digest
    changed[3] = trade("t3", SELL, "3", ago=50)
    assert run(changed).provenance.input_digest != digest


def test_provenance_is_bounded_regardless_of_input_size():
    many = [trade(f"t{i}", BUY if i % 2 else SELL, "1", ago=2 + i / 100) for i in range(3000)]
    small, large = run(known()), run(many, c=config(window=60, session=300))
    assert large.provenance.contributing_trade_count == 3000
    assert len(large.model_dump_json()) < 2 * len(small.model_dump_json())
    dumped = large.model_dump_json()
    assert "t1500" not in dumped.replace(large.provenance.earliest_trade_id, "").replace(large.provenance.latest_trade_id, "")


def test_provenance_is_kept_for_untrusted_quality_and_absent_when_nothing_contributed():
    stale = run([trade("a", BUY, "1", ago=40)])
    assert stale.session_cvd.value is None and stale.provenance.contributing_trade_count == 1
    for r in (run([]), run(known() + [trade("x", None, "1")])):
        assert r.provenance is None
    r = run(known())
    with pytest.raises(ValidationError, match="provenance"):
        FlowReport.model_validate({**r.model_dump(), "provenance": None})


def retag(trades, **changes):
    """Copies of the trades with provenance fields replaced (receipt lag in seconds via `lag`)."""
    lag = changes.pop("lag", None)
    out = []
    for t in trades:
        fields = {**dict(t.provenance), **changes}
        if lag is not None:
            fields["received_timestamp"] = t.timestamp + timedelta(seconds=lag)
        out.append(t.model_copy(update={"provenance": SourceProvenance(**fields)}))
    return out


def test_digest_binds_receipt_timestamps_that_drive_quality_and_lateness():
    base = run(known())
    # Same event times and source ages, different receipt times: receipt_age differs.
    later_receipt = run(retag(known(), lag=0.5))
    assert later_receipt.quality.receipt_age != base.quality.receipt_age
    assert later_receipt.provenance.input_digest != base.provenance.input_digest
    # A single earlier trade received later (still within tolerance) is also bound.
    moved = known()
    moved[1] = retag([moved[1]], lag=4)[0]
    assert run(moved).provenance.input_digest != base.provenance.input_digest
    # Pushing one past the tolerance changes lateness and, necessarily, the digest.
    late = known()
    late[1] = retag([late[1]], lag=20)[0]
    assert run(late).late_count == 1 and run(late).provenance.input_digest != base.provenance.input_digest


def test_digest_binds_source_transport_symbol_and_trade_id():
    base = run(known()).provenance.input_digest
    assert run(retag(known(), source="other")).provenance.input_digest != base
    assert run(retag(known(), source_type="public_info")).provenance.input_digest != base
    eth = [t.model_copy(update={"symbol": "ETH"}) for t in known()]
    eth_config = config().model_copy(update={"symbol": "ETH"})
    assert run(eth, c=eth_config).provenance.input_digest != base
    renamed = known()
    renamed[2] = retag([renamed[2]], source_id="renamed")[0]
    assert run(renamed).provenance.input_digest != base


def test_digest_encoding_is_unambiguous_for_delimiter_like_content():
    one = run(retag(known(), source="a|b", source_type="c")).provenance.input_digest
    two = run(retag(known(), source="a", source_type="b|c")).provenance.input_digest
    three = run(retag(known(), source='a","b', source_type="c")).provenance.input_digest
    assert len({one, two, three}) == 3


def test_digest_version_and_order_independence_are_preserved():
    r = run(known())
    assert r.provenance.digest_algorithm == "sha256-canonical-trades-v2"
    shuffled = known() + retag(known(), lag=0.0)  # identical redelivery
    random.Random(5).shuffle(shuffled)
    assert run(shuffled).provenance.input_digest == r.provenance.input_digest
    # Which delivery is kept is deterministic: the earliest receipt wins, regardless of order.
    earlier_first = run(retag(known(), lag=0.2) + known()).provenance.input_digest
    assert earlier_first == run(known() + retag(known(), lag=0.2)).provenance.input_digest == r.provenance.input_digest
