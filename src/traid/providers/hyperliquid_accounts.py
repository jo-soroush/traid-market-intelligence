"""Read-only Hyperliquid account-data client for C11 (public ``info`` endpoint only).

Only four documented info request types are ever sent: ``clearinghouseState``,
``userFillsByTime``, ``userFunding`` and ``userRole``. No credential, exchange route or order
action exists here. Raw provider dictionaries never leave this
module: responses are validated and normalized into C11 canonical observations.

Verified provider behavior used (docs, and a live read-only check on public HLP
vault accounts): ``clearinghouseState`` carries a response ``time`` and signed
``szi`` per ``oneWay`` position; ``userFillsByTime`` returns fills in ascending time,
is paged by re-using the last returned time as the next inclusive ``startTime`` (so
boundary records repeat), returns at most 2000 fills per page and only the 10000
most recent fills at all; ``userFunding`` pages the same way (500 per page observed).

Paging never trusts a page size: it continues until the provider returns an empty
page, and the cursor strictly increases every request, so it always terminates.
A page whose records all share the cursor millisecond cannot be advanced by its own
times; the cursor then moves 1 ms on, and if that page reached the smallest
documented page limit (500) records at that millisecond may have been cut off, so
the history is INCOMPLETE (PAGE_LIMIT_REACHED_WITHIN_ONE_MILLISECOND).
A fill history is COMPLETE only if that happened with fewer than 10000 unique fills
in total, the query was open-ended (provider default end = current time) and no
client bound or stall intervened; otherwise it is INCOMPLETE with explicit reasons.
Receipt time comes from an injectable clock; provider times are never backdated or
shifted. Requests are bounded by ``max_pages`` per history; a provider 429 raises
``AdapterRateLimitError`` and nothing is retried or slept here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from traid.domain.models import SourceProvenance
from traid.exchange.errors import AdapterError, AdapterErrorCode, AdapterRateLimitError, ProviderDataError
from traid.whales.models import (
    BTC, FILL_HISTORY_CAP, BtcPosition, Completeness, FillHistory, FillLiquidation, FundingHistory,
    PositionSnapshot, WalletFill, WalletFunding, address,
)

DEFAULT_INFO_URL = "https://api.hyperliquid.xyz/info"
MIN_DOCUMENTED_PAGE = 500  # docs: time-range responses return 500 (userFillsByTime: 2000)
ALLOWED_INFO_TYPES = frozenset({"clearinghouseState", "userFillsByTime", "userFunding", "userRole"})
ROLES = frozenset({"user", "vault", "subAccount", "agent", "missing"})
SOURCE = "hyperliquid"
SOURCE_TYPE = "public_info"
UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _ms(value: Any) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderDataError("provider timestamp must be non-negative integer milliseconds")
    return EPOCH + timedelta(milliseconds=value)  # exact; no float conversion


def _to_ms(value: datetime) -> int:
    return (value.astimezone(UTC) - EPOCH) // timedelta(milliseconds=1)


def _dec(value: Any, *, allow_number: bool = False) -> Decimal:
    if isinstance(value, bool) or not (isinstance(value, str) or (allow_number and isinstance(value, (int, float)))):
        raise ProviderDataError("provider decimal must be a decimal string")
    try:
        result = Decimal(value.strip() if isinstance(value, str) else repr(value))
    except InvalidOperation as error:
        raise ProviderDataError("provider decimal is malformed") from error
    if not result.is_finite():
        raise ProviderDataError("provider decimal must be finite")
    return result


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderDataError("provider record shape is invalid")
    return value


def _list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderDataError("provider response shape is invalid")
    return value


def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderDataError("provider identifier must be a non-negative integer")
    return value


class HyperliquidAccountClient:
    def __init__(self, *, info_url: str = DEFAULT_INFO_URL, timeout: float = 10.0, max_pages: int = 10,
                 clock: Callable[[], datetime] | None = None,
                 transport: Callable[[Mapping[str, Any]], Any] | None = None) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or not 1 <= max_pages <= 100:
            raise ValueError("max_pages must be an integer in 1..100")
        self.info_url = info_url
        self.timeout = timeout
        self.max_pages = max_pages
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._transport = transport or self._http

    # ----------------------------------------------------------------- transport
    def _http(self, payload: Mapping[str, Any]) -> Any:
        request = Request(self.info_url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if error.code == 429:
                raise AdapterRateLimitError() from error
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "provider HTTP request failed") from error
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise AdapterError(AdapterErrorCode.PROVIDER_FAILURE, "provider request failed") from error

    def _post(self, payload: Mapping[str, Any]) -> tuple[Any, datetime]:
        if payload.get("type") not in ALLOWED_INFO_TYPES:
            raise AdapterError(AdapterErrorCode.CONTRACT, "info request type is not allowed")
        data = self._transport(dict(payload))
        received = self._clock()
        if not isinstance(received, datetime) or received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("clock must return an aware datetime")
        return data, received.astimezone(UTC)

    def _provenance(self, source_id: str, received: datetime, source_time: datetime | None = None):
        try:
            return SourceProvenance(source=SOURCE, source_type=SOURCE_TYPE, source_id=source_id,
                                    source_timestamp=source_time, received_timestamp=received)
        except ValidationError as error:  # e.g. provider time ahead of the receipt clock
            raise ProviderDataError("provider time is after local receipt") from error

    # -------------------------------------------------------------------- reads
    def account_role(self, wallet: str) -> str:
        """Provider role: user, vault, subAccount, agent or missing (agent/missing hold no account data)."""
        data, _ = self._post({"type": "userRole", "user": address(wallet)})
        role = _mapping(data).get("role")
        if role not in ROLES:
            raise ProviderDataError("unknown account role")
        return role

    def position_snapshot(self, wallet: str) -> PositionSnapshot:
        wallet = address(wallet)
        data, received = self._post({"type": "clearinghouseState", "user": wallet})
        return parse_clearinghouse_state(
            wallet, data, lambda source_time: self._provenance("clearinghouseState", received, source_time))

    def fill_history(self, wallet: str, start: datetime) -> FillHistory:
        wallet = address(wallet)
        records, pages, reasons, received = self._paged("userFillsByTime", wallet, start, _fill_key)
        if len(records) >= FILL_HISTORY_CAP:
            reasons.append("PROVIDER_FILL_HISTORY_CAP_REACHED")
        fills = tuple(sorted((parse_fill(wallet, r) for r in records.values() if _coin(r) == BTC),
                             key=lambda f: (f.time, f.tid, f.oid)))
        return _build(FillHistory, wallet, start, pages, len(records), reasons,
                      self._provenance("userFillsByTime", received), fills=fills)

    def funding_history(self, wallet: str, start: datetime) -> FundingHistory:
        wallet = address(wallet)
        records, pages, reasons, received = self._paged("userFunding", wallet, start, _funding_key)
        funding = tuple(sorted((parse_funding(wallet, r) for r in records.values() if _funding_coin(r) == BTC),
                               key=lambda f: f.time))
        return _build(FundingHistory, wallet, start, pages, len(records), reasons,
                      self._provenance("userFunding", received), funding=funding)

    def _paged(self, kind: str, wallet: str, start: datetime, key):
        """Inclusive-start paging until an empty page; boundary repeats deduplicate by identity."""
        cursor = _to_ms(start)
        if cursor < 0:
            raise ValueError("start must not precede the epoch")
        records: dict[Any, Mapping[str, Any]] = {}
        reasons: list[str] = []
        pages, received = 0, None
        while True:
            if pages == self.max_pages:
                reasons.append("CLIENT_PAGE_LIMIT_REACHED")
                break
            data, received = self._post({"type": kind, "user": wallet, "startTime": cursor})
            pages += 1
            page = _list(data)
            times = []
            for raw in page:
                raw = _mapping(raw)
                when = _to_ms(_ms(raw.get("time")))
                if when < cursor:
                    raise ProviderDataError("provider returned a record before the requested start")
                times.append(when)
                k = key(raw)
                kept = records.get(k)
                if kept is None:
                    records[k] = raw
                elif kept != raw:
                    raise ProviderDataError("provider returned conflicting records for one identity")
            if not page:
                break
            following = max(times)
            if following == cursor:
                # Every record shares the cursor time: re-requesting it would repeat this page.
                if len(page) >= MIN_DOCUMENTED_PAGE:
                    reasons.append("PAGE_LIMIT_REACHED_WITHIN_ONE_MILLISECOND")
                following = cursor + 1
            cursor = following
        return records, pages, reasons, received


def _build(cls, wallet, start, pages, total, reasons, provenance, **records):
    try:
        return cls(address=wallet, requested_start=start, pages=pages, total_record_count=total,
                   completeness=Completeness.INCOMPLETE if reasons else Completeness.COMPLETE,
                   reasons=tuple(dict.fromkeys(reasons)), provenance=provenance, **records)
    except ValidationError as error:
        raise ProviderDataError("provider history is internally inconsistent") from error


def _coin(raw: Mapping[str, Any]) -> str:
    coin = raw.get("coin")
    if not isinstance(coin, str) or not coin:
        raise ProviderDataError("fill coin must be a non-empty string")
    return coin


def _fill_key(raw: Mapping[str, Any]):
    return _int(raw.get("tid")), _int(raw.get("oid"))


def _funding_delta(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    delta = _mapping(raw.get("delta"))
    if delta.get("type") != "funding":
        raise ProviderDataError("userFunding returned a non-funding delta")
    return delta


def _funding_coin(raw: Mapping[str, Any]) -> str:
    coin = _funding_delta(raw).get("coin")
    if not isinstance(coin, str) or not coin:
        raise ProviderDataError("funding coin must be a non-empty string")
    return coin


def _funding_key(raw: Mapping[str, Any]):
    return _funding_coin(raw), _to_ms(_ms(raw.get("time")))


# ---------------------------------------------------------------------- parsers
def parse_clearinghouse_state(wallet: str, data: Any, provenance_for) -> PositionSnapshot:
    data = _mapping(data)
    snapshot_time = _ms(data.get("time"))
    margin = data.get("marginSummary")
    account_value = None if margin is None else _dec(_mapping(margin).get("accountValue"))
    btc = None
    for item in _list(data.get("assetPositions")):
        item = _mapping(item)
        if item.get("type") != "oneWay":
            raise ProviderDataError("unsupported position mode")
        position = _mapping(item.get("position"))
        if position.get("coin") != BTC:
            continue
        if btc is not None:
            raise ProviderDataError("provider reported BTC twice in one snapshot")
        leverage = _mapping(position.get("leverage"))
        liquidation = position.get("liquidationPx")
        try:
            btc = BtcPosition(
                size=_dec(position.get("szi")), entry_price=_dec(position.get("entryPx")),
                position_value=_dec(position.get("positionValue")), unrealized_pnl=_dec(position.get("unrealizedPnl")),
                liquidation_price=None if liquidation is None else _dec(liquidation),
                leverage_type=leverage.get("type"), leverage=_int(leverage.get("value")),
                margin_used=_dec(position.get("marginUsed")))
        except ValidationError as error:
            raise ProviderDataError("provider BTC position is invalid") from error
    try:
        return PositionSnapshot(address=wallet, snapshot_time=snapshot_time, btc_position=btc,
                                account_value=account_value, provenance=provenance_for(snapshot_time))
    except ValidationError as error:
        raise ProviderDataError("provider snapshot is invalid") from error


def parse_fill(wallet: str, raw: Mapping[str, Any]) -> WalletFill:
    raw = _mapping(raw)
    marker = raw.get("liquidation")
    liquidation = None
    if marker is not None:
        marker = _mapping(marker)
        liquidation = dict(liquidated_user=marker.get("liquidatedUser"),
                           mark_price=_dec(marker.get("markPx"), allow_number=True), method=marker.get("method"))
    builder = raw.get("builderFee")
    try:
        return WalletFill(
            address=wallet, coin=_coin(raw), price=_dec(raw.get("px")), size=_dec(raw.get("sz")),
            side=raw.get("side"), time=_ms(raw.get("time")), start_position=_dec(raw.get("startPosition")),
            direction_label=raw.get("dir"), closed_pnl=_dec(raw.get("closedPnl")), fee=_dec(raw.get("fee")),
            fee_token=raw.get("feeToken").strip() if isinstance(raw.get("feeToken"), str) else raw.get("feeToken"),
            builder_fee=None if builder is None else _dec(builder), tid=_int(raw.get("tid")), oid=_int(raw.get("oid")),
            transaction_hash=raw.get("hash"), crossed=_bool(raw.get("crossed")),
            liquidation=None if liquidation is None else FillLiquidation(**liquidation))
    except ValidationError as error:
        raise ProviderDataError("provider fill is invalid") from error


def parse_funding(wallet: str, raw: Mapping[str, Any]) -> WalletFunding:
    raw = _mapping(raw)
    delta = _funding_delta(raw)
    try:
        return WalletFunding(address=wallet, coin=delta.get("coin"), time=_ms(raw.get("time")),
                             usdc=_dec(delta.get("usdc")), position_size=_dec(delta.get("szi")),
                             funding_rate=_dec(delta.get("fundingRate")))
    except ValidationError as error:
        raise ProviderDataError("provider funding entry is invalid") from error


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ProviderDataError("provider flag must be boolean")
    return value
