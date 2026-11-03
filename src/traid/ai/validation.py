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
    citable values; then the clause-aware narrative-authority policy and the evidence predicates for
    descriptive market assertions (below); no asset words in the macro task.
S   section rules: summary source, substantive assessment, uncertainty, refuting evidence for FALSE or
    MISLEADING claims.

Then a deterministic adapter projects the canonical blueprint fields from the validated output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import unicodedata

from pydantic import ValidationError

from traid.ai.grammar import (
    CONNECTORS, DESCRIPTORS, GENERIC_DESCRIPTORS, UNIT_ATTRIBUTION, UNIT_PHRASES, WORD, GrammarError, check_statement,
    is_literal_candidate, unit_class,
)
from traid.ai.models import (
    Annotation, AnchorAssessment, CanonicalFactor, CanonicalNote, Category, CategoryState, MissingInformation,
    SourceReference, Stance, TaskId, TaskOutput, Tier, ValidatedInterpretation,
)
from traid.ai.prompts import NARRATIVE_POLICY_VERSION, TOOL_NAME
from traid.ai.provider import ModelReply
from traid.ai.selection import INTERPRETATION_LIMITATIONS, RequestContext

MAX_RAW_BYTES = 64 * 1024
MAX_DEPTH = 6
MIN_STATEMENT, MAX_STATEMENT = 20, 600
STOP_CODES = {"max_tokens": "OUTPUT_TRUNCATED", "model_context_window_exceeded": "OUTPUT_TRUNCATED",
              "content_filtered": "CONTENT_FILTERED", "guardrail_intervened": "CONTENT_FILTERED",
              "malformed_model_output": "MALFORMED_OUTPUT", "malformed_tool_use": "MALFORMED_OUTPUT"}
PROHIBITED_LANGUAGE_VERSION = NARRATIVE_POLICY_VERSION
ASSET_WORDS = frozenset(("btc", "bitcoin", "bitcoins", "xbt", "crypto", "cryptocurrency", "cryptocurrencies",
                         "price", "prices"))
MACRO_TASK_EXCLUDED = (Category.C10, Category.C11)
CATEGORY_TEXT = {Category.C10: "C10", Category.C11: "C11", Category.C12_MACRO: "C12", Category.C12_ETF: "C12",
                 Category.C13: "C13"}


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
    literals = set(ctx.global_literals) | {u.subject for u in ctx.unavailable if is_literal_candidate(u.subject)}
    values = set()
    for r in cited:
        if r in ctx.items:
            literals |= ctx.literals.get(r, frozenset())
            literals.add(CATEGORY_TEXT[ctx.items[r].category])      # "C10" etc.: only beside eligible cited evidence
            values |= {v.value_id for v in ctx.items[r].values}
        elif r in ctx.facts:
            claim_id, fact = ctx.facts[r]
            literals |= ctx.literals.get(claim_id, frozenset())
            literals.add(CATEGORY_TEXT[Category.C13])
            values |= set(fact.linked_value_ids)
        elif r in ctx.claims:
            literals |= ctx.literals.get(r, frozenset())
            literals.add(CATEGORY_TEXT[Category.C13])
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
        narrative_check(statement, tokens, cited, ctx, [n.value_id for n in numbers], section,
                        owner.anchor_id if isinstance(owner, AnchorAssessment) else None,
                        owner.stance.value if isinstance(owner, AnchorAssessment) else None,
                        owner.claim_id if section == "claim_notes" else None)
        for t in tokens:
            low = t.core.lower()
            parts = {low, *low.split("-"), low.split("'")[0]}
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


# ------------------------------------------------------------------ narrative authority (F6, policy 2)
# A deterministic, clause-aware screen over the word tokens of a model-written statement. It is lexical:
# acceptance never proves that a sentence is not advice, only that it uses none of the constructions below.
# Descriptive market language (buy-side or sell-side pressure, long and short positions, funding, liquidation,
# direction) is allowed, but every descriptive market-state assertion must be backed by cited, eligible C10
# evidence of that subject and state (the evidence predicates). Whatever cannot be decided here fails closed.
CLAUSE_END = ",;:."
_CONJ = frozenset(("and", "but", "so", "then", "while", "because", "therefore", "thus", "hence", "yet", "whereas",
                   "although", "though", "however", "if", "when", "meaning"))
