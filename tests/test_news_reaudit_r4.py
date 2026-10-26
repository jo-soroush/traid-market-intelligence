"""Regression tests for the final C13 audit finding: curation supersession cycles (R4 rule A3).

A `supersedes` cycle anywhere among the curations admitted at T is CONFLICTING_CURATIONS. An
independent acyclic head must not hide it (pre-fix: the cycle members vanished from the heads and the
independent head restored CONFIRMED). Acyclic correction chains collapse to their heads as before; only
curations available at T count; the result is invariant under input order and exact duplicates.

REAL official components and C12-free claims; SYNTHETIC_TEST manual records under TEST_POLICY, plus the
production DEFAULT_POLICY where it matters.
"""
from datetime import timedelta
import itertools

import pytest

from news_support import NOW, TEST_POLICY, _no_network, claim, curate, official  # noqa: F401  (autouse fixture)
from traid.news import verify
from traid.news.models import DEFAULT_POLICY, VerificationState

S = VerificationState
E = official()
CONFLICT = ("CONFLICTING_CURATIONS",)
C = claim("SEC approved SR-NASDAQ-2023-016")
RECEIVED = C.claim_received_at


def cur(cid, action="APPROVED", supersedes=None, at=None):
    return curate(C, [("e", "REG_EVENT", {"subjects": ("SR-NASDAQ-2023-016",), "action": action})],
                  [("p", "e", [("ACTION", action)])], curation_id=cid, supersedes=supersedes, curated_at=at)


def report(curations, T=NOW, policy=TEST_POLICY):
    return verify(claims=(C,), curations=tuple(curations), evidence=E, evaluation_time=T, policy=policy)


def result(curations, T=NOW, policy=TEST_POLICY):
    return report(curations, T, policy).results[0]


def cycle(n, action="DISAPPROVED", prefix="cyc"):
    """n curations, each superseding the next, the last superseding the first (n = 1: a self-cycle)."""
    ids = [f"{prefix}-{k}" for k in range(n)]
    return [cur(i, action, supersedes=ids[(k + 1) % n]) for k, i in enumerate(ids)]


HEAD = cur("cur-head")                                                   # independent, valid, CONFIRMED on its own


def test_the_independent_head_alone_is_confirmed():
    r = result([HEAD])
    assert r.state is S.CONFIRMED and r.curation_id == "cur-head"


@pytest.mark.parametrize("n", [1, 2, 3, 4, 7])
@pytest.mark.parametrize("action", ["APPROVED", "DISAPPROVED"])
def test_a_cycle_alone_is_conflicting(n, action):
    r = result(cycle(n, action))
    assert r.state is S.UNVERIFIED and r.reasons == CONFLICT and r.curation_id is None


@pytest.mark.parametrize("n", [1, 2, 3, 4, 7])
@pytest.mark.parametrize("action", ["APPROVED", "DISAPPROVED"])
def test_a_cycle_beside_an_independent_valid_head_is_still_conflicting(n, action):
    """The audit counterexample: pre-fix, the head survived alone and the claim was CONFIRMED.
    APPROVED members normalize like the head, so even an agreeing cycle is not silently accepted."""
    r = result(cycle(n, action) + [HEAD])
    assert r.state is S.UNVERIFIED and r.reasons == CONFLICT and r.curation_id is None


def test_a_cycle_with_an_acyclic_feeder_and_an_independent_head_is_conflicting():
    feeder = cur("cur-feeder", "APPROVED", supersedes="cyc-0")             # points into the cycle; not on it
    r = result(cycle(3) + [feeder, HEAD])
    assert r.reasons == CONFLICT


def test_two_curations_sharing_an_id_where_one_closes_a_cycle():
    """Distinct curations may share an id; edges are a set, so any order finds the cycle."""
    a = cur("cur-a", "APPROVED", supersedes="cur-b")
    b = cur("cur-b", "APPROVED")
    b_cyclic = cur("cur-b", "APPROVED", supersedes="cur-a")
    for order in itertools.permutations([a, b, b_cyclic, HEAD]):
        assert result(order).reasons == CONFLICT


