"""Approved v3.4 §19 structural fixtures; no source adapter or live input."""
import ast
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from pydantic import ValidationError
import pytest

import traid.fusion as fusion
import traid.fusion.identity as identity
from traid.fusion import (
    Basis, Coverage, MetricObservation, SeriesKey, Slot, SlotClaim, SlotInstant, SlotPeriod, SlotWindow,
    exposed_content_id, id_digest, id_json, series_id, slot_id,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = dict(kind="DER", section="candles", symbol="BTC-PERP", interval="1h",
           source="hyperliquid", qualifier=None)
SERIES = "sr1:a8eb04b981cbb2c036eb5404486b9e7a5d88f2fcf6cafd0d33e59918a80e30ae"
SLOTS = (
    "sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f",
    "sl1:8d6cb6ced1c83e0dcee39e1ac2c22a30969e34efa160e32e43b71f15f7c56d56",
    "sl1:588aeede2aa7f97416c7641d32c6afe2ba83ff3199b41cc6a425e8f6b9915ffa",
    "sl1:d4a37999a079b19e2715833cdc6a33d400cd332fcd872fffa9b7420fe0f330bc",
)
CONTENT = "xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14"
EMPTY = "xc1:8f19c767a2eff3fd1a93ffbf19b5662ed8608ad84426d213c35fba39ce296a2b"
KEY_JSON = '{"$":"map","v":[["interval","1h"],["kind","DER"],["qualifier",null],["section","candles"],["source","hyperliquid"],["symbol","BTC-PERP"]]}'
CONTENT_JSON = (
    '{"$":"map","v":[["basis","EXPOSED_FIELDS"],["coverage",{"$":"map","v":[["contributing_count",'
    '{"$":"int","v":"6"}],["earliest_time",{"$":"dt","v":"2026-01-01T07:00:00.000000Z"}],'
    '["interval","1h"],["latest_time",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}]]}],'
    '["metrics",{"$":"seq","v":[{"$":"map","v":[["name","atr"],["reason",null],["state","PRESENT"],'
    '["unit","USD"],["value",{"$":"dec","v":"15e-1"}],["window_id","atr:2:2026-01-01T12:00:00Z"]]},'
    '{"$":"map","v":[["name","vwap"],["reason","UNTRUSTED"],["state","WITHHELD"],["unit","USD"],'
    '["value",null],["window_id",null]]}]}],'
    '["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"]]}'
)


def moment(hour):
    return datetime(2026, 1, 1, hour, tzinfo=timezone.utc)


def slot_forms():
    return (
        SlotInstant(form="INSTANT", at="2026-01-01T12:00:00Z"),
        SlotWindow(form="WINDOW_SESSION", window_start=moment(11), session_start=moment(0)),
        SlotPeriod(form="REFERENCE_PERIOD", period="2025-12"),
        SlotClaim(form="CLAIM_ID", claim_id="a" * 64),
    )


def slot():
    return Slot(series_key=SeriesKey(**KEY), slot_time=slot_forms()[0])


def metrics(value=Decimal("1.50")):
    return (
        MetricObservation(name="atr", state="PRESENT", value=value, unit="USD",
                          window_id="atr:2:2026-01-01T12:00:00Z"),
        MetricObservation(name="vwap", state="WITHHELD", unit="USD", reason="UNTRUSTED"),
    )


def content(**changes):
    args = dict(slot=slot(), coverage=Coverage(earliest_time=moment(7), latest_time=moment(12),
                                             contributing_count=6, interval="1h"),
                metrics=metrics(), basis=Basis.EXPOSED_FIELDS)
    args.update(changes)
    return exposed_content_id(**args)


def test_series_golden():
    assert series_id(SeriesKey(**KEY)) == SERIES


@pytest.mark.parametrize("index", range(4))
def test_four_slot_goldens(index):
    assert slot_id(Slot(series_key=SeriesKey(**KEY), slot_time=slot_forms()[index])) == SLOTS[index]


def test_content_and_empty_goldens():
    assert content() == CONTENT
    assert content(coverage=Coverage(), metrics=(), basis=Basis.NO_OBSERVATION) == EMPTY


def test_explicit_projection_bytes_and_string_enums(monkeypatch):
    calls = []
    real_digest = identity.id_digest

    def capture(tag, value):
        calls.append((tag, value))
        return real_digest(tag, value)

    monkeypatch.setattr(identity, "id_digest", capture)
    assert series_id(SeriesKey(**KEY)) == SERIES
    assert calls[-1] == ("c15.series.v1", KEY)
    assert id_json(calls[-1][1]) == KEY_JSON
    assert content() == CONTENT
    tag, value = calls[-1]
    assert tag == "c15.xc.v1" and id_json(value) == CONTENT_JSON
    assert type(value["basis"]) is str
    assert all(type(m["state"]) is str for m in value["metrics"])
    assert id_digest(tag, dict(value, basis=Basis.EXPOSED_FIELDS)) != CONTENT.split(":")[1]
    assert set(value["coverage"]) == {"earliest_time", "latest_time", "contributing_count", "interval"}
    assert calls[-2] == ("c15.slot.v1", {"series_key": KEY, "slot_time": {"form": "INSTANT", "at": moment(12)}})


@pytest.mark.parametrize("value", [Decimal("1.5"), Decimal("1.50"), Decimal("15E-1")])
def test_decimal_equivalence(value):
    assert content(metrics=metrics(value)) == CONTENT


def test_exact_decimal_and_signed_zero():
    assert content(metrics=metrics(Decimal("-0"))) == content(metrics=metrics(Decimal("0.00")))
    a = Decimal("1." + "0" * 8200 + "1")
    b = Decimal("1." + "0" * 8200 + "2")
    assert content(metrics=metrics(a)) != content(metrics=metrics(b))


@pytest.mark.parametrize("field", KEY)
def test_every_series_field_is_required(field):
    missing = dict(KEY)
    del missing[field]
    with pytest.raises(ValidationError):
        SeriesKey(**missing)


def test_null_is_not_omission_and_insertion_order_is_irrelevant():
    assert series_id(SeriesKey(**dict(reversed(list(KEY.items()))))) == SERIES
    omitted = dict(KEY)
    del omitted["qualifier"]
    assert "sr1:" + id_digest("c15.series.v1", omitted) != SERIES


@pytest.mark.parametrize("bad", ["", " DER", "DER ", 7, False, 1.0])
@pytest.mark.parametrize("field", KEY)
def test_strict_series_text(field, bad):
    with pytest.raises(ValidationError):
        SeriesKey(**dict(KEY, **{field: bad}))


@pytest.mark.parametrize("field", ["kind", "section"])
def test_required_text_is_not_nullable(field):
    with pytest.raises(ValidationError):
        SeriesKey(**dict(KEY, **{field: None}))


@pytest.mark.parametrize("bad", ["a" * 63, "a" * 65, "A" * 64, "g" * 64, "a" * 64 + "\n", 1])
def test_claim_id_is_exact(bad):
    with pytest.raises(ValidationError):
        SlotClaim(form="CLAIM_ID", claim_id=bad)


@pytest.mark.parametrize("bad", ["", " 2025-12", 202512, None])
def test_period_stays_strict_text(bad):
    with pytest.raises(ValidationError):
        SlotPeriod(form="REFERENCE_PERIOD", period=bad)


def test_tag_discrimination_and_extra_fields():
    for bad in ({"at": moment(12)}, {"form": "UNKNOWN", "at": moment(12)},
                {"form": "INSTANT", "at": moment(12), "period": "2025-12"},
                {"form": "CLAIM_ID", "period": "a" * 64}):
        with pytest.raises(ValidationError):
            Slot(series_key=SeriesKey(**KEY), slot_time=bad)
    with pytest.raises(ValidationError):
        SeriesKey(**KEY, extra="x")
    assert slot_id(Slot(series_key=SeriesKey(**KEY), slot_time=SlotPeriod(form="REFERENCE_PERIOD", period="a" * 64))) != SLOTS[3]


@pytest.mark.parametrize("value", [moment(12), "2026-01-01T12:00:00Z", "2026-01-01T13:00:00+01:00",
                                  datetime(2026, 1, 1, 13, tzinfo=timezone(timedelta(hours=1)))])
def test_same_instant_same_identity(value):
    assert slot_id(Slot(series_key=SeriesKey(**KEY), slot_time=SlotInstant(form="INSTANT", at=value))) == SLOTS[0]


@pytest.mark.parametrize("bad", ["2026-01-01T12:00:00.1234567Z", "1767268800", "2026-02-30T12:00:00Z",
                                "2026-01-01T12:00:00", datetime(2026, 1, 1), 1767268800])
def test_strict_timestamp_admission(bad):
    with pytest.raises(ValueError):
        SlotInstant(form="INSTANT", at=bad)
    with pytest.raises(ValueError):
        SlotWindow(form="WINDOW_SESSION", window_start=bad, session_start=moment(0))


def test_custom_timezone_rejected_without_callbacks_and_zoneinfo_folds():
    class Custom(tzinfo):
        calls = 0

        def utcoffset(self, dt):
            self.calls += 1
            return timedelta(0)

    zone = Custom()
    with pytest.raises(ValueError):
        SlotInstant(form="INSTANT", at=datetime(2026, 1, 1, tzinfo=zone))
    assert zone.calls == 0
    ids = []
    for fold, hour in ((0, 5), (1, 6)):
        value = SlotInstant(form="INSTANT", at=datetime(2026, 11, 1, 1, 30,
                            tzinfo=ZoneInfo("America/New_York"), fold=fold))
        assert value.at == datetime(2026, 11, 1, hour, 30, tzinfo=timezone.utc)
        ids.append(slot_id(Slot(series_key=SeriesKey(**KEY), slot_time=value)))
    assert ids[0] != ids[1]


def test_order_and_duplicate_keys_fail_closed():
    with pytest.raises(ValidationError, match="ascending"):
        content(metrics=tuple(reversed(metrics())))
    a = metrics()[0]
    for duplicate in (a, a.model_copy(update={"value": Decimal("999")})):
        with pytest.raises(ValidationError, match="unique"):
            content(metrics=(a, duplicate))
    none = a.model_copy(update={"window_id": None})
    assert content(metrics=(none, a))
    with pytest.raises(ValidationError, match="ascending"):
        content(metrics=(a, none))


def test_function_inputs_and_forged_leaf_models_are_revalidated():
    for bad in (list(metrics()), {metrics()[0]}, (dict(name="atr"),)):
        with pytest.raises((ValidationError, TypeError)):
            content(metrics=bad)
    with pytest.raises(ValidationError):
        content(basis="EXPOSED_FIELDS")
    with pytest.raises(ValidationError):
        content(metrics=(metrics()[0].model_copy(update={"value": 1.5}),))
    with pytest.raises(ValidationError):
        content(coverage=Coverage.model_construct(contributing_count=True))
    with pytest.raises(ValidationError):
        series_id(SeriesKey.model_construct(**dict(KEY, kind=3)))


def test_series_dictionary_input_matches_typed_input_without_mutation():
    supplied = dict(KEY)
    assert series_id(supplied) == series_id(SeriesKey(**KEY)) == SERIES
    assert supplied == KEY


@pytest.mark.parametrize("index", range(4))
def test_slot_dictionary_inputs_match_typed_inputs(index):
    supplied = {"series_key": dict(KEY), "slot_time": slot_forms()[index].model_dump(mode="python")}
    before = {"series_key": dict(supplied["series_key"]), "slot_time": dict(supplied["slot_time"])}
    assert slot_id(supplied) == SLOTS[index]
    assert supplied == before


def test_content_accepts_slot_and_coverage_dictionaries_without_mutation():
    supplied_slot = {"series_key": dict(KEY),
                     "slot_time": {"form": "INSTANT", "at": "2026-01-01T13:00:00+01:00"}}
    supplied_coverage = {"earliest_time": "2026-01-01T07:00:00Z",
                         "latest_time": "2026-01-01T12:00:00Z",
                         "contributing_count": 6, "interval": "1h"}
    assert content(slot=supplied_slot, coverage=supplied_coverage) == CONTENT
    assert supplied_slot == {"series_key": KEY,
                             "slot_time": {"form": "INSTANT", "at": "2026-01-01T13:00:00+01:00"}}
    assert supplied_coverage == {"earliest_time": "2026-01-01T07:00:00Z",
                                 "latest_time": "2026-01-01T12:00:00Z",
                                 "contributing_count": 6, "interval": "1h"}


@pytest.mark.parametrize("bad,field", [
    ({k: v for k, v in KEY.items() if k != "qualifier"}, "qualifier"),
    (dict(KEY, kind=7), "kind"),
    (dict(KEY, kind=" DER"), "kind"),
    (dict(KEY, extra="x"), "extra"),
])
def test_invalid_series_dictionaries_are_validated(bad, field):
    with pytest.raises(ValidationError) as caught:
        series_id(bad)
    assert any(field in error["loc"] for error in caught.value.errors())


@pytest.mark.parametrize("bad_time,field", [
    ({"at": "2026-01-01T12:00:00Z"}, "slot_time"),
    ({"form": "UNKNOWN", "at": "2026-01-01T12:00:00Z"}, "slot_time"),
    ({"form": "INSTANT", "at": "2026-01-01T12:00:00.1234567Z"}, "at"),
    ({"form": "INSTANT", "at": "2026-01-01T12:00:00"}, "at"),
    ({"form": "INSTANT", "at": "2026-01-01T12:00:00Z", "period": "2025-12"}, "period"),
    ({"form": "CLAIM_ID", "claim_id": "A" * 64}, "claim_id"),
])
def test_invalid_slot_dictionaries_are_validated(bad_time, field):
    with pytest.raises(ValidationError) as caught:
        slot_id({"series_key": dict(KEY), "slot_time": bad_time})
    assert any(field in error["loc"] for error in caught.value.errors())


@pytest.mark.parametrize("changes,field", [
    ({"slot": {"series_key": dict(KEY, symbol=1),
               "slot_time": {"form": "INSTANT", "at": "2026-01-01T12:00:00Z"}}}, "symbol"),
    ({"coverage": {"contributing_count": True}}, "contributing_count"),
    ({"coverage": {"contributing_count": "6"}}, "contributing_count"),
    ({"coverage": {"earliest_time": "2026-01-01T12:00:00.1234567Z"}}, "earliest_time"),
    ({"coverage": {"extra": "x"}}, "extra"),
])
def test_invalid_content_dictionaries_are_validated(changes, field):
    with pytest.raises(ValidationError) as caught:
        content(**changes)
    assert any(field in error["loc"] for error in caught.value.errors())


def test_dictionary_metric_entries_are_not_admitted_as_metric_instances():
    # Dictionary admission for SeriesKey/Slot/Coverage does not extend to metric entries.
    supplied = tuple(metric.model_dump(mode="python") for metric in metrics())
    with pytest.raises(ValidationError, match="MetricObservation instances"):
        content(metrics=supplied)


def test_immutability_and_json_roundtrips():
    for model in (SeriesKey(**KEY), slot(), *slot_forms()):
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValidationError, match="frozen"):
            setattr(model, field, getattr(model, field))
        assert type(model).model_validate_json(model.model_dump_json()) == model


