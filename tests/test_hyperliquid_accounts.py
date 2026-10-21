from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import traid.providers.hyperliquid_accounts as module
from traid.exchange.errors import AdapterError, AdapterErrorCode, AdapterRateLimitError, ProviderDataError
from traid.providers.hyperliquid_accounts import EPOCH, HyperliquidAccountClient
from traid.whales import Completeness

D = Decimal
UTC = timezone.utc
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "hyperliquid_accounts.json").read_text())
W1 = "0x010461c14e146ac35fe42271bdc1134ee31c703a"   # public HLP child vault (userRole "vault")
W2 = "0x31ca8395cf837de08b24da3f660e77761dfb974b"   # public HLP child vault
HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"  # public HLP parent vault


def ms(value):
    return EPOCH + timedelta(milliseconds=value)


class Provider:
    """Simulated info endpoint: time-ordered records, inclusive startTime, fixed page size."""

    def __init__(self, records=(), page=2000, other=None):
        self.records = sorted(records, key=lambda r: r["time"])
        self.page = page
        self.other = other or {}
        self.requests = []

    def __call__(self, payload):
        self.requests.append(payload)
        if payload["type"] in ("userFillsByTime", "userFunding"):
            return [r for r in self.records if r["time"] >= payload["startTime"]][:self.page]
        return self.other[payload["type"]]


def client(provider, received=None, **kw):
    return HyperliquidAccountClient(transport=provider, clock=lambda: received or ms(2_000_000_000_000), **kw)


def raw_fill(tid, t, start="0", sz="1", side="B", coin="BTC", **extra):
    return dict(dict(coin=coin, px="100000.0", sz=sz, side=side, time=t, startPosition=start, dir="Open Long",
                     closedPnl="0.0", hash="0xab", oid=tid + 7, crossed=False, fee="0.01", tid=tid, feeToken="USDC"), **extra)


# ----------------------------------------------------------------- real snapshots
def test_real_clearinghouse_states_parse_with_provider_semantics():
    for wallet, sign in ((W1, 1), (W2, -1)):
        data = FIXTURE["clearinghouseState"][wallet]
        snap = client(Provider(other={"clearinghouseState": data}), received=ms(data["time"] + 500)).position_snapshot(wallet)
        raw = next(p["position"] for p in data["assetPositions"] if p["position"]["coin"] == "BTC")
        p = snap.btc_position
        assert snap.snapshot_time == ms(data["time"]) and snap.provenance.source_timestamp == snap.snapshot_time
        assert snap.provenance.received_timestamp == ms(data["time"] + 500)
        assert p.size == D(raw["szi"]) and (p.size > 0) == (sign > 0)
        assert (p.entry_price, p.position_value, p.unrealized_pnl) == (D(raw["entryPx"]), D(raw["positionValue"]), D(raw["unrealizedPnl"]))
        assert p.liquidation_price == (None if raw["liquidationPx"] is None else D(raw["liquidationPx"]))
        assert (p.leverage_type, p.leverage) == (raw["leverage"]["type"], raw["leverage"]["value"])
    assert FIXTURE["clearinghouseState"][W1]["assetPositions"][0]["position"]["liquidationPx"] is None  # real null


def _state(**position):
    base = dict(coin="BTC", szi="1.5", entryPx="100000", positionValue="150000", unrealizedPnl="10", liquidationPx="90000",
                leverage={"type": "isolated", "value": 5}, marginUsed="30000")
    base.update(position)
    return {"time": 1_700_000_000_000, "marginSummary": {"accountValue": "50000"},
            "assetPositions": [{"type": "oneWay", "position": base}]}


def snap_of(data, received=ms(1_700_000_000_500)):
    return client(Provider(other={"clearinghouseState": data}), received=received).position_snapshot(W1)


def test_no_btc_position_is_reported_flat_not_missing():
    data = {"time": 1_700_000_000_000, "assetPositions": [
        {"type": "oneWay", "position": dict(_state()["assetPositions"][0]["position"], coin="ETH")}]}
    snap = snap_of(data)
    assert snap.btc_position is None and snap.account_value is None


@pytest.mark.parametrize("data", [
    dict(_state(), assetPositions=[{"type": "hedge", "position": _state()["assetPositions"][0]["position"]}]),
    dict(_state(), assetPositions=_state()["assetPositions"] * 2),
    _state(szi="0.0"),
    _state(szi=1.5),
    _state(szi="abc"),
    _state(szi="NaN"),
    _state(entryPx="-1"),
    _state(liquidationPx="0"),
    _state(leverage={"type": "portfolio", "value": 5}),
    _state(leverage={"type": "cross", "value": True}),
    dict(_state(), time="1700000000000"),
    dict(_state(), time=None),
    dict(_state(), assetPositions=None),
    [],
])
def test_malformed_or_contradictory_snapshots_are_rejected(data):
    with pytest.raises(ProviderDataError):
        snap_of(data)