_HARD = frozenset((
    "recommend", "recommends", "recommended", "recommending", "recommendation", "recommendations", "advise", "advises",
    "advised", "advising", "advice", "advisable", "should", "shall", "must", "ought", "would", "will", "gonna",
    "leverage", "leveraged", "leverages", "allocate", "allocates", "allocated", "allocating", "allocation",
    "allocations", "sizing", "stoploss", "takeprofit", "invest", "invests", "invested", "investing", "investment",
    "investments", "opportunity", "opportunities", "accumulate", "accumulates", "accumulating", "signal", "signals",
    "setup", "setups", "forecast", "forecasts", "forecasting", "predict", "predicts", "predicted", "predicting",
    "prediction", "predictions", "outlook", "likely", "unlikely", "probably", "certainly", "surely", "definitely",
    "undoubtedly", "inevitable", "inevitably", "guaranteed", "guarantee", "guarantees", "riskless", "immediately",
    "urgent", "urgently", "asap", "tomorrow", "tonight", "soon", "imminent", "imminently", "shortly", "eventually",
    "you", "your", "yours", "yourself", "we", "our", "ours", "ourselves", "entry", "entries", "exit", "exits",
    "exiting", "exited", "enter", "enters", "entering", "entered", "hedges", "hedging", "hedged", "bull", "bulls",
    "bear", "bears", "bullishness", "bearishness", "surge", "surges", "surged", "surging", "soar", "soars", "soared",
    "soaring", "plunge", "plunges", "plunged", "plunging", "plummet", "plummets", "plummeted", "crash", "crashes",
    "crashed", "crashing", "rally", "rallies", "rallied", "rallying", "skyrocket", "skyrockets", "skyrocketed",
    "moon", "pump", "dump", "breakout", "breakdown", "squeeze", "squeezes", "squeezed", "bought", "sold",
    "shorting", "longing", "undervalued", "overvalued", "oversold", "overbought", "bargain", "attractive",
    "upside", "downside", "bias", "biased", "derisk", "continue", "continues", "continuing", "poised",
    "bullishly", "bearishly", "tp", "sl", "i", "me", "my", "mine", "myself", "kindly", "prudent", "wise", "wiser",
    "sensible", "worthwhile", "favors", "favours", "favored", "favorable", "favourable", "favor", "warrant",
    "warrants", "warranted", "justify", "justifies", "justified", "merit", "merits", "urge", "urges", "argue",
    "argues", "advocate", "advocates", "endorse", "endorses", "appealing", "cheap", "candidate", "deserve",
    "deserves", "better", "best", "now", "acting", "acts"))
_BIGRAMS = frozenset((("stop", "loss"), ("stop", "losses"), ("take", "profit"), ("take", "profits"),
                      ("position", "size"), ("position", "sizes"), ("position", "sizing"), ("risk", "free"),
                      ("de", "risk"), ("going", "to"), ("about", "to"), ("set", "to"), ("time", "to"), ("need", "to"),
                      ("needs", "to"), ("have", "to"), ("good", "moment"), ("good", "time"), ("good", "idea"),
                      ("makes", "sense"), ("make", "sense"), ("reason", "to"), ("moment", "to"), ("chance", "to"),
                      ("way", "to"), ("time", "for")))
_IMPERATIVE = frozenset((
    "buy", "sell", "open", "close", "go", "add", "reduce", "increase", "decrease", "cut", "trim", "scale", "set",
    "place", "take", "hold", "keep", "stay", "avoid", "wait", "consider", "hedge", "size", "reverse", "flip",
    "raise", "lower", "adjust", "use", "apply", "watch", "monitor", "look", "prepare", "be", "do", "don", "never",
    "always", "please", "try", "make", "ensure", "remember", "note", "let", "expect", "rotate", "switch", "shift",
    "move", "load", "cover", "fade", "ape", "scalp", "dca", "dump", "chase", "average", "wait", "position", "sit",
    "step", "lean", "tilt", "prefer", "act", "stand"))
_NOUN_AFTER_IMPERATIVE = frozenset(("in", "of"))                       # "Increase in funding" is a noun phrase
_SIDE_VERBS = frozenset(("short", "long"))
_SIDE_OBJECT = frozenset(("the", "it", "this", "that", "now", "here", "more", "less", "btc", "bitcoin"))
_TRADE_VERBS = frozenset((
    "open", "opens", "opened", "opening", "close", "closes", "closed", "closing", "reverse", "reverses", "reversed",
    "reversing", "flip", "flips", "flipped", "add", "adds", "added", "adding", "increase", "increases", "increased",
    "increasing", "reduce", "reduces", "reduced", "reducing", "decrease", "decreases", "decreased", "decreasing",
    "cut", "cuts", "trim", "trims", "scale", "scales", "raise", "raises", "raised", "raising", "lower", "lowers",
    "lowered", "lowering", "boost", "boosts", "take", "takes", "go", "goes", "going", "went", "get", "gets", "hold",
    "holds", "stay", "stays", "keep", "keeps", "switch", "switches", "rotate", "rotates", "size", "sized", "set",
    "sets", "place", "places", "placing"))
_TRADE_OBJECTS = frozenset(("position", "positions", "long", "longs", "short", "shorts", "exposure", "exposures",
                            "capital", "portfolio", "holdings", "stop", "stops"))
_SIDE_WORDS = frozenset(("long", "longs", "short", "shorts"))
_TERM_WORDS = frozenset(("term", "run", "dated", "end", "maturity"))   # "short-term rates", "long run"
_FLOW_HEADS = frozenset(("pressure", "side", "volume", "volumes", "flow", "flows", "orders", "order", "activity",
                         "imbalance", "aggressor", "aggressors", "interest", "trades", "taker", "takers",
                         "quantity", "share"))
_MODAL_SOFT = frozenset(("could", "might", "may", "can"))
_MOVES = frozenset(("rise", "rises", "fall", "falls", "drop", "drops", "increase", "decrease", "climb", "climbs",
                    "decline", "declines", "continue", "continues", "reverse", "move", "moves", "go", "break",
                    "test", "reach", "hit", "push", "gain", "gains", "lose", "loses"))
_TRADING_NOUN_AFTER = frozenset(("volume", "activity", "session", "hours", "day", "days", "range"))
_LIQUIDATION_WORDS = frozenset(("liquidation", "liquidations", "liquidated", "liquidating", "liquidate", "liquidates"))

