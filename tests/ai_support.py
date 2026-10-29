"""Shared V1-C14 test fixtures. Everything is offline.

REAL: C10 reports from the real C07-C10 engines (``test_regime`` builders); C11 reports from the real C11
engine over synthetic test wallets (test-only addresses, no real account); C12 macro and ETF reports from
the real C12 engines over the repository's real BLS/Fed fixtures; C13 reports from the real C13 engine with
the real C12 macro adapter.
SYN: a C13 regulatory result is re-timed to T and stripped of its synthetic-record marker only where a test
needs a BTC-applicable claim; the C12 ETF mapping is the shipped one re-dated before T. Each such edit is
named where it happens.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import errno
import json
import os
import socket
import threading

import pytest

from news_support import claim, curate, official, TEST_POLICY
from test_macro_evidence import APPROVED, BLS_REAL, CAL, REAL, SERIES, sched, with_value
from test_regime import NOW as T, classify as c10_classify, liquidity as c10_liquidity
from traid.ai.models import TaskId
from traid.ai.provider import ContentBlock, ModelReply, ProviderDescription, ProviderFailure, ProviderSession
from traid.ai.records import OsOps
from traid.ai.service import Clock
from traid.domain.models import SourceProvenance
from traid.macro import PROVIDERS, US_SPOT_BTC_ETFS, AssetEtfMapping, EtfMetric, EtfObservation, ValueBasis
from traid.macro.bls import parse_bls_response
from traid.macro.etf import UNITS, build_etf_evidence
from traid.macro.evidence import build_macro_evidence
from traid.news import OfficialEvidence, VerificationReport, verify
from traid.news.macro_adapter import C12MacroEvaluator
from traid.whales import BtcPosition, PositionSnapshot, ScoreWeight, SmartMoneyRules, WalletEntry, Watchlist, \
    WhaleRules, analyze_whales

UTC = timezone.utc
D = Decimal
T1 = TaskId.BTC_MARKET_STATE
T2 = TaskId.MACRO_CONTEXT
assert T == datetime(2026, 10, 15, 12, 5, tzinfo=UTC)


# --------------------------------------------------------------------- environment
@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No network and no real AWS configuration in any C14 test."""
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted in a C14 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE",
                 "AWS_DEFAULT_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/nonexistent/traid-c14-test-config")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/nonexistent/traid-c14-test-credentials")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


# ------------------------------------------------------------------------------ C10
def market_state(**kw):
    return c10_classify(**kw)


# ------------------------------------------------------------------------------ C11
def wallet(i: int) -> str:
    return f"0x{i + 1:040x}"


def whales(positions, *, at=T, stale=(), extra_flat=0):
    """positions: list of (side, notional) with side in "L", "S", "F". Wallet i holds positions[i]."""
    entries, snaps = [], []
    for i, (side, notional) in enumerate(list(positions) + [("F", "0")] * extra_flat):
        a = wallet(i)
        entries.append(WalletEntry(address=a, label=f"test-{i}", account_role="user", rationale="C14 test wallet",
                                   source="test", added_at=at - timedelta(days=1)))
        when = at - (timedelta(minutes=30) if i in stale else timedelta(seconds=30))
        size = {"L": D(1), "S": D(-1), "F": D(0)}[side]
        pos = None if side == "F" else BtcPosition(size=size, entry_price=D(100000), position_value=D(notional),
                                                   unrealized_pnl=D(0), liquidation_price=None, leverage_type="cross",
                                                   leverage=2, margin_used=D(1))
        snaps.append(PositionSnapshot(address=a, snapshot_time=when, btc_position=pos, account_value=D(1000000),
                                      provenance=SourceProvenance(source="hyperliquid", source_type="public_info",
                                                                  source_id="clearinghouseState", source_timestamp=when,
                                                                  received_timestamp=when + timedelta(seconds=1))))
    rules = WhaleRules(rules_version="c14-test-1", max_snapshot_age=timedelta(minutes=5),
                       max_history_age=timedelta(minutes=5), activity_window=timedelta(hours=1),
                       smart_money=SmartMoneyRules(methodology_version="sm-c14-test", evaluation_window=timedelta(hours=2),
                                                   min_closing_fills=2, weights=()))
    return analyze_whales(evaluation_time=at, watchlist=Watchlist.build("c14-test-watchlist", entries), rules=rules,
                          snapshots=tuple(snaps))


