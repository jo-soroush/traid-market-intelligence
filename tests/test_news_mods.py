"""C13 structural MODS validation (design R4 §6.7) and the mandatory E1 container-cardinality test.

Inputs are the REAL committed GovInfo MODS records and deterministic edits of them (SYN)."""
import itertools
import random
import re

import pytest

from news_support import DOCS, _no_network, body, metadata, retrieval  # noqa: F401  (autouse fixture)
from traid.news.mods import MAX_BYTES, MISSING, bind_mods, mods_record, parse_mods

REAL = body("2024-00743", "GOVINFO_MODS")
META = metadata("2024-00743")


def once(data: bytes, old: bytes, new: bytes) -> bytes:
    assert data.count(old) == 1, old
    return data.replace(old, new, 1)


def span(data: bytes, start: bytes, end: bytes) -> tuple[int, int]:
    s = data.find(start)
    e = data.find(end, s) + len(end)
    assert s >= 0 and e > s
    return s, e


def cut(data: bytes, start: bytes, end: bytes) -> bytes:
    s, e = span(data, start, end)
    return data[:s] + data[e:]


S_HOST, E_HOST = span(REAL, b'<relatedItem type="host"', b"</relatedItem>\n</mods>")
E_HOST -= len(b"\n</mods>")
HOST = REAL[S_HOST:E_HOST]
DOCNO = b'    <identifier type="FR Doc No.">2024-00743</identifier>\n'


def outcome(data: bytes) -> str:
    return bind_mods(parse_mods(data), META)


@pytest.mark.parametrize("document", DOCS)
def test_real_records_parse_and_bind(document):
    meta = metadata(document)
    record = mods_record([retrieval(document, "GOVINFO_MODS")], meta)
    assert not isinstance(record, str)
    assert (record.fr_doc_no, record.fr_citation, record.start_page, record.end_page, record.volume) == (
        document, meta.citation, meta.start_page, meta.end_page, meta.volume)
    assert record.package_record_identifier == f"FR-{meta.publication_date.isoformat()}"
    assert record.issue_start_page <= record.start_page <= record.end_page <= record.issue_end_page


def test_real_2024_00743_scoped_fields():
    f = parse_mods(REAL)
    assert {k: f[k] for k in ("doc", "citation", "volume", "issue", "start", "end", "date", "host_start", "host_end",
                              "package")} == dict(doc="2024-00743", citation="89 FR 3008", volume="89", issue="11",
                                                  start="3008", end="3014", date="2024-01-17", host_start="2875",
                                                  host_end="3298", package="FR-2024-01-17")
    assert len(f["departments"]) == 12 and f["departments"][0] == "Release No. 34-99306"
    # an unscoped text search would be ambiguous: two page extents exist
    assert [x.decode() for x in re.findall(rb'<extent unit="pages">\s*<start>(\d+)</start>', REAL)] == ["3008", "2875"]


