from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, ROUND_UP
from fractions import Fraction
import random

import pytest
from pydantic import ValidationError

from traid.domain.models import OrderBookLevel, OrderBookSnapshot, SourceProvenance, DataQualityState
from traid.exchange import Capability, CapabilityAvailability, CapabilityCoverage
from traid.quality import ContinuityStatus, RecoveryStatus, default_quality_policy
from traid.liquidity import LiquidityConfig, Metric, OrderRequest, Side, analyze_book

D = Decimal
NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def book(bids=(("100", "2"), ("99", "3"), ("98", "5")),
         asks=(("102", "2"), ("103", "3"), ("104", "5")), age=0):
    time = NOW - timedelta(seconds=age)
    return OrderBookSnapshot(symbol="BTC", timestamp=time,
        provenance=SourceProvenance(source="fixture", source_type="canonical-test",
                                    source_timestamp=time, received_timestamp=NOW),
        bids=tuple(OrderBookLevel(price=D(p), quantity=D(q)) for p, q in bids),
        asks=tuple(OrderBookLevel(price=D(p), quantity=D(q)) for p, q in asks))


def config(bands=("100", "200"), orders=(("BUY", "4"), ("SELL", "4"), ("BUY", "12"))):
    return LiquidityConfig(symbol="BTC", base_asset="BTC", quote_currency="USD", bands_bps=tuple(map(D, bands)),
        orders=tuple(OrderRequest(side=s, quantity=D(q)) for s, q in orders))


def run(b=None, c=None, **kwargs):
    args = dict(config=c or config(), coverage=CapabilityCoverage(Capability.ORDER_BOOK, CapabilityAvailability.SUPPORTED),
        evaluation_time=NOW, policy=default_quality_policy(), continuity=ContinuityStatus.PROVEN,
        recovery=RecoveryStatus.NONE)
    args.update(kwargs)
    return analyze_book(b or book(), **args)


def test_known_prices_spreads_and_units():
    r = run()
    assert [m.value for m in (r.best_bid, r.best_ask, r.mid, r.spread_absolute)] == list(map(D, (100, 102, 101, 2)))
    with localcontext() as ctx:
        ctx.prec = 50
        assert r.spread_bps.value == D(20000) / 101
    assert r.mid.unit == "USD/BTC" and r.spread_bps.unit == "bps"
    assert r.provenance == book().provenance and r.snapshot_timestamp == NOW
    assert r.quality.trusted_for_current_use
    assert r.formula_version == "c07-liquidity-1"


def test_known_depth_hhi_imbalance_and_decay():
    r = run()
    a, b = r.bands
    assert [a.bid_base.value, a.ask_base.value, a.bid_quote.value, a.ask_quote.value] == list(map(D, (5, 5, 497, 513)))
    assert a.bid_concentration_hhi.value == D("0.52")  # (2/5)^2+(3/5)^2
    assert a.imbalance.value == 0
    assert a.bid_ring_density.value == D("0.05")
    assert a.bid_decay_ratio.reason == "FIRST_BAND_NO_PREDECESSOR"
    assert b.bid_base.value == 10 and b.bid_quote.value == 987
    assert b.bid_decay_ratio.value == 1
    assert b.ask_concentration_hhi.value == D("0.38")
    assert a.bid_base.unit == "BTC" and a.ask_quote.unit == "USD"
    assert a.bid_ring_density.unit == "BTC/bps"


def test_asymmetric_base_imbalance_not_quote_imbalance():
    r = run(book(bids=(("100", "6"),), asks=(("102", "2"),)))
    assert r.bands[0].imbalance.value == D("0.5")
    assert r.bands[0].bid_concentration_hhi.value == 1


