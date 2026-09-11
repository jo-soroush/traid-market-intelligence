# CryptoRadar → TraID Engineering Reconnaissance

**Source repository:** `artyomsv/crypto-radar`  
**License observed:** MIT  
**TraID decision:** `REFERENCE ONLY + selective ADAPT / VERIFY`  
**Primary relevance:** Outcome tracking, detector architecture, versioned configuration, deployment markers, signal-vs-execution separation, empirical evaluation

## 1. Executive Summary

CryptoRadar contains a broad deterministic signal pipeline with six dimensions:

```text
Technical
Whale
Derivatives
Sentiment
Order Book
Macro
```

It also includes market regime logic, detector abstractions, outcome tracking, execution gates, backtesting, configuration versioning, deployment markers, and a substantial operational stack.

The key finding is that its strongest reusable engineering is **not the signal-scoring formulas**. Several scoring rules are heuristic, and some show semantic mismatches. Its strongest reusable ideas are instead:

- immutable/versioned configuration
- signal/dimension snapshots
- pure detector boundaries
- strategy-specific outcome identity
- MFE/MAE and time-to-extreme
- realized R and fee accounting
- explicit exit/trail state
- deployment markers
- performance slicing
- separation between signal labels and execution gates

TraID should adapt these patterns selectively while keeping its own architecture and mandatory deterministic Risk Gate.

## 2. Architecture at a Glance

Observed stack:

```text
React / Vite frontend
        ↓
Quarkus API Gateway
        ↓
Market Data
News
Analytics
Whale
Derivatives
Signal
Trade Execution
        ↓
TimescaleDB / PostgreSQL / Redis
```

The architecture shows useful boundary ideas, but TraID should not reproduce the full microservice topology without measurable need.

**Lesson:** adapt boundaries, not service count.

## 3. Signal Engine

The main signal engine builds six `DimensionScore` values and computes:

```text
overallScore = Σ(dimension.score × dimension.weight)
```

clamped to:

```text
[-100, +100]
```

This is deterministic and explainable, but explainability alone does not validate financial semantics.

## 4. Alignment

CryptoRadar explicitly distinguishes alignment from the old name `confidence`.

Alignment measures weighted directional agreement among dimensions and penalizes strong contradictions.

Inputs include:

- `minScoreForNonZero`
- `contradictionScoreThreshold`
- `contradictionPenaltyMultiplier`
- `oneContradictionPenalty`
- `twoContradictionPenalty`
- `outputScale`
- `minOutput`
- `maxOutput`

### TraID invariant

```text
Alignment != Confidence
Alignment != Probability
Alignment != Expected Return
Alignment != Risk Approval
Alignment != Trade Approval
```

## 5. Empirical Alignment Finding

A repository knowledge-base document reports a 14-day sample:

```text
25–50    n=49    total -3.23R
50–70    n=217   total +35.39R
70–85    n=8     total +0.06R
85+      n=0
```

The repo hypothesizes that very high alignment can occur after a move is already mature/crowded.

Correct interpretation:

- this is an association
- it is not causal proof
- the high-alignment sample is very small

The useful lesson is:

> Internal agreement must be evaluated empirically and must never be marketed as calibrated confidence.

## 6. Technical Dimension

Technical scoring combines:

```text
RSI
MACD
SMA200
Support/Resistance
Bollinger Bands
Volume Confirmation
```

### RSI

Configured threshold buckets for oversold/overbought.

**Decision:** VERIFY.

### MACD

Primarily uses the sign of the histogram. Magnitude is not meaningfully represented in the inspected logic.

**Decision:** VERIFY.

### SMA200

The implementation compares SMA200 with:

```text
(support + resistance) / 2
```

instead of directly using current price.

**Decision:** REJECT current implementation.

### Support/Resistance

The scorer uses `analytics.overallScore` as a normalized position input rather than calculating current-price position from support/resistance levels.

**Decision:** REJECT current implementation.

### Bollinger

The inspected formula uses:

```text
(bbMiddle - bbLower) / (bbUpper - bbLower)
```

and does not use current price, even though the reason text says price is near a band.

**Decision:** REJECT current implementation.

### Volume Confirmation

Increasing/decreasing volume is used as a coarse conviction heuristic.

