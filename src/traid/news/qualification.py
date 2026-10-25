"""Qualification of an SEC Federal Register document at T, and fund links (design §6.3-§6.7, §7.4, §9.3).

A document qualifies only through a manual verification record of the rendered official PDF,
bound to a TraID PDF retrieval's SHA-256 and cross-checked by machine against the GovInfo HTML
(literal, after N), the Federal Register metadata and the structurally parsed GovInfo MODS. PDF
bytes are never read. Every input passed here is already filtered to availability <= T.

Availability is the layered DAG of §7.4: level 1 (document) depends only on its own components and
its qualifying record; level 2 (fund link) on its curation, identity evidence, FUND_NAME record and
the level-1 document. Disqualifiers (corrections, conflicting retrievals or record heads) are
separate predicates and never change any availability value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from traid.news.models import (
    AbsentCheck, ComponentKind, ComponentRef, FileNumberFundLink, FrMetadataRecord, FrPublicInspectionRecord,
    GovInfoHtml, GovInfoModsRetrieval, GovInfoPdf, ManualPassageVerification, PassageCheck, PassageKind,
    QualifiedDocument, RecordOrigin, RecordPurpose, VerificationPolicy, VerifiedPassage, canonical_json, sha256_hex,
)
from traid.news.mods import mods_record
from traid.news.patterns import classify
from traid.news.sources import SEC_AGENCY, govinfo_url, validate_govinfo_url
from traid.news.text import (
    HEADING_MARK, SECTION_OF_TYPE, TERMINATOR_MARK, WEEKDAYS, canonical_file_number, docket_identifiers, html_pages,
    html_text, normalize_passage, page_at, parse_date_line, parse_heading, parse_html_header, parse_page_header,
    parse_terminator,
)

REQUIRED_KINDS = (PassageKind.PAGE_HEADER, PassageKind.HEADING, PassageKind.DATE_LINE, PassageKind.OPERATIVE,
                  PassageKind.TERMINATOR)
LITERAL_ORDER = (PassageKind.HEADING, PassageKind.DATE_LINE, PassageKind.OPERATIVE, PassageKind.TERMINATOR,
                 PassageKind.STATED_DATE)
CONFIRMATIONS = {AbsentCheck.NO_SECOND_OPERATIVE_SENTENCE, AbsentCheck.NO_SECOND_HEADING, AbsentCheck.NO_SECOND_TERMINATOR}
SIGNATURE = "By the Commission."


@dataclass(frozen=True)
class Qualification:
    document_number: str
    document: QualifiedDocument | None
    reason: str | None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Html:
    retrieval: GovInfoHtml
    text: str
    pages: list
    region: tuple[int, int] | None


def _bound_fields(m: FrMetadataRecord) -> str:
    return canonical_json(m.model_dump(include={"document_number", "citation", "volume", "start_page", "end_page",
                                                "publication_date", "document_type", "agency_slugs", "docket_ids",
                                                "title"}))


def _heads(records: list[ManualPassageVerification]) -> list[ManualPassageVerification]:
    superseded = {r.supersedes for r in records if r.supersedes}
    return [r for r in records if r.record_id not in superseded]


def _cyclic(records: list[ManualPassageVerification]) -> bool:
    """A supersedes cycle (a self-cycle included) among these records. Each record supersedes at most
    one other, so following ``supersedes`` from every record finds every cycle; a target outside the
    records ends the walk."""
    target = {r.record_id: r.supersedes for r in records}
    for start in sorted(target):
        seen, at = set(), start
        while at in target and at not in seen:
            seen.add(at)
            at = target[at]
        if at in seen:
            return True
    return False


def _content(r: ManualPassageVerification) -> str:
    passages = sorted((p.kind.value, normalize_passage(p.text), p.fr_printed_page) for p in r.passages)
    return canonical_json([passages, sorted(a.value for a in r.absent_checks), r.purpose.value])


def _record_ref(r: ManualPassageVerification) -> ComponentRef:
    return ComponentRef(kind=ComponentKind.MANUAL_RECORD, url=f"manual-record:{r.record_id}",
                        sha256=sha256_hex(canonical_json(r.model_dump(mode="python"))), retrieved_at=r.available_at)


def _prepare_html(retrieval: GovInfoHtml, first_page: int) -> _Html | str:
    try:
        raw = retrieval.body.decode("utf-8")
    except UnicodeDecodeError:
        return "CONFLICTING_OFFICIAL_EVIDENCE:HTML_ENCODING"
    text = html_text(raw)
    if text.count(HEADING_MARK) != 1 or text.count(TERMINATOR_MARK) != 1:
        return _Html(retrieval, text, html_pages(raw, first_page), None)
    start = text.index(HEADING_MARK)
    end = text.index("]", text.index(TERMINATOR_MARK)) + 1
    return _Html(retrieval, text, html_pages(raw, first_page), (start, end) if start < end else None)


def _locate(h: _Html, passage: str) -> int | None:
    """Offset of the passage's single occurrence inside the document region, else None."""
    if h.region is None or not passage or h.text.count(passage) != 1:
        return None
    at = h.text.index(passage)
    return at if h.region[0] <= at and at + len(passage) <= h.region[1] else None


