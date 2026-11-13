"""C15 Slice 4, v3.5 §21.8: structural fixtures, never source mappings."""
import ast
from datetime import datetime, timedelta, timezone, tzinfo
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core import TzInfo
import pytest

import traid.fusion as fusion
import traid.fusion.input_identity as module
from traid.fusion import Delivery, InputDigestRef, InputSetRef, id_digest, id_json, input_set_id

ROOT = Path(__file__).resolve().parents[1]
SOURCE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
RECEIVED = SOURCE + timedelta(seconds=1)
D0 = dict(source="hyperliquid", source_type="REST", source_id="book-1",
          source_timestamp=SOURCE, received_timestamp=RECEIVED)
G0 = ("sha256-canonical-candles-v1", "b" * 64)
VECTORS = (
    "is1:71ae34903b46b3741b7c856c674db3997ac7d433602487a8b5c353e390e59320",
    "is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b",
    "is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb",
    "is1:cb2e6ddeafe7c39450cfb3cf9d78f6c40893a2527dc8fb2e56d682b2d909b6ab",
)
JSON_FIXTURES = (
    '{"$":"map","v":[["delivery",{"$":"map","v":[["received_timestamp",{"$":"dt","v":"2026-01-01T12:00:01.000000Z"}],["source","hyperliquid"],["source_id","book-1"],["source_timestamp",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}],["source_type","REST"]]}],["digest",null],["state","COMPLETE_SINGLE"]]}',
    '{"$":"map","v":[["delivery",{"$":"map","v":[["received_timestamp",{"$":"dt","v":"2026-01-01T12:00:01.000000Z"}],["source","hyperliquid"],["source_id","book-1"],["source_timestamp",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}],["source_type","REST"]]}],["digest",{"$":"seq","v":["sha256-canonical-candles-v1","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]}],["state","DIGEST_WITH_NEWEST"]]}',
    '{"$":"map","v":[["delivery",null],["digest",null],["state","UNAVAILABLE"]]}',
    '{"$":"map","v":[["delivery",null],["digest",null],["state","KNOWN_EMPTY"]]}',
)
SENSITIVITY = (
    ({"received_timestamp": RECEIVED + timedelta(seconds=1)}, G0,
     "is1:033dbc5e0d778620c89ae961ac828edc98e765bec2449916a64c864bc99194dc"),
    ({"source_timestamp": None}, G0,
     "is1:fcb087cf940e56f83823a53f2b3ccb2c01f3ca1442a984ef61b6207ece15b0f9"),
    ({"source_id": None}, G0,
     "is1:91df3539e71cbbccfc9fa4eb9e351b901dd4d3cd655e1c2537ad85a5df24f42b"),
    ({}, ("sha256-canonical-funding-v1", "b" * 64),
     "is1:481fac8425c0a8db3a421eb846a9a9053bc17639f64627e77623089dab876464"),
    ({}, (G0[0], "c" * 64),
     "is1:3fc84508b950946469f7bcd7bf3008ccad22ffa7b296ba3c566919c206cb964b"),
)


def ref(**changes):
    values = dict(state="DIGEST_WITH_NEWEST", digest=G0, delivery=Delivery(**D0))
    values.update(changes)
    return InputSetRef(**values)


def raw_vectors():
    return (
        dict(state="COMPLETE_SINGLE", digest=None, delivery=dict(D0)),
        dict(state="DIGEST_WITH_NEWEST", digest=G0, delivery=dict(D0)),
        dict(state="UNAVAILABLE", digest=None, delivery=None),
        dict(state="KNOWN_EMPTY", digest=None, delivery=None),
    )


@pytest.mark.parametrize("index", range(3))
def test_constructible_state_goldens(index):
    assert input_set_id(InputSetRef(**raw_vectors()[index])) == VECTORS[index]


