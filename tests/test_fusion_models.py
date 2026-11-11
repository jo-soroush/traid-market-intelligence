"""C15 Phase 1, slice 2: leaf models and strict timestamp admission (TRAID_C15_SLICE2_FINAL_DESIGN_CORRECTION.md).

Offline; no network. Tests that encode the proposed errata C-1 (no ELIGIBLE role) and C-2 (name rule allowlist) are
marked ERRATUM and are pending authoritative documentation reconciliation of contract v3.2.
"""
import ast
from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
import enum
import inspect
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ValidationError
from pydantic_core import TzInfo
import pytest

import traid.fusion.models as models
from traid.domain.models import CanonicalModel
from traid.fusion import (
    ROLE_RULES_ACTIVE, Basis, Comparison, Coverage, EvidenceRole, FusionModel, IdentityEncodingError,
    InputDigestRef, MetricObservation, MetricState, RawIdentity, SourceReportedContradiction, id_digest, id_enc,
)

ROOT = Path(__file__).resolve().parents[1]
LEAVES = (MetricObservation, Coverage, InputDigestRef, SourceReportedContradiction)
ENUMS = (EvidenceRole, MetricState, Comparison, Basis, RawIdentity)


def stored(text):
    return Coverage(earliest_time=text).earliest_time


def utc_text(dt):
    return id_enc(dt)["v"]


# ------------------------------------------------------------------------------------------ positive vectors
POSITIVE = [
    ("2026-01-01T12:00:00Z", "2026-01-01T12:00:00.000000Z"),
    ("2026-01-01T12:00:00.1Z", "2026-01-01T12:00:00.100000Z"),
    ("2026-01-01T12:00:00.123456Z", "2026-01-01T12:00:00.123456Z"),
    ("2026-01-01T12:00:00.000001Z", "2026-01-01T12:00:00.000001Z"),
    ("2026-01-01T12:00:00+02:00", "2026-01-01T10:00:00.000000Z"),
    ("2026-01-01T12:00:00-05:30", "2026-01-01T17:30:00.000000Z"),
    ("2026-01-01T12:00:00.5+00:00", "2026-01-01T12:00:00.500000Z"),
    ("2026-01-01T12:00:00-00:00", "2026-01-01T12:00:00.000000Z"),
    ("2026-01-01T00:00:00+14:00", "2025-12-31T10:00:00.000000Z"),
    ("2026-01-01T12:00:00+23:59", "2025-12-31T12:01:00.000000Z"),
    ("2026-01-01T12:00:00-23:59", "2026-01-02T11:59:00.000000Z"),
    ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00.000000Z"),
    ("9999-12-31T23:59:59.999999Z", "9999-12-31T23:59:59.999999Z"),
    ("2024-02-29T00:00:00Z", "2024-02-29T00:00:00.000000Z"),
    ("2026-02-28T23:59:59Z", "2026-02-28T23:59:59.000000Z"),
]


@pytest.mark.parametrize("text,expected", POSITIVE)
def test_positive_iso_vectors_are_admitted_and_stored_as_utc(text, expected):
    value = stored(text)
    assert type(value) is datetime and type(value.tzinfo) is timezone and value.tzinfo is timezone.utc
    assert utc_text(value) == expected
    model = Coverage(earliest_time=text)
    assert id_enc(model.model_dump())                                     # python dump passes the Slice 1 serializer
    assert id_digest("t", model.model_dump())
    assert Coverage.model_validate(model.model_dump(mode="json")) == model   # JSON round trip
    assert Coverage.model_validate_json(model.model_dump_json()) == model


# ------------------------------------------------------------------------------------------ negative vectors
NEGATIVE = [
    "2026-01-01T12:00:00.1234567Z", "2026-01-01T12:00:00.123456789Z", "2026-01-01T12:00:00.1234567+02:00",
    "2026-01-01T12:00:00.Z",
    "2026-01-01T12:00Z", "2026-01-01T12Z", "2026-01-01 12:00:00Z", "2026-01-01t12:00:00Z", "2026-01-01T12:00:00z",
    "20260101T120000Z", "2026-W01-1T12:00:00Z", "2026-001T12:00:00Z",
    "2026-01-01", "2026-01-01Z", "2026-01-01T12:00:00", "2026-01-01T12:00:00.123456",
    "2026-01-01T12:00:00+0200", "2026-01-01T12:00:00+02", "2026-01-01T12:00:00+02:00:30",
    "2026-01-01T12:00:00+24:00", "2026-01-01T12:00:00+02:60", "2026-01-01T12:00:00 +02:00",
    "2026-01-01T12:00:00Z+00:00",
    " 2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z ", "2026-01-01T12:00:00Z\n", "\t2026-01-01T12:00:00Z",
    "２０２６-01-01T12:00:00Z", "2026-1-1T12:00:00Z",
    "2026-02-30T12:00:00Z", "2023-02-29T00:00:00Z", "2026-13-01T12:00:00Z", "2026-01-01T24:00:00Z",
    "2026-01-01T12:60:00Z", "2026-01-01T23:59:60Z",
    "0", "1.5", "1700000000", "-1", "1e9", "", "nan", "T12:00:00Z",
    "0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00",
]