def test_inclusive_band_boundaries_and_rings():
    b = book(bids=(("100", "1"), ("99.0001", "2"), ("99", "3"), ("98.9999", "4")))
    r = run(b, config(bands=("100", "101", "102", "103")))
    assert r.bands[0].bid_base.value == 6
    assert r.bands[1].bid_base.value == 10
    assert r.bands[2].bid_ring_density.value == 0
    assert r.bands[2].bid_decay_ratio.value == 0
    assert r.bands[3].bid_decay_ratio.reason == "ZERO_PREVIOUS_DENSITY"


def test_buy_sell_and_partial_known_answer():
    buy, sell, partial = run().executions
    assert buy.complete and sell.complete and not partial.complete
    assert buy.displayed_quote.value == 410 and buy.partial_vwap.value == D("102.5")
    assert sell.displayed_quote.value == 398 and sell.partial_vwap.value == D("99.5")
    assert buy.full_size_slippage_absolute.value == sell.full_size_slippage_absolute.value == D("0.5")
    assert sell.full_size_slippage_bps.value == 50
    with localcontext() as ctx:
        ctx.prec = 50
        assert buy.full_size_slippage_bps.value == D(5000) / 102
    assert partial.displayed_filled_base.value == 10
    assert partial.displayed_quote.value == 1033
    assert partial.partial_vwap.value == D("103.3")
    assert partial.full_size_slippage_bps.value is None
    assert partial.reason == "INSUFFICIENT_DISPLAYED_DEPTH"
    assert buy.hypothetical


@pytest.mark.parametrize('size', ['0.0001', '2', '10', '10.0001'])
def test_explicit_sizes_and_exact_exhaustion(size):
    r = run(c=config(orders=(("BUY", size),))).executions[0]
    assert r.complete == (D(size) <= 10)
    assert r.displayed_filled_base.value == min(D(size), D(10))


@pytest.mark.parametrize('bid,ask', [((), ()), ((), (("102","2"),)), ((("100","2"),), ())])
def test_empty_and_one_sided_are_not_neutral(bid, ask):
    r = run(book(bids=bid, asks=ask))
    assert r.mid.value is None and r.spread_absolute.value is None
    assert r.bands[0].imbalance.reason == "TWO_SIDED_BOOK_REQUIRED"
    assert (r.best_bid.value is None) == (not bid)
    assert (r.best_ask.value is None) == (not ask)
    if not ask:
        assert r.executions[0].reason == "SIDE_UNAVAILABLE"
        assert r.executions[0].displayed_filled_base.value is None


@pytest.mark.parametrize('age,state', [(5,DataQualityState.LIVE), (6,DataQualityState.DELAYED),
                                        (15,DataQualityState.DELAYED), (16,DataQualityState.STALE)])
def test_quality_thresholds(age,state):
    r = run(book(age=age))
    assert r.quality.state is state
    assert (r.mid.value is not None) == (state is DataQualityState.LIVE)
    if state is not DataQualityState.LIVE:
        assert all(m.value is None for m in (r.best_bid,r.best_ask,r.mid))
        assert not r.executions[0].complete


@pytest.mark.parametrize('kwargs', [dict(continuity=ContinuityStatus.UNKNOWN),
    dict(continuity=ContinuityStatus.GAP_RISK), dict(recovery=RecoveryStatus.RECOVERING),
    dict(recovery=RecoveryStatus.RECOVERED_WITHOUT_REPLAY_PROOF),
    dict(coverage=CapabilityCoverage(Capability.ORDER_BOOK,CapabilityAvailability.UNAVAILABLE,"provider unavailable")),
    dict(coverage=CapabilityCoverage(Capability.ORDER_BOOK,CapabilityAvailability.LIMITED,"partial source"))])
def test_degraded_quality_is_preserved(kwargs):
    r = run(**kwargs)
    assert not r.quality.trusted_for_current_use
    assert r.mid.value is None and r.bands[0].bid_base.value is None
    assert r.executions[0].partial_vwap.value is None
    assert r.provenance == book().provenance