CASES = {
    # R3 binding cases (unchanged expectations)
    "M04-other-document": (REAL.replace(b'FR Doc No.">2024-00743', b'FR Doc No.">2024-00744'), "MODS_IDENTITY_MISMATCH:doc"),
    "M05-date-mismatch": (REAL.replace(b">2024-01-17</dateIssued>", b">2024-01-18</dateIssued>"), "MODS_IDENTITY_MISMATCH:date"),
    "M06-docket-mismatch": (REAL.replace(b"Release No. 34-99306", b"Release No. 34-99307"), "MODS_IDENTITY_MISMATCH:docket_ids"),
    "M08-duplicate-field": (REAL.replace(b"<issue>11</issue>", b"<issue>11</issue><issue>12</issue>"), MISSING),
    "M11-pages-outside-issue": (REAL.replace(b"<end>3014</end>", b"<end>3299</end>", 1), MISSING),
    "M12-no-host-item": (REAL.replace(b'<relatedItem type="host"', b'<relatedItem type="series"'), MISSING),
    # the three R3 defects
    "D1-closing-root-removed": (once(REAL, b"</mods>", b""), "MODS_XML_MALFORMED"),
    "D2-foreign-root-namespace": (once(REAL, b'xmlns="http://www.loc.gov/mods/v3"', b'xmlns="urn:example:not-mods"'),
                                  "MODS_ROOT_NOT_MODS_V3"),
    "D3-host-inside-comment": (REAL[:S_HOST] + b"<!-- " + HOST + b" -->" + REAL[E_HOST:], MISSING),
    # malformed bytes
    "S1b-closing-root-misspelled": (once(REAL, b"</mods>", b"</mod>"), "MODS_XML_MALFORMED"),
    "S1c-truncated-mid-host": (REAL[: S_HOST + 400], "MODS_XML_MALFORMED"),
    "S1d-mismatched-tags": (once(REAL, b"<issue>11</issue>", b"<issue>11</volume>"), "MODS_XML_MALFORMED"),
    "S1e-undefined-entity": (once(REAL, b"<issue>11</issue>", b"<issue>&eleven;</issue>"), "MODS_XML_MALFORMED"),
    "S1f-junk-after-root": (REAL + b"<mods/>", "MODS_XML_MALFORMED"),
    "S1g-empty-body": (b"", "MODS_XML_MALFORMED"),
    "S1h-not-xml": (b"<html><body>Error</body>", "MODS_XML_MALFORMED"),
    "S1i-invalid-utf8": (once(REAL, b"<issue>11</issue>", b"<issue>1\xff</issue>"), "MODS_XML_ENCODING_REJECTED"),
    "S1j-declared-latin1": (once(REAL, b'encoding="UTF-8"', b'encoding="ISO-8859-1"'), "MODS_XML_ENCODING_REJECTED"),
    "S1k-utf16-body": (REAL.decode().replace('encoding="UTF-8"', 'encoding="UTF-16"').encode("utf-16"),
                       "MODS_XML_ENCODING_REJECTED"),
    "S1l-oversized": (once(REAL, b"</mods>", b"<!--" + b"x" * MAX_BYTES + b"--></mods>"), "MODS_XML_TOO_LARGE"),
    # namespaces
    "S2b-no-namespace": (once(REAL, b' xmlns="http://www.loc.gov/mods/v3"', b""), "MODS_ROOT_NOT_MODS_V3"),
    "S2c-mods-v4": (once(REAL, b'xmlns="http://www.loc.gov/mods/v3"', b'xmlns="http://www.loc.gov/mods/v4"'),
                    "MODS_ROOT_NOT_MODS_V3"),
    "S2d-root-local-name": (once(once(REAL, b"<mods xmlns:xlink", b"<record xmlns:xlink"), b"</mods>", b"</record>"),
                            "MODS_ROOT_NOT_MODS_V3"),
    "S2e-field-in-foreign-namespace": (once(REAL, b"<issue>11</issue>", b'<issue xmlns="urn:x">11</issue>'), MISSING),
    # comments, CDATA and PIs are never evidence
    "S3b-issue-only-in-comment": (once(REAL, b"<issue>11</issue>", b"<!-- <issue>11</issue> -->"), MISSING),
    "S3c-docno-only-in-comment": (once(REAL, DOCNO, b"<!-- " + DOCNO.strip() + b" -->\n"), MISSING),
    "S3d-host-only-in-cdata": (REAL[:S_HOST] + b"<extension><![CDATA[" + HOST + b"]]></extension>" + REAL[E_HOST:], MISSING),
    "S3e-comment-inside-field": (once(REAL, b"<issue>11</issue>", b"<issue>1<!-- -->1</issue>"), "MODS_FIELD_MALFORMED:issue"),
    "S3f-pi-inside-field": (once(REAL, b"<volume>89</volume>", b"<volume>89<?x y?></volume>"), "MODS_FIELD_MALFORMED:volume"),
    "S3g-comment-elsewhere-ignored": (once(REAL, b"<typeOfResource>", b"<!-- <issue>99</issue> --><typeOfResource>"), "OK"),
    # missing document-level and host-level fields
    "S4a-no-fr-doc-no": (once(REAL, DOCNO, b""), MISSING),
    "S4b-no-fr-citation": (once(REAL, b'    <identifier type="FR citation">89 FR 3008</identifier>\n', b""), MISSING),
    "S4c-no-granule-part": (cut(REAL, b'<part type="Notices">', b"</part>"), MISSING),
    "S4d-no-granule-end": (once(REAL, b"<end>3014</end>", b""), MISSING),
    "S5a-no-volume": (once(REAL, b"<volume>89</volume>", b""), MISSING),
    "S5b-no-issue": (once(REAL, b"<issue>11</issue>", b""), MISSING),
    "S5c-no-date-issued": (cut(REAL, b"<dateIssued", b"</dateIssued>"), MISSING),
    "S5d-no-issue-part": (cut(REAL, b'<part type="issue">', b"</part>"), MISSING),
    "S5e-issue-part-wrong-type": (once(REAL, b'<part type="issue">', b'<part type="Notices">'), "MODS_UNEXPECTED_NESTING:start"),
    "S5f-no-record-identifier": (cut(REAL, b"<recordIdentifier", b"</recordIdentifier>"), MISSING),
    "S5g-host-removed": (REAL[:S_HOST] + REAL[E_HOST:], MISSING),
    # duplicates
    "S6a-duplicate-fr-doc-no": (once(REAL, DOCNO, DOCNO + DOCNO), MISSING),
    "S6b-duplicate-host": (REAL[:E_HOST] + b"\n    " + HOST + REAL[E_HOST:], MISSING),
    "S6d-duplicate-date-issued": (once(REAL, b"<issuance>", b"<dateIssued>2024-01-17</dateIssued><issuance>"), MISSING),
    "S6e-duplicate-volume": (once(REAL, b"<volume>89</volume>", b"<volume>89</volume><volume>90</volume>"), MISSING),
    # document vs. issue conflicts and package identity
    "S7a-host-volume-vs-citation": (once(REAL, b"<volume>89</volume>", b"<volume>90</volume>"),
                                    "MODS_INTERNAL_CONFLICT:citation_volume"),
    "S7b-granule-start-vs-citation": (once(REAL, b"<start>3008</start>", b"<start>3009</start>"),
                                      "MODS_INTERNAL_CONFLICT:citation_page"),
    "S7c-pages-outside-issue": (once(REAL, b"<start>2875</start>", b"<start>3009</start>"), MISSING),
    "S7d-package-other-issue": (once(REAL, b">FR-2024-01-17</recordIdentifier>", b">FR-2024-01-18</recordIdentifier>"),
                                "MODS_IDENTITY_MISMATCH:package"),
    # unexpected nesting
    "S8a-fr-doc-no-in-extension": (once(once(REAL, DOCNO, b""), b"<granuleClass>", DOCNO.strip() + b"<granuleClass>"),
                                   "MODS_UNEXPECTED_NESTING:doc"),
    "S8b-extra-fr-doc-no-in-host": (once(REAL, b"<docClass>FR</docClass>",
                                         b'<docClass>FR</docClass><identifier type="FR Doc No.">2024-00744</identifier>'),
                                    "MODS_UNEXPECTED_NESTING:doc"),
    "S8c-issue-in-origin-info": (once(once(REAL, b"<issue>11</issue>", b""), b"<issuance>", b"<issue>11</issue><issuance>"),
                                 "MODS_UNEXPECTED_NESTING:issue"),
    "S8d-host-in-extension": (REAL[:S_HOST] + b"<extension>" + HOST + b"</extension>" + REAL[E_HOST:],
                              "MODS_UNEXPECTED_NESTING:host"),
    "S8e-related-item-in-host": (once(REAL, b"<docClass>FR</docClass>", b'<docClass>FR</docClass><relatedItem type="constituent">'
                                      b"<titleInfo><title>x</title></titleInfo></relatedItem>"),
                                 "MODS_UNEXPECTED_NESTING:related_item_in_host"),
    "S8f-nested-mods": (once(REAL, b"<granuleClass>", b'<mods version="3.3"/><granuleClass>'), "MODS_UNEXPECTED_NESTING:mods"),
    "S8h-field-wrapped": (once(REAL, b"<issue>11</issue>", b"<wrap><issue>11</issue></wrap>"), "MODS_UNEXPECTED_NESTING:issue"),
    "S8i-child-in-field": (once(REAL, b"<issue>11</issue>", b"<issue>11<b/></issue>"), "MODS_FIELD_MALFORMED:issue"),
    # leaf grammar
    "S9a-trailing-space": (once(REAL, b"<issue>11</issue>", b"<issue>11 </issue>"), "MODS_FIELD_MALFORMED:issue"),
    "S9b-leading-zero": (once(REAL, b"<volume>89</volume>", b"<volume>089</volume>"), "MODS_FIELD_MALFORMED:volume"),
    "S9c-impossible-date": (once(REAL, b">2024-01-17</dateIssued>", b">2024-02-30</dateIssued>"), "MODS_FIELD_MALFORMED:date"),
    "S9d-empty-issue": (once(REAL, b"<issue>11</issue>", b"<issue/>"), "MODS_FIELD_MALFORMED:issue"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_structural_cases(case):
    data, expected = CASES[case]
    assert outcome(data) == expected


# ----------------------------------------------------------------------- E1 (mandatory)
GRANULE_PART = b'<part type="Notices">\n        <extent unit="pages">\n            <start>3008</start>\n            <end>3014</end>\n        </extent>\n    </part>'
E1 = {
    "granule-part-split": once(REAL, GRANULE_PART, b'<part type="Notices"><extent unit="pages"><start>3008</start></extent></part>'
                                                   b'<part type="Notices"><extent unit="pages"><end>3014</end></extent></part>'),
    "granule-extent-split": once(REAL, b'<extent unit="pages">\n            <start>3008</start>\n            <end>3014</end>\n        </extent>',
                                 b'<extent unit="pages"><start>3008</start></extent><extent unit="pages"><end>3014</end></extent>'),
    "empty-second-granule-part": once(REAL, b'    <identifier type="preferred citation">',
                                      b'    <part type="Notices"/>\n    <identifier type="preferred citation">'),
    "host-extension-split": once(REAL, b"<volume>89</volume>\n            <issue>11</issue>",
                                 b"<volume>89</volume></extension><extension><issue>11</issue>"),
    "empty-second-origin-info": once(REAL, b"<physicalDescription>\n            <note", b"<originInfo/><physicalDescription>\n            <note"),
    "empty-second-record-info": once(REAL, b"<recordInfo>", b"<recordInfo/><recordInfo>"),
    "empty-second-issue-part": once(REAL, b'<part type="issue">', b'<part type="other"/><part type="issue">'),
    "empty-second-issue-extent": once(REAL, b'<part type="issue">', b'<part type="issue"><extent unit="pages"/>'),
    "duplicate-granule-part": once(REAL, b'    <identifier type="preferred citation">',
                                   b'    <part type="Notices"><extent unit="pages"><start>3008</start><end>3014</end></extent></part>\n'
                                   b'    <identifier type="preferred citation">'),
}


@pytest.mark.parametrize("case", sorted(E1))
def test_e1_intermediate_container_cardinality(case):
    """Every container on a designated path occurs exactly once under its parent; the audited R4 probe accepted the
    first six of these (non-blocking finding E1)."""
    assert outcome(E1[case]) == MISSING


def test_e1_preserves_every_real_record():
    for document in DOCS:
        assert bind_mods(parse_mods(body(document, "GOVINFO_MODS")), metadata(document)) == "OK"


# ----------------------------------------------------------------------- DTD / entities / prefixes
LOL = (b'<?xml version="1.0"?><!DOCTYPE m [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
       b'<mods xmlns="http://www.loc.gov/mods/v3">&b;</mods>')
XXE = b'<?xml version="1.0"?><!DOCTYPE m [<!ENTITY x SYSTEM "file:///etc/hosts">]><mods xmlns="http://www.loc.gov/mods/v3">&x;</mods>'
EXT = once(REAL, b"<mods xmlns:xlink", b'<!DOCTYPE mods SYSTEM "https://evil.example/mods.dtd"><mods xmlns:xlink')


@pytest.mark.parametrize("data", [LOL, XXE, EXT], ids=["entity-expansion", "external-entity", "external-dtd"])
def test_dtd_and_entities_refused_before_and_during_parse(data):
    assert parse_mods(data) == "MODS_XML_DTD_OR_ENTITY_REJECTED"
    assert parse_mods(data, prescan=False) == "MODS_XML_DTD_OR_ENTITY_REJECTED"


def test_prefixed_namespace_is_equivalent():
    text = REAL.decode()
    prefixed = re.sub(r"<(/?)(?![?!])([A-Za-z])", r"<\1m:\2", text).replace(
        'xmlns="http://www.loc.gov/mods/v3"', 'xmlns:m="http://www.loc.gov/mods/v3"').encode()
    assert outcome(prefixed) == "OK" and parse_mods(prefixed) == parse_mods(REAL)


# ----------------------------------------------------------------------- properties
def test_every_prefix_is_rejected_until_the_root_closes():
    closed = REAL.rindex(b"</mods>") + len(b"</mods>")
    for n in range(len(REAL) + 1):
        got = outcome(REAL[:n])
        assert (got == "OK") == (n >= closed), n
        assert got in ("OK", "MODS_XML_MALFORMED"), (n, got)


def test_seeded_single_byte_mutations_never_raise_or_rebind():
    rng = random.Random(20261023)
    want = parse_mods(REAL)
    bound = ("doc", "citation", "volume", "start", "end", "date", "package")
    for _ in range(1500):
        data = bytearray(REAL)
        data[rng.randrange(len(data))] = rng.randrange(256)
        data = bytes(data)
        first, second = outcome(data), outcome(data)
        assert first == second
        if first == "OK":
            got = parse_mods(data)
            assert {k: got[k] for k in bound} == {k: want[k] for k in bound}
            assert [x.upper() for x in got["departments"]] == [x.upper() for x in want["departments"]]


def test_retrievals_are_order_independent_and_any_rejection_blocks():
    good = retrieval("2024-00743", "GOVINFO_MODS")
    bad = [retrieval("2024-00743", "GOVINFO_MODS", data=CASES[k][0]) for k in
           ("D1-closing-root-removed", "D2-foreign-root-namespace", "D3-host-inside-comment", "M04-other-document")]
    pool = [good, *bad]
    for k in range(1, len(pool) + 1):
        for combo in itertools.combinations(pool, k):
            results = {mods_record(list(p), META) if isinstance(mods_record(list(p), META), str) else "RECORD"
                       for p in itertools.permutations(combo)}
            assert len(results) == 1
            assert (results == {"RECORD"}) == (combo == (good,))


def test_missing_conflicting_and_identical_retrievals():
    good = retrieval("2024-00743", "GOVINFO_MODS")
    assert mods_record([], META) == "MODS_NOT_AVAILABLE_AT_T"
    other_issue = retrieval("2024-00743", "GOVINFO_MODS", data=REAL.replace(b"<issue>11</issue>", b"<issue>12</issue>"))
    assert mods_record([good, other_issue], META) == "CONFLICTING_MODS_METADATA"
    later = retrieval("2024-00743", "GOVINFO_MODS", retrieved_at=good.retrieved_at.replace(year=2027))
    record = mods_record([later, good], META)
    assert record.retrieved_at == good.retrieved_at      # earliest identical retrieval sets availability
