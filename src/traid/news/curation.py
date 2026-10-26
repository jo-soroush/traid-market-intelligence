"""Claim admission, curation validation and normalization into event frames (design §4.1-§4.3).

Identity lives only on a ``CuratedEvent``; a document number, subject or action written inside a
proposition is a predicate to verify. A frame is one event plus the union of its propositions'
facts, so splitting, merging, duplicating, reordering or renaming cannot change a result. Two
events that are neither provably incompatible (from asserted identity alone) nor declared
distinct make the claim UNVERIFIED; no association is ever guessed. Roles come from the frame
type and contents, never from the curator. An invalid curation is never repaired.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
import re

from traid.news.models import (
    BLS_FRAMES, CPI_SERIES, DATE_ROLES, FOMC_FRAMES, NON_ASSERTIVE_SPANS, REGULATORY_FRAMES, RESIDUAL_SPANS,
    SERIES_TOKENS, ChangeToken, ClaimRecord, CurationRecord, DateToken, FactField, FactRole, FomcAction, FrameType,
    NonSourceEvent, RegAction, RegStatus, Sequence, SpanCategory, canonical_json, decimal_text,
)
from traid.news.text import canonical_file_number, parse_date_value

MAX_DIGITS = 64
DATE_RE = r"\d{4}-\d{2}-\d{2}"
PERIOD_RE = r"\d{4}-(0[1-9]|1[0-2])"
RESIDUAL_REASON = {SpanCategory.INTERPRETATION: "RESIDUAL_INTERPRETATION_NOT_VERIFIED",
                   SpanCategory.EMBEDDED_INSTRUCTION: "RESIDUAL_EMBEDDED_INSTRUCTION",
                   SpanCategory.NUMERIC_ETF_MARKET_DATA: "NUMERIC_ETF_MARKET_DATA_NOT_NEWS",
                   SpanCategory.UNCURATABLE: "RESIDUAL_UNCURATABLE"}
F = FactField

ALLOWED_FACTS = {
    FrameType.REG_DOC: {F.ACTION, F.SUBJECT, F.DATE, F.RELEASE_NO, F.FILE_NUMBER, F.VENUE, F.ACCELERATED},
    FrameType.REG_EVENT: {F.ACTION, F.SUBJECT, F.DATE, F.VENUE, F.ACCELERATED},
    FrameType.REG_STATUS_AT: {F.STATUS},
    FrameType.REG_CURRENT_STATUS: {F.STATUS, F.SINCE},
    FrameType.LATEST_IDENTITY: {F.MEMBER_IS_LATEST, F.ACTION, F.DATE},
    FrameType.NON_SOURCE_EVENT: {F.EVENT, F.DATE},
    FrameType.MACRO_VALUE: {F.VALUE, F.UNIT, F.PRELIMINARY},
    FrameType.MACRO_CHANGE: {F.CHANGE},
    FrameType.MACRO_CONSENSUS: {F.CONSENSUS, F.SURPRISE},
    FrameType.FOMC_DECISION: {F.ACTION, F.TARGET_RANGE, F.CHANGE_SIZE},
    FrameType.FOMC_CURRENT_RANGE: {F.TARGET_RANGE},
    FrameType.FOMC_SCHEDULE: {F.SCHEDULED_ON, F.ANNOUNCEMENT_TIME, F.PROJECTIONS},
}
IDENTITY_FIELDS = {
    FrameType.REG_DOC: ({"document_number"}, set()),
    FrameType.REG_EVENT: ({"subjects", "action"}, set()),
    FrameType.REG_STATUS_AT: ({"subjects", "status_date"}, set()),
    FrameType.REG_CURRENT_STATUS: ({"subjects"}, set()),
    FrameType.LATEST_IDENTITY: ({"sequence"}, {"sequence_file", "member_document_number", "member_pattern", "member_date",
                                               "board_date"}),
    FrameType.NON_SOURCE_EVENT: ({"event_type"}, {"subjects"}),
    FrameType.MACRO_VALUE: ({"series", "period", "scope"}, set()),
    FrameType.MACRO_CHANGE: ({"series", "period", "change_kind"}, set()),
    FrameType.MACRO_CONSENSUS: ({"series", "period"}, set()),
    FrameType.FOMC_DECISION: ({"board_date"}, set()),
    FrameType.FOMC_CURRENT_RANGE: (set(), set()),
    FrameType.FOMC_SCHEDULE: ({"meeting_start", "meeting_end"}, set()),
}


class CurationInvalid(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class NormFact:
    field: str                       # FactField value
    value: str                       # canonical value
    token: str | None
    role: FactRole
    alternatives: tuple[str, ...] = ()   # admissible interpretations (G4): date roles, actions, subjects

    def key(self):
        return (self.field, self.value, self.token or "", self.role.value, self.alternatives)


@dataclass(frozen=True)
class NormEvent:
    cid: str                         # canonical id E<k>
    frame_type: FrameType
    identity: tuple[tuple[str, object], ...]     # canonical asserted identity
    resolved: tuple[tuple[str, object], ...]     # identity after resolution at T (fund subjects)
    facts: tuple[NormFact, ...]
    key: str
    problem: str | None = None       # identity unresolved or self-contradictory: the frame is UNVERIFIED

    @property
    def ident(self) -> dict:
        return dict(self.resolved)


@dataclass(frozen=True)
class Normalized:
    events: tuple[NormEvent, ...]
    residuals: tuple[tuple[str, SpanCategory], ...]      # (frame key, span category)
    distinct: tuple[tuple[str, str], ...]
    association_problem: str | None
    form: str = field(default="")


# --------------------------------------------------------------------- value canonicalization
def canonical_subject(value: str) -> str:
    v = value.strip()
    if v == "BTC":
        return "BTC"                                # the bare token: asset or ticker (admissible set)
    if v.startswith("FUND:"):
        name = re.sub(r"\s+", " ", v[5:]).strip()
        if not name:
            raise CurationInvalid("VALUE:SUBJECT")
        return f"FUND:{name}"
    f = canonical_file_number(v)
    if f is None:
        raise CurationInvalid("VALUE:SUBJECT")
    return f


def _decimal(value: str, field_name: str) -> Decimal:
    try:
        d = Decimal(value.strip().replace(",", ""))
    except (ArithmeticError, ValueError):          # whatever traps the ambient context enables
        raise CurationInvalid(f"VALUE:{field_name}") from None
    # bounded so the exact plain-notation text stays small (1E+999999999 would be a billion digits)
    if not d.is_finite() or len(d.as_tuple().digits) > MAX_DIGITS or abs(d.adjusted()) > MAX_DIGITS:
        raise CurationInvalid(f"VALUE:{field_name}")
    return d


def _dec(d: Decimal) -> str:
    """Exact canonical text: never rounded, never dependent on the ambient decimal context."""
    return decimal_text(d)


def _date_label(value: str, field_name: str) -> str:
    d = parse_date_value(value)
    if d is None or hasattr(d, "hour"):
        raise CurationInvalid(f"VALUE:{field_name}")
    return d.isoformat()


def _bool(value: str, field_name: str) -> str:
    v = value.strip().lower()
    if v not in ("true", "false"):
        raise CurationInvalid(f"VALUE:{field_name}")
    return v


def canonical_value(frame_type: FrameType, fact) -> tuple[str, str | None]:
    """(canonical value, canonical token) or CurationInvalid."""
    f, v, token = fact.field, fact.value, fact.token
    if f is F.DATE:
        try:
            token = DateToken(token).value
        except ValueError:
            raise CurationInvalid("VALUE:DATE_TOKEN") from None
        d = parse_date_value(v)
        if d is None:
            raise CurationInvalid("VALUE:DATE")
        return d.isoformat(), token
    if f is F.CHANGE_SIZE:
        try:
            token = ChangeToken(token).value
        except ValueError:
            raise CurationInvalid("VALUE:CHANGE_SIZE_TOKEN") from None
        d = _decimal(v, "CHANGE_SIZE")
        if d <= 0:
            raise CurationInvalid("VALUE:CHANGE_SIZE")
        return _dec(d), token
    if token is not None:
        raise CurationInvalid(f"VALUE:{f.value}_TOKEN_NOT_ALLOWED")
    if f is F.ACTION:
        vocabulary = FomcAction if frame_type in FOMC_FRAMES else RegAction
        try:
            return vocabulary(v.strip().upper()).value, None
        except ValueError:
            raise CurationInvalid("VALUE:ACTION") from None
    if f is F.SUBJECT:
        return canonical_subject(v), None
    if f is F.FILE_NUMBER:
        c = canonical_file_number(v)
        if c is None:
            raise CurationInvalid("VALUE:FILE_NUMBER")
        return c, None
    if f is F.RELEASE_NO:
        r = re.sub(r"^Release No\.\s*", "", v.strip())
        if not re.fullmatch(r"\d{2}-\d{4,6}", r):
            raise CurationInvalid("VALUE:RELEASE_NO")
        return r, None
    if f is F.VENUE:
        r = re.sub(r"[^A-Z0-9]", "", v.upper())
        if not r:
            raise CurationInvalid("VALUE:VENUE")
        return r, None
    if f in (F.ACCELERATED, F.PROJECTIONS, F.PRELIMINARY, F.MEMBER_IS_LATEST):
        return _bool(v, f.value), None
    if f is F.STATUS:
        try:
            return RegStatus(v.strip().upper()).value, None
        except ValueError:
            raise CurationInvalid("VALUE:STATUS") from None
    if f is F.SINCE:
        return _date_label(v, "SINCE"), None
    if f is F.EVENT:
        try:
            return NonSourceEvent(v.strip().upper()).value, None
        except ValueError:
            raise CurationInvalid("VALUE:EVENT") from None
    if f in (F.VALUE, F.CHANGE, F.CONSENSUS, F.SURPRISE):
        return _dec(_decimal(v, f.value)), None
    if f is F.UNIT:
        r = re.sub(r"\s+", " ", v.strip().lower())
        if not r:
            raise CurationInvalid("VALUE:UNIT")
        return r, None
    if f is F.TARGET_RANGE:
        m = re.fullmatch(r"\s*([0-9.]+)\s*(?:-|to|–)\s*([0-9.]+)\s*%?\s*", v)
        if m is None:
            raise CurationInvalid("VALUE:TARGET_RANGE")
        lo, hi = _decimal(m.group(1), "TARGET_RANGE"), _decimal(m.group(2), "TARGET_RANGE")
        if not 0 <= lo < hi:
            raise CurationInvalid("VALUE:TARGET_RANGE")
        return f"{_dec(lo)}-{_dec(hi)}", None
    if f is F.SCHEDULED_ON:
        m = re.fullmatch(rf"({DATE_RE})/({DATE_RE})", v.strip())
        if m is None:
            raise CurationInvalid("VALUE:SCHEDULED_ON")
        return f"{_date_label(m.group(1), 'SCHEDULED_ON')}/{_date_label(m.group(2), 'SCHEDULED_ON')}", None
    if f is F.ANNOUNCEMENT_TIME:
        d = parse_date_value(v)
        if d is None or not hasattr(d, "hour"):
            raise CurationInvalid("VALUE:ANNOUNCEMENT_TIME")
        return d.isoformat(), None
    raise CurationInvalid(f"VALUE:{f.value}")


def canonical_identity(frame_type: FrameType, identity) -> dict:
    raw = {k: v for k, v in identity.model_dump(exclude={"schema_version"}).items() if v not in (None, ())}
    required, optional = IDENTITY_FIELDS[frame_type]
    if not required <= set(raw) or set(raw) - required - optional:
        raise CurationInvalid(f"IDENTITY_FIELDS:{frame_type.value}")
    out: dict = {}
    for k, v in raw.items():
        if k == "subjects":
            subjects = tuple(sorted({canonical_subject(s) for s in v}))
            if frame_type in (FrameType.REG_STATUS_AT, FrameType.REG_CURRENT_STATUS, FrameType.NON_SOURCE_EVENT) \
                    and len(subjects) != 1:
                raise CurationInvalid("IDENTITY:ONE_SUBJECT_REQUIRED")
            out[k] = subjects
        elif k == "document_number" or k == "member_document_number":
            if not re.fullmatch(r"\d{4}-\d{5}", v.strip()):
                raise CurationInvalid(f"IDENTITY:{k.upper()}")
            out[k] = v.strip()
        elif k == "action":
            try:
                out[k] = RegAction(v.strip().upper()).value
            except ValueError:
                raise CurationInvalid("IDENTITY:ACTION") from None
        elif k in ("status_date", "member_date", "board_date", "meeting_start", "meeting_end"):
            out[k] = _date_label(v, k.upper())
        elif k == "sequence_file":
            c = canonical_file_number(v)
            if c is None:
                raise CurationInvalid("IDENTITY:SEQUENCE_FILE")
            out[k] = c
        elif k == "series":
            if v not in SERIES_TOKENS:
                raise CurationInvalid("IDENTITY:SERIES")
            out[k] = v
        elif k == "period":
            if not re.fullmatch(PERIOD_RE, v):
                raise CurationInvalid("IDENTITY:PERIOD")
            out[k] = v
        else:
            out[k] = str(v.value if hasattr(v, "value") else v)
    if frame_type is FrameType.LATEST_IDENTITY:
        seq = out["sequence"]
        if seq == Sequence.SEC_ORDERS_ON_FILE.value:
            if "sequence_file" not in out or "board_date" in out:
                raise CurationInvalid("IDENTITY:SEC_ORDERS_ON_FILE")
            if ("member_pattern" in out) != ("member_date" in out):
                raise CurationInvalid("IDENTITY:MEMBER_PATTERN_AND_DATE")
            if "member_document_number" in out and "member_pattern" in out:
                raise CurationInvalid("IDENTITY:ONE_MEMBER_IDENTIFIER")
        elif {"sequence_file", "member_document_number", "member_pattern", "member_date"} & set(out):
            raise CurationInvalid("IDENTITY:FOMC_STATEMENTS")
    if frame_type is FrameType.FOMC_SCHEDULE and out["meeting_start"] > out["meeting_end"]:
        raise CurationInvalid("IDENTITY:MEETING_DATES")
    return out


def family(frame_type: FrameType, identity: dict) -> str:
    if frame_type in BLS_FRAMES:
        return "BLS"
    if frame_type in FOMC_FRAMES or identity.get("sequence") == Sequence.FOMC_STATEMENTS.value:
        return "FOMC"
    return "REGULATORY"


def incompatible(a: tuple, b: tuple) -> bool:
    """Provable incompatibility from asserted identity only (§4.3 step 5), no evidence lookup."""
    (ta, ia), (tb, ib) = a, b
    if family(ta, ia) != family(tb, ib):
        return True
    docs_a = {ia.get("document_number"), ia.get("member_document_number")} - {None}
    docs_b = {ib.get("document_number"), ib.get("member_document_number")} - {None}
    if docs_a and docs_b and docs_a.isdisjoint(docs_b):
        return True
    if ia.get("subjects") and ib.get("subjects") and set(ia["subjects"]).isdisjoint(ib["subjects"]):
        return True
    acts_a = {ia.get("action"), ia.get("event_type")} - {None}
    acts_b = {ib.get("action"), ib.get("event_type")} - {None}
    if acts_a and acts_b and acts_a.isdisjoint(acts_b):
        return True
    if family(ta, ia) == "BLS" and (ia["series"] != ib["series"] or ia["period"] != ib["period"]):
        return True
    if family(ta, ia) == "FOMC" and ia.get("board_date") and ib.get("board_date") and ia["board_date"] != ib["board_date"]:
        return True
    return False


# -------------------------------------------------------------------- validation (A4)
def validate(claim: ClaimRecord, curation: CurationRecord) -> None:
    if curation.curated_at < claim.claim_received_at:
        raise CurationInvalid("CURATED_BEFORE_CLAIM_RECEIPT")
    spans = sorted(curation.spans, key=lambda s: (s.start, s.end))
    position = 0
    for s in spans:
        if s.start != position or s.end <= s.start:
            raise CurationInvalid("SPANS_DO_NOT_PARTITION_TEXT")
        position = s.end
    if position != len(claim.text):
        raise CurationInvalid("SPANS_DO_NOT_PARTITION_TEXT")
    props = {}
    for p in curation.propositions:
        if p.proposition_id in props and props[p.proposition_id] != p:
            raise CurationInvalid("DUPLICATE_PROPOSITION_ID")
        props[p.proposition_id] = p
    events = {}
    for e in curation.events:
        if e.event_id in events and events[e.event_id] != e:
            raise CurationInvalid("DUPLICATE_EVENT_ID")
        events[e.event_id] = e
    referenced = set()
    for s in spans:
        if s.category is SpanCategory.PROPOSITION:
            if not s.proposition_ids:
                raise CurationInvalid("PROPOSITION_SPAN_WITHOUT_PROPOSITIONS")
            if any(pid not in props for pid in s.proposition_ids):
                raise CurationInvalid("SPAN_REFERENCES_UNKNOWN_PROPOSITION")
            referenced |= set(s.proposition_ids)
        elif s.proposition_ids:
            raise CurationInvalid("NON_PROPOSITION_SPAN_WITH_PROPOSITIONS")
    if set(props) - referenced:
        raise CurationInvalid("PROPOSITION_NOT_IN_ANY_SPAN")
    if any(p.event_id not in events for p in props.values()):
        raise CurationInvalid("PROPOSITION_REFERENCES_UNKNOWN_EVENT")
    if set(events) - {p.event_id for p in props.values()}:
        raise CurationInvalid("EVENT_WITHOUT_PROPOSITION")
    for a, b in curation.distinct:
        if a == b or a not in events or b not in events:
            raise CurationInvalid("DISTINCT_REFERENCES_UNKNOWN_EVENT")
    for p in props.values():
        ft = events[p.event_id].frame_type
        if ft is FrameType.RESIDUAL:
            raise CurationInvalid("RESIDUAL_IS_NOT_CURATED")
        if any(f.field not in ALLOWED_FACTS[ft] for f in p.facts):
            raise CurationInvalid(f"FACT_NOT_ALLOWED_FOR:{ft.value}")


def admission(curation: CurationRecord) -> str | None:
    """A5: numeric ETF market data with only non-assertive spans around it is not news."""
    cats = {s.category for s in curation.spans}
    if SpanCategory.NUMERIC_ETF_MARKET_DATA in cats and cats <= NON_ASSERTIVE_SPANS | {SpanCategory.NUMERIC_ETF_MARKET_DATA}:
        return "NUMERIC_ETF_MARKET_DATA_NOT_NEWS"
    return None


# -------------------------------------------------------------------- normalization
def _roles(frame_type: FrameType, facts: list[tuple]) -> list[tuple]:
    """Assign PREDICATE / QUALIFIER from the frame type and the frame's facts (§4.1)."""
    fields = {f for f, *_ in facts}
    out = []
    for f, value, token in facts:
        if frame_type is FrameType.REG_DOC:
            qualifier = F.ACTION.value in fields and f in (F.DATE.value, F.VENUE.value, F.ACCELERATED.value)
        elif frame_type is FrameType.REG_EVENT:
            qualifier = f in (F.DATE.value, F.VENUE.value, F.ACCELERATED.value)
        elif frame_type is FrameType.REG_CURRENT_STATUS:
            qualifier = f == F.SINCE.value
        elif frame_type is FrameType.LATEST_IDENTITY:
            qualifier = f in (F.ACTION.value, F.DATE.value)
        elif frame_type is FrameType.NON_SOURCE_EVENT:
            qualifier = f == F.DATE.value
        elif frame_type is FrameType.MACRO_VALUE:
            qualifier = f == F.PRELIMINARY.value
        elif frame_type is FrameType.FOMC_DECISION:
            qualifier = f in (F.TARGET_RANGE.value, F.CHANGE_SIZE.value)
        elif frame_type is FrameType.FOMC_SCHEDULE:
            qualifier = f in (F.ANNOUNCEMENT_TIME.value, F.PROJECTIONS.value)
        else:
            qualifier = False
        out.append((f, value, token, FactRole.QUALIFIER if qualifier else FactRole.PREDICATE))
    return out


