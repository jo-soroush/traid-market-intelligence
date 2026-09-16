from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import re

import pytest

from traid.domain import (
    Candle,
    FundingSnapshot,
    MarketContext,
    MarketTrade,
    OpenInterestSnapshot,
    OrderBookLevel,
    OrderBookSnapshot,
    SourceProvenance,
    DataQualityState,
)
from traid.exchange import (
    AdapterError,
    AdapterErrorCode,
    AdapterHealth,
    AdapterHealthState,
    Capability,
    CapabilityAvailability,
    CapabilityCoverage,
    ExchangeAdapter,
    InvalidCapabilityError,
    InvalidOutputError,
    UnsupportedCapabilityError,
    AdapterUnavailableError,
    invoke_capability,
    normalize_adapter_error,
)


UTC = timezone.utc
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def provenance() -> SourceProvenance:
    return SourceProvenance(
        source="test-source",
        source_type="fixture",
        source_timestamp=NOW,
        received_timestamp=NOW,
    )


class FakeExchangeAdapter(ExchangeAdapter):
    """Deterministic test-owned implementation, not a provider simulator."""

    def __init__(self, capabilities: frozenset[Capability] | None = None) -> None:
        self._capabilities = capabilities or frozenset(Capability)
        coverage = tuple(
            CapabilityCoverage(
                capability=capability,
                availability=(
                    CapabilityAvailability.SUPPORTED
                    if capability in self._capabilities
                    else CapabilityAvailability.UNAVAILABLE
                ),
                limitation=("not advertised by fake" if capability not in self._capabilities else ""),
            )
            for capability in Capability
        )
        super().__init__(capabilities=self._capabilities, coverage=coverage)

    def _trades(self, symbol: str) -> tuple[MarketTrade, ...]:
        return (MarketTrade(symbol=symbol, price=Decimal("100"), quantity=Decimal("1"), timestamp=NOW, provenance=provenance()),)

    def _order_book(self, symbol: str) -> OrderBookSnapshot:
        return OrderBookSnapshot(symbol=symbol, bids=(OrderBookLevel(price="99", quantity="1"),), timestamp=NOW, provenance=provenance())

    def _candles(self, symbol: str) -> tuple[Candle, ...]:
        return (Candle(symbol=symbol, start_timestamp=NOW, end_timestamp=NOW.replace(minute=13), open="99", high="101", low="98", close="100", volume="2", provenance=provenance()),)

    def _funding(self, symbol: str) -> FundingSnapshot:
        return FundingSnapshot(symbol=symbol, funding_rate="0.001", timestamp=NOW, provenance=provenance())

    def _open_interest(self, symbol: str) -> OpenInterestSnapshot:
        return OpenInterestSnapshot(symbol=symbol, open_interest="10", timestamp=NOW, provenance=provenance())

    def _market_context(self, symbol: str) -> MarketContext:
        return MarketContext(symbol=symbol, as_of_timestamp=NOW, data_quality=DataQualityState.LIVE, provenance=(provenance(),))


def test_fake_adapter_satisfies_lifecycle_and_capability_contract() -> None:
    adapter = FakeExchangeAdapter()
    assert isinstance(adapter, ExchangeAdapter)
    assert adapter.health().state is AdapterHealthState.DISCONNECTED
    adapter.connect()
    assert adapter.health().state is AdapterHealthState.CONNECTED
    assert adapter.capabilities() == frozenset(Capability)
    adapter.disconnect()
    assert adapter.health().state is AdapterHealthState.DISCONNECTED


def test_capability_discovery_and_typed_access_are_consistent() -> None:
    adapter = FakeExchangeAdapter()
    adapter.connect()
    trades = invoke_capability(adapter, Capability.TRADES, "BTC-USD")
    order_book = invoke_capability(adapter, Capability.ORDER_BOOK, "BTC-USD")
    context = invoke_capability(adapter, Capability.MARKET_CONTEXT, "BTC-USD")
    assert isinstance(trades[0], MarketTrade)
    assert isinstance(order_book, OrderBookSnapshot)
    assert isinstance(context, MarketContext)