# Canonical C10 state labels and the C10 dimensions (item subjects) that can carry them.
LABEL_DIMS = {
    "BUY_DOMINANT": ("flow",), "SELL_DOMINANT": ("flow",), "BALANCED": ("flow",),
    "LONGS_PAY_SHORTS": ("funding",), "SHORTS_PAY_LONGS": ("funding",), "ZERO": ("funding",),
    "TRENDING_UP": ("direction", "regime"), "TRENDING_DOWN": ("direction", "regime"),
    "RANGING": ("direction", "regime"), "HIGH_VOLATILITY": ("regime",),
    "HIGH": ("volatility",), "NOT_HIGH": ("volatility",), "THIN": ("liquidity",), "NOT_THIN": ("liquidity",),
    "AUTHORITATIVE_LIQUIDATION_EVENT": ("liquidation",), "HEURISTIC_LIQUIDATION_PRESSURE": ("liquidation",),
}
# A canonical label written as a hyphenated or joined WORD ("buy-dominant", "TrendingUp") is an alias, never accepted.
_ALIAS_KEYS = frozenset(k.replace("_", "").lower() for k in (
    "BUY_DOMINANT", "SELL_DOMINANT", "LONGS_PAY_SHORTS", "SHORTS_PAY_LONGS", "TRENDING_UP", "TRENDING_DOWN",
    "AUTHORITATIVE_LIQUIDATION_EVENT", "HEURISTIC_LIQUIDATION_PRESSURE", "NOT_HIGH", "NOT_THIN"))
CATEGORY_WORDS = frozenset(("C10", "C11", "C12", "C13"))


# --- default-deny constructions (F6 final) ----------------------------------------------------------------------
# Every clause of every model-written statement must be one of the constructions below. Nothing else is accepted,
# whatever its vocabulary: there is no list of forbidden words behind this, only a list of what may be written.
# Each construction is matched on the whole clause, may end only in neutral words or identifiers the statement
# actually cites, and is bound to an evidence predicate over the request context (RequestContext):
#
#   STATE        "The cited X state is S."            a cited item with subject X and exactly state S
#   CLASSIFIED   "C10 classified X as S."             the same, and the item belongs to that category
#   BTC          "The BTC market state was S."        S a state of exactly one C10 dimension
#   SIDE         "The cited buy-side pressure reflects BUY_DOMINANT."   (sell-side with SELL_DOMINANT)
#   PAYER        "Funding indicates longs pay shorts."                  the matching funding state
#   BULL         "The observed direction condition is bullish; the cited direction state is TRENDING_UP."
#                the whole statement, BTC task only (bearish with TRENDING_DOWN)
#   AVAILABLE    "X evidence is described | available | partial | unavailable."   see _availability
#   CATEGORY     "The category CAT:C11 is not supplied | partial | excluded | rejected."   the category status
#   SOME         "Some evidence categories are unavailable or only partly included."       a category not included
#   CLAIM        "Claim N001 has the assessed state S."                the claim's own state
#   FACT         "Fact N001.F01 is supported | contradicted | superseded | unresolved for claim N001."
#                the fact belongs to that claim and has that outcome
#   ASSERTED     "Claim N003 asserted DISAPPROVED, which N003.F01 contradicts."   the claim's own asserted value,
#                then the fact of that claim that refutes (supersedes, supports) exactly that value
#   ANCHOR       "Anchor A01 is consistent with | inconsistent with | partly consistent with | not assessable
#                from the cited evidence."    anchor_assessments only; the wording must match the stance
#   EVIDENCE     "The evidence at the evaluation time is described in E001."   a neutral remark
#   CATEGORY_WORD "C10 evidence is described."   the category word, with eligible cited evidence of that category
#   NUMBER       "The latest funding rate was <display> as a fraction in E005."   see _numeric
_SUBJ = r"(?P<s>@lit:\S+|(?!(?:the|cited|supplied|some) )[a-z]+)"
_ST = r"(?P<st>@L:\S+|@lit:\S+)"
_TAIL = r"(?P<tail>(?: \S+)*)"
_TEMPLATES = {
    "STATE": re.compile(rf"^(?:the )?(?:cited )?{_SUBJ} (?:(?:state|condition) )?(?:is|was) {_ST}{_TAIL}$"),
    "CLASSIFIED": re.compile(rf"^@c(?P<n>\d\d) classified (?:the )?(?:cited )?{_SUBJ} (?:state )?as {_ST}{_TAIL}$"),
    "BTC": re.compile(rf"^the btc market state (?:is|was) {_ST}{_TAIL}$"),
    "SIDE": re.compile(rf"^the cited (?P<w>buy|sell) side pressure (?:reflects|matches) {_ST}{_TAIL}$"),
    "PAYER": re.compile(r"^(?:the )?(?:cited )?funding (?:evidence |state )?(?:indicates|shows) "
                        rf"(?P<a>longs|shorts) pay (?P<b>longs|shorts){_TAIL}$"),
    "BULL": re.compile(r"^the observed direction condition is (?P<w>bullish|bearish)$"),
    "AVAILABLE": re.compile(rf"^(?:the )?(?:cited )?{_SUBJ} evidence (?:is|was) "
                            rf"(?P<p>described|available|unavailable|missing|partial|incomplete){_TAIL}$"),
    "CATEGORY": re.compile(r"^the category (?P<c>@lit:CAT:\S+) is (?P<p>not supplied|partial|excluded|rejected)"
                           rf"{_TAIL}$"),
    "SOME": re.compile(r"^some evidence categories are unavailable or only partly included$"),
    "CLAIM": re.compile(rf"^(?:the )?claim (?P<c>@lit:\S+) has (?:the )?assessed state {_ST}{_TAIL}$"),
    "FACT": re.compile(r"^(?:the )?fact (?P<f>@lit:\S+) is (?P<o>supported|contradicted|superseded|unresolved) "
                       rf"for claim (?P<c>@lit:\S+){_TAIL}$"),
    "ASSERTED": re.compile(rf"^(?:the )?claim (?P<c>@lit:\S+) asserted (?P<v>@lit:\S+|[a-z]+){_TAIL}$"),
    "REL": re.compile(r"^which (?P<f>@lit:\S+) (?P<o>contradicts|supersedes|supports)$"),
    "ANCHOR": re.compile(r"^anchor (?P<a>@lit:\S+) is (?P<v>consistent with|inconsistent with|partly consistent with|"
                         rf"not assessable from)(?: the)? cited evidence{_TAIL}$"),
    "EVIDENCE": re.compile(r"^(?:the )?(?:cited |supplied )?evidence(?: at the evaluation time)? (?:is|are) "
                           rf"(?:described|listed|cited|supplied|referenced){_TAIL}$"),
    "CATEGORY_WORD": re.compile(rf"^@c(?P<n>\d\d) evidence is described{_TAIL}$"),
}
_TAIL_WORDS = frozenset(("in", "of", "by", "from", "for", "at", "within", "on", "with", "this", "that", "the", "a",
                         "same", "cited", "supplied", "item", "items", "window", "evidence", "category", "note",
                         "section", "statement", "evaluation", "time", "interval", "period", "data", "here",
                         "again", "current", "state", "flow", "funding", "direction", "regime", "volatility",
                         "liquidity"))
