"""F5: C11 reaches the model only as one gated gross notional (USDC) or as the constant
WHALE_EVIDENCE_NOT_RELEASED. Checked on the exact request bytes built from real C11 reports."""
from collections import defaultdict
import itertools
import json
import re

import pytest

from ai_support import (  # noqa: F401
    T, T1, FakeProvider, market_state, offline, record_root, valid_output, wallet, whales,
)
from traid.ai import AIService, AIStatus, EvidenceInputs, RecordStore, select
from traid.whales import WhaleReport

C10 = market_state()


def request(report):
    sel = select(T1, T, EvidenceInputs(market_state=C10, whales=report))
    assert sel.skip is None
    return sel, sel.request_json


def c11_part(text):
    req = json.loads(text)
    items = [i for i in req["structured"] + req["contextual"] if i["category"] == "C11"]
    cat = next(c for c in req["categories"] if c["category"] == "C11")
    unavailable = [u for u in req["unavailable"] if u["category"] == "C11"]
    return items, cat, unavailable


def released(report):
    items, cat, _ = c11_part(request(report)[1])
    if not items:
        assert cat == {"category": "C11", "state": "NOT_RELEASED", "reasons": ["WHALE_EVIDENCE_NOT_RELEASED"]}
        return "ABSENT"
    (item,) = items
    (v,) = item["values"]
    assert v["field_path"] == "aggregate.gross_notional" and v["unit"] == "USDC"
    return f"GROSS({v['value']})"


L, S, F = "L", "S", "F"


@pytest.mark.parametrize("positions,expected", [
    ([(L, "100")] * 5 + [(F, "0")], "GROSS(500)"),                     # Codex audit 6: 5 long + 1 FLAT
    ([(L, "100")] * 5 + [(S, "37")], "GROSS(537)"),                    # Codex audit 4: 5 long + 1 short
    ([(L, "85")] + [(S, "40")] * 5, "GROSS(285)"),
    ([(L, "100")] * 4 + [(S, "37")] * 2, "GROSS(474)"),
    ([(L, "100")] * 6 + [(S, "90")] * 5, "GROSS(1050)"),               # Codex audit 5: 11 wallets, correlated histograms
    ([(L, "100")] * 5 + [(L, "0")], "GROSS(500)"),                     # 6 long, one at $0: still 5 positive
    ([(L, "100")] * 6, "GROSS(600)"),
    ([(L, "500")] + [(L, "100")] * 5, "GROSS(1000)"),                  # dominance exactly 50% passes
])
def test_gross_only_release(positions, expected):
    assert released(whales(positions)) == expected


@pytest.mark.parametrize("positions", [
    [(L, "100")] * 4 + [(L, "0")],                                     # 5 long with one $0: |P| = 4
    [(L, "1000")] + [(L, "100")] * 5,                                  # dominated: 1000 of 1500
    [(L, "501")] + [(L, "100")] * 5,                                   # just above 50%
    [(L, "100")] * 4,                                                  # 4 eligible
    [(L, "100")] * 3 + [(F, "0")] * 3,
    [(L, "100")] * 4 + [(S, "0")] + [(F, "0")] * 4,
])
def test_absent_cases(positions):
    assert released(whales(positions)) == "ABSENT"
    assert released(None) == "ABSENT"


def _tamper(report, path, value):
    data = report.model_dump()
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return WhaleReport.model_validate(data)


def test_inconsistent_or_invalid_reports_are_the_same_constant_absence_byte_for_byte():
    base = whales([(L, "100")] * 6)
    variants = {
        "no report": None,
        "sum mismatch": _tamper(base, ["aggregate", "gross_notional", "value"], base.aggregate.gross_notional.value + 1),
        "flat not zero": _tamper(whales([(L, "100")] * 6 + [(F, "0")]), ["wallets", 6, "exposure", "provider_notional", "value"], 5),
        "fresh count": _tamper(base, ["aggregate", "wallets_available"], 7),
        "wrong time": whales([(L, "100")] * 6, at=T.replace(minute=6)),
        "wrong version": _tamper(base, ["engine_version"], "c11-whale-intelligence-0"),
        "too few": whales([(L, "100")] * 4),
        "dominated": whales([(L, "1000")] + [(L, "100")] * 5),
        "stale": whales([(L, "100")] * 6, stale=(0, 1)),
    }
    texts = {name: request(r)[1] for name, r in variants.items()}
    assert len(set(texts.values())) == 1, {k: len(v) for k, v in texts.items()}     # identical request bytes
    gates = {name: request(r)[0].bindings.whale_gate for name, r in variants.items()}
    assert gates["sum mismatch"] == "INCONSISTENT:SUMS" and gates["flat not zero"] == "INCONSISTENT:FLAT_NOT_ZERO"
    assert gates["fresh count"] == "INCONSISTENT:FRESH_COUNT" and gates["no report"] == "NOT_SUPPLIED"
    assert gates["wrong time"] == "REPORT_REJECTED:EVALUATION_TIME_MISMATCH"
    assert gates["too few"] == "FEWER_THAN_MIN_CONTRIBUTORS" and gates["dominated"] == "DOMINATED_BY_ONE_CONTRIBUTOR"


