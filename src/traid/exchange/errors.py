"""Small provider-neutral error contract for V1-C03."""

from __future__ import annotations

from enum import StrEnum

from traid.exchange.contract_types import Capability


class AdapterErrorCode(StrEnum):
    """Stable error categories visible at the Core/adapter boundary."""

    CONTRACT = "CONTRACT"
    INVALID_CAPABILITY = "INVALID_CAPABILITY"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_DATA = "PROVIDER_DATA"


class AdapterError(Exception):
    """Base error; provider-native exception ownership stops at the adapter."""

    def __init__(self, code: AdapterErrorCode, message: str, capability: Capability | None = None) -> None:
        self.code = code
        self.capability = capability
        self.message = message
        super().__init__(message)


class AdapterContractError(AdapterError):
    def __init__(self, message: str, capability: Capability | None = None) -> None:
        super().__init__(AdapterErrorCode.CONTRACT, message, capability)


class InvalidCapabilityError(AdapterError):
    def __init__(self, message: str = "invalid adapter capability") -> None:
        super().__init__(AdapterErrorCode.INVALID_CAPABILITY, message)


class InvalidOutputError(AdapterError):
    def __init__(self, capability: Capability) -> None:
        super().__init__(AdapterErrorCode.INVALID_OUTPUT, "adapter returned an invalid canonical output", capability)


class AdapterUnavailableError(AdapterError):
    def __init__(self, message: str = "adapter is unavailable", capability: Capability | None = None) -> None:
        super().__init__(AdapterErrorCode.UNAVAILABLE, message, capability)


class UnsupportedCapabilityError(AdapterError):
    def __init__(self, capability: Capability) -> None:
        super().__init__(AdapterErrorCode.UNSUPPORTED_CAPABILITY, f"unsupported capability: {capability.value}", capability)


class AdapterRateLimitError(AdapterError):
    def __init__(self, message: str = "provider rate limit reached", capability: Capability | None = None) -> None:
        super().__init__(AdapterErrorCode.RATE_LIMITED, message, capability)


class ProviderDataError(AdapterError):
    def __init__(self, message: str, capability: Capability | None = None) -> None:
        super().__init__(AdapterErrorCode.PROVIDER_DATA, message, capability)


def normalize_adapter_error(capability: Capability, error: BaseException) -> AdapterError:
    """Convert an implementation exception without leaking its native type/text."""

    if isinstance(error, AdapterError):
        return error
    return AdapterError(
        AdapterErrorCode.PROVIDER_FAILURE,
        "adapter operation failed",
        capability,
    )