def _synthesized(frame_type: FrameType, ident: dict) -> tuple | None:
    """Predicates fixed by the event's identity (the claim asserts the event itself)."""
    if frame_type is FrameType.REG_EVENT:
        return (F.ACTION.value, ident["action"], None)
    if frame_type is FrameType.LATEST_IDENTITY:
        return (F.MEMBER_IS_LATEST.value, "true", None)
    if frame_type is FrameType.NON_SOURCE_EVENT:
        return (F.EVENT.value, ident["event_type"], None)
    if frame_type is FrameType.FOMC_SCHEDULE:
        return (F.SCHEDULED_ON.value, f"{ident['meeting_start']}/{ident['meeting_end']}", None)
    return None


def frame_key(frame_type: FrameType, ident: dict) -> str:
    g = ident.get
    if frame_type is FrameType.REG_DOC:
        return f"DOC:{g('document_number')}"
    if frame_type is FrameType.REG_EVENT:
        return f"EVT:{','.join(g('subjects'))}:{g('action')}"
    if frame_type is FrameType.REG_STATUS_AT:
        return f"STA:{g('subjects')[0]}:{g('status_date')}"
    if frame_type is FrameType.REG_CURRENT_STATUS:
        return f"CUR:{g('subjects')[0]}"
    if frame_type is FrameType.LATEST_IDENTITY:
        seq = g("sequence") + (f":{g('sequence_file')}" if g("sequence_file") else "")
        member = g("member_document_number") or (f"{g('member_pattern')}@{g('member_date')}" if g("member_pattern")
                                                  else g("board_date") or "UNIDENTIFIED")
        return f"LAT:{seq}:{member}"
    if frame_type is FrameType.NON_SOURCE_EVENT:
        return f"NSE:{g('event_type')}:{','.join(g('subjects') or ('UNSPECIFIED',))}"
    if frame_type is FrameType.MACRO_VALUE:
        return f"BLS:{g('series')}:{g('period')}:{g('scope')}"
    if frame_type is FrameType.MACRO_CHANGE:
        return f"BLSCHG:{g('series')}:{g('period')}:{g('change_kind')}"
    if frame_type is FrameType.MACRO_CONSENSUS:
        return f"BLSCONS:{g('series')}:{g('period')}"
    if frame_type is FrameType.FOMC_DECISION:
        return f"FOMC:{g('board_date')}"
    if frame_type is FrameType.FOMC_CURRENT_RANGE:
        return "FOMCCUR"
    return f"FOMCSCH:{g('meeting_start')}:{g('meeting_end')}"


