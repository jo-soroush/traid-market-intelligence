"""Strict acceptance of one model reply, in order; the first failure decides and nothing is repaired.

W1  serialized response <= 64 KiB, else RESPONSE_LIMIT_EXCEEDED.
V0  stop reason ``tool_use`` only (truncation -> OUTPUT_TRUNCATED, filtering -> CONTENT_FILTERED);
    role ``assistant``; blocks are text or tool use only; exactly one ``submit_interpretation`` call with
    an id and an object input. Text blocks are never parsed.
V1  the tool input holds only dict (str keys), list and str, depth <= 6, else SCHEMA_INVALID.
V2  re-encoded with ``json.dumps(ensure_ascii=True, allow_nan=False, separators=(",", ":"))``; its SHA-256
    is recorded; then ``TaskOutput.model_validate_json(strict=True)``.
V3  references: exact, unnormalized equality; claim handles and unresolved facts never stand as evidence;
    CAT references only for categories not INCLUDED; anchors and claims each covered exactly once.
V4  statements 20-600 characters, unique under NFC, not made only of identifiers and numbers.
G   the strict whole-token grammar (``traid.ai.grammar``) per statement, with the section's literals and
    citable values; prohibited trade language; no asset words in the macro task.
S   section rules: summary source, substantive assessment, uncertainty, refuting evidence for FALSE or
    MISLEADING claims.

Then a deterministic adapter projects the canonical blueprint fields from the validated output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import unicodedata

from pydantic import ValidationError

from traid.ai.grammar import GrammarError, check_statement
from traid.ai.models import (
    Annotation, AnchorAssessment, CanonicalFactor, CanonicalNote, Category, CategoryState, MissingInformation,
    SourceReference, Stance, TaskId, TaskOutput, Tier, ValidatedInterpretation,
)
from traid.ai.prompts import TOOL_NAME
from traid.ai.provider import ModelReply
from traid.ai.selection import INTERPRETATION_LIMITATIONS, RequestContext

MAX_RAW_BYTES = 64 * 1024
MAX_DEPTH = 6
MIN_STATEMENT, MAX_STATEMENT = 20, 600
STOP_CODES = {"max_tokens": "OUTPUT_TRUNCATED", "model_context_window_exceeded": "OUTPUT_TRUNCATED",
              "content_filtered": "CONTENT_FILTERED", "guardrail_intervened": "CONTENT_FILTERED",
              "malformed_model_output": "MALFORMED_OUTPUT", "malformed_tool_use": "MALFORMED_OUTPUT"}
PROHIBITED_LANGUAGE_VERSION = "c14-prohibited-language-1"
TRADE_WORDS = frozenset((
    "buy", "buys", "buying", "sell", "sells", "selling", "recommend", "recommends", "recommended", "recommendation",
    "recommendations", "advise", "advised", "advice", "should", "enter", "entry", "exit", "target", "targets",
    "stop-loss", "take-profit", "leverage", "leveraged", "allocate", "allocation", "sizing", "position-size",
    "bullish", "bearish", "forecast", "forecasts", "predict", "predicts", "prediction", "outlook", "signal",
    "signals", "trade", "trades", "trading", "invest", "investment", "opportunity", "accumulate", "short-sell"))
ASSET_WORDS = frozenset(("btc", "bitcoin", "bitcoins", "xbt", "crypto", "cryptocurrency", "cryptocurrencies",
                         "price", "prices"))
MACRO_TASK_EXCLUDED = (Category.C10, Category.C11)


class OutputInvalid(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}{': ' + detail if detail else ''}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Validation:
    valid: bool
    code: str | None
    detail: str
    tool_input_sha256: str | None
    interpretation: ValidatedInterpretation | None


def _invalid(code: str, detail: str = "", sha: str | None = None) -> Validation:
    return Validation(valid=False, code=code, detail=detail, tool_input_sha256=sha, interpretation=None)


def _types(value, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise OutputInvalid("SCHEMA_INVALID", "depth")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise OutputInvalid("SCHEMA_INVALID", "key type")
            _types(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            _types(v, depth + 1)
    elif not isinstance(value, str):
        raise OutputInvalid("SCHEMA_INVALID", f"type {type(value).__name__}")


def validate_reply(reply: ModelReply, ctx: RequestContext, analysis_timestamp: datetime) -> Validation:
    if reply.raw_size > MAX_RAW_BYTES:
        return _invalid("RESPONSE_LIMIT_EXCEEDED", str(reply.raw_size))
    if reply.stop_reason != "tool_use":
        return _invalid(STOP_CODES.get(reply.stop_reason or "", "UNEXPECTED_STOP_REASON"), str(reply.stop_reason))
    if reply.role != "assistant" or any(b.kind not in ("text", "tool_use") for b in reply.blocks):
        return _invalid("UNEXPECTED_CONTENT_BLOCK")
    tools = [b for b in reply.blocks if b.kind == "tool_use"]
    if len(tools) != 1 or tools[0].tool_name != TOOL_NAME or not isinstance(tools[0].tool_use_id, str) \
            or not tools[0].tool_use_id or not isinstance(tools[0].tool_input, dict):
        return _invalid("TOOL_CONTRACT")
    try:
        _types(tools[0].tool_input, 1)
        data = json.dumps(tools[0].tool_input, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except OutputInvalid as e:
        return _invalid(e.code, e.detail)
    except (TypeError, ValueError):
        return _invalid("SCHEMA_INVALID", "encoding")
    sha = hashlib.sha256(data.encode()).hexdigest()
    try:
        output = TaskOutput.model_validate_json(data, strict=True)
    except (ValidationError, ValueError) as e:
        return _invalid("SCHEMA_INVALID", type(e).__name__, sha)
    try:
        check_output(output, ctx)
    except OutputInvalid as e:
        return _invalid(e.code, e.detail, sha)
    return Validation(valid=True, code=None, detail="", tool_input_sha256=sha,
                      interpretation=adapt(output, ctx, analysis_timestamp))


# ------------------------------------------------------------------------- output rules
def _kind(ref: str, ctx: RequestContext) -> str | None:
    if ref in ctx.items:
        return "item"
    if ref in ctx.facts:
        return "fact"
    if ref in ctx.claims:
        return "claim"
    if ref.startswith("CAT:") and ref[4:] in {c.value for c in Category}:
        return "cat"
    return None


def _check_refs(refs, ctx: RequestContext, *, claims_allowed: bool, unresolved_allowed: bool) -> None:
    seen = set()
    for r in refs:
        if r in seen:
            raise OutputInvalid("DUPLICATE_REFERENCE", r)
        seen.add(r)
        kind = _kind(r, ctx)
        if kind is None:
            raise OutputInvalid("UNKNOWN_REFERENCE", r)
        if kind == "claim" and not claims_allowed:
            raise OutputInvalid("CLAIM_CITED_AS_FACT", r)
        if kind == "fact" and not unresolved_allowed and ctx.facts[r][1].outcome == "UNRESOLVED":
            raise OutputInvalid("CLAIM_CITED_AS_FACT", r)
        if kind == "cat":
            cat = Category(r[4:])
            if ctx.task_id is TaskId.MACRO_CONTEXT and cat in MACRO_TASK_EXCLUDED:
                raise OutputInvalid("OUT_OF_SCOPE_REFERENCE", r)
            if ctx.categories.get(cat) is CategoryState.INCLUDED:
                raise OutputInvalid("MISSING_CATEGORY_CONTRADICTION", r)


def _sections(output: TaskOutput):
    """(section, statement, cited refs, numbers, owner) for every model-written statement, in order."""
    yield "summary", output.summary.statement, output.summary.refs, output.summary.numbers, None
    for a in output.anchor_assessments:
        yield "anchor_assessments", a.statement, a.evidence_ids, a.numbers, a
    for n in output.context_notes:
        yield "context_notes", n.statement, n.refs, n.numbers, None
    for c in output.claim_notes:
        yield "claim_notes", c.statement, c.refs, c.numbers, c
    for n in output.uncertainties:
        yield "uncertainties", n.statement, n.refs, n.numbers, None


def _cited(section: str, refs, owner, ctx: RequestContext) -> set[str]:
    cited = set(refs)
    if section == "anchor_assessments" and owner.anchor_id in ctx.anchors:
        cited.add(ctx.anchors[owner.anchor_id].evidence_id)
    if section == "claim_notes":
        cited.add(owner.claim_id)
    return cited


def _literals_and_values(cited: set[str], ctx: RequestContext) -> tuple[frozenset[str], frozenset[str]]:
    literals = set(ctx.global_literals)
    values = set()
    for r in cited:
        if r in ctx.items:
            literals |= ctx.literals.get(r, frozenset())
            values |= {v.value_id for v in ctx.items[r].values}
        elif r in ctx.facts:
            claim_id, fact = ctx.facts[r]
            literals |= ctx.literals.get(claim_id, frozenset())
            values |= set(fact.linked_value_ids)
        elif r in ctx.claims:
            literals |= ctx.literals.get(r, frozenset())
            values |= {v for fr in ctx.claims[r].frames for f in fr.facts for v in f.linked_value_ids}
    return frozenset(literals), frozenset(values)


def check_output(output: TaskOutput, ctx: RequestContext) -> None:
    # V3 references and coverage
    _check_refs(output.summary.refs, ctx, claims_allowed=False, unresolved_allowed=False)
    for a in output.anchor_assessments:
        if a.anchor_id not in ctx.anchors:
            raise OutputInvalid("UNKNOWN_ANCHOR", a.anchor_id)
        _check_refs(a.evidence_ids, ctx, claims_allowed=False, unresolved_allowed=False)
    for n in output.context_notes:
        _check_refs(n.refs, ctx, claims_allowed=False, unresolved_allowed=False)
    for c in output.claim_notes:
        if c.claim_id not in ctx.claims:
            raise OutputInvalid("UNKNOWN_REFERENCE", c.claim_id)
        _check_refs(c.refs, ctx, claims_allowed=True, unresolved_allowed=True)
    for n in output.uncertainties:
        _check_refs(n.refs, ctx, claims_allowed=True, unresolved_allowed=True)
    for _, _, _, numbers, _ in _sections(output):
        for num in numbers:
            if num.value_id not in ctx.values:
                raise OutputInvalid("UNKNOWN_REFERENCE", num.value_id)
    anchors = [a.anchor_id for a in output.anchor_assessments]
    if len(anchors) != len(set(anchors)) or set(anchors) != set(ctx.anchors):
        raise OutputInvalid("ANCHOR_COVERAGE_INVALID")
    claims = [c.claim_id for c in output.claim_notes]
    if len(claims) != len(set(claims)) or set(claims) != set(ctx.claims):
        raise OutputInvalid("CLAIM_COVERAGE_INVALID")

    # V4 statement form
    seen = set()
    for _, statement, _, _, _ in _sections(output):
        if not MIN_STATEMENT <= len(statement) <= MAX_STATEMENT:
            raise OutputInvalid("STATEMENT_INVALID", "length")
        key = unicodedata.normalize("NFC", statement)
        if key in seen:
            raise OutputInvalid("STATEMENT_INVALID", "duplicate")
        seen.add(key)

    # G1-G5 and prohibited language
    for section, statement, refs, numbers, owner in _sections(output):
        cited = _cited(section, refs, owner, ctx)
        literals, citable = _literals_and_values(cited, ctx)
        try:
            tokens = check_statement(statement, literals, [(n.value_id, n.text) for n in numbers], ctx.values, citable)
        except GrammarError as e:
            raise OutputInvalid(e.code, e.detail) from None
        if not any(t.kind == "WORD" for t in tokens):
            raise OutputInvalid("STATEMENT_INVALID", "identifiers or numbers only")
        for t in tokens:
            low = t.core.lower()
            parts = {low, *low.split("-"), low.split("'")[0]}
            if t.kind == "WORD" and parts & TRADE_WORDS:
                raise OutputInvalid("PROHIBITED_TRADE_LANGUAGE", low)
            if ctx.task_id is TaskId.MACRO_CONTEXT and t.kind in ("WORD", "LITERAL") and parts & ASSET_WORDS:
                raise OutputInvalid("ASSET_CONCLUSION_IN_MACRO_TASK", low)

    # T2: ETF evidence is optional context only, never the basis of a macro conclusion
    if ctx.task_id is TaskId.MACRO_CONTEXT:
        conclusions = list(output.summary.refs) + [r for a in output.anchor_assessments for r in a.evidence_ids] + \
            [r for c in output.claim_notes for r in c.refs]
        if any(r in ctx.items and ctx.items[r].category is Category.C12_ETF for r in conclusions) or \
                any(r == "CAT:C12_ETF" for r in conclusions):
            raise OutputInvalid("OUT_OF_SCOPE_REFERENCE", "C12_ETF outside context")

    # S section rules
    summary_ok = any(r in ctx.items and ctx.items[r].category is _summary_category(ctx)
                     and ctx.items[r].tier is Tier.STRUCTURED for r in output.summary.refs)
    if not summary_ok:
        raise OutputInvalid("SUMMARY_SOURCE_MISSING")
    if any(not a.evidence_ids for a in output.anchor_assessments):
        raise OutputInvalid("ASSESSMENT_WITHOUT_REFERENCE")
    if all(a.stance is Stance.NOT_ASSESSABLE for a in output.anchor_assessments):
        raise OutputInvalid("NO_SUBSTANTIVE_ASSESSMENT")
    if ctx.task_id is TaskId.BTC_MARKET_STATE:
        for n in output.context_notes:
            if any(r in ctx.items and ctx.items[r].category is Category.C10 for r in n.refs):
                raise OutputInvalid("CONTEXT_REFERENCE_INVALID")
    if not output.uncertainties:
        raise OutputInvalid("UNCERTAINTY_MISSING")
    for c in output.claim_notes:
        claim = ctx.claims[c.claim_id]
        if claim.state in ("FALSE", "MISLEADING"):
            refuting = {f.fact_id for fr in claim.frames for f in fr.facts if f.outcome in ("CONTRADICTED", "SUPERSEDED")}
            if refuting and not refuting & set(c.refs):
                raise OutputInvalid("REFUTING_EVIDENCE_NOT_CITED", c.claim_id)


def _summary_category(ctx: RequestContext) -> Category:
    return Category.C10 if ctx.task_id is TaskId.BTC_MARKET_STATE else Category.C12_MACRO


# ------------------------------------------------------------------- canonical adapter
def adapt(output: TaskOutput, ctx: RequestContext, analysis_timestamp: datetime) -> ValidatedInterpretation:
    """Deterministic projection to the blueprint fields; adds nothing the output and request do not hold."""
    supporting, contradicting, uncertainty, flags = [], [], [], []
    for a in output.anchor_assessments:
        if a.stance in (Stance.SUPPORTS, Stance.CONTRADICTS):
            anchor_item = ctx.anchors[a.anchor_id].evidence_id
            anchor_keys = ctx.source_keys.get(anchor_item, frozenset())
            independent = tuple(r for r in a.evidence_ids if r != anchor_item and not r.startswith("CAT:")
                                and not (ctx.source_keys.get(r, frozenset()) & anchor_keys))
            if not independent:
                flags.append(f"ANCHOR_ASSESSMENT_WITHOUT_INDEPENDENT_EVIDENCE:{a.anchor_id}")
                continue
            factor = CanonicalFactor(anchor_id=a.anchor_id, statement=a.statement, evidence_ids=independent,
                                     numbers=a.numbers)
            (supporting if a.stance is Stance.SUPPORTS else contradicting).append(factor)
        else:
            uncertainty.append(CanonicalNote(origin="ANCHOR_MIXED" if a.stance is Stance.MIXED else "ANCHOR_NOT_ASSESSABLE",
                                             anchor_id=a.anchor_id, statement=a.statement, refs=a.evidence_ids,
                                             numbers=a.numbers))
    for n in output.uncertainties:
        uncertainty.append(CanonicalNote(origin="UNCERTAINTIES_SECTION", anchor_id=None, statement=n.statement,
                                         refs=n.refs, numbers=n.numbers))
    missing = [MissingInformation(category=c, subject=f"CAT:{c.value}", reasons=(s.value,))
               for c, s in ctx.categories.items() if s not in (CategoryState.INCLUDED, CategoryState.NOT_USED_BY_TASK)]
    missing += [MissingInformation(category=u.category, subject=u.subject, reasons=u.reasons) for u in ctx.unavailable]
    for item in ctx.items.values():
        if item.values_withheld:
            missing.append(MissingInformation(category=item.category, subject=item.evidence_id,
                                              reasons=item.values_withheld))
    refs = []
    for _, statement, cited, _, owner in _sections(output):
        refs += [r for r in cited if not r.startswith("CAT:")]
        if isinstance(owner, AnchorAssessment):
            refs.append(ctx.anchors[owner.anchor_id].evidence_id)
        for r in cited:
            if r in ctx.facts and ctx.facts[r][1].outcome == "CONTRADICTED":
                asserted = ctx.facts[r][1].claim_asserted
                words = {w.rstrip(",;:.") for w in statement.split(" ")}
                if asserted and asserted in words:
                    flags.append(f"ASSERTED_VALUE_QUOTED_FOR_REFUTED_FACT:{r}")
    for c in output.claim_notes:
        refs.append(c.claim_id)
    evidence = tuple(sorted(set(refs)))
    sources, annotations = [], []
    for r in evidence:
        if r in ctx.items:
            item = ctx.items[r]
            sources.append(SourceReference(ref=r, category=item.category, tier=item.tier, kind=item.kind,
                                           subject=item.subject, engine_version=ctx.engine_versions[item.category]))
            annotations.append(Annotation(ref=r, category=item.category, tier=item.tier, upstream_state=item.state,
                                          claim_state=None))
        else:
            claim_id = ctx.facts[r][0] if r in ctx.facts else r
            claim = ctx.claims[claim_id]
            kind = "C13_FACT" if r in ctx.facts else "C13_CLAIM"
            sources.append(SourceReference(ref=r, category=Category.C13, tier=Tier.ASSESSED_CLAIM, kind=kind,
                                           subject=claim_id, engine_version=ctx.engine_versions[Category.C13]))
            annotations.append(Annotation(ref=r, category=Category.C13, tier=Tier.ASSESSED_CLAIM,
                                          upstream_state=ctx.facts[r][1].outcome if r in ctx.facts else None,
                                          claim_state=claim.state))
    return ValidatedInterpretation(
        task_id=ctx.task_id, output=output, supporting_factors=tuple(supporting),
        contradicting_factors=tuple(contradicting), uncertainty=tuple(uncertainty),
        missing_information=tuple(missing), evidence=evidence, source_references=tuple(sources),
        analysis_timestamp=analysis_timestamp, annotations=tuple(annotations),
        flags=tuple(dict.fromkeys(flags)), limitations=INTERPRETATION_LIMITATIONS)
