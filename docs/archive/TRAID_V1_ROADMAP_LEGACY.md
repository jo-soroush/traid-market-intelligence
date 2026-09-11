# TRAID V1 ROADMAP

**Date:** 2026-09-03  
**Status:** Implementation roadmap  
**Primary reference:** `TRAID_FINAL_SYSTEM_BLUEPRINT.md`  
**Supporting reference:** `TRAID_MASTER_INTEGRATION_TRACEABILITY_PLAN.md`  
**Engineering reference:** `AI_ENGINEERING_PLAYBOOK.md`  
**Target:** A real, read-only, decision-support TraID V1 that can be built in approximately three focused weeks without sacrificing correctness at the financial and risk boundaries.

---

# 1. V1 Mission

TraID V1 must turn real Hyperliquid market data and verified external evidence into transparent, reproducible trading intelligence.

The system must:

1. ingest real Hyperliquid data;
2. normalize it into TraID-owned schemas;
3. detect stale, missing, malformed, or degraded data;
4. calculate deterministic market analytics;
5. add whale, macro, and verified-news evidence;
6. use Amazon Bedrock only for structured interpretation;
7. fuse evidence without pretending alignment is probability;
8. evaluate typed deterministic strategy rules;
9. pass every candidate through a mandatory deterministic Risk Gate;
10. expose the result in a clean dashboard;
11. replay/backtest the same strategy and risk logic;
12. track what happened after live candidates;
13. retain enough provenance to explain why a result was produced.

TraID V1 is **decision support**.

It does **not** execute live trades.

---

# 2. Non-Negotiable Architecture

```text
Hyperliquid
    ↓
Exchange Adapter
    ↓
Canonical TraID Data
    ↓
Data Quality + Provenance
    ↓
Deterministic Analytics
    ↓
Whale + Macro + Verified News
    ↓
Bedrock Evidence Intelligence
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

No component may bypass the layers beneath it.

In particular:

```text
AI ≠ trade authority
Whale score ≠ trade authority
News ≠ trade authority
Signal alignment ≠ trade authority
Strategy setup ≠ trade authority
```

Only a deterministic Risk Gate may convert a valid setup into:

```text
TRADE_CANDIDATE
```

Otherwise:

```text
NO_TRADE
```

with explicit reason codes.

---

# 3. V1 Scope Freeze

## In V1

- Python backend
- FastAPI
- typed domain models
- Hyperliquid live REST/WebSocket integration
- multi-exchange-ready adapter contract
- BTC as the initial fully validated market path
- canonical market schemas
- data validation
- freshness
- provenance
- gap/degraded-state handling
- deterministic analytics
- basic whale/watchlist intelligence
- core macro events
- primary-source news verification
- Amazon Bedrock provider adapter
- structured AI intelligence
- Signal Fusion
- typed deterministic Strategy Engine
- deterministic Risk Gate
- historical data/replay
- deterministic backtesting
- Outcome Tracking
- evaluation registry
- clean dashboard
- observability
- Docker
- pytest
- GitHub Actions
- local-first execution
- cloud-ready configuration

## Architecture-ready but not implemented as live V1 integrations

- Binance
- Bybit
- OKX
- Coinbase
- Kraken

## Explicitly deferred

- live order execution
- automated trading
- XGBoost
- LightGBM
- LSTM
- CNN
- MLflow
- Model Registry
- automated retraining
- model promotion/rollback
- prediction drift
- multi-agent orchestration
- unnecessary microservices
- Redis unless a measured need appears
- LangChain/LangGraph unless a later requirement proves necessary
- Tauri desktop application
- full NEXUS stack
- hard dependency on audited third-party trading systems

---

# 4. Engineering Rules

## 4.1 One coherent application

External repositories are sources of ideas and selected implementation patterns.

They are not merged into TraID.

## 4.2 TraID owns its core contracts

TraID owns:

- canonical schemas
- adapter interface
- Data Quality contract
- provenance
- Smart Money methodology/score
- News Verification
- Bedrock output schema
- Signal Fusion calibration
- strategy rules
- Risk Gate
- audit trail
- evaluation registry
- final dashboard composition

## 4.3 Deterministic financial authority

Authoritative calculations must be deterministic and testable.

## 4.4 Fail closed

If critical input is:

- stale;
- malformed;
- unavailable;
- contradictory beyond allowed policy;
- missing;
- unverifiable;

the system reduces authority or returns `NO_TRADE`.

It does not manufacture confidence.

## 4.5 Traceability

Any externally derived implementation must record:

```text
Decision ID
TraID subsystem
Source project
Source repository
Source audit
Source section
Source file/module
License
Classification
Why selected
Required modifications
Verification status
Tests required
Final evidence
```

Unknown source files must be recorded as:

```text
SOURCE FILE NOT YET VERIFIED
```

Never guess.

## 4.6 STOP on critical failure

A Card is not COMPLETE if its required tests fail.

Critical failures in:

- data integrity;
- financial formulas;
- strategy determinism;
- Risk Gate;
- backtesting invariants;
- provenance;
- AI fail-closed behavior;

block progression until resolved.

---

# 5. Definition of Card States

Every Card uses one of:

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
COMPLETE
DEFERRED
```