_STANCE_WORDS = {"SUPPORTS": "consistent with", "CONTRADICTS": "inconsistent with",
                 "MIXED": "partly consistent with", "NOT_ASSESSABLE": "not assessable from"}
_CATEGORY_WORDS = {CategoryState.NOT_SUPPLIED: "not supplied", CategoryState.PARTIAL: "partial",
                   CategoryState.ALL_EXCLUDED: "excluded", CategoryState.REPORT_REJECTED: "rejected"}
_FACT_STRONG = frozenset(("verified", "confirmed", "confirms", "confirm", "proven", "proved", "established", "true",
                          "factual", "fact", "facts"))
_FILLER = frozenset(("the", "cited", "value", "range"))
_SIDE_NOUNS = frozenset(("long", "longs", "short", "shorts"))


def _bad(code: str, detail: str) -> OutputInvalid:
    return OutputInvalid(code, detail)


def _clauses(statement: str, tokens) -> list[list[tuple[str, str]]]:
    """Clauses of (text, kind) parts. Kind W: a lower-case word part (hyphen compounds split); V: the same for a
    cited all-lower-case literal such as "flow"; L: a literal kept exactly (state label, category word, identifier,
    upper-case state such as FALSE); N: a number. A clause ends at punctuation and starts at a conjunction."""
    raw = statement.split(" ")
    clauses: list[list[tuple[str, str]]] = [[]]
    for tok, r in zip(tokens, raw):
        if tok.kind == "WORD":
            low = tok.core.lower()
            if low in _CONJ and clauses[-1]:
                clauses.append([])
            parts = [(p, "W") for p in low.split("'")[0].split("-")]
            if low.endswith("n't"):
                parts.append(("not", "W"))
        elif tok.kind == "LITERAL":
            plain = tok.core == tok.core.lower() and tok.core not in CATEGORY_WORDS and WORD.fullmatch(tok.core)
            parts = [(p, "V") for p in tok.core.split("-")] if plain else [(tok.core, "L")]
        else:
            parts = [(tok.core, "N")]
        clauses[-1].extend(parts)
        if len(r) > 1 and r[-1] in CLAUSE_END:
            clauses.append([])
    return [c for c in clauses if c]


def _encode(clause) -> list[str]:
    out = []
    for p, k in clause:
        if k in ("W", "V"):
            out.append(p)
        elif k == "N":
            out.append("#")
        elif p in LABEL_DIMS:
            out.append(f"@L:{p}")
        elif p in CATEGORY_WORDS:
            out.append("@c" + p[1:])
        else:
            out.append(f"@lit:{p}")
    return out


@dataclass(frozen=True)
class _Env:
    ctx: RequestContext
    cited: frozenset
    items: tuple                      # the cited evidence items
    t1: bool
    section: str
    anchor_id: str | None
    stance: str | None
    claim_id: str | None
    numbers: tuple                    # value ids of the statement's written numbers, in order

# Source policy for the optional words after a construction. A suffix is only a remark: it may name the item or items
# that satisfied this construction's own evidence predicate, an interval of those items, and neutral words. It never
# names a category word (C10 to C13; "C10 classified ..." already says it), a time, another cited item or a subject
# other than the construction's own. The structured citation stays in refs[]; the text can neither add nor swap it.
_SUBJECT_WORDS = frozenset(("flow", "funding", "direction", "regime", "volatility", "liquidity"))


def _tail_ok(tail: str, env: _Env, owners: set[str], subjects: frozenset = frozenset()) -> bool:
    items = [i for i in env.items if i.evidence_id in owners]
    intervals = {a.value for i in items for a in i.attributes if a.name == "interval"}
    for w in tail.split():
        if w.startswith("@lit:"):
            if w[5:] not in owners and w[5:] not in intervals:
                return False
        elif w in _SUBJECT_WORDS:
            if w not in subjects:
                return False
        elif w not in _TAIL_WORDS:
            return False
    return True