# ------------------------------------------------------------------------------ C12
CPI_AT_T = (sched("2026-09", date(2026, 10, 15), hh=8, mm=0), sched("2026-10", date(2026, 11, 10)))   # 12:00Z <= T


def bls(received=T - timedelta(minutes=3), payload=BLS_REAL):
    return parse_bls_response(payload, SERIES, received)


def macro(*, caps=None, statements=REAL, calendars=(CAL,), schedules=CPI_AT_T, at=T):
    return build_macro_evidence(evaluation_time=at, schedules=tuple(schedules),
                                bls_captures=tuple(bls() if caps is None else caps),
                                fomc_statements=tuple(statements), fomc_calendars=tuple(calendars))


# SYN: the shipped mapping re-dated before T, so that it is knowable at T.
MAPPING = AssetEtfMapping.model_validate({**US_SPOT_BTC_ETFS.model_dump(), "mapping_version": "c14-test-2026-10-01",
                                          "identity_retrieved_on": date(2026, 10, 1),
                                          "available_at": datetime(2026, 10, 1, 12, tzinfo=UTC),
                                          "available_at_evidence": "C14 test re-dating of the shipped mapping"})


def etf_obs(ticker, raw="1000000", metric=EtfMetric.NET_FLOW_USD, day=date(2026, 10, 14)):
    return EtfObservation(provider_id="test_provider", ticker=ticker, metric=metric, trade_date=day, raw_value=raw,
                          value=D(raw), unit=UNITS[metric], basis=ValueBasis.REPORTED, methodology="test fixture",
                          as_of=None, published_at=None,
                          provenance=SourceProvenance(source="test_provider", source_type="test",
                                                      received_timestamp=T - timedelta(hours=1)))


def etf(observations=(), *, approved=True, mapping=MAPPING, at=T):
    providers = PROVIDERS + ((APPROVED,) if approved else ())
    return build_etf_evidence(evaluation_time=at, mappings=(mapping,), providers=providers,
                              observations=tuple(observations))


# ------------------------------------------------------------------------------ C13
def macro_claim(frame_type, identity, facts, *, text="macro claim for C14", source_id="item-1"):
    c = claim(text, received=T - timedelta(hours=1), source_id=source_id)
    return c, curate(c, [("e", frame_type, identity)], [("p", "e", facts)])


def news(pairs, macro_report, *, at=T) -> VerificationReport:
    claims = tuple(c for c, _ in pairs)
    curations = tuple(cur for _, cur in pairs)
    return verify(claims=claims, curations=curations, evidence=OfficialEvidence(), evaluation_time=at,
                  macro=C12MacroEvaluator(macro_report))


def cpi_claim(value="336.940", source_id="cpi-1"):
    return macro_claim("MACRO_VALUE", {"series": "CUUR0000SA0", "period": "2026-09",
                                       "scope": "AS_PUBLISHED_AT_SOME_RECEIPT"}, [("VALUE", value)],
                       source_id=source_id)


def fomc_claim(extra=(("TARGET_RANGE", "3.75-4.00"),), source_id="fomc-1", action="RAISE"):
    return macro_claim("FOMC_DECISION", {"board_date": "2026-09-16"}, [("ACTION", action), *extra], source_id=source_id)


def regulatory_news(text, subjects, action, *, at=T) -> VerificationReport:
    """REAL C13 run on the real official fixtures with the synthetic manual records; then SYN: re-timed to T,
    fund-resolution availability set before T and the synthetic marker removed, so C14 sees a
    BTC-applicable result. Tests that need the marker use the unedited ``verify`` output."""
    c = claim(text)
    cur = curate(c, [("e", "REG_EVENT", {"subjects": tuple(subjects), "action": action})],
                 [("p", "e", [("ACTION", action)])])
    real = verify(claims=(c,), curations=(cur,), evidence=official(), evaluation_time=datetime(2026, 10, 24, tzinfo=UTC),
                  policy=TEST_POLICY)
    data = real.model_dump()
    data["evaluation_time"] = at
    for r in data["results"]:
        r["evaluation_time"] = at
        r["limitations"] = [x for x in r["limitations"] if x != "SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED"]
        r["reasons"] = [x for x in r["reasons"] if x != "SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED"]
        for fr in r["frames"]:
            for res in fr["fund_resolutions"]:
                res["available_at"] = at - timedelta(days=1)
    return VerificationReport.model_validate(data), real