A Card becomes `COMPLETE` only when:

1. implementation matches scope;
2. required tests pass;
3. failure cases are tested;
4. documentation is updated;
5. evidence is recorded;
6. no critical unresolved defect remains;
7. downstream contracts are stable enough for the next Card.

---

# 6. Roadmap Structure

The roadmap is divided into six gates.

```text
GATE A — Foundation & Contracts
GATE B — Trusted Market Data
GATE C — Deterministic Intelligence
GATE D — External Evidence & AI
GATE E — Strategy, Risk & Evaluation
GATE F — Product Integration & Release
```

Cards are numbered in dependency order.

---

# GATE A — FOUNDATION & CONTRACTS

The purpose of Gate A is to create a stable skeleton before market logic is added.

---

## V1-C01 — Repository Baseline & Engineering Harness

**Goal:** Create the controlled TraID application baseline.

### Build

- Python project structure
- FastAPI application skeleton
- configuration layer
- environment separation
- logging baseline
- test structure
- Docker baseline
- GitHub Actions baseline
- project instructions for Claude Code
- architecture/evidence documentation structure

### Suggested top-level shape

```text
traid/
├── app/
│   ├── api/
│   ├── domain/
│   ├── providers/
│   ├── data_quality/
│   ├── analytics/
│   ├── intelligence/
│   ├── signals/
│   ├── strategy/
│   ├── risk/
│   ├── backtest/
│   ├── outcomes/
│   └── observability/
├── tests/
├── docs/
├── scripts/
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Required controls

- no trading credentials required
- secrets excluded from Git
- deterministic configuration loading
- health endpoint
- CI runs tests

### Acceptance

- app starts locally
- `/health` returns healthy state
- test suite runs
- Docker image builds
- CI executes automatically
- no secrets committed

### Dependencies

None.

---

## V1-C02 — Canonical Domain Models

**Goal:** Define the TraID-owned language shared by all later components.

### Core models

```text
MarketTrade
OrderBookLevel
OrderBookSnapshot
Candle
FundingSnapshot
OpenInterestSnapshot
LiquidationEvent
PriceSnapshot
MarketContext
SourceProvenance
DataQualityState
EvidenceItem
```

### Common requirements

- typed
- timezone-aware timestamps
- explicit exchange/source identity
- versionable
- serialization round-trip
- invalid data rejected
- exchange-specific payloads do not leak into Core

### Acceptance

- schema tests pass
- invalid timestamps rejected
- invalid numeric fields rejected where required
- serialization/deserialization tested
- Hyperliquid-specific fields remain in provider layer unless intentionally normalized

### Dependencies

C01.

---

## V1-C03 — Exchange Adapter Contract

**Goal:** Make the Core multi-exchange-ready without implementing multiple exchanges.

### Define capabilities

```text
connect
disconnect
health
get_trades
get_orderbook
get_candles
get_funding
get_open_interest
get_market_context
```

Optional capabilities must be explicit rather than assumed.

### Important design

```text
Exchange payload
↓
Adapter
↓
Canonical TraID model
```

### Acceptance

- adapter interface does not mention Hyperliquid-specific types
- fake/test adapter can satisfy the contract
- capability discovery is explicit
- provider failure maps to controlled TraID errors

### Dependencies

C02.

---

# GATE B — TRUSTED MARKET DATA

No analytics or strategy work should be trusted until the market-data path is reliable.

---

## V1-C04 — Hyperliquid Provider Verification & Adapter

**Goal:** Connect TraID to real Hyperliquid data using the canonical adapter.

### Source inspiration

Primary source candidate:

**Hyperliquid Analytics Dashboard**

Relevant inspected candidates include:

```text
hyperliquid_client.py
transport_hyperliquid_sdk.py
candle_fetcher.py
candle_aggregator.py
models.py
rate_limit_tracker.py
```

### Rule

Use external implementation only after source/license/behavior verification.

### Implement

- REST connectivity
- WebSocket connectivity
- BTC initial path
- trade normalization
- order-book normalization
- candle normalization
- funding/OI/context normalization
- reconnect behavior
- controlled retry/backoff
- rate-limit awareness
- clean shutdown

### Acceptance

- real BTC feed received
- canonical models emitted
- reconnect tested
- malformed payload tested
- API failure tested
- no exchange payload escapes into Core
- rate-limit behavior observable

### Dependencies

C03.

---

## V1-C05 — Data Quality, Freshness & Provenance

**Goal:** Prevent bad data from silently becoming market intelligence.

### States

```text
LIVE
DELAYED
STALE
UNAVAILABLE
```

### Track

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

### Implement

- freshness thresholds by data type
- malformed-data rejection
- missing-data detection
- duplicate detection where relevant
- sequence/gap detection where supported
- degraded mode
- provider health
- provenance IDs
- last-good-state metadata without pretending stale data is live

### Critical rule

Downstream components must be able to ask:

```text
Can this evidence currently be trusted?
```

### Acceptance

Tests prove:

- fresh → LIVE
- delayed → DELAYED
- stale → STALE
- unavailable → UNAVAILABLE
- malformed input rejected
- gap visible
- provenance survives normalization
- downstream consumers receive quality state

### Dependencies

C04.

---

## V1-C06 — Historical Data & Replay Foundation

**Goal:** Establish deterministic historical input before strategy/backtesting is built.

### Implement

- canonical historical candle representation
- funding history where available
- market-context history where available
- incremental local storage
- deduplication
- incomplete trailing-bar removal
- deterministic dataset snapshot ID/hash
- replay iterator

### Important rule

Historical data must use the same canonical domain concepts as live data.

### Acceptance

- same input produces same replay
- duplicates handled
- incomplete bar excluded
- invalid timestamps detected
- dataset snapshot identifiable
- missing periods visible rather than silently filled

### Dependencies

C02, C05.

---

# GATE C — DETERMINISTIC INTELLIGENCE

This gate produces market measurements. No LLM authority is involved.

---

## V1-C07 — Order Book & Liquidity Analytics

**Goal:** Build trustworthy liquidity measurements.

### Source inspiration

Project 04:

```text
orderbook_metrics.py
depth_decay.py
slippage_estimator.py
```

### Implement

- spread
- L1 imbalance
- multi-level imbalance
- depth
- depth concentration
- depth decay
- book-walking slippage estimate
- liquidity quality state

### Tests

- balanced book
- one-sided book
- empty book
- thin book
- extreme spread
- deterministic slippage
- malformed levels

### Acceptance

Financial formula fixtures pass.

### Dependencies

C05.

---

## V1-C08 — Trade Flow & CVD Analytics

**Goal:** Measure aggressive market flow.

### Source inspiration

Project 04:

```text
trade_flow_tracker.py
```

### Implement

- aggressive buy volume
- aggressive sell volume
- net flow
- CVD
- rolling windows
- directional sweep detection where evidence supports it

### Requirements

- window definitions explicit
- reset/restart behavior deterministic
- late/duplicate trade behavior defined

### Acceptance

Known trade sequences produce expected CVD and flow results.

### Dependencies

C05.

---

## V1-C09 — Derivatives & Volatility Analytics

**Goal:** Add deterministic derivatives and volatility context.

### Implement

- OI
- OI change
- funding
- funding extremes
- basis where source semantics support it
- ATR
- realized volatility
- VWAP/session context
- price momentum

### Source inspiration

Project 04:

```text
market_indicators.py
volatility.py
session_context.py
price_momentum.py
```

### Acceptance

- formulas verified against fixed fixtures
- insufficient warm-up handled
- missing OI/funding handled
- stale derivatives data propagated
- no AI-generated calculations

### Dependencies

C05, C06.

---

## V1-C10 — Market Regime, Crowding & Liquidation Context

**Goal:** Create higher-level deterministic market-state evidence.

### Source inspiration

Project 04:

```text
regime_detector.py
crowding_detector.py
liquidations.py
```

CryptoRadar regime methodology may be used as a comparison reference.

### Implement

Initial interpretable states such as:

```text
TRENDING_UP
TRENDING_DOWN
RANGE
HIGH_VOLATILITY
UNKNOWN
```

Crowding/liquidation context remains evidence, not trade authority.

### Important rule

Thresholds are versioned and treated as hypotheses until Outcome Tracking provides calibration evidence.

### Acceptance

- regime rules deterministic
- insufficient data → UNKNOWN
- thresholds stored in configuration/version
- liquidation anomalies visible
- no hidden confidence probability

### Dependencies

C07, C08, C09.

---

# GATE D — EXTERNAL EVIDENCE & AI

This gate enriches deterministic market context without giving AI financial authority.

---

## V1-C11 — Whale Intelligence Foundation

**Goal:** Track a controlled set of Hyperliquid wallets and position behavior.

### V1 scope

Use a curated watchlist.

Do not attempt universal whale discovery in V1.

### Lifecycle

```text
OPEN
INCREASE
REDUCE
CLOSE
FLIP
LIQUIDATION
```

### Track

- wallet ID
- position direction
- size
- notional
- entry
- leverage
- liquidation
- realized PnL
- unrealized PnL
- lifecycle event
- current exposure
- recent activity

### Methodology inspiration

HyperStats:

- Quality + Proof
- realized-first
- current exposure vs activity window
- notional L/S bias
- noise filtering

### Smart Money V1

Use transparent factors only.

Do not reproduce a hidden external grade.

### Acceptance

- lifecycle transitions tested
- wallet snapshot reproducible
- realized vs unrealized separated
- current exposure vs recent activity separated
- score factors explainable
- whale output cannot directly create `TRADE_CANDIDATE`

### Dependencies

C04, C05.

---

## V1-C12 — Macro Intelligence

**Goal:** Provide authoritative macro-event context.

### V1 priority

```text
FOMC
CPI
PCE
NFP
interest-rate decisions
```

### Source architecture inspiration

NEXUS provider/calendar/checkpoint/status patterns.

### Implement

- provider abstraction
- event schema
- scheduled event timestamp
- actual/forecast/previous where available
- source provenance
- freshness
- event importance
- checkpoint/state

### Acceptance

- source recorded
- timezone normalized
- duplicate event handling
- missing values handled
- stale source state visible
- macro evidence cannot bypass Risk Gate

### Dependencies

C02, C05.

---

## V1-C13 — Primary-Source News Verification

**Goal:** Separate market claims from verified facts.

### Initial primary sources

- Federal Reserve
- BLS
- BEA
- SEC

### Pipeline

```text
Claim
↓
Claim Extraction
↓
Primary-Source Search/Match
↓
Timestamp Validation
↓
Fact vs Interpretation
↓
Verification Status
```

### Status

```text
CONFIRMED
PARTIALLY_CONFIRMED
UNVERIFIED
MISLEADING
FALSE
OUTDATED
```

### Required output

- claim
- status
- primary source
- source timestamp
- verification timestamp
- factual evidence
- uncertainty
- provenance

### Security rule

External text is untrusted input.

It cannot issue instructions to TraID or alter system policy.

### Acceptance

Fixtures cover:

- confirmed claim
- false claim
- outdated claim
- partial confirmation
- unavailable primary source
- ambiguous claim

### Dependencies

C02, C05.

---

## V1-C14 — Bedrock Provider & Structured Intelligence

**Goal:** Add AI interpretation behind a strict provider boundary.

### Architecture

```text
TraID Evidence
↓
AI Provider Interface
↓
Amazon Bedrock
↓
Structured Intelligence Schema
```

### Model

A Bedrock-hosted Claude model may be used, but Core must not depend directly on Claude-specific behavior.

### Input

Only structured evidence required for the analysis.

### Output

```text
supporting_factors
contradicting_factors
uncertainty
missing_information
evidence_refs
source_refs
model_metadata
```

### Required controls

- schema validation
- timeout
- retry policy
- model ID recorded
- prompt version recorded
- latency recorded
- cost/usage metadata where available
- malformed response → `AI_UNAVAILABLE`
- provider error → `AI_UNAVAILABLE`

### Inspiration

Quant Flow:

- typed output
- fail closed
- prompt separation
- provider separation
- deterministic replay concept

### Acceptance

Tests cover:

- valid structured output
- malformed output
- timeout
- provider error
- missing evidence
- model response cannot create/override Risk Gate decision

### Dependencies

C11, C12, C13.

---

# GATE E — STRATEGY, RISK & EVALUATION

This is the core decision-support gate.

---

## V1-C15 — Evidence Registry & Signal Fusion

**Goal:** Combine evidence without hiding contradiction or provenance.

### Evidence dimensions may include

```text
orderbook
trade_flow
derivatives
volatility
regime
liquidations
whales
macro
verified_news
AI_interpretation
```

### Output

```text
alignment_score
supporting_evidence
contradicting_evidence
missing_evidence
market_regime
data_quality
evidence_refs
fusion_version
```

### Inspiration

CryptoRadar Signal Engine:

- multi-dimensional fusion
- alignment
- contradiction
- regime-aware thresholds

### Critical rule

`alignment_score` is not a win probability.

### Acceptance

- same evidence → same deterministic fusion result
- contradiction remains visible
- missing evidence remains visible
- stale evidence cannot silently count as fresh support
- every contributing item traceable

### Dependencies

C07-C14.

---

## V1-C16 — Typed Strategy Engine

**Goal:** Evaluate explicit strategy rules rather than prompt-generated decisions.

### Architecture inspiration

Keel:

```text
Strategy Definition
↓
Validation
↓
Typed Strategy Artifact
↓
Deterministic Evaluation
```

CryptoRadar contributes the independent detector pattern.

### V1 strategy scope

Start with **one well-defined BTC strategy family**, not many weak strategies.

The exact financial rules must be explicitly documented and versioned before implementation.

### Output

```text
LONG_SETUP
SHORT_SETUP
NO_SETUP
```

plus:

```text
strategy_id
strategy_version
triggered_rules
failed_rules
required_evidence
timestamp
```

### Acceptance

- strategy deterministic
- configuration validation
- insufficient evidence → NO_SETUP
- stale required evidence → NO_SETUP
- rule fixtures pass
- no Bedrock call inside deterministic rule evaluation

### Dependencies

C15.

---

## V1-C17 — Deterministic Risk Gate

**Goal:** Make unsafe or invalid candidates impossible to promote silently.

### Mandatory checks

At minimum:

```text
data freshness
required evidence
stop validity
risk/reward
leverage
position risk
volatility
liquidity
slippage
abnormal regime
configuration validity
```

### Output

```text
TRADE_CANDIDATE
NO_TRADE
```

with reason codes.

Example:

```text
STALE_DATA
MISSING_EVIDENCE
INVALID_STOP
RISK_REWARD_TOO_LOW
LEVERAGE_TOO_HIGH
VOLATILITY_TOO_HIGH
LIQUIDITY_TOO_LOW
SLIPPAGE_TOO_HIGH
ABNORMAL_REGIME
INVALID_CONFIGURATION
```

### Hard rules

- no AI bypass
- no whale bypass
- no manual UI override that silently changes recorded decision
- every check auditable
- policy/configuration version recorded

### Acceptance

- every rejection path tested
- boundary-value tests
- malformed configuration fails closed
- stale data fails closed
- deterministic replay gives identical decision
- no downstream component can mutate Risk Gate result without creating a new audited decision

### Dependencies

C16.

---

## V1-C18 — Backtest Engine Integration

**Goal:** Replay the same strategy and Risk Gate over historical canonical data.

### Primary inspiration

Hyperliquid Backtester:

```text
src/hlbt/backtester.py
src/hlbt/strategy.py
src/hlbt/sync.py
src/hlbt/metrics.py
tests/
```

### Preserve

- bar-by-bar simulation
- structural anti-lookahead
- next-bar-open execution
- fees
- funding
- liquidation
- P&L reconciliation
- deterministic replay
- incomplete-bar protection
- provider/engine separation

### TraID extensions

- TraID canonical data
- same Strategy Artifact
- same Risk Gate
- slippage model from TraID analytics
- run ID
- dataset hash
- strategy version
- Risk Gate version
- config version
- engine version

### Acceptance

Tests prove:

- no future candle access
- next-bar fill semantics
- fee accounting
- funding accounting
- long liquidation
- short liquidation
- P&L reconciliation
- deterministic rerun
- data-gap behavior
- incomplete-bar exclusion

### Dependencies

C06, C16, C17.

---

## V1-C19 — Outcome Tracking

**Goal:** Measure what happened after every live decision-support candidate.

### Inspiration

CryptoRadar OutcomeEvaluator.

### Track

```text
MFE
MAE
time_to_MFE
time_to_MAE
realized_R
fees
exit_reason
market_regime
alignment_score
strategy_version
risk_gate_version
data_snapshot_hash
AI_model_version
prompt_version
source_evidence_ids
configuration_version
```

### Important distinction

Outcome Tracking evaluates the system.

It does not automatically modify strategy parameters in V1.

### Acceptance

- candidate linked to later outcome
- MFE/MAE fixtures verified
- outcome remains reproducible
- version metadata retained
- unresolved/open outcomes represented explicitly

### Dependencies

C17, C18.

---

## V1-C20 — Evaluation Registry

**Goal:** Make TraID measurable rather than anecdotal.

### Record

#### Data
- gaps
- stale events
- feed availability
- latency

#### Analytics
- formula/invariant results
- reproducibility

#### Strategy
- setup count
- candidate count
- expectancy
- win/loss metrics
- drawdown
- regime breakdown

#### Risk
- rejection count
- rejection reason distribution
- candidate pass rate

#### AI
- structured-output success
- malformed output rate
- timeout rate
- latency
- cost/usage
- source-grounding checks

#### System
- version
- configuration
- dataset
- timestamps

### Acceptance

One evaluation run can answer:

> Which version produced this result, on which data, under which configuration, and how did it perform?

### Dependencies

C18, C19.

---

# GATE F — PRODUCT INTEGRATION & RELEASE

---

## V1-C21 — Decision-Support API

**Goal:** Expose stable application-level contracts to the UI.

### API areas

```text
/status
/market
/analytics
/whales
/macro
/news
/intelligence
/signals
/strategy
/risk
/outcomes
/evaluations
```

Exact endpoint design may be consolidated where simpler.

### Requirements

- typed responses
- consistent error envelope
- provenance included where useful
- health/degraded state
- no execution endpoint
- no secret leakage

### Acceptance

- contract tests
- degraded-state tests
- invalid request tests
- read-only boundary verified

### Dependencies

C05-C20.

---

## V1-C22 — Dashboard

**Goal:** Make TraID useful during real daily market analysis.

### Main-screen question

The UI must answer:

> What is happening?  
> What changed?  
> What is risky?  
> What deserves inspection?

### Main view

Keep it compact.

Candidate sections:

```text
Market Overview
Data Quality
Market Regime
Key Analytics
Whale Activity
Macro Events
Verified News
Evidence Alignment
Strategy Status
Risk Gate Status
```

### Progressive disclosure

Detailed information opens in dedicated panels/pages.

Do not create a giant terminal containing every metric simultaneously.

### Required visibility

- feed status
- stale/degraded warnings
- supporting evidence
- contradictory evidence
- uncertainty
- Risk Gate rejection reasons
- source/provenance access
- outcome history

### UX inspirations

- HyperStats → whale hierarchy/context
- Hyper Display → position-first clarity
- CryptoRadar → outcome/status patterns
- Project 04 → data-health visibility
- Quant Flow → evidence/contradiction visibility

### Acceptance

A user can understand the current BTC state without reading logs or raw JSON.

### Dependencies

C21.

---

## V1-C23 — Observability, Audit & Failure Recovery

**Goal:** Make failures visible and explainable.

### Observe

```text
API latency
WebSocket state
reconnect count
feed gaps
data age
rate-limit events
provider failures
AI failures
AI latency
AI usage/cost
strategy decisions
Risk Gate decisions
Risk Gate reason codes
backtest runs
system errors
```

### Audit trail

For important decisions retain:

```text
decision_id
timestamp
input evidence refs
strategy version
risk version
AI metadata
data snapshot
configuration version
output
reason codes
```

### Recovery

Define behavior for:

- WebSocket disconnect
- REST outage
- Bedrock outage
- macro/news source outage
- process restart
- corrupted historical input
- stale market feed

### Acceptance

Operational failure can be diagnosed from system evidence without guessing.

### Dependencies

C04-C22.

---

## V1-C24 — Security & Secrets Hardening

**Goal:** Keep the read-only intelligence application safe.

### Controls

- no exchange private key required for V1 market intelligence
- least privilege
- `.env` excluded from source control
- AWS credentials handled through appropriate environment/profile/role mechanisms
- secret scanning
- input validation
- external news/web content treated as untrusted
- AI cannot interpret retrieved instructions as system authority
- no live execution capability

### Acceptance

- repository secret scan clean
- no secrets in logs
- no execution endpoint
- prompt-injection test fixtures for external content
- malformed external input cannot alter policy

### Dependencies

C13, C14, C21.

---

## V1-C25 — Docker, CI & Release Gate

**Goal:** Produce a reproducible V1 candidate.

### CI

At minimum:

- tests
- lint
- type checks
- critical financial tests
- Risk Gate tests
- backtest invariants
- Docker build

### Release blockers

Any failure in:

```text
canonical data integrity
financial formula tests
anti-lookahead tests
Risk Gate tests
AI fail-closed tests
security checks
```

blocks release.

### Acceptance

- clean checkout can build
- Docker starts application
- CI green
- documented environment variables
- local startup documented
- health/status works
- no hidden manual setup required beyond documented credentials/config

### Dependencies

C01-C24.

---

## V1-C26 — Golden Case End-to-End Validation

**Goal:** Prove TraID works as one system, not only as isolated modules.

### Golden Case

Use a controlled BTC scenario containing:

- market data
- order book
- trade flow
- derivatives
- volatility
- whale evidence
- macro event
- news claim
- Bedrock evidence analysis
- Signal Fusion
- strategy evaluation
- Risk Gate decision
- later outcome

### Validate

```text
Source
↓
Canonical Data
↓
Quality
↓
Analytics
↓
Evidence
↓
AI Interpretation
↓
Signal Fusion
↓
Strategy
↓
Risk Gate
↓
Dashboard
↓
Outcome
↓
Evaluation
```

### Required proof

For the final displayed decision, TraID must answer:

1. What data was used?
2. Was it fresh?
3. Which evidence supported the setup?
4. Which evidence contradicted it?
5. What did AI contribute?
6. What deterministic strategy rules fired?
7. Which Risk Gate checks passed or failed?
8. What versions were active?
9. What happened afterward?
10. Can the result be replayed?

### Acceptance

All ten questions are answerable from stored system evidence.

### Dependencies

C25.

---

## V1-C27 — V1 Documentation & Demo Package

**Goal:** Make V1 understandable, reproducible, and demonstrable.

### Documentation

- architecture
- setup
- configuration
- data sources
- provider boundaries
- strategy contract
- Risk Gate contract
- AI boundary
- known limitations
- testing
- backtesting methodology
- outcome methodology
- security
- observability
- demo flow

### Demo

A short demo should show:

1. live BTC feed;
2. Data Quality;
3. analytics;
4. whale/macro/news evidence;
5. Bedrock structured interpretation;
6. Signal Fusion;
7. strategy status;
8. Risk Gate;
9. historical replay/backtest;
10. Outcome Tracking.

### Acceptance

A new developer can set up, run, verify, and understand V1 using the repository documentation.

### Dependencies

C26.

---

# 7. Dependency Chain

The critical path is:

```text
C01
↓
C02
↓
C03
↓
C04
↓
C05
├─────────────┬───────────────┐
↓             ↓               ↓
C06        C07-C10          C11-C13
│             │               │
│             └──────┬────────┘
│                    ↓
│                   C14
│                    ↓
└──────────────→    C15
                     ↓
                    C16
                     ↓
                    C17
                     ↓
                    C18
                     ↓
                    C19
                     ↓
                    C20
                     ↓
                    C21
                     ↓
                    C22
                     ↓
                 C23-C24
                     ↓
                    C25
                     ↓
                    C26
                     ↓
                    C27
