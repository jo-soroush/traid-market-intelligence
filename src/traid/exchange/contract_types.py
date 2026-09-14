"""Shared type-only names for the provider-neutral exchange boundary."""

from enum import StrEnum


class Capability(StrEnum):
    TRADES = "trades"
    ORDER_BOOK = "order_book"
    CANDLES = "candles"
    FUNDING = "funding"
    OPEN_INTEREST = "open_interest"
    MARKET_CONTEXT = "market_context"