@pytest.mark.parametrize("text", NEGATIVE)
def test_negative_iso_vectors_are_rejected(text):
    with pytest.raises(ValidationError):
        Coverage(earliest_time=text)
    with pytest.raises(ValidationError):
        Coverage.model_validate({"earliest_time": text})
    with pytest.raises(ValidationError):
        Coverage.model_validate_json('{"earliest_time": %s}' % __import__("json").dumps(text))


class StrSub(str):
    pass


@pytest.mark.parametrize("raw", [0, 1.5, 1700000000, True, b"2026-01-01T12:00:00Z", Decimal("1"),
                                 StrSub("2026-01-01T12:00:00Z"), date(2026, 1, 1), ["2026-01-01T12:00:00Z"]])
def test_non_string_non_datetime_inputs_are_rejected(raw):
    with pytest.raises(ValidationError):
        Coverage(earliest_time=raw)


@pytest.mark.parametrize("payload", ['{"earliest_time":"0"}', '{"earliest_time":"1.5"}',
                                     '{"earliest_time":"1700000000"}', '{"earliest_time":0}',
                                     '{"earliest_time":1.5}', '{"earliest_time":1700000000}',
                                     '{"earliest_time":true}', '{"earliest_time":"2026-01-01"}'])
def test_json_numeric_and_date_only_inputs_are_rejected(payload):
    with pytest.raises(ValidationError):
        Coverage.model_validate_json(payload)


def test_optional_datetime_null_and_omitted_give_none():
    assert Coverage.model_validate_json('{"earliest_time": null}').earliest_time is None
    assert Coverage().earliest_time is None and Coverage().latest_time is None


# ------------------------------------------------------------------------------------------ fraction boundary
@pytest.mark.parametrize("digits", range(0, 9))
def test_fractional_digit_boundary(digits):
    text = "2026-01-01T12:00:00" + ("." + "1234567890"[:digits] if digits else "") + "Z"
    if digits <= 6:
        value = stored(text)
        assert value.microsecond == int(("1234567890"[:digits]).ljust(6, "0")) if digits else value.microsecond == 0
    else:
        with pytest.raises(ValidationError):
            Coverage(earliest_time=text)
        datetime.fromisoformat(text)          # fromisoformat alone accepts it: only the shape check rejects it


def test_microseconds_are_preserved_exactly():
    assert stored("2026-01-01T12:00:00.123456+01:00").microsecond == 123456


# ------------------------------------------------------------------------------------------ direct datetimes
class Counting(tzinfo):
    calls = 0

    def utcoffset(self, dt):
        type(self).calls += 1
        return timedelta(0)

    def dst(self, dt):
        type(self).calls += 1
        return timedelta(0)

    def tzname(self, dt):
        type(self).calls += 1
        return "X"

    def fromutc(self, dt):
        type(self).calls += 1
        return dt


class DtSub(datetime):
    def utcoffset(self):
        return timedelta(0)


class ZiSub(ZoneInfo):
    pass


def ny(fold):
    try:
        return datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=fold)
    except ZoneInfoNotFoundError:             # pragma: no cover
        pytest.skip("no time-zone database")


def test_direct_datetime_accepted_forms():
    assert utc_text(stored(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))) == "2026-01-01T12:00:00.000000Z"
    assert utc_text(stored(datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2))))) == "2026-01-01T10:00:00.000000Z"
    assert utc_text(stored(datetime(2026, 1, 1, 12, tzinfo=TzInfo(3600)))) == "2026-01-01T11:00:00.000000Z"
    assert utc_text(stored(ny(0))) == "2026-11-01T05:30:00.000000Z"
    assert utc_text(stored(ny(1))) == "2026-11-01T06:30:00.000000Z"
    assert stored(ny(1)).tzinfo is timezone.utc


def test_direct_datetime_rejected_forms_and_no_callbacks():
    Counting.calls = 0
    custom = datetime(2026, 1, 1, tzinfo=Counting())
    Counting.calls = 0
    with pytest.raises(ValidationError):
        Coverage(earliest_time=custom)
    with pytest.raises(ValidationError):
        Coverage.model_validate({"earliest_time": custom})
    with pytest.raises(ValidationError):
        Coverage.model_validate({"latest_time": custom, "earliest_time": None})
    assert Counting.calls == 0
    for bad in (datetime(2026, 1, 1), DtSub(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=ZiSub("UTC"))):
        with pytest.raises(ValidationError):
            Coverage(earliest_time=bad)


