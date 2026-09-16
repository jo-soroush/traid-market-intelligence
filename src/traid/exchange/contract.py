"""Validated, provider-neutral exchange adapter boundary for V1-C03."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar, cast

from traid.domain import (
    Candle,
    FundingSnapshot,
    MarketContext,
    MarketTrade,
    OpenInterestSnapshot,
    OrderBookSnapshot,
)
from traid.exchange.contract_types import Capability
from traid.exchange.errors import (
    AdapterContractError,
    AdapterError,
    AdapterUnavailableError,
    InvalidCapabilityError,
    InvalidOutputError,
    UnsupportedCapabilityError,
    normalize_adapter_error,
)


class AdapterHealthState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"


class CapabilityAvailability(StrEnum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class CapabilityCoverage:
    """Provider-neutral capability coverage, not a freshness state."""

    capability: Capability
    availability: CapabilityAvailability
    limitation: str = ""

    def __post_init__(self) -> None:
        if self.availability is not CapabilityAvailability.SUPPORTED and not self.limitation.strip():
            raise ValueError("limited or unavailable capabilities require a limitation")


@dataclass(frozen=True)
class AdapterHealth:
    """Transport/provider availability only; freshness belongs to C05."""

    state: AdapterHealthState
    message: str = ""


AdapterCapability = TypeVar("AdapterCapability", bound="ExchangeAdapter")


_PUBLIC_METHODS = frozenset(
    {
        "connect",
        "disconnect",
        "health",
        "capabilities",
        "coverage",
        "trades",
        "order_book",
        "candles",
        "funding",
        "open_interest",
        "market_context",
    }
)


class ExchangeAdapter:
    """Core-facing facade; providers implement only protected hooks.

    Public capability methods all dispatch through ``invoke_capability``.
    Provider adapters must implement ``_trades``-style hooks and may not
    override this validated public surface.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        overridden = _PUBLIC_METHODS.intersection(cls.__dict__)
        if overridden:
            names = ", ".join(sorted(overridden))
            raise TypeError(f"provider adapters must not override validated public methods: {names}")

    def __init__(
        self,
        *,
        capabilities: frozenset[Capability],
        coverage: tuple[CapabilityCoverage, ...],
    ) -> None:
        self._declared_capabilities = capabilities
        self._declared_coverage = coverage
        self._health_state = AdapterHealthState.DISCONNECTED

    def connect(self) -> None:
        self._connect()
        self._health_state = AdapterHealthState.CONNECTED

    def disconnect(self) -> None:
        self._disconnect()
        self._health_state = AdapterHealthState.DISCONNECTED

    def health(self) -> AdapterHealth:
        return AdapterHealth(self._health_state)

    def capabilities(self) -> frozenset[Capability]:
        return self._declared_capabilities

    def coverage(self) -> tuple[CapabilityCoverage, ...]:
        return self._declared_coverage

    def trades(self, symbol: str) -> tuple[MarketTrade, ...]:
        return cast(tuple[MarketTrade, ...], invoke_capability(self, Capability.TRADES, symbol))

    def order_book(self, symbol: str) -> OrderBookSnapshot:
        return cast(OrderBookSnapshot, invoke_capability(self, Capability.ORDER_BOOK, symbol))

    def candles(self, symbol: str) -> tuple[Candle, ...]:
        return cast(tuple[Candle, ...], invoke_capability(self, Capability.CANDLES, symbol))

    def funding(self, symbol: str) -> FundingSnapshot:
        return cast(FundingSnapshot, invoke_capability(self, Capability.FUNDING, symbol))

    def open_interest(self, symbol: str) -> OpenInterestSnapshot:
        return cast(OpenInterestSnapshot, invoke_capability(self, Capability.OPEN_INTEREST, symbol))

    def market_context(self, symbol: str) -> MarketContext:
        return cast(MarketContext, invoke_capability(self, Capability.MARKET_CONTEXT, symbol))

    def _connect(self) -> None:
        return None

    def _disconnect(self) -> None:
        return None

    def _invoke_raw(self, capability: Capability, *args: object) -> object:
        hook_name = _CAPABILITY_CONTRACTS[capability][0]
        hook = getattr(self, hook_name)
        if hook.__func__ is getattr(ExchangeAdapter, hook_name):
            raise AdapterContractError("advertised capability has no provider implementation", capability)
        return hook(*args)

    def _trades(self, symbol: str) -> tuple[MarketTrade, ...]:
        raise AdapterContractError("trades capability is not implemented", Capability.TRADES)

    def _order_book(self, symbol: str) -> OrderBookSnapshot:
        raise AdapterContractError("order book capability is not implemented", Capability.ORDER_BOOK)

    def _candles(self, symbol: str) -> tuple[Candle, ...]:
        raise AdapterContractError("candles capability is not implemented", Capability.CANDLES)

    def _funding(self, symbol: str) -> FundingSnapshot:
        raise AdapterContractError("funding capability is not implemented", Capability.FUNDING)

    def _open_interest(self, symbol: str) -> OpenInterestSnapshot:
        raise AdapterContractError("open interest capability is not implemented", Capability.OPEN_INTEREST)

    def _market_context(self, symbol: str) -> MarketContext:
        raise AdapterContractError("market context capability is not implemented", Capability.MARKET_CONTEXT)


