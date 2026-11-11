"""V1-C15 Phase 1, slice 2: leaf data models (design TRAID_C15_SLICE2_FINAL_DESIGN_CORRECTION.md, contract v3.2).

Structural validation only. No source identity recomputation, no source-window verification, no digests computed,
no score, probability, weight or forecast, no SUPPORT/CONTRADICT/ELIGIBLE role. Models here are data holders; nothing
is derived or repaired. Datetimes are admitted through the Slice 1 identity boundary (``id_enc``) and nothing else.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, StrictStr, \
    model_validator

from traid.fusion.serialization import id_enc

ROLE_RULES_ACTIVE: tuple = ()

# ---------------------------------------------------------------------------------------------------- timestamps
_ISO = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?"
    r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def _admit(value):
    """Runs BEFORE pydantic sees the value. Admits a datetime object or strict ISO text; rejects everything else."""
    if isinstance(value, datetime):                  # direct datetime object
        id_enc(value)                                # exact type, aware, accepted tz type; rejects before any callback
        return value
    if type(value) is str:                           # exact str only: no str subclasses
        if _ISO.fullmatch(value) is None:            # shape check BEFORE fromisoformat (no silent truncation)
            raise ValueError("not strict ISO datetime text")
        parsed = datetime.fromisoformat(value)       # calendar and clock validity
        id_enc(parsed)                               # aware, accepted tz type, UTC range
        return parsed
    raise ValueError("datetime or strict ISO datetime text required")


def _normalize(value):
    """Runs AFTER pydantic, on an already-admitted datetime."""
    id_enc(value)
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, BeforeValidator(_admit), AfterValidator(_normalize)]


# ---------------------------------------------------------------------------------------------------- base and text
class FusionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


def _text(value: str) -> str:
    if value == "" or value != value.strip():
        raise ValueError("text must be non-empty with no leading or trailing whitespace")
    return value


Text = Annotated[StrictStr, AfterValidator(_text)]


def _no_float(value):
    if isinstance(value, (float, bool)):
        raise ValueError("float and bool are not accepted as a Decimal value")
    return value


ExactDecimal = Annotated[Decimal, BeforeValidator(_no_float)]


# ---------------------------------------------------------------------------------------------------- enums
class EvidenceRole(StrEnum):
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
    MISSING = "MISSING"
    STALE = "STALE"
    UNVERIFIED = "UNVERIFIED"
    INELIGIBLE = "INELIGIBLE"


class MetricState(StrEnum):
    PRESENT = "PRESENT"
    WITHHELD = "WITHHELD"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class Comparison(StrEnum):
    EQUAL = "EQUAL"
    DIFFERENT = "DIFFERENT"
    UNKNOWN = "UNKNOWN"


class Basis(StrEnum):
    SOURCE_INPUT_DIGEST = "SOURCE_INPUT_DIGEST"
    EXPOSED_FIELDS = "EXPOSED_FIELDS"
    NO_OBSERVATION = "NO_OBSERVATION"


class RawIdentity(StrEnum):
    VERIFIED_BY_SOURCE_DIGEST = "VERIFIED_BY_SOURCE_DIGEST"
    EXPOSED_CONTENT_COMPLETE = "EXPOSED_CONTENT_COMPLETE"
    EXPOSED_CONTENT_PARTIAL = "EXPOSED_CONTENT_PARTIAL"


# ---------------------------------------------------------------------------------------------------- leaf models
class MetricObservation(FusionModel):
    name: Text
    state: MetricState
    value: ExactDecimal | None = None
    unit: Text
    window_id: Text | None = None
    reason: Text | None = None

    @model_validator(mode="after")
    def _structure(self) -> "MetricObservation":
        if self.state is MetricState.PRESENT:
            if self.value is None or not self.value.is_finite():
                raise ValueError("a PRESENT metric requires a finite value")
            if self.reason is not None:
                raise ValueError("a PRESENT metric carries no reason")
        elif self.value is not None:
            raise ValueError(f"a {self.state.value} metric must not carry a value")
        return self


class Coverage(FusionModel):
    earliest_time: UtcDatetime | None = None
    latest_time: UtcDatetime | None = None
    contributing_count: Annotated[StrictInt, Field(ge=0)] | None = None
    interval: Text | None = None

    @model_validator(mode="after")
    def _structure(self) -> "Coverage":
        if self.earliest_time is not None and self.latest_time is not None and self.earliest_time > self.latest_time:
            raise ValueError("earliest_time is after latest_time")
        return self


class InputDigestRef(FusionModel):
    algorithm: Text
    digest: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceReportedContradiction(FusionModel):
    category: Text
    kind: Text
    code: Text
    location: Text