def test_reserved_vector_is_raw_serializer_fixture_only():
    assert "is1:" + id_digest("c15.is.v1", raw_vectors()[3]) == VECTORS[3]
    assert len(set(VECTORS)) == 4
    with pytest.raises(ValidationError):
        InputSetRef(**raw_vectors()[3])
    with pytest.raises(ValidationError):
        input_set_id(raw_vectors()[3])


@pytest.mark.parametrize("index", range(4))
def test_four_complete_json_fixtures(index):
    assert id_json(raw_vectors()[index]) == JSON_FIXTURES[index]


def test_actual_projection_bytes_and_string_tag(monkeypatch):
    captured = []
    real = module.id_digest

    def capture(tag, value):
        captured.append((tag, value))
        return real(tag, value)

    monkeypatch.setattr(module, "id_digest", capture)
    for index in range(3):
        assert input_set_id(InputSetRef(**raw_vectors()[index])) == VECTORS[index]
        tag, value = captured[-1]
        assert tag == "c15.is.v1"
        assert id_json(value) == JSON_FIXTURES[index]
        assert type(value["state"]) is str
        assert set(value) == {"state", "digest", "delivery"}
        if value["delivery"] is not None:
            assert set(value["delivery"]) == set(D0)
        if value["digest"] is not None:
            assert type(value["digest"]) is tuple and value["digest"] == G0


@pytest.mark.parametrize("delivery_changes,digest,expected", SENSITIVITY)
def test_five_sensitivity_goldens(delivery_changes, digest, expected):
    assert input_set_id(ref(delivery=Delivery(**dict(D0, **delivery_changes)), digest=digest)) == expected
    assert expected != VECTORS[1]


@pytest.mark.parametrize("field,value", [("source", "other"), ("source_type", "WEBSOCKET"),
                                        ("source_id", "book-2"),
                                        ("source_timestamp", SOURCE - timedelta(microseconds=1))])
def test_other_delivery_field_changes_affect_identity(field, value):
    assert input_set_id(ref(delivery=Delivery(**dict(D0, **{field: value})))) != VECTORS[1]


def test_digest_pair_order_nulls_and_omission_are_not_interchangeable():
    assert input_set_id(ref(digest=list(G0))) == VECTORS[1]
    value = raw_vectors()[1]
    for changed in (dict(value, digest=tuple(reversed(G0))),
                    dict(value, digest={"algorithm": G0[0], "digest": G0[1]}),
                    {k: v for k, v in value.items() if k != "delivery"}):
        assert "is1:" + id_digest("c15.is.v1", changed) != VECTORS[1]
        with pytest.raises(ValidationError):
            input_set_id(changed)


@pytest.mark.parametrize("state,has_digest,has_delivery", itertools.product(
    ["COMPLETE_SINGLE", "DIGEST_WITH_NEWEST", "UNAVAILABLE", "KNOWN_EMPTY", "UNKNOWN"], [False, True], [False, True]))
def test_state_presence_matrix(state, has_digest, has_delivery):
    values = dict(state=state, digest=G0 if has_digest else None, delivery=Delivery(**D0) if has_delivery else None)
    allowed = {("COMPLETE_SINGLE", False, True), ("DIGEST_WITH_NEWEST", True, True), ("UNAVAILABLE", False, False)}
    if (state, has_digest, has_delivery) in allowed:
        assert input_set_id(InputSetRef(**values))
    else:
        with pytest.raises(ValidationError):
            InputSetRef(**values)


@pytest.mark.parametrize("field", ["state", "digest", "delivery"])
def test_input_reference_requires_all_fields(field):
    values = raw_vectors()[1]
    del values[field]
    with pytest.raises(ValidationError):
        InputSetRef(**values)


@pytest.mark.parametrize("field", D0)
def test_delivery_requires_all_fields_including_explicit_nulls(field):
    values = dict(D0)
    del values[field]
    with pytest.raises(ValidationError):
        Delivery(**values)