FundResolver = Callable[[str], tuple[str | None, str | None]]


def _resolve(ft: FrameType, ident: dict, resolve_fund: FundResolver) -> tuple[dict, str | None]:
    """Step 2: resolve identities at T. A fund subject resolves only through a link valid at T."""
    resolved, problem = dict(ident), None
    if ft not in REGULATORY_FRAMES or not ident.get("subjects"):
        return resolved, None
    subjects = []
    for s in ident["subjects"]:
        if s == "BTC":
            problem = problem or "AMBIGUOUS_SUBJECT"
            subjects.append(s)
        elif s.startswith("FUND:"):
            file_number, why = resolve_fund(s[5:])
            problem = problem or (why if file_number is None else None)
            subjects.append(file_number or s)
        else:
            subjects.append(s)
    resolved["subjects"] = tuple(sorted(set(subjects)))
    if ft is FrameType.REG_EVENT:
        if ident["action"] == RegAction.RULE_CHANGE_APPROVED.value:
            resolved["action"] = RegAction.APPROVED.value
        elif ident["action"] == RegAction.APPROVED.value and any(s.startswith("FUND:") for s in ident["subjects"]):
            resolved["action"] = AMBIGUOUS_APPROVAL      # rule-change approval or registration effectiveness
    return resolved, problem