def test_provider_time_after_local_receipt_is_rejected_not_backdated():
    with pytest.raises(ProviderDataError, match="after local receipt"):
        snap_of(_state(), received=ms(1_699_999_999_999))


def test_hip3_and_other_coins_are_not_btc():
    data = _state()
    data["assetPositions"].append({"type": "oneWay", "position": dict(data["assetPositions"][0]["position"], coin="xyz:BTC")})
    assert snap_of(data).btc_position.size == D("1.5")


# ----------------------------------------------------------------------- roles
@pytest.mark.parametrize("role", ["user", "vault", "subAccount", "agent", "missing"])
def test_account_roles_are_reported_verbatim(role):
    assert client(Provider(other={"userRole": {"role": role}})).account_role(W1) == role


def test_real_vault_roles_and_unknown_role():
    assert client(Provider(other={"userRole": FIXTURE["userRole"][HLP]})).account_role(HLP) == "vault"
    with pytest.raises(ProviderDataError):
        client(Provider(other={"userRole": {"role": "admin"}})).account_role(W1)


# ------------------------------------------------------------------------- fills
def test_real_fills_page_to_a_complete_history_with_boundary_repeats_deduplicated():
    records = FIXTURE["userFillsByTime_btc"][W1] + FIXTURE["userFillsByTime_other_coin"]
    provider = Provider(records, page=10)   # small pages force several inclusive-boundary repeats
    start = ms(min(r["time"] for r in records))
    history = client(provider, received=ms(max(r["time"] for r in records) + 1000)).fill_history(W1, start)
    assert history.completeness is Completeness.COMPLETE and history.reasons == ()
    assert len(history.fills) == len(FIXTURE["userFillsByTime_btc"][W1]) and history.total_record_count == len(records)
    assert history.pages == len(provider.requests) >= 3
    assert [f.time for f in history.fills] == sorted(f.time for f in history.fills)
    assert all(r["type"] == "userFillsByTime" and r["user"] == W1 for r in provider.requests)
    first = history.fills[0]
    raw = next(r for r in records if r["tid"] == first.tid)
    assert (first.price, first.size, first.side, first.start_position, first.closed_pnl, first.fee) == (
        D(raw["px"]), D(raw["sz"]), raw["side"], D(raw["startPosition"]), D(raw["closedPnl"]), D(raw["fee"]))
    assert first.direction_label == raw["dir"] and first.transaction_hash == raw["hash"]


def test_paging_trusts_no_page_size():
    records = [raw_fill(i, 1_700_000_000_000 + i * 1000) for i in range(25)]
    for page in (1, 7, 500, 2000):
        history = client(Provider(records, page=page), max_pages=100).fill_history(W1, ms(1_700_000_000_000))
        assert history.completeness is Completeness.COMPLETE and len(history.fills) == 25
    small_bound = client(Provider(records, page=1), max_pages=10).fill_history(W1, ms(1_700_000_000_000))
    assert small_bound.reasons == ("CLIENT_PAGE_LIMIT_REACHED",)


def test_client_page_bound_makes_history_incomplete():
    records = [raw_fill(i, 1_700_000_000_000 + i) for i in range(50)]
    history = client(Provider(records, page=10), max_pages=3).fill_history(W1, ms(1_700_000_000_000))
    assert history.completeness is Completeness.INCOMPLETE and history.reasons == ("CLIENT_PAGE_LIMIT_REACHED",)


def test_provider_history_cap_makes_history_incomplete():
    records = [raw_fill(i, 1_700_000_000_000 + i, coin="ETH") for i in range(10000)]
    history = client(Provider(records, page=2000), max_pages=20).fill_history(W1, ms(1_700_000_000_000))
    assert "PROVIDER_FILL_HISTORY_CAP_REACHED" in history.reasons and history.fills == ()
    assert history.total_record_count == 10000 and history.completeness is Completeness.INCOMPLETE


def test_a_full_page_within_one_millisecond_is_incomplete():
    records = [raw_fill(i, 1_700_000_000_000) for i in range(600)] + [raw_fill(900, 1_700_000_000_005)]
    history = client(Provider(records, page=500)).fill_history(W1, ms(1_700_000_000_000))
    assert history.reasons == ("PAGE_LIMIT_REACHED_WITHIN_ONE_MILLISECOND",)
    assert 900 in {f.tid for f in history.fills}   # paging moved past the stuck millisecond


def test_a_short_page_within_one_millisecond_is_complete():
    records = [raw_fill(i, 1_700_000_000_000) for i in range(3)] + [raw_fill(9, 1_700_000_000_002)]
    history = client(Provider(records, page=2000)).fill_history(W1, ms(1_700_000_000_000))
    assert history.completeness is Completeness.COMPLETE and len(history.fills) == 4


def fixed(page):
    """A provider that returns one page as given, then nothing."""
    pages = [page]
    return lambda payload: pages.pop() if pages else []


