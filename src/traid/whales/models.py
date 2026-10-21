"""C11 canonical whale observations: curated watchlist, snapshots, fills and funding.

Observed provider values keep their provider meaning; nothing here is derived. A
position snapshot is what Hyperliquid's ``clearinghouseState`` reported at its own
``time``; a fill is one ``userFillsByTime`` record; a funding entry is one
``userFunding`` record. Paged histories carry their completeness explicitly: only
the 10000 most recent fills are available from the provider, so a history is
COMPLETE only when its paging proved it (see the account client).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, ROUND_HALF_EVEN
from enum import StrEnum
import hashlib
import json
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from traid.domain.models import CanonicalModel, SourceProvenance

ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
VERSION_PATTERN = r"^[A-Za-z0-9._-]+$"
MAX_WATCHLIST = 200
MAX_HISTORY_RECORDS = 100000
FILL_HISTORY_CAP = 10000  # provider docs: only the 10000 most recent fills are available
CANONICAL = Context(prec=8192, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
BTC = "BTC"  # first perp dex coin name; HIP-3 "dex:coin" and spot "@n" assets are not BTC perps


def utc(value, name: str = "timestamp") -> datetime:
    if isinstance(value, str):  # JSON round trip
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def address(value) -> str:
    """Hyperliquid account address: 42-character hex, compared in lowercase."""
    if not isinstance(value, str) or not ADDRESS_PATTERN.match(value.strip()):
        raise ValueError("address must be 0x followed by 40 hexadecimal characters")
    return value.strip().lower()


def canonical_json(value) -> str:
    def convert(v):
        if isinstance(v, dict):
            return {k: convert(v[k]) for k in sorted(v)}
        if isinstance(v, (list, tuple)):
            return [convert(x) for x in v]
        if isinstance(v, Decimal):  # equal values share one identity, whatever the spelling
            return format(v.normalize(CANONICAL), "f")
        if isinstance(v, timedelta):
            return f"{v // timedelta(microseconds=1)}us"
        if isinstance(v, datetime):
            return v.isoformat()
        return v
    return json.dumps(convert(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(model: CanonicalModel) -> str:
    return hashlib.sha256(canonical_json(model.model_dump(mode="python")).encode()).hexdigest()


class WhaleModel(CanonicalModel):
    @field_validator("added_at", "time", "snapshot_time", "requested_start", "evaluation_time",
                     "observed_through", "window_start", "earliest_snapshot_time", "latest_snapshot_time",
                     mode="before", check_fields=False)
    @classmethod
    def aware(cls, value):
        return None if value is None else utc(value)

    @field_validator("address", "liquidated_user", mode="before", check_fields=False)
    @classmethod
    def valid_address(cls, value):
        return None if value is None else address(value)


# ------------------------------------------------------------------------- watchlist
class AccountRole(StrEnum):
    """Provider ``userRole`` values that hold their own account data ("agent"/"missing" do not)."""
    USER = "user"
    VAULT = "vault"
    SUB_ACCOUNT = "subAccount"


class WalletEntry(WhaleModel):
    address: str
    label: str = Field(min_length=1, max_length=80)
    account_role: AccountRole | None = None  # provider-reported if checked, else unknown
    rationale: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=200)  # who or what curated this entry
    added_at: datetime


class Watchlist(WhaleModel):
    """A caller-curated, versioned BTC wallet sample. Inclusion asserts nothing about skill."""
    watchlist_version: str = Field(min_length=1, max_length=64, pattern=VERSION_PATTERN)
    entries: tuple[WalletEntry, ...] = Field(min_length=1, max_length=MAX_WATCHLIST)
    limitations: tuple[str, ...] = (
        "CURATED_SAMPLE_NOT_EXCHANGE_TOTAL",
        "INCLUSION_IS_NOT_SKILL_OR_SMART_MONEY",
        "NOT_TRADE_AUTHORIZATION",
    )

    @model_validator(mode="after")
    def ordered_unique(self):
        addresses = [e.address for e in self.entries]
        if addresses != sorted(set(addresses)):
            raise ValueError("watchlist entries must be unique and ordered by address; use Watchlist.build")
        return self

    @classmethod
    def build(cls, watchlist_version: str, entries) -> "Watchlist":
        """Deterministic order; identical repeats collapse; conflicting repeats are rejected."""
        by_address: dict[str, WalletEntry] = {}
        for entry in entries:
            entry = WalletEntry.model_validate(entry.model_dump() if isinstance(entry, WalletEntry) else entry)
            kept = by_address.setdefault(entry.address, entry)
            if kept != entry:
                raise ValueError(f"conflicting watchlist entries for {entry.address}")
        return cls(watchlist_version=watchlist_version, entries=tuple(by_address[a] for a in sorted(by_address)))

    def digest(self) -> str:
        return digest(self)

    def entry(self, wallet: str) -> WalletEntry | None:
        wallet = address(wallet)
        return next((e for e in self.entries if e.address == wallet), None)


# ----------------------------------------------------------------------- observations
class BtcPosition(WhaleModel):
    """One ``assetPositions`` entry for coin BTC, as the provider reported it."""
    size: Decimal                       # szi: signed, positive long, negative short
    entry_price: Decimal = Field(gt=0)  # entryPx
    position_value: Decimal = Field(ge=0)  # positionValue: provider notional, price basis unverified
    unrealized_pnl: Decimal             # unrealizedPnl: provider value
    liquidation_price: Decimal | None   # liquidationPx: provider estimate, may be null
    leverage_type: Literal["cross", "isolated"]
    leverage: int = Field(ge=1)
    margin_used: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def nonzero(self):
        if self.size == 0:
            raise ValueError("a reported position must have non-zero size")
        if self.liquidation_price is not None and self.liquidation_price <= 0:
            raise ValueError("liquidation price estimate must be positive when present")
        return self


class PositionSnapshot(WhaleModel):
    """``clearinghouseState`` at provider ``time``; btc_position None = no BTC position reported."""
    address: str
    snapshot_time: datetime
    btc_position: BtcPosition | None
    account_value: Decimal | None  # marginSummary.accountValue, provider value
    provenance: SourceProvenance

    @model_validator(mode="after")
    def timed_by_provider(self):
        if self.provenance.source_timestamp != self.snapshot_time:
            raise ValueError("snapshot provenance must carry the provider snapshot time")
        return self


class FillLiquidation(WhaleModel):
    """Provider liquidation marker on a fill (``liquidation`` field)."""
    liquidated_user: str | None
    mark_price: Decimal = Field(gt=0)
    method: Literal["market", "backstop"]


class WalletFill(WhaleModel):
    """One BTC perp fill as reported by ``userFillsByTime``."""
    address: str
    coin: Literal["BTC"] = BTC
    price: Decimal = Field(gt=0)
    size: Decimal = Field(gt=0)
    side: Literal["B", "A"]            # B: buy (position size increases), A: sell
    time: datetime
    start_position: Decimal            # startPosition: signed size before this fill
    direction_label: str = Field(min_length=1)  # provider `dir`, documented as frontend display text
    closed_pnl: Decimal                # closedPnl: provider value, fee treatment unverified
    fee: Decimal                       # negative means rebate (provider docs)
    fee_token: str = Field(min_length=1)
    builder_fee: Decimal | None = None
    tid: int = Field(ge=0)
    oid: int = Field(ge=0)
    transaction_hash: str = Field(min_length=1)
    crossed: bool
    liquidation: FillLiquidation | None = None

    @property
    def end_position(self) -> Decimal:
        # Exact and ambient-context independent: copy_negate never rounds, and the addition
        # runs in the explicit 8192-digit context (provider decimals are far shorter).
        delta = self.size if self.side == "B" else self.size.copy_negate()
        return CANONICAL.add(self.start_position, delta)

    @property
    def identity(self) -> tuple[int, int]:
        return self.tid, self.oid


class WalletFunding(WhaleModel):
    """One ``userFunding`` delta of type funding for coin BTC."""
    address: str
    coin: Literal["BTC"] = BTC
    time: datetime
    usdc: Decimal            # provider amount (example: negative when a long pays positive funding)
    position_size: Decimal   # szi at the funding time
    funding_rate: Decimal


class Completeness(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class _PagedHistory(WhaleModel):
    """Records from ``requested_start`` through the receipt of the final page (open-ended query)."""
    address: str
    requested_start: datetime
    pages: int = Field(ge=1)
    total_record_count: int = Field(ge=0)   # unique records of every coin that the paging returned
    completeness: Completeness
    reasons: tuple[str, ...]
    provenance: SourceProvenance            # received_timestamp: receipt of the final page

    def _records(self):
        raise NotImplementedError

    @model_validator(mode="after")
    def consistent(self):
        if (self.completeness is Completeness.COMPLETE) == bool(self.reasons):
            raise ValueError("completeness must be COMPLETE exactly when no reason degrades it")
        received = self.provenance.received_timestamp
        if self.requested_start > received:
            raise ValueError("history cannot start after its own receipt")
        records = self._records()
        if len(records) > self.total_record_count or len(records) > MAX_HISTORY_RECORDS:
            raise ValueError("record count exceeds the reported total")
        for record in records:
            if record.address != self.address:
                raise ValueError("history records must belong to the history wallet")
            if not self.requested_start <= record.time <= received:
                raise ValueError("record time outside the queried range or after receipt")
        return self


class FillHistory(_PagedHistory):
    fills: tuple[WalletFill, ...]

    def _records(self):
        return self.fills


class FundingHistory(_PagedHistory):
    funding: tuple[WalletFunding, ...]

    def _records(self):
        return self.funding