def _anchored(h: _Html, anchor: str, operative_at: int, date_line_at: int) -> bool:
    start, end = h.region
    if not date_line_at < operative_at:
        return False
    if anchor == "BEFORE_SIGNATURE":
        region = h.text[start:end]
        return region.count(SIGNATURE) == 1 and operative_at < start + region.index(SIGNATURE)
    return True


def _page_header(text: str, meta: FrMetadataRecord, mods, h: _Html) -> tuple[str | None, tuple | None]:
    parsed = parse_page_header(text)
    if parsed is None:
        return "PAGE_HEADER_UNPARSEABLE", None
    page, volume, issue, weekday, day, section = parsed
    if day is None or WEEKDAYS[day.weekday()] != weekday:
        return "PAGE_HEADER_WEEKDAY_OR_DATE_INVALID", None
    header = parse_html_header(h.text)
    if header is None:
        return "HTML_HEADER_UNPARSEABLE", None
    checks = {
        "VOLUME": volume == meta.volume == mods.volume == header["volume"],
        "ISSUE": issue == mods.issue == header["issue"],             # FR JSON has no issue field [S]
        "PAGE": page == meta.start_page == mods.start_page == header["start"],
        "DATE": day == meta.publication_date == mods.date_issued == header["date"],
        "SECTION": section == SECTION_OF_TYPE.get(meta.document_type) == header["section"],
    }
    bad = [k for k, ok in checks.items() if not ok]
    return ("PAGE_HEADER_MISMATCH:" + ",".join(bad) if bad else None), parsed


@dataclass(frozen=True)
class _Examined:
    record: ManualPassageVerification
    passages: dict
    header: tuple
    located: dict
    heading: tuple
    order_date: object
    operative: str
    pattern: object


