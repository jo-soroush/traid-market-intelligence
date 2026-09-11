# TRAID SOURCE VERIFICATION — C15, C16, C18, C19

**Date:** 2026-09-03  
**Scope:** Function-level verification of CryptoRadar and Hyperliquid Backtester  
**Cards covered:** C15 Signal Fusion, C16 Strategy architecture/detectors, C18 Backtest, C19 Outcome Tracking  
**Runtime status:** External repos source-verified, not yet TraID-runtime approved

---

# 1. Executive Decision

This source block gives TraID two very strong things:

1. **CryptoRadar** gives useful methodology for multi-dimensional evidence fusion, modular setup detectors, and outcome tracking.
2. **Hyperliquid Backtester** gives the strongest deterministic simulation mechanics found so far.

The key rule after verification is:

```text
CryptoRadar
→ ADAPT methodology
→ DO NOT copy Java/microservice architecture
→ DO NOT copy its trade authority

Hyperliquid Backtester
→ ADAPT engine invariants strongly
→ replace provider/storage/domain contracts with TraID-owned ones
```

---

# 2. C15 — Signal Fusion

## Source

Repository:

```text
artyomsv/crypto-radar
```

License:

```text
MIT
```

Exact file:

```text
services/signal-service/src/main/java/com/cryptoradar/signal/service/SignalEngine.java
```

Source status:

```text
SOURCE VERIFIED
```

---

# 3. SignalEngine — Exact Flow Verified

The engine constructs six dimensions:

```text
technical
whale
derivatives
sentiment
orderBook
macro
```

Then performs:

```text
DimensionScore list
↓
computeOverallScore(...)
↓
computeAlignment(...)
↓
determineSignalLabel(...)
```

Verified call flow:

```text
technical = scoreTechnical(...)
whale = scoreWhale(...)
derivatives = scoreDerivatives(...)
sentiment = scoreSentiment(...)
orderBook = scoreOrderBook(...)
macro = scoreMacro(...)

overallScore = computeOverallScore(...)
alignment = computeAlignment(...)
signalLabel = determineSignalLabel(...)
```

The repo explicitly states that the field previously called “confidence” was renamed to **alignment** after outcome analysis showed an inverse relationship with win rate.

That is one of the most valuable lessons in the repo.

## TraID consequence

TraID must never expose:

```text
alignment = probability of winning
```

Instead:

```text
alignment = degree of directional agreement among selected evidence dimensions
```

---

# 4. determineSignalLabel() Verified

The source uses:

```text
score
alignment
market regime
regime-adjusted thresholds
```

to return labels such as:

```text
STRONG_BUY
BUY
STRONG_SELL
SELL
NEUTRAL
```

The source pattern is:

```text
if score >= strongBuy threshold
and alignment >= strong alignment threshold
→ STRONG_BUY

...
```

and thresholds are adjusted for regime.

Example policy:

```text
BULL
→ raise counter-trend SELL threshold

BEAR
→ raise counter-trend BUY threshold
```

## What TraID takes

```text
multi-dimensional evidence
explicit agreement
explicit contradiction
regime-aware interpretation
versioned thresholds
outcome-based recalibration
```

## What TraID rejects

```text
BUY/SELL label as final authority
static copied weights
static copied thresholds
Java implementation
alignment as confidence/probability
direct action from fusion score
```

## TraID C15 output

TraID should instead produce:

```text
alignment_score
supporting_evidence
contradicting_evidence
missing_evidence
regime
data_quality
evidence_refs
fusion_version
```

Signal Fusion remains evidence aggregation only.

---

# 5. C15 — Important Design Improvement

CryptoRadar combines dimensions into score + alignment.

TraID should make contradiction more first-class.

Instead of only:

```text
overallScore
alignment
```

TraID should retain:

```text
support_count
contradiction_count
missing_count
stale_count
weighted_support
weighted_contradiction
```

This allows the Strategy Engine and UI to see why evidence aligns or conflicts.

## Final C15 decision

```text
Six-dimension architecture: ADAPT
computeAlignment concept: ADAPT
regime modulation: ADAPT
weights: BUILD/CALIBRATE
thresholds: BUILD/CALIBRATE
BUY/SELL authority: REJECT
Python TraID implementation: BUILD
```

---

# 6. C16 — Modular Strategy / Setup Detectors

CryptoRadar confirms a useful plugin-like detector architecture.

Verified detector classes include:

```text
TrendContinuationDetector
LiquiditySweepDetector
TradeSetupDetector
```

The README confirms detectors auto-register and are evaluated independently by Outcome Tracking.

This is important because TraID should not create one giant strategy function.

## Useful pattern

```text
Evidence
↓
Independent Detector
↓
Typed Setup
↓
Strategy Engine
↓
Risk Gate
```

