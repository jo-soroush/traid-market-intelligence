"""Shared fixtures for the C15 serialization tests. Offline; standard library only."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import enum

from traid.fusion import Unordered, id_digest, id_json


class Color(enum.Enum):
    RED = "red"


class Mode(enum.StrEnum):
    FAST = "fast"


class Level(enum.IntEnum):
    ONE = 1


class Wrapper(enum.Enum):
    INNER = Mode.FAST
    PAIR = (Color.RED, Level.ONE)
    NUM = Decimal("1.50")


def battery() -> list[str]:
    """Digests of a fixed, varied set of values; used to pin stability across processes and hash seeds."""
    tz = timezone(timedelta(hours=1))
    values = [
        None, True, False, "text", 7, -7, Decimal("1.0"), Decimal("-0"), Decimal("1E+2"),
        Decimal((0, (1,) * 9000, 0)),
        datetime(2026, 1, 1, 12, tzinfo=timezone.utc), datetime(2026, 1, 1, 13, tzinfo=tz),
        date(2026, 1, 1), timedelta(days=-1, microseconds=1), timedelta(microseconds=-1),
        Color.RED, Mode.FAST, Level.ONE, Wrapper.INNER, Wrapper.PAIR, Wrapper.NUM,
        (1, "a", Decimal("2")), [Color.RED, Mode.FAST], frozenset({"b", "a", "c"}),
        Unordered(("b", "a", "b")), {"z": 1, "a": {"y": Decimal("0.10"), "x": (Level.ONE,)}},
    ]
    return [id_digest("c15.test.v1", v) for v in values] + [id_json(v) for v in values]