def false_regulatory_news(*, at=T) -> VerificationReport:
    """REAL C13 FALSE result (FR 2024-00743 did not disapprove SR-NASDAQ-2023-016), then SYN: re-timed to T,
    synthetic marker removed, and the IBIT fund resolution of the real CONFIRMED fund claim attached to its
    frame, so the claim is BTC-applicable for C14."""
    c = claim("FR 2024-00743 disapproved SR-NASDAQ-2023-016 on January 10, 2024", source_id="false-1")
    cur = curate(c, [("e", "REG_DOC", {"document_number": "2024-00743"})],
                 [("p", "e", [("ACTION", "DISAPPROVED"), ("SUBJECT", "SR-NASDAQ-2023-016"),
                              ("DATE", "2024-01-10", "ORDERED_ON")])])
    real = verify(claims=(c,), curations=(cur,), evidence=official(), evaluation_time=datetime(2026, 10, 24, tzinfo=UTC),
                  policy=TEST_POLICY)
    fund, _ = regulatory_news("SEC approved the rule change to list IBIT", ["FUND:IBIT"], "RULE_CHANGE_APPROVED", at=at)
    resolution = fund.results[0].frames[0].fund_resolutions[0].model_dump()
    data = real.model_dump()
    data["evaluation_time"] = at
    for r in data["results"]:
        r["evaluation_time"] = at
        r["limitations"] = [x for x in r["limitations"] if x != "SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED"]
        r["reasons"] = [x for x in r["reasons"] if x != "SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED"]
        for fr in r["frames"]:
            if fr["frame_type"] == "REG_DOC":
                fr["fund_resolutions"] = [resolution]
    return VerificationReport.model_validate(data)


def merge_news(*reports) -> VerificationReport:
    data = reports[0].model_dump()
    for r in reports[1:]:
        data["results"] += r.model_dump()["results"]
        data["rejections"] += r.model_dump()["rejections"]
    return VerificationReport.model_validate(data)


# --------------------------------------------------------------------- fake provider
DESCRIPTION = ProviderDescription(provider="fake", api="fake", model_id="fake-model-1", source_region=None,
                                  approved_destination_regions=(), destinations_verified_on=None)


def reply(tool_input, *, stop="tool_use", role="assistant", extra_blocks=(), name="submit_interpretation",
          tool_id="tool-1", raw_size=None, sends=1) -> ModelReply:
    blocks = (ContentBlock(kind="tool_use", tool_name=name, tool_use_id=tool_id, tool_input=tool_input),) + tuple(extra_blocks)
    raw = json.dumps({"input": tool_input}, default=str)
    return ModelReply(stop_reason=stop, role=role, blocks=blocks, raw_text=raw,
                      raw_size=len(raw.encode()) if raw_size is None else raw_size, input_tokens=10, output_tokens=20,
                      total_tokens=30, provider_latency_ms=5, request_id="req-1", http_sends=sends)


class FakeProvider:
    """Scripted, provider-neutral stand-in. Each script entry is a tool-input dict, a ModelReply, a
    ProviderFailure or a callable(request) returning one of those."""
    def __init__(self, script=(), *, setup=None, gates=None):
        self.script = list(script)
        self.setup_result = setup
        self.gates = gates or {}         # attempt -> (entered Event, release Event)
        self.calls = []
        self.requests = []
        self.threads = []

    def describe(self):
        return DESCRIPTION

    def setup(self):
        return self.setup_result if self.setup_result is not None else ProviderSession()

    def send(self, session, request, attempt, connect_timeout, read_timeout):
        self.calls.append((attempt, connect_timeout, read_timeout))
        self.requests.append(request)
        self.threads.append(threading.get_ident())
        if attempt in self.gates:
            entered, release = self.gates[attempt]
            entered.set()
            release.wait(10)
        item = self.script.pop(0)
        if callable(item) and not isinstance(item, (ModelReply, ProviderFailure)):
            item = item(request)
        return reply(item) if isinstance(item, dict) else item


def failure(code, retry_safe=False, sends=1):
    return ProviderFailure(code=code, retry_safe=retry_safe, http_sends=sends)


