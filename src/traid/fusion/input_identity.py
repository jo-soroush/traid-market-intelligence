"""C15 Phase 1 Slice 4: supplied L5 references only (contract v3.5 §21).

Equal identifiers never establish shared inputs, provenance, content equivalence
or emptiness. UNAVAILABLE deliberately has one identity across sources and times.
No source mapping, digest-to-content verification or lineage is implemented here.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator, ConfigDict, model_validator, validate_call

from traid.fusion.models import FusionModel, InputDigestRef, Text, UtcDatetime
from traid.fusion.serialization import id_digest


class _InputIdentityModel(FusionModel):
    model_config = ConfigDict(strict=True, revalidate_instances="always")

    @classmethod
    def model_construct(cls, _fields_set=None, **values):
        # These public construction/copy paths must not enable a reserved state.
        # Unlike BaseModel's trusted shortcut, construction here always validates.
        return cls.model_validate(values)

    def model_copy(self, *, update=None, deep=False):
        return type(self).model_validate(super().model_copy(update=update, deep=deep))


class Delivery(_InputIdentityModel):
    """Five explicit provenance fields; not a completeness or eligibility verdict."""

    source: Text
    source_type: Text
    source_id: Text | None
    source_timestamp: UtcDatetime | None
    received_timestamp: UtcDatetime

    @model_validator(mode="after")
    def _receipt_order(self) -> Delivery:
        if self.source_timestamp is not None and self.received_timestamp < self.source_timestamp:
            raise ValueError("received_timestamp cannot precede source_timestamp")
        return self


def _digest_pair(value):
    if type(value) not in (tuple, list) or len(value) != 2:
        raise ValueError("digest must be an ordered (algorithm, digest) pair")
    checked = InputDigestRef(algorithm=value[0], digest=value[1])
    return checked.algorithm, checked.digest


class InputSetRef(_InputIdentityModel):
    """Closed state-tagged value: exactly three constructible variants.

    COMPLETE_SINGLE carries one exposed delivery, not proof of complete raw data.
    DIGEST_WITH_NEWEST carries only the newest delivery beside a source digest.
    KNOWN_EMPTY is contract-reserved and is intentionally absent from this API.
    """

    state: Literal["COMPLETE_SINGLE", "DIGEST_WITH_NEWEST", "UNAVAILABLE"]
    digest: Annotated[tuple[Text, Text], BeforeValidator(_digest_pair)] | None
    delivery: Delivery | None

    @model_validator(mode="after")
    def _state_presence(self) -> InputSetRef:
        if self.state == "COMPLETE_SINGLE":
            valid = self.digest is None and self.delivery is not None
        elif self.state == "DIGEST_WITH_NEWEST":
            valid = self.digest is not None and self.delivery is not None
        else:
            valid = self.digest is None and self.delivery is None
        if not valid:
            raise ValueError("digest and delivery do not match the declared input-set state")
        return self


@validate_call(config=ConfigDict(strict=True))
def input_set_id(input_set_ref: InputSetRef) -> str:
    """Hash the exact §21.5 projection; equality alone proves no shared lineage."""
    delivery = input_set_ref.delivery
    value = {
        "state": input_set_ref.state,
        "digest": input_set_ref.digest,
        "delivery": None if delivery is None else {
            "source": delivery.source,
            "source_type": delivery.source_type,
            "source_id": delivery.source_id,
            "source_timestamp": delivery.source_timestamp,
            "received_timestamp": delivery.received_timestamp,
        },
    }
    return "is1:" + id_digest("c15.is.v1", value)