def test_all_required_capabilities_return_canonical_c02_types() -> None:
    adapter = FakeExchangeAdapter()
    adapter.connect()
    assert isinstance(adapter.candles("BTC-USD")[0], Candle)
    assert isinstance(adapter.funding("BTC-USD"), FundingSnapshot)
    assert isinstance(adapter.open_interest("BTC-USD"), OpenInterestSnapshot)
    assert isinstance(adapter.market_context("BTC-USD"), MarketContext)


def test_unsupported_capability_fails_before_method_invocation() -> None:
    adapter = FakeExchangeAdapter(frozenset({Capability.TRADES}))
    with pytest.raises(UnsupportedCapabilityError) as error:
        adapter.order_book("BTC-USD")
    assert error.value.code is AdapterErrorCode.UNSUPPORTED_CAPABILITY
    assert error.value.capability is Capability.ORDER_BOOK


def test_advertised_but_missing_capability_fails_contract_check() -> None:
    class AdvertisedMissing(ExchangeAdapter):
        def __init__(self) -> None:
            super().__init__(
                capabilities=frozenset({Capability.ORDER_BOOK}),
                coverage=(CapabilityCoverage(Capability.ORDER_BOOK, CapabilityAvailability.SUPPORTED),),
            )

    adapter = AdvertisedMissing()
    adapter.connect()
    with pytest.raises(AdapterError) as error:
        adapter.order_book("BTC-USD")
    assert error.value.code is AdapterErrorCode.CONTRACT


def test_provider_cannot_override_validated_public_methods() -> None:
    with pytest.raises(TypeError):
        class BrokenPublicAdapter(FakeExchangeAdapter):
            def order_book(self, symbol: str) -> OrderBookSnapshot:
                return "unchecked"  # type: ignore[return-value]


def test_direct_and_dispatcher_paths_share_output_and_lifecycle_enforcement() -> None:
    class WrongOrderBook(FakeExchangeAdapter):
        def _order_book(self, symbol: str) -> OrderBookSnapshot:
            return "wrong"  # type: ignore[return-value]

    wrong = WrongOrderBook()
    wrong.connect()
    for call in (
        lambda: wrong.order_book("BTC-USD"),
        lambda: invoke_capability(wrong, Capability.ORDER_BOOK, "BTC-USD"),
    ):
        with pytest.raises(InvalidOutputError):
            call()

    disconnected = FakeExchangeAdapter()
    for call in (
        lambda: disconnected.trades("BTC-USD"),
        lambda: invoke_capability(disconnected, Capability.TRADES, "BTC-USD"),
    ):
        with pytest.raises(AdapterUnavailableError):
            call()


def test_unknown_capability_is_normalized() -> None:
    with pytest.raises(InvalidCapabilityError) as error:
        invoke_capability(FakeExchangeAdapter(), "unknown", "BTC-USD")
    assert error.value.code is AdapterErrorCode.INVALID_CAPABILITY


def test_wrong_scalar_output_is_rejected_at_runtime_boundary() -> None:
    class WrongScalar(FakeExchangeAdapter):
        def _order_book(self, symbol: str) -> OrderBookSnapshot:
            return "wrong"  # type: ignore[return-value]

    adapter = WrongScalar()
    adapter.connect()
    with pytest.raises(InvalidOutputError) as error:
        adapter.order_book("BTC-USD")
    assert error.value.code is AdapterErrorCode.INVALID_OUTPUT


def test_wrong_collection_element_is_rejected_at_runtime_boundary() -> None:
    class WrongCollection(FakeExchangeAdapter):
        def _trades(self, symbol: str) -> tuple[MarketTrade, ...]:
            return ("wrong",)  # type: ignore[return-value]

    adapter = WrongCollection()
    adapter.connect()
    with pytest.raises(InvalidOutputError):
        adapter.trades("BTC-USD")