# ------------------------------------------------------------------------- fake clock
class FakeClock(Clock):
    """Monotonic time set by the test; it can return exactly the deadline. The caller's wait returns only
    when (its event is set or time >= its deadline) and ``caller_gate`` is open."""
    def __init__(self, start=1000.0, wall=T + timedelta(seconds=30)):
        self._now = start
        self._start = start
        self._wall = wall
        self._cond = threading.Condition()
        self.caller_gate = threading.Event()
        self.caller_gate.set()
        self.waiting = threading.Event()

    def monotonic(self):
        with self._cond:
            return self._now

    def wall(self):
        with self._cond:
            return self._wall + timedelta(seconds=self._now - self._start)

    def set(self, t):
        with self._cond:
            self._now = t
            self._cond.notify_all()

    def advance(self, dt):
        with self._cond:
            self._now += dt
            self._cond.notify_all()

    def wait_until(self, event, deadline):
        with self._cond:
            self.waiting.set()
            while not ((event.is_set() or self._now >= deadline) and self.caller_gate.is_set()):
                self._cond.wait(0.005)

    sleep_gate = None       # (entered Event, release Event): block the worker's backoff for a race

    def sleep(self, seconds):
        if self.sleep_gate is not None:
            entered, release = self.sleep_gate
            entered.set()
            release.wait(10)
            return
        self.advance(seconds)


# ---------------------------------------------------------------------- fake filesystem
class FaultyOps(OsOps):
    """Real filesystem calls with injectable failures and blocking points."""
    def __init__(self, *, fail=None, block=None):
        self.fail = dict(fail or {})        # step -> OSError
        self.block = dict(block or {})      # step -> (entered Event, release Event)
        self.calls = []
        self.dir_fds = set()
        self.threads = []

    def _step(self, name):
        self.calls.append(name)
        self.threads.append(threading.get_ident())
        if name in self.block:
            entered, release = self.block[name]
            entered.set()
            release.wait(10)
        if name in self.fail:
            raise self.fail[name]

    def open(self, path, flags, mode=0o777, *, dir_fd=None):
        if flags & os.O_DIRECTORY:
            self._step("open_root")
            fd = super().open(path, flags, mode, dir_fd=dir_fd)
            self.dir_fds.add(fd)
            return fd
        self._step("open_stage")
        return super().open(path, flags, mode, dir_fd=dir_fd)

    def write(self, fd, data):
        self._step("write")
        return super().write(fd, data)

    def fsync(self, fd):
        self._step("fsync_dir" if fd in self.dir_fds else "fsync_stage")
        super().fsync(fd)

    def link(self, src, dst, *, dir_fd):
        self._step("link")
        super().link(src, dst, dir_fd=dir_fd)

    def unlink(self, path, *, dir_fd):
        self._step("unlink")
        super().unlink(path, dir_fd=dir_fd)


def oserror(code=errno.EIO):
    return OSError(code, os.strerror(code))


@pytest.fixture
def record_root(tmp_path):
    root = tmp_path / "c14-records"
    root.mkdir(mode=0o700)
    return root.resolve()


# ------------------------------------------------------------------------ tool output
def items(request: dict):
    return {i["evidence_id"]: i for i in request["structured"] + request["contextual"]}


def valid_output(request: dict, **override) -> dict:
    """A minimal output that satisfies every rule for the given request."""
    its = items(request)
    summary_cat = request["required"]["summary_category"]
    summary_ref = next(e for e, i in its.items() if i["category"] == summary_cat and i["tier"] == "STRUCTURED")
    cat_ref = next(f"CAT:{c['category']}" for c in request["categories"]
                   if c["state"] not in ("INCLUDED", "NOT_USED_BY_TASK"))
    out = {
        "summary": {"statement": f"The evidence at the evaluation time is described in {summary_ref}.",
                    "refs": [summary_ref], "numbers": []},
        "anchor_assessments": [
            {"anchor_id": a["anchor_id"], "stance": "SUPPORTS",
             "statement": f"Anchor {a['anchor_id']} is consistent with the cited evidence in {a['evidence_id']}.",
             "evidence_ids": [a["evidence_id"]], "numbers": []} for a in request["anchors"]],
        "context_notes": [],
        "claim_notes": [
            {"claim_id": c["claim_id"], "statement": f"Claim {c['claim_id']} has the assessed state {c['state']}.",
             "refs": [c["claim_id"]] + ([f["fact_id"] for fr in c["frames"] for f in fr["facts"]
                                         if f["outcome"] in ("CONTRADICTED", "SUPERSEDED")][:1]
                                        if c["state"] in ("FALSE", "MISLEADING") else []),
             "numbers": []} for c in request["assessed_claims"]],
        "uncertainties": [{"statement": "Some evidence categories are unavailable or only partly included.",
                           "refs": [cat_ref], "numbers": []}],
    }
    out.update(override)
    return out