@pytest.mark.parametrize("n", [1, 2, 3])
def test_permutation_invariance_of_the_complete_report(n):
    items = cycle(n) + [HEAD, cur("cur-feeder", supersedes="cyc-0")]
    reference = report(items).model_dump_json()
    for order in itertools.permutations(items):
        assert report(order).model_dump_json() == reference


@pytest.mark.parametrize("n", [1, 2, 3])
def test_exact_duplicates_never_change_the_complete_report(n):
    items = cycle(n) + [HEAD]
    reference = report(items).model_dump_json()
    for k in (2, 3):
        assert report(items * k).model_dump_json() == reference
        assert report(list(reversed(items)) * k).model_dump_json() == reference
    assert result(items).reasons == CONFLICT


def test_the_record_closing_a_cycle_counts_only_from_its_availability():
    """Point in time: before the closing curation is available it is only counted, the chain is acyclic,
    and the agreeing heads give CONFIRMED; at and after its availability the cycle is CONFLICTING."""
    first = cur("cur-x", "APPROVED", supersedes="cur-y", at=RECEIVED)        # cur-y not yet curated: chain end
    closing_at = RECEIVED + timedelta(hours=1)
    closing = cur("cur-y", "APPROVED", supersedes="cur-x", at=closing_at)
    items = [first, closing, HEAD]
    before = result(items, T=closing_at - timedelta(microseconds=1))
    assert before.state is S.CONFIRMED and before.excluded_after_evaluation.curations == 1
    assert report(items, T=closing_at - timedelta(microseconds=1)).model_dump_json() == \
        report([first, HEAD], T=closing_at - timedelta(microseconds=1)).model_dump_json().replace(
            '"curations":0', '"curations":1')
    for T in (closing_at, closing_at + timedelta(days=1)):
        at = result(items, T=T)
        assert at.reasons == CONFLICT and at.excluded_after_evaluation.curations == 0


def test_legitimate_acyclic_correction_chains_collapse_to_their_head():
    wrong = cur("cur-1", "DISAPPROVED", at=RECEIVED)
    fixed = cur("cur-2", "APPROVED", supersedes="cur-1", at=RECEIVED + timedelta(minutes=1))
    refined = cur("cur-3", "APPROVED", supersedes="cur-2", at=RECEIVED + timedelta(minutes=2))
    for order in itertools.permutations([wrong, fixed, refined]):
        r = result(order)
        assert r.state is S.CONFIRMED and r.curation_id == "cur-3"
    r = result([wrong, fixed, refined, HEAD])                               # agreeing independent head: compared
    assert r.state is S.CONFIRMED and r.curation_id in {"cur-3", "cur-head"}
    r = result([wrong, fixed, refined, cur("cur-other", "DISAPPROVED")])  # disagreeing independent head
    assert r.reasons == CONFLICT
    r = result([wrong, cur("cur-2", "APPROVED", supersedes="cur-1", at=RECEIVED + timedelta(minutes=1))])
    assert r.state is S.CONFIRMED and r.curation_id == "cur-2"
    assert result([cur("cur-dangling", supersedes="cur-never-admitted"), HEAD]).state is S.CONFIRMED


def test_production_policy_without_synthetic_records_also_fails_closed_on_a_cycle():
    """Under DEFAULT_POLICY no document qualifies (no human record is in the evidence), so nothing is
    CONFIRMED; the cycle is still reported as the curation conflict, never as an evidence outcome."""
    assert result(cycle(2) + [HEAD], policy=DEFAULT_POLICY).reasons == CONFLICT
    plain = result([HEAD], policy=DEFAULT_POLICY)
    assert plain.state is not S.CONFIRMED and plain.reasons != CONFLICT
