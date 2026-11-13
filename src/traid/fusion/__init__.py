"""V1-C15 Evidence Registry & Signal Fusion, Phase 1 (partial milestone; C15 remains OPEN).

Slices 1–4: exact serialization, leaf models and structural identities. No adapters, relations, lineage or AI binding yet.
"""
from traid.fusion.identity import (
    SeriesKey, Slot, SlotClaim, SlotInstant, SlotPeriod, SlotWindow, exposed_content_id, series_id, slot_id,
)
from traid.fusion.input_identity import Delivery, InputSetRef, input_set_id
from traid.fusion.models import (
    ROLE_RULES_ACTIVE, Basis, Comparison, Coverage, EvidenceRole, FusionModel, InputDigestRef, MetricObservation,
    MetricState, RawIdentity, SourceReportedContradiction, UtcDatetime,
)
from traid.fusion.serialization import (
    AmbiguousEnumTypeError, IdentityEncodingError, Unordered, id_digest, id_enc, id_json,
)

__all__ = ["AmbiguousEnumTypeError", "IdentityEncodingError", "Unordered", "id_digest", "id_enc", "id_json",
           "ROLE_RULES_ACTIVE", "Basis", "Comparison", "Coverage", "EvidenceRole", "FusionModel", "InputDigestRef",
           "MetricObservation", "MetricState", "RawIdentity", "SourceReportedContradiction", "UtcDatetime",
           "SeriesKey", "Slot", "SlotClaim", "SlotInstant", "SlotPeriod", "SlotWindow",
           "exposed_content_id", "series_id", "slot_id", "Delivery", "InputSetRef", "input_set_id"]