def _owners(name: str, g: dict, state, env: _Env) -> tuple[set[str], frozenset]:
    """The items (or handles) whose evidence supports the construction, and its own subject words."""
    cat = {"BTC": None, "SIDE": Category.C10, "PAYER": Category.C10}
    if name in ("STATE", "CLASSIFIED"):
        hit = [i for i in env.items if i.subject == _subject(g) and i.state == state]
    elif name == "BTC":
        hit = [i for i in env.items if i.state == state and i.category is Category.C10
               and i.subject in LABEL_DIMS.get(state, ())]
    elif name == "SIDE":
        hit = [i for i in env.items if i.subject == "flow" and i.state == state and i.category is cat[name]]
    elif name == "PAYER":
        want = {("longs", "shorts"): "LONGS_PAY_SHORTS", ("shorts", "longs"): "SHORTS_PAY_LONGS"}.get((g["a"], g["b"]))
        hit = [i for i in env.items if i.subject == "funding" and i.state == want and i.category is cat[name]]
    elif name == "AVAILABLE":
        hit = [i for i in env.items if i.subject == _subject(g)]
    elif name == "CLAIM":
        return {g["c"][5:]}, frozenset()
    elif name == "ASSERTED":
        return {g["c"][5:]}, frozenset()
    elif name == "FACT":
        return {g["f"][5:], g["c"][5:]}, frozenset()
    elif name == "CATEGORY_WORD":                             # "C12 evidence ...": only that category's own evidence
        if g["n"] == "13":
            own = {r for r in env.cited if r in env.ctx.claims or r in env.ctx.facts}
            if env.claim_id:                                  # in a claim note: that claim and its own facts
                own = {r for r in own if r == env.claim_id or (r in env.ctx.facts and env.ctx.facts[r][0] == env.claim_id)}
            return own, frozenset()
        return {i.evidence_id for i in env.items if CATEGORY_TEXT[i.category] == f"C{g['n']}"}, frozenset()
    elif name in ("ANCHOR", "EVIDENCE"):
        return set(env.cited), frozenset()                    # a remark about what the statement itself cites
    else:                                                     # CATEGORY, SOME: no source suffix
        return set(), frozenset()
    return {i.evidence_id for i in hit}, frozenset(i.subject for i in hit if i.subject in _SUBJECT_WORDS)


def _subject(g: dict) -> str:
    return g["s"][5:] if g["s"].startswith("@lit:") else g["s"]


def _has_item(env: _Env, subject: str, state: str | None = None, category: Category | None = None) -> bool:
    return any(i.subject == subject and (state is None or i.state == state) and (category is None or i.category is category)
               for i in env.items)


def _availability(env: _Env, subject: str, word: str) -> None:
    ctx = env.ctx
    anywhere = [i for i in ctx.items.values() if i.subject == subject]
    listed = any(u.subject in (subject, f"C10.{subject}") for u in ctx.unavailable)
    if word in ("described", "available"):
        ok = _has_item(env, subject)                                         # eligible and cited
    elif word in ("unavailable", "missing"):
        ok = not anywhere and listed                                          # no eligible item, and a stated reason
    else:                                                                     # partial, incomplete
        ok = any(i.subject == subject and i.values_withheld for i in env.items)
    if not ok:
        raise _bad("STATUS_NOT_EVIDENCED", f"{subject} evidence is not {word}")


