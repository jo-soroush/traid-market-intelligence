"""C15 Phase 1 Slice 5: supplied observation projection (contract v3.6 §23).

Equality proves no raw-source equality, verified provenance or shared lineage.
No adapters, assessments or decision authority are implemented here.
"""
from __future__ import annotations

from traid.fusion.identity import Slot, exposed_content_id, slot_id
from traid.fusion.input_identity import InputSetRef, input_set_id
from traid.fusion.models import Basis, Coverage, MetricObservation
from traid.fusion.serialization import id_digest


def observation_id(
    *, slot: Slot, coverage: Coverage, metrics: tuple[MetricObservation, ...],
    basis: Basis, input_set: InputSetRef,
) -> str:
    """Compose validated component identities without changing their admission rules.

    Deliberately no outer validation wrapper: metric dictionaries must reach the
    instance-only guard in exposed_content_id before any model conversion.
    """
    value = {
        "slot": slot_id(slot),
        "xc": exposed_content_id(slot=slot, coverage=coverage, metrics=metrics, basis=basis),
        "is": input_set_id(input_set),
    }
    return "ob1:" + id_digest("c15.ob.v1", value)
