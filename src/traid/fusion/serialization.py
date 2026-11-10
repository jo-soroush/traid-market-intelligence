"""V1-C15 Phase 1, slice 1: exact identity serialization (contract v3.1 section 4).

``id_enc`` maps a value to a typed, tagged JSON structure used ONLY for C15 identities. It is deliberately
separate from the C14-compatible report digest (``traid.ai.selection.report_sha256``), which this module never
imports, reimplements or alters. No upstream TraID module is imported; the only non-stdlib name is pydantic_core.TzInfo, recognised by type.

Implemented here: exact Decimal encoding (no context, no rounding), signed-zero collapse, UTC datetimes, distinct
dates, exact timedeltas, recursive enums with module-qualified type identity, ordered and unordered collections,
and explicit rejection of anything else. Nothing else (models, adapters, relations) belongs to this slice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import enum
import hashlib
import json
import threading
from zoneinfo import ZoneInfo

try:                                                  # pydantic's own fixed-offset tzinfo, produced when it parses ISO text
    from pydantic_core import TzInfo as _PydanticTzInfo
except ImportError:                                   # pragma: no cover - pydantic is a project dependency
    _PydanticTzInfo = None

MAX_DEPTH = 64
# id_digest encodes the already-encoded value a second time (contract 4.4); each source level becomes at most
# three nested containers (map, entry list, pair), so the envelope pass needs a proportionally larger bound.
ENVELOPE_DEPTH = 4 * MAX_DEPTH


class IdentityEncodingError(ValueError):
    """The value has no defined identity encoding. Never coerced. ``code`` is a stable failure code (contract 4.2b)."""

    def __init__(self, message: str = "", code: str = "ID_ENCODING") -> None:
        super().__init__(message)
        self.code = code


class AmbiguousEnumTypeError(IdentityEncodingError):
    """An enum type name cannot be tied to exactly one class."""


@dataclass(frozen=True)
class Unordered:
    """Adapter declaration: a sequence whose order carries no meaning (encoded as a sorted multiset)."""
    items: tuple

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


# Contract 4.2b: bounded type policy. Exact built-in types only (a subclass can override accessors or iteration, so it
# is rejected, never coerced). Only str and int subclasses are accepted: their base value is extracted through
# str.__str__ / int.__int__ and no override can reach it. Timezones: exact timezone, ZoneInfo or pydantic TzInfo.
_TZ_TYPES = frozenset(t for t in (timezone, ZoneInfo, _PydanticTzInfo) if t is not None)
_REGISTRY: dict[str, type] = {}
_LOCK = threading.Lock()


def _enum_type_key(cls: type) -> str:
    module = getattr(cls, "__module__", None)
    qualname = getattr(cls, "__qualname__", None)
    if not isinstance(module, str) or not module or not isinstance(qualname, str) or not qualname:
        raise AmbiguousEnumTypeError("enum type has no module or qualified name")
    if module == "__main__" or "<locals>" in qualname:
        raise AmbiguousEnumTypeError(f"enum type {module}:{qualname} does not identify one class across runs")
    key = f"{module}:{qualname}"
    with _LOCK:
        known = _REGISTRY.setdefault(key, cls)
    if known is not cls:
        raise AmbiguousEnumTypeError(f"two distinct enum classes share the identity {key}")
    return key


def _exact(v, cls: type) -> None:
    if type(v) is not cls:
        raise IdentityEncodingError(f"subclass {type(v).__qualname__} of {cls.__qualname__} is not accepted",
                                    "ID_TYPE_SUBCLASS_REJECTED")


def _enum_value(v: enum.Enum):
    """The stored member value, with nonstandard value access rejected (contract 4.2b)."""
    cls = type(v)
    for klass in cls.__mro__:
        if klass.__module__ not in ("enum", "builtins") and ("value" in vars(klass) or "_value_" in vars(klass)):
            raise IdentityEncodingError(f"enum {cls.__qualname__} overrides value access", "ID_ENUM_NONSTANDARD")
    try:
        value = object.__getattribute__(v, "_value_")
        declared = cls(value) is v
    except Exception as error:
        raise IdentityEncodingError(f"enum {cls.__qualname__} member value is not recoverable",
                                    "ID_ENUM_NONSTANDARD") from error
    if not declared:
        raise IdentityEncodingError(f"enum {cls.__qualname__} member value does not resolve to its member",
                                    "ID_ENUM_NONSTANDARD")
    return value


def _decimal(value: Decimal) -> str:
    if not Decimal.is_finite(value):                 # base-class calls throughout: subclass overrides are ignored
        raise IdentityEncodingError("non-finite Decimal")
    sign, digits, exponent = Decimal.as_tuple(value)
    coefficient = "".join(map(str, digits))
    stripped = coefficient.rstrip("0")
    if not stripped:
        return "0"                                   # -0 and 0 are one economic value (contract 4.3)
    exponent += len(coefficient) - len(stripped)
    return f"{'-' if sign else ''}{stripped}e{exponent}"


def _datetime(value: datetime) -> str:
    """UTC text of an aware datetime, read only through base-class accessors (a subclass cannot change it)."""
    zone = datetime.tzinfo.__get__(value)
    if zone is None:
        raise IdentityEncodingError("naive datetime")
    if type(zone) not in _TZ_TYPES:
        raise IdentityEncodingError(f"timezone type {type(zone).__qualname__} is not accepted", "ID_TZ_UNSUPPORTED")
    offset = datetime.utcoffset(value)                # evaluated once; honours fold for ZoneInfo
    if offset is None:
        raise IdentityEncodingError("naive datetime")
    try:
        u = datetime(datetime.year.__get__(value), datetime.month.__get__(value), datetime.day.__get__(value),
                     datetime.hour.__get__(value), datetime.minute.__get__(value),
                     datetime.second.__get__(value), datetime.microsecond.__get__(value)) - offset
    except (OverflowError, ValueError) as error:
        raise IdentityEncodingError("datetime outside the UTC range") from error
    return (f"{u.year:04d}-{u.month:02d}-{u.day:02d}T{u.hour:02d}:{u.minute:02d}:{u.second:02d}"
            f".{u.microsecond:06d}Z")


def _int(value: int) -> str:
    """Base-10 text of an integer of any size. ``str(int)`` is deliberately not used: it is limited by the
    interpreter setting ``sys.set_int_max_str_digits`` / ``PYTHONINTMAXSTRDIGITS``, which would make an identity
    depend on the environment. ``Decimal(int)`` is exact and has no such limit."""
    sign, digits, _ = Decimal(int.__int__(value)).as_tuple()   # base-class call: ignores an overridden __int__
    return f"{'-' if sign else ''}{''.join(map(str, digits))}"


def _sorted(encoded: list, *, allow_duplicates: bool) -> list:
    keyed = sorted(((json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False), e)
                    for e in encoded), key=lambda pair: pair[0])
    texts = [k for k, _ in keyed]
    if not allow_duplicates and len(set(texts)) != len(texts):
        raise IdentityEncodingError("duplicate element in a set")
    return [e for _, e in keyed]


def _encode(v, depth: int, limit: int = MAX_DEPTH):
    if depth > limit:
        raise IdentityEncodingError("value nested too deeply")
    if v is None:
        return None
    if isinstance(v, enum.Enum):                       # before str, int and bool: an Enum may subclass them
        return {"$": "enum", "c": _enum_type_key(type(v)), "v": _encode(_enum_value(v), depth + 1, limit)}
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return str.__str__(v)                           # base-class call: ignores an overridden __str__
    if isinstance(v, int):
        return {"$": "int", "v": _int(v)}
    if isinstance(v, Decimal):
        _exact(v, Decimal)
        return {"$": "dec", "v": _decimal(v)}
    if isinstance(v, datetime):                        # before date: datetime is a date subclass
        _exact(v, datetime)
        return {"$": "dt", "v": _datetime(v)}
    if isinstance(v, date):
        _exact(v, date)
        return {"$": "date", "v": f"{date.year.__get__(v):04d}-{date.month.__get__(v):02d}-{date.day.__get__(v):02d}"}
    if isinstance(v, timedelta):
        _exact(v, timedelta)
        return {"$": "td", "v": _int((timedelta.days.__get__(v) * 86400 + timedelta.seconds.__get__(v)) * 1_000_000
                                  + timedelta.microseconds.__get__(v))}
    if isinstance(v, (set, frozenset)):
        _exact(v, set if isinstance(v, set) else frozenset)
        items = set.__iter__(v) if isinstance(v, set) else frozenset.__iter__(v)
        return {"$": "set", "v": _sorted([_encode(x, depth + 1, limit) for x in items], allow_duplicates=False)}
    if isinstance(v, Unordered):
        _exact(v, Unordered)
        return {"$": "bag", "v": _sorted([_encode(x, depth + 1, limit) for x in v.items], allow_duplicates=True)}
    if isinstance(v, dict):
        _exact(v, dict)
        entries = []
        for key, item in dict.items(v):
            if not isinstance(key, str):                     # str, StrEnum and (str, Enum) only (contract 4.2)
                raise IdentityEncodingError("mapping keys must be str")
            entries.append((_encode(key, depth + 1, limit), _encode(item, depth + 1, limit)))
        keyed = sorted(((_dumps(k), k, i) for k, i in entries), key=lambda triple: triple[0])
        texts = [t for t, _, _ in keyed]
        if len(set(texts)) != len(texts):
            raise IdentityEncodingError("two distinct mapping keys share one encoding")
        return {"$": "map", "v": [[k, i] for _, k, i in keyed]}
    if isinstance(v, (tuple, list)):
        _exact(v, list if isinstance(v, list) else tuple)
        items = list.__iter__(v) if isinstance(v, list) else tuple.__iter__(v)
        return {"$": "seq", "v": [_encode(x, depth + 1, limit) for x in items]}
    raise IdentityEncodingError(f"unsupported type {type(v).__qualname__}")


def _encode_envelope(value):
    return _encode(value, 0, ENVELOPE_DEPTH)


def id_enc(value):
    """Typed, tagged, JSON-compatible encoding of ``value`` (contract v3.1 section 4.2). Raises
    ``IdentityEncodingError`` for unsupported or non-finite input and ``AmbiguousEnumTypeError`` for an enum
    type whose name does not identify one class."""
    return _encode(value, 0)


def _dumps(structure) -> str:
    return json.dumps(structure, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def id_json(value) -> str:
    """Canonical JSON text of ``id_enc(value)``."""
    return _dumps(id_enc(value))


def id_digest(tag: str, value) -> str:
    """``HID`` of contract v3.1 section 4.4, literally: ``sha256(ID_JSON({"tag": tag, "v": ID_ENC(value)}))``.

    ``ID_JSON(x)`` is ``json.dumps(ID_ENC(x), ...)`` (section 4.2), so the already-encoded value inside the
    envelope is itself encoded once more: its dicts become ``map`` entries, its lists ``seq`` and its strings stay
    strings. ``tag`` is a non-empty versioned string such as ``"c15.series.v1"``."""
    if not isinstance(tag, str) or not tag:
        raise IdentityEncodingError("tag must be a non-empty str")
    envelope = {"tag": tag, "v": id_enc(value)}
    return hashlib.sha256(_dumps(_encode_envelope(envelope)).encode("ascii")).hexdigest()