A detector should have:

```text
strategy_id
strategy_version
required_evidence
rules
direction
entry logic
stop logic
target logic
reason codes
```

## What TraID takes

- independent detector pattern
- detector-specific outcome tracking
- strategy identity/version
- explicit rule firing
- separate strategy families

## What TraID does not take

- CDI/Quarkus registration
- Java interfaces
- live signal dispatch
- execution integration
- Gemini involvement

---

# 7. C16 — Relationship With Keel

Keel remains the stronger architecture reference for:

```text
typed definition
validation
compile
deterministic artifact
```

CryptoRadar is stronger for:

```text
simple modular detectors
independent detector evaluation
```

TraID should combine the ideas:

```text
StrategyDefinition
↓
validate
↓
StrategyArtifact
↓
one or more deterministic detector/rule components
↓
StrategyResult
```

## Final C16 decision

```text
Keel typed artifact architecture: ADAPT
CryptoRadar detector pattern: ADAPT
External strategy runtime dependency: REJECT
TraID Strategy Engine: BUILD
```

---

# 8. C18 — Hyperliquid Backtester

Repository:

```text
Crypto-Data-API/hyperliquid-backtester
```

License:

```text
MIT
```

Exact verified files:

```text
src/hlbt/backtester.py
src/hlbt/strategy.py
src/hlbt/sync.py
src/hlbt/indicators.py
src/hlbt/metrics.py
src/hlbt/demo.py
tests/
```

This remains the strongest code-level candidate for C18.

---

# 9. backtester.py — Order of Operations Verified

The source explicitly documents this order per bar:

```text
1. fill pending order at current bar open
2. accrue funding
3. check liquidation
4. check hard stop
5. check take profit
6. ask strategy whether to exit
7. ask strategy whether to enter
8. queue new entry for next bar
```

This is excellent because execution ordering is explicit.

## Critical principle

A signal generated from bar `i` cannot fill at bar `i` close.

It fills at:

```text
bar i+1 open
```

This prevents same-bar lookahead optimism.

## TraID decision

```text
next-bar-open rule: ADAPT STRONG
explicit event ordering: ADAPT STRONG
```

---

# 10. Intrabar Ambiguity

The backtester uses a conservative rule:

If one OHLC bar spans both:

```text
stop
and
target
```

then:

```text
STOP WINS
```

Reason:

OHLC does not reveal intrabar event ordering.

This is a strong anti-optimism rule and should be TraID V1 default.

## TraID decision

```text
ambiguous stop+target bar
→ pessimistic policy
→ stop first
```

Any future higher-resolution simulation can improve this.

---

# 11. BacktestConfig — Defaults Are Not Truth

Verified configuration includes defaults such as:

```text
initial_capital = 10,000
taker_fee = 0.00035
slippage = 0.0002
maintenance_margin_fraction = 0.5
apply_funding = true
```

These defaults are useful examples only.

TraID must not silently inherit them.

## TraID action

All financial assumptions must be:

```text
explicit
versioned
included in run metadata
```

Especially:

```text
fee model
slippage model
maintenance/liquidation logic
funding semantics
```

---

# 12. strategy.py — Anti-Lookahead Architecture Verified

Exact verified classes:

```text
Signal
Position
Context
Strategy
```

The most important design is `Context`.

On bar `i`, arrays are sliced only through:

```text
[:i+1]
```

Therefore the strategy literally cannot access future bars through its context.

This is much stronger than relying on programmer discipline.

## TraID decision

This principle should be mandatory.

TraID strategy evaluation receives a **present-only view**.

Never provide a full historical dataframe to arbitrary strategy logic.

---

# 13. strategy.py — Useful Contracts

Verified `Signal` contains concepts such as:

```text
side
reason
stop_pct
take_pct
meta
```

`Position` contains:

```text
side
entry_price
entry_index
entry_time
size
notional
leverage
stop
take
funding_paid
meta
```

`Strategy` provides:

```text
on_bar(...)
should_exit(...)
warmup
max_positions
position_size_pct
leverage
```

## What TraID takes

- small typed strategy context
- explicit warmup
- explicit signal object
- explicit position state
- unknown configuration parameter rejection
- strategy parameter introspection

## What TraID changes

TraID must not let `Strategy` directly choose unrestricted leverage/position risk.

Those are subject to:

```text
Strategy
↓
Risk Gate
```

The Risk Gate remains final authority.

---

# 14. Funding Handling

The engine can consume a per-bar funding series.

This is useful.

However TraID must first normalize Hyperliquid funding semantics correctly in the data layer.

The backtester should consume:

```text
canonical_funding_rate
```

rather than provider-specific raw fields.

## Decision