**Decision:** VERIFY.

## 7. Whale Intelligence

### What `whalePressure` actually is

The repository computes one-hour large-trade flow imbalance:

```text
(buyVolumeUsd1h - sellVolumeUsd1h)
--------------------------------- × 100
(buyVolumeUsd1h + sellVolumeUsd1h)
```

clamped to `[-100,+100]`.

Identified source:

```text
services/whale-service/src/main/java/com/cryptoradar/whale/service/WhaleAnalyticsService.java
→ computeDerivedMetrics
```

This is not automatically Smart Money intelligence.

### TraID naming rule

Prefer:

```text
LargeTradeFlowImbalance
```

not:

```text
SmartMoneyConfidence
```

unless wallet/entity performance evidence exists.

## 8. Whale Sample Dampening

`scoreWhale` reduces the score when `tradeCount1h` is below a configured minimum:

```text
dampening = tradeCount / minSampleSize
adjustedScore = score × dampening
```

High activity can amplify the score.

Good idea: weak evidence is made weaker.

Caveat: transaction count is not independent sample count. Multiple prints may belong to one participant or execution sequence.

**Decision:** VERIFY / ADAPT concept.

## 9. Whale Flow Is Not Smart Money

TraID must keep these separate:

```text
Large trade
≠ Whale identity
≠ Profitable wallet
≠ Smart money
≠ Directional truth
```

Recommended conceptual layers:

```text
Large Trade Flow
Wallet / Entity
Position Lifecycle
Historical Wallet Performance
Smart-Money Evidence
Aggregate Whale Bias
```

## 10. Derivatives

CryptoRadar includes deterministic rules around derivatives context such as funding, positioning, OI-related context, and crowding/liquidation evidence.

**Decision:** VERIFY.

Before adaptation, TraID must verify:

- funding sign
- funding interval
- OI units
- source definitions
- lag
- long/short ratio meaning
- liquidation semantics

Unknown financially material semantics must remain `UNKNOWN`.

## 11. Order Book Finding

A major semantic issue is that the signal dimension named `"Order Book"` is not cleanly equivalent to actual resting bid/ask depth analytics. The repository has order-book functionality elsewhere, while the signal dimension was reported as using liquidation/OI-related inputs.

**Decision:** REJECT current naming/coupling.

TraID must keep distinct:

```text
Order Book = resting bids/asks/depth/spread
Trade Flow = executed aggressor trades
Liquidation Flow = liquidation events/estimates
Derivatives Positioning = OI/funding/crowding
```

## 12. Market Regime

The repo uses simple BTC regime states:

```text
BULL
BEAR
CHOP
UNKNOWN
```

Tests reportedly cover rising, falling, flat, and insufficient-history synthetic data.

The regime mainly changes signal-label thresholds rather than rewriting dimension scores, weights, detector rules, or trade levels.

Decision:

```text
simple regime service     ADAPT concept
exact parameters          VERIFY
regime as market truth    REJECT
```

TraID should keep `UNKNOWN` when evidence is insufficient.

## 13. Detector Architecture

A detector interface exposes concepts equivalent to:

```text
name()
detect(MarketContext)
```

The engine can discover and run detector implementations independently.

Strong qualities:

- separate detector classes
- shared context
- independent strategy identity
- independent outcome aggregation
- detector-specific trade levels
- detector-specific trail config
- isolated detector failures

Weak qualities:

- untyped `Map<String,Object>`
- string-based dimension names
- detector-specific alignment differs from engine alignment
- no complete detector replay framework

**Decision:** ADAPT architecture pattern.

TraID version:

```text
Typed MarketContext
        ↓
StrategyDetector
        ↓
StrategyCandidate
        ↓
Deterministic Risk Gate
        ↓
Decision Support
```

A detector can propose. It cannot approve.

## 14. Trend Continuation Detector

Reported inputs include current price, SMA20/50/200, ATR14, RSI14, support/resistance, and Technical/Derivatives/Whale dimension scores.

Direction includes:

```text
LONG  if sma50 > sma200 and price > sma50
SHORT if sma50 < sma200 and price < sma50
```

with pullback, RSI, and opposition filters.

**Decision:** REFERENCE exact rules, ADAPT detector pattern.