@pytest.mark.parametrize("field", ["source", "source_type", "source_id"])
@pytest.mark.parametrize("value", ["", " x", "x ", 1, True, 1.5])
def test_strict_delivery_text(field, value):
    with pytest.raises(ValidationError):
        Delivery(**dict(D0, **{field: value}))


@pytest.mark.parametrize("value", [None, 1, True, 1.5, (), (G0[0],), (*G0, "extra"),
                                  {"algorithm": G0[0], "digest": G0[1]},
                                  ("", G0[1]), (" sha256", G0[1]), (1, G0[1]),
                                  (G0[0], "b" * 63), (G0[0], "b" * 65), (G0[0], "B" * 64),
                                  (G0[0], "b" * 64 + "\n"), (G0[0], 1.5)])
def test_invalid_digest_pairs(value):
    with pytest.raises(ValidationError):
        ref(digest=value)


@pytest.mark.parametrize("value", ["2026-01-01T13:00:01+01:00", RECEIVED,
                                  datetime(2026, 1, 1, 13, 0, 1, tzinfo=timezone(timedelta(hours=1))),
                                  datetime(2026, 1, 1, 13, 0, 1, tzinfo=TzInfo(3600))])
def test_receipt_normalization(value):
    delivery = Delivery(**dict(D0, received_timestamp=value))
    assert delivery.received_timestamp == RECEIVED and delivery.received_timestamp.tzinfo is timezone.utc
    assert input_set_id(ref(delivery=delivery)) == VECTORS[1]


@pytest.mark.parametrize("field", ["source_timestamp", "received_timestamp"])
@pytest.mark.parametrize("value", ["2026-01-01T12:00:00.1234567Z", "1767268800", "2026-02-30T12:00:00Z",
                                  "2026-01-01T12:00:00", datetime(2026, 1, 1), 1.5])
def test_bad_timestamp_admission(field, value):
    with pytest.raises(ValueError):
        Delivery(**dict(D0, **{field: value}))


def test_receipt_invariant_equality_null_and_microsecond_precision():
    assert Delivery(**dict(D0, received_timestamp=SOURCE))
    assert Delivery(**dict(D0, source_timestamp=None))
    with pytest.raises(ValidationError, match="cannot precede"):
        Delivery(**dict(D0, received_timestamp=SOURCE - timedelta(microseconds=1)))
    a = Delivery(**dict(D0, received_timestamp="2026-01-01T12:00:01.000001Z"))
    b = Delivery(**dict(D0, received_timestamp="2026-01-01T12:00:01.000002Z"))
    assert a.received_timestamp.microsecond == 1
    assert input_set_id(ref(delivery=a)) != input_set_id(ref(delivery=b))


def test_timezone_callback_rejection_and_zoneinfo_folds():
    class Custom(tzinfo):
        calls = 0

        def utcoffset(self, dt):
            self.calls += 1
            return timedelta(0)

    custom = Custom()
    with pytest.raises(ValueError):
        Delivery(**dict(D0, source_timestamp=datetime(2026, 1, 1, tzinfo=custom)))
    assert custom.calls == 0
    values = []
    for fold, hour in ((0, 5), (1, 6)):
        time = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=fold)
        delivery = Delivery(**dict(D0, source_timestamp=None, received_timestamp=time))
        assert delivery.received_timestamp == datetime(2026, 11, 1, hour, 30, tzinfo=timezone.utc)
        values.append(input_set_id(ref(delivery=delivery)))
    assert values[0] != values[1]


def test_frozen_models_extra_fields_and_roundtrips():
    for model in (Delivery(**D0), ref(), ref(state="UNAVAILABLE", digest=None, delivery=None)):
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValidationError, match="frozen"):
            setattr(model, field, getattr(model, field))
        with pytest.raises(ValidationError):
            type(model).model_validate(dict(model.model_dump(), extra="x"))
        assert type(model).model_validate_json(model.model_dump_json()) == model
    assert set(Delivery.model_fields) == set(D0)
    assert set(InputSetRef.model_fields) == {"state", "digest", "delivery"}