AMBIGUOUS_APPROVAL = "APPROVED|REGISTRATION_EFFECTIVE"


def _norm_facts(ft: FrameType, roled: list[tuple], resolved: dict) -> tuple[NormFact, ...]:
    fund_subject = any(v.startswith("FUND:") for f, v, *_ in roled if f == F.SUBJECT.value)
    out = set()
    for f, value, token, role in roled:
        alternatives = ()
        if f == F.DATE.value:
            alternatives = tuple(r.value for r in DATE_ROLES[DateToken(token)])
        elif f == F.ACTION.value and ft is FrameType.REG_EVENT:
            value = resolved["action"]
        elif f == F.ACTION.value and ft in REGULATORY_FRAMES | {FrameType.LATEST_IDENTITY}:
            if value == RegAction.RULE_CHANGE_APPROVED.value:
                value = RegAction.APPROVED.value
            elif value == RegAction.APPROVED.value and fund_subject:
                value = AMBIGUOUS_APPROVAL
        if f == F.ACTION.value and "|" in value:
            alternatives = tuple(value.split("|"))
        out.add(NormFact(field=f, value=value, token=token, role=role, alternatives=alternatives))
    return tuple(sorted(out, key=NormFact.key))


def normalize(claim: ClaimRecord, curation: CurationRecord, resolve_fund: FundResolver) -> Normalized:
    """Validated curation -> canonical events (§4.3 steps 1-9). Raises CurationInvalid for A4 failures."""
    validate(claim, curation)
    events = {e.event_id: e for e in curation.events}
    props = {p.proposition_id: p for p in curation.propositions}
    built: dict[str, tuple] = {}                 # step 1: canonical identity and facts per event
    for eid, e in sorted(events.items()):
        ident = canonical_identity(e.frame_type, e.identity)
        facts = {(f.field.value, *canonical_value(e.frame_type, f)) for p in props.values() if p.event_id == eid
                 for f in p.facts}
        built[eid] = (e.frame_type, ident, facts)
    # step 4: one event per REG_EVENT subject, mutually distinct. Internal keys are structured
    # (curator event id, expanded subject or ""), so no derived key can equal another event's key,
    # whatever ids the curator chose; a canonical subject is never empty.
    expanded: dict[tuple[str, str], tuple] = {}
    declared: set[frozenset] = set()
    for eid, (ft, ident, facts) in built.items():
        if ft is FrameType.REG_EVENT and len(ident["subjects"]) > 1:
            derived = [(eid, s) for s in ident["subjects"]]
            for d in derived:
                expanded[d] = (ft, {**ident, "subjects": (d[1],)}, facts)
            declared |= {frozenset((a, b)) for a in derived for b in derived if a != b}
        else:
            expanded[(eid, "")] = (ft, ident, facts)
    for a, b in curation.distinct:
        declared |= {frozenset((x, y)) for x in expanded if x[0] == a for y in expanded if y[0] == b}

    staged = {}                                  # steps 2, 3, 6, 7
    for eid, (ft, ident, facts) in expanded.items():
        problem, own = None, set(facts)
        synth = _synthesized(ft, ident)
        if synth is not None:
            for x in [x for x in own if x[0] == synth[0]]:
                problem = problem if x[1] == synth[1] else "SELF_CONTRADICTORY_IDENTITY"
                own.discard(x)
            own.add(synth)
        if ft is FrameType.REG_EVENT:
            for x in [x for x in own if x[0] == F.SUBJECT.value]:
                problem = problem if x[1] in ident["subjects"] else "SELF_CONTRADICTORY_IDENTITY"
                own.discard(x)
        roled = _roles(ft, sorted(own, key=lambda x: (x[0], x[1], x[2] or "")))
        if not any(r is FactRole.PREDICATE for *_, r in roled):
            raise CurationInvalid("NO_PREDICATE")
        resolved, unresolved = _resolve(ft, ident, resolve_fund)
        staged[eid] = (ft, ident, resolved, _norm_facts(ft, roled, resolved), problem or unresolved)

    # step 8: canonical ids from canonical (resolved) content; identical content is one event
    content = {eid: canonical_json([ft.value, resolved, [list(f.key()) for f in facts], problem])
               for eid, (ft, _, resolved, facts, problem) in staged.items()}
    order = sorted(set(content.values()))
    cid = {eid: f"E{order.index(c) + 1}" for eid, c in content.items()}

    pairs = set()                                # step 5: association check on asserted identity only
    ids = sorted(expanded)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if cid[a] == cid[b] or frozenset((a, b)) in declared:
                continue
            if not incompatible((staged[a][0], staged[a][1]), (staged[b][0], staged[b][1])):
                pairs.add(tuple(sorted((cid[a], cid[b]), key=lambda c: int(c[1:]))))
    association = ("EVENT_ASSOCIATION_UNDETERMINED:" + ";".join(f"{x},{y}" for x, y in sorted(pairs))) if pairs else None

    norm = {}
    for eid, (ft, ident, resolved, facts, problem) in staged.items():
        norm[cid[eid]] = NormEvent(cid=cid[eid], frame_type=ft, identity=tuple(sorted(ident.items())),
                                   resolved=tuple(sorted(resolved.items())), facts=facts, key=frame_key(ft, resolved),
                                   problem=problem)
    events_out = tuple(norm[k] for k in sorted(norm, key=lambda c: int(c[1:])))
    residuals = tuple(sorted({(f"RES:{s.start}:{s.end}", s.category) for s in curation.spans if s.category in RESIDUAL_SPANS}))
    # only declarations that matter: a pair already provably incompatible needs none (so equivalent curations agree)
    distinct = tuple(sorted({tuple(sorted((cid[a], cid[b]), key=lambda c: int(c[1:]))) for a, b in map(tuple, declared)
                             if cid[a] != cid[b] and not incompatible((staged[a][0], staged[a][1]), (staged[b][0], staged[b][1]))}))
    form = canonical_json([[e.cid, e.frame_type.value, list(e.resolved), [list(f.key()) for f in e.facts], e.problem]
                           for e in events_out] + [[k, c.value] for k, c in residuals] + [list(d) for d in distinct]
                          + [association])
    return Normalized(events=events_out, residuals=residuals, distinct=distinct, association_problem=association, form=form)


def series_alternatives(series: str) -> tuple[str, ...]:
    """CPI with no SA/NSA stated is the admissible set of both CPI series (G4)."""
    return CPI_SERIES if series == "CPI" else (series,)