```text
funding cost inclusion: ADAPT STRONG
provider funding normalization: TRAID-owned
```

---

# 15. Liquidation Model

The backtester checks leverage-aware liquidation against the adverse OHLC extreme.

This is better than ignoring liquidation.

But the current maintenance margin abstraction is simplified.

TraID should preserve the invariant:

```text
leveraged position can liquidate
```

while validating the exact Hyperliquid liquidation semantics before claiming exchange-perfect simulation.

## Decision

```text
liquidation presence: ADAPT
exact formula: VERIFY / REWRITE
```

---

# 16. Backtest Limitations Confirmed

The repo itself explicitly says it does not model fully:

```text
order-book depth
partial fills
market impact
```

Therefore V1 should never market the engine as a perfect execution simulator.

TraID V1 backtest is:

```text
deterministic research simulation
```

not exchange-microstructure reproduction.

---

# 17. C18 — Metrics

Verified source file:

```text
src/hlbt/metrics.py
```

README confirms metrics including:

```text
profit factor
expectancy
Sharpe
max drawdown
fees
funding
liquidations
```

The repo also deliberately emphasizes that no single metric is enough.

This is a good evaluation principle.

TraID should retain a metric set rather than optimize for win rate alone.

## Required V1 metrics

At minimum:

```text
net return
win rate
profit factor
expectancy
max drawdown
fees
funding
liquidations
number of trades
average R
```

---

# 18. C18 — Validation Philosophy

The repo provides a valuable example of held-out validation.

Its documentation warns against:

```text
parameter searching
multiple comparisons
overfitting
```

This supports TraID's later walk-forward/evaluation design.

V1 should at minimum separate:

```text
development period
validation period
```

for strategy experiments.

Do not optimize thresholds on the same window used for final reporting.

---

# 19. Final C18 Decision

```text
bar-by-bar engine: ADAPT STRONG
present-only Context: ADAPT STRONG
next-bar-open fill: ADAPT STRONG
stop-first ambiguity: ADAPT STRONG
fees: ADAPT concept, configure exact value
funding: ADAPT STRONG after canonical normalization
liquidation: ADAPT concept, verify formula
metrics: ADAPT
CryptoDataAPI dependency: REJECT
provider storage: REPLACE
TraID Strategy + Risk Gate: INTEGRATE
```

---

# 20. C19 — Outcome Tracking

Primary CryptoRadar sources:

```text
services/signal-service/src/main/java/com/cryptoradar/signal/service/OutcomeEvaluator.java
services/signal-service/src/main/java/com/cryptoradar/signal/service/OutcomeTracker.java
```

Additional repository component:

```text
SignalOutcomeRepository
```

Source status:

```text
SOURCE VERIFIED
```

---

# 21. OutcomeEvaluator — Evaluation Loop Verified

The service runs periodically and evaluates pending outcomes against 1-minute candles.

Verified flow:

```text
find pending outcomes
↓
fetch recent 1m candles
↓
resolve last scanned timestamp
↓
for each new candle:
    update excursions
    update trailing stop
    detect stop/target
↓
close if terminal
↓
otherwise update last evaluated timestamp
↓
optional stagnation/expiry rules
```

This incremental evaluation structure is useful.

## What TraID takes

- incremental scanning
- `last_evaluated_at`
- no reprocessing already-consumed bars
- MFE/MAE tracking
- terminal reason
- outcome lifecycle

---

# 22. MFE / MAE

CryptoRadar tracks:

```text
Maximum Favorable Excursion
Maximum Adverse Excursion
```

with timestamps.

This is high-value for TraID because it lets us answer:

```text
Did the setup move favorably?
How far?
How quickly?
How bad was the adverse move?
```

These are much more informative than win/loss alone.

## TraID C19 must store

```text
mfe
mae
time_to_mfe
time_to_mae
realized_R
final_exit_reason
```

plus all relevant system versions.

---

# 23. OutcomeEvaluator — ATR-Scaled Stagnation Rule

A useful design evolution appears in the source.

Older absolute stagnation thresholds caused problems across assets.

The repo moved toward ATR-scaled thresholds.

This is a valuable general lesson:

```text
fixed percent threshold
can behave very differently across volatility regimes
```

TraID should retain the concept that thresholds may need volatility normalization.

But:

```text
0.25 ATR
0.4 ATR
45 bars
```

are not TraID truths.

They are hypotheses requiring evaluation.

---

# 24. Important Conflict Found: Intrabar Policy

CryptoRadar's `detectHit()` contains two policies.

When trail is inactive:

```text
stop first
```

which is conservative.

When trail is active and the same bar touches target and stop/trail:

```text
target first
```

The source describes this as an optimistic assumption based on the path required to activate the trail.

This is a real methodological assumption.

