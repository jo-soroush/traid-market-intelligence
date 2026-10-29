"""Architecture boundaries: provider neutrality, SDK isolation, import direction, no authority,
offline enforcement, upstream immutability and the canonical four-status contract."""
import ast
from datetime import date
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from ai_support import (  # noqa: F401
    MAPPING, T, T1, T2, FakeClock, cpi_claim, etf, failure, fomc_claim, macro, market_state, news, offline,
    record_root, valid_output, whales,
)
from traid.ai import AIService, AIStatus, EvidenceInputs, ProcessSlot, RecordStore
from traid.ai.models import AIResult, AnchorAssessment, ClaimNote, Note, NumberRef, TaskOutput, ValidatedInterpretation
from traid.ai.prompts import ALLOWED_SCHEMA_KEYWORDS, PROMPT_DIGEST, SYSTEM_PROMPT, TOOL_SCHEMA
from traid.ai.provider import ContentBlock, ModelReply, ProviderDescription, ProviderSession

SRC = Path(__file__).resolve().parents[1] / "src" / "traid"
ROOT = SRC.parents[1]


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_no_upstream_package_imports_traid_ai():
    for path in SRC.rglob("*.py"):
        if "ai" in path.relative_to(SRC).parts[:1]:
            continue
        assert not any(m == "traid.ai" or m.startswith("traid.ai.") for m in imports(path)), path


def test_only_the_bedrock_adapter_imports_the_sdk_and_only_lazily():
    for path in SRC.rglob("*.py"):
        sdk = {m for m in imports(path) if m.split(".")[0] in ("boto3", "botocore")}
        if path.name == "bedrock.py":
            top = {n.names[0].name if isinstance(n, ast.Import) else n.module
                   for n in ast.parse(path.read_text()).body if isinstance(n, (ast.Import, ast.ImportFrom))}
            assert sdk and not any(str(m).split(".")[0] in ("boto3", "botocore") for m in top)   # lazy only
        else:
            assert not sdk, path
    code = "import sys, traid.ai, traid.ai.service, traid.ai.bedrock; print('boto3' in sys.modules or 'botocore' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         env={"PYTHONPATH": str(SRC.parent), "PATH": "/usr/bin:/bin"})
    assert out.stdout.strip() == "False"


def test_core_modules_never_name_a_model_family():
    for name in ("service.py", "selection.py", "validation.py", "grammar.py", "provider.py", "models.py", "records.py"):
        text = (SRC / "ai" / name).read_text().lower()
        assert "boto" not in text and "nova" not in text and "converse" not in text, name


class EchoProvider:
    """An independent, non-Bedrock provider written against the protocol only."""
    def __init__(self):
        self.sent = []

    def describe(self):
        return ProviderDescription(provider="echo", api="local", model_id="echo-1", source_region=None,
                                   approved_destination_regions=(), destinations_verified_on=date(2026, 10, 1))

    def setup(self):
        return ProviderSession(state="ready")

    def send(self, session, request, attempt, connect_timeout, read_timeout):
        self.sent.append(request)
        output = valid_output(json.loads(request.user_text))
        return ModelReply(stop_reason="tool_use", role="assistant",
                          blocks=(ContentBlock(kind="tool_use", tool_name=request.tool_name, tool_use_id="e1",
                                               tool_input=output),),
                          raw_text=json.dumps(output), raw_size=len(json.dumps(output)))


def test_the_service_is_provider_neutral(record_root):
    provider = EchoProvider()
    result = AIService(provider, RecordStore(record_root), slot=ProcessSlot()).interpret(
        T1, T, EvidenceInputs(market_state=market_state()))
    assert result.status is AIStatus.VALID and len(provider.sent) == 1
    assert provider.sent[0].system_prompt == SYSTEM_PROMPT and provider.sent[0].tool_schema == TOOL_SCHEMA
    disabled = AIService(None, RecordStore(record_root), slot=ProcessSlot()).interpret(
        T1, T, EvidenceInputs(market_state=market_state()))
    assert (disabled.status, disabled.reasons) == (AIStatus.AI_NOT_REQUESTED, ("AI_DISABLED",))


