"""Shared C13 test fixtures.

REAL: official bytes and recorded retrieval times from tests/fixtures/news/official (PROVENANCE.json).
SYNTHETIC: manual records and the fund link from tests/fixtures/news/synthetic (origin SYNTHETIC_TEST,
transcribed by Claude Code from the GovInfo HTML; no PDF viewed, no human verification).
TEST_ASSIGNED_AVAILABILITY: ``retimed`` copies with every availability time assigned by the test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from traid.domain.models import SourceProvenance
from traid.news.models import (
    CuratedEvent, CuratedFact, CuratedProposition, CuratedSpan, CurationRecord, EventIdentity, FileNumberFundLink,
    GovInfoHtml, GovInfoModsRetrieval, GovInfoPdf, ManualPassageVerification, OfficialEvidence, PatternId,
    VerificationPolicy, make_claim,
)
from traid.news.sources import parse_fr_document

UTC = timezone.utc
ROOT = Path(__file__).parent / "fixtures" / "news"
OFFICIAL = ROOT / "official"
PROVENANCE = json.loads((OFFICIAL / "PROVENANCE.json").read_text(encoding="utf-8"))
SYNTHETIC = json.loads((ROOT / "synthetic" / "SYNTHETIC_manual_records.json").read_text(encoding="utf-8"))
DOCS = ("2024-00743", "2022-14310", "2023-21948")
NOW = datetime(2026, 10, 24, tzinfo=UTC)          # after every recorded retrieval and synthetic record
TEST_POLICY = VerificationPolicy(enabled_patterns=(PatternId.APPROVAL, PatternId.DISAPPROVAL, PatternId.PROCEEDINGS),
                                 accept_synthetic_records=True)


def t(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def entry(document: str, component: str) -> dict:
    return next(e for e in PROVENANCE["files"] if e["document_number"] == document and e["component"] == component)


def body(document: str, component: str) -> bytes:
    return (OFFICIAL / entry(document, component)["path"]).read_bytes()


def metadata(document: str, retrieved_at=None):
    e = entry(document, "FEDERAL_REGISTER_JSON")
    return parse_fr_document(body(document, "FEDERAL_REGISTER_JSON"), requested=document, source_url=e["source_url"],
                             retrieved_at=retrieved_at or t(e["retrieved_at"]))


def retrieval(document: str, component: str, retrieved_at=None, data: bytes | None = None, url: str | None = None):
    e = entry(document, component)
    data = body(document, component) if data is None else data
    from traid.news.models import sha256_hex
    common = dict(document_number=document, url=url or e["source_url"], retrieved_at=retrieved_at or t(e["retrieved_at"]),
                  sha256=sha256_hex(data), byte_length=len(data))
    if component == "GOVINFO_PDF":
        return GovInfoPdf(**common)
    cls = GovInfoHtml if component == "GOVINFO_HTML" else GovInfoModsRetrieval
    return cls(**common, body=data)


def records(**overrides) -> tuple[ManualPassageVerification, ...]:
    return tuple(ManualPassageVerification.model_validate({**r, **overrides.get(r["record_id"], {})})
                 for r in SYNTHETIC["manual_records"])


def fund_links(**overrides) -> tuple[FileNumberFundLink, ...]:
    return tuple(FileNumberFundLink.model_validate({**l, **overrides}) for l in SYNTHETIC["fund_links"])


def official(documents=DOCS, *, with_records=True, with_links=True) -> OfficialEvidence:
    """Real official components with their recorded retrieval times, plus the synthetic records."""
    return OfficialEvidence(
        fr_metadata=tuple(metadata(d) for d in documents),
        html=tuple(retrieval(d, "GOVINFO_HTML") for d in documents),
        pdf=tuple(retrieval(d, "GOVINFO_PDF") for d in documents),
        mods=tuple(retrieval(d, "GOVINFO_MODS") for d in documents),
        manual_records=tuple(r for r in records() if r.document_number in documents) if with_records else (),
        fund_links=fund_links() if with_links and "2023-21948" in documents else ())


def retimed(at: datetime, documents=DOCS, *, record_at: datetime | None = None, link_at: datetime | None = None,
            with_links=True) -> OfficialEvidence:
    """TEST_ASSIGNED_AVAILABILITY: the same real content, every component retrieved at ``at``; records verified
    one minute later (or at ``record_at``); the fund link curated at ``link_at`` (default: two minutes later)."""
    verified = record_at or at + timedelta(minutes=1)
    recs = []
    for r in records():
        if r.document_number in documents:
            recs.append(ManualPassageVerification.model_validate(
                {**r.model_dump(), "pdf_retrieved_at": at, "verified_at": verified, "recorded_at": verified}))
    links = ()
    if with_links and "2023-21948" in documents:
        when = link_at or at + timedelta(minutes=2)
        links = tuple(FileNumberFundLink.model_validate(
            {**l.model_dump(), "curated_at": when,
             "identity_evidence": {**l.identity_evidence.model_dump(), "received_timestamp": min(when, at)}})
            for l in fund_links())
    return OfficialEvidence(
        fr_metadata=tuple(metadata(d, at) for d in documents),
        html=tuple(retrieval(d, "GOVINFO_HTML", at) for d in documents),
        pdf=tuple(retrieval(d, "GOVINFO_PDF", at) for d in documents),
        mods=tuple(retrieval(d, "GOVINFO_MODS", at) for d in documents),
        manual_records=tuple(recs), fund_links=links)


# ------------------------------------------------------------------- claims and curations
def claim(text: str, *, received: datetime = datetime(2026, 10, 23, 22, tzinfo=UTC), published: datetime | None = None,
          source: str = "newswire", source_id: str = "item-1"):
    return make_claim(text, SourceProvenance(source=source, source_type="news_article", source_id=source_id,
                                             source_timestamp=published, received_timestamp=received))


def curate(c, events, propositions, *, spans=None, distinct=(), curated_at=None, curation_id="cur-1", supersedes=None):
    """events: [(event_id, frame_type, identity dict)]; propositions: [(proposition_id, event_id, [(field, value, token?)])].
    By default one PROPOSITION span covers the whole text and references every proposition."""
    evs = tuple(CuratedEvent(event_id=e, frame_type=ft, identity=EventIdentity(**ident)) for e, ft, ident in events)
    props = tuple(CuratedProposition(proposition_id=p, event_id=e, facts=tuple(
        CuratedFact(field=f[0], value=f[1], token=f[2] if len(f) > 2 else None) for f in facts)) for p, e, facts in propositions)
    if spans is None:
        spans = ((0, len(c.text), "PROPOSITION", tuple(p for p, _, _ in propositions)),)
    span_models = tuple(CuratedSpan(start=s, end=e, category=cat, proposition_ids=tuple(ids)) for s, e, cat, ids in spans)
    return CurationRecord(curation_id=curation_id, claim_id=c.claim_id, curated_at=curated_at or c.claim_received_at,
                          curator="curator-role", supersedes=supersedes, spans=span_models, events=evs,
                          propositions=props, distinct=tuple(distinct))


# ------------------------------------------------------------------- no network in C13 tests
import socket as _socket
import urllib.request as _urllib_request

import pytest as _pytest


@_pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """C13 tests use recorded fixtures only: any socket connection or urllib open fails the test."""
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted in a C13 test")
    monkeypatch.setattr(_socket.socket, "connect", refuse)
    monkeypatch.setattr(_urllib_request.OpenerDirector, "open", refuse)