def _check(name: str, m, env: _Env) -> None:
    """The evidence predicate of one construction; raises OutputInvalid."""
    g = m.groupdict()
    ctx = env.ctx
    state = g["st"].split(":", 1)[1] if g.get("st") and g["st"].startswith("@L:") else (
        g["st"][5:] if g.get("st") else None)
    if name == "STATE":
        if not _has_item(env, _subject(g), state):
            raise _bad("STATE_NOT_EVIDENCED", f"{state} for {_subject(g)}")
    elif name == "CLASSIFIED":
        if not any(i.subject == _subject(g) and i.state == state and CATEGORY_TEXT[i.category] == f"C{g['n']}"
                   for i in env.items):
            raise _bad("STATE_NOT_EVIDENCED", f"C{g['n']} did not classify {_subject(g)} as {state}")
    elif name == "BTC":
        dims = LABEL_DIMS.get(state, ())
        if len(dims) != 1 or not _has_item(env, dims[0], state, Category.C10):
            raise _bad("STATE_NOT_EVIDENCED", f"{state} for the BTC market state")
    elif name == "SIDE":
        want = "BUY_DOMINANT" if g["w"] == "buy" else "SELL_DOMINANT"
        if state != want or not _has_item(env, "flow", state, Category.C10):
            raise _bad("STATE_NOT_EVIDENCED", f"{g['w']}-side pressure for {state}")
    elif name == "PAYER":
        want = {("longs", "shorts"): "LONGS_PAY_SHORTS", ("shorts", "longs"): "SHORTS_PAY_LONGS"}.get((g["a"], g["b"]))
        if want is None or not _has_item(env, "funding", want, Category.C10):
            raise _bad("STATE_NOT_EVIDENCED", f"{g['a']} pay {g['b']} without matching funding evidence")
    elif name == "AVAILABLE":
        _availability(env, _subject(g), g["p"])
    elif name == "CATEGORY":
        cat = g["c"][5:]
        c = next((x for x in Category if f"CAT:{x.value}" == cat), None)
        if c is None or cat not in env.cited or _CATEGORY_WORDS.get(ctx.categories.get(c)) != g["p"]:
            raise _bad("STATUS_NOT_EVIDENCED", f"{cat} is not {g['p']}")
    elif name == "SOME":
        if not any(s not in (CategoryState.INCLUDED, CategoryState.NOT_USED_BY_TASK) for s in ctx.categories.values()):
            raise _bad("STATUS_NOT_EVIDENCED", "every category is included")
    elif name == "CLAIM":
        claim = g["c"][5:]
        if claim not in ctx.claims or claim not in env.cited or (env.claim_id and claim != env.claim_id) \
                or ctx.claims[claim].state != state:
            raise _bad("CLAIM_NOT_EVIDENCED", f"{claim} does not have the assessed state {state}")
    elif name == "FACT":
        fact, claim = g["f"][5:], g["c"][5:]
        owner = ctx.facts.get(fact)
        if owner is None or owner[0] != claim or fact not in env.cited or claim not in env.cited \
                or owner[1].outcome.lower() != g["o"] or (env.claim_id and claim != env.claim_id):
            raise _bad("CLAIM_NOT_EVIDENCED", f"{fact} is not {g['o']} for {claim}")
    elif name == "ASSERTED":
        claim, value = g["c"][5:], _bare(g["v"])
        own = [f for fr in ctx.claims[claim].frames for f in fr.facts] if claim in ctx.claims else []
        if claim not in env.cited or (env.claim_id and claim != env.claim_id) or not any(
                f.claim_asserted.lower() == value.lower() for f in own):
            raise _bad("CLAIM_NOT_EVIDENCED", f"{claim} did not assert {value}")
    elif name == "ANCHOR":
        if env.section != "anchor_assessments" or g["a"][5:] != env.anchor_id \
                or _STANCE_WORDS.get(env.stance) != g["v"]:
            raise _bad("ANCHOR_NOT_EVIDENCED", "the wording does not match the anchor and its stance")
    elif name == "CATEGORY_WORD":
        if not any(CATEGORY_TEXT[i.category] == f"C{g['n']}" for i in env.items) and not (
                g["n"] == "13" and any(r in ctx.claims or r in ctx.facts for r in env.cited)):
            raise _bad("UNSUPPORTED_CONSTRUCTION", f"no cited C{g['n']} evidence")
    if "tail" in g:
        owners, subjects = _owners(name, g, state, env)
        if not _tail_ok(g["tail"], env, owners, subjects):
            raise _bad("SOURCE_NOT_EVIDENCED", f"the words after the {name.lower()} construction name a source "
                       "that does not support it")


_UNIT_PER_INTERVAL = "per 1h interval"


def _bare(token: str) -> str:
    return token[5:] if token.startswith("@lit:") else token


_REL_OUTCOME = {"contradicts": "CONTRADICTED", "supersedes": "SUPERSEDED", "supports": "SUPPORTED"}


def _check_rel(m, prev, env: _Env) -> None:
    """REL follows ASSERTED and names a fact of that claim for exactly the asserted value, with the matching outcome."""
    fact = m.group("f")[5:]
    owner = env.ctx.facts.get(fact)
    claim, value = prev.group("c")[5:], _bare(prev.group("v"))
    if owner is None or fact not in env.cited or owner[0] != claim or owner[1].claim_asserted.lower() != value.lower() \
            or owner[1].outcome != _REL_OUTCOME[m.group("o")]:
        raise _bad("CLAIM_NOT_EVIDENCED", f"{fact} does not {m.group('o')} {value} for {claim}")


def _metric_words(value, owner) -> set[str]:
    words = set(re.findall("[a-z]{2,}", value.field_path.lower())) | set(re.findall("[a-z]{2,}", owner.subject.lower()))
    words |= set(re.findall("[a-z]{2,}", (value.qualifier or "").lower()))
    for a in owner.attributes:
        if a.name in ("event_type", "measure"):
            words |= set(re.findall("[a-z]{2,}", a.value.lower()))
    words |= {w for ph in UNIT_PHRASES.get(unit_class(value.unit), ()) for w in ph}      # "the index level"
    return words | DESCRIPTORS.get(unit_class(value.unit), frozenset()) | GENERIC_DESCRIPTORS


def _unit_words(value, owner) -> set[str]:
    cls = unit_class(value.unit)
    allowed = {w for ph in UNIT_PHRASES.get(cls, ()) for w in ph} | CONNECTORS | UNIT_ATTRIBUTION | {"a", "as"}
    if _UNIT_PER_INTERVAL in value.unit:                    # an hourly rate may say so, and nothing else about time
        allowed |= {"per", "hour", "interval"}
        allowed |= {f"@lit:{a.value}" for a in owner.attributes if a.name == "interval"}
    return allowed


def _unit_remark(toks: list[str], env: _Env, used: int) -> bool:
    """A short unit remark after a written number ("measured in BTC"): only the words of that number's own unit."""
    if not used or not toks:
        return False
    ctx = env.ctx
    b = ctx.values.get(env.numbers[used - 1])
    o = ctx.items.get(b.owner) if b else None
    v = next((x for x in o.values if x.value_id == b.value_id), None) if o else None
    return bool(v) and all(t in _unit_words(v, o) for t in toks)