def test_layer_sensitivity():
    later = Slot(series_key=SeriesKey(**KEY), slot_time=SlotInstant(form="INSTANT", at=moment(13)))
    assert series_id(later.series_key) == SERIES
    assert slot_id(later) != SLOTS[0]
    assert content(slot=later) != CONTENT
    assert content(coverage=Coverage()) != CONTENT
    assert content(metrics=metrics(Decimal("2"))) != CONTENT
    assert content(basis=Basis.SOURCE_INPUT_DIGEST) != CONTENT


def test_cross_process_hash_seed_determinism():
    code = '''
import json
from decimal import Decimal
from traid.fusion import *
k = SeriesKey(**dict({('kind','DER'),('section','candles'),('symbol','BTC-PERP'),('interval','1h'),('source','hyperliquid'),('qualifier',None)}))
s = Slot(series_key=k, slot_time=SlotInstant(form='INSTANT',at='2026-01-01T12:00:00Z'))
c = Coverage(earliest_time='2026-01-01T07:00:00Z',latest_time='2026-01-01T12:00:00Z',contributing_count=6,interval='1h')
m = (MetricObservation(name='atr',state='PRESENT',value=Decimal('1.50'),unit='USD',window_id='atr:2:2026-01-01T12:00:00Z'),MetricObservation(name='vwap',state='WITHHELD',unit='USD',reason='UNTRUSTED'))
print(json.dumps([series_id(k),slot_id(s),exposed_content_id(slot=s,coverage=c,metrics=m,basis=Basis.EXPOSED_FIELDS)]))
'''
    outputs = []
    for seed in ("0", "1", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "src"))
        outputs.append(subprocess.check_output([sys.executable, "-B", "-c", code], env=env, cwd=ROOT, text=True))
    assert len(set(outputs)) == 1
    import json
    assert json.loads(outputs[0]) == [SERIES, SLOTS[0], CONTENT]


def test_scope_is_structural_and_imports_have_no_io():
    assert fusion.ROLE_RULES_ACTIVE == ()
    assert {r.value for r in fusion.EvidenceRole} == {"DESCRIPTIVE_ONLY", "MISSING", "STALE", "UNVERIFIED", "INELIGIBLE"}
    assert not {"fuse", "Delivery", "InputSetRef", "Methodology", "EvidenceUnit", "observation_id",
                "input_set_id", "methodology_id", "assessment_id"} & set(vars(identity))
    tree = ast.parse(Path(identity.__file__).read_text())
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and
                   n.func.id in {"open", "eval", "exec", "__import__"} for n in ast.walk(tree))
    for cls in (SeriesKey, Slot, SlotInstant, SlotWindow, SlotPeriod, SlotClaim):
        assert not {"role", "score", "weight", "probability", "confidence", "activation"} & set(cls.model_fields)
