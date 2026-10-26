"""Structural GovInfo MODS validation and identity binding (design R4 §6.7, plus acceptance test E1).

The record is parsed with the standard-library ``xml.etree.ElementTree`` (expat) into an element
tree; no field is ever located by text search. DTDs and entity declarations are refused before and
during parsing, so nothing is expanded or fetched. Matching is by namespace URI. Comments,
processing instructions and CDATA are never evidence; a comment or PI inside a bound field is
detected. Every container on a designated path, and every bound field, must occur exactly once
under its parent (E1). Every outcome is a field record or one deterministic reason; no input raises.
"""
from __future__ import annotations

from datetime import date
import json
import re
import xml.etree.ElementTree as ET

from traid.news.models import FrMetadataRecord, GovInfoMods, GovInfoModsRetrieval

MODS_NS = "http://www.loc.gov/mods/v3"
MAX_BYTES = 1 * 2**20
MISSING = "MODS_FIELD_MISSING_OR_DUPLICATED"


def q(local: str) -> str:
    return f"{{{MODS_NS}}}{local}"


class _DtdRefused(Exception):
    pass


class _Builder(ET.TreeBuilder):
    """Keeps comments and PIs as non-element nodes so one inside a bound field is detected; they never
    match a MODS element name. Any DOCTYPE aborts the parse."""
    def __init__(self):
        super().__init__(insert_comments=True, insert_pis=True)

    def doctype(self, name, pubid, system):
        raise _DtdRefused()


# field -> (scope, direct-child steps as (local name, required attributes), leaf grammar, exactly one?)
FIELDS = {
    "doc":         ("granule", [("identifier", {"type": "FR Doc No."})], r"\d{4}-\d{5}", True),
    "citation":    ("granule", [("identifier", {"type": "FR citation"})], r"[1-9]\d{0,3} FR [1-9]\d{0,5}", True),
    "departments": ("granule", [("identifier", {"type": "department code"})], r"\S(?:[^\x00-\x1f\x7f]{0,254}\S)?", False),
    "start":       ("granule", [("part", {}), ("extent", {"unit": "pages"}), ("start", {})], r"[1-9]\d{0,5}", True),
    "end":         ("granule", [("part", {}), ("extent", {"unit": "pages"}), ("end", {})], r"[1-9]\d{0,5}", True),
    "volume":      ("host", [("extension", {}), ("volume", {})], r"[1-9]\d{0,3}", True),
    "issue":       ("host", [("extension", {}), ("issue", {})], r"[1-9]\d{0,3}", True),
    "date":        ("host", [("originInfo", {}), ("dateIssued", {})], r"\d{4}-\d{2}-\d{2}", True),
    "host_start":  ("host", [("part", {"type": "issue"}), ("extent", {"unit": "pages"}), ("start", {})], r"[1-9]\d{0,5}", True),
    "host_end":    ("host", [("part", {"type": "issue"}), ("extent", {"unit": "pages"}), ("end", {})], r"[1-9]\d{0,5}", True),
    "package":     ("host", [("recordInfo", {}), ("recordIdentifier", {})], r"FR-\d{4}-\d{2}-\d{2}", True),
}
# element signatures allowed only at their designated paths (anywhere else: unexpected nesting)
SIGNATURES = {"doc": ("identifier", {"type": "FR Doc No."}), "citation": ("identifier", {"type": "FR citation"}),
              "departments": ("identifier", {"type": "department code"}), "volume": ("volume", {}),
              "issue": ("issue", {}), "date": ("dateIssued", {}), "package": ("recordIdentifier", {})}
# E1: containers on designated paths; each exactly once under its parent (the parent must be unique too)
CONTAINERS = (("granule", [("part", {})]), ("granule", [("part", {}), ("extent", {"unit": "pages"})]),
              ("host", [("extension", {})]), ("host", [("originInfo", {})]),
              ("host", [("part", {"type": "issue"})]), ("host", [("part", {"type": "issue"}), ("extent", {"unit": "pages"})]),
              ("host", [("recordInfo", {})]))


def _is(el, local: str, attrs: dict) -> bool:
    return el.tag == q(local) and all(el.get(k) == v for k, v in attrs.items())


def _walk(parent, steps) -> list:
    nodes = [parent]
    for local, attrs in steps:
        nodes = [c for n in nodes for c in n if _is(c, local, attrs)]   # direct children only
    return nodes


def _container_children(parent, local: str) -> list:
    """Every direct child with this element name, whatever its attributes (a second part, extent, ...)."""
    return [c for c in parent if c.tag == q(local)]


def _decl_encoding_ok(text: str) -> bool:
    m = re.match(r"﻿?<\?xml\b[^>]*?\bencoding\s*=\s*([\"'])([^\"']*)\1", text)
    return m is None or m.group(2).lower() in ("utf-8", "utf8")