def test_datetime_gate_matches_the_slice_1_serializer():
    cases = [datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=5))),
             datetime(2026, 1, 1, tzinfo=TzInfo(60)), ny(0), ny(1), datetime(2026, 1, 1),
             DtSub(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=Counting()),
             datetime(2026, 1, 1, tzinfo=ZiSub("UTC")),
             datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1)))]
    for dt in cases:
        try:
            id_enc(dt)
            enc_ok = True
        except IdentityEncodingError:
            enc_ok = False
        try:
            Coverage(earliest_time=dt)
            cov_ok = True
        except ValidationError:
            cov_ok = False
        assert enc_ok == cov_ok, dt


# ------------------------------------------------------------------------------------------ base, enums, scope
def test_role_rules_and_roles():
    assert ROLE_RULES_ACTIVE == ()
    assert [m.name for m in EvidenceRole] == ["DESCRIPTIVE_ONLY", "MISSING", "STALE", "UNVERIFIED", "INELIGIBLE"]
    for name in ("SUPPORT", "CONTRADICT", "ELIGIBLE"):                    # ERRATUM C-1 (pending reconciliation)
        assert not hasattr(EvidenceRole, name)


def test_enums_are_module_level_strenum_with_value_equal_to_name():
    for enum_cls in ENUMS:
        assert issubclass(enum_cls, enum.StrEnum) and enum_cls.__qualname__ == enum_cls.__name__
        for member in enum_cls:
            assert member.value == member.name and type(member)(member.value) is member
            assert id_enc(member)["v"] == member.name


def test_base_behaviour():
    for cls in LEAVES:
        assert issubclass(cls, FusionModel) and not issubclass(cls, CanonicalModel)
        assert "schema_version" not in cls.model_fields
        assert cls.model_config["frozen"] and cls.model_config["extra"] == "forbid"
    c = Coverage()
    with pytest.raises(ValidationError):
        c.contributing_count = 1
    with pytest.raises(ValidationError):
        Coverage(unknown=1)
    with pytest.raises(ValidationError):
        MetricObservation(name="a", state="PRESENT", value="1", unit="u", extra_field=1)


FORBIDDEN = ("score", "alignment", "strength", "confidence", "probability", "weight", "readiness", "priority",
             "support")


def test_name_scan_has_no_authority_names():                              # ERRATUM C-2 allowlist
    names = []
    for cls in LEAVES:
        names += [cls.__name__, *cls.model_fields]
    for enum_cls in ENUMS:
        names += [enum_cls.__name__, *[m.name for m in enum_cls]]
    names += [n for n in vars(models) if not n.startswith("__")]
    for name in names:
        low = name.lower()
        assert not any(word in low for word in FORBIDDEN), name
        if "contradict" in low:
            assert name in {"SourceReportedContradiction"}, name


def test_no_ai_derived_authority_in_models():
    fields = {f for cls in LEAVES for f in cls.model_fields}
    assert not {"supporting_factors", "contradicting_factors"} & fields
    assert "ai" not in {n.lower() for n in vars(models)}


# ------------------------------------------------------------------------------------------ MetricObservation
def obs(**kw):
    base = dict(name="atr", state="PRESENT", value=Decimal("1.50"), unit="usd")
    base.update(kw)
    return MetricObservation(**base)


def test_metric_state_matrix():
    assert obs().value == Decimal("1.50") and str(obs().value) == "1.50"
    assert obs(state="WITHHELD", value=None, reason="r").reason == "r"
    assert obs(state="NOT_AVAILABLE", value=None).value is None
    with pytest.raises(ValidationError):
        obs(value=None)                                                    # PRESENT needs a value
    with pytest.raises(ValidationError):
        obs(reason="x")                                                    # PRESENT carries no reason
    for state in ("WITHHELD", "NOT_AVAILABLE"):
        with pytest.raises(ValidationError):
            obs(state=state, value=Decimal("1"))
    with pytest.raises(ValidationError):
        obs(state="BOGUS")


@pytest.mark.parametrize("bad", [1.5, True, Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), "NaN", "inf",
                                 "abc", [], {}])
def test_metric_value_rejects_float_bool_nonfinite_and_junk(bad):
    with pytest.raises(ValidationError):
        obs(value=bad)


