"""C15 Phase 1 slice 1: exact identity serialization (contract v3.1 section 4, AT-SER-1..12, 8a..8f).

Offline. Standard library plus the repository's own report digest for the compatibility pins.
"""
import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
import enum
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from pydantic import BaseModel
import pytest

import fusion_support as fs
from traid.ai.selection import canonical_json, report_sha256
import traid.fusion.serialization as serialization
from traid.fusion import (
    AmbiguousEnumTypeError, IdentityEncodingError, Unordered, id_digest, id_enc, id_json,
)

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]


def same(a, b) -> bool:
    return id_json(a) == id_json(b)


def dec(digits: int, last: int = 1, exponent: int = 0) -> Decimal:
    return Decimal((0, (1,) * (digits - 1) + (last,), exponent))


def fresh_enum(name: str, module: str, **members):
    return enum.Enum(name, members, module=module, qualname=name)


def unique_module() -> str:
    return f"c15_fixture_{uuid.uuid4().hex}"


# --------------------------------------------------------------------------- Decimal (AT-SER-1,2,12)
def test_at_ser_1_decimals_beyond_8192_digits_are_not_rounded():
    a, b = dec(9000, 1), dec(9000, 2)               # differ only in the 9000th digit
    assert not same(a, b)
    assert same(a, dec(9000, 1))
    assert same(a, Decimal((0, (1,) * 9000 + (0, 0), -2)))   # trailing zeros are not significant
    # the repository converter rounds at 8,192 digits and would merge the two (intended divergence, contract 4.3)
    from traid.whales.models import canonical_json as whales_canonical
    assert whales_canonical({"v": a}) == whales_canonical({"v": b})


def test_at_ser_1_no_precision_context_is_consulted():
    with localcontext() as ctx:
        ctx.prec = 3
        assert not same(dec(50, 1), dec(50, 2))
        assert id_enc(Decimal("123456.789")) == {"$": "dec", "v": "123456789e-3"}


@pytest.mark.parametrize("group", [
    ["1", "1.0", "1.00", "1E+0", "0.1E+1"],
    ["100", "1E+2", "10E+1", "100.000"],
    ["0", "0.00", "0E+5", "-0", "-0.0", "-0E-3"],
    ["-1.5", "-1.50", "-15E-1"],
])
def test_at_ser_2_equivalent_decimal_spellings_share_one_encoding(group):
    assert len({id_json(Decimal(x)) for x in group}) == 1


def test_at_ser_2_distinct_values_stay_distinct():
    assert not same(Decimal("1"), Decimal("1.0000001"))
    assert not same(Decimal("1"), Decimal("-1"))
    assert not same(Decimal("100"), Decimal("1E+3"))


def test_at_ser_2_exact_forms():
    assert id_enc(Decimal("1.0")) == {"$": "dec", "v": "1e0"}
    assert id_enc(Decimal("1E+2")) == {"$": "dec", "v": "1e2"}
    assert id_enc(Decimal("0.00")) == {"$": "dec", "v": "0"}
    assert id_enc(Decimal("-1.50")) == {"$": "dec", "v": "-15e-1"}


def test_at_ser_12_very_large_coefficients_encode_without_digit_limit_errors():
    big = dec(20000, 7)
    assert id_enc(big)["v"].startswith("1" * 5) and id_enc(big)["v"].endswith("7e0")
    assert len(id_digest("c15.test.v1", big)) == 64
    assert len(id_enc(Decimal((0, (1,), 999_000)))["v"]) < 20      # no giant fixed-point expansion


# ------------------------------------------------------------------------------ signed zero (AT-SER-4)
def test_at_ser_4_signed_zero_is_one_identity_and_report_json_keeps_the_repository_spelling():
    assert same(Decimal("-0"), Decimal("0"))

    class M(BaseModel):
        x: Decimal

    assert canonical_json(M(x=Decimal("-0")).model_dump(mode="json")) == '{"x":"-0"}'
    assert report_sha256(M(x=Decimal("-0"))) != report_sha256(M(x=Decimal("0")))