def test_missing_source_timestamp_and_mismatched_snapshot():
    b = book(); facts = b.provenance.model_dump();facts['source_timestamp']=None
    b = b.model_copy(update={'provenance':SourceProvenance(**facts)})
    r=run(b)
    assert not r.quality.trusted_for_current_use and r.mid.value is None
    b=book().model_copy(update={'timestamp':NOW-timedelta(seconds=1)})
    assert run(b).mid.reason == 'SNAPSHOT_SOURCE_TIMESTAMP_MISMATCH'


@pytest.mark.parametrize('b,reason', [
    (book(bids=(("102","1"),)), 'CROSSED_OR_LOCKED_BOOK'),
    (book(bids=(("103","1"),)), 'CROSSED_OR_LOCKED_BOOK'),
    (book(bids=(("100","1"),("100","2"))), 'DUPLICATE_PRICE_LEVEL'),
    (book(asks=(("102","0"),)), 'NONPOSITIVE_LEVEL_SIZE'),
    (book(bids=(("1e1001","1"),)), 'NUMERIC_RANGE_UNSUPPORTED')])
def test_analytically_invalid_book_is_not_trusted(b,reason):
    r=run(b)
    assert r.mid.reason == reason and r.best_bid.value is None
    assert r.quality.state is DataQualityState.UNAVAILABLE
    assert not r.quality.trusted_for_current_use
    assert r.provenance == b.provenance


@pytest.mark.parametrize('field,value',[('price','0'),('price','-1'),('quantity','-1'),
    ('price','NaN'),('price','Infinity'),('quantity','Infinity')])
def test_canonical_invalid_numeric_rejected(field,value):
    facts={'price':D(100),'quantity':D(1),field:D(value)}
    with pytest.raises(ValidationError):OrderBookLevel(**facts)


def test_bypassed_model_validation_and_wrong_coverage_fail_closed():
    bad = OrderBookLevel.model_construct(price=D('-1'),quantity=D(1))
    with pytest.raises(ValidationError):run(book().model_copy(update={'bids':(bad,)}))
    with pytest.raises(ValueError):run(coverage=CapabilityCoverage(Capability.TRADES,CapabilityAvailability.SUPPORTED))
    with pytest.raises(ValueError):run(evaluation_time=NOW-timedelta(seconds=1))
    with pytest.raises(ValidationError):OrderBookSnapshot(symbol='BTC',timestamp=NOW,provenance=book().provenance,bids=(None,))


@pytest.mark.parametrize('bands',[(),('0',),('-1',),('10000',),('2','1'),('1','1'),('NaN',),('Infinity',)])
def test_invalid_configuration(bands):
    with pytest.raises((ValueError,ValidationError)):config(bands=bands)


@pytest.mark.parametrize('size',['0','-1','NaN','Infinity','1e1001'])
def test_invalid_order_size(size):
    with pytest.raises((ValueError,ValidationError)):config(orders=(("BUY",size),))


def test_thin_extreme_and_deep_books():
    r=run(book(bids=(("1e-999","1e-999"),),asks=(("2e-999","1e-999"),)),config(orders=(("BUY","2e-999"),)))
    assert r.mid.value == D('1.5e-999')
    assert r.executions[0].reason == 'INSUFFICIENT_DISPLAYED_DEPTH'
    r=run(book(bids=(("1e999","1e999"),),asks=(("2e999","1e999"),)),config(orders=(("BUY","1e999"),)))
    assert r.executions[0].displayed_quote.value == D('2e1998')
    bids=tuple((str(10000-i), '1') for i in range(5000))
    r=run(book(bids=bids,asks=(("10001","1"),)),config(bands=('5000',),orders=(("SELL","5000"),)))
    assert r.bands[0].bid_base.value == 5000 and r.executions[0].complete