def _numeric(toks: list[str], env: _Env, used: int) -> int:
    """NUMBER: "<metric words> is|was <number> [to <number>] [unit words] [in E005]". The metric words must be words of
    the value's own source path, subject, qualifier or event type; unit words only those of its unit (an hourly funding
    rate may say 'per hour', never 'per day'); the only source phrase is 'in' plus the value's own item. Returns the
    number of written numbers consumed."""
    ctx = env.ctx
    marks = [i for i, t in enumerate(toks) if t == "#"]
    n = len(marks)
    if n not in (1, 2) or used + n > len(env.numbers) or (n == 2 and toks[marks[0] + 1:marks[1]] not in (["to"], ["and"])):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "a number needs its own construction")
    bounds = [ctx.values.get(v) for v in env.numbers[used:used + n]]
    owners = [ctx.items.get(b.owner) if b else None for b in bounds]
    values = [next((x for x in o.values if x.value_id == b.value_id), None) if o else None
              for b, o in zip(bounds, owners)]
    if any(v is None or o is None for v, o in zip(values, owners)):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "the number has no eligible source item")
    before = toks[:marks[0]]
    if len(before) < 2 or before[-1] not in ("is", "was"):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "a number is written as '<metric> is <number>'")
    allowed = set.intersection(*(_metric_words(v, o) for v, o in zip(values, owners)))
    subjects = {f"@lit:{o.subject}" for o in owners}
    # an upper-case cited attribute word (CPI, LEVEL) is a literal for the grammar and an ordinary word here
    metric = [t[5:].lower() if t.startswith("@lit:") and t[5:].isalpha() else t for t in before[:-1]]
    if not all(t in allowed or t in _FILLER or t in subjects for t in metric):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "the metric words are not those of the cited value")
    rest = toks[marks[-1] + 1:]
    owner_ids = {o.evidence_id for o in owners}
    if len(rest) >= 2 and rest[-2] in ("in", "for", "from") and rest[-1].startswith("@lit:"):
        src = rest[-1][5:]
        linked = src in env.cited and src in ctx.facts and all(
            v.value_id in ctx.facts[src][1].linked_value_ids for v in values)       # a cited fact that links the value
        if {src} != owner_ids and not linked:
            raise _bad("UNSUPPORTED_CONSTRUCTION", "the source is not the value's own item")
        rest = rest[:-2]
    elif rest[-4:] in (["in", "the", "cited", "item"], ["at", "the", "evaluation", "time"]):
        rest = rest[:-4]
    unit = set.intersection(*(_unit_words(v, o) for v, o in zip(values, owners)))
    if not all(t in unit for t in rest):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "an unsupported unit or time qualifier follows the number")
    return n


def _first_match(enc: str):
    for name, rx in _TEMPLATES.items():
        m = rx.match(enc)
        if m:
            return name, m
    return None, None


