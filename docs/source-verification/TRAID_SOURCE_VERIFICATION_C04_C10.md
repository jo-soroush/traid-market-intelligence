# TRAID SOURCE VERIFICATION — C04 TO C10

**Date:** 2026-09-03  
**Scope:** Function-level source verification for the first high-value external source block  
**Primary repo:** `lewbei/hyperliquid-analytics-dashboard`  
**Repository license:** Apache-2.0  
**Runtime status:** NOT VERIFIED  
**Decision style:** ADAPT selectively, never import the repository as TraID's base

---

# 1. Executive Decision

Project 04 remains highly valuable for TraID, but the function-level review changes several earlier assumptions.

## Strongest areas to ADAPT

- Hyperliquid message parsing and transport separation
- order-book depth and imbalance formulas
- book-walking slippage calculation
- trade-flow aggregation
- OI change/velocity
- market-context calculations
- simple momentum/context helpers
- deterministic regime composition as a starting pattern

## Areas that TraID must NOT trust directly

- production reconnect/resilience
- funding annualization as currently implemented
- liquidation detection as real liquidation truth
- arbitrary crowding/regime thresholds
- default fee assumptions
- current session/VWAP conventions without redefinition
- heuristic interpretations presented as financial truth

The correct TraID approach is therefore:

```text
TAKE THE CALCULATION PATTERNS
↓
REWRITE AGAINST CANONICAL TRAID MODELS
↓
VERIFY AGAINST OFFICIAL HYPERLIQUID SEMANTICS
↓
ADD DATA QUALITY
↓
ADD DETERMINISTIC TEST FIXTURES
↓
VERSION ALL THRESHOLDS
```

---

# 2. C04 — Hyperliquid Adapter

## Source files verified

```text
backend/hyperliquid_client.py
backend/transport_hyperliquid_sdk.py
backend/candle_fetcher.py
backend/candle_aggregator.py
backend/models.py
backend/config.py
```

## High-value source architecture

`hyperliquid_client.py` separates:

```text
Transport
↓
Raw Hyperliquid messages
↓
HyperliquidMessageParser
↓
Normalized event objects
```

Important public types/classes verified:

```text
HyperliquidTransport
HyperliquidMessageParser
HyperliquidClient
```

`HyperliquidMessageParser.parse_message()` dispatches channels including:

```text
l2Book
bbo
trades
candle
activeAssetCtx
```

This separation is strongly aligned with TraID's provider-adapter design.

## Critical limitation discovered

The source itself explicitly states that production-grade reconnect/backoff/clean-shutdown semantics are not fully implemented in the interface and are left for later work.

Therefore:

### ADAPT

- parser/transport separation
- testable pure normalization
- channel dispatch pattern
- provider isolation

### BUILD IN TRAID

- reconnect state machine
- exponential backoff
- jitter
- resubscription
- gap detection
- reconnect health state
- deterministic shutdown
- retry budget
- REST fallback where semantically valid
- provenance
- connection metrics

## Final C04 decision

```text
Parser architecture: ADAPT STRONG
Transport abstraction: ADAPT STRONG
Production connection resilience: BUILD
Whole client: DO NOT REUSE AS-IS
```

---

# 3. C05 — Data Quality & Provenance

Project 04 exposes useful health/freshness concepts but not the complete contract required by TraID.

README-verified freshness examples include:

```text
orderbook < 5s
trades < 60s
market data < 120s
```

These are useful examples, not final TraID truth.

TraID must own:

```text
LIVE
DELAYED
STALE
UNAVAILABLE
```

and retain:

```text
source_timestamp
received_timestamp
age
validation_status
gap_status
recovery_status
provider
exchange
provenance_id
```

## Important design correction

Freshness thresholds should be **per data type and versioned**, not copied globally from Project 04.

For example, order-book freshness requirements are fundamentally different from macro-event freshness.

## Final C05 decision

```text
Health/status concept: ADAPT
Freshness contract: BUILD
Gap handling: BUILD
Provenance: BUILD
Threshold values: CALIBRATE / VERSION
```

---

# 4. C07 — Order Book & Liquidity Analytics

## Source files verified

```text
backend/orderbook_metrics.py
backend/depth_decay.py
backend/slippage_estimator.py
```

## Verified useful formulas

### Mid price

```text
(best_bid + best_ask) / 2
```

### Absolute spread

```text
best_ask - best_bid
```

### Spread in basis points

```text
(spread / mid) * 10000
```

### Cumulative depth

Sum of:

```text
price * size
```

over top N levels.

### Imbalance

```text
(bid_depth - ask_depth) / (bid_depth + ask_depth)
```

This yields a normalized value in approximately:

```text
[-1, +1]
```

These are straightforward deterministic calculations and are good adaptation candidates.

---

# 5. C07 — Slippage

## Source file

```text
backend/slippage_estimator.py
```

Verified public class/functions:

```text
SlippageEstimator
estimate_buy()
estimate_sell()
estimate_for_sizes()
```

## Useful method

The estimator walks order-book levels and calculates:

- amount filled
- average fill price / VWAP
- slippage from best bid/ask
- feasibility
- liquidity utilization
- fee contribution
- estimated round-trip cost

### Buy slippage

Conceptually:

```text
(avg_fill_price - best_ask) / best_ask * 10000
```

Sell side mirrors this appropriately.

## Problems requiring changes

### Hard-coded fee

Default:

```text
2.8 bps
```

must not be treated as universal/current truth.

TraID should obtain or configure fees explicitly and version the configuration.

### 99% feasibility rule

The source treats a fill reaching approximately 99% of target size as feasible.

That is a product heuristic, not a financial invariant.

TraID should define explicit policy.

### Round-trip cost simplification

The current formula combines:

```text
spread + slippage + 2 * fee
```

This is useful as a screening approximation but not necessarily a precise future exit-cost model.

## Final decision

```text
Book walking: ADAPT STRONG
VWAP calculation: ADAPT STRONG
Slippage bps: ADAPT STRONG
Fee default: REJECT
99% feasibility threshold: REJECT AS DEFAULT
Risk use: BUILD TraID policy
```

---

# 6. C08 — Trade Flow

## Source file verified

```text
backend/trade_flow_tracker.py
```

Verified classes/functions include:

```text
Trade
TradeBucket
TradeFlowTracker
add_trade()
get_stats()
get_multi_timeframe_stats()
get_bucket_distribution()
```

## Useful concepts

- rolling in-memory windows
- aggressive buy/sell notional
- buy ratio
- sell ratio
- trade-size buckets
- 30s / 5m / 15m views
- cleanup by timestamp

Default buckets include ranges such as:

```text
0-1k
1k-5k
5k-10k
10k-50k
50k-250k
250k+
```

These bucket thresholds should be configurable and calibrated for BTC/liquidity regime.

## Important weakness

The repository's "sweep" helper is essentially a dominance heuristic:

```text
buy_ratio >= 0.65 → up
sell_ratio >= 0.65 → down
minimum 3 trades
```

This is not a true order-book sweep detector.

## Final C08 decision

```text
Rolling trade aggregation: ADAPT STRONG
Buy/sell notional: ADAPT
Trade buckets: ADAPT with configuration
65% sweep heuristic: REFERENCE ONLY
True sweep detection: BUILD BETTER if needed
```

## CVD

TraID should implement CVD explicitly from canonical aggressor-side trades, with defined rules for:

- duplicate events
- out-of-order events
- replay
- restart
- missing sequence
- timestamp window

Do not let wall-clock cleanup determine historical replay behavior.

---

# 7. C09 — OI / Funding / Basis

## Source file verified

```text
backend/market_indicators.py
```

Verified functions include:

```text
add_context()
get_oi_stats()
get_funding_stats()
get_basis_stats()
get_multi_timeframe_oi()
get_historical_values()
get_summary()
```

## Open Interest

Useful method:

```text
change_percent =
(current_oi - start_oi) / start_oi * 100
```

Velocity:

```text
change_percent / elapsed_minutes
```

This is useful and easy to test.

## Critical funding issue

The source comments/logic annualize funding using an assumption equivalent to:

```text
3 funding periods per day
```

based on an 8-hour funding period.

Hyperliquid's official documentation states that funding payments occur **every hour**.

Therefore, TraID must not reuse the source annualization formula unchanged.

### TraID action

Before implementing annualized funding:

1. define exactly which Hyperliquid field is being received;
2. determine whether it represents the hourly paid rate or an 8-hour formula representation;
3. normalize into a clearly named TraID field;
4. test against official examples;
5. avoid ambiguous naming such as simply `annualized_rate`.

## Basis

The source's basis status:

```text
Premium
Discount
Normal
```

is useful as a presentation pattern.

But TraID must explicitly document which prices form the basis calculation:

```text
mark?
mid?
oracle?
spot?
```

Hyperliquid uses oracle and mark prices for different purposes, so this cannot remain ambiguous.