def test_determinism_context_and_input_permutation():
    expected=run().model_dump_json()
    with localcontext() as ctx:
        ctx.prec=6;ctx.rounding=ROUND_UP
        assert run().model_dump_json() == expected
    b=book();b=b.model_copy(update={'bids':tuple(reversed(b.bids)),'asks':tuple(reversed(b.asks))})
    assert run(b).model_dump_json() == expected


def test_generated_invariants_and_independent_fraction_reference():
    rng=random.Random(7)
    for _ in range(100):
        sizes=[rng.randint(1,20) for _ in range(4)]
        asks=tuple((str(102+i),str(q)) for i,q in enumerate(sizes))
        qty=rng.randint(1,sum(sizes))
        r=run(book(asks=asks),config(bands=('1','100','300'),orders=(("BUY",str(qty)),)))
        e=r.executions[0]; remaining=qty; cost=0
        for i,q in enumerate(sizes):
            take=min(q,remaining);cost+=take*(102+i);remaining-=take
        with localcontext() as ctx:
            ctx.prec=50
            f=Fraction(cost,qty)
            assert e.partial_vwap.value == D(f.numerator)/D(f.denominator)
        assert e.displayed_quote.value == cost and e.complete
        assert all(-1 <= b.imbalance.value <= 1 for b in r.bands)
        assert all(0 < b.ask_concentration_hhi.value <= 1 for b in r.bands)
        assert [b.ask_base.value for b in r.bands] == sorted(b.ask_base.value for b in r.bands)


def test_metric_unavailable_contract():
    with pytest.raises(ValidationError):Metric(value=None,unit='BTC')
    with pytest.raises(ValidationError):Metric(value=D(1),unit='BTC',reason='missing')


def test_extreme_dynamic_range_does_not_round_partial_into_complete():
    b=book(bids=(("1", "1"),),asks=(("2","1"),("3","1e-1000")))
    r=run(b,config(orders=(("BUY","1.0000000000000000000000000000000000000000000000001"),)))
    assert not r.executions[0].complete
    assert r.executions[0].reason == 'INSUFFICIENT_DISPLAYED_DEPTH'


def test_tiny_adverse_slippage_is_not_lost_to_vwap_cancellation():
    b=book(asks=(("102","1"),("103","1e-1000")))
    r=run(b,config(orders=(("BUY","2"),)))
    assert not r.executions[0].complete
    b=book(asks=(("102","1e1000"),("103","1")))
    # All displayed quantity requested with 50-digit input: 1e1000 cannot
    # represent +1, so consuming it is correctly zero slippage at top level.
    r=run(b,config(orders=(("BUY","1e1000"),)))
    assert r.executions[0].complete and r.executions[0].full_size_slippage_absolute.value == 0


def test_numeric_precision_limit_and_level_limit():
    b=book(bids=(("100.1234567890123456789012345678901234567890123456789","1"),))
    assert run(b).mid.reason == 'NUMERIC_RANGE_UNSUPPORTED'
    level=OrderBookLevel(price=D(100),quantity=D(1))
    b=book().model_copy(update={'bids':(level,)*100001})
    assert run(b).mid.reason == 'BOOK_LEVEL_LIMIT_EXCEEDED'


def test_generated_malformed_sizes_fail_without_fallback():
    rng=random.Random(11)
    for _ in range(50):
        size=str(-rng.randint(1,1000000))
        with pytest.raises(ValidationError):OrderBookLevel(price=D(100),quantity=D(size))


def test_canonical_instrument_match_and_mismatch():
    assert run().config.symbol == run().symbol == 'BTC'
    with pytest.raises(ValueError,match='INSTRUMENT_IDENTITY_MISMATCH'):
        run(c=config().model_copy(update={'symbol':'ETH','base_asset':'ETH','quote_currency':'EUR'}))
    # Canonical symbols are trimmed nonempty strings, not provider parsers.
    assert run(c=LiquidityConfig(**{**config().model_dump(),'symbol':' BTC '})).symbol == 'BTC'
    with pytest.raises(ValueError,match='INSTRUMENT_IDENTITY_MISMATCH'):
        run(c=config().model_copy(update={'symbol':'btc'}))


