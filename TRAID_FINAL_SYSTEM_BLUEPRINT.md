# TRAID FINAL SYSTEM BLUEPRINT

**Status:** Consolidated architecture blueprint before implementation  
**Goal:** Build TraID as a real, coherent, production-shaped market-intelligence system by taking the strongest ideas, methods, and engineering patterns from audited projects without copying whole repositories.

---

# 1. Core Principle

TraID is **not** a merge of external repositories.

The governing rule is:

> Take the best ideas, algorithms, architecture patterns, and engineering practices from other projects, remove unnecessary complexity, and implement them as one coherent TraID system.

Every external idea must be classified as one of:

- **ADAPT** — use the method/pattern after modifying it for TraID
- **BUILD** — implement TraID's own version
- **REFERENCE ONLY** — learn from it but do not import it
- **REJECT** — intentionally exclude it

TraID must preserve one clean system boundary and one canonical domain model.

---

# 2. Final Architecture

```text
Market Data Sources
├── Hyperliquid      ← V1 live implementation
├── Binance          ← later adapter
├── Bybit            ← later adapter
├── OKX              ← later adapter
└── other sources    ← later
        ↓
Exchange Adapters
        ↓
Canonical TraID Data
        ↓
Data Quality + Provenance
        ↓
Deterministic Analytics
        ↓
Whale Intelligence + Macro + Verified News
        ↓
Bedrock Intelligence
        ↓
Signal Fusion
        ↓
Typed Deterministic Strategy Engine
        ↓
Mandatory Deterministic Risk Gate
        ↓
Decision Support
├── Dashboard
├── Outcome Tracking
└── Backtest / Replay
```

---

# 3. Non-Negotiable Boundary

AI does not control the trading logic.

```text
AI:
- explains
- compares
- summarizes evidence
- detects contradiction
- exposes uncertainty

Deterministic software:
- calculates market metrics
- validates strategy rules
- evaluates risk
- approves/rejects trade candidates
```

No AI model, Bedrock output, whale score, macro signal, or news interpretation may bypass:

```text
Strategy Engine
↓
Risk Gate
```

---

# 4. Multi-Exchange Architecture

V1 will connect live to **Hyperliquid only**.

However, the architecture must be ready for:

- Binance
- Bybit
- OKX
- Coinbase
- Kraken
- other exchanges later

The Core must never depend on exchange-specific schemas.

```text
Hyperliquid JSON ─┐
Binance JSON ─────┤
Bybit JSON ───────┤
OKX JSON ─────────┘
        ↓
Exchange Adapters
        ↓
Canonical TraID Data
```

This means exchange-specific handling stays inside adapters.

---

# 5. Canonical TraID Data Model

TraID must own its own schemas.

Initial core entities:

```text
MarketTrade
OrderBookSnapshot
Candle
FundingSnapshot
OpenInterestSnapshot
LiquidationEvent
MarketContext
PriceSnapshot
DataQualityState
SourceProvenance
```

Typical normalized fields:

```text
symbol
exchange
source
source_timestamp
received_timestamp
price
volume
side
size
open_interest
funding_rate
mark_price
oracle_price
bid
ask
liquidation_value
validation_status
freshness_state
```

The Core should not care whether the source was Hyperliquid, Binance, Bybit, or OKX.

---

# 6. Data Provider Layer

## Primary inspiration

### Hyperliquid Analytics Dashboard

Best current source for:

- Hyperliquid REST
- Hyperliquid WebSocket
- market transport pattern
- candle ingestion
- data normalization ideas

Important source modules identified:

```text
hyperliquid_client.py
transport_hyperliquid_sdk.py
candle_aggregator.py
candle_fetcher.py
config.py
models.py
```

## TraID decision

**BUILD clean adapter interface + ADAPT Hyperliquid connection patterns**

TraID must add:

- reconnect handling
- recovery
- gap detection
- provenance
- canonical schemas
- freshness
- historical gap handling

---

# 7. Data Quality + Provenance

TraID must explicitly know whether data can be trusted.

## Data states

```text
LIVE
DELAYED
STALE
UNAVAILABLE
```

Every important observation should carry:

```text
source
exchange
source_timestamp
received_timestamp
age
validation_status
gap_status
recovery_status
```

## Inspirations

### Hyperliquid Analytics Dashboard
Provides:

- freshness checks
- module health
- feed status
- rate-limit awareness
- latency monitoring

### CryptoRadar
Useful patterns:

- green/amber/red connection state
- staleness handling
- WebSocket + REST fallback

### NEXUS
Useful patterns:

- IndexerCheckpoint
- health/status endpoints

## TraID decision

**BUILD TraID's own complete Data Quality contract**

No audited repository provides the full contract required by TraID.

---

# 8. Deterministic Market Analytics

The analytics layer must be deterministic and testable.

AI must never calculate authoritative financial metrics.

## Primary implementation inspiration

### Hyperliquid Analytics Dashboard

Important source modules:

```text
orderbook_metrics.py
trade_flow_tracker.py
market_indicators.py
volatility.py
session_context.py
crowding_detector.py
regime_detector.py
slippage_estimator.py
liquidations.py
price_momentum.py
depth_decay.py
cross_asset_context.py
```

## Candidate analytics

### Order Book
- L1 imbalance
- L5 imbalance
- depth
- liquidity concentration
- book walking
- depth decay

### Trade Flow
- buy/sell pressure
- CVD
- directional sweep
- aggressive flow

### Derivatives
- Open Interest
- OI change
- OI spike
- funding
- funding extremes
- basis
- price/OI divergence

### Volatility
- ATR
- realized volatility
- volatility regime

### Session
- VWAP
- session context

### Liquidity
- slippage estimate
- available depth
- abnormal liquidity state

### Market State
- crowding
- regime
- momentum
- liquidation activity
- cross-asset context later

## TraID decision

**ADAPT formulas and methods, then verify/calibrate**

Do not blindly copy thresholds or heuristics.

Thresholds must later be calibrated from TraID outcomes.

---

# 9. Whale / Smart Money Intelligence

## Primary methodology source

### HyperStats

Useful ideas:

- Quality + Proof
- realized-first evaluation
- current exposure vs historical activity
- notional long/short bias
- bot/noise filtering
- Top Positions
- wallet lifecycle
- Discovery → Verification → Token Context

## Position lifecycle

```text
OPEN
INCREASE
REDUCE
CLOSE
FLIP
LIQUIDATION
```

## TraID must track

- wallet
- position size
- position value
- entry
- leverage
- liquidation price
- realized PnL
- unrealized PnL
- drawdown
- consistency
- position lifecycle
- activity windows
- current exposure

## Smart Money Score

TraID must **BUILD** its own transparent score.

Required properties:

- explicit formula
- versioned weights
- realized performance
- risk/drawdown
- consistency
- evidence depth
- current behavior

Important rule:

> Large wallet ≠ Smart Money

Whale activity is evidence only.

It never directly authorizes a trade.

---

# 10. Macro Intelligence

## Primary architecture reference

### NEXUS

Useful patterns:

- FRED provider
- Treasury data
- World Bank data
- economic calendar
- central-bank calendar
- correlations
- checkpoints
- alerts
- health/status

## V1 Macro priority

```text
1. FOMC
2. CPI
3. PCE
4. NFP
5. interest rates
6. major central-bank events
```

Later:

- broader macro correlations
- additional government sources
- options context
- cross-asset relationships

## TraID decision

**ADAPT provider architecture, not the full NEXUS stack**

Do not bring in unnecessary:

- Redis complexity
- multi-chain indexers
- full Next.js architecture
- unrelated services

---

# 11. News Verification

No audited project is sufficient for TraID's desired verification layer.

Therefore this is a core TraID capability.

## Pipeline

```text
News / Social / Telegram / X
        ↓
Claim Extraction
        ↓
Primary Source Matching
        ↓
Timestamp Validation
        ↓
FACT vs INTERPRETATION
        ↓
Verification Status
        ↓
Verified Event Intelligence
```

## Verification statuses

```text
CONFIRMED
PARTIALLY_CONFIRMED
UNVERIFIED
MISLEADING
FALSE
OUTDATED
```

## Primary sources initially

- Federal Reserve
- BLS
- BEA
- SEC
- other authoritative sources when relevant

## Important rule

Unverified high-impact news should:

- increase uncertainty
- increase risk
- be surfaced clearly

It should **not** automatically create a directional trading signal.

---

# 12. Bedrock Intelligence Layer

TraID will use Amazon Bedrock as the AI intelligence layer.

The model may later be Claude through Bedrock or another compatible Bedrock model.

Core logic must remain provider-neutral.

```text
TraID
↓
AI Provider Adapter
↓
Amazon Bedrock
├── Claude
├── Nova
└── other supported models
```