@pytest.mark.parametrize("records", [
    [raw_fill(1, 1_700_000_000_000), raw_fill(1, 1_700_000_000_000, sz="2")],      # one identity, two contents
    [raw_fill(1, 1_699_999_999_999)],                                               # before requested start
    [raw_fill(1, 1_700_000_000_000, side="X")],
    [raw_fill(1, 1_700_000_000_000, crossed="false")],
    [dict(raw_fill(1, 1_700_000_000_000), tid=-1)],
    [raw_fill(1, 1_700_000_000_000, coin="")],
    [raw_fill(1, 1_700_000_000_000, liquidation={"liquidatedUser": "nope", "markPx": 1, "method": "market"})],
    [raw_fill(1, 1_700_000_000_000, liquidation={"markPx": 1, "method": "magic"})],
    ["not a mapping"],
])
def test_malformed_or_conflicting_fills_are_rejected(records):
    with pytest.raises(ProviderDataError):
        client(fixed(records)).fill_history(W1, ms(1_700_000_000_000))


def test_non_btc_fills_are_counted_but_not_interpreted():
    records = [raw_fill(1, 1_700_000_000_000, coin="@107", px=None), raw_fill(2, 1_700_000_000_001)]
    history = client(Provider(records)).fill_history(W1, ms(1_700_000_000_000))
    assert history.total_record_count == 2 and [f.tid for f in history.fills] == [2]


def test_liquidation_marker_is_preserved_from_the_documented_shape():
    marker = {"liquidatedUser": W1.upper().replace("0X", "0x"), "markPx": 98765.4, "method": "backstop"}
    history = client(Provider([raw_fill(1, 1_700_000_000_000, liquidation=marker, feeToken=" USDC")])).fill_history(
        W1, ms(1_700_000_000_000))
    (f,) = history.fills
    assert f.liquidation.liquidated_user == W1 and f.liquidation.mark_price == D("98765.4")
    assert f.liquidation.method == "backstop" and f.fee_token == "USDC"


# ----------------------------------------------------------------------- funding
def test_real_funding_parses_and_non_btc_is_counted_only():
    records = FIXTURE["userFunding"]
    history = client(Provider(records, page=500)).funding_history(W1, ms(min(r["time"] for r in records)))
    btc = [r for r in records if r["delta"]["coin"] == "BTC"]
    assert len(history.funding) == len(btc) and history.total_record_count == len(records)
    assert history.funding[0].usdc == D(btc[0]["delta"]["usdc"].strip())
    assert history.completeness is Completeness.COMPLETE


def test_non_funding_delta_is_rejected():
    bad = [{"time": 1_700_000_000_000, "hash": "0x0", "delta": {"type": "deposit", "usdc": "5"}}]
    with pytest.raises(ProviderDataError):
        client(Provider(bad)).funding_history(W1, ms(1_700_000_000_000))


# ----------------------------------------------------------------- transport safety
def test_only_documented_read_only_info_types_can_be_sent():
    c = client(Provider())
    with pytest.raises(AdapterError) as error:
        c._post({"type": "order", "user": W1})
    assert error.value.code is AdapterErrorCode.CONTRACT
    assert module.ALLOWED_INFO_TYPES == {"clearinghouseState", "userFillsByTime", "userFunding", "userRole"}
    source = inspect.getsource(module).lower()
    for banned in ("/exchange", "private_key", "privatekey", "signature", "sign_", "eth_account", "nonce", "secret"):
        assert banned not in source
    assert c.info_url == "https://api.hyperliquid.xyz/info"


def test_http_errors_map_to_adapter_errors(monkeypatch):
    c = HyperliquidAccountClient()

    def raise_429(*args, **kwargs):
        raise HTTPError("u", 429, "slow down", {}, io.BytesIO())
    monkeypatch.setattr(module, "urlopen", raise_429)
    with pytest.raises(AdapterRateLimitError):
        c.account_role(W1)

    def raise_500(*args, **kwargs):
        raise HTTPError("u", 500, "boom", {}, io.BytesIO())
    monkeypatch.setattr(module, "urlopen", raise_500)
    with pytest.raises(AdapterError) as error:
        c.account_role(W1)
    assert error.value.code is AdapterErrorCode.PROVIDER_FAILURE


@pytest.mark.parametrize("kw", [dict(timeout=0), dict(max_pages=0), dict(max_pages=101), dict(max_pages=True)])
def test_client_bounds_are_validated(kw):
    with pytest.raises(ValueError):
        HyperliquidAccountClient(**kw)


def test_naive_clock_and_bad_addresses_are_rejected():
    with pytest.raises(ValueError):
        HyperliquidAccountClient(transport=Provider(other={"userRole": {"role": "user"}}),
                                 clock=lambda: datetime(2026, 1, 1)).account_role(W1)
    for bad in ("0x123", W1[:-1] + "g", "010461c14e146ac35fe42271bdc1134ee31c703a00"):
        with pytest.raises(ValueError):
            client(Provider(other={"userRole": {"role": "user"}})).account_role(bad)