def test_raw_dict_output_is_rejected() -> None:
    class RawDict(FakeExchangeAdapter):
        def _order_book(self, symbol: str) -> OrderBookSnapshot:
            return {}  # type: ignore[return-value]

    adapter = RawDict()
    adapter.connect()
    with pytest.raises(InvalidOutputError):
        adapter.order_book("BTC-USD")


def test_disconnected_data_call_is_unavailable_and_connected_call_succeeds() -> None:
    adapter = FakeExchangeAdapter()
    with pytest.raises(AdapterUnavailableError) as error:
        adapter.trades("BTC-USD")
    assert error.value.code is AdapterErrorCode.UNAVAILABLE
    adapter.connect()
    assert isinstance(adapter.trades("BTC-USD")[0], MarketTrade)


def test_degraded_adapter_remains_callable_without_freshness_semantics() -> None:
    adapter = FakeExchangeAdapter()
    adapter._health_state = AdapterHealthState.DEGRADED
    assert isinstance(adapter.trades("BTC-USD")[0], MarketTrade)


def test_coverage_explicitly_represents_supported_limited_and_unavailable() -> None:
    entries = (
        CapabilityCoverage(Capability.TRADES, CapabilityAvailability.SUPPORTED),
        CapabilityCoverage(Capability.CANDLES, CapabilityAvailability.LIMITED, "fixture has one interval"),
        CapabilityCoverage(Capability.FUNDING, CapabilityAvailability.UNAVAILABLE, "not supplied"),
    )
    assert entries[0].availability is CapabilityAvailability.SUPPORTED
    assert entries[1].limitation == "fixture has one interval"
    assert entries[2].availability is CapabilityAvailability.UNAVAILABLE


def test_coverage_requires_inspectable_limitation_for_limited_or_unavailable() -> None:
    with pytest.raises(ValueError):
        CapabilityCoverage(Capability.TRADES, CapabilityAvailability.LIMITED)


def test_provider_native_error_is_normalized_without_leaking_native_text() -> None:
    error = normalize_adapter_error(Capability.TRADES, RuntimeError("provider payload internals"))
    assert error.code is AdapterErrorCode.PROVIDER_FAILURE
    assert error.capability is Capability.TRADES
    assert str(error) == "adapter operation failed"


def test_provider_native_error_through_invoke_is_normalized() -> None:
    class ProviderFailure(FakeExchangeAdapter):
        def _trades(self, symbol: str) -> tuple[MarketTrade, ...]:
            raise RuntimeError("provider-native payload details")

    adapter = ProviderFailure()
    adapter.connect()
    with pytest.raises(AdapterError) as error:
        adapter.trades("BTC-USD")
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE
    assert str(error.value) == "adapter operation failed"


def test_normalization_preserves_existing_contract_error() -> None:
    original = UnsupportedCapabilityError(Capability.CANDLES)
    assert normalize_adapter_error(Capability.CANDLES, original) is original


def test_contract_outputs_are_deterministic() -> None:
    first_adapter = FakeExchangeAdapter()
    second_adapter = FakeExchangeAdapter()
    first_adapter.connect()
    second_adapter.connect()
    first = first_adapter.trades("BTC-USD")
    second = second_adapter.trades("BTC-USD")
    assert first == second
    assert first[0].model_dump() == second[0].model_dump()


def test_contract_has_no_provider_or_transport_coupling() -> None:
    source_root = Path(__file__).parents[1] / "src" / "traid" / "exchange"
    text = "\n".join(path.read_text().lower() for path in source_root.glob("*.py"))
    pattern = re.compile(r"\b(hyperliquid|websocket|requests|httpx|rest)\b", re.IGNORECASE)
    assert not pattern.search(text)
    assert not pattern.search("open_interest")
    assert pattern.search("REST client")
    assert pattern.search("WebSocket transport")
    assert pattern.search("Hyperliquid adapter")