# -------------------------------------------------------------------------- datetime (AT-SER-5, 6)
def test_at_ser_5_equivalent_instants_share_one_encoding():
    plus1 = timezone(timedelta(hours=1))
    a = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    b = datetime(2026, 1, 1, 13, 0, tzinfo=plus1)
    c = datetime(2026, 1, 1, 7, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert id_json(a) == id_json(b) == id_json(c)
    assert id_enc(a) == {"$": "dt", "v": "2026-01-01T12:00:00.000000Z"}
    assert not same(a, a + timedelta(microseconds=1))
    assert id_enc(a + timedelta(microseconds=5))["v"].endswith(".000005Z")


def test_at_ser_5_naive_datetimes_are_rejected():
    with pytest.raises(IdentityEncodingError):
        id_enc(datetime(2026, 1, 1, 12))


def test_at_ser_5_years_before_1000_are_zero_padded():
    assert id_enc(datetime(5, 1, 1, tzinfo=UTC))["v"] == "0005-01-01T00:00:00.000000Z"


def test_at_ser_6_date_is_distinct_from_datetime():
    d, dt = date(2026, 1, 1), datetime(2026, 1, 1, tzinfo=UTC)
    assert id_enc(d) == {"$": "date", "v": "2026-01-01"}
    assert id_enc(dt)["$"] == "dt"
    assert not same(d, dt)


# ------------------------------------------------------------------------------ timedelta (AT-SER-7)
@pytest.mark.parametrize("delta, text", [
    (timedelta(microseconds=1), "1"), (timedelta(microseconds=-1), "-1"), (timedelta(0), "0"),
    (timedelta(days=-1, microseconds=1), "-86399999999"), (timedelta(days=1, seconds=2, microseconds=3), "86402000003"),
    (timedelta(days=-2), "-172800000000"),
])
def test_at_ser_7_timedelta_is_exact_in_microseconds(delta, text):
    assert id_enc(delta) == {"$": "td", "v": text}


def test_at_ser_7_equal_durations_share_an_encoding():
    assert same(timedelta(hours=1), timedelta(seconds=3600))
    assert not same(timedelta(microseconds=1), timedelta(microseconds=-1))


# --------------------------------------------------------------------------------- enums (AT-SER-8*)
def test_at_ser_8_nested_and_recursive_enum_values():
    assert id_enc(fs.Wrapper.INNER)["v"] == id_enc(fs.Mode.FAST)
    assert id_enc(fs.Wrapper.PAIR)["v"] == {"$": "seq", "v": [id_enc(fs.Color.RED), id_enc(fs.Level.ONE)]}
    assert id_enc(fs.Wrapper.NUM)["v"] == id_enc(Decimal("1.5"))      # a Decimal value is normalized recursively
    assert id_enc(fs.Wrapper.INNER) == {"$": "enum", "c": "fusion_support:Wrapper",
                                        "v": {"$": "enum", "c": "fusion_support:Mode", "v": "fast"}}


def test_at_ser_8a_same_named_enums_from_different_modules_differ():
    one = fresh_enum("State", unique_module(), UP="up")
    two = fresh_enum("State", unique_module(), UP="up")
    assert one.UP.value == two.UP.value and one.__name__ == two.__name__
    assert id_enc(one.UP)["c"] != id_enc(two.UP)["c"]
    assert not same(one.UP, two.UP)
    assert id_digest("c15.test.v1", one.UP) != id_digest("c15.test.v1", two.UP)


def test_at_ser_8b_strenum_and_intenum_are_not_their_primitives():
    assert id_enc(fs.Mode.FAST) != id_enc("fast") and not same(fs.Mode.FAST, "fast")
    assert id_enc(fs.Level.ONE) != id_enc(1) and not same(fs.Level.ONE, 1)
    assert not same(fs.Level.ONE, True)
    assert id_enc(fs.Mode.FAST)["$"] == "enum" and id_enc(fs.Level.ONE)["$"] == "enum"
    assert id_enc(True) is True and id_enc(1) == {"$": "int", "v": "1"} and id_enc("1") == "1"


def test_at_ser_8b_flag_values_are_integers():
    Perm = enum.IntFlag("Perm", {"R": 4, "W": 2}, module=unique_module(), qualname="Perm")
    assert id_enc(Perm.R | Perm.W)["v"] == {"$": "int", "v": "6"}


def test_at_ser_8c_enum_tuple_and_set_members():
    assert id_enc((fs.Color.RED, fs.Mode.FAST)) == {"$": "seq", "v": [id_enc(fs.Color.RED), id_enc(fs.Mode.FAST)]}
    assert same(frozenset({fs.Color.RED, fs.Mode.FAST}), frozenset({fs.Mode.FAST, fs.Color.RED}))


def test_at_ser_8e_ambiguous_enum_registrations_are_rejected():
    module = unique_module()
    first, second = fresh_enum("State", module, A=1), fresh_enum("State", module, A=1)
    id_enc(first.A)
    id_enc(first.A)                                              # the same class is fine, repeatedly
    with pytest.raises(AmbiguousEnumTypeError):
        id_enc(second.A)
    with pytest.raises(AmbiguousEnumTypeError):
        id_enc(second.A)                                         # and it stays rejected


def test_at_ser_8e_unidentifiable_enum_types_are_rejected():
    class Local(enum.Enum):
        A = 1

    Local.__module__ = unique_module()
    with pytest.raises(AmbiguousEnumTypeError):                  # "<locals>" in the qualified name
        id_enc(Local.A)
    main = fresh_enum("Anywhere", "__main__", A=1)
    with pytest.raises(AmbiguousEnumTypeError):
        id_enc(main.A)
    assert issubclass(AmbiguousEnumTypeError, IdentityEncodingError)


# ------------------------------------------------------------------------ structured values (AT-SER-9)
def test_at_ser_9_sequences_keep_order_but_sets_and_bags_do_not():
    assert not same((1, 2), (2, 1)) and not same([1, 2], [2, 1])
    assert same((1, 2), [1, 2])
    assert same(frozenset({3, 1, 2}), {2, 3, 1})
    assert same(Unordered(("b", "a", "b")), Unordered(("a", "b", "b")))
    assert not same(Unordered(("a", "b", "b")), Unordered(("a", "b")))        # a bag keeps multiplicity
    assert not same(frozenset({"a"}), Unordered(("a",))) and not same(frozenset({"a"}), ("a",))


def test_at_ser_9_mappings_are_order_independent_and_tagged():
    assert same({"a": 1, "b": 2}, {"b": 2, "a": 1})
    assert id_enc({"b": 1, "a": 2}) == {"$": "map", "v": [["a", {"$": "int", "v": "2"}], ["b", {"$": "int", "v": "1"}]]}


def test_at_ser_9_a_user_dict_with_a_dollar_key_cannot_collide_with_a_tagged_value():
    forged = {"$": "int", "v": "1"}
    assert id_enc(forged) != id_enc(1) and not same(forged, 1)
    assert id_enc(forged)["$"] == "map"


def test_at_ser_9_primitive_types_never_collide():
    values = [1, True, "1", Decimal("1"), (1,), {"1": 1}, None, "1.0", date(2026, 1, 1),
              frozenset({1}), Unordered((1,)), timedelta(microseconds=1)]
    texts = [id_json(v) for v in values]
    assert len(set(texts)) == len(texts)
    assert not same(0, False) and not same(0, Decimal("0")) and not same(0, None) and not same("", None)


def test_at_ser_9_output_is_ascii_compact_json():
    text = id_json({"é": "ü"})
    assert text.isascii() and " " not in text
    assert json.loads(text) == id_enc({"é": "ü"})


def test_at_ser_9_nesting_is_bounded():
    value = ()
    for _ in range(200):
        value = (value,)
    with pytest.raises(IdentityEncodingError):
        id_enc(value)
    cyclic: list = []
    cyclic.append(cyclic)
    with pytest.raises(IdentityEncodingError):
        id_enc(cyclic)


# ---------------------------------------------------------------------------- rejection (AT-SER-10)
@pytest.mark.parametrize("bad", [
    1.5, float("nan"), float("inf"), b"bytes", bytearray(b"x"), complex(1, 2), object(), range(3), {1: "int key"},
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"),
    datetime(2026, 1, 1), (1, 2.5), {"k": float("nan")}, Unordered((1.5,)), frozenset({1.5}),
], ids=repr)
def test_at_ser_10_unsupported_and_non_finite_values_are_rejected(bad):
    with pytest.raises(IdentityEncodingError):
        id_enc(bad)
    with pytest.raises(IdentityEncodingError):
        id_digest("c15.test.v1", bad)


def test_at_ser_10_time_and_models_are_rejected():
    from datetime import time

    class Model(BaseModel):
        x: int = 1

    for bad in (time(1, 2, 3), Model()):
        with pytest.raises(IdentityEncodingError):
            id_enc(bad)


def test_at_ser_10_the_tag_must_be_a_non_empty_string():
    for bad in ("", None, 1, b"x"):
        with pytest.raises(IdentityEncodingError):
            id_digest(bad, 1)


# ------------------------------------------------------------------------------ digests and pins
TAG = "c15.test.v1"


def hand_envelope(inner: str) -> str:
    """Contract 4.4 written out by hand: ID_JSON({"tag": tag, "v": ID_ENC(value)}) where ID_ENC of the envelope dict
    is a `map` whose entries are sorted by encoded key and whose inner value is encoded a second time."""
    return '{"$":"map","v":[["tag","' + TAG + '"],["v",' + inner + ']]}'


# (value, hand-built canonical text of the envelope, sha256 of that text computed with hashlib alone)
VECTORS = {
    "int": (1, hand_envelope('{"$":"map","v":[["$","int"],["v","1"]]}'),
            "3f61d7402209625263a525b7d5cde022b5883fad851d96f1d8075ca161e967fa"),
    "decimal": (Decimal("1.00"), hand_envelope('{"$":"map","v":[["$","dec"],["v","1e0"]]}'),
                "079f926b31824a24641717a288fd86e096b01d9e31b4f07c4ad7c63586747897"),
    "sequence": ((1, "a", None), hand_envelope(
        '{"$":"map","v":[["$","seq"],["v",{"$":"seq","v":[{"$":"map","v":[["$","int"],["v","1"]]},"a",null]}]]}'),
        "c2887dd1d86edfff8562aa3b6baaf0be1c495c54e8affbb879a1183c2e6de71a"),
    "datetime": (datetime(2026, 1, 1, 12, tzinfo=UTC), hand_envelope(
        '{"$":"map","v":[["$","dt"],["v","2026-01-01T12:00:00.000000Z"]]}'),
        "594a62302c35cde42816b0e1d31214db0c261c2bf4b2cf2fbd0396efd63bb1d6"),
    "mapping": ({"b": 1, "a": 2}, hand_envelope(
        '{"$":"map","v":[["$","map"],["v",{"$":"seq","v":[{"$":"seq","v":["a",{"$":"map","v":[["$","int"],["v","2"]]}]},'
        '{"$":"seq","v":["b",{"$":"map","v":[["$","int"],["v","1"]]}]}]}]]}'),
        "b2e4ffe192340468108fd8daeeca86f348953abc0b7f53d203e239aa1e492fb8"),
}


@pytest.mark.parametrize("name", VECTORS)
def test_b1_digest_is_the_literal_contract_4_4_formula(name):
    value, hand_text, fixed_hash = VECTORS[name]
    assert hashlib.sha256(hand_text.encode("ascii")).hexdigest() == fixed_hash        # the vectors are self-consistent
    assert id_json({"tag": TAG, "v": id_enc(value)}) == hand_text                      # ID_JSON(envelope): recursive
    assert id_digest(TAG, value) == fixed_hash


def test_b1_the_envelope_is_encoded_recursively_not_once():
    value = (1, "a")
    once = hashlib.sha256(json.dumps({"tag": TAG, "v": id_enc(value)}, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert id_digest(TAG, value) != once                                              # the v3.1 first attempt
    assert id_digest(TAG, Decimal("1.0")) == id_digest(TAG, Decimal("1.00"))
    assert id_digest(TAG, 1) != id_digest("c15.test.v2", 1)
    assert id_digest(TAG, 1) != id_digest(TAG, "1") != id_digest(TAG, True)


def test_b1_deeply_nested_values_that_id_enc_accepts_are_also_digestible():
    value = ()
    for _ in range(serialization.MAX_DEPTH - 2):
        value = (value,)
    id_enc(value)
    assert len(id_digest(TAG, value)) == 64
    value = {"k": value}
    with pytest.raises(IdentityEncodingError):
        id_digest(TAG, {"k": {"k": {"k": value}}})


def test_golden_digests_pin_the_encoding():
    assert id_digest(TAG, (1, "a", None)) == VECTORS["sequence"][2]
    assert id_digest(TAG, datetime(2026, 1, 1, 12, tzinfo=UTC)) == VECTORS["datetime"][2]


# ------------------------------------------------------------------------ stability (AT-SER-8d)
def run_battery(seed: str) -> list[str]:
    env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")]))
    out = subprocess.run([sys.executable, "-c", "import json, fusion_support; print(json.dumps(fusion_support.battery()))"],
                         env=env, capture_output=True, text=True, check=True, cwd=ROOT)
    return json.loads(out.stdout)


def test_at_ser_8d_encoding_is_stable_in_process_and_across_hash_seeds():
    here = fs.battery()
    assert here == fs.battery()
    assert run_battery("0") == here
    assert run_battery("1") == here
    assert run_battery("987654321") == here


# ------------------------------------------------------- C14 report digest compatibility (AT-SER-8f, 11)
class Report(BaseModel):
    when: datetime
    rate: Decimal
    label: str


REPORT = Report(when=datetime(2026, 1, 1, 12, tzinfo=UTC), rate=Decimal("0.00030"), label="x")


def test_at_ser_8f_report_sha256_is_the_c14_digest_and_is_unchanged_by_this_package():
    expected = hashlib.sha256(json.dumps(REPORT.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert report_sha256(REPORT) == expected
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"\\u00e9","b":1}'
    assert report_sha256(REPORT) == "08e4efef15e4b4dd8bc28c1a1b35a0fc16070ec2c9891472c13f26d3f1ce6c5e"


def test_at_ser_11_report_json_keeps_decimal_spelling_while_identities_do_not():
    a = Report(when=REPORT.when, rate=Decimal("0.00030"), label="x")
    b = Report(when=REPORT.when, rate=Decimal("0.0003"), label="x")
    assert report_sha256(a) != report_sha256(b)                                  # C14 digest sees the spelling
    assert same(a.model_dump(), b.model_dump()) and id_digest("t", a.model_dump()) == id_digest("t", b.model_dump())


def test_at_ser_11_no_separate_reimplementation_of_the_c14_digest_exists_in_the_package():
    for path in (ROOT / "src/traid/fusion").glob("*.py"):
        names = {n.name for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef)}
        assert not {"report_sha256", "canonical_json"} & names, path.name


def test_fusion_package_imports_only_the_standard_library_and_itself():
    serializer_exports = {"AmbiguousEnumTypeError", "IdentityEncodingError", "Unordered", "id_digest", "id_enc", "id_json"}
    model_exports = {"ROLE_RULES_ACTIVE", "Basis", "Comparison", "Coverage", "EvidenceRole", "FusionModel",
                     "InputDigestRef", "MetricObservation", "MetricState", "RawIdentity",
                     "SourceReportedContradiction", "UtcDatetime"}
    # File-specific modules and symbols: approving models must not broaden serialization's dependencies.
    allowed_imports = {
        "serialization.py": {
            "__future__": {"annotations"}, "dataclasses": {"dataclass"},
            "datetime": {"date", "datetime", "timedelta", "timezone"}, "decimal": {"Decimal"},
            "enum": None, "hashlib": None, "json": None, "threading": None,
            "zoneinfo": {"ZoneInfo"}, "pydantic_core": {"TzInfo"},
        },
        "models.py": {
            "__future__": {"annotations"}, "datetime": {"datetime", "timezone"}, "decimal": {"Decimal"},
            "enum": {"StrEnum"}, "re": None, "typing": {"Annotated"},
            "pydantic": {"AfterValidator", "BaseModel", "BeforeValidator", "ConfigDict", "Field",
                         "StrictInt", "StrictStr", "model_validator"},
            "traid.fusion.serialization": {"id_enc"},
        },
        "__init__.py": {"traid.fusion.serialization": serializer_exports, "traid.fusion.models": model_exports},
    }
    for path in (ROOT / "src/traid/fusion").glob("*.py"):
        assert path.name in allowed_imports, path.name
        policy = allowed_imports[path.name]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name in policy and policy[alias.name] is None, (path.name, alias.name)
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, (path.name, "relative import")
                assert node.module in policy and policy[node.module] is not None, (path.name, node.module)
                assert {alias.name for alias in node.names} <= policy[node.module], (path.name, node.module)


# ------------------------------------------------------------- B2: dictionary keys are encoded (section 4.2)
class Cat(enum.StrEnum):
    C10 = "C10"


def test_b2_enum_keys_are_distinct_from_plain_string_keys():
    from traid.ai.models import Category

    assert id_json({Category.C10: 1}) != id_json({"C10": 1})
    assert id_json({Cat.C10: 1}) != id_json({"C10": 1})
    assert id_enc({Cat.C10: 1}) == {"$": "map", "v": [[
        {"$": "enum", "c": f"{Cat.__module__}:Cat", "v": "C10"}, {"$": "int", "v": "1"}]]}
    assert id_enc({"C10": 1}) == {"$": "map", "v": [["C10", {"$": "int", "v": "1"}]]}


def test_b2_keys_keep_type_distinctions_and_digests_differ():
    from traid.ai.models import Category

    assert id_digest(TAG, {Category.C10: 1}) != id_digest(TAG, {"C10": 1})
    assert id_digest(TAG, {Cat.C10: 1}) != id_digest(TAG, {Category.C10: 1})        # different enum classes


def test_b2_encoded_key_order_is_deterministic_and_independent_of_insertion_order():
    one = {"b": 1, Cat.C10: 2, "a": 3, "z": 4}
    two = {"z": 4, "a": 3, Cat.C10: 2, "b": 1}
    assert id_json(one) == id_json(two) and id_digest(TAG, one) == id_digest(TAG, two)
    keys = [json.dumps(k, sort_keys=True, separators=(",", ":")) for k, _ in id_enc(one)["v"]]
    assert keys == sorted(keys)


def test_b2_enum_keys_are_subject_to_enum_validation():
    module = unique_module()
    first = enum.StrEnum("Key", {"A": "a"}, module=module, qualname="Key")
    second = enum.StrEnum("Key", {"A": "a"}, module=module, qualname="Key")
    id_enc({first.A: 1})
    with pytest.raises(AmbiguousEnumTypeError):
        id_enc({second.A: 1})
    with pytest.raises(AmbiguousEnumTypeError):
        id_enc({fresh_str_enum_in_main().A: 1})
    one = enum.StrEnum("Key", {"A": "a"}, module=unique_module(), qualname="Key")
    two = enum.StrEnum("Key", {"A": "a"}, module=unique_module(), qualname="Key")
    assert id_json({one.A: 1}) != id_json({two.A: 1})                               # same name, different modules


def fresh_str_enum_in_main():
    return enum.StrEnum("Anywhere", {"A": "a"}, module="__main__", qualname="Anywhere")


def test_b2_two_distinct_keys_with_one_encoding_are_rejected():
    class Twin(str):
        __hash__ = lambda self: 12345            # noqa: E731
        __eq__ = lambda self, other: self is other  # noqa: E731

    a, b = Twin("k"), Twin("k")
    mapping = {a: 1, b: 2}
    assert len(mapping) == 2
    with pytest.raises(IdentityEncodingError):
        id_enc(mapping)
    with pytest.raises(IdentityEncodingError):
        id_enc({"k": 1, Twin("k"): 2})


@pytest.mark.parametrize("key", [1, True, None, Decimal("1"), (1,), date(2026, 1, 1), 1.5, b"k"], ids=repr)
def test_b2_non_str_keys_are_still_rejected_not_stringified(key):
    with pytest.raises(IdentityEncodingError):
        id_enc({key: 1})


def test_b2_collection_semantics_are_unchanged():
    assert same({"a": 1, "b": 2}, {"b": 2, "a": 1})
    assert id_enc({"b": 1, "a": 2})["v"][0][0] == "a"
    assert not same((1, 2), (2, 1)) and same(frozenset({1, 2}), {2, 1})
    assert same(Unordered(("b", "a", "b")), Unordered(("a", "b", "b")))
    assert id_enc({"é": 1, "z": 2})["v"][0][0] == "é"      # ordered by encoded (escaped) text, deterministic


# ------------------------------------------------ B3: integers independent of PYTHONINTMAXSTRDIGITS
INT_SCRIPT = r'''
import json, sys
from decimal import Decimal
from traid.fusion import id_digest, id_enc, id_json
big = 10 ** 5000
out = {
    "enc_pos": id_enc(big)["v"], "enc_neg": id_enc(-big - 1)["v"], "enc_zero": id_enc(0)["v"],
    "json": id_json(big), "digest": id_digest("c15.test.v1", big), "nested": id_digest("c15.test.v1", (big, {"k": -big})),
    "dec": id_enc(Decimal((0, (1,) * 9000, 0)))["v"][-6:],
}
print(json.dumps(out))
'''


def run_ints(limit: str) -> dict:
    env = dict(os.environ, PYTHONINTMAXSTRDIGITS=limit, PYTHONHASHSEED="0", PYTHONPATH=str(ROOT / "src"))
    out = subprocess.run([sys.executable, "-c", INT_SCRIPT], env=env, capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout)


def test_b3_the_interpreter_digit_limit_is_actually_active_in_the_subprocess():
    env = dict(os.environ, PYTHONINTMAXSTRDIGITS="640")
    out = subprocess.run([sys.executable, "-c", "n = 10**5000\ntry:\n    str(n)\nexcept ValueError:\n    print('limited')"],
                         env=env, capture_output=True, text=True)
    assert out.stdout.strip() == "limited"


def test_b3_integer_identities_do_not_depend_on_the_digit_limit_setting():
    results = {limit: run_ints(limit) for limit in ("0", "640", "4300", "100000")}
    first = results["0"]
    assert all(r == first for r in results.values())
    digits = "1" + "0" * 5000                                   # built as text: no str(int) involved
    assert first["enc_pos"] == digits
    assert first["enc_neg"] == "-" + "1" + "0" * 4999 + "1"
    assert first["enc_zero"] == "0"
    expected_json = '{"$":"int","v":"' + digits + '"}'
    assert first["json"] == expected_json
    hand = hand_envelope('{"$":"map","v":[["$","int"],["v","' + digits + '"]]}')
    assert first["digest"] == hashlib.sha256(hand.encode("ascii")).hexdigest()
    assert first["dec"] == "1111e0"


def test_b3_in_process_integers_cover_signs_sizes_and_subclasses():
    assert id_enc(0) == {"$": "int", "v": "0"} and id_enc(-7) == {"$": "int", "v": "-7"}
    assert id_enc(10 ** 100)["v"] == "1" + "0" * 100
    assert id_enc(-(10 ** 5000))["v"] == "-1" + "0" * 5000
    assert id_enc(2 ** 20000)["v"].endswith("376")                       # 2**20000 ends ...376 (known value)
    assert len(id_enc(2 ** 20000)["v"]) == 6021
    assert not same(10 ** 5000, Decimal(10) ** 5000) and not same(1, True)

    class Number(int):
        pass

    assert id_enc(Number(41)) == {"$": "int", "v": "41"}


def test_b3_decimal_behaviour_is_unchanged():
    assert id_enc(Decimal("1.00")) == {"$": "dec", "v": "1e0"}
    assert same(Decimal("-0"), Decimal("0")) and not same(dec(9000, 1), dec(9000, 2))


# ---- final subclass remediation: overridable conversion methods must not change an identity ----

class _OverStr(str):
    def __str__(self):
        return "other"


class _OverInt(int):
    def __int__(self):
        return 0

    def __index__(self):
        return 0

    def __str__(self):
        return "0"

    def __repr__(self):
        return "0"


def test_b2_str_subclass_with_overridden_str_encodes_its_underlying_value():
    key = _OverStr("original")
    assert key == "original" and str(key) == "other"
    assert id_enc(key) == "original" and type(id_enc(key)) is str
    assert id_json(key) == '"original"'
    assert id_digest("t", key) == id_digest("t", "original") != id_digest("t", "other")


def test_b2_str_subclass_dictionary_key_uses_underlying_value():
    d = {_OverStr("original"): 1}
    assert id_json(d) == id_json({"original": 1})
    assert id_digest("t", d) == id_digest("t", {"original": 1}) != id_digest("t", {"other": 1})
    # ordering stays deterministic and by encoded key
    assert id_json({_OverStr("b"): 1, "a": 2}) == id_json({"a": 2, "b": 1})


def test_b2_str_subclass_collision_is_still_rejected():
    class Apart(_OverStr):                      # distinct as a dict key, yet the same underlying string
        __hash__ = object.__hash__

        def __eq__(self, other):
            return self is other

    d = {Apart("original"): 1, "original": 2}
    assert len(d) == 2
    with pytest.raises(IdentityEncodingError):
        id_enc(d)


def test_b2_enum_keys_stay_distinct_from_overriding_string_keys():
    from traid.ai.models import Category
    assert id_json({Category.C10: 1}) != id_json({_OverStr("C10"): 1})
    assert id_json({_OverStr("C10"): 1}) == id_json({"C10": 1})


def test_b3_int_subclass_with_overridden_int_encodes_its_underlying_value():
    n = _OverInt(7)
    assert n == 7 and int(n) == 0
    assert id_enc(n) == {"$": "int", "v": "7"}
    assert id_enc(_OverInt(-12)) == {"$": "int", "v": "-12"}
    assert id_digest("t", n) == id_digest("t", 7) != id_digest("t", 0)


def test_b3_int_subclass_large_value_stays_exact():
    big = _OverInt(10 ** 5000 + 3)
    assert id_enc(big)["v"] == "1" + "0" * 4999 + "3"
    assert id_digest("t", big) == id_digest("t", 10 ** 5000 + 3)


def test_b3_int_subclass_inside_collections_and_enum_values():
    assert id_json([_OverInt(7)]) == id_json([7])
    assert id_json({"k": _OverInt(7)}) == id_json({"k": 7})


# ---- bounded type policy (contract v3.2, section 4.2b): exact built-in types, restricted enums and timezones ----
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: E402

from pydantic_core import TzInfo  # noqa: E402


class _SubDecimal(Decimal):
    def as_tuple(self):
        return Decimal("9").as_tuple()


class _SubDatetime(datetime):
    year = property(lambda self: 1999)


class _SubDate(date):
    year = property(lambda self: 1999)


class _SubTimedelta(timedelta):
    def __floordiv__(self, other):
        return 5


class _SubList(list):
    def __iter__(self):
        return iter([9])


class _SubTuple(tuple):
    def __iter__(self):
        return iter([9])


class _SubDict(dict):
    def items(self):
        return iter([("z", 9)])


class _SubSet(set):
    def __iter__(self):
        return iter([9])


class _SubFrozenset(frozenset):
    def __iter__(self):
        return iter([9])


class _SubUnordered(fs.Unordered):
    def __init__(self, items):
        self.__dict__["_stored"] = tuple(items)     # the real contents live under another name

    @property
    def items(self):
        return ()


_UTC = timezone.utc
SUBCLASS_CASES = [
    ("Decimal", _SubDecimal("1.5")), ("datetime", _SubDatetime(2026, 1, 1, tzinfo=_UTC)),
    ("date", _SubDate(2026, 3, 4)), ("timedelta", _SubTimedelta(days=1)), ("list", _SubList([1, 2])),
    ("tuple", _SubTuple((1, 2))), ("dict", _SubDict(a=1)), ("set", _SubSet({1, 2})),
    ("frozenset", _SubFrozenset({1, 2})), ("Unordered", _SubUnordered(("a", "b"))),
]


@pytest.mark.parametrize("name,value", SUBCLASS_CASES, ids=[n for n, _ in SUBCLASS_CASES])
def test_policy_subclasses_of_builtin_types_are_rejected_with_a_stable_code(name, value):
    with pytest.raises(IdentityEncodingError) as caught:
        id_enc(value)
    assert caught.value.code == "ID_TYPE_SUBCLASS_REJECTED"
    with pytest.raises(IdentityEncodingError):
        id_digest("t", value)
    with pytest.raises(IdentityEncodingError):
        id_enc({"k": [value]})                      # also when nested


def test_policy_exact_builtin_types_are_accepted():
    for value in (Decimal("1.5"), datetime(2026, 1, 1, tzinfo=_UTC), date(2026, 1, 1), timedelta(1), [1], (1,),
                  {"a": 1}, {1}, frozenset({1}), fs.Unordered((1,)), "s", 7, None, True):
        id_enc(value)


def test_policy_str_and_int_subclasses_still_use_their_base_value():
    class S(str):
        def __str__(self):
            return "other"

    class I(int):
        def __int__(self):
            return 0

    assert id_enc(S("a")) == "a" and id_enc(I(7)) == {"$": "int", "v": "7"}


def test_policy_standard_namedtuple_and_ordereddict_are_rejected():
    from collections import OrderedDict, namedtuple
    with pytest.raises(IdentityEncodingError):
        id_enc(namedtuple("P", "x")(1))
    with pytest.raises(IdentityEncodingError):
        id_enc(OrderedDict(a=1))


# F1: an Enum whose ``value`` property is overridden to return zero
class _ValueZero(enum.Enum):
    A = 1
    B = 2

    @property
    def value(self):
        return 0


class _ValueShadow(enum.IntEnum):
    A = 1
    value = 2                  # a member named like the accessor


def test_f1_enum_with_overridden_value_is_rejected_and_members_never_collide():
    assert _ValueZero.A.value == _ValueZero.B.value == 0          # the attack: both members read 0
    for member in (_ValueZero.A, _ValueZero.B):
        with pytest.raises(IdentityEncodingError) as caught:
            id_enc(member)
        assert caught.value.code == "ID_ENUM_NONSTANDARD"
    with pytest.raises(IdentityEncodingError):
        id_digest("t", {"k": _ValueZero.A})
    with pytest.raises(IdentityEncodingError):
        id_enc(_ValueShadow.A)


class _Declared(enum.Enum):
    def __new__(cls, raw, label):
        member = object.__new__(cls)
        member._value_ = raw
        member.label = label
        return member

    A = (1, "alpha")
    B = (2, "beta")


class _Perm(enum.IntFlag):
    R = 4
    W = 2


class _Alias(enum.Enum):
    A = 1
    B = 1                       # alias of A


def test_f1_standard_enums_keep_their_declared_value():
    assert id_enc(_Declared.A) == {"$": "enum", "c": f"{_Declared.__module__}:_Declared", "v": {"$": "int", "v": "1"}}
    assert id_digest("t", _Declared.A) != id_digest("t", _Declared.B)
    assert id_enc(_Perm.R | _Perm.W)["v"] == {"$": "int", "v": "6"}
    assert id_enc(_Alias.B) == id_enc(_Alias.A)
    for member in (fs.Color.RED, fs.Mode.FAST, fs.Level.ONE, fs.Wrapper.PAIR, fs.Wrapper.NUM):
        id_enc(member)


# F2: an Unordered subclass whose ``items`` hides the stored contents
def test_f2_unordered_subclass_cannot_hide_its_items():
    hidden = _SubUnordered(("a", "b"))
    assert hidden.items == () and hidden._stored == ("a", "b")      # the attack: stored contents are not visible
    with pytest.raises(IdentityEncodingError) as caught:
        id_enc(hidden)
    assert caught.value.code == "ID_TYPE_SUBCLASS_REJECTED"
    assert id_digest("t", fs.Unordered(("a", "b"))) != id_digest("t", fs.Unordered(()))


# F3: a stateful custom timezone gives a different offset on every call
class _Flapping(timezone.__mro__[1]):                              # datetime.tzinfo
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=self.calls)

    def dst(self, dt):
        return None

    def tzname(self, dt):
        return "FLAP"


def test_f3_stateful_custom_timezone_is_rejected():
    value = datetime(2026, 1, 1, 12, tzinfo=_Flapping())
    assert value.utcoffset() != value.utcoffset()                  # the attack: unstable offset
    for _ in range(2):
        with pytest.raises(IdentityEncodingError) as caught:
            id_enc(value)
        assert caught.value.code == "ID_TZ_UNSUPPORTED"
    with pytest.raises(IdentityEncodingError):
        id_digest("t", [value])


def test_timezone_policy_accepts_utc_fixed_offset_zoneinfo_and_pydantic_tzinfo():
    expected = {"$": "dt", "v": "2026-01-01T10:00:00.000000Z"}
    assert id_enc(datetime(2026, 1, 1, 10, tzinfo=timezone.utc)) == expected
    assert id_enc(datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2)))) == expected
    assert id_enc(datetime(2026, 1, 1, 12, tzinfo=TzInfo(7200))) == expected
    try:
        paris = ZoneInfo("Europe/Paris")
    except ZoneInfoNotFoundError:                                  # pragma: no cover - no tz database installed
        pytest.skip("no tz database")
    assert id_enc(datetime(2026, 1, 1, 11, tzinfo=paris)) == expected          # CET, UTC+1