def test_released_bytes_depend_only_on_the_gross_value():
    a = whales([(L, "100")] * 5 + [(S, "37")])                             # 5 long, 1 short
    b = whales([(L, "137")] + [(S, "100")] * 4, extra_flat=3)              # 1 long, 4 short, 3 flat
    assert released(a) == released(b) == "GROSS(537)"
    assert request(a)[1] == request(b)[1]                                  # counts, sides, flats invisible


def test_request_bytes_hold_no_wallet_side_count_time_or_watchlist_data():
    report = whales([(L, "100")] * 6 + [(S, "90")] * 5, extra_flat=2)
    sel, text = request(report)
    items, _, _ = c11_part(text)
    (item,) = items
    assert set(item) == {"evidence_id", "category", "tier", "kind", "subject", "state", "attributes", "values",
                         "values_withheld", "times", "reasons", "limitations"}
    assert item["tier"] == "CONTEXTUAL" and item["attributes"] == [] and item["times"] == [] and item["reasons"] == []
    assert item["limitations"] == list(WhaleReport.model_fields["limitations"].default)
    assert not re.search(r"0x[0-9a-fA-F]{40}", text)
    for secret in (report.watchlist_version, report.watchlist_digest, report.rules_digest, "c14-test-1", "test-0",
                   "2026-10-15T12:04:30Z", '"LONG"', '"SHORT"', '"FLAT"', "wallets_available", "long_notional",
                   "net_notional", "largest_wallet_share", "concentration_hhi", "PARTIAL_WATCHLIST"):
        assert secret not in text, secret
    assert '"value":"1050"' in text.replace(" ", "")
    assert sel.bindings.whale_contributors == tuple(sorted(wallet(i) for i in range(11)))
    assert sel.bindings.watchlist_digest == report.watchlist_digest


def test_exhaustive_worlds_pin_no_small_group_statistic():
    """PRIV-G6 on real C11 reports: every multiset of up to 6 wallets over long/short notionals {0, 37, 100}
    and FLAT. Within each observable output class no side group of 1-4 wallets has a constant count or sum."""
    kinds = [(L, "0"), (L, "37"), (L, "100"), (S, "37"), (S, "100"), (F, "0")]
    classes = defaultdict(list)
    for n in range(0, 7):
        for world in itertools.combinations_with_replacement(range(len(kinds)), n):
            positions = [kinds[k] for k in world]
            out = released(whales(positions)) if positions else released(None)
            groups = {side: [int(v) for s, v in positions if s == side] for side in (L, S, F)}
            classes[out].append({side: (len(v), sum(v)) for side, v in groups.items()})
    pinned = []
    for out, worlds in classes.items():
        for side in (L, S, F):
            counts = {w[side][0] for w in worlds}
            sums = {w[side][1] for w in worlds}
            sizes = [w[side][0] for w in worlds]
            if len(counts) == 1 and 1 <= next(iter(counts)) <= 4:
                pinned.append((out, side, "count"))
            if len(sums) == 1 and all(1 <= s <= 4 for s in sizes):
                pinned.append((out, side, "sum"))
    assert len(classes) > 10 and pinned == []


def test_t1_stays_valid_from_c10_when_c11_is_absent(record_root):
    inputs = EvidenceInputs(market_state=C10, whales=whales([(L, "100")] * 3))
    provider = FakeProvider([lambda r: valid_output(json.loads(r.user_text))])
    result = AIService(provider, RecordStore(record_root)).interpret(T1, T, inputs)
    assert result.status is AIStatus.VALID
    assert any(m.subject == "C11" and m.reasons == ("WHALE_EVIDENCE_NOT_RELEASED",)
               for m in result.interpretation.missing_information)


def test_an_address_anywhere_in_the_request_stops_the_call():
    from ai_support import macro, news, cpi_claim
    from traid.news import VerificationReport
    rep = macro()
    real = news([cpi_claim()], rep)
    data = real.model_dump()
    data["results"][0]["reasons"] = ["SEE_" + wallet(3)]
    injected = VerificationReport.model_validate(data)
    sel = select(T1, T, EvidenceInputs(market_state=C10, macro=rep, news=injected))
    assert sel.skip == ("PRIVACY_GUARD",) and sel.request is None