```

---

# 8. Three-Week Execution Plan

This is a planning target, not permission to skip failed gates.

## Week 1 — Trusted Data + Deterministic Analytics

Primary target:

```text
C01-C10
```

Expected result by end of Week 1:

- TraID application skeleton
- canonical domain model
- provider abstraction
- real Hyperliquid BTC data
- freshness/provenance
- historical/replay foundation
- order-book analytics
- CVD/trade flow
- OI/funding/volatility
- regime/crowding/liquidation context

**Week 1 success test:**

TraID can receive BTC market data and explain whether the data is trustworthy and what the deterministic market state is.

---

## Week 2 — Evidence + Strategy + Risk

Primary target:

```text
C11-C17
```

Expected result:

- whale watchlist intelligence
- core macro context
- primary-source news verification
- Bedrock structured intelligence
- Signal Fusion
- one typed BTC strategy family
- deterministic Risk Gate

**Week 2 success test:**

TraID can turn trusted market/external evidence into a transparent setup and then independently approve/reject it through deterministic risk rules.

---

## Week 3 — Evaluation + Product + Release

Primary target:

```text
C18-C27
```

Expected result:

- backtest/replay
- Outcome Tracking
- Evaluation Registry
- application API
- dashboard
- observability
- security hardening
- CI/Docker release gate
- Golden Case
- final documentation/demo

**Week 3 success test:**

TraID can run as a coherent read-only market-intelligence application and explain, replay, evaluate, and display its decisions.

---

# 9. Scope Protection Under Time Pressure

If schedule pressure appears, do **not** weaken the Core.

## Must survive

These are P0:

```text
C01-C10
C15-C18
C21
C23
C25-C26
```

Specifically never cut:

- canonical data
- Data Quality
- deterministic analytics
- strategy determinism
- Risk Gate
- anti-lookahead
- backtest invariants
- observability of critical failures
- Golden Case traceability

## May be reduced in breadth, not falsified

These are P1:

```text
Whale Intelligence
Macro breadth
News source breadth
Bedrock sophistication
Outcome UI depth
Dashboard polish
```

Examples of acceptable scope reduction:

- 5 curated whales instead of universal discovery;
- 4 authoritative macro event types instead of broad macro coverage;
- Federal Reserve/BLS/BEA/SEC verification instead of dozens of news providers;
- one Bedrock structured analysis task instead of multiple AI agents;
- one strong BTC strategy instead of five strategies.

## Defer first

These are P2:

- extra exchanges
- extra assets
- complex alerts
- advanced visualizations
- broad wallet discovery
- cross-chain intelligence
- ML/MLOps
- automated strategy optimization
- live execution

---

# 10. V1 Quality Gates

V1 is not complete merely because the UI works.

## Gate 1 — Data Trust

Must prove:

- normalization
- freshness
- provenance
- failure visibility
- reconnect behavior

## Gate 2 — Financial Correctness

Must prove:

- formulas
- deterministic calculations
- accounting invariants
- reproducibility

## Gate 3 — AI Boundary

Must prove:

- structured output
- schema validation
- fail closed
- no trade authority

## Gate 4 — Strategy & Risk

Must prove:

- deterministic strategy
- explicit rules
- deterministic Risk Gate
- no bypass

## Gate 5 — Backtest Integrity

Must prove:

- anti-lookahead
- fill timing
- fees
- funding
- liquidation
- P&L reconciliation

## Gate 6 — End-to-End Traceability

Must prove:

```text
source → evidence → strategy → risk → result → outcome
```

---

# 11. Testing Strategy

## Unit tests

For:

- schemas
- validators
- formulas
- state transitions
- strategy rules
- Risk Gate rules
- verification classification

## Integration tests

For:

- Hyperliquid adapter
- Data Quality pipeline
- analytics pipeline
- Bedrock boundary
- API contracts

## Failure tests

For:

- disconnect
- timeout
- malformed payload
- stale data
- missing data
- rate limit
- malformed AI output
- provider outage

## Financial invariant tests

For:

- CVD
- slippage
- P&L
- fees
- funding
- liquidation
- MFE/MAE

## Replay/regression tests

For:

- strategy version
- Risk Gate version
- Golden Case
- historical deterministic results

---

# 12. Observability Contract

Every critical subsystem should expose:

```text
status
last_success
last_failure
latency
error_count
data_age
source
version
```

Critical events should include correlation IDs where practical.

Important decision records should be reconstructable.

---

# 13. Configuration & Versioning

Version at minimum:

```text
canonical_schema_version
analytics_version
whale_score_version
news_verification_version
prompt_version
AI_model_id
signal_fusion_version
strategy_version
risk_gate_version
backtest_engine_version
configuration_version
```

A result without its relevant versions is incomplete evidence.

---

# 14. V1 Data Authority Hierarchy

When sources disagree:

1. authoritative primary source for macro/regulatory facts;
2. direct exchange data for exchange market state;
3. deterministic TraID calculation;
4. verified external evidence;
5. AI interpretation.

AI interpretation is never the authoritative source for a factual numeric market value.

---

# 15. Failure Philosophy

Examples:

```text
Hyperliquid WebSocket down
→ reconnect / REST fallback where valid
→ mark degraded state
→ never pretend LIVE