@pytest.mark.parametrize('value',[None,'','   ',123])
def test_invalid_instrument_identity(value):
    with pytest.raises((ValueError,TypeError)):
        LiquidityConfig(**{**config().model_dump(),'symbol':value})


def test_missing_instrument_identity_and_construct_bypass():
    facts=config().model_dump();del facts['symbol']
    with pytest.raises(ValidationError):LiquidityConfig(**facts)
    constructed={**config().__dict__};del constructed['symbol']
    with pytest.raises(ValidationError):run(c=LiquidityConfig.model_construct(**constructed))


def test_matching_symbol_never_verifies_caller_unit_assertions():
    r=run(c=config().model_copy(update={'base_asset':'ETH','quote_currency':'EUR'}))
    # Equality proves only the instrument identifier. There is no canonical
    # quote/base mapping to authenticate these declarations; never infer one.
    assert r.symbol == 'BTC' and r.mid.unit == 'EUR/ETH'
    assert r.quality.trusted_for_current_use  # C05 facts remain unchanged.
    assert r.units_provider_verified is False
    assert 'UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED' in r.limitations
    assert r.quality == run().quality and r.provenance == run().provenance


def test_unit_disclosure_cannot_claim_provider_verification():
    from traid.liquidity import LiquidityReport
    facts=run().model_dump()
    with pytest.raises(ValidationError):LiquidityReport(**{**facts,'units_provider_verified':True})
    with pytest.raises(ValidationError):LiquidityReport(**{**facts,'limitations':()})
    with pytest.raises(ValidationError):LiquidityConfig(**{**config().model_dump(),'units_provider_verified':True})


@pytest.mark.parametrize('age',[0,6,16])
def test_unit_disclosure_and_reference_survive_quality_states(age):
    r=run(book(age=age))
    assert r.units_provider_verified is False
    assert 'UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED' in r.limitations
    assert (r.executions[0].reference_price.value is not None) == (age==0)
    assert run(book(age=age)).model_dump_json() == r.model_dump_json()


def test_execution_reference_prices_and_unavailable_behavior():
    r=run()
    assert r.executions[0].reference_price == r.best_ask
    assert r.executions[1].reference_price == r.best_bid
    assert r.executions[2].reference_price == r.best_ask  # Partial depth keeps benchmark.
    assert r.executions[0].reference_price.unit == 'USD/BTC'
    r=run(book(asks=()))
    assert r.executions[0].reference_price.value is None
    assert r.executions[0].reference_price.reason == 'SIDE_UNAVAILABLE'
    r=run(book(bids=(("102","1"),)))
    assert r.executions[0].reference_price.value is None
    assert r.executions[0].reference_price.reason == 'CROSSED_OR_LOCKED_BOOK'


def test_band_count_boundaries():
    from traid.liquidity.analytics import MAX_BANDS
    assert len(run(c=config(bands=tuple(str(i+1) for i in range(MAX_BANDS)))).bands)==MAX_BANDS
    with pytest.raises(ValidationError):config(bands=tuple(str(i+1) for i in range(MAX_BANDS+1)))


def test_order_count_boundaries_and_bypass():
    from traid.liquidity.analytics import MAX_ORDERS
    orders=tuple(('BUY','1') for _ in range(MAX_ORDERS))
    assert len(run(c=config(orders=orders)).executions)==MAX_ORDERS
    assert run(c=config(orders=())).executions==()
    with pytest.raises(ValidationError):config(orders=orders+(('BUY','1'),))
    c=config().model_copy(update={'orders':tuple(OrderRequest(side='BUY',quantity=D(1)) for _ in range(MAX_ORDERS+1))})
    with pytest.raises(ValidationError):run(c=c)