A dedicated full detector test was reportedly missing, so exact strategy logic should not be copied.

## 15. Liquidity Sweep Detector

The detector uses swing-level pierce/reclaim structure, ATR, wick/body relationships, volume confirmation, drift limits, and derivatives opposition. It has dedicated boundary tests.

**Decision:** VERIFY strategy logic / ADAPT testable-detector pattern.

Thresholds must be independently evaluated.

## 16. Outcome Tracking

This is CryptoRadar's strongest area for TraID.

Persisted outcome information reportedly includes:

- signal identity
- strategy
- direction
- entry
- stop
- target
- risk/reward
- dimension snapshots
- status
- realized PnL
- realized R
- MFE
- MAE
- trail state
- fees
- timestamps
- final exit reason

The system asks not only "what signal did we create?" but:

> What happened afterward?

**Decision:** ADAPT strongly.

## 17. Strategy-Specific Outcome Identity

Pending outcomes are deduplicated using symbol, direction, strategy, and pending status.

This lets different strategies retain independent outcomes for the same market direction.

**Decision:** ADAPT.

TraID must preserve detector/strategy attribution.

## 18. MFE / MAE

For LONG, conceptually:

```text
MFE = (bar.high - entry) / entry × 100
MAE = (bar.low  - entry) / entry × 100
```

and direction reverses for SHORT.

The repo also tracks:

```text
timeToMFE
timeToMAE
```

**Decision:** ADAPT.

TraID improvement: store source resolution and exact event timestamps because candle extremes do not reveal intrabar path.

## 19. Realized R

Conceptually:

```text
grossR = signed(exit-entry) / abs(entry-initialStop)
feesInR = feesPct / riskPct
netR = grossR - feesInR
```

**Decision:** ADAPT.

TraID should store:

```text
gross_r
fee_r
slippage_r
funding_r
other_cost_r
net_r
```

## 20. Exit Reasons

Reported statuses:

```text
PENDING
HIT_TARGET
HIT_STOP
EXPIRED
```

Reported reasons:

```text
TARGET
INITIAL_STOP
TRAIL_STOP
EXPIRED
STAGNATION
```

A semantic mismatch exists because `STAGNATION` may be represented under `HIT_STOP`.

**Decision:** ADAPT concept but improve typing.

TraID should use a typed terminal reason that cannot conflict with status.

## 21. Trailing Stop

Shared R-based trail configuration includes concepts such as:

```text
activationR
stepR
offsetR
widerOffsetActivationR
widerOffsetR
```

**Decision:** ADAPT framework concept / VERIFY exact parameters.

## 22. Same-Bar Ambiguity

CryptoRadar reportedly uses:

```text
trail inactive → stop wins
trail active   → target wins
```

when both target and stop occur in one OHLC bar.

The repo acknowledges OHLC cannot reveal actual ordering.

**Decision:** REJECT optimistic branch.

TraID rule remains:

```text
unresolved same-bar ambiguity → STOP FIRST
```

unless higher-resolution evidence proves sequence.

## 23. Backtesting

CryptoRadar Tier-1 backtesting loads stored completed outcomes and re-scores them instead of reconstructing the full historical decision path.

Reported flow:

```text
stored SignalOutcome
→ rebuild dimensions
→ recompute score
→ recompute alignment
→ recompute label
→ apply floor
→ optional trail simulation
→ aggregate realized R
```

`BacktestScorer` duplicates logic from live `SignalEngine`, creating divergence risk. Historical regime is also not fully reproduced.

**Decision:** REJECT as TraID backtest architecture.

TraID should use event-time replay and canonical production decision logic.

## 24. Versioned Configuration

CryptoRadar uses immutable configuration records and an active config mechanism.

**Decision:** ADAPT strongly.

TraID outcomes should retain:

```text
config_version
strategy_version
risk_gate_version
data_contract_version
source snapshots
```

## 25. Deployment Markers

Append-only deployment markers support before/after performance comparisons.

**Decision:** ADAPT.

TraID should connect material releases to evaluation evidence.

## 26. Empirical Skepticism

The repo's own documentation flags:

- short windows
- small samples
- configuration iteration bias
- confidence intervals crossing zero
- regime dependence
- earlier trail defects
- correlation vs causation