def test_known_empty_rejected_by_public_validation_construction_and_copy():
    bad = raw_vectors()[3]
    for build in (lambda: InputSetRef(**bad), lambda: InputSetRef.model_construct(**bad),
                  lambda: InputSetRef.model_validate(bad), lambda: InputSetRef.model_validate_json(json.dumps(bad)),
                  lambda: TypeAdapter(InputSetRef).validate_python(bad),
                  lambda: ref(state="UNAVAILABLE", digest=None, delivery=None).model_copy(update={"state": "KNOWN_EMPTY"})):
        with pytest.raises(ValidationError):
            build()


def test_forged_instances_cannot_be_hashed():
    forged = BaseModel.model_construct.__func__(InputSetRef, **raw_vectors()[3])
    with pytest.raises(ValidationError):
        input_set_id(forged)
    forged_delivery = BaseModel.model_construct.__func__(Delivery, **dict(D0, source=1.5))
    forged_ref = BaseModel.model_copy(ref(), update={"delivery": forged_delivery})
    with pytest.raises(ValidationError):
        input_set_id(forged_ref)
    with pytest.raises(ValidationError):
        input_set_id(BaseModel.model_copy(ref(), update={"digest": ("", "x")}))
    with pytest.raises(ValidationError):
        Delivery.model_construct(**dict(D0, received_timestamp=SOURCE - timedelta(seconds=1)))


def test_dictionary_inputs_and_copy_are_validated_without_input_mutation():
    values = raw_vectors()[1]
    assert input_set_id(values) == VECTORS[1]
    assert values == raw_vectors()[1]
    assert ref().model_copy(deep=True) == ref()
    assert input_set_id(ref().model_copy(update={"digest": list(G0)})) == VECTORS[1]
    assert InputDigestRef(algorithm=G0[0], digest=G0[1]).digest == G0[1]


def test_cross_process_hash_seed_determinism():
    code = '''
import json
from traid.fusion import Delivery, InputSetRef, input_set_id
d = Delivery(**dict({('source','hyperliquid'),('source_type','REST'),('source_id','book-1'),('source_timestamp','2026-01-01T12:00:00Z'),('received_timestamp','2026-01-01T12:00:01Z')}))
refs = [InputSetRef(state='COMPLETE_SINGLE',digest=None,delivery=d),InputSetRef(state='DIGEST_WITH_NEWEST',digest=('sha256-canonical-candles-v1','b'*64),delivery=d),InputSetRef(state='UNAVAILABLE',digest=None,delivery=None)]
print(json.dumps([input_set_id(r) for r in refs]))
'''
    for seed in ("0", "1", "42"):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "src"))
        output = subprocess.check_output([sys.executable, "-B", "-c", code], cwd=ROOT, env=env, text=True)
        assert json.loads(output) == list(VECTORS[:3])


def test_identity_equality_carries_no_lineage_or_source_mapping_authority():
    assert input_set_id(ref(state="UNAVAILABLE", digest=None, delivery=None)) == VECTORS[2]
    assert not {"observation_id", "methodology_id", "assessment_id", "Methodology", "EvidenceUnit",
                "fuse", "LineageEdge", "Relation"} & set(vars(fusion))
    assert fusion.ROLE_RULES_ACTIVE == ()
    assert {x.value for x in fusion.EvidenceRole} == {"DESCRIPTIVE_ONLY", "MISSING", "STALE", "UNVERIFIED", "INELIGIBLE"}
    tree = ast.parse(Path(module.__file__).read_text())
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports == {"__future__", "typing", "pydantic", "traid.fusion.models", "traid.fusion.serialization"}
    assert not any(isinstance(n, ast.Import) for n in ast.walk(tree))
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and
                   n.func.id in {"open", "exec", "eval", "__import__"} for n in ast.walk(tree))