_CAPABILITY_CONTRACTS: dict[Capability, tuple[str, type[object], bool]] = {
    Capability.TRADES: ("_trades", MarketTrade, True),
    Capability.ORDER_BOOK: ("_order_book", OrderBookSnapshot, False),
    Capability.CANDLES: ("_candles", Candle, True),
    Capability.FUNDING: ("_funding", FundingSnapshot, False),
    Capability.OPEN_INTEREST: ("_open_interest", OpenInterestSnapshot, False),
    Capability.MARKET_CONTEXT: ("_market_context", MarketContext, False),
}


def _validated_capability(capability: object) -> Capability:
    if not isinstance(capability, Capability):
        raise InvalidCapabilityError()
    return capability


def _coverage_for(adapter: ExchangeAdapter, capability: Capability) -> CapabilityCoverage:
    entries = adapter.coverage()
    matching = tuple(entry for entry in entries if entry.capability is capability)
    if len(matching) != 1:
        raise AdapterContractError("adapter coverage must contain exactly one entry per capability", capability)
    return matching[0]


def require_capability(
    adapter: ExchangeAdapter,
    capability: object,
    capability_type: type[AdapterCapability] | None = None,
) -> ExchangeAdapter:
    """Validate the advertised capability and its provider implementation."""

    capability = _validated_capability(capability)
    if not isinstance(adapter, ExchangeAdapter):
        raise AdapterContractError("adapter must use the validated C03 facade", capability)
    if capability not in adapter.capabilities():
        raise UnsupportedCapabilityError(capability)
    coverage = _coverage_for(adapter, capability)
    if coverage.availability is CapabilityAvailability.UNAVAILABLE:
        raise AdapterUnavailableError(coverage.limitation, capability)
    if capability_type is not None and not isinstance(adapter, capability_type):
        raise AdapterContractError("adapter capability type is incompatible", capability)
    return adapter


def invoke_capability(adapter: ExchangeAdapter, capability: object, *args: object) -> object:
    """Invoke one capability through the shared C03 runtime boundary."""

    capability = _validated_capability(capability)
    require_capability(adapter, capability)
    try:
        if adapter.health().state is AdapterHealthState.DISCONNECTED:
            raise AdapterUnavailableError(capability=capability)
        result = adapter._invoke_raw(capability, *args)
    except AdapterError:
        raise
    except BaseException as error:
        raise normalize_adapter_error(capability, error) from None
    output_type, is_collection = _CAPABILITY_CONTRACTS[capability][1:]
    if is_collection:
        valid = isinstance(result, tuple) and all(isinstance(item, output_type) for item in result)
    else:
        valid = isinstance(result, output_type)
    if not valid:
        raise InvalidOutputError(capability)
    return result