This skepticism is more valuable than headline performance.

Possible TraID evidence-strength states:

```text
DESCRIPTIVE
EXPLORATORY
OUT_OF_SAMPLE
REPLICATED
PRODUCTION_OBSERVED
```

## 27. Tests and Gaps

Reported useful tests include signal bias/config, derivatives, regime, whale calculations/providers, outcome evaluator, trailing, fees, stagnation, Liquidity Sweep, alignment floor, confluence, and reconciliation.

Important gaps include:

- Bollinger current-price semantics
- support/resistance position semantics
- SMA200 price semantics
- hand-calculated alignment contradiction fixtures
- zero/non-normalized weights
- wallet/entity deduplication
- actual order-book-to-signal wiring
- immutable historical replay
- same-bar sequencing
- spread/slippage
- funding cost
- backtest/live divergence

## 28. Architecture Lessons

Strong patterns:

- detector boundary
- shared context
- outcome snapshots
- immutable config
- deployment markers
- bounded caches/timeouts
- shared trade math
- health/readiness
- typed frontend models

Risks:

- `Map<String,Object>` contracts
- string-based dimension names
- duplicated live/backtest scoring
- seed/runtime config divergence
- signal/execution outcome divergence
- fail-open missing-data behavior
- unnecessary microservice complexity for TraID V1

## 29. Decision Matrix

| Capability | Decision | Why | TraID treatment |
|---|---|---|---|
| Versioned config | ADAPT | Reproducibility | Tie every outcome to exact version |
| Deployment markers | ADAPT | Before/after evaluation | Release evidence |
| Dimension snapshots | ADAPT | Preserves decision context | Typed/schema-versioned |
| Detector interface | ADAPT | Modular strategies | Candidate only, no approval |
| Strategy outcomes | ADAPT | Clean attribution | Preserve identity |
| MFE/MAE | ADAPT | Strong diagnostics | Add resolution/provenance |
| Time-to-extreme | ADAPT | Exit/trail analysis | Exact timestamps |
| Gross/net R | ADAPT | Comparable outcomes | Separate cost components |
| Explicit trail state | ADAPT | Auditable exits | Typed/versioned |
| Signal vs execution gate | ADAPT | Governance | Risk Gate remains mandatory |
| Alignment | VERIFY | Useful agreement metric | Never call probability |
| Whale pressure | VERIFY | Transparent flow metric | Rename honestly |
| Sample dampening | VERIFY | Exposes weak evidence | Do not imply independence |
| Regime | VERIFY | Simple context | Evaluate walk-forward |
| Liquidity Sweep | VERIFY | Testable detector | Re-evaluate thresholds |
| Technical additive score | REFERENCE ONLY | Heuristic | Rebuild validated features only |
| Bollinger scorer | REJECT | Wrong price semantics | Independent implementation |
| Support/resistance scorer | REJECT | Semantic mismatch | Use actual price/levels |
| SMA200 midpoint | REJECT | Unusual substitution | Use current price |
| Smart-money inference | REJECT | Flow ≠ skill | Require entity evidence |
| Tier-1 backtest | REJECT | Not event-time replay | TraID-owned replay |
| Optimistic same-bar policy | REJECT | Sequence unknown | STOP FIRST |
| Full microservices | REJECT for V1 | Complexity | Preserve TraID architecture |

## 30. Mapping to TraID Cards

### V1-C10 — Market Regime

Use simple, deterministic, interpretable regime concepts. Do not copy exact thresholds.

### V1-C11 — Whale Intelligence

Separate:

```text
large-trade flow
wallet/entity
position lifecycle
wallet performance
smart-money evidence
```

### V1-C15 — Evidence Registry & Signal Fusion

Possible typed fields:

```text
direction
strength
source refs
contradictions
alignment
uncertainty
```

but alignment cannot become probability or authority.

### V1-C16 — Typed Strategy Engine

Adapt:

- detector interface
- immutable typed context
- strategy identity
- explicit candidate output
- independent evaluation

### V1-C17 — Risk Gate

Maintain strict separation:

```text
signal
strategy candidate
risk approval
decision support
```

### V1-C19 — Outcome Tracking

Highest-value mapping:

