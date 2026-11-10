"""V1-C15 Evidence Registry & Signal Fusion, Phase 1 (partial milestone; C15 remains OPEN).

Slice 1 only: exact identity serialization. No fusion models, adapters, relations, lineage or AI binding yet.
"""
from traid.fusion.serialization import (
    AmbiguousEnumTypeError, IdentityEncodingError, Unordered, id_digest, id_enc, id_json,
)

__all__ = ["AmbiguousEnumTypeError", "IdentityEncodingError", "Unordered", "id_digest", "id_enc", "id_json"]