## Final C09 decision

```text
OI change: ADAPT STRONG
OI velocity: ADAPT
Funding ingestion: ADAPT only after semantic verification
Funding annualization: REJECT CURRENT FORMULA
Basis calculation: REWRITE with explicit price semantics
Human-readable interpretation: REFERENCE ONLY
```

---

# 8. C09 — Volatility

## Source file verified

```text
backend/volatility.py
```

Verified:

```text
VolatilityTracker
calculate_metrics()
_detect_regime()
```

## Useful idea

Volatility regime uses historical ATR percentile.

Default thresholds:

```text
<= 33rd percentile → low
>= 67th percentile → high
otherwise normal
```

Uses a rolling history of approximately 100 values by default.

## Weakness

When fewer than 10 values exist, it returns:

```text
normal, 50th percentile
```

That hides insufficient warm-up.

TraID should instead represent:

```text
UNKNOWN / INSUFFICIENT_HISTORY
```

or maintain a separate quality state.

## Final decision

```text
Percentile regime idea: ADAPT
33/67 defaults: EVALUATE
Warm-up → normal: REJECT
Warm-up quality state: BUILD
```

---

# 9. C09 — Session / VWAP

## Source file verified

```text
backend/session_context.py
```

Verified methods:

```text
reset_session()
add_trade()
update_price()
_calculate_vwap()
_calculate_volume_for_window()
get_context()
```

## Important issue to verify during implementation

The method stores `size_usd` and computes:

```text
total_notional += price * size_usd
total_volume += size_usd
VWAP = total_notional / total_volume
```

If `size_usd` truly means USD notional rather than base quantity, this weighting convention requires careful validation because multiplying price by USD notional is not the standard base-volume VWAP formulation.

Therefore TraID should **not copy this VWAP implementation until unit semantics are verified**.

## Final decision

```text
Session-state concept: ADAPT
High/low context: ADAPT
VWAP idea: ADAPT
Current VWAP implementation: VERIFY UNITS BEFORE USE
Session reset semantics: BUILD explicitly
```

---

# 10. C09 — Momentum

## Source file verified

```text
backend/price_momentum.py
```

Verified:

```text
add_price()
get_momentum()
get_short_momentum()
get_long_momentum()
get_all_momentum()
detect_trend_alignment()
```

Useful feature:

The source marks a momentum window usable only when approximately at least half of the requested time window is covered.

This is a good idea because it distinguishes "a value exists" from "there is enough history."

TraID should generalize this through Data Quality rather than embed a magical 50% threshold in each indicator.

## Final decision

```text
Momentum calculation: ADAPT
Coverage awareness: ADAPT STRONG
50% threshold: VERSION / EVALUATE
Data-quality integration: BUILD
```

---

# 11. C10 — Regime Detector

## Source file verified

```text
backend/regime_detector.py
```

Verified methods:

```text
detect_trend_regime()
detect_liquidity_regime()
detect_market_regime()
detect_all()
```

## Trend method

Uses multi-timeframe returns, directional agreement, average return, and magnitude/alignment.

The source has configurable thresholds such as approximately:

```text
trend threshold: 0.1%
strong trend: 0.5%
range threshold: 0.05%
```

These values are heuristics and should not be copied as universal thresholds.

## Liquidity regime

Combines:

```text
spread_bps
L5 bid depth
L5 ask depth
```

to produce:

```text
high
normal
thin
```

This is a useful deterministic design pattern.

## Overall market regime

The source combines:

- trend
- volatility
- buy ratio
- liquidation counts
- optional funding
- optional OI velocity

and returns states including:

```text
normal
trend
chop
liquidation_event
short_squeeze
crash
```

This is useful structurally but depends strongly on downstream heuristics.

## Final decision

```text
Regime composition architecture: ADAPT
Return-alignment approach: ADAPT
Liquidity regime pattern: ADAPT
Threshold values: DO NOT COPY
"crash"/"squeeze" labels: REQUIRE STRONGER EVIDENCE
Outcome-driven calibration: BUILD
```

---

# 12. C10 — Crowding

## Source file verified

```text
backend/crowding_detector.py
```

Verified:

```text
CrowdingDetector
detect()
_generate_interpretation()
```

Inputs include:

```text
OI trend
OI velocity
funding
funding trend
basis
basis status
```

It builds long and short crowding scores.

## Good part

The input dimensions are sensible for a crowding heuristic.

## Weak part

The thresholds and score weights are hand-configured heuristics.

They should not be interpreted as probability.

