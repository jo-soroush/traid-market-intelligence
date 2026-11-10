"""AT-AI-0 (C15 Phase 1 contract v3.1, section 12): C14 ``select`` must be deterministic for identical explicit
inputs before any replay-based AI binding may be built on it.

The real C14 ``select`` and the real C07-C14 report builders are used: nothing is mocked. Offline (the shared
``offline`` fixture refuses network access).
"""
from dataclasses import fields, is_dataclass
import enum
import json
import os
from pathlib import Path
import subprocess
import sys

from pydantic import BaseModel
import pytest

from ai_support import (  # noqa: F401
    MAPPING, T1, T2, T, cpi_claim, etf, fomc_claim, macro, market_state, merge_news, news, offline,
    false_regulatory_news, whales,
)
from traid.ai import EvidenceInputs, select

ROOT = Path(__file__).resolve().parents[1]


def full_inputs() -> dict:
    rep = macro()
    return dict(market_state=market_state(), whales=whales([("L", "100")] * 6), macro=rep, etf=etf(),
                etf_mapping=MAPPING,
                news=merge_news(news([cpi_claim(), fomc_claim()], rep), false_regulatory_news()))


def canon(value):
    """Order-free, JSON-able form of a selection component (frozensets have hash-seed dependent repr)."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: canon(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): canon(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted((canon(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, default=str))
    if isinstance(value, (tuple, list)):
        return [canon(v) for v in value]
    if isinstance(value, enum.Enum):
        return value.value
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)


def fingerprint(task, inputs: dict) -> dict:
    s = select(task, T, EvidenceInputs(**inputs))
    return {
        "skip": s.skip,
        "request": None if s.request is None else s.request.model_dump_json(),
        "request_sha256": s.request_sha256,
        "bindings": s.bindings.model_dump_json(),
        "excluded": [e.model_dump_json() for e in s.excluded],
        "context": None if s.context is None else canon(s.context),
    }


@pytest.mark.parametrize("task", [T1, T2])
def test_at_ai_0_repeated_select_returns_identical_request_digest_bindings_and_exclusions(task):
    inputs = full_inputs()
    first = select(task, T, EvidenceInputs(**inputs))
    assert first.skip is None and first.request is not None and first.context is not None
    for _ in range(3):
        again = select(task, T, EvidenceInputs(**inputs))
        assert again.skip == first.skip
        assert again.request == first.request                       # EvidenceRequest, model equality
        assert again.request_json == first.request_json
        assert again.request_sha256 == first.request_sha256
        assert again.bindings == first.bindings                     # PrivateBindings
        assert again.excluded == first.excluded                     # excluded evidence
        assert again.context == first.context
    assert first.bindings.report_digests and first.bindings.handle_sources


def test_at_ai_0_equal_but_separately_built_inputs_give_identical_selection():
    a, b = select(T1, T, EvidenceInputs(**full_inputs())), select(T1, T, EvidenceInputs(**full_inputs()))
    assert (a.request, a.request_sha256, a.bindings, a.excluded, a.context) == \
           (b.request, b.request_sha256, b.bindings, b.excluded, b.context)


def test_at_ai_0_selection_does_not_mutate_its_inputs():
    inputs = full_inputs()
    before = {k: v.model_dump_json() for k, v in inputs.items()}
    select(T1, T, EvidenceInputs(**inputs))
    assert {k: v.model_dump_json() for k, v in inputs.items()} == before


def test_at_ai_0_excluded_evidence_is_exercised_and_stable():
    inputs = dict(full_inputs(), whales=whales([("L", "100")] * 6, stale=(0,)))
    a, b = select(T1, T, EvidenceInputs(**inputs)), select(T1, T, EvidenceInputs(**inputs))
    assert a.excluded, "the fixture must actually exclude evidence"
    assert a.excluded == b.excluded and a.bindings == b.bindings and a.request_sha256 == b.request_sha256


def test_at_ai_0_selection_is_stable_across_processes_and_hash_seeds():
    here = json.dumps([fingerprint(T1, full_inputs()), fingerprint(T2, full_inputs())], sort_keys=True, default=str)
    script = ("import json, test_fusion_ai_select_determinism as m\n"
              "print(json.dumps([m.fingerprint(m.T1, m.full_inputs()), m.fingerprint(m.T2, m.full_inputs())], "
              "sort_keys=True, default=str))")
    for seed in ("0", "1", "424242"):
        env = dict(os.environ, PYTHONHASHSEED=seed,
                   PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")]))
        out = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, cwd=ROOT)
        assert out.returncode == 0, out.stderr[-2000:]
        assert out.stdout.strip() == here, seed