def test_no_output_or_result_field_carries_authority():
    banned = {"action", "side", "direction", "size", "leverage", "stop", "target", "confidence", "probability",
              "recommendation", "order", "entry", "exit", "position", "allocation", "trade", "signal"}
    for model in (TaskOutput, Note, AnchorAssessment, ClaimNote, NumberRef, ValidatedInterpretation, AIResult):
        assert not set(model.model_fields) & banned, model
    src = "\n".join(p.read_text() for p in (SRC / "ai").glob("*.py"))
    assert "TRADE_CANDIDATE" not in src


def test_tool_schema_uses_only_supported_keywords_and_the_prompt_is_versioned():
    def walk(node):
        if isinstance(node, dict):
            keys = set(node) - {"properties"} if "type" in node else set()
            assert keys <= ALLOWED_SCHEMA_KEYWORDS, keys
            for k, v in node.items():
                if k == "properties":
                    for child in v.values():
                        walk(child)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(TOOL_SCHEMA)
    text = json.dumps(TOOL_SCHEMA)
    assert all(k not in text for k in ('"$ref"', '"anyOf"', '"pattern"', '"maxItems"', '"additionalProperties"'))
    from traid.ai import select
    sel = select(T1, T, EvidenceInputs(market_state=market_state()))
    assert sel.request.prompt_digest == PROMPT_DIGEST and sel.request.prompt_id == "c14-prompt-1"


def test_offline_fixture_refuses_sockets_and_name_lookups():
    with pytest.raises(AssertionError):
        socket.create_connection(("bedrock-runtime.eu-north-1.amazonaws.com", 443), timeout=1)
    s = socket.socket()
    try:
        with pytest.raises(AssertionError):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()


@pytest.mark.parametrize("status", ["VALID", "AI_INVALID", "AI_UNAVAILABLE", "AI_NOT_REQUESTED"])
def test_upstream_reports_are_byte_identical_under_every_status(record_root, status):
    from ai_support import FakeProvider
    rep = macro()
    inputs = dict(market_state=market_state(), whales=whales([("L", "100")] * 6), macro=rep, etf=etf(),
                  etf_mapping=MAPPING, news=news([cpi_claim(), fomc_claim()], rep))
    before = {k: v.model_dump_json() for k, v in inputs.items()}
    script = {"VALID": [lambda r: valid_output(json.loads(r.user_text))], "AI_INVALID": [{"summary": "x"}],
              "AI_UNAVAILABLE": [failure("PROVIDER_ERROR")], "AI_NOT_REQUESTED": []}[status]
    ev = EvidenceInputs(**inputs) if status != "AI_NOT_REQUESTED" else EvidenceInputs(**{**inputs, "market_state": None})
    result = AIService(FakeProvider(script), RecordStore(record_root), clock=FakeClock(), slot=ProcessSlot()).interpret(
        T1, T, ev)
    assert result.status.value == status
    assert {k: v.model_dump_json() for k, v in inputs.items()} == before


def test_canonical_documents_define_the_four_statuses():
    guardrails = (ROOT / "FINANCIAL_AND_DATA_GUARDRAILS.md").read_text()
    codes_line = next(line for line in guardrails.splitlines() if line.startswith("Use stable typed codes:"))
    codes = {c.strip(" `.") for c in codes_line.split(":", 1)[1].split(",")}
    assert {s.value for s in AIStatus} - {"VALID"} <= codes
    assert "| AI call deliberately skipped | `AI_NOT_REQUESTED`; no promotion |" in guardrails
    spec = (ROOT / "TRAID_CARD_SPECIFICATIONS.md").read_text()
    assert "- explicit outcome states: `VALID`, `AI_INVALID`, `AI_UNAVAILABLE`, `AI_NOT_REQUESTED`" in spec
    blueprint = (ROOT / "TRAID_FINAL_SYSTEM_BLUEPRINT.md").read_text()
    assert "Only a validated and recorded `VALID` interpretation is released." in blueprint