## Bedrock input

Structured evidence from:

- market analytics
- whales
- macro
- news verification
- data quality
- signal context

## Bedrock output

Structured intelligence object:

```text
supporting_factors
contradicting_factors
uncertainty
missing_information
evidence
source_references
analysis_timestamp
```

## Inspiration

### Quant Flow

Useful patterns:

- structured model output
- schema validation
- fail-closed AI behavior
- prompt separation
- provider separation
- malformed-response testing
- replayability
- deterministic decision replay

## Failure rule

If the model times out or returns malformed output:

```text
AI_UNAVAILABLE
```

The system must not guess or fabricate analysis.

---

# 13. Signal Fusion

## Primary inspiration

### CryptoRadar

Important ideas:

- multiple evidence dimensions
- weighted fusion
- alignment
- contradiction
- regime awareness
- outcome-driven calibration

## Important lesson

Alignment is **not** probability of winning.

TraID should never mislabel evidence alignment as trade probability.

## TraID Signal Fusion output

Example:

```text
alignment_score
supporting_evidence
contradicting_evidence
missing_evidence
market_regime
data_quality
```

Signal Fusion does not authorize execution.

It only organizes evidence.

---

# 14. Strategy Engine

## Primary architecture inspiration

### Keel

Useful ideas:

```text
Rules
↓
Validate
↓
Compile
↓
Typed Strategy Artifact
↓
Evaluate
```

Strategy must not be a prompt blob.

## Example

```text
StrategyVersion: BTC_BREAKOUT_V3

RequiredEvidence:
  OI
  CVD
  Volume
  Volatility

Rules:
  deterministic conditions
```

## Possible output

```text
LONG_SETUP
SHORT_SETUP
NO_SETUP
```

## Secondary inspiration

### CryptoRadar

Useful detector pattern:

```text
TradeSetupEngine
TradeSetupDetector
TrendContinuationDetector
LiquiditySweepDetector
```

TraID can use independent setup detectors but must define its own rules.

---

# 15. Mandatory Deterministic Risk Gate

This is one of the core features TraID must own.

No external project provides the complete TraID Risk Gate.

## Risk checks

At minimum:

```text
Data fresh?
Required evidence available?
Stop valid?
Risk/Reward valid?
Leverage acceptable?
Position risk acceptable?
Volatility acceptable?
Liquidity acceptable?
Slippage acceptable?
Abnormal market regime?
Configuration valid?
```

## Output

```text
TRADE_CANDIDATE
NO_TRADE
```

With deterministic reason codes.

Example:

```text
NO_TRADE:
STALE_DATA
RISK_REWARD_TOO_LOW
LIQUIDITY_TOO_LOW
VOLATILITY_TOO_HIGH
STOP_INVALID
```

## Non-bypass rule

The following cannot override the Risk Gate:

- Bedrock
- AI agent
- whale score
- macro event
- news signal
- signal fusion
- strategy confidence
- user interface

---

# 16. Backtesting

## Primary implementation inspiration

### Hyperliquid Backtester

Important files identified:

```text
src/hlbt/backtester.py
src/hlbt/strategy.py
src/hlbt/sync.py
src/hlbt/indicators.py
src/hlbt/metrics.py
src/hlbt/demo.py
strategies/
tests/
```

## Important engineering patterns

- bar-by-bar execution
- anti-lookahead
- sliced strategy context
- next-bar-open fills
- fees
- funding
- liquidation
- P&L reconciliation
- incomplete trailing-bar removal
- reproducibility
- local resampling

## TraID backtesting pipeline

```text
Historical TraID Data
↓
Same Strategy Artifact
↓
Same Risk Gate
↓
Bar-by-bar Simulation
↓
Fees + Funding + Liquidation + Slippage
↓
Evaluation Registry
```

## Important rule

Backtest and live strategy logic should use the same strategy definition wherever possible.

---

# 17. Leakage Prevention

TraID must protect against:

- lookahead bias
- future data leakage
- incomplete candle leakage
- future funding knowledge
- future market-state leakage

Strategies must only receive information available at the simulated timestamp.

---

# 18. Outcome Tracking

## Primary inspiration

### CryptoRadar

Important tracked values:

- MFE
- MAE
- time-to-MFE
- time-to-MAE
- realized R
- fees
- exit reason
- detector identity
- alignment
- market regime

## TraID additions

Every candidate should also store:

```text
strategy_version
risk_gate_version
data_snapshot_hash
AI_model_version
prompt_version
source_evidence_ids
configuration_version
timestamp
```

## Purpose

TraID must know:

> What did the system believe at the time, and what actually happened afterward?

This creates a measurable feedback loop.

---

# 19. Evaluation

TraID should evaluate the system at multiple levels.

## Data
- missing data
- freshness
- gaps
- latency
- feed health

## Analytics
- formula correctness
- financial invariants
- reproducibility

## Strategy
- setup frequency
- win/loss behavior
- expectancy
- drawdown
- regime performance

## Risk
- rejection frequency
- false approvals
- risk-rule effectiveness

## AI
- structured output success
- malformed outputs
- latency
- cost
- contradiction detection
- source grounding
- fail-closed behavior

## Overall
- outcome quality
- decision reliability
- strategy version comparison
- performance degradation

---

# 20. Observability

TraID must monitor:

```text
API latency
WebSocket health
feed gaps
stale data
rate-limit events
tool failures
AI failures
AI latency
AI cost
strategy outcomes
Risk Gate rejection reasons
backtest performance
system errors
```

This should be treated as part of the product, not debugging only.

---

# 21. Dashboard

The UI should be clean and progressively disclose detail.

The main page should answer:

> What is happening?  
> What changed?  
> What is risky?  
> What deserves inspection?

## Inspirations

### HyperStats
- wallet discovery flow
- token context
- Top Positions
- current exposure vs recent activity

### Hyper Display
- positions
- multi-wallet monitoring
- PnL
- funding
- liquidation
- watchlists
- alerts

### CryptoRadar
- outcome ledger
- regime badge
- connection/staleness indicator

### Hyperliquid Analytics Dashboard
- Data Quality
- Feed status
- module health

### Quant Flow
- evidence
- supporting factors
- contradictions
- uncertainty

## Main dashboard areas

Possible structure:

```text
Market Overview
Data Quality
Analytics
Whale Intelligence
Macro
Verified News
AI Intelligence
Signal Fusion
Strategy Result
Risk Gate
Outcome Tracking
```

Detailed information should open progressively instead of filling one giant screen.

---

# 22. API / Backend

TraID backend should be simple and cohesive.

Preferred shape:

```text
Python
FastAPI
typed domain models
modular services
deterministic core
```

No unnecessary microservice architecture in V1.

---

# 23. Docker

TraID should be containerized.

Docker should support:

- reproducible local environment
- backend startup
- dependency control
- later AWS deployment
- CI testing

---

# 24. Testing

Use automated tests extensively.

Preferred:

```text
pytest
```

Critical areas:

- financial formulas
- canonical normalization
- stale data handling
- reconnect logic
- gap detection
- strategy rules
- Risk Gate
- backtest invariants
- anti-lookahead
- malformed AI output
- timeout behavior
- deterministic replay

---

# 25. CI/CD

Use GitHub Actions for:

- test execution
- linting
- type checks
- security checks where appropriate
- Docker validation
- deployment checks later

Any failure in critical financial/risk tests must block deployment.

---

# 26. AWS

TraID should be local-first but cloud-ready.

Potential AWS usage:

```text
Amazon Bedrock
container deployment
managed storage later
monitoring later
secrets management
```

Cloud services should be added only where justified.

---

# 27. What TraID Owns

These components define TraID's identity and should not be delegated wholesale to external projects.

TraID must own:

1. Canonical Domain Schemas
2. Exchange Adapter Interface
3. Data Quality Contract
4. Provenance
5. Smart Money Score
6. News Verification
7. Bedrock Intelligence Schema
8. Signal Fusion calibration
9. Strategy rules
10. Deterministic Risk Gate
11. Cross-component audit trail
12. Evaluation Registry
13. Final Dashboard composition

---

# 28. External Project Contribution Map

| Project | Best contribution | TraID decision |
|---|---|---|
| Hyperliquid Analytics Dashboard | Hyperliquid connection + deterministic analytics + data health | ADAPT |
| CryptoRadar | Signal Fusion + Outcome Tracking + detector patterns | ADAPT |
| Hyperliquid Backtester | Backtest engine principles + anti-lookahead + trading costs | ADAPT |
| HyperStats | Whale / Smart Money methodology | REFERENCE + ADAPT methodology |
| NEXUS | Macro provider architecture + calendar + health/checkpoints | ADAPT selected patterns |
| Keel | Typed Strategy architecture | ADAPT architecture |
| Quant Flow | Safe AI boundary + structured output + fail-closed + replay | ADAPT architecture |
| Hyper Display | Wallet/position UX | REFERENCE + ADAPT UX |
| Hyperliquid Data Layer API | Endpoint/provider ideas | CONDITIONAL / EVALUATE |

