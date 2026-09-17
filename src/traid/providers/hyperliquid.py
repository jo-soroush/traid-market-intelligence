"""Bounded, public read-only Hyperliquid market-data adapter for V1-C04."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Mapping
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from time import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from traid.domain import (
    Candle,
    DataQualityState,
    FundingSnapshot,
    MarketContext,
    MarketTrade,
    OrderBookLevel,
    OrderBookSnapshot,
    SourceProvenance,
)
from traid.exchange import (
    AdapterError,
    AdapterErrorCode,
    AdapterHealthState,
    AdapterRateLimitError,
    Capability,
    CapabilityAvailability,
    CapabilityCoverage,
    ExchangeAdapter,
    ProviderDataError,
)


UTC = timezone.utc
DEFAULT_INFO_URL = "https://api.hyperliquid.xyz/info"
DEFAULT_WS_URL = "wss://api.hyperliquid.xyz/ws"


def _timestamp(value: Any, capability: Capability) -> datetime:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProviderDataError("provider timestamp is invalid", capability)
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _decimal(value: Any, capability: Capability, *, positive: bool = False) -> Decimal:
    if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
        raise ProviderDataError("provider numeric value is invalid", capability)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ProviderDataError("provider numeric value is invalid", capability) from error
    if not result.is_finite() or (positive and result <= 0) or (not positive and result < 0):
        raise ProviderDataError("provider numeric value is outside the canonical domain", capability)
    return result


class HyperliquidAdapter(ExchangeAdapter):
    """C04 adapter; raw provider dictionaries do not cross this class boundary."""

    def __init__(
        self,
        *,
        info_url: str = DEFAULT_INFO_URL,
        websocket_url: str = DEFAULT_WS_URL,
        timeout: float = 10.0,
        clock: Callable[[], datetime] | None = None,
        websocket_connect: Callable[..., Any] | None = None,
        reconnect_backoff: float = 1.0,
    ) -> None:
        coverage = tuple(
            CapabilityCoverage(
                capability=capability,
                availability=(CapabilityAvailability.UNAVAILABLE if capability is Capability.OPEN_INTEREST else CapabilityAvailability.SUPPORTED),
                limitation=("Hyperliquid OI unit and aggregation semantics are unverified" if capability is Capability.OPEN_INTEREST else ""),
            )
            for capability in Capability
        )
        super().__init__(
            capabilities=frozenset(Capability),
            coverage=coverage,
        )
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if reconnect_backoff < 0:
            raise ValueError("reconnect_backoff must not be negative")
        self.info_url = info_url
        self.websocket_url = websocket_url
        self.timeout = timeout
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._websocket_connect = websocket_connect
        self._reconnect_backoff = reconnect_backoff

    def _connect(self) -> None:
        return None

    def _disconnect(self) -> None:
        return None

    def _received(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return an aware datetime")
        return value.astimezone(UTC)

    def _post(self, payload: Mapping[str, Any], capability: Capability) -> Any:
        request = Request(
            self.info_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if error.code == 429:
                raise AdapterRateLimitError(capability=capability) from error
            raise AdapterError(code=AdapterErrorCode.PROVIDER_FAILURE, message="provider HTTP request failed", capability=capability) from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise AdapterError(code=AdapterErrorCode.PROVIDER_FAILURE, message="provider request failed", capability=capability) from error

    @staticmethod
    def _require_list(value: Any, capability: Capability) -> list[Any]:
        if not isinstance(value, list):
            raise ProviderDataError("provider response shape is invalid", capability)
        return value

    @staticmethod
    def _require_mapping(value: Any, capability: Capability) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ProviderDataError("provider record shape is invalid", capability)
        return value

    def _trades(self, symbol: str) -> tuple[MarketTrade, ...]:
        capability = Capability.TRADES
        records = self._require_list(self._post({"type": "recentTrades", "coin": symbol}, capability), capability)
        received = self._received()
        result: list[MarketTrade] = []
        for record in records:
            item = self._require_mapping(record, capability)
            result.append(MarketTrade(symbol=item["coin"], price=_decimal(item["px"], capability, positive=True), quantity=_decimal(item["sz"], capability, positive=True), timestamp=_timestamp(item["time"], capability), provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id=str(item["tid"]), source_timestamp=_timestamp(item["time"], capability), received_timestamp=received)))
        return tuple(result)

    def _order_book(self, symbol: str) -> OrderBookSnapshot:
        capability = Capability.ORDER_BOOK
        payload = self._require_mapping(self._post({"type": "l2Book", "coin": symbol}, capability), capability)
        levels = payload.get("levels")
        if not isinstance(levels, list) or len(levels) != 2:
            raise ProviderDataError("provider order book levels are invalid", capability)
        def parse_side(side: Any) -> tuple[OrderBookLevel, ...]:
            return tuple(OrderBookLevel(price=_decimal(self._require_mapping(level, capability)["px"], capability, positive=True), quantity=_decimal(self._require_mapping(level, capability)["sz"], capability)) for level in self._require_list(side, capability))
        received = self._received()
        source_time = _timestamp(payload["time"], capability)
        return OrderBookSnapshot(symbol=str(payload.get("coin", symbol)), bids=parse_side(levels[0]), asks=parse_side(levels[1]), timestamp=source_time, provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id="l2Book", source_timestamp=source_time, received_timestamp=received))

    def _candles(self, symbol: str) -> tuple[Candle, ...]:
        capability = Capability.CANDLES
        now_ms = int(time() * 1000)
        payload = self._post({"type": "candleSnapshot", "req": {"coin": symbol, "interval": "1h", "startTime": now_ms - 86_400_000, "endTime": now_ms}}, capability)
        records = self._require_list(payload, capability)
        received = self._received()
        result: list[Candle] = []
        for record in records:
            item = self._require_mapping(record, capability)
            start = _timestamp(item["t"], capability)
            end = _timestamp(item["T"], capability)
            result.append(Candle(symbol=str(item["s"]), start_timestamp=start, end_timestamp=end, open=_decimal(item["o"], capability, positive=True), high=_decimal(item["h"], capability, positive=True), low=_decimal(item["l"], capability, positive=True), close=_decimal(item["c"], capability, positive=True), volume=_decimal(item["v"], capability), provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id=str(item["t"]), source_timestamp=start, received_timestamp=received)))
        return tuple(result)

    def _funding(self, symbol: str) -> FundingSnapshot:
        capability = Capability.FUNDING
        now_ms = int(time() * 1000)
        records = self._require_list(self._post({"type": "fundingHistory", "coin": symbol, "startTime": now_ms - 86_400_000, "endTime": now_ms}, capability), capability)
        if not records:
            raise AdapterError(code=AdapterErrorCode.UNAVAILABLE, message="no funding observation returned", capability=capability)
        item = self._require_mapping(records[-1], capability)
        source_time = _timestamp(item["time"], capability)
        return FundingSnapshot(symbol=str(item["coin"]), funding_rate=_decimal(item["fundingRate"], capability), timestamp=source_time, provenance=SourceProvenance(source="hyperliquid", source_type="public_info", source_id="fundingHistory", source_timestamp=source_time, received_timestamp=self._received()))

    def _market_context(self, symbol: str) -> MarketContext:
        capability = Capability.MARKET_CONTEXT
        payload = self._post({"type": "metaAndAssetCtxs"}, capability)
        records = self._require_list(payload, capability)
        if len(records) != 2:
            raise ProviderDataError("provider asset context response is invalid", capability)
        meta = self._require_mapping(records[0], capability)
        universe = self._require_list(meta.get("universe"), capability)
        contexts = self._require_list(records[1], capability)
        index = next((i for i, item in enumerate(universe) if self._require_mapping(item, capability).get("name") == symbol), None)
        if index is None or index >= len(contexts):
            raise AdapterError(code=AdapterErrorCode.UNAVAILABLE, message="symbol context unavailable", capability=capability)
        self._require_mapping(contexts[index], capability)
        received = self._received()
        provenance = SourceProvenance(source="hyperliquid", source_type="public_info", source_id=f"asset_context:{symbol}", received_timestamp=received)
        return MarketContext(symbol=symbol, as_of_timestamp=received, data_quality=DataQualityState.LIVE, provenance=(provenance,))

    def normalize_ws_message(self, message: Mapping[str, Any]) -> object:
        """Convert one documented market-data envelope to a canonical value."""
        channel = message.get("channel")
        data = message.get("data")
        if channel == "subscriptionResponse":
            return message
        received = self._received()
        if channel == "trades":
            records = self._require_list(data, Capability.TRADES)
            return tuple(
                MarketTrade(
                    symbol=str((item := self._require_mapping(record, Capability.TRADES))["coin"]),
                    price=_decimal(item["px"], Capability.TRADES, positive=True),
                    quantity=_decimal(item["sz"], Capability.TRADES, positive=True),
                    timestamp=(source_time := _timestamp(item["time"], Capability.TRADES)),
                    provenance=SourceProvenance(source="hyperliquid", source_type="public_websocket", source_id=str(item["tid"]), source_timestamp=source_time, received_timestamp=received),
                )
                for record in records
            )
        if channel == "l2Book":
            item = self._require_mapping(data, Capability.ORDER_BOOK)
            levels = item.get("levels")
            if not isinstance(levels, list) or len(levels) != 2:
                raise ProviderDataError("provider websocket order book is invalid", Capability.ORDER_BOOK)
            def side(value: Any) -> tuple[OrderBookLevel, ...]:
                return tuple(OrderBookLevel(price=_decimal(self._require_mapping(level, Capability.ORDER_BOOK)["px"], Capability.ORDER_BOOK, positive=True), quantity=_decimal(self._require_mapping(level, Capability.ORDER_BOOK)["sz"], Capability.ORDER_BOOK)) for level in self._require_list(value, Capability.ORDER_BOOK))
            source_time = _timestamp(item["time"], Capability.ORDER_BOOK)
            return OrderBookSnapshot(symbol=str(item["coin"]), bids=side(levels[0]), asks=side(levels[1]), timestamp=source_time, provenance=SourceProvenance(source="hyperliquid", source_type="public_websocket", source_id="l2Book", source_timestamp=source_time, received_timestamp=received))
        if channel == "candle":
            item = self._require_mapping(data, Capability.CANDLES)
            start = _timestamp(item["t"], Capability.CANDLES)
            end = _timestamp(item["T"], Capability.CANDLES)
            return Candle(symbol=str(item["s"]), start_timestamp=start, end_timestamp=end, open=_decimal(item["o"], Capability.CANDLES, positive=True), high=_decimal(item["h"], Capability.CANDLES, positive=True), low=_decimal(item["l"], Capability.CANDLES, positive=True), close=_decimal(item["c"], Capability.CANDLES, positive=True), volume=_decimal(item["v"], Capability.CANDLES), provenance=SourceProvenance(source="hyperliquid", source_type="public_websocket", source_id=str(item["t"]), source_timestamp=start, received_timestamp=received))
        raise ProviderDataError("unsupported or malformed websocket channel", Capability.TRADES)

    async def stream(self, subscriptions: tuple[Mapping[str, Any], ...]) -> AsyncIterator[object]:
        """Yield validated envelopes with bounded reconnects for caller-owned streams."""
        try:
            from websockets.asyncio.client import connect
        except ImportError as error:
            raise AdapterError(code=AdapterErrorCode.UNAVAILABLE, message="websocket transport is not installed", capability=Capability.TRADES) from error
        connect_fn = self._websocket_connect or connect
        retries = 0
        while retries < 3:
            try:
                async with connect_fn(self.websocket_url, open_timeout=self.timeout, close_timeout=self.timeout, max_queue=128) as socket:
                    for subscription in subscriptions:
                        await socket.send(json.dumps({"method": "subscribe", "subscription": dict(subscription)}))
                    async for message in socket:
                        if not isinstance(message, str):
                            raise ProviderDataError("websocket message is not text", Capability.TRADES)
                        try:
                            value = json.loads(message)
                        except json.JSONDecodeError as error:
                            raise ProviderDataError("websocket JSON is malformed", Capability.TRADES) from error
                        if not isinstance(value, Mapping):
                            raise ProviderDataError("websocket envelope is invalid", Capability.TRADES)
                        yield self.normalize_ws_message(value)
                return
            except asyncio.CancelledError:
                raise
            except AdapterError:
                raise
            except Exception as error:
                retries += 1
                if retries >= 3:
                    raise AdapterError(code=AdapterErrorCode.PROVIDER_FAILURE, message="websocket reconnect exhausted", capability=Capability.TRADES) from error
                await asyncio.sleep(min(self._reconnect_backoff * (2 ** (retries - 1)), 4))