- snapshots
- MFE/MAE
- time-to-extreme
- gross/net R
- exit reason
- trail state
- strategy attribution

### V1-C20 — Evaluation Registry

Adapt performance slicing by strategy, signal type, symbol, exit reason, alignment bucket, and deployment marker. Combine with the stronger holdout/trial discipline learned from Hyperliquid Backtester.

### V1-C23 — Observability

Adapt version markers, config snapshots, outcome history, and bounded failure handling. Avoid silently converting missing required evidence into neutral trusted inputs.

## 31. TraID Invariants Derived from This Audit

```text
CR01 Alignment MUST NOT be described as probability/confidence.
CR02 Signal generation MUST NOT authorize a trade.
CR03 Detector output MUST pass deterministic Risk Gate.
CR04 Every candidate MUST retain exact evidence/input snapshots.
CR05 Every outcome MUST retain strategy identity.
CR06 MFE/MAE MUST retain resolution and time provenance.
CR07 Gross and net outcome accounting MUST remain distinct.
CR08 Exit reason MUST be typed and status-consistent.
CR09 Same-bar ambiguity MUST NOT become optimistic without sequence evidence.
CR10 Large-trade flow MUST NOT be labeled Smart Money without entity/performance evidence.
CR11 Order Book, Trade Flow, Liquidations, and Derivatives MUST remain separate domains.
CR12 Missing required data MUST NOT silently become trusted neutral evidence.
CR13 Replay MUST reuse canonical decision logic rather than duplicate scorer logic.
CR14 Config/release versions MUST be reproducible from outcome evidence.
CR15 Empirical performance MUST carry sample size and evidence strength.
```

## 32. Strongest Reusable Patterns

1. immutable versioned configuration
2. deployment markers
3. complete signal/input snapshots
4. pure detector interface
5. strategy-specific outcome identity
6. MFE/MAE
7. time-to-extreme
8. gross/net R accounting
9. explicit trail state and exit reason
10. performance slicing
11. signal-vs-execution separation
12. documented negative findings and empirical skepticism

## 33. Do Not Copy Blindly

- Technical additive score as truth
- Bollinger implementation
- support/resistance implementation
- SMA200 midpoint substitution
- alignment as confidence
- high alignment as assumed edge
- whale flow as Smart Money
- transfer-side assumptions as wallet intent
- mixed `"Order Book"` semantics
- optimistic same-bar ordering
- stored-outcome Tier-1 backtest
- duplicated live/backtest scoring
- exact regime/detector thresholds
- full microservice topology

## 34. Combined Lesson with Hyperliquid Backtester

The two repositories complement each other:

```text
CryptoRadar
→ detectors
→ outcome lifecycle
→ MFE/MAE
→ R attribution
→ version/deployment evaluation

Hyperliquid Backtester
→ anti-lookahead
→ event ordering
→ next-bar fills
→ cost discipline
→ same-bar pessimism
→ reconciliation
→ holdout/trial discipline
```

TraID should combine the **ideas**, not the codebases:

```text
Canonical point-in-time data
        ↓
Typed deterministic evidence
        ↓
Typed strategy candidate
        ↓
Mandatory deterministic Risk Gate
        ↓
Decision support
        ↓
Outcome lifecycle
        ↓
MFE / MAE / R / costs
        ↓
Event-time replay
        ↓
Evaluation registry
        ↓
Version/deployment comparison
```

## 35. Final Decision

**Repository decision:** `REFERENCE ONLY + selective ADAPT / VERIFY`

Strongly adapt:

- outcome tracking
- versioned configuration
- deployment markers
- typed detector equivalent
- signal snapshots
- MFE/MAE
- time-to-extreme
- R accounting
- strategy attribution
- signal-vs-execution separation

Verify:

- whale flow imbalance
- low-sample dampening
- regime rules
- derivatives heuristics
- Liquidity Sweep strategy concepts

Reject:

- flawed Technical sub-formulas
- Smart Money inference from flow alone
- misleading Order Book coupling
- optimistic same-bar policy
- Tier-1 backtest architecture
- alignment-as-confidence
- full microservice topology for TraID V1

**Primary TraID influence:** `C16`, `C19`, `C20`, and `C23`, with selected lessons for `C10`, `C11`, and `C15`.
