"""Provider-neutral exchange adapter contracts owned by V1-C03."""

from traid.exchange.contract import (
    AdapterHealth,
    AdapterHealthState,
    Capability,
    CapabilityAvailability,
    CapabilityCoverage,
    ExchangeAdapter,
    invoke_capability,
    require_capability,
)
from traid.exchange.errors import (
    AdapterError,
    AdapterErrorCode,
    AdapterContractError,
    AdapterUnavailableError,
    InvalidCapabilityError,
    InvalidOutputError,
    UnsupportedCapabilityError,
    normalize_adapter_error,
)

__all__ = [
    "AdapterError",
    "AdapterErrorCode",
    "AdapterContractError",
    "AdapterHealth",
    "AdapterHealthState",
    "AdapterUnavailableError",
    "Capability",
    "CapabilityAvailability",
    "CapabilityCoverage",
    "ExchangeAdapter",
    "UnsupportedCapabilityError",
    "InvalidCapabilityError",
    "InvalidOutputError",
    "invoke_capability",
    "normalize_adapter_error",
    "require_capability",
]