def narrative_check(statement: str, tokens, cited: set[str], ctx: RequestContext, numbers=(), section: str = "summary",
                    anchor_id: str | None = None, stance: str | None = None, claim_id: str | None = None) -> None:
    """Default deny for one model-written statement: the trading-authority screen, then every clause must be an
    approved construction bound to its evidence predicate."""
    t1 = ctx.task_id is TaskId.BTC_MARKET_STATE
    cited_items = [ctx.items[r] for r in cited if r in ctx.items]
    clauses = _clauses(statement, tokens)
    all_words = [p for c in clauses for p, k in c if k == "W"]

    for i, tok in enumerate(tokens):
        if tok.kind == "WORD":
            low = tok.core.lower()
            modal = low in ("might", "could", "can") or tok.core == "may"          # "May" is a month
            if modal and not (i + 1 < len(tokens) and tokens[i + 1].kind == "WORD" and tokens[i + 1].core.lower() == "not"):
                raise _bad("PROHIBITED_TRADE_LANGUAGE", f"modal {low}")
            if re.sub("[^a-z]", "", low) in _ALIAS_KEYS:
                raise _bad("STATE_ALIAS", tok.core)
            if tok.core in LABEL_DIMS:                   # an uncited canonical state written as a plain word
                raise _bad("STATE_NOT_EVIDENCED", f"{tok.core} is not cited")
            if tok.core == "us":                         # the pronoun; "US" the country is a different token
                raise _bad("PROHIBITED_TRADE_LANGUAGE", "us")
    if _LIQUIDATION_WORDS & set(all_words) and (_side_word_present(clauses) or "buyers" in all_words
                                                or "sellers" in all_words):
        raise _bad("LIQUIDATION_SIDE_UNSUPPORTED", "no side-specific liquidation evidence is supplied")

    for clause in clauses:                               # trading authority: kept as a second layer, not extended
        words = [p for p, k in clause if k == "W"]
        for i, w in enumerate(words):
            nxt = words[i + 1] if i + 1 < len(words) else ""
            if w in _HARD:
                raise _bad("PROHIBITED_TRADE_LANGUAGE", w)
            if (w, nxt) in _BIGRAMS:
                raise _bad("PROHIBITED_TRADE_LANGUAGE", f"{w} {nxt}")
            if w in ("target", "targets", "targeted", "targeting") and nxt not in ("range", "ranges", "rate", "rates"):
                raise _bad("PROHIBITED_TRADE_LANGUAGE", w)
            if w == "hedge" and nxt not in ("fund", "funds"):
                raise _bad("PROHIBITED_TRADE_LANGUAGE", w)
            if w in ("trade", "trading") and not (w == "trading" and nxt in _TRADING_NOUN_AFTER):
                raise _bad("PROHIBITED_TRADE_LANGUAGE", w)
            if w in ("buy", "buys", "sell", "sells", "buying", "selling") and nxt not in _FLOW_HEADS:
                raise _bad("PROHIBITED_TRADE_LANGUAGE", w)
        if words[:2] == ["it", "is"] and "to" in words[2:]:
            raise _bad("PROHIBITED_TRADE_LANGUAGE", "it is ... to")
        first = next((w for w in words if w not in _CONJ | {"also", "just"}), "")
        after = words[words.index(first) + 1] if first and words.index(first) + 1 < len(words) else ""
        if first in _IMPERATIVE and first not in ("buy", "sell") and not (
                first in ("increase", "decrease", "raise", "lower") and after in _NOUN_AFTER_IMPERATIVE):
            raise _bad("PROHIBITED_TRADE_LANGUAGE", f"imperative {first}")
        if first in _SIDE_VERBS and after in _SIDE_OBJECT:
            raise _bad("PROHIBITED_TRADE_LANGUAGE", f"imperative {first}")
        objects = [w for j, w in enumerate(words) if w in _TRADE_OBJECTS and not (
            w in _SIDE_WORDS and (words[j + 1:j + 2] or [""])[0] in _TERM_WORDS)]
        if objects and any(w in _TRADE_VERBS for w in words):
            raise _bad("PROHIBITED_TRADE_LANGUAGE", "trade action on a position")
        if "next" in words and _MOVES & set(words):
            raise _bad("PROHIBITED_TRADE_LANGUAGE", "forward-looking movement")

    # claims are never facts; a negated clause ("could not be verified") asserts no verification
    for clause in clauses:
        written = {p for p, k in clause if k == "W"}
        if written & {"not", "no", "cannot", "never", "without", "unverified"}:
            continue
        strong, plain = written & (_FACT_STRONG - {"fact", "facts"}), written & {"fact", "facts"}
        if (strong and not any(r in ctx.facts and ctx.facts[r][1].outcome == "SUPPORTED" for r in cited)) or (
                plain and not any(r in ctx.facts for r in cited)):
            raise _bad("CLAIM_CITED_AS_FACT", "factual wording without a cited, supporting fact")

    env = _Env(ctx=ctx, cited=frozenset(cited), items=tuple(cited_items), t1=t1, section=section, anchor_id=anchor_id,
               stance=stance, claim_id=claim_id, numbers=tuple(numbers))
    matched, used = [], 0
    for clause in clauses:
        enc = _encode(clause)
        while len(enc) > 1 and enc[0] in _CONJ:
            enc = enc[1:]
        if "#" in enc:
            used += _numeric(enc, env, used)
            matched.append(("NUMBER", None))
            continue
        if matched and matched[-1][0] == "NUMBER" and _unit_remark(enc, env, used):
            matched.append(("UNITS", None))
            continue
        name, m = _first_match(" ".join(enc))
        if m is None:
            words = {p for p, k in clause if k in ("W", "V")} | {p.lower() for p, k in clause if k == "L"}
            cats = [p for p, k in clause if k == "L" and p in CATEGORY_WORDS and p != "C10"]
            if not t1 and words & ASSET_WORDS:
                raise _bad("ASSET_CONCLUSION_IN_MACRO_TASK", sorted(words & ASSET_WORDS)[0])
            if words & {"bullish", "bearish"}:
                raise _bad("SENTIMENT_NOT_EVIDENCED", "bullish or bearish outside the observed direction construction")
            if cats:
                raise _bad("CROSS_CATEGORY_ATTRIBUTION", f"{cats[0]} cannot carry this assertion")
            if _LIQUIDATION_WORDS & words:
                raise _bad("LIQUIDATION_SIDE_UNSUPPORTED", "no liquidation evidence supports this clause")
            raise _bad("UNSUPPORTED_CONSTRUCTION", "not one of the approved constructions")
        if name == "REL":
            if not matched or matched[-1][0] != "ASSERTED":
                raise _bad("UNSUPPORTED_CONSTRUCTION", "a fact relation needs the asserted value before it")
            _check_rel(m, matched[-1][1], env)
        else:
            _check(name, m, env)
        matched.append((name, m))
    if section == "anchor_assessments" and sum(1 for h in matched if h[0] == "ANCHOR") != 1:
        raise _bad("ANCHOR_NOT_EVIDENCED", "an anchor assessment states its anchor and stance exactly once")
    if used != len(env.numbers):
        raise _bad("UNSUPPORTED_CONSTRUCTION", "a declared number is not written in an approved construction")
    for i, hit in enumerate(matched):
        if hit[0] == "BULL":                             # exactly: the observed condition, then its state, nothing else
            label = "TRENDING_UP" if hit[1].group("w") == "bullish" else "TRENDING_DOWN"
            nxt = matched[i + 1] if i + 1 < len(matched) else None
            if not t1 or i != 0 or len(matched) != 2 or not nxt or nxt[0] != "STATE" or \
                    _subject(nxt[1].groupdict()) != "direction" or nxt[1].group("st") != f"@L:{label}":
                raise _bad("SENTIMENT_NOT_EVIDENCED", "needs exactly the observed direction condition and its state")


def _side_word_present(clauses) -> bool:
    for c in clauses:
        ws = [p for p, k in c if k == "W"]
        for i, w in enumerate(ws):
            if w in _SIDE_WORDS and (ws[i + 1:i + 2] or [""])[0] not in _TERM_WORDS:
                return True
    return False



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