def test_metric_decimal_preservation():
    assert str(obs(value="1.50").value) == "1.50"
    assert str(obs(value=Decimal("0.10")).value) == "0.10"
    assert str(obs(value=Decimal("-0")).value) == "-0"
    assert str(obs(value=Decimal("1E+3")).value) == "1E+3"
    assert obs(value=7).value == Decimal(7)
    big = Decimal("123456789012345678901234567890.123456789012345678901234567890")
    assert obs(value=big).value == big and str(obs(value=big).value) == str(big)
    model = obs(value=Decimal("1.50"))
    assert str(MetricObservation.model_validate_json(model.model_dump_json()).value) == "1.50"
    assert MetricObservation.model_validate(model.model_dump(mode="json")) == model
    assert id_digest("t", model.model_dump())


@pytest.mark.parametrize("field", ["name", "unit", "window_id", "reason"])
@pytest.mark.parametrize("bad", ["", " ", " x", "x ", "\tx", "x\n", 1, None])
def test_metric_text_rules(field, bad):
    optional = field in ("window_id", "reason")
    kw = {field: bad}
    if field == "reason":
        kw.update(state="WITHHELD", value=None)
    if optional and bad is None:
        assert getattr(obs(**kw), field) is None
        return
    with pytest.raises(ValidationError):
        obs(**kw)


def test_metric_text_is_not_stripped_or_altered():
    assert obs(name="a b", window_id="w:1").name == "a b"


# ------------------------------------------------------------------------------------------ Coverage
def test_coverage_rules():
    assert Coverage().contributing_count is None
    assert Coverage(earliest_time="2026-01-01T00:00:00Z", latest_time="2026-01-01T00:00:00Z")
    assert Coverage(earliest_time="2026-01-01T01:00:00+01:00", latest_time="2026-01-01T00:00:00Z")   # equal instants
    with pytest.raises(ValidationError):
        Coverage(earliest_time="2026-01-02T00:00:00Z", latest_time="2026-01-01T00:00:00Z")
    assert Coverage(contributing_count=0).contributing_count == 0
    for bad in (-1, True, 1.0, "1"):
        with pytest.raises(ValidationError):
            Coverage(contributing_count=bad)
    for bad in ("", " 1h", "1h "):
        with pytest.raises(ValidationError):
            Coverage(interval=bad)
    assert Coverage(interval="1h").interval == "1h"


# ------------------------------------------------------------------------------------------ InputDigestRef
def test_input_digest_ref_rules():
    good = "a" * 64
    assert InputDigestRef(algorithm="sha256", digest=good).digest == good
    for bad in (good.upper(), "a" * 63, "a" * 65, "g" * 64, "", good + "\n", " " + good, 1):
        with pytest.raises(ValidationError):
            InputDigestRef(algorithm="sha256", digest=bad)
    for bad in ("", " sha256"):
        with pytest.raises(ValidationError):
            InputDigestRef(algorithm=bad, digest=good)


# ------------------------------------------------------------------------------------------ contradiction
def test_source_reported_contradiction():
    c = SourceReportedContradiction(category="c", kind="k", code="CODE", location="a.b[0]")
    assert (c.category, c.kind, c.code, c.location) == ("c", "k", "CODE", "a.b[0]")
    for field in ("category", "kind", "code", "location"):
        for bad in ("", " x", "x ", None, 1):
            kw = dict(category="c", kind="k", code="CODE", location="l", **{})
            kw[field] = bad
            with pytest.raises(ValidationError):
                SourceReportedContradiction(**kw)
    assert SourceReportedContradiction.model_validate_json(c.model_dump_json()) == c
    assert id_digest("t", c.model_dump())


# ------------------------------------------------------------------------------------------ serializer compat
def test_every_leaf_dump_passes_the_slice_1_serializer():
    samples = [obs(), obs(state="WITHHELD", value=None, reason="r", window_id="w"),
               Coverage(earliest_time="2026-01-01T00:00:00Z", latest_time=ny(0), contributing_count=3, interval="1h"),
               InputDigestRef(algorithm="sha256", digest="b" * 64),
               SourceReportedContradiction(category="c", kind="k", code="x", location="l")]
    for model in samples:
        dumped = model.model_dump()
        assert id_digest("t", dumped) == id_digest("t", type(model).model_validate(model.model_dump(mode="json")).model_dump())


# ------------------------------------------------------------------------------------------ import purity
def test_models_module_imports_only_stdlib_pydantic_and_the_serializer():
    tree = ast.parse(Path(inspect.getsourcefile(models)).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            roots = [(node.module or "").split(".")[0]]
            if roots == ["traid"]:
                assert node.module == "traid.fusion.serialization"
        else:
            continue
        for root in roots:
            assert root in sys.stdlib_module_names or root in {"pydantic", "traid"}, root
    source = Path(inspect.getsourcefile(models)).read_text()
    for banned in ("boto3", "botocore", "requests", "httpx", "socket", "urllib", "traid.strategy", "traid.risk",
                   "traid.ai", "report_sha256", "canonical_json"):
        assert not re.search(rf"\b{re.escape(banned)}\b", source), banned