def _examine(record: ManualPassageVerification, N: str, meta: FrMetadataRecord, mods, htmls: list,
             public_inspection: list[FrPublicInspectionRecord], policy: VerificationPolicy) -> _Examined | str:
    """One bound record against every retained machine source; the first failing check's reason."""
    passages = {p.kind: p for p in record.passages}
    missing = [k.value for k in REQUIRED_KINDS if k not in passages]
    if missing:
        return "RECORD_INCOMPLETE:" + ",".join(missing)
    for h in htmls:
        if isinstance(h, str):
            return h
        if h.region is None:
            return "CONFLICTING_OFFICIAL_EVIDENCE:HTML_REGION"
    header = None
    for h in htmls:                                # every HTML copy, not only the first
        why, parsed = _page_header(passages[PassageKind.PAGE_HEADER].text, meta, mods, h)
        if why:
            return why
        header = header or parsed
    located: dict[PassageKind, int] = {}
    for kind in LITERAL_ORDER:
        if kind not in passages:
            continue
        text = normalize_passage(passages[kind].text)
        offsets = [_locate(h, text) for h in htmls]
        if any(o is None for o in offsets):
            return f"CONFLICTING_OFFICIAL_EVIDENCE:{kind.value}"
        located[kind] = offsets[0]
    heading = parse_heading(passages[PassageKind.HEADING].text)
    release, files = docket_identifiers(meta.docket_ids)
    if heading is None or heading[0] != release or sorted(heading[1]) != sorted(files):
        return "IDENTIFIER_MISMATCH:HEADING"
    terminator = parse_terminator(passages[PassageKind.TERMINATOR].text)
    if terminator is None or terminator[0] != N:
        return "IDENTIFIER_MISMATCH:TERMINATOR"
    if any(not meta.start_page <= p.fr_printed_page <= meta.end_page for p in record.passages):
        return "PASSAGE_OUTSIDE_DOCUMENT_PAGES"
    order_date = parse_date_line(passages[PassageKind.DATE_LINE].text)
    if order_date is None:
        return "DATE_LINE_UNPARSEABLE"
    if not CONFIRMATIONS <= set(record.absent_checks) or AbsentCheck.SECOND_OPERATIVE_SENTENCE_RENDERED in record.absent_checks:
        return "UNCLASSIFIED_SEC_NOTICE"
    operative = normalize_passage(passages[PassageKind.OPERATIVE].text)
    matches = classify(operative)
    if len(matches) != 1:
        return "UNCLASSIFIED_SEC_NOTICE"
    pattern = matches[0]
    if pattern.pattern_id not in policy.enabled_patterns:
        return "PATTERN_NOT_FIXTURE_VERIFIED"
    if any(not _anchored(h, pattern.anchor, _locate(h, operative), _locate(h, normalize_passage(passages[PassageKind.DATE_LINE].text)))
           for h in htmls):
        return "CONFLICTING_OFFICIAL_EVIDENCE:OPERATIVE_ANCHOR"
    # public inspection (optional component): every record's filed_at must equal the FILED line
    if public_inspection:
        if len({p.filed_at for p in public_inspection}) != 1:
            return "CONFLICTING_OFFICIAL_EVIDENCE:PUBLIC_INSPECTION"
        for pi in public_inspection:
            local = datetime.fromisoformat(pi.filed_at_source.replace("Z", "+00:00"))
            if (local.date(), local.time().replace(second=0, microsecond=0)) != (terminator[1], terminator[2]) \
                    or local.second or local.microsecond:
                return "CONFLICTING_OFFICIAL_EVIDENCE:FILED_LINE"
    return _Examined(record, passages, header, located, heading, order_date, operative, pattern)


def is_correction_number(document_number: str) -> bool:
    """A Federal Register correction document number, e.g. C1-2024-26524."""
    return re.fullmatch(r"C\d+-\d{4}-\d{5}", document_number) is not None