def test_timezone_policy_zoneinfo_fold_is_honoured():
    try:
        ny = ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:                                  # pragma: no cover
        pytest.skip("no tz database")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=ny, fold=0)        # EDT, UTC-4
    second = datetime(2026, 11, 1, 1, 30, tzinfo=ny, fold=1)       # EST, UTC-5
    assert id_enc(first)["v"] == "2026-11-01T05:30:00.000000Z"
    assert id_enc(second)["v"] == "2026-11-01T06:30:00.000000Z"
    assert id_digest("t", first) != id_digest("t", second)


def test_timezone_policy_rejects_zoneinfo_and_timezone_subclasses_and_naive():
    class MyZone(ZoneInfo):
        pass

    try:
        zone = MyZone("UTC")
    except ZoneInfoNotFoundError:                                  # pragma: no cover
        pytest.skip("no tz database")
    with pytest.raises(IdentityEncodingError) as caught:
        id_enc(datetime(2026, 1, 1, tzinfo=zone))
    assert caught.value.code == "ID_TZ_UNSUPPORTED"
    with pytest.raises(IdentityEncodingError):
        id_enc(datetime(2026, 1, 1))


def test_policy_previous_encodings_are_unchanged():
    assert id_json({"a": [Decimal("1.50"), date(2026, 1, 1)]}) == id_json({"a": (Decimal("1.5"), date(2026, 1, 1))})
    assert id_enc(timedelta(days=2, seconds=3, microseconds=4)) == {"$": "td", "v": "172803000004"}
