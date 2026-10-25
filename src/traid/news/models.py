"""C13 typed contracts: untrusted claims, human curations, official-source records and results.

Design R4 §3. Every model is a frozen C02 ``CanonicalModel`` (``extra="forbid"``) with UTC-aware
datetimes. Text is never stripped: claim text and verbatim passages keep their exact characters,
so span offsets and literal cross-checks stay exact. Date-only values are ``date`` labels, never
synthetic timestamps. A ``VerificationResult`` has no direction, impact, score or trade field.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import unicodedata

from pydantic import ConfigDict, Field, field_validator, model_validator

from traid.domain.models import CanonicalModel, SourceProvenance

UTC = timezone.utc
ENGINE_VERSION = "c13-news-verification-1"


def utc(value, name: str = "timestamp") -> datetime:
    if isinstance(value, str):  # JSON round trip
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def decimal_text(d: Decimal) -> str:
    """Exact plain-notation text of a finite Decimal, independent of the ambient decimal context.

    Only trailing zeros are removed (3.7500 -> 3.75, 1E+2 -> 100); no digit is ever rounded. The
    digit tuple is rendered by hand, so no context precision, rounding mode or trap applies."""
    sign, digits, exponent = d.as_tuple()
    if not isinstance(exponent, int):
        return str(d)                               # NaN / Infinity: never canonicalized as numbers
    digits = list(digits)
    while len(digits) > 1 and digits[-1] == 0 and exponent < 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        return "0"
    text = "".join(map(str, digits))
    if exponent >= 0:
        text += "0" * exponent
    else:
        text = text.rjust(-exponent + 1, "0")
        text = f"{text[:exponent]}.{text[exponent:]}"
    return ("-" if sign else "") + text


def canonical_json(value) -> str:
    def convert(v):
        if isinstance(v, dict):
            return {str(k): convert(v[k]) for k in sorted(v, key=str)}
        if isinstance(v, (list, tuple, frozenset, set)):
            items = [convert(x) for x in v]
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True)) if isinstance(v, (set, frozenset)) else items
        if isinstance(v, Decimal):
            return decimal_text(v)
        if isinstance(v, (datetime, date, time)):
            return v.isoformat()
        if isinstance(v, timedelta):
            return f"{v // timedelta(microseconds=1)}us"
        if isinstance(v, bytes):
            return hashlib.sha256(v).hexdigest()
        if isinstance(v, StrEnum):
            return str(v)
        return v
    return json.dumps(convert(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def text_digest(text: str) -> str:
    return sha256_hex(unicodedata.normalize("NFC", text))


class NewsModel(CanonicalModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    @field_validator("claim_received_at", "curated_at", "retrieved_at", "filed_at", "verified_at", "recorded_at",
                     "pdf_retrieved_at", "available_at", "evaluation_time", mode="before", check_fields=False)
    @classmethod
    def aware(cls, value):
        return None if value is None else utc(value)


SHA256 = r"^[0-9a-f]{64}$"
DOCUMENT_NUMBER = r"^\d{4}-\d{5}$"
METADATA_DOCUMENT_NUMBER = r"^(C\d+-)?\d{4}-\d{5}$"   # FR metadata may describe a correction, e.g. C1-2024-26524


# ------------------------------------------------------------------------- vocabularies
class VerificationState(StrEnum):
    CONFIRMED = "CONFIRMED"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    UNVERIFIED = "UNVERIFIED"
    MISLEADING = "MISLEADING"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"


class FactOutcome(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    SUPERSEDED = "SUPERSEDED"
    UNRESOLVED = "UNRESOLVED"


class FactRole(StrEnum):
    PREDICATE = "PREDICATE"
    QUALIFIER = "QUALIFIER"


class FrameType(StrEnum):
    REG_DOC = "REG_DOC"
    REG_EVENT = "REG_EVENT"
    REG_STATUS_AT = "REG_STATUS_AT"
    REG_CURRENT_STATUS = "REG_CURRENT_STATUS"
    LATEST_IDENTITY = "LATEST_IDENTITY"
    NON_SOURCE_EVENT = "NON_SOURCE_EVENT"
    MACRO_VALUE = "MACRO_VALUE"
    MACRO_CHANGE = "MACRO_CHANGE"
    MACRO_CONSENSUS = "MACRO_CONSENSUS"
    FOMC_DECISION = "FOMC_DECISION"
    FOMC_CURRENT_RANGE = "FOMC_CURRENT_RANGE"
    FOMC_SCHEDULE = "FOMC_SCHEDULE"
    RESIDUAL = "RESIDUAL"        # built from uncovered spans; never curated directly


REGULATORY_FRAMES = frozenset({FrameType.REG_DOC, FrameType.REG_EVENT, FrameType.REG_STATUS_AT,
                               FrameType.REG_CURRENT_STATUS, FrameType.NON_SOURCE_EVENT})
BLS_FRAMES = frozenset({FrameType.MACRO_VALUE, FrameType.MACRO_CHANGE, FrameType.MACRO_CONSENSUS})
FOMC_FRAMES = frozenset({FrameType.FOMC_DECISION, FrameType.FOMC_CURRENT_RANGE, FrameType.FOMC_SCHEDULE})
MACRO_FRAMES = BLS_FRAMES | FOMC_FRAMES


class SpanCategory(StrEnum):
    PROPOSITION = "PROPOSITION"
    ATTRIBUTION = "ATTRIBUTION"
    DATELINE_OR_BYLINE = "DATELINE_OR_BYLINE"
    QUOTATION_MARKUP = "QUOTATION_MARKUP"
    INTERPRETATION = "INTERPRETATION"
    EMBEDDED_INSTRUCTION = "EMBEDDED_INSTRUCTION"
    NUMERIC_ETF_MARKET_DATA = "NUMERIC_ETF_MARKET_DATA"
    UNCURATABLE = "UNCURATABLE"


NON_ASSERTIVE_SPANS = frozenset({SpanCategory.ATTRIBUTION, SpanCategory.DATELINE_OR_BYLINE,
                                 SpanCategory.QUOTATION_MARKUP})
RESIDUAL_SPANS = frozenset({SpanCategory.INTERPRETATION, SpanCategory.EMBEDDED_INSTRUCTION,
                            SpanCategory.NUMERIC_ETF_MARKET_DATA, SpanCategory.UNCURATABLE})


class FactField(StrEnum):
    ACTION = "ACTION"
    SUBJECT = "SUBJECT"
    DATE = "DATE"                      # role comes from the date-role token, never from the curator
    RELEASE_NO = "RELEASE_NO"
    FILE_NUMBER = "FILE_NUMBER"
    VENUE = "VENUE"
    ACCELERATED = "ACCELERATED"
    STATUS = "STATUS"
    SINCE = "SINCE"
    MEMBER_IS_LATEST = "MEMBER_IS_LATEST"
    EVENT = "EVENT"
    VALUE = "VALUE"
    UNIT = "UNIT"
    PRELIMINARY = "PRELIMINARY"
    CHANGE = "CHANGE"
    CONSENSUS = "CONSENSUS"
    SURPRISE = "SURPRISE"
    TARGET_RANGE = "TARGET_RANGE"
    CHANGE_SIZE = "CHANGE_SIZE"
    SCHEDULED_ON = "SCHEDULED_ON"
    ANNOUNCEMENT_TIME = "ANNOUNCEMENT_TIME"
    PROJECTIONS = "PROJECTIONS"


class DateToken(StrEnum):
    ORDERED_ON = "ORDERED_ON"
    PUBLISHED_FR = "PUBLISHED_FR"
    PUBLIC_INSPECTION = "PUBLIC_INSPECTION"
    EXCHANGE_FILED = "EXCHANGE_FILED"
    DESIGNATED_DEADLINE = "DESIGNATED_DEADLINE"
    AMBIGUOUS = "AMBIGUOUS"


class DateRole(StrEnum):
    ORDER_DATE = "ORDER_DATE"
    FR_PUBLICATION_DATE = "FR_PUBLICATION_DATE"
    PUBLIC_INSPECTION = "PUBLIC_INSPECTION"
    FILING_DATE = "FILING_DATE"
    DEADLINE = "DEADLINE"


DATE_ROLES = {DateToken.ORDERED_ON: (DateRole.ORDER_DATE,), DateToken.PUBLISHED_FR: (DateRole.FR_PUBLICATION_DATE,),
              DateToken.PUBLIC_INSPECTION: (DateRole.PUBLIC_INSPECTION,),
              DateToken.EXCHANGE_FILED: (DateRole.FILING_DATE,), DateToken.DESIGNATED_DEADLINE: (DateRole.DEADLINE,),
              DateToken.AMBIGUOUS: tuple(DateRole)}


class ChangeToken(StrEnum):
    STATED_IN_DECISION = "STATED_IN_DECISION"
    DERIVED_COMPARISON = "DERIVED_COMPARISON"


class RegAction(StrEnum):
    APPROVED = "APPROVED"                          # bare "approved": admissible set for a fund subject
    RULE_CHANGE_APPROVED = "RULE_CHANGE_APPROVED"  # explicitly "approved the rule change"
    DISAPPROVED = "DISAPPROVED"
    INSTITUTED_PROCEEDINGS = "INSTITUTED_PROCEEDINGS"
    NOTICE_OF_FILING = "NOTICE_OF_FILING"
    LONGER_PERIOD_DESIGNATED = "LONGER_PERIOD_DESIGNATED"
    EFFECTIVE_ON_FILING = "EFFECTIVE_ON_FILING"
    REGISTRATION_EFFECTIVE = "REGISTRATION_EFFECTIVE"   # issuer registration: no approved source


class RegStatus(StrEnum):
    FILED = "FILED"
    UNDER_PROCEEDINGS = "UNDER_PROCEEDINGS"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DISAPPROVED = "DISAPPROVED"
    EFFECTIVE_ON_FILING = "EFFECTIVE_ON_FILING"


class NonSourceEvent(StrEnum):
    ISSUER_REGISTRATION_EFFECTIVE = "ISSUER_REGISTRATION_EFFECTIVE"
    LISTING_ANNOUNCEMENT = "LISTING_ANNOUNCEMENT"
    SCHEDULED_LISTING = "SCHEDULED_LISTING"
    TRADING_START = "TRADING_START"
    COURT_ACTION = "COURT_ACTION"


class MacroScope(StrEnum):
    AS_PUBLISHED_AT_SOME_RECEIPT = "AS_PUBLISHED_AT_SOME_RECEIPT"
    CURRENT = "CURRENT"
    ORIGINAL = "ORIGINAL"


class ChangeKind(StrEnum):
    MOM_PCT = "MOM_PCT"
    YOY_PCT = "YOY_PCT"
    LEVEL_DIFF = "LEVEL_DIFF"


class FomcAction(StrEnum):
    MAINTAIN = "MAINTAIN"
    RAISE = "RAISE"
    LOWER = "LOWER"


# Series tokens a curation may name (closed). "CPI" without SA/NSA is the admissible set of both CPI series.
# The macro adapter checks these against C12's verified BLS registry.
BLS_SERIES_TOKENS = ("CES0000000001", "CUSR0000SA0", "CUUR0000SA0", "LNS14000000")
CPI_SERIES = ("CUSR0000SA0", "CUUR0000SA0")
BEA_SERIES_TOKENS = ("GDP", "PCE")
SERIES_TOKENS = BLS_SERIES_TOKENS + ("CPI",) + BEA_SERIES_TOKENS


class Sequence(StrEnum):
    SEC_ORDERS_ON_FILE = "SEC_ORDERS_ON_FILE"
    FOMC_STATEMENTS = "FOMC_STATEMENTS"


class PatternId(StrEnum):
    NOTICE_OF_FILING = "NOTICE_OF_FILING"
    LONGER_PERIOD = "LONGER_PERIOD"
    PROCEEDINGS = "PROCEEDINGS"
    APPROVAL = "APPROVAL"
    DISAPPROVAL = "DISAPPROVAL"
    EFFECTIVE_ON_FILING_19B4F6 = "EFFECTIVE_ON_FILING_19B4F6"


class PassageKind(StrEnum):
    PAGE_HEADER = "PAGE_HEADER"
    HEADING = "HEADING"
    DATE_LINE = "DATE_LINE"
    OPERATIVE = "OPERATIVE"
    TERMINATOR = "TERMINATOR"      # "[FR Doc. N Filed M-D-YY; H:MM am]": terminator and filed line
    STATED_DATE = "STATED_DATE"
    NAME = "NAME"


class PassageCheck(StrEnum):
    LITERAL_HTML = "LITERAL_HTML"
    STRUCTURED_METADATA = "STRUCTURED_METADATA"


class RecordPurpose(StrEnum):
    QUALIFYING = "QUALIFYING"
    FUND_NAME = "FUND_NAME"


class RecordOrigin(StrEnum):
    """Who produced a manual record. Only HUMAN records count unless a test policy says otherwise."""
    HUMAN = "HUMAN"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"


class AbsentCheck(StrEnum):
    NO_SECOND_OPERATIVE_SENTENCE = "NO_SECOND_OPERATIVE_SENTENCE"
    NO_SECOND_HEADING = "NO_SECOND_HEADING"
    NO_SECOND_TERMINATOR = "NO_SECOND_TERMINATOR"
    SECOND_OPERATIVE_SENTENCE_RENDERED = "SECOND_OPERATIVE_SENTENCE_RENDERED"   # the verifier saw a second one


class CitationRole(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    ESTABLISHES_EARLIER_STATUS = "ESTABLISHES_EARLIER_STATUS"


class ComponentKind(StrEnum):
    FR_METADATA = "FR_METADATA"
    GOVINFO_MODS = "GOVINFO_MODS"
    GOVINFO_HTML = "GOVINFO_HTML"
    GOVINFO_PDF = "GOVINFO_PDF"
    FR_PUBLIC_INSPECTION = "FR_PUBLIC_INSPECTION"
    MANUAL_RECORD = "MANUAL_RECORD"


# ------------------------------------------------------------------------ untrusted input
class ClaimRecord(NewsModel):
    """A claim as received. ``text`` is opaque untrusted data: never parsed or executed by the engine."""
    claim_id: str = Field(pattern=SHA256)
    text: str = Field(min_length=1, max_length=20000)
    text_digest: str = Field(pattern=SHA256)
    provenance: SourceProvenance        # source_timestamp = claimed publication time (untrusted), may be None
    claim_received_at: datetime

    @model_validator(mode="after")
    def identified(self):
        if self.text_digest != text_digest(self.text):
            raise ValueError("text_digest must be the SHA-256 of the NFC-normalized text")
        if self.claim_id != claim_id_for(self.provenance, self.text_digest):
            raise ValueError("claim_id must be derived from the source id and the text digest")
        if self.claim_received_at != self.provenance.received_timestamp:
            raise ValueError("claim_received_at is TraID's receipt time")
        return self


def claim_id_for(provenance: SourceProvenance, digest: str) -> str:
    return sha256_hex(f"{provenance.source}|{provenance.source_id or ''}|{digest}")


def make_claim(text: str, provenance: SourceProvenance) -> ClaimRecord:
    digest = text_digest(text)
    return ClaimRecord(claim_id=claim_id_for(provenance, digest), text=text, text_digest=digest,
                       provenance=provenance, claim_received_at=provenance.received_timestamp)


# ------------------------------------------------------------------------------ curation
class CuratedSpan(NewsModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    category: SpanCategory
    proposition_ids: tuple[str, ...] = ()


class EventIdentity(NewsModel):
    """Only what the claim states. Which fields are allowed is fixed per frame type (curation.py)."""
    document_number: str | None = None
    subjects: tuple[str, ...] = ()
    action: str | None = None
    status_date: str | None = None
    sequence: Sequence | None = None
    sequence_file: str | None = None
    member_document_number: str | None = None
    member_pattern: PatternId | None = None
    member_date: str | None = None
    board_date: str | None = None
    series: str | None = None
    period: str | None = None
    scope: MacroScope | None = None
    change_kind: ChangeKind | None = None
    event_type: NonSourceEvent | None = None
    meeting_start: str | None = None
    meeting_end: str | None = None


class CuratedEvent(NewsModel):
    event_id: str = Field(min_length=1)
    frame_type: FrameType
    identity: EventIdentity


class CuratedFact(NewsModel):
    field: FactField
    value: str = Field(min_length=1)
    token: str | None = None            # date-role or change-size token from the closed lists


class CuratedProposition(NewsModel):
    proposition_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    facts: tuple[CuratedFact, ...] = Field(min_length=1)


class CurationRecord(NewsModel):
    """A human curation of one claim. Structural validity (span partition, references) is checked by
    the engine (rule A4) so that an invalid curation yields UNVERIFIED instead of being repaired."""
    curation_id: str = Field(min_length=1)
    claim_id: str = Field(pattern=SHA256)
    curated_at: datetime
    curator: str = Field(min_length=1)            # role label, never a personal identifier
    supersedes: str | None = None
    spans: tuple[CuratedSpan, ...]
    events: tuple[CuratedEvent, ...] = ()
    propositions: tuple[CuratedProposition, ...] = ()
    distinct: tuple[tuple[str, str], ...] = ()


# ------------------------------------------------------------------------ source records
class FrMetadataRecord(NewsModel):
    """Federal Register API document metadata: discovery and identifiers only, never classification."""
    document_number: str = Field(pattern=METADATA_DOCUMENT_NUMBER)
    citation: str
    volume: int = Field(gt=0)
    start_page: int = Field(gt=0)
    end_page: int = Field(gt=0)
    publication_date: date
    document_type: str
    agency_slugs: tuple[str, ...]
    docket_ids: tuple[str, ...]
    title: str                          # cross-check only, never classifies
    correction_of: str | None
    corrections: tuple[str, ...]
    pdf_url: str | None                 # FR JSON URL fields: equality cross-check only (R3 §6.5)
    mods_url: str | None
    source_url: str
    retrieved_at: datetime
    payload_digest: str = Field(pattern=SHA256)

    @model_validator(mode="after")
    def pages(self):
        if self.end_page < self.start_page:
            raise ValueError("end_page precedes start_page")
        return self


class FrPublicInspectionRecord(NewsModel):
    document_number: str = Field(pattern=DOCUMENT_NUMBER)
    filed_at: datetime                  # normalized to UTC
    filed_at_source: str                # exactly as published, with its UTC offset
    source_url: str
    retrieved_at: datetime
    payload_digest: str = Field(pattern=SHA256)

    @model_validator(mode="after")
    def same_instant(self):
        if utc(self.filed_at_source, "filed_at_source") != self.filed_at:
            raise ValueError("filed_at must equal the published filed_at instant")
        return self


class DocketListing(NewsModel):
    file_number: str
    query_url: str
    count: int = Field(ge=0)
    returned: int = Field(ge=0)
    pages_fetched: int = Field(ge=0)
    complete: bool                      # count == returned and no further page
    document_numbers: tuple[str, ...]
    retrieved_at: datetime
    payload_digest: str = Field(pattern=SHA256)


class _Retrieval(NewsModel):
    document_number: str = Field(pattern=DOCUMENT_NUMBER)
    url: str
    retrieved_at: datetime
    sha256: str = Field(pattern=SHA256)
    byte_length: int = Field(ge=0)


class GovInfoPdf(_Retrieval):
    """A PDF retrieval. Its bytes are never read for qualification (R2): only its digest is bound."""


class GovInfoHtml(_Retrieval):
    body: bytes = Field(repr=False)

    @model_validator(mode="after")
    def bound(self):
        if sha256_hex(self.body) != self.sha256 or len(self.body) != self.byte_length:
            raise ValueError("sha256 and byte_length must describe body")
        return self


class GovInfoModsRetrieval(_Retrieval):
    body: bytes = Field(repr=False)

    @model_validator(mode="after")
    def bound(self):
        if sha256_hex(self.body) != self.sha256 or len(self.body) != self.byte_length:
            raise ValueError("sha256 and byte_length must describe body")
        return self


class GovInfoMods(NewsModel):
    """MODS fields from the structural parse (§6.7), never from text search."""
    document_number: str
    url: str
    retrieved_at: datetime
    sha256: str
    volume: int
    issue: int
    start_page: int
    end_page: int
    issue_start_page: int
    issue_end_page: int
    date_issued: date
    fr_doc_no: str
    fr_citation: str
    department_codes: tuple[str, ...]
    package_record_identifier: str


class ManualPassage(NewsModel):
    kind: PassageKind
    text: str = Field(min_length=1)     # verbatim, as rendered
    pdf_page_index: int = Field(ge=0)
    fr_printed_page: int = Field(gt=0)


class ManualPassageVerification(NewsModel):
    """A human reading of the RENDERED official PDF (R2/R5). Append-only; corrections use supersedes."""
    record_id: str = Field(min_length=1)
    origin: RecordOrigin
    document_number: str = Field(pattern=DOCUMENT_NUMBER)
    purpose: RecordPurpose
    qualifying_record_id: str | None = None
    pdf_url: str
    pdf_sha256: str = Field(pattern=SHA256)
    pdf_retrieved_at: datetime
    viewer: str = Field(min_length=1)   # rendering application and version; never a text extractor
    passages: tuple[ManualPassage, ...] = Field(min_length=1)
    absent_checks: tuple[AbsentCheck, ...] = ()
    verifier: str = Field(min_length=1)  # role label, never a personal identifier
    verified_at: datetime
    recorded_at: datetime
    supersedes: str | None = None

    @model_validator(mode="after")
    def coherent(self):
        if not self.pdf_retrieved_at <= self.verified_at <= self.recorded_at:
            raise ValueError("a record is verified after its PDF retrieval and recorded after verification")
        kinds = [p.kind for p in self.passages]
        if len(kinds) != len(set(kinds)):
            raise ValueError("each passage kind occurs at most once in a record")
        if self.purpose is RecordPurpose.FUND_NAME:
            if self.qualifying_record_id is None or set(kinds) != {PassageKind.NAME}:
                raise ValueError("a FUND_NAME record holds NAME passages only and names its qualifying record")
        elif self.qualifying_record_id is not None or PassageKind.NAME in kinds:
            raise ValueError("a QUALIFYING record holds no NAME passage and names no qualifying record")
        return self

    @property
    def available_at(self) -> datetime:
        """§7.4 level 0′: its own times and the level-0 PDF retrieval it cites, nothing downstream."""
        return max(self.verified_at, self.recorded_at, self.pdf_retrieved_at)


class FileNumberFundLink(NewsModel):
    """Curated, evidence-backed link from a fund subject to a rule-change file number (§9.3)."""
    link_id: str = Field(min_length=1)
    file_number: str
    name_in_document: str = Field(min_length=1)
    document_number: str = Field(pattern=DOCUMENT_NUMBER)
    name_record_id: str
    ticker: str = Field(min_length=1)
    cik: str = Field(pattern=r"^\d{10}$")
    identity_evidence: SourceProvenance
    sro: str
    listing_exchange_per_identity_source: str | None = None
    curated_at: datetime


class OfficialEvidence(NewsModel):
    """Every official-source input known to the caller; filtered at T by the engine (I1)."""
    fr_metadata: tuple[FrMetadataRecord, ...] = ()
    public_inspection: tuple[FrPublicInspectionRecord, ...] = ()
    docket_listings: tuple[DocketListing, ...] = ()
    html: tuple[GovInfoHtml, ...] = ()
    pdf: tuple[GovInfoPdf, ...] = ()
    mods: tuple[GovInfoModsRetrieval, ...] = ()
    manual_records: tuple[ManualPassageVerification, ...] = ()
    fund_links: tuple[FileNumberFundLink, ...] = ()


class VerificationPolicy(NewsModel):
    """Versioned verification configuration.

    ``enabled_patterns``: a pattern is usable only once a human manual record exists for at least one
    real fixture of it (§6.4). No human record exists yet, so the production default enables none.
    ``accept_synthetic_records``: test-only; results then carry SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED."""
    enabled_patterns: tuple[PatternId, ...] = ()
    accept_synthetic_records: bool = False


DEFAULT_POLICY = VerificationPolicy()


# ------------------------------------------------------------------------------ output
class ComponentRef(NewsModel):
    kind: ComponentKind
    url: str
    sha256: str
    retrieved_at: datetime


class VerifiedPassage(NewsModel):
    kind: PassageKind
    normalized_text: str
    check: PassageCheck
    parsed_header: tuple[int, int, int, str, date, str] | None = None   # page, volume, issue, weekday, date, section
    html_location: tuple[int, int] | None = None                      # (fr_page, char_offset) in the GovInfo HTML
    pdf_location: tuple[int, int]                                     # (pdf_page_index, fr_printed_page) as recorded
    manual_record_id: str


class QualifiedDocument(NewsModel):
    document_number: str
    pattern_id: PatternId
    release_no: str
    file_numbers: tuple[str, ...]
    order_or_notice_date: date | None
    accelerated: bool
    start_page: int
    end_page: int
    fr_publication_date: date
    public_inspection_filed_at: datetime | None
    public_inspection_local_date: date | None
    passages: tuple[VerifiedPassage, ...]
    components: tuple[ComponentRef, ...]
    qualifying_record_id: str
    record_origin: RecordOrigin
    available_at: datetime


class EvidenceCitation(NewsModel):
    role: CitationRole
    document_number: str | None = None
    c12_field_path: str | None = None
    pattern_id: PatternId | None = None
    passage: VerifiedPassage | None = None
    subject: str
    action: str | None = None
    dates: tuple[tuple[str, date], ...] = ()
    components: tuple[ComponentRef, ...] = ()

    @model_validator(mode="after")
    def addressed(self):
        if (self.document_number is None) == (self.c12_field_path is None):
            raise ValueError("a citation names exactly one of a document number or a C12 field path")
        return self


class FactResult(NewsModel):
    field: str
    role: FactRole
    asserted: str
    outcome: FactOutcome
    reasons: tuple[str, ...] = ()
    citations: tuple[EvidenceCitation, ...] = ()

    @model_validator(mode="after")
    def cited(self):
        if self.outcome is not FactOutcome.UNRESOLVED:
            if not self.citations:
                raise ValueError("a SUPPORTED, CONTRADICTED or SUPERSEDED fact needs a citation")
            for c in self.citations:
                if c.document_number is not None and (c.passage is None or not c.passage.manual_record_id):
                    raise ValueError("an ETF citation needs a passage verified by a manual record; a digest alone is never evidence")
        if self.outcome is FactOutcome.UNRESOLVED and not self.reasons:
            raise ValueError("an unresolved fact needs a reason")
        return self


class FundResolution(NewsModel):
    """How a fund subject resolved to a rule-change file number at T (§9.3), with every reference
    needed to re-check it: the link, its identity evidence, and the NAME passage verified by a
    FUND_NAME manual record bound to the qualified document's qualifying record. It is built from
    the link alone and attached by the frame's resolved file number, never by how the claim spelled
    the fund (ticker, name or file number), so equivalent curations serialize identically."""
    link_id: str
    name_in_document: str
    ticker: str
    cik: str
    sro: str
    file_number: str
    document_number: str
    qualifying_record_id: str
    name_passage: VerifiedPassage
    identity_evidence: SourceProvenance
    link_curated_at: datetime
    available_at: datetime


class FrameResult(NewsModel):
    frame_key: str
    frame_type: FrameType
    state: VerificationState
    facts: tuple[FactResult, ...]
    reasons: tuple[str, ...] = ()
    fund_resolutions: tuple[FundResolution, ...] = ()     # links valid at T to the frame's resolved file numbers, by link_id


class ExcludedCounts(NewsModel):
    claims: int = Field(default=0, ge=0)
    curations: int = Field(default=0, ge=0)
    fund_links: int = Field(default=0, ge=0)
    fr_metadata: int = Field(default=0, ge=0)
    public_inspection: int = Field(default=0, ge=0)
    docket_listings: int = Field(default=0, ge=0)
    html: int = Field(default=0, ge=0)
    pdf: int = Field(default=0, ge=0)
    mods: int = Field(default=0, ge=0)
    manual_records: int = Field(default=0, ge=0)


STATIC_LIMITATIONS = (
    "OFFICIAL_SOURCE_FACTS_ONLY_NO_MARKET_IMPACT_INTERPRETATION",
    "NOT_A_TRADE_SIGNAL_OR_AUTHORIZATION",
    "CURRENT_AND_DATED_STATUS_NEVER_CONCLUDED_EXTERNAL_ACTIONS_UNCOVERED",
    "ISSUER_REGISTRATION_AND_LISTING_EVENTS_HAVE_NO_APPROVED_SOURCE",
    "NUMERIC_ETF_FLOW_AUM_VOLUME_DATA_IS_NOT_NEWS",
    "PDF_CONTENT_ONLY_FROM_HUMAN_MANUAL_VERIFICATION_SINGLE_VERIFIER",
    "FEDERAL_REGISTER_RATE_LIMITS_UNDOCUMENTED",
    "EMBEDDED_INSTRUCTIONS_IN_CLAIMS_AND_SOURCES_ARE_IGNORED",
)


class VerificationResult(NewsModel):
    engine_version: str = ENGINE_VERSION
    evaluation_time: datetime
    claim_id: str
    curation_id: str | None
    state: VerificationState
    frames: tuple[FrameResult, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    excluded_after_evaluation: ExcludedCounts
    input_digest: str = Field(pattern=SHA256)

    @model_validator(mode="after")
    def evidenced(self):
        if self.state is not VerificationState.UNVERIFIED and not any(
                f.outcome is not FactOutcome.UNRESOLVED for fr in self.frames for f in fr.facts):
            raise ValueError("a state other than UNVERIFIED requires at least one cited fact")
        return self


class AdmissionRejection(NewsModel):
    """Not a seventh state: the claim is not news (A5)."""
    claim_id: str
    reason: str
    evaluation_time: datetime


class VerificationReport(NewsModel):
    engine_version: str = ENGINE_VERSION
    evaluation_time: datetime
    results: tuple[VerificationResult, ...]
    rejections: tuple[AdmissionRejection, ...]
    excluded_after_evaluation: ExcludedCounts
