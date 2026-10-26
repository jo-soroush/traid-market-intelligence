"""Deterministic six-state primary-source verification at one explicit evaluation time T (design §4-§9).

Pure: no clock, network or ambient state. Inputs whose availability is after T are counted and
never otherwise read (I1); the result is the same function of the filtered inputs at every call
(I2) and adding a later input changes only the exclusion counts (I3). Claim text is untrusted and
never interpreted; only the human curation's typed facts are evaluated. Absence of a document is
never evidence (G1); contradiction requires a uniquely identified source (G2). Current and dated
status is never concluded. No output carries direction, impact, score or trade authority.

Macro frames are evaluated by an injected ``MacroEvaluator`` (``traid.news.macro_adapter``); this
module imports only C02 contracts and C13 modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from traid.news.curation import RESIDUAL_REASON, CurationInvalid, NormEvent, NormFact, admission, normalize
from traid.news.models import (
    MACRO_FRAMES, REGULATORY_FRAMES, STATIC_LIMITATIONS, AdmissionRejection, CitationRole, ClaimRecord, CurationRecord, EvidenceCitation,
    ExcludedCounts, FactField, FactOutcome, FactResult, FactRole, FrameResult, FrameType, OfficialEvidence, PassageKind,
    FundResolution, QualifiedDocument, RegAction, Sequence, SpanCategory, VerificationPolicy, VerificationReport, VerificationResult,
    VerificationState, DEFAULT_POLICY, canonical_json, sha256_hex, utc,
)
from traid.news.patterns import ACTION_FAMILY, BY_ID
from traid.news.qualification import LinkCheck, check_fund_link, qualify_document
from traid.news.text import canonical_file_number, compare_labels, normalize_passage, parse_date_value, precedes, window

MAX_INPUTS = 10000
S, O = VerificationState, FactOutcome
FIELD_PASSAGE = {"ACTION": PassageKind.OPERATIVE, "ACCELERATED": PassageKind.OPERATIVE, "SUBJECT": PassageKind.HEADING,
                 "FILE_NUMBER": PassageKind.HEADING, "RELEASE_NO": PassageKind.HEADING, "VENUE": PassageKind.HEADING,
                 "ORDER_DATE": PassageKind.DATE_LINE, "FR_PUBLICATION_DATE": PassageKind.PAGE_HEADER,
                 "PUBLIC_INSPECTION": PassageKind.TERMINATOR}


# ------------------------------------------------------------------- macro boundary
@dataclass(frozen=True)
class MacroContext:
    evaluation_time: datetime
    reference_time: datetime
    reference_is_upper_bound: bool


@dataclass(frozen=True)
class FrameOutcome:
    facts: tuple[FactResult, ...]
    identity_resolved: bool = True
    reasons: tuple[str, ...] = ()


class MacroEvaluator:
    """Evaluates MACRO_*/FOMC_* frames and FOMC_STATEMENTS LATEST_IDENTITY frames from read-only evidence."""
    input_digest: str = ""

    def evaluate(self, event: NormEvent, context: MacroContext) -> FrameOutcome:   # pragma: no cover - interface
        raise NotImplementedError


def unresolved_frame(event: NormEvent, reason: str, identity_resolved: bool = True) -> FrameOutcome:
    return FrameOutcome(facts=tuple(FactResult(field=fact_label(f), role=f.role, asserted=f.value, outcome=O.UNRESOLVED,
                                               reasons=(reason,)) for f in event.facts),
                        identity_resolved=identity_resolved)


def fact_label(f: NormFact) -> str:
    return f"{f.field}:{f.token}" if f.token else f.field


# ------------------------------------------------------------------- outcome helpers
@dataclass(frozen=True)
class Outcome:
    outcome: FactOutcome
    reasons: tuple[str, ...] = ()
    citations: tuple[EvidenceCitation, ...] = ()


def unresolved(*reasons: str) -> Outcome:
    return Outcome(O.UNRESOLVED, tuple(reasons))


def combine(alternatives: list[Outcome], label: str) -> Outcome:
    """G4: every interpretation SUPPORTED -> SUPPORTED; every CONTRADICTED -> CONTRADICTED; else unresolved."""
    if len(alternatives) == 1:
        return alternatives[0]
    kinds = {a.outcome for a in alternatives}
    cites = tuple(c for a in alternatives for c in a.citations)
    if kinds == {O.SUPPORTED} or kinds == {O.CONTRADICTED}:
        return Outcome(kinds.pop(), tuple(sorted({r for a in alternatives for r in a.reasons})), cites)
    return Outcome(O.UNRESOLVED, tuple(sorted({f"AMBIGUOUS_{label}"} | {r for a in alternatives for r in a.reasons})))


def to_fact(f: NormFact, outcome: Outcome) -> FactResult:
    cites = tuple(sorted(set(outcome.citations), key=lambda c: canonical_json(c.model_dump(mode="python"))))
    return FactResult(field=fact_label(f), role=f.role, asserted=f.value, outcome=outcome.outcome,
                      reasons=tuple(sorted(set(outcome.reasons))), citations=cites)


def _passage(doc: QualifiedDocument, kind: PassageKind):
    return next(p for p in doc.passages if p.kind is kind)


def doc_dates(doc: QualifiedDocument) -> dict[str, date]:
    dates = {"FR_PUBLICATION_DATE": doc.fr_publication_date}
    if doc.order_or_notice_date is not None:
        dates["ORDER_DATE"] = doc.order_or_notice_date
    if doc.public_inspection_local_date is not None:
        dates["PUBLIC_INSPECTION"] = doc.public_inspection_local_date
    return dates


def cite(doc: QualifiedDocument, role: CitationRole, field_name: str, subject: str) -> EvidenceCitation:
    pattern = BY_ID[doc.pattern_id]
    return EvidenceCitation(role=role, document_number=doc.document_number, pattern_id=doc.pattern_id,
                            passage=_passage(doc, FIELD_PASSAGE.get(field_name, PassageKind.OPERATIVE)), subject=subject,
                            action=pattern.action.value, dates=tuple(sorted(doc_dates(doc).items())),
                            components=doc.components)


# ------------------------------------------------------------------- evaluation context
@dataclass
class Context:
    T: datetime
    docs: dict[str, QualifiedDocument]
    disqualified: dict[str, str]
    links: list[LinkCheck]
    reference_time: datetime
    reference_is_upper_bound: bool
    macro: MacroEvaluator | None
    used_docs: set = field(default_factory=set)
    reasons: set = field(default_factory=set)

    def _matches(self, name: str) -> list[LinkCheck]:
        wanted = normalize_passage(name)
        return [c for c in self.links if c.link.ticker == name or normalize_passage(c.link.name_in_document) == wanted]

    def resolve_fund(self, name: str) -> tuple[str | None, str | None]:
        """A fund subject resolves only through a link valid at T: exact ticker or exact verbatim name."""
        matches = self._matches(name)
        valid = {c.link.file_number for c in matches if c.valid and c.available_at <= self.T}
        if len(valid) == 1:
            return valid.pop(), None
        if len(valid) > 1:
            return None, "FUND_LINK_AMBIGUOUS"
        invalid = sorted(c.reason for c in matches if not c.valid)
        return None, invalid[0] if invalid else "FUND_LINK_NOT_AVAILABLE_AT_T"

    def fund_resolutions(self, file_numbers: set[str]) -> tuple[FundResolution, ...]:
        """Every link valid at T to one of these file numbers, sorted and deduplicated. Keyed by the
        resolved file number only, so a fund spelled by ticker, by name or as its file number (and
        whichever equivalent event survives deduplication) carries the same evidence."""
        out = {}
        for c in self.links:
            if c.valid and c.available_at <= self.T and c.link.file_number in file_numbers:
                l, doc = c.link, self.docs[c.link.document_number]
                r = FundResolution(link_id=l.link_id, name_in_document=l.name_in_document, ticker=l.ticker, cik=l.cik,
                                   sro=l.sro, file_number=l.file_number, document_number=l.document_number,
                                   qualifying_record_id=doc.qualifying_record_id, name_passage=c.name_passage,
                                   identity_evidence=l.identity_evidence, link_curated_at=l.curated_at,
                                   available_at=c.available_at)
                out[canonical_json(r.model_dump(mode="python"))] = r
        return tuple(out[k] for k in sorted(out, key=lambda k: (out[k].link_id, k)))


# ------------------------------------------------------------------- ETF fact rules (§5.5)
def _future(f: NormFact, T: datetime) -> bool:
    d = parse_date_value(f.value)
    if d is None:
        return False
    start = d if isinstance(d, datetime) else window(d)[0]
    return start > T


def date_outcome(f: NormFact, doc: QualifiedDocument, subject: str, T: datetime) -> Outcome:
    if _future(f, T):
        return unresolved("FUTURE_EVENT")
    asserted = parse_date_value(f.value)
    provided = doc_dates(doc)
    roles = [r for r in f.alternatives if r in provided] if f.token == "AMBIGUOUS" else list(f.alternatives)
    if not roles:
        return unresolved("DATE_ROLE_NOT_PROVIDED_BY_DOCUMENT")
    results = []
    for role in roles:
        if role not in provided:
            results.append(unresolved("DATE_ROLE_NOT_PROVIDED_BY_DOCUMENT"))
            continue
        if isinstance(asserted, datetime):
            if role == "PUBLIC_INSPECTION" and doc.public_inspection_filed_at == asserted:
                results.append(Outcome(O.SUPPORTED, (), (cite(doc, CitationRole.SUPPORTS, role, subject),)))
            else:
                results.append(unresolved("TIME_OF_DAY_NOT_IN_EVIDENCE"))
            continue
        verdict = compare_labels(asserted, provided[role])
        if verdict == "SUPPORTED":
            results.append(Outcome(O.SUPPORTED, (), (cite(doc, CitationRole.SUPPORTS, role, subject),)))
        elif verdict == "CONTRADICTED":
            results.append(Outcome(O.CONTRADICTED, (), (cite(doc, CitationRole.CONTRADICTS, role, subject),)))
        else:
            results.append(unresolved(verdict))
    return combine(results, "DATE_ROLE")


def action_outcome(asserted: str, doc: QualifiedDocument, subject: str) -> Outcome:
    if asserted == RegAction.REGISTRATION_EFFECTIVE.value:
        return unresolved("NO_APPROVED_SOURCE_FOR_EVENT_TYPE")
    pattern = BY_ID[doc.pattern_id]
    if ACTION_FAMILY.get(RegAction(asserted)) != pattern.family:
        return unresolved("AMBIGUOUS_ACTION")         # never matched across status families
    role = CitationRole.SUPPORTS if pattern.action.value == asserted else CitationRole.CONTRADICTS
    return Outcome(O.SUPPORTED if role is CitationRole.SUPPORTS else O.CONTRADICTED, (), (cite(doc, role, "ACTION", subject),))


def doc_fact(f: NormFact, doc: QualifiedDocument, ctx: Context, subject: str) -> Outcome:
    if f.field == FactField.DATE.value:
        return date_outcome(f, doc, subject, ctx.T)
    if f.field == FactField.ACTION.value:
        return combine([action_outcome(a, doc, subject) for a in (f.alternatives or (f.value,))], "ACTION")
    if f.field in (FactField.SUBJECT.value, FactField.FILE_NUMBER.value):
        value = f.value
        if value == "BTC":
            return unresolved("AMBIGUOUS_SUBJECT")
        if value.startswith("FUND:"):
            value, why = ctx.resolve_fund(value[5:])
            if value is None:
                return unresolved(why)
        role = CitationRole.SUPPORTS if value in doc.file_numbers else CitationRole.CONTRADICTS
        return Outcome(O.SUPPORTED if role is CitationRole.SUPPORTS else O.CONTRADICTED, (), (cite(doc, role, f.field, subject),))
    if f.field == FactField.RELEASE_NO.value:
        role = CitationRole.SUPPORTS if f.value == doc.release_no else CitationRole.CONTRADICTS
        return Outcome(O.SUPPORTED if role is CitationRole.SUPPORTS else O.CONTRADICTED, (), (cite(doc, role, "RELEASE_NO", subject),))
    if f.field == FactField.VENUE.value:
        venues = {n.split("-")[1] for n in doc.file_numbers}
        role = CitationRole.SUPPORTS if f.value in venues else CitationRole.CONTRADICTS
        return Outcome(O.SUPPORTED if role is CitationRole.SUPPORTS else O.CONTRADICTED, (), (cite(doc, role, "VENUE", subject),))
    if f.field == FactField.ACCELERATED.value:
        if doc.pattern_id.value != "APPROVAL":
            return unresolved("ACCELERATED_NOT_APPLICABLE_TO_PATTERN")
        role = CitationRole.SUPPORTS if (f.value == "true") == doc.accelerated else CitationRole.CONTRADICTS
        return Outcome(O.SUPPORTED if role is CitationRole.SUPPORTS else O.CONTRADICTED, (), (cite(doc, role, "ACCELERATED", subject),))
    return unresolved("FIELD_NOT_EVALUATED_FOR_FRAME")


def eval_reg_doc(event: NormEvent, ctx: Context) -> FrameOutcome:
    N = event.ident["document_number"]
    doc = ctx.docs.get(N)
    if doc is None:
        why = ctx.disqualified.get(N, "METADATA_NOT_AVAILABLE_AT_T")
        return unresolved_frame(event, f"DOCUMENT_NOT_QUALIFIED:{why}", identity_resolved=N in ctx.disqualified)
    ctx.used_docs.add(N)
    return FrameOutcome(facts=tuple(to_fact(f, doc_fact(f, doc, ctx, N)) for f in event.facts))


def establishing(ctx: Context, subject: str, action: str) -> list[QualifiedDocument]:
    """Qualified documents that establish (subject, action) under §9.1."""
    return sorted((d for d in ctx.docs.values() if subject in d.file_numbers and BY_ID[d.pattern_id].action.value == action),
                  key=lambda d: d.document_number)


def eval_reg_event(event: NormEvent, ctx: Context) -> FrameOutcome:
    subject = event.ident["subjects"][0]
    if any(f.field == FactField.DATE.value and _future(f, ctx.T) for f in event.facts):
        return unresolved_frame(event, "FUTURE_EVENT")
    action_fact = next(f for f in event.facts if f.field == FactField.ACTION.value)
    actions = action_fact.alternatives or (action_fact.value,)
    facts = []
    for f in event.facts:
        if f.role is FactRole.PREDICATE:
            outcomes = []
            for a in actions:
                if a == RegAction.REGISTRATION_EFFECTIVE.value:
                    outcomes.append(unresolved("NO_APPROVED_SOURCE_FOR_EVENT_TYPE"))
                    continue
                docs = establishing(ctx, subject, a)
                ctx.used_docs |= {d.document_number for d in docs}
                outcomes.append(Outcome(O.SUPPORTED, (), tuple(cite(d, CitationRole.SUPPORTS, "ACTION", subject) for d in docs))
                                if docs else unresolved("NO_QUALIFYING_EVIDENCE"))
            facts.append(to_fact(f, combine(outcomes, "ACTION")))
            continue
        if len(actions) != 1:
            facts.append(to_fact(f, unresolved("QUALIFIER_EVENT_NOT_UNIQUELY_IDENTIFIED")))
            continue
        matching = []
        for d in establishing(ctx, subject, actions[0]):
            o = doc_fact(f, d, ctx, subject)
            if o.outcome is O.SUPPORTED:
                matching.extend(o.citations)
        facts.append(to_fact(f, Outcome(O.SUPPORTED, (), tuple(matching)) if matching
                             else unresolved("QUALIFIER_EVENT_NOT_UNIQUELY_IDENTIFIED")))
    return FrameOutcome(facts=tuple(facts))


def status_citations(ctx: Context, subject: str) -> tuple[EvidenceCitation, ...]:
    docs = [d for d in ctx.docs.values() if subject in d.file_numbers and BY_ID[d.pattern_id].status is not None]
    ctx.used_docs |= {d.document_number for d in docs}
    return tuple(cite(d, CitationRole.ESTABLISHES_EARLIER_STATUS, "ACTION", subject) for d in docs)


def eval_status(event: NormEvent, ctx: Context) -> FrameOutcome:
    """Current and dated status is never concluded (R4): historical transitions are cited only."""
    subject = event.ident["subjects"][0]
    cites = status_citations(ctx, subject)
    reasons = ("STATUS_COVERAGE_INCOMPLETE",) + (("HISTORICAL_TRANSITIONS_CITED_CURRENT_STATUS_NOT_CONCLUDED",) if cites else ())
    return FrameOutcome(facts=tuple(FactResult(field=fact_label(f), role=f.role, asserted=f.value, outcome=O.UNRESOLVED,
                                               reasons=reasons, citations=cites) for f in event.facts))


def reference_code(later: QualifiedDocument, ctx: Context) -> str:
    start, end = window(later.order_or_notice_date)
    if start >= ctx.reference_time:
        return "LATER_MEMBER_AFTER_REFERENCE_TIME"
    if end <= ctx.reference_time:
        return "LATER_MEMBER_BEFORE_REFERENCE_TIME"
    return "LATER_MEMBER_ORDER_RELATIVE_TO_REFERENCE_UNRESOLVED"


def eval_latest_sec(event: NormEvent, ctx: Context) -> FrameOutcome:
    ident = event.ident
    file_number = ident["sequence_file"]
    members = sorted((d for d in ctx.docs.values() if file_number in d.file_numbers and BY_ID[d.pattern_id].sequence_member),
                     key=lambda d: (d.order_or_notice_date, d.document_number))
    if ident.get("member_document_number"):
        candidates = [d for d in members if d.document_number == ident["member_document_number"]]
    elif ident.get("member_pattern"):
        candidates = [d for d in members if d.pattern_id.value == ident["member_pattern"]
                      and d.order_or_notice_date == date.fromisoformat(ident["member_date"])]
    else:
        return unresolved_frame(event, "MEMBER_NOT_IDENTIFIED")
    if not candidates:
        return unresolved_frame(event, "MEMBER_NOT_IN_EVIDENCE")
    if len(candidates) > 1:
        return unresolved_frame(event, "SAME_DATE_ORDER_UNRESOLVED")
    m = candidates[0]
    ctx.used_docs.add(m.document_number)
    later = [d for d in members if precedes(m.order_or_notice_date, d.order_or_notice_date)]
    overlapping = [d for d in members if d is not m and not precedes(d.order_or_notice_date, m.order_or_notice_date)
                   and d not in later]
    facts = []
    for f in event.facts:
        if f.role is FactRole.QUALIFIER:
            facts.append(to_fact(f, doc_fact(f, m, ctx, file_number)))
        elif later:
            ctx.used_docs |= {d.document_number for d in later}
            first = min(later, key=lambda d: (d.order_or_notice_date, d.document_number))
            reasons = tuple(f"LATER_SEQUENCE_MEMBER_KNOWN:{d.document_number}" for d in later) + (reference_code(first, ctx),) \
                + (("REFERENCE_TIME_UPPER_BOUND_ONLY",) if ctx.reference_is_upper_bound else ())
            cites = tuple(cite(d, CitationRole.SUPERSEDES, "ACTION", file_number) for d in later) \
                + (cite(m, CitationRole.ESTABLISHES_EARLIER_STATUS, "ACTION", file_number),)
            facts.append(to_fact(f, Outcome(O.SUPERSEDED, reasons, cites)))
        else:
            facts.append(to_fact(f, unresolved("SAME_DATE_ORDER_UNRESOLVED" if overlapping else "LATEST_NOT_PROVABLE")))
    return FrameOutcome(facts=tuple(facts))


def eval_event(event: NormEvent, ctx: Context) -> FrameOutcome:
    if event.problem:
        return unresolved_frame(event, event.problem, identity_resolved=False)
    ft = event.frame_type
    if ft in MACRO_FRAMES or (ft is FrameType.LATEST_IDENTITY and event.ident["sequence"] == Sequence.FOMC_STATEMENTS.value):
        if ctx.macro is None:
            return unresolved_frame(event, "MACRO_EVIDENCE_NOT_CONFIGURED")
        return ctx.macro.evaluate(event, MacroContext(ctx.T, ctx.reference_time, ctx.reference_is_upper_bound))
    if ft is FrameType.REG_DOC:
        return eval_reg_doc(event, ctx)
    if ft is FrameType.REG_EVENT:
        return eval_reg_event(event, ctx)
    if ft in (FrameType.REG_STATUS_AT, FrameType.REG_CURRENT_STATUS):
        return eval_status(event, ctx)
    if ft is FrameType.LATEST_IDENTITY:
        return eval_latest_sec(event, ctx)
    return unresolved_frame(event, "NO_APPROVED_SOURCE_FOR_EVENT_TYPE")     # NON_SOURCE_EVENT (G6)


# ------------------------------------------------------------------- state tables
def frame_state(frame_type: FrameType, outcome: FrameOutcome) -> VerificationState:
    """§5.3, first matching row wins (F1-F8)."""
    if not outcome.identity_resolved or frame_type is FrameType.RESIDUAL:
        return S.UNVERIFIED
    preds = [f.outcome for f in outcome.facts if f.role is FactRole.PREDICATE]
    quals = [f.outcome for f in outcome.facts if f.role is FactRole.QUALIFIER]
    if not preds:
        return S.UNVERIFIED
    if O.CONTRADICTED in preds:
        return S.FALSE
    if O.SUPERSEDED in preds:
        return S.OUTDATED
    if O.UNRESOLVED in preds:
        return S.UNVERIFIED
    if O.CONTRADICTED in quals:
        return S.MISLEADING
    if O.UNRESOLVED in quals:
        return S.PARTIALLY_CONFIRMED
    return S.CONFIRMED


def claim_state(states: set[VerificationState]) -> VerificationState:
    """§5.4 on the set of frame states (C1-C6): order and duplication cannot matter."""
    if S.FALSE in states:
        return S.FALSE
    if S.MISLEADING in states:
        return S.MISLEADING
    if S.OUTDATED in states:
        return S.OUTDATED
    if states == {S.CONFIRMED}:
        return S.CONFIRMED
    if states & {S.CONFIRMED, S.PARTIALLY_CONFIRMED}:
        return S.PARTIALLY_CONFIRMED
    return S.UNVERIFIED


# ------------------------------------------------------------------- the engine
def _bounded(items, name: str) -> tuple:
    if not isinstance(items, tuple) or len(items) > MAX_INPUTS:
        raise ValueError(f"{name}: a bounded tuple is required")
    return items


def _dedupe(items) -> list:
    seen = {}
    for item in items:
        seen.setdefault(canonical_json(item.model_dump(mode="python")), item)
    return [seen[k] for k in sorted(seen)]


def _filter(items, when, T):
    """I1: the inputs available at T, and how many DISTINCT inputs are not. Excluded inputs are counted
    under the same canonical equality that deduplicates admitted ones (P4: an exact duplicate never
    changes the report; genuinely distinct excluded inputs still count separately)."""
    known = [x for x in items if when(x) <= T]
    later = [x for x in items if not when(x) <= T]
    return _dedupe(known), len(_dedupe(later))


def verify(*, claims: tuple[ClaimRecord, ...], curations: tuple[CurationRecord, ...], evidence: OfficialEvidence,
           evaluation_time: datetime, policy: VerificationPolicy = DEFAULT_POLICY,
           macro: MacroEvaluator | None = None) -> VerificationReport:
    T = utc(evaluation_time, "evaluation_time")
    for name, items in (("claims", claims), ("curations", curations)):
        _bounded(items, name)
    if type(evidence) is not OfficialEvidence or type(policy) is not VerificationPolicy:
        raise ValueError("canonical OfficialEvidence and VerificationPolicy required")
    for name in OfficialEvidence.model_fields:
        if name != "schema_version":
            _bounded(getattr(evidence, name), name)

    # I1: filter first; later inputs are only counted
    known_claims, n_claims = _filter(claims, lambda c: c.claim_received_at, T)
    known_curations, n_curations = _filter(curations, lambda c: c.curated_at, T)
    links, n_links = _filter(evidence.fund_links, lambda l: max(l.curated_at, l.identity_evidence.received_timestamp), T)
    metadata, n_meta = _filter(evidence.fr_metadata, lambda x: x.retrieved_at, T)
    pis, n_pi = _filter(evidence.public_inspection, lambda x: x.retrieved_at, T)
    listings, n_listings = _filter(evidence.docket_listings, lambda x: x.retrieved_at, T)
    html, n_html = _filter(evidence.html, lambda x: x.retrieved_at, T)
    pdf, n_pdf = _filter(evidence.pdf, lambda x: x.retrieved_at, T)
    mods, n_mods = _filter(evidence.mods, lambda x: x.retrieved_at, T)
    records, n_records = _filter(evidence.manual_records, lambda x: x.available_at, T)
    excluded = ExcludedCounts(claims=n_claims, curations=n_curations, fund_links=n_links, fr_metadata=n_meta,
                              public_inspection=n_pi, docket_listings=n_listings, html=n_html, pdf=n_pdf, mods=n_mods,
                              manual_records=n_records)

    # level 1: qualified documents, recomputed at T
    numbers = sorted({x.document_number for group in (metadata, html, pdf, mods, records) for x in group})
    docs, disqualified, doc_limits = {}, {}, {}
    for n in numbers:
        q = qualify_document(n, metadata=[m for m in metadata if m.document_number == n],
                             mods=[m for m in mods if m.document_number == n], html=[h for h in html if h.document_number == n],
                             pdf=[p for p in pdf if p.document_number == n],
                             public_inspection=[p for p in pis if p.document_number == n],
                             records=[r for r in records if r.document_number == n], policy=policy,
                             corrections=[m for m in metadata if (m.correction_of or "").strip() == n])
        doc_limits[n] = q.limitations
        if q.document is not None:
            docs[n] = q.document
        else:
            disqualified[n] = q.reason
    # level 2: fund links
    checks = [check_fund_link(l, documents=docs, records=records, html=html, policy=policy) for l in links]
    incomplete = {l.file_number for l in listings if not l.complete}
    evidence_digest = sha256_hex(canonical_json([canonical_json(x.model_dump(mode="python")) for group in
                                                 (metadata, pis, listings, html, pdf, mods, records, links) for x in group]))

    results, rejections = [], []
    for claim in sorted(known_claims, key=lambda c: c.claim_id):
        reference = claim.provenance.source_timestamp
        ctx = Context(T=T, docs=docs, disqualified=disqualified, links=checks,
                      reference_time=reference or claim.claim_received_at, reference_is_upper_bound=reference is None,
                      macro=macro)
        outcome = _verify_claim(claim, [c for c in known_curations if c.claim_id == claim.claim_id], ctx)
        if isinstance(outcome, str):
            rejections.append(AdmissionRejection(claim_id=claim.claim_id, reason=outcome, evaluation_time=T))
            continue
        state, frames, reasons, curation_id, form = outcome
        files = {part for fr in frames for part in fr.frame_key.split(":") if part.startswith("SR-")}
        limitations = set(STATIC_LIMITATIONS) | {l for n in ctx.used_docs for l in doc_limits.get(n, ())} \
            | {f"RESULT_SET_INCOMPLETE:{f}" for f in files & incomplete}
        if policy.accept_synthetic_records:
            limitations.add("TEST_POLICY_ACCEPTS_SYNTHETIC_RECORDS")
        digest = sha256_hex(canonical_json([claim.claim_id, claim.text_digest, T, policy.model_dump(mode="python"), form,
                                            evidence_digest, macro.input_digest if macro else None]))
        results.append(VerificationResult(evaluation_time=T, claim_id=claim.claim_id, curation_id=curation_id, state=state,
                                          frames=frames, reasons=reasons, limitations=tuple(sorted(limitations)),
                                          excluded_after_evaluation=excluded, input_digest=digest))
    return VerificationReport(evaluation_time=T, results=tuple(results),
                              rejections=tuple(sorted(rejections, key=lambda r: r.claim_id)), excluded_after_evaluation=excluded)


def _unverified(reason: str, curation_id: str | None, form: str = ""):
    return S.UNVERIFIED, (), (reason,), curation_id, form or reason


def _fund_resolutions(event: NormEvent, ctx: Context) -> tuple[FundResolution, ...]:
    """Fund-link evidence for the frame's resolved file numbers: its resolved subjects and its SUBJECT
    and FILE_NUMBER facts (a fund value resolved at T). Never read from the asserted identity, which
    differs between equivalent events and depends on which of them deduplication kept."""
    if event.frame_type not in REGULATORY_FRAMES:
        return ()
    values = set(event.ident.get("subjects", ())) | {f.value for f in event.facts
                                                     if f.field in (FactField.SUBJECT.value, FactField.FILE_NUMBER.value)}
    files = set()
    for v in values:
        if v.startswith("FUND:"):
            v = ctx.resolve_fund(v[5:])[0]
        if v is not None and canonical_file_number(v) == v:
            files.add(v)
    return ctx.fund_resolutions(files) if files else ()


def _supersession_cycle(curations: list[CurationRecord]) -> bool:
    """A3: whether any admitted curation lies on a ``supersedes`` cycle (a self-cycle included). Checked
    over every admitted curation before heads are taken, so an unrelated acyclic head cannot hide a
    cycle. Edges are sets keyed by curation id, so the answer depends neither on input order nor on
    duplicates; a target that is not admitted at T ends the chain."""
    edges: dict[str, set[str]] = {c.curation_id: set() for c in curations}
    for c in curations:
        if c.supersedes in edges:
            edges[c.curation_id].add(c.supersedes)
    state: dict[str, bool] = {}                                            # True: on the current path; False: done
    for root in sorted(edges):
        if root in state:
            continue
        state[root], path = True, [(root, iter(sorted(edges[root])))]
        while path:
            node, targets = path[-1]
            nxt = next(targets, None)
            if nxt is None:
                state[node] = False
                path.pop()
            elif state.get(nxt) is True:
                return True
            elif nxt not in state:
                state[nxt] = True
                path.append((nxt, iter(sorted(edges[nxt]))))
    return False


def _verify_claim(claim: ClaimRecord, curations: list[CurationRecord], ctx: Context):
    if not curations:                                                      # A2
        return _unverified("CURATION_NOT_AVAILABLE_AT_T", None)
    if _supersession_cycle(curations):                                     # A3: fail closed, even beside a valid head
        return _unverified("CONFLICTING_CURATIONS", None)
    superseded = {c.supersedes for c in curations if c.supersedes}
    heads = sorted((c for c in curations if c.curation_id not in superseded), key=lambda c: c.curation_id)
    if not heads:                                                          # unreachable without a cycle; kept fail-closed
        return _unverified("CONFLICTING_CURATIONS", None)
    forms = []
    for c in heads:                                                        # A3, A4
        try:
            forms.append((normalize(claim, c, ctx.resolve_fund), c))
        except CurationInvalid as error:
            forms.append((f"CURATION_INVALID:{error.detail}", c))
    if len({f if isinstance(f, str) else f.form for f, _ in forms}) > 1:
        return _unverified("CONFLICTING_CURATIONS", None)
    normalized, curation = forms[0]
    if isinstance(normalized, str):
        return _unverified(normalized, curation.curation_id)
    rejected = admission(curation)                                         # A5
    if rejected:
        return rejected
    if normalized.association_problem:
        return _unverified(normalized.association_problem, curation.curation_id, normalized.form)
    frames, reasons = [], set()
    for event in normalized.events:
        outcome = eval_event(event, ctx)
        frames.append(FrameResult(frame_key=event.key, frame_type=event.frame_type,
                                  state=frame_state(event.frame_type, outcome),
                                  facts=tuple(sorted(outcome.facts, key=lambda f: (f.role.value, f.field, f.asserted))),
                                  reasons=tuple(sorted(set(outcome.reasons))),
                                  fund_resolutions=_fund_resolutions(event, ctx)))
    for key, category in normalized.residuals:                            # A6
        why = RESIDUAL_REASON[category]
        frames.append(FrameResult(frame_key=key, frame_type=FrameType.RESIDUAL, state=S.UNVERIFIED, facts=(), reasons=(why,)))
        if category is SpanCategory.EMBEDDED_INSTRUCTION:
            reasons.add("EMBEDDED_INSTRUCTION_IGNORED")
    frames.sort(key=lambda fr: (fr.frame_key, canonical_json(fr.model_dump(mode="python"))))
    for fr in frames:
        reasons |= set(fr.reasons) | {r for f in fr.facts for r in f.reasons}
    state = claim_state({fr.state for fr in frames}) if frames else S.UNVERIFIED
    if not frames:
        reasons.add("NO_ASSERTION_CURATED")
    return state, tuple(frames), tuple(sorted(reasons)), curation.curation_id, normalized.form