---

# 29. Explicit Rejections

Do not bring these into V1 without a concrete measured need:

- Java/Quarkus microservice stack
- Gemini or any LLM as BUY/SELL authority
- hidden Smart Money grading formulas
- provider-specific schemas in Core
- AI chat as trading authority
- full NEXUS stack
- unnecessary Redis architecture
- multi-chain complexity
- Keel as a critical alpha dependency
- live automated execution
- hard CryptoDataAPI dependency
- Tauri desktop architecture
- Pydantic AI only because another project uses it
- LangChain/LangGraph without a demonstrated need
- AI-generated financial calculations as authority
- AI bypass of deterministic risk controls

---

# 30. V1 Scope

V1 should be real, but controlled.

## Implement now

- Hyperliquid live data
- canonical schemas
- data validation
- freshness/provenance
- deterministic analytics
- basic Whale Intelligence
- core Macro
- primary-source News Verification
- Bedrock structured intelligence
- Signal Fusion
- typed deterministic Strategy Engine
- mandatory Risk Gate
- backtest/replay
- Outcome Tracking
- FastAPI
- Docker
- pytest
- CI
- dashboard
- AWS/Bedrock integration

## Architecture-ready, but not live in V1

- Binance
- Bybit
- OKX
- Coinbase
- Kraken

Adapters can be added later without redesigning the Core.

---

# 31. Intentionally Deferred

Do not add yet:

```text
XGBoost
LightGBM
LSTM
1D CNN
MLflow
Model Registry
Automated Retraining
Prediction Drift
Model Promotion
Model Rollback
full MLOps stack
live trade execution
multi-agent complexity
```

These should only be introduced if real TraID data and evaluation show a measurable benefit.

---

# 32. Future ML Extension

Machine Learning can later become an additional evidence module:

```text
TraID Features
↓
Baseline
↓
XGBoost / LightGBM
↓
Walk Forward Evaluation
↓
Compare against deterministic baseline
```

Only if it adds measurable value should TraID introduce:

- MLflow
- Model Registry
- Model Versioning
- Data Drift
- Prediction Drift
- Controlled Retraining
- Promotion
- Rollback

ML must never replace the deterministic Risk Gate.

---

# 33. Final Engineering Philosophy

TraID should be built with these rules:

### Data before AI
Bad data must never be hidden by an AI layer.

### Deterministic financial calculations
Financial metrics must be testable and reproducible.

### AI as intelligence, not authority
AI explains evidence and uncertainty.

### Risk controls are deterministic
Risk Gate is mandatory.

### Provider isolation
Exchange-specific complexity stays in adapters.

### Evaluation before complexity
New technology must prove measurable benefit.

### Traceability
Every important decision should be explainable from source data to final output.

### Fail closed
Missing, stale, malformed, or unreliable data must reduce system authority, not produce fabricated confidence.

### Outcome feedback
Every setup should eventually be judged against what actually happened.

### One coherent system
TraID is its own application, not a collection of copied repositories.

---

# 34. Final TraID Flow

```text
Hyperliquid
↓
Exchange Adapter
↓
Canonical TraID Data
↓
Data Quality + Provenance
↓
Deterministic Market Analytics
↓
Whale Intelligence + Macro + Verified News
↓
Bedrock Evidence Intelligence
↓
Signal Fusion
↓
Typed Strategy Engine
↓
Mandatory Deterministic Risk Gate
↓
TRADE CANDIDATE / NO TRADE
↓
Dashboard
↓
Outcome Tracking
↓
Backtest / Replay / Evaluation
```

---

# 35. Definition of Success

TraID V1 is successful when it is:

- connected to real Hyperliquid data
- able to detect stale/bad data
- calculating real deterministic market analytics
- tracking whale behavior
- consuming macro context
- verifying important news
- using Bedrock for structured evidence analysis
- producing deterministic strategy setups
- applying a mandatory Risk Gate
- backtesting the same strategy logic
- tracking real outcomes
- tested
- containerized
- observable
- deployable
- useful as a real daily market-intelligence application

The resume value comes from building this system correctly.

The primary goal remains:

> **Build a real TraID system first. Portfolio value is the consequence.**
