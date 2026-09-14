from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re

import pytest
from pydantic import ValidationError

from traid.domain import (
    DOMAIN_SCHEMA_VERSION,
    Candle,
    DataQualityState,
    EvidenceReference,
    MarketContext,
    MarketTrade,
    FundingSnapshot,
    LiquidationEvent,
    PriceSnapshot,
    OpenInterestSnapshot,
    OrderBookLevel,
    OrderBookSnapshot,
    SourceProvenance,
)


UTC = timezone.utc
SOURCE_TIME = datetime(2026, 1, 1, 12, tzinfo=UTC)
RECEIVED_TIME = SOURCE_TIME + timedelta(seconds=1)


def provenance() -> SourceProvenance:
    return SourceProvenance(
        source="market-feed",
        source_type="exchange",
        source_id="feed-1",
        source_timestamp=SOURCE_TIME,
        received_timestamp=RECEIVED_TIME,
    )


def test_market_trade_is_typed_decimal_and_provider_neutral() -> None:
    trade = MarketTrade(
        symbol="BTC-USD",
        price="100.25",
        quantity="0.5",
        timestamp=SOURCE_TIME,
        provenance=provenance(),
    )
    assert trade.price == Decimal("100.25")
    assert trade.schema_version == DOMAIN_SCHEMA_VERSION
    assert "hyperliquid" not in trade.model_dump_json().lower()


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        MarketTrade(
            symbol="BTC-USD",
            price=Decimal("100"),
            quantity=Decimal("1"),
            timestamp=datetime(2026, 1, 1, 12),
            provenance=provenance(),
        )


def test_timestamp_normalizes_to_utc_and_round_trips() -> None:
    local = datetime(2026, 1, 1, 13, tzinfo=timezone(timedelta(hours=1)))
    trade = MarketTrade(
        symbol="BTC-USD", price=Decimal("100"), quantity=Decimal("1"), timestamp=local, provenance=provenance()
    )
    rebuilt = MarketTrade.model_validate_json(trade.model_dump_json())
    assert trade.timestamp == datetime(2026, 1, 1, 12, tzinfo=UTC)
    assert rebuilt == trade
    assert rebuilt.provenance.received_timestamp.tzinfo == UTC


def test_provenance_rejects_received_time_before_source_time() -> None:
    with pytest.raises(ValidationError, match="received_timestamp"):
        SourceProvenance(
            source="market-feed",
            source_type="exchange",
            source_timestamp=RECEIVED_TIME,
            received_timestamp=SOURCE_TIME,
        )


def test_numeric_and_candle_constraints_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        PriceSnapshot(symbol="BTC-USD", price=Decimal("0"), timestamp=SOURCE_TIME, provenance=provenance())
    with pytest.raises(ValidationError):
        Candle(
            symbol="BTC-USD",
            start_timestamp=SOURCE_TIME,
            end_timestamp=SOURCE_TIME,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1"),
            provenance=provenance(),
        )


def test_quality_state_and_evidence_reference_are_serializable() -> None:
    reference = EvidenceReference(
        evidence_id="e-1", evidence_type="observation", provenance=provenance(), related_symbol="BTC-USD"
    )
    context = MarketContext(
        symbol="BTC-USD",
        as_of_timestamp=RECEIVED_TIME,
        data_quality=DataQualityState.LIVE,
        evidence=(reference,),
        provenance=(provenance(),),
    )
    rebuilt = MarketContext.model_validate_json(context.model_dump_json())
    assert rebuilt == context
    assert '"data_quality":"LIVE"' in context.model_dump_json()


def test_all_c02_market_models_construct_with_canonical_types() -> None:
    assert OrderBookLevel(price="100", quantity="1").price == Decimal("100")
    assert OrderBookSnapshot(
        symbol="BTC-USD", bids=(OrderBookLevel(price="100", quantity="1"),), asks=(), timestamp=SOURCE_TIME, provenance=provenance()
    ).bids[0].quantity == Decimal("1")
    assert Candle(
        symbol="BTC-USD", start_timestamp=SOURCE_TIME, end_timestamp=RECEIVED_TIME,
        open="100", high="101", low="99", close="100", volume="2", provenance=provenance()
    ).volume == Decimal("2")
    assert FundingSnapshot(symbol="BTC-USD", funding_rate="0.001", timestamp=SOURCE_TIME, provenance=provenance()).funding_rate == Decimal("0.001")
    assert OpenInterestSnapshot(symbol="BTC-USD", open_interest="10", timestamp=SOURCE_TIME, provenance=provenance()).open_interest == Decimal("10")
    assert LiquidationEvent(symbol="BTC-USD", price="100", quantity="1", timestamp=SOURCE_TIME, provenance=provenance()).quantity == Decimal("1")
    assert PriceSnapshot(symbol="BTC-USD", price="100", timestamp=SOURCE_TIME, provenance=provenance()).price == Decimal("100")


def test_schema_version_is_explicit_and_unsupported_versions_fail() -> None:
    trade = MarketTrade(
        symbol="BTC-USD", price=Decimal("100"), quantity=Decimal("1"), timestamp=SOURCE_TIME, provenance=provenance()
    )
    assert trade.model_dump()["schema_version"] == DOMAIN_SCHEMA_VERSION
    invalid = trade.model_dump()
    invalid["schema_version"] = "9.9"
    with pytest.raises(ValidationError, match="unsupported schema version"):
        MarketTrade.model_validate(invalid)


def test_domain_module_has_no_provider_or_transport_imports() -> None:
    source = __import__("pathlib").Path(__file__).parents[1] / "src" / "traid" / "domain"
    text = "\n".join(path.read_text().lower() for path in source.glob("*.py"))
    assert not re.search(r"\b(hyperliquid|websocket|rest|sdk|requests)\b", text)