## TraID decision

```text
Input dimensions: ADAPT
Score architecture: REFERENCE / ADAPT cautiously
Thresholds: BUILD/CALIBRATE
Interpretation strings: REFERENCE ONLY
Trade authority: REJECT
```

---

# 13. C10 — Liquidations

## Source file verified

```text
backend/liquidations.py
```

This is one of the most important corrections from the source review.

The module explicitly describes its events as:

```text
SuspectedLiquidation
```

and states the mechanism is estimation-based rather than definitive liquidation data.

### Heuristic 1

A single trade over a configurable threshold, default approximately:

```text
$10,000
```

may be classified as a suspected liquidation.

### Heuristic 2

A same-direction cascade such as:

```text
5+ trades
within ~5 seconds
with enough total volume
```

may be classified as a suspected liquidation.

This is **not authoritative liquidation data**.

A $10k aggressive sell can be many things other than a forced long liquidation.

## TraID decision

Do not name these events:

```text
LiquidationEvent
```

unless the upstream source proves they are real liquidation events.

If TraID uses this heuristic, name it something like:

```text
ForcedFlowCandidate
LiquidationPressureHeuristic
SuspectedLiquidation
```

and preserve confidence/method provenance.

For actual liquidation intelligence, prefer direct authoritative/verified event sources if Hyperliquid exposes the required semantics.

## Final decision

```text
Current detector as real liquidation feed: REJECT
Cascade/large-flow heuristic: REFERENCE ONLY / optional ADAPT
Explicit uncertainty: ADOPT
Actual liquidation source: VERIFY/BUILD
```

---

# 14. Revised C04-C10 Source Map

| Card | Component | Source | Final decision after function review |
|---|---|---|---|
| C04 | parser/normalization | `hyperliquid_client.py` | ADAPT STRONG |
| C04 | transport | `transport_hyperliquid_sdk.py` | ADAPT interface/pattern |
| C04 | reconnect/backoff | source incomplete | BUILD |
| C05 | freshness/health | Project 04 patterns | ADAPT concept + BUILD contract |
| C07 | depth/imbalance | `orderbook_metrics.py` | ADAPT STRONG |
| C07 | slippage book-walk | `slippage_estimator.py` | ADAPT STRONG with policy rewrite |
| C08 | trade aggregation | `trade_flow_tracker.py` | ADAPT STRONG |
| C08 | sweep signal | ratio heuristic | REFERENCE ONLY |
| C09 | OI | `market_indicators.py` | ADAPT STRONG |
| C09 | funding annualization | `market_indicators.py` | REJECT current formula |
| C09 | basis | `market_indicators.py` | REWRITE semantics |
| C09 | volatility regime | `volatility.py` | ADAPT, fix warm-up |
| C09 | VWAP/session | `session_context.py` | VERIFY UNITS before adapt |
| C09 | momentum | `price_momentum.py` | ADAPT |
| C10 | regime structure | `regime_detector.py` | ADAPT |
| C10 | thresholds | `regime_detector.py` | CALIBRATE, do not copy |
| C10 | crowding | `crowding_detector.py` | ADAPT methodology |
| C10 | liquidation truth | `liquidations.py` | REJECT as authoritative |
| C10 | liquidation pressure heuristic | `liquidations.py` | optional REFERENCE/ADAPT |

---

# 15. Consequence for TraID

After function-level review, Project 04 is still a strong source, but its role is now clearer:

```text
PROJECT 04 IS A CALCULATION / ARCHITECTURE REFERENCE
NOT A PRODUCTION DATA ENGINE TO COPY WHOLESALE
```

The strongest reusable value lies in simple deterministic formulas and separation of concerns.

The weakest areas are where the project moves from measurement into heuristic interpretation.

TraID should therefore preserve this boundary:

```text
MEASUREMENTS
    → reuse/adapt aggressively when correct

HEURISTIC LABELS
    → calibrate/version

FINANCIAL TRUTH
    → verify against official source

RISK AUTHORITY
    → TraID-owned deterministic logic
```

---

# 16. Next Verification Block

Next source-level block should cover:

```text
CryptoRadar:
SignalEngine.java
MarketRegimeService.java
OutcomeEvaluator.java
OutcomeTracker.java
detectors/

Hyperliquid Backtester:
backtester.py
strategy.py
sync.py
metrics.py
tests/
```

This will resolve the strongest sources for:

```text
C15 Signal Fusion
C16 detector architecture
C18 Backtest
C19 Outcome Tracking
```