Bedrock unavailable
→ AI_UNAVAILABLE
→ deterministic components remain usable

News source unavailable
→ UNVERIFIED / source unavailable
→ do not promote claim to fact

Required market evidence stale
→ strategy NO_SETUP or Risk Gate NO_TRADE

Invalid Risk configuration
→ NO_TRADE
```

---

# 16. External-Code Adoption Gate

Before adapting code from an audited repository:

1. verify exact source file;
2. verify license;
3. understand formula/behavior;
4. compare with official exchange semantics where relevant;
5. isolate the useful method;
6. remove provider/framework coupling;
7. implement TraID contract;
8. add TraID tests;
9. record provenance.

No whole-repository adoption is planned.

---

# 17. Architecture Decisions Frozen for V1

The following are frozen unless evidence forces a change:

- Python/FastAPI backend
- one coherent application
- Hyperliquid live provider first
- multi-exchange-ready adapter contract
- TraID-owned canonical schemas
- deterministic analytics
- Bedrock behind provider abstraction
- AI for interpretation only
- deterministic Signal Fusion
- typed deterministic Strategy Engine
- mandatory deterministic Risk Gate
- same strategy/risk concepts for live decision support and backtest
- read-only V1
- local-first/cloud-ready
- no predictive ML in V1

Changing one of these requires an explicit architecture decision with justification and impact analysis.

---

# 18. V1 Completion Definition

TraID V1 is COMPLETE only when all of the following are true:

- [ ] Real Hyperliquid BTC data is ingested.
- [ ] Data is normalized into TraID schemas.
- [ ] Freshness and provenance are visible.
- [ ] Data failures degrade safely.
- [ ] Core deterministic analytics are working.
- [ ] Whale evidence is available from a controlled watchlist.
- [ ] Core macro events are available.
- [ ] Important claims can be verified against primary sources.
- [ ] Bedrock returns validated structured intelligence.
- [ ] AI failure is safe.
- [ ] Signal Fusion exposes support and contradiction.
- [ ] One BTC strategy family is deterministic and versioned.
- [ ] Risk Gate is deterministic and non-bypassable.
- [ ] Historical replay uses canonical data.
- [ ] Backtest prevents lookahead.
- [ ] Fees/funding/liquidation are tested.
- [ ] Outcome Tracking records MFE/MAE and relevant versions.
- [ ] Evaluation Registry records reproducible runs.
- [ ] Dashboard exposes current state and risk clearly.
- [ ] Critical operational failures are observable.
- [ ] Docker build works.
- [ ] CI is green.
- [ ] Golden Case passes end-to-end.
- [ ] Documentation allows another developer to run and verify V1.
- [ ] No live trade execution exists.

---

# 19. Final Build Order

```text
C01 Repository Baseline & Harness
C02 Canonical Domain Models
C03 Exchange Adapter Contract
C04 Hyperliquid Adapter
C05 Data Quality + Provenance
C06 Historical Data + Replay
C07 Order Book + Liquidity
C08 Trade Flow + CVD
C09 Derivatives + Volatility
C10 Regime + Crowding + Liquidations
C11 Whale Intelligence
C12 Macro Intelligence
C13 News Verification
C14 Bedrock Intelligence
C15 Signal Fusion
C16 Typed Strategy Engine
C17 Deterministic Risk Gate
C18 Backtest Engine
C19 Outcome Tracking
C20 Evaluation Registry
C21 Decision-Support API
C22 Dashboard
C23 Observability + Audit + Recovery
C24 Security + Secrets
C25 Docker + CI + Release Gate
C26 Golden Case
C27 Documentation + Demo
```

---

# 20. Final Roadmap Principle

The objective is not to complete the largest number of features.

The objective is to finish a **trustworthy vertical slice**:

```text
REAL DATA
→ TRUSTED DATA
→ DETERMINISTIC ANALYTICS
→ VERIFIED EVIDENCE
→ CONTROLLED AI
→ EXPLICIT STRATEGY
→ DETERMINISTIC RISK
→ REPRODUCIBLE EVALUATION
→ USEFUL PRODUCT
```

If a feature does not materially improve that chain, it does not belong in TraID V1.