It differs from Hyperliquid Backtester's simpler conservative policy:

```text
stop always wins when OHLC ordering is unknown
```

## TraID decision

For V1:

```text
DO NOT ADOPT CryptoRadar optimistic target-first trail policy
```

Use one explicit conservative rule:

```text
if event ordering cannot be known from data resolution
→ choose pessimistic outcome
```

unless higher-resolution data proves sequence.

This avoids strategy-specific optimism.

---

# 25. Trailing Stop Ladder

CryptoRadar supports per-strategy trail configuration such as:

```text
activation R
step R
offset R
```

and stores it per outcome.

This architecture is useful.

## Take

```text
strategy-specific trailing policy
stored with the outcome
versionable parameters
attribution of exit reason
```

## Do not take

The particular default parameter values as universal.

---

# 26. OutcomeTracker

The tracker creates persistent outcome records from setups/signals.

Verified behavior includes storing:

```text
strategy
signal type
direction
entry
stop
target
trail configuration
```

and applying per-strategy trail settings.

This is valuable for traceability.

TraID should go further and attach:

```text
strategy_version
risk_gate_version
fusion_version
analytics_version
data_snapshot_hash
AI_model_id
prompt_version
configuration_version
evidence_refs
```

---

# 27. Outcome Status / Exit Reason

CryptoRadar distinguishes reasons such as:

```text
TARGET
TRAIL_STOP
INITIAL_STOP
EXPIRED
STAGNATION
```

This is better than storing only PnL.

TraID should preserve an explicit terminal reason taxonomy.

It should also support:

```text
OPEN
UNRESOLVED
DATA_GAP
INVALIDATED
```

where appropriate.

---

# 28. C19 — Final Decision

```text
incremental outcome loop: ADAPT STRONG
MFE/MAE: ADAPT STRONG
time-to-MFE/MAE: ADAPT
exit reason: ADAPT
per-strategy trailing config: ADAPT architecture
ATR-scaled rule concept: REFERENCE/ADAPT
specific thresholds: DO NOT COPY
optimistic intrabar trail policy: REJECT
TimescaleDB dependency: REJECT
Python TraID implementation: BUILD
```

---

# 29. Revised Card Map

| Card | Source | Exact code | Decision |
|---|---|---|---|
| C15 | CryptoRadar | `SignalEngine.java` | ADAPT methodology |
| C16 | CryptoRadar + Keel | detector classes + typed artifact architecture | ADAPT architecture, BUILD TraID |
| C18 | Hyperliquid Backtester | `backtester.py`, `strategy.py`, `metrics.py`, `sync.py`, tests | ADAPT STRONG |
| C19 | CryptoRadar | `OutcomeEvaluator.java`, `OutcomeTracker.java` | ADAPT methodology |

---

# 30. Strongest Functions / Patterns Worth Bringing Into TraID

## CryptoRadar

```text
SignalEngine:
computeOverallScore(...)
computeAlignment(...)
determineSignalLabel(...)
regimeAdjustedThresholds(...)

OutcomeEvaluator:
evaluatePending()
evaluateOne(...)
updateExcursions(...)
updateTrailingStop(...)
detectHit(...)
effectiveStop(...)
ATR-scaled stagnation concept

OutcomeTracker:
outcome creation
per-strategy trail config persistence
```

These names should be re-confirmed at implementation time if exact direct translation is considered.

## Hyperliquid Backtester

```text
Backtester.run(...)
present-only Context
next-bar fill queue
stop-before-target policy
funding accounting
liquidation check
BacktestResult.summary()
Strategy.on_bar(...)
Strategy.should_exit(...)
```

---

# 31. What TraID Should Build Better

External sources do not provide these complete requirements:

```text
canonical evidence registry
explicit contradiction registry
data-quality-aware fusion
typed StrategyArtifact
non-bypassable Risk Gate
shared live/backtest risk contract
full version/provenance metadata
dataset hash
Golden Case replay
```

These remain TraID-owned.

---

# 32. Key Engineering Decision

The strongest combination now appears to be:

```text
Project 04
→ deterministic market measurements

CryptoRadar
→ evidence fusion + detector pattern + outcome methodology

Keel
→ typed strategy artifact architecture

Hyperliquid Backtester
→ simulation mechanics

TraID
→ canonical contracts + Risk Gate + provenance + integration
```

This combination is substantially stronger than choosing any one repository as the base system.

---

# 33. Next Source Verification Block

The remaining highest-value unresolved sources are:

```text
C12 — NEXUS macro exact provider files
C14 — Quant Flow exact AI boundary files
C16 — Keel exact compiler/artifact files
```

Once those three are function-level verified, the external source map for V1 is essentially complete.

At that point TraID can move from research/source selection into controlled Card implementation.