def qualify_document(document_number: str, *, metadata: list[FrMetadataRecord], mods: list[GovInfoModsRetrieval],
                     html: list[GovInfoHtml], pdf: list[GovInfoPdf], public_inspection: list[FrPublicInspectionRecord],
                     records: list[ManualPassageVerification], policy: VerificationPolicy,
                     corrections: list[FrMetadataRecord] = ()) -> Qualification:
    """``corrections``: metadata of OTHER documents, available at T, whose ``correction_of`` names this one."""
    N = document_number

    def no(reason: str, limitations=()) -> Qualification:
        return Qualification(N, None, reason, tuple(limitations))

    # ---- level-0 components (each list is already filtered to availability <= T)
    if not metadata:
        return no("METADATA_NOT_AVAILABLE_AT_T")
    if any(SEC_AGENCY not in m.agency_slugs for m in metadata):
        return no("NOT_SEC_DOCUMENT")
    # a correction known at T, from this document's own metadata or from the correcting document's
    if is_correction_number(N) or any(m.corrections or m.correction_of for m in metadata) \
            or any((m.correction_of or "").strip() == N and m.document_number != N for m in corrections):
        return no("CORRECTION_CONTENT_UNVERIFIED")
    if len({_bound_fields(m) for m in metadata}) != 1:
        return no("CONFLICTING_OFFICIAL_EVIDENCE:METADATA")
    meta = min(metadata, key=lambda m: (m.retrieved_at, m.payload_digest))
    D = meta.publication_date
    if (meta.pdf_url is not None and meta.pdf_url != govinfo_url("PDF", D, N)) or \
            (meta.mods_url is not None and meta.mods_url != govinfo_url("MODS", D, N)):
        return no("CONFLICTING_OFFICIAL_EVIDENCE:METADATA_URL")

    url_problems = sorted({why for kind, items in (("MODS", mods), ("HTML", html), ("PDF", pdf)) for r in items
                           if (why := validate_govinfo_url(r.url, kind, D, N)) != "OK"})
    if url_problems:
        return no(url_problems[0])
    bound_mods = mods_record(mods, meta)
    if isinstance(bound_mods, str):
        return no(bound_mods)
    if not html:
        return no("HTML_NOT_AVAILABLE_AT_T")
    if not pdf:
        return no("PDF_NOT_AVAILABLE_AT_T")

    # ---- level 0': manual records (QUALIFYING heads bound to a PDF retrieval)
    limitations = []
    usable = []
    for r in records:
        if r.purpose is not RecordPurpose.QUALIFYING:
            continue
        if r.origin is RecordOrigin.SYNTHETIC_TEST and not policy.accept_synthetic_records:
            continue
        usable.append(r)
    if not usable:
        return no("MANUAL_VERIFICATION_NOT_AVAILABLE_AT_T")
    by_id: dict[str, ManualPassageVerification] = {}
    for r in usable:                               # records are append-only: one id names one record
        if by_id.setdefault(r.record_id, r) != r:
            return no("CONFLICTING_MANUAL_VERIFICATIONS")
    retrievals ={(p.sha256, p.retrieved_at) for p in pdf}
    bound = [r for r in usable if r.pdf_url == govinfo_url("PDF", D, N) and (r.pdf_sha256, r.pdf_retrieved_at) in retrievals]
    if not bound:
        return no("NO_MATCHING_PDF_RETRIEVAL")
    by_digest: dict[str, list] = {}
    for r in bound:
        by_digest.setdefault(r.pdf_sha256, []).append(r)
    # supersession is resolved only after admission and PDF binding, and only within one
    # (document, pdf_sha256): an unbound record, or one bound to other bytes, never removes a record.
    # A cycle is detected before anything is removed: cyclic records never vanish silently, even when
    # another record would survive as a head.
    for digest, group in by_digest.items():
        if _cyclic(group):
            return no("CONFLICTING_MANUAL_VERIFICATIONS")
        by_digest[digest] = _heads(group)          # acyclic: at least one head remains
    for heads in by_digest.values():
        if len({_content(r) for r in heads}) > 1:
            return no("CONFLICTING_MANUAL_VERIFICATIONS")
    digests = sorted({p.sha256 for p in pdf}, key=lambda d: (min(p.retrieved_at for p in pdf if p.sha256 == d), d))
    if any(d not in by_digest for d in digests):
        return no("CONFLICTING_OFFICIAL_EVIDENCE:PDF_REVISION_UNVERIFIED")
    if len({canonical_json([(p.kind.value, normalize_passage(p.text)) for p in sorted(by_digest[d][0].passages, key=lambda p: p.kind.value)])
            for d in digests}) > 1:
        return no("CONFLICTING_OFFICIAL_EVIDENCE:PDF_REVISION")
    if len(digests) > 1:
        limitations.append(f"NONMATERIAL_REVISION:{N}")
    record = min(by_digest[digests[0]], key=lambda r: r.record_id)

    if any(r.origin is RecordOrigin.SYNTHETIC_TEST for heads in by_digest.values() for r in heads):
        limitations.append("SYNTHETIC_MANUAL_RECORD_NOT_HUMAN_VERIFIED")

    # ---- every retained record and retrieval is checked before one is chosen to represent them,
    # so a disqualifier in any of them (a later revision's record, a later HTML copy, a later
    # public-inspection record) cannot be hidden by deduplication or revision classification
    htmls = [_prepare_html(h, meta.start_page) for h in sorted(html, key=lambda h: (h.retrieved_at, h.sha256))]
    examined = [_examine(r, N, meta, bound_mods, htmls, public_inspection, policy)
                for r in sorted({r.record_id: r for heads in by_digest.values() for r in heads}.values(),
                                key=lambda r: r.record_id)]
    failures = sorted(x for x in examined if isinstance(x, str))
    if failures:                                   # order-independent: the smallest reason
        return no(failures[0], limitations)
    x = next(x for x in examined if x.record is record)
    passages, header, located, heading, order_date, operative, pattern = \
        x.passages, x.header, x.located, x.heading, x.order_date, x.operative, x.pattern
    pi = min(public_inspection, key=lambda p: (p.retrieved_at, p.payload_digest)) if public_inspection else None

    # ---- the qualified document (level 1 availability: own components and qualifying record only)
    first_html = htmls[0]
    verified = []
    for kind, p in sorted(passages.items(), key=lambda kp: kp[0].value):
        if kind is PassageKind.PAGE_HEADER:
            verified.append(VerifiedPassage(kind=kind, normalized_text=normalize_passage(p.text),
                                            check=PassageCheck.STRUCTURED_METADATA, parsed_header=header,
                                            pdf_location=(p.pdf_page_index, p.fr_printed_page), manual_record_id=record.record_id))
            continue
        at = located[kind]
        verified.append(VerifiedPassage(kind=kind, normalized_text=normalize_passage(p.text), check=PassageCheck.LITERAL_HTML,
                                        html_location=(page_at(first_html.pages, at), at),
                                        pdf_location=(p.pdf_page_index, p.fr_printed_page), manual_record_id=record.record_id))
    pdf_first = min((p for p in pdf if p.sha256 == record.pdf_sha256), key=lambda p: p.retrieved_at)
    components = [
        ComponentRef(kind=ComponentKind.FR_METADATA, url=meta.source_url, sha256=meta.payload_digest, retrieved_at=meta.retrieved_at),
        ComponentRef(kind=ComponentKind.GOVINFO_MODS, url=bound_mods.url, sha256=bound_mods.sha256, retrieved_at=bound_mods.retrieved_at),
        ComponentRef(kind=ComponentKind.GOVINFO_HTML, url=first_html.retrieval.url, sha256=first_html.retrieval.sha256,
                     retrieved_at=first_html.retrieval.retrieved_at),
        ComponentRef(kind=ComponentKind.GOVINFO_PDF, url=pdf_first.url, sha256=pdf_first.sha256, retrieved_at=pdf_first.retrieved_at),
        _record_ref(record),
    ]
    if pi is not None:
        components.append(ComponentRef(kind=ComponentKind.FR_PUBLIC_INSPECTION, url=pi.source_url, sha256=pi.payload_digest,
                                       retrieved_at=pi.retrieved_at))
    accelerated = operative.endswith("approved on an accelerated basis.")
    pi_local = datetime.fromisoformat(pi.filed_at_source.replace("Z", "+00:00")).date() if pi else None
    document = QualifiedDocument(
        document_number=N, pattern_id=pattern.pattern_id, release_no=heading[0], file_numbers=tuple(sorted(heading[1])),
        order_or_notice_date=order_date, accelerated=accelerated, start_page=meta.start_page, end_page=meta.end_page,
        fr_publication_date=meta.publication_date,
        public_inspection_filed_at=pi.filed_at if pi else None, public_inspection_local_date=pi_local,
        passages=tuple(verified), components=tuple(sorted(components, key=lambda c: (c.kind.value, c.url))),
        qualifying_record_id=record.record_id, record_origin=record.origin,
        available_at=max([c.retrieved_at for c in components] + [record.available_at]))
    return Qualification(N, document, None, tuple(sorted(set(limitations))))