def parse_mods(body: bytes, *, prescan: bool = True) -> dict | str:
    """Scoped MODS fields, or a deterministic rejection reason. Never raises on input."""
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        return "MODS_XML_TOO_LARGE"
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return "MODS_XML_ENCODING_REJECTED"
    if not _decl_encoding_ok(text):
        return "MODS_XML_ENCODING_REJECTED"
    if prescan and ("<!DOCTYPE" in text or "<!ENTITY" in text):
        return "MODS_XML_DTD_OR_ENTITY_REJECTED"
    parser = ET.XMLParser(target=_Builder())
    try:
        parser.feed(body)
        root = parser.close()
    except _DtdRefused:
        return "MODS_XML_DTD_OR_ENTITY_REJECTED"
    except ET.ParseError:
        return "MODS_XML_MALFORMED"

    if root.tag != q("mods"):
        return "MODS_ROOT_NOT_MODS_V3"
    parent = {c: p for p in root.iter() for c in p}
    if any(el is not root for el in root.iter(q("mods"))):
        return "MODS_UNEXPECTED_NESTING:mods"
    hosts = [el for el in root.iter(q("relatedItem")) if el.get("type") == "host"]
    if any(parent.get(h) is not root for h in hosts):
        return "MODS_UNEXPECTED_NESTING:host"
    if len(hosts) != 1:
        return MISSING
    host = hosts[0]
    if any(el is not host for el in host.iter(q("relatedItem"))):
        return "MODS_UNEXPECTED_NESTING:related_item_in_host"

    scope = {"granule": root, "host": host}
    found = {k: _walk(scope[s], steps) for k, (s, steps, _, _) in FIELDS.items()}
    designated = {id(el) for els in found.values() for el in els}
    for k, (local, attrs) in SIGNATURES.items():
        if any(id(el) not in designated for el in root.iter(q(local)) if _is(el, local, attrs)):
            return f"MODS_UNEXPECTED_NESTING:{k}"
    for k in ("start", "end"):
        if any(id(el) not in designated for el in root.iter(q(k))):
            return f"MODS_UNEXPECTED_NESTING:{k}"
    # E1: a container on a designated path occurs exactly once under its unique parent, so fields cannot be
    # split across sibling containers or accompanied by an empty duplicate container.
    for s, steps in CONTAINERS:
        parents = _walk(scope[s], steps[:-1])
        local = steps[-1][0]
        if len(parents) != 1 or len(_container_children(parents[0], local)) != 1 or len(_walk(scope[s], steps)) != 1:
            return MISSING
    for k, (_, _, _, one) in FIELDS.items():
        if one and len(found[k]) != 1:
            return MISSING

    f: dict = {}
    for k, (_, _, grammar, one) in FIELDS.items():
        values = []
        for el in found[k]:
            if len(el) != 0 or el.text is None or not re.fullmatch(grammar, el.text):
                return f"MODS_FIELD_MALFORMED:{k}"
            values.append(el.text)
        f[k] = values[0] if one else values
    try:
        date.fromisoformat(f["date"])
        date.fromisoformat(f["package"][3:])
    except ValueError:
        return "MODS_FIELD_MALFORMED:date"
    if not int(f["host_start"]) <= int(f["start"]) <= int(f["end"]) <= int(f["host_end"]):
        return MISSING
    volume, page = f["citation"].split(" FR ")
    if volume != f["volume"]:
        return "MODS_INTERNAL_CONFLICT:citation_volume"
    if page != f["start"]:
        return "MODS_INTERNAL_CONFLICT:citation_page"
    return f


def bind_mods(fields: dict | str, meta: FrMetadataRecord) -> str:
    """Identity binding to the expected Federal Register document and package."""
    if isinstance(fields, str):
        return fields
    want = dict(doc=meta.document_number, citation=meta.citation, volume=str(meta.volume),
                start=str(meta.start_page), end=str(meta.end_page), date=meta.publication_date.isoformat(),
                package=f"FR-{meta.publication_date.isoformat()}")
    bad = [k for k, v in want.items() if fields[k] != v]
    if [x.upper() for x in fields["departments"]] != [x.upper() for x in meta.docket_ids]:
        bad.append("docket_ids")
    return "OK" if not bad else "MODS_IDENTITY_MISMATCH:" + ",".join(bad)


def mods_record(retrievals: list[GovInfoModsRetrieval], meta: FrMetadataRecord) -> GovInfoMods | str:
    """All MODS retrievals known by T for one document: none -> missing; any rejected -> the smallest
    reason (order-independent); differing bound fields -> conflict; else the earliest identical retrieval."""
    if not retrievals:
        return "MODS_NOT_AVAILABLE_AT_T"
    parsed = [(r, parse_mods(r.body)) for r in retrievals]
    rejected = sorted({bind_mods(f, meta) for _, f in parsed} - {"OK"})
    if rejected:
        return rejected[0]
    if len({json.dumps(f, sort_keys=True) for _, f in parsed}) != 1:
        return "CONFLICTING_MODS_METADATA"
    first, f = min(parsed, key=lambda rf: (rf[0].retrieved_at, rf[0].sha256))
    return GovInfoMods(document_number=meta.document_number, url=first.url, retrieved_at=first.retrieved_at,
                       sha256=first.sha256, volume=int(f["volume"]), issue=int(f["issue"]),
                       start_page=int(f["start"]), end_page=int(f["end"]), issue_start_page=int(f["host_start"]),
                       issue_end_page=int(f["host_end"]), date_issued=date.fromisoformat(f["date"]),
                       fr_doc_no=f["doc"], fr_citation=f["citation"], department_codes=tuple(f["departments"]),
                       package_record_identifier=f["package"])
