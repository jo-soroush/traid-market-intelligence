"""V1-C14 contracts: the request sent to a model, the model's output, the validated interpretation,
the local analysis record and the result returned to the caller.

None of these models inherits ``CanonicalModel``: it strips whitespace (``domain/models.py:39-44``)
and would silently change model-written references. ``ExactModel`` keeps every string exactly,
forbids extra fields and is strict; ``C14Model`` adds an explicit UTC-aware check for every
datetime field, because ``CanonicalModel`` normalizes only six named fields.

Nothing here carries trading, pricing, sizing or execution authority: there is no field for an
action, a direction to trade, a size, a target or a confidence, and extra fields are rejected.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UTC = timezone.utc

REQUEST_SCHEMA = "c14-request-1"
RECORD_SCHEMA = "c14-record-1"

HANDLE = r"^E\d{3}$"
CLAIM = r"^N\d{3}$"
FACT = r"^N\d{3}\.F\d{2}$"
ANCHOR = r"^A\d{2}$"
VALUE = r"^(E\d{3})\.V\d{1,3}$"
CATREF = r"^CAT:(C10|C11|C12_MACRO|C12_ETF|C13)$"
SHA256 = r"^[0-9a-f]{64}$"
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?Z$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def aware_utc(value: datetime, name: str = "timestamp") -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def render_time(value: datetime) -> str:
    """The one rendering of an instant used in requests and in the literal catalogue."""
    return aware_utc(value).isoformat().replace("+00:00", "Z")


class ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, str_strip_whitespace=False)


class C14Model(ExactModel):
    @field_validator("*", mode="after")
    @classmethod
    def _utc(cls, value, info):
        if isinstance(value, datetime):
            return aware_utc(value, info.field_name)
        return value


# ------------------------------------------------------------------------ vocabularies
class AIStatus(StrEnum):
    VALID = "VALID"
    AI_INVALID = "AI_INVALID"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AI_NOT_REQUESTED = "AI_NOT_REQUESTED"


class TaskId(StrEnum):
    BTC_MARKET_STATE = "c14-task-btc-market-state-1"     # T1
    MACRO_CONTEXT = "c14-task-macro-context-1"           # T2


class Category(StrEnum):
    C10 = "C10"
    C11 = "C11"
    C12_MACRO = "C12_MACRO"
    C12_ETF = "C12_ETF"
    C13 = "C13"


class Tier(StrEnum):
    STRUCTURED = "STRUCTURED"
    CONTEXTUAL = "CONTEXTUAL"
    ASSESSED_CLAIM = "ASSESSED_CLAIM"


class CategoryState(StrEnum):
    INCLUDED = "INCLUDED"
    PARTIAL = "PARTIAL"
    NOT_SUPPLIED = "NOT_SUPPLIED"
    ALL_EXCLUDED = "ALL_EXCLUDED"
    REPORT_REJECTED = "REPORT_REJECTED"
    NOT_USED_BY_TASK = "NOT_USED_BY_TASK"
    NOT_RELEASED = "NOT_RELEASED"          # C11 only: one constant for every reason it is absent


class TimeKind(StrEnum):
    AVAILABILITY = "AVAILABILITY"                          # when TraID obtained it; <= T
    OBSERVATION_OR_PUBLICATION = "OBSERVATION_OR_PUBLICATION"   # about the world; <= T, never aged
    SCHEDULED = "SCHEDULED"                                # never compared with T
    DATE = "DATE"                                          # a date label, unchanged
    PERIOD_LABEL = "PERIOD_LABEL"                          # e.g. a BLS reference period


class Stance(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    MIXED = "MIXED"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


class Persistence(StrEnum):
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    UNCONFIRMED = "UNCONFIRMED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class PersistenceDetail(StrEnum):
    TERMINAL = "TERMINAL"                                  # the commit finished (succeeded or failed) before the decision
    UNRESOLVED_AT_DEADLINE = "UNRESOLVED_AT_DEADLINE"      # the commit was still in progress at the deadline
    DEFERRED_AFTER_FINALIZATION = "DEFERRED_AFTER_FINALIZATION"   # the one record is written after the caller returned
    NO_RECORD = "NO_RECORD"                                # no record is ever written for this invocation


# ------------------------------------------------------------------------- the request
class TimedValue(C14Model):
    """An upstream time, passed through unchanged and classified; any time not classified is not sent."""
    kind: TimeKind
    name: str = Field(min_length=1)
    value: str

    @model_validator(mode="after")
    def rendered(self):
        if self.kind in (TimeKind.AVAILABILITY, TimeKind.OBSERVATION_OR_PUBLICATION):
            if not ISO_UTC.match(self.value):
                raise ValueError("an instant must be rendered in UTC with a Z suffix")
        elif self.kind is TimeKind.SCHEDULED:
            if not (ISO_UTC.match(self.value) or ISO_DATE.match(self.value)):
                raise ValueError("a schedule is a UTC instant or a date")
        elif self.kind is TimeKind.DATE and not ISO_DATE.match(self.value):
            raise ValueError("a date label must be an ISO date")
        return self


class Attribute(C14Model):
    """A categorical, code-supplied value (state, unit, identifier)."""
    name: str = Field(min_length=1)
    value: str


class BoundValue(C14Model):
    """An eligible upstream number. Only these may be written by the model, and only as one of ``displays``."""
    value_id: str = Field(pattern=VALUE)
    field_path: str
    value: str                                 # exact fixed-point rendering of the upstream Decimal
    unit: str
    displays: tuple[str, ...] = Field(min_length=1)
    qualifier: str | None = None               # e.g. EARLIER_RECEIPT_VALUE, AS_STATED_IN_STATEMENT_DATED_<D>
    group: str | None = None                   # values that may appear together in one statement


class EvidenceItem(C14Model):
    evidence_id: str = Field(pattern=HANDLE)
    category: Category
    tier: Literal[Tier.STRUCTURED, Tier.CONTEXTUAL]
    kind: str
    subject: str
    state: str | None
    attributes: tuple[Attribute, ...] = ()
    values: tuple[BoundValue, ...] = ()
    values_withheld: tuple[str, ...] = ()
    times: tuple[TimedValue, ...] = ()
    reasons: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class Anchor(C14Model):
    anchor_id: str = Field(pattern=ANCHOR)
    evidence_id: str = Field(pattern=HANDLE)
    statement: str                             # code template; gives "supports"/"contradicts" its meaning


class UnavailableEntry(C14Model):
    """Code-owned missing information: shown to the model, never citable as evidence."""
    category: Category
    subject: str
    reasons: tuple[str, ...]


class CitationView(C14Model):
    role: Literal["SUPPORTS", "CONTRADICTS", "SUPERSEDES", "ESTABLISHES_EARLIER_STATUS"]
    document_number: str | None
    c12_field_path: str | None
    subject: str
    action: str | None
    dates: tuple[TimedValue, ...]


class FactEntry(C14Model):
    fact_id: str = Field(pattern=FACT)
    field: str
    role: Literal["PREDICATE", "QUALIFIER"]
    outcome: Literal["SUPPORTED", "CONTRADICTED", "SUPERSEDED", "UNRESOLVED"]
    claim_asserted: str                        # the claim side: curated assertion, never evidence or a value source
    citations: tuple[CitationView, ...]        # the evidence side
    reasons: tuple[str, ...]
    linked_value_ids: tuple[str, ...] = ()     # eligible C12 values that the cited path and comparison bind


class FrameView(C14Model):
    frame_type: str
    state: str
    reasons: tuple[str, ...]
    facts: tuple[FactEntry, ...]
    fund_tickers: tuple[str, ...] = ()


class AssessedClaim(C14Model):
    claim_id: str = Field(pattern=CLAIM)
    tier: Literal[Tier.ASSESSED_CLAIM] = Tier.ASSESSED_CLAIM
    state: str                                 # the C13 claim state, always shown
    applicability: Literal["BTC_VIA_FUND_RESOLUTION", "MACRO"]
    frames: tuple[FrameView, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]


class CategoryStatus(C14Model):
    category: Category
    state: CategoryState
    reasons: tuple[str, ...]


class RequiredSections(C14Model):
    """Computed by code: the model never decides which sections apply."""
    anchor_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    summary_category: Category
    min_uncertainties: int = Field(ge=1)


class AIInterpretationRequest(C14Model):
    """Exactly what is serialized into the single user message."""
    request_schema: Literal["c14-request-1"] = REQUEST_SCHEMA
    task_id: TaskId
    evaluation_time: datetime
    asset_scope: Literal["BTC", "NONE_MACRO_ONLY"]
    anchors: tuple[Anchor, ...]
    structured: tuple[EvidenceItem, ...]
    contextual: tuple[EvidenceItem, ...]
    assessed_claims: tuple[AssessedClaim, ...]
    unavailable: tuple[UnavailableEntry, ...]
    categories: tuple[CategoryStatus, ...]
    required: RequiredSections
    limitations: tuple[str, ...]
    prompt_id: str
    prompt_digest: str = Field(pattern=SHA256)
    schema_id: str
    schema_digest: str = Field(pattern=SHA256)
    selection_policy_id: str
    selection_policy_digest: str = Field(pattern=SHA256)


# -------------------------------------------------------------------- the model output
class NumberRef(ExactModel):
    value_id: str
    text: str


class Note(ExactModel):
    statement: str
    refs: tuple[str, ...] = Field(max_length=8)
    numbers: tuple[NumberRef, ...] = Field(max_length=4)


class AnchorAssessment(ExactModel):
    anchor_id: str
    stance: Stance
    statement: str
    evidence_ids: tuple[str, ...] = Field(max_length=8)
    numbers: tuple[NumberRef, ...] = Field(max_length=4)


class ClaimNote(ExactModel):
    claim_id: str
    statement: str
    refs: tuple[str, ...] = Field(max_length=8)
    numbers: tuple[NumberRef, ...] = Field(max_length=4)


class TaskOutput(ExactModel):
    summary: Note
    anchor_assessments: tuple[AnchorAssessment, ...] = Field(max_length=6)
    context_notes: tuple[Note, ...] = Field(max_length=10)
    claim_notes: tuple[ClaimNote, ...] = Field(max_length=8)
    uncertainties: tuple[Note, ...] = Field(max_length=10)


# ------------------------------------------------------- the validated, canonical interpretation
class CanonicalFactor(ExactModel):
    anchor_id: str
    statement: str
    evidence_ids: tuple[str, ...]          # independent evidence only: the anchor's own sources are removed
    numbers: tuple[NumberRef, ...]


class CanonicalNote(ExactModel):
    origin: Literal["ANCHOR_MIXED", "ANCHOR_NOT_ASSESSABLE", "UNCERTAINTIES_SECTION"]
    anchor_id: str | None
    statement: str
    refs: tuple[str, ...]
    numbers: tuple[NumberRef, ...]


class MissingInformation(C14Model):
    category: Category
    subject: str
    reasons: tuple[str, ...]


class SourceReference(C14Model):
    ref: str
    category: Category
    tier: Tier
    kind: str
    subject: str
    engine_version: str


class Annotation(C14Model):
    """Attached by code to every reference the model used; the model never supplies these."""
    ref: str
    category: Category
    tier: Tier
    upstream_state: str | None
    claim_state: str | None


class ValidatedInterpretation(C14Model):
    """Blueprint fields (``supporting_factors`` ... ``analysis_timestamp``) projected by a deterministic
    adapter from the strict task output, which is kept unchanged in ``output``."""
    task_id: TaskId
    output: TaskOutput
    supporting_factors: tuple[CanonicalFactor, ...]
    contradicting_factors: tuple[CanonicalFactor, ...]
    uncertainty: tuple[CanonicalNote, ...]
    missing_information: tuple[MissingInformation, ...]
    evidence: tuple[str, ...]
    source_references: tuple[SourceReference, ...]
    analysis_timestamp: datetime
    annotations: tuple[Annotation, ...]
    flags: tuple[str, ...]
    limitations: tuple[str, ...]


# ----------------------------------------------------------------------------- records
class ExcludedItem(C14Model):
    category: Category
    locator: str
    reason: str


class AttemptRecord(C14Model):
    number: int = Field(ge=1, le=2)
    outcome: Literal["RESPONSE", "FAILURE", "DISCARDED_AFTER_DEADLINE"]
    error_code: str | None
    retry_safe: bool
    http_sends: int = Field(ge=0, le=2)
    started_offset_ms: int = Field(ge=0)
    duration_ms: int | None
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider_latency_ms: int | None = None
    request_id: str | None = None


class Measure(C14Model):
    value: Decimal | None
    unit: str
    reason: str | None

    @model_validator(mode="after")
    def explicit(self):
        if (self.value is None) == (self.reason is None):
            raise ValueError("a measure has a value or a reason, never both or neither")
        return self


class ModelMetadata(C14Model):
    provider: str
    api: str
    model_id_sent: str
    source_region: str | None
    approved_destination_regions: tuple[str, ...]
    destinations_verified_on: date | None
    destination_region: Literal["NOT_REPORTED_BY_API"] = "NOT_REPORTED_BY_API"
    model_version: Literal["NOT_REPORTED_BY_API"] = "NOT_REPORTED_BY_API"
    temperature: Decimal
    max_tokens: int
    cost: Measure
    price_table_version: str | None


class BoundedRaw(C14Model):
    """The provider response, bounded. ``content`` is cut only with ``truncated`` set, never silently."""
    content: str | None
    sha256: str = Field(pattern=SHA256)
    size_bytes: int = Field(ge=0)
    truncated: bool
    omitted_reason: str | None


class ReportDigest(C14Model):
    category: Category
    engine_version: str
    sha256: str = Field(pattern=SHA256)


class HandleSource(C14Model):
    ref: str
    category: Category
    locator: str


class PrivateBindings(C14Model):
    """Owner-only replay bindings. Never part of the request (the request model has no such field)."""
    report_digests: tuple[ReportDigest, ...]
    handle_sources: tuple[HandleSource, ...]
    watchlist_version: str | None
    watchlist_digest: str | None
    whale_rules_digest: str | None
    whale_contributors: tuple[str, ...]
    whale_gate: str | None


class AIAnalysisRecord(C14Model):
    """One immutable record per invocation (none for a busy-slot refusal). It holds the outcome the
    worker decided before persistence; it is never proof that anything was released (``release_rule``)."""
    record_schema: Literal["c14-record-1"] = RECORD_SCHEMA
    run_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    invoked_at: datetime
    decided_at: datetime
    deadline_at: datetime
    release_rule: str
    status: AIStatus
    reasons: tuple[str, ...]
    task_id: str
    evaluation_time: datetime | None
    request: AIInterpretationRequest | None
    request_sha256: str | None
    excluded_items: tuple[ExcludedItem, ...]
    attempts: tuple[AttemptRecord, ...] = Field(max_length=2)
    model: ModelMetadata | None
    interpretation: ValidatedInterpretation | None
    tool_input_sha256: str | None
    raw_response: BoundedRaw | None
    private_bindings: PrivateBindings | None
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def interpretation_only_when_valid(self):
        if (self.interpretation is not None) != (self.status is AIStatus.VALID):
            raise ValueError("a record carries an interpretation exactly when its status is VALID")
        return self


class AIResult(C14Model):
    """Returned to the caller. ``interpretation`` is present only on the confirmed, on-time VALID path."""
    run_id: str | None
    status: AIStatus
    reasons: tuple[str, ...]
    interpretation: ValidatedInterpretation | None
    persistence: Persistence
    persistence_detail: PersistenceDetail
    persistence_reason: str | None
    pre_persistence_status: AIStatus | None
    record_path: str | None
    limitations: tuple[str, ...]

    @model_validator(mode="after")
    def released_only_when_valid(self):
        if self.interpretation is not None and (
                self.status is not AIStatus.VALID or self.persistence is not Persistence.COMMITTED):
            raise ValueError("an interpretation is released only as a committed VALID result")
        if self.status is AIStatus.VALID and self.interpretation is None:
            raise ValueError("a VALID result carries its interpretation")
        return self