# ------------------------------------------------------------------- fund links (level 2)
@dataclass(frozen=True)
class LinkCheck:
    link: FileNumberFundLink
    valid: bool
    reason: str | None
    available_at: datetime | None
    name_passage: VerifiedPassage | None = None


def check_fund_link(link: FileNumberFundLink, *, documents: dict[str, QualifiedDocument],
                    records: list[ManualPassageVerification], html: list[GovInfoHtml],
                    policy: VerificationPolicy) -> LinkCheck:
    def bad(why: str) -> LinkCheck:
        return LinkCheck(link, False, f"FUND_LINK_UNVERIFIED:{why}", None)

    doc = documents.get(link.document_number)
    if doc is None:
        return bad("DOCUMENT_NOT_QUALIFIED")
    file_number = canonical_file_number(link.file_number)
    if file_number is None or file_number != link.file_number or file_number not in doc.file_numbers:
        return bad("FILE_NUMBER_NOT_IN_DOCUMENT_HEADING")
    if file_number.split("-")[1] != link.sro.upper():
        return bad("SRO_NOT_THE_FILING_EXCHANGE")
    name = [r for r in records if r.record_id == link.name_record_id and r.purpose is RecordPurpose.FUND_NAME]
    if len(name) != 1:
        return bad("NAME_RECORD_NOT_AVAILABLE_AT_T")
    record = name[0]
    if record.origin is RecordOrigin.SYNTHETIC_TEST and not policy.accept_synthetic_records:
        return bad("NAME_RECORD_NOT_AVAILABLE_AT_T")
    qualifying = next(c for c in doc.components if c.kind is ComponentKind.GOVINFO_PDF)
    if record.document_number != doc.document_number or record.qualifying_record_id != doc.qualifying_record_id \
            or record.pdf_sha256 != qualifying.sha256:
        return bad("NAME_RECORD_NOT_BOUND_TO_QUALIFYING_RECORD")
    passage = record.passages[0]
    text = normalize_passage(passage.text)
    if normalize_passage(link.name_in_document) not in text:
        return bad("NAME_NOT_IN_NAME_PASSAGE")
    if not doc.start_page <= passage.fr_printed_page <= doc.end_page:
        return bad("PASSAGE_OUTSIDE_DOCUMENT_PAGES")
    located = []
    for h in sorted((h for h in html if h.document_number == doc.document_number), key=lambda h: (h.retrieved_at, h.sha256)):
        prepared = _prepare_html(h, doc.start_page)
        at = None if isinstance(prepared, str) else _locate(prepared, text)
        located.append(None if at is None else (page_at(prepared.pages, at), at))
    if not located or any(x is None for x in located):
        return bad("NAME_PASSAGE_NOT_IN_HTML")
    available = max(link.curated_at, link.identity_evidence.received_timestamp, record.available_at, doc.available_at)
    verified = VerifiedPassage(kind=PassageKind.NAME, normalized_text=text, check=PassageCheck.LITERAL_HTML,
                               html_location=located[0], pdf_location=(passage.pdf_page_index, passage.fr_printed_page),
                               manual_record_id=record.record_id)
    return LinkCheck(link, True, None, available, verified)
