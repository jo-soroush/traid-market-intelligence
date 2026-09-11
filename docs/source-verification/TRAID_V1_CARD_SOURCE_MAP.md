# TRAID V1 CARD SOURCE MAP

**Date:** 2026-09-03  
**Status:** Pre-implementation source and provenance map  
**Primary roadmap:** `TRAID_V1_ROADMAP.md`  
**Architecture:** `TRAID_FINAL_SYSTEM_BLUEPRINT.md`  
**Traceability baseline:** `TRAID_MASTER_INTEGRATION_TRACEABILITY_PLAN.md`  
**Engineering reference:** `AI_ENGINEERING_PLAYBOOK.md`

---

# 1. Purpose

This file answers one implementation question for every TraID V1 Card:

> **Where should the implementation come from?**

For each Card we define:

```text
SOURCE
→ EXACT FILE / MODULE
→ WHAT TO TAKE
→ WHAT NOT TO TAKE
→ WHAT TRAID BUILDS
→ REQUIRED MODIFICATION
→ VERIFICATION
→ TESTS
```

This is not permission to copy whole repositories.

TraID remains one coherent application.

---

# 2. Classification

Every Card or source component receives one of:

```text
REUSE
ADAPT
REFERENCE ONLY
BUILD
REJECT
```

Meaning:

- **REUSE** — direct reuse may be possible after license and runtime verification.
- **ADAPT** — use the implementation or method, but rewrite/integrate it into TraID contracts.
- **REFERENCE ONLY** — learn from the design/method; do not import the code.
- **BUILD** — TraID owns and implements the component itself.
- **REJECT** — intentionally do not use the source.

---

# 3. Verification Status

Use one of:

```text
SOURCE VERIFIED
SOURCE PARTIALLY VERIFIED
SOURCE FILE NOT YET VERIFIED
LICENSE VERIFIED
LICENSE NOT YET VERIFIED
RUNTIME NOT VERIFIED
TRAID TEST REQUIRED
```

A source being visible on GitHub does not mean its behavior is approved for production.

---

# 4. Governing Rule

For externally-derived work, every implementation Card must preserve:

```text
Decision ID
Card ID
TraID subsystem
Source project
Repository
Source file/module
License
Classification
Why selected
What is adapted
What is rejected
Runtime verification status
Required tests
Final evidence
```

Unknown filenames must never be guessed.

---

# 5. Master Card Source Matrix

| Card | TraID capability | Main source | Exact source | Decision |
|---|---|---|---|---|
| C01 | Repository baseline & harness | TraID + Playbook + good repo patterns | No external production code required | BUILD |
| C02 | Canonical domain models | TraID | No external source should own these | BUILD |
| C03 | Exchange adapter contract | TraID + Project 04/Data Layer ideas | Interface is TraID-owned | BUILD + ADAPT pattern |
| C04 | Hyperliquid adapter | Hyperliquid Analytics Dashboard | `hyperliquid_client.py`, `transport_hyperliquid_sdk.py`, `candle_fetcher.py`, `candle_aggregator.py`, `models.py`, `rate_limit_tracker.py` | ADAPT |
| C05 | Data quality & provenance | Project 04 + CryptoRadar + NEXUS | Project 04 health/freshness modules; CryptoRadar status/fallback patterns; NEXUS checkpoint/status | BUILD + ADAPT |
| C06 | Historical data & replay foundation | Hyperliquid Backtester | `src/hlbt/sync.py`, canonical ideas from `src/hlbt/strategy.py` | ADAPT |
| C07 | Order book & liquidity | Project 04 | `orderbook_metrics.py`, `depth_decay.py`, `slippage_estimator.py` | ADAPT |
| C08 | Trade flow & CVD | Project 04 | `trade_flow_tracker.py` | ADAPT |
| C09 | Derivatives & volatility | Project 04 | `market_indicators.py`, `volatility.py`, `session_context.py`, `price_momentum.py` | ADAPT |
| C10 | Regime/crowding/liquidation | Project 04 + CryptoRadar | `regime_detector.py`, `crowding_detector.py`, `liquidations.py`, CryptoRadar `MarketRegimeService.java` | COMPARE + ADAPT |
| C11 | Whale intelligence | HyperStats methodology | No confirmed public source code | BUILD from methodology |
| C12 | Macro intelligence | NEXUS | API/module structure verified; exact implementation files not fully mapped | ADAPT pattern; source file mapping still required |
| C13 | News verification | TraID | No audited repo meets requirement | BUILD |
| C14 | Bedrock structured intelligence | Quant Flow | `src/agent/`, `src/llm/`, `prompts/`, `tests/test_decision_validator.py`, decision replay under `src/backtest/` verified at directory/test level; exact core files partially unresolved | ADAPT architecture |
| C15 | Signal Fusion | CryptoRadar | `service/SignalEngine.java` | ADAPT method |
| C16 | Typed Strategy Engine | Keel + CryptoRadar | Public repo exposes `keel/`, `pipeline_engine/`; exact compiler/artifact implementation not yet fully verified; CryptoRadar detector package verified | ADAPT architecture + BUILD |
| C17 | Risk Gate | TraID + general risk references | No audited repo provides required TraID gate | BUILD |
| C18 | Backtest Engine | Hyperliquid Backtester | `src/hlbt/backtester.py`, `src/hlbt/strategy.py`, `src/hlbt/sync.py`, `src/hlbt/metrics.py`, `tests/` | ADAPT STRONG |
| C19 | Outcome Tracking | CryptoRadar | `service/OutcomeEvaluator.java`, `service/OutcomeTracker.java`, `repository/SignalOutcomeRepository.java` | ADAPT method |
| C20 | Evaluation Registry | TraID + CryptoRadar/Quant Flow ideas | No single source owns required registry | BUILD |
| C21 | Decision-Support API | TraID + NEXUS API-envelope pattern | NEXUS `{data, meta, error}` pattern; exact route implementation optional | BUILD + ADAPT pattern |
| C22 | Dashboard | HyperStats + Hyper Display + Project 04 + CryptoRadar + Quant Flow | UX references, not one source tree | BUILD UI from patterns |
| C23 | Observability/audit/recovery | TraID + Project 04 + CryptoRadar + NEXUS | health/status/reconnect/outcome/deployment marker patterns | BUILD + ADAPT |
| C24 | Security/secrets | TraID + Playbook + repo hardening patterns | `.gitleaks.toml` from Keel is a reference; source-specific security code not required | BUILD |
| C25 | Docker/CI/release gate | Project 04, Quant Flow, NEXUS, TraID | `Dockerfile`, `docker-compose.yml`, `.github/workflows/` patterns | BUILD + ADAPT |
| C26 | Golden Case | TraID | No external code | BUILD |
| C27 | Documentation/demo | TraID + useful README/demo patterns | Hyperliquid Backtester replay/demo and audited docs as references | BUILD |

---

# 6. Detailed Card Source Decisions

---

## V1-C01 — Repository Baseline & Engineering Harness

### Classification

**BUILD**

### Source basis

Primary:

- `AI_ENGINEERING_PLAYBOOK.md`
- `TRAID_FINAL_SYSTEM_BLUEPRINT.md`
- `TRAID_V1_ROADMAP.md`

Useful external patterns:

- Project 04 FastAPI/Docker structure
- Quant Flow `.github/workflows/`, Docker and test organization
- Keel `AGENTS.md`, `.gitleaks.toml` as engineering-governance references

### Exact external code to copy

**None required.**

### Take

- clear Python package structure
- deterministic configuration
- FastAPI health/status convention
- pytest-first harness
- Docker reproducibility
- CI blocking critical tests
- Claude Code project instructions
- secret scanning

### Reject

- importing another repo skeleton wholesale
- microservice baseline
- Redis baseline
- execution credentials

### TraID owns

Entire repository layout and engineering harness.

### Required tests

- app boot
- `/health`
- config loading
- test discovery
- Docker build
- CI test job

---

## V1-C02 — Canonical Domain Models

### Classification

**BUILD**

### Why

These models define TraID's domain language and must remain vendor-neutral.

### Source references

Project 04 `models.py` can help understand current Hyperliquid event shapes.

NEXUS database model separation may inspire conceptual boundaries.

### Exact code to copy

**None.**

### TraID must build

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

### Reject

- Project 04 provider-specific model ownership in Core
- NEXUS Prisma models as TraID domain model
- arbitrary raw exchange dicts in business logic

### Tests

- validation
- timezone awareness
- serialization round-trip
- numeric constraints
- source identity
- schema version

---

## V1-C03 — Exchange Adapter Contract

### Classification

**BUILD + ADAPT PATTERN**

### Source

Primary inspiration:

Project 04:

```text
hyperliquid_client.py
transport_hyperliquid_sdk.py
```

Secondary:

Hyperliquid Data Layer API endpoint/provider taxonomy.

### Exact reusable concept

Separate:

```text
exchange transport
↓
normalization
↓
core models
```

### TraID must build

An exchange-neutral interface:

```text
connect()
disconnect()
health()
get_trades()
get_orderbook()
get_candles()
get_funding()
get_open_interest()
get_market_context()
```

### Reject

- provider-specific field names in the interface
- MoonDev-hosted dependency as Core contract
- assumption every exchange supports identical capabilities

### Tests

- fake adapter
- capability discovery
- provider error mapping
- no Hyperliquid-specific types in Core interface

---

## V1-C04 — Hyperliquid Provider Verification & Adapter

### Classification

**ADAPT**

### Primary source

**Hyperliquid Analytics Dashboard**  
Repository: `lewbei/hyperliquid-analytics-dashboard`  
License: **Apache-2.0**  
Source visibility: **VERIFIED**  
Runtime in TraID: **NOT VERIFIED**

### Exact files

```text
signal_only/backend/hyperliquid_client.py
signal_only/backend/transport_hyperliquid_sdk.py
signal_only/backend/candle_fetcher.py
signal_only/backend/candle_aggregator.py
signal_only/backend/models.py
signal_only/backend/rate_limit_tracker.py
signal_only/backend/config.py
```

Path prefix may need re-confirmation against current branch before implementation, but module names and backend structure are verified publicly.

### Take

- REST/WS connection approach
- subscription lifecycle
- candle retrieval
- candle aggregation
- Hyperliquid SDK transport separation
- rate-limit tracking idea
- clean asset switching/subscription patterns

### Required TraID changes

- implement TraID `ExchangeAdapter`
- canonical models
- stronger reconnect/backoff
- explicit gap handling
- provenance
- quality state
- structured errors
- provider health
- clean shutdown
- BTC-first validated path

### Reject

- coupling Core directly to this client
- dashboard-specific payload contract
- assuming its reconnect/recovery is production complete
- using its heuristics as authority without tests

### Tests

- real BTC data integration
- mocked REST failure
- WS disconnect/reconnect
- malformed event
- duplicate event
- rate limit
- normalization
- shutdown

---

## V1-C05 — Data Quality, Freshness & Provenance

### Classification

**BUILD + ADAPT**

### Sources

#### Project 04

Verified capabilities:

- Data Quality monitoring
- feed connection status
- module health
- freshness
- rate-limit visibility

Candidate files/components are distributed around:

```text
api_server.py
hyperliquid_client.py
rate_limit_tracker.py
analytics module health logic
```

The precise complete quality contract is not a single source file.

#### CryptoRadar

Verified patterns:

- connection state
- stale state
- WebSocket + REST fallback concepts

#### NEXUS

Verified concepts:

```text
IndexerCheckpoint
GET /api/v1/status
```

Exact source implementation path for these remains partially unresolved.

### TraID builds

```text
LIVE
DELAYED
STALE
UNAVAILABLE
```

with:

```text
source_timestamp
received_timestamp
age
validation_status
gap_status
recovery_status
provenance_id
```

### Important decision

There is **no source we should directly reuse** for this Card.

This is a TraID-owned reliability contract.

### Tests

- freshness boundary values
- stale transitions
- provider unavailable
- malformed data
- gap
- duplicate
- last-good data marked stale
- provenance survives entire pipeline

---

## V1-C06 — Historical Data & Replay Foundation

### Classification

**ADAPT**

### Primary source

**Hyperliquid Backtester**  
Repository: `Crypto-Data-API/hyperliquid-backtester`  
License: **MIT**  
Runtime in TraID: **NOT VERIFIED**

### Exact files

```text
src/hlbt/sync.py
src/hlbt/strategy.py
tests/
```

### Take

From `sync.py`:

- incremental synchronization
- 1-minute source data pattern
- local resampling
- incomplete trailing-bar removal

From `strategy.py`:

- present-only context concept
- structural prevention of future access

### Do not take

- hard dependency on CryptoDataAPI
- its storage contract as TraID's canonical contract

### TraID builds

- source-neutral historical store
- canonical snapshots
- dataset hash/id
- deterministic replay iterator
- explicit gaps

### Tests

- reproducibility
- trailing incomplete bar
- gaps
- duplicate data
- snapshot identity

---

## V1-C07 — Order Book & Liquidity Analytics

### Classification

**ADAPT**

### Primary source

Project 04.

### Exact files

```text
orderbook_metrics.py
depth_decay.py
slippage_estimator.py
```

### Take

- mid/spread calculation
- L1/L5 or multi-level imbalance
- bid/ask depth
- depth decay concept
- book walking
- slippage basis points
- feasibility/liquidity utilization concepts

### TraID changes

- operate only on canonical `OrderBookSnapshot`
- formula names documented
- thresholds externalized/versioned
- stale input blocked/flagged
- numeric invariants enforced

### Reject

- unexplained threshold values
- dashboard-specific output schema
- implicit source assumptions

### Tests

- balanced book
- one-sided book
- thin liquidity
- empty book
- extreme spread
- deterministic book walk
- no negative impossible depth

---

## V1-C08 — Trade Flow & CVD Analytics

### Classification

**ADAPT**

### Primary source

Project 04.

### Exact file

```text
trade_flow_tracker.py
```

### Take

- buy/sell flow windows
- volume ratios
- CVD concept
- sweep detection approach

### TraID changes

- canonical `MarketTrade`
- explicit aggressor-side semantics
- deterministic time windows
- duplicate behavior
- late-event behavior
- restart/state policy

### Tests

Known trade fixtures:

```text
all buys
all sells
balanced sequence
mixed sequence
duplicate sequence
out-of-order sequence
```

Expected CVD must be exact.

---

## V1-C09 — Derivatives & Volatility Analytics

### Classification

**ADAPT**

### Primary source

Project 04.

### Exact files

```text
market_indicators.py
volatility.py
session_context.py
price_momentum.py
```

### Take

- OI
- funding
- basis concepts
- ATR
- realized volatility
- session VWAP
- daily context
- momentum

### TraID changes

- verify Hyperliquid semantics for mark/oracle/mid before basis calculations
- canonical model inputs
- explicit windows
- warm-up status
- quality propagation
- version parameters

### Reject

- hidden defaults
- treating insufficient warm-up as valid
- AI computation of these values

### Tests

- formula fixtures
- warm-up
- missing OI
- missing funding
- stale inputs
- zero-volume VWAP edge case

---

## V1-C10 — Market Regime, Crowding & Liquidation Context

### Classification

**COMPARE + ADAPT**

### Primary source A

Project 04:

```text
regime_detector.py
crowding_detector.py
liquidations.py
```

### Primary source B

CryptoRadar:

```text
services/signal-service/src/main/java/com/cryptoradar/signal/service/MarketRegimeService.java
```

Verified CryptoRadar method:

- 60 daily BTC candles
- 50-day SMA
- 7-day slope
- 2% band
- `BULL / BEAR / CHOP / UNKNOWN`
- refresh around every 15 minutes

### Decision

Do **not** blindly select either regime method.

TraID should compare them and create an interpretable V1 method.

### Take

Project 04:

- broader trend/liquidity/market-condition classification
- crowding
- liquidation context

CryptoRadar:

- simple, auditable macro regime pattern
- regime-dependent downstream threshold idea

### TraID builds

Versioned regime rules.

Initial output may include:

```text
TRENDING_UP
TRENDING_DOWN
RANGE
HIGH_VOLATILITY
UNKNOWN
```

### Tests

- deterministic regimes
- insufficient data → UNKNOWN
- threshold boundaries
- calibration parameters versioned

---

## V1-C11 — Whale Intelligence Foundation

### Classification

**BUILD FROM METHODOLOGY**

### Primary reference

**HyperStats**

### Source code status

**No confirmed public source repository suitable for code reuse.**

### Take

Methodology only:

- Quality + Proof
- realized-first evaluation
- current exposure vs activity window
- notional L/S bias
- bot/noise filtering
- position lifecycle
- Discovery → Verification → Context
- Top Positions UX

### TraID builds

- curated wallet watchlist
- wallet state store
- position lifecycle engine
- realized/unrealized PnL separation
- exposure aggregation
- transparent Smart Money Score

Lifecycle:

```text
OPEN
INCREASE
REDUCE
CLOSE
FLIP
LIQUIDATION
```

### Reject

- hidden HyperStats grade formula
- treating wallet size as skill
- whale signal as direct trade trigger

### Tests

- lifecycle transitions
- PnL accounting
- flip
- partial reduction
- score explainability
- aggregate notional bias

---

## V1-C12 — Macro Intelligence

### Classification

**ADAPT PATTERN + BUILD PROVIDER**

### Primary source

**NEXUS**  
Repository: `oyi77/1ai-nexus`

### Verified public architecture

- `GET /api/v1/macro`
- `GET /api/v1/calendar`
- FRED-backed macro
- Treasury/World Bank context
- central-bank schedules
- standard API envelope
- checkpoint/status concepts

### Exact implementation files

**SOURCE FILE NOT YET FULLY VERIFIED**

The repository tree confirms `src/app/api/` and relevant endpoints, but this source pass did not establish the exact current macro/calendar route filenames and all provider helper paths with enough certainty to approve code adaptation.

### Decision

For C12 Claude Code should not import NEXUS code until those exact files are locally/source verified.

### Take now

Architecture/method:

```text
Provider
↓
Normalize
↓
Checkpoint
↓
Health
↓
MacroEvent
```

### TraID builds

- Python macro provider abstraction
- `MacroEvent`
- primary source metadata
- release schedule/state
- actual/forecast/previous fields
- time normalization
- checkpoint

### V1 priority

```text
FOMC
CPI
PCE
NFP
interest-rate decisions
```

### Reject

- NEXUS whole Next.js stack
- Redis
- multi-chain services
- broad macro surface before core events work

### Tests

- timezones
- duplicate release
- missing actual
- source outage
- stale event state
- checkpoint recovery

---

## V1-C13 — Primary-Source News Verification

### Classification

**BUILD**

### Why

No audited repository provides TraID's required claim-verification system.

### References

Playbook World Event pattern:

```text
Source
→ Ingestion
→ Deduplication
→ Classification
→ Verification
→ Summarization
→ Impact Analysis
```

### Primary sources V1

- Federal Reserve
- BLS
- BEA
- SEC

### TraID builds

```text
Claim
ClaimEvidence
VerificationResult
```

Statuses:

```text
CONFIRMED
PARTIALLY_CONFIRMED
UNVERIFIED
MISLEADING
FALSE
OUTDATED
```

### Do not use

- CryptoRadar news sentiment as fact verification
- NEXUS news feed as authoritative verification
- LLM judgment alone

### Tests

- true claim
- false claim
- partial claim
- outdated claim
- ambiguous claim
- source unavailable
- prompt injection in retrieved content

---

## V1-C14 — Bedrock Provider & Structured Intelligence

### Classification

**ADAPT ARCHITECTURE + BUILD BEDROCK PROVIDER**

### Primary source

**Quant Flow**  
Repository: `web3spreads/quant-flow`

### Verified source areas

```text
src/agent/
src/llm/
src/backtest/
prompts/
tests/
tests/test_decision_validator.py
backtest.py
```

README/source structure verifies:

- structured JSON/typed decisions
- deterministic validation
- separate LLM layer
- decision recording
- deterministic replay that skips the LLM
- dedicated decision-validator tests

### Exact central implementation files

Some filenames inside `src/agent/`, `src/llm/`, and `src/backtest/` are:

**SOURCE FILE NOT YET FULLY VERIFIED**

Do not guess them before implementation.

### Take

- strict structured output
- validation after model output
- provider separation
- prompts outside business logic
- `AI_UNAVAILABLE`
- record/replay model decisions
- deterministic code remains authority

### TraID builds

```text
AIProvider
BedrockProvider
StructuredIntelligence
```

Output:

```text
supporting_factors
contradicting_factors
uncertainty
missing_information
evidence_refs
source_refs
model_metadata
```

### Reject

- Quant Flow BUY/SELL trade authority
- live execution
- Pydantic AI just because Quant Flow uses it
- private keys
- prompts containing financial risk authority

### Tests

- valid output
- malformed output
- timeout
- provider error
- schema mismatch
- replay
- AI cannot alter Risk Gate output

---

## V1-C15 — Evidence Registry & Signal Fusion

### Classification

**ADAPT METHOD + BUILD PYTHON IMPLEMENTATION**

### Primary source

CryptoRadar.

### Exact file

```text
services/signal-service/src/main/java/com/cryptoradar/signal/service/SignalEngine.java
```

### Verified method

- six evidence dimensions
- alignment score
- regime-aware thresholds
- contradiction/alignment concepts
- prior confidence naming was abandoned after outcome evidence showed inverse win-rate correlation

### Take

- evidence dimensions
- explicit alignment
- contradiction
- regime context
- performance-driven calibration

### TraID builds

Python version using canonical `EvidenceItem`.

Output:

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

### Reject

- Java service
- alignment as probability
- Gemini trade authority
- blindly copying weights

### Tests

- deterministic same-input result
- missing evidence
- contradictory evidence
- stale evidence
- regime variation
- no probability wording

---

## V1-C16 — Typed Strategy Engine

### Classification

**ADAPT ARCHITECTURE + BUILD**

### Primary source A

**Keel**  
Repository: `keel-trade/keel-trade`  
License: **MIT**  
Status: **Alpha**

Verified public repository areas:

```text
keel/
pipeline_engine/
tests/
AGENTS.md
```

Verified architecture:

```text
compose
↓
Strategy graph
↓
compile
↓
Deterministic artifact
↓
backtest/live engine
```

Verified design principles:

- typed composition
- versioned components
- compile-time validation
- agent builds strategy
- deterministic engine executes
- same artifact intended for backtest/live parity

### Exact compiler/artifact source files

**SOURCE FILE NOT YET FULLY VERIFIED**

The public mirror confirms directories and architecture, but this pass does not justify naming internal compiler files not directly surfaced.

### Primary source B

CryptoRadar detector package:

```text
services/signal-service/src/main/java/com/cryptoradar/signal/detector/
```

Verified classes/patterns:

```text
TradeSetupDetector
LiquiditySweepDetector
TrendContinuationDetector
```

### Take

From Keel:

- typed strategy definition
- validation before execution
- immutable/versioned artifact concept
- shared strategy logic across evaluation paths

From CryptoRadar:

- modular independent detectors

### TraID builds

Its own:

```text
StrategyDefinition
StrategyArtifact
StrategyValidator
StrategyEvaluator
```

### Reject

- Keel as critical runtime dependency while alpha
- live execution
- dynamic AI-generated strategy logic in trade loop

### Tests

- schema validation
- compile/validation error
- deterministic evaluation
- insufficient evidence
- stale evidence
- versioned artifact
- identical input/version → identical output

---

## V1-C17 — Deterministic Risk Gate

### Classification

**BUILD**

### Source status

No audited repository provides the required non-bypassable TraID gate.

### Reference ideas

- Playbook deterministic risk-control requirement
- useful individual risk patterns in trading projects
- Quant Flow deterministic code boundary
- CryptoRadar's explicit R:R-related concepts

But none becomes the TraID authority.

### TraID builds

Checks at minimum:

```text
freshness
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

Output:

```text
TRADE_CANDIDATE
NO_TRADE
```

Reason codes mandatory.

### Hard rejection

- LLM override
- whale override
- signal-score override
- UI silent override

### Tests

Every single reason code, boundary values, malformed config, replay determinism, stale data.

---

## V1-C18 — Backtest Engine Integration

### Classification

**ADAPT STRONG**

### Primary source

**Hyperliquid Backtester**  
Repository: `Crypto-Data-API/hyperliquid-backtester`  
License: **MIT**

### Exact files

```text
src/hlbt/backtester.py
src/hlbt/strategy.py
src/hlbt/sync.py
src/hlbt/indicators.py
src/hlbt/metrics.py
src/hlbt/demo.py
tests/
```

### Verified important behavior

`backtester.py`:

- bar-by-bar loop
- next-bar-open fills
- fees both legs
- per-bar funding
- leverage-aware liquidation

`strategy.py`:

- strategy Context
- arrays sliced only through current bar
- structural anti-lookahead

`sync.py`:

- incremental sync
- local resampling
- drops partial trailing bar

`metrics.py`:

- profit factor
- expectancy
- Sharpe
- max drawdown
- fees
- funding
- liquidations

Tests:

- lookahead
- fill timing
- costs
- P&L reconciliation
- liquidation

### Take

These engine invariants and implementation methods are high-value.

### TraID changes

- replace provider dependency with canonical TraID history
- same TraID Strategy Artifact
- same TraID Risk Gate
- TraID slippage
- dataset hash
- run/version metadata

### Reject

- hard CryptoDataAPI dependency
- claims of full order-book execution realism
- partial-fill/queue assumptions not modeled

### Tests

All source invariants plus TraID data gaps and Risk Gate parity.

---

## V1-C19 — Outcome Tracking

### Classification

**ADAPT METHOD + BUILD PYTHON IMPLEMENTATION**

### Primary source

CryptoRadar.

### Exact files

```text
services/signal-service/src/main/java/com/cryptoradar/signal/service/OutcomeEvaluator.java
services/signal-service/src/main/java/com/cryptoradar/signal/service/OutcomeTracker.java
services/signal-service/src/main/java/com/cryptoradar/signal/repository/SignalOutcomeRepository.java
```

### Verified behavior

OutcomeEvaluator:

- scheduled evaluation using 1m candles
- MFE/MAE
- time-to-MFE/MAE
- trailing stop state
- final exit reason
- realized R net of round-trip fees
- stagnation handling

OutcomeTracker:

- stores new outcome candidates
- deduplicates per strategy/symbol/direction concept

### Take

- continuous outcome lifecycle
- MFE/MAE
- R-multiple
- reason attribution
- strategy-specific evaluation
- before/after deployment/version comparison concept

### TraID changes

- Python
- TraID strategy/risk versions
- data snapshot hash
- AI/prompt metadata
- source evidence IDs

### Reject

- hard-coded trailing configuration as universal truth
- optimistic same-bar assumptions without explicit policy
- TimescaleDB requirement

### Tests

- MFE
- MAE
- exit ordering policy
- fees
- unresolved state
- version metadata
- deterministic outcome replay

---

## V1-C20 — Evaluation Registry

### Classification

**BUILD**

### Sources

CryptoRadar gives useful evidence:

- outcome metrics
- strategy breakdown
- signal type breakdown
- alignment bucket
- deployment markers

Quant Flow gives:

- model decision record/replay
- validation tests

Hyperliquid Backtester gives:

- run metrics
- reproducible engine invariants

### Exact external code to copy

**None required.**

### TraID builds

A cross-system evaluation registry keyed by:

```text
run_id
dataset_hash
strategy_version
risk_gate_version
analytics_version
fusion_version
AI_model_id
prompt_version
configuration_version
```

### Tests

- run reproducibility
- missing metadata rejection for critical evaluation
- version comparison
- stable metric calculation

---

## V1-C21 — Decision-Support API

### Classification

**BUILD + ADAPT PATTERN**

### Primary reference

NEXUS public API pattern:

```text
{ data, meta, error }
```

and:

```text
GET /api/v1/status
```

Project 04 demonstrates FastAPI + WebSocket analytics delivery.

### Exact code to copy

No need to reuse NEXUS TypeScript routes.

### TraID builds

FastAPI contracts for:

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

Endpoint consolidation is allowed where simpler.

### Reject

- exposing execution endpoints
- coupling API response to source provider
- one giant untyped payload

### Tests

- schema contracts
- degraded responses
- bad requests
- no write/execution capability

---

## V1-C22 — Dashboard

### Classification

**BUILD FROM UX PATTERNS**

### Sources

#### HyperStats

Take:

- whale information hierarchy
- current exposure vs recent activity
- top positions
- token/wallet context

#### Hyper Display

Take:

- compact position-first view
- multi-wallet clarity
- PnL/funding/liquidation emphasis
- read-only UX

#### Project 04

Take:

- Data Quality
- feed status
- module health

#### CryptoRadar

Take:

- regime badge
- outcome ledger
- status indicators
- closed-loop outcome feedback

#### Quant Flow

Take:

- supporting evidence
- contradiction
- uncertainty
- decision visibility

### Exact source code

**REFERENCE ONLY unless a later UI component is separately license/source verified.**

### TraID builds

Entire dashboard composition.

### Reject

- copy entire dashboard
- Tauri
- giant terminal
- every metric on one screen

### Tests

- degraded state obvious
- NO_TRADE reason visible
- provenance reachable
- mobile/responsive basics if practical
- no execution controls

---

## V1-C23 — Observability, Audit & Failure Recovery

### Classification

**BUILD + ADAPT PATTERNS**

### Source patterns

Project 04:

- feed status
- data quality
- module health
- rate limit tracking

CryptoRadar:

- connection/staleness state
- Outcome Tracking
- deployment markers
- service status patterns

NEXUS:

- `/status`
- `IndexerCheckpoint`

Quant Flow:

- model failure tests
- deterministic replay

### Exact external code

No single module should be copied as TraID's observability architecture.

### TraID builds

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

Decision audit:

```text
decision_id
evidence_refs
strategy_version
risk_version
AI metadata
dataset/config version
result
reason codes
```

### Tests

- simulated WS disconnect
- REST outage
- Bedrock outage
- macro/news outage
- process restart
- stale data
- replay after restart where required

---

## V1-C24 — Security & Secrets Hardening

### Classification

**BUILD**

### Sources

`AI_ENGINEERING_PLAYBOOK.md`

Useful repo reference:

Keel:

```text
.gitleaks.toml
```

Quant Flow/NEXUS/Project 04 provide environment/Docker examples, but TraID should define its own least-privilege model.

### TraID builds

- no live trading key requirement
- AWS credentials through standard secure mechanisms
- `.env` exclusion
- secret scanning
- untrusted-content isolation
- prompt-injection tests
- no execution endpoints
- log redaction where needed

### Reject

- copying production secret defaults
- wallet private key architecture
- trading permissions

### Tests

- secret scan
- credential redaction
- malicious external instructions
- invalid input
- permission boundary

---

## V1-C25 — Docker, CI & Release Gate

### Classification

**BUILD + ADAPT DEVOPS PATTERNS**

### Sources

Project 04:

- Docker/Docker Compose
- backend test command

Quant Flow:

```text
Dockerfile
docker-compose.yml
.github/workflows/
pyproject.toml
```

NEXUS:

```text
Dockerfile
docker-compose.yml
.github/workflows/
```

Keel:

```text
pyproject.toml
.gitleaks.toml
```

### TraID builds

Its own minimal:

- Dockerfile
- optional compose
- GitHub Actions
- test/lint/type/security gates

### Release blockers

```text
canonical data tests
financial invariant tests
Risk Gate tests
anti-lookahead
AI fail-closed
security scan
```

### Reject

- 5-service Docker topology
- Redis just for matching another repo
- frontend/backend complexity not required by TraID architecture

---

## V1-C26 — Golden Case End-to-End Validation

### Classification

**BUILD**

### Source

TraID architecture itself.

### External code

None.

### Build

Controlled BTC case spanning:

```text
market data
order book
flow
derivatives
volatility
whale
macro
news
AI
fusion
strategy
risk
outcome
```

### Required trace

```text
Source
→ Canonical Data
→ Quality
→ Analytics
→ Evidence
→ AI
→ Fusion
→ Strategy
→ Risk
→ UI
→ Outcome
→ Evaluation
```

### Tests

Must answer the ten Golden Case questions defined in `TRAID_V1_ROADMAP.md`.

---

## V1-C27 — Documentation & Demo Package

### Classification

**BUILD**

### Source references

Hyperliquid Backtester:

```text
src/hlbt/demo.py
docs/
README.md
```

Useful as a reference for demonstrating replay and making invariants explicit.

All audited repos are references for how to document capabilities and limitations.

### TraID builds

- README
- architecture
- setup
- source map
- strategy contract
- Risk Gate contract
- AI boundary
- data provenance
- backtest methodology
- outcome methodology
- limitations
- demo script

### Critical requirement

Documentation must distinguish:

```text
source-verified
runtime-verified
TraID-implemented
assumption
known limitation
```

---

# 7. Source Project → TraID Card Map

## Project 04 — Hyperliquid Analytics Dashboard

Primary Card contribution:

```text
C03 adapter pattern
C04 Hyperliquid adapter
C05 data health patterns
C07 order book/liquidity
C08 trade flow/CVD
C09 derivatives/volatility
C10 regime/crowding/liquidations
C21 FastAPI/WebSocket delivery pattern
C22 data health UX
C23 operational status
C25 Docker/test patterns
```

This is currently the **largest code-method contributor** to TraID V1.

It is **not** the TraID base repository.

---

## CryptoRadar

Primary contribution:

```text
C05 staleness/fallback ideas
C10 regime comparison
C15 Signal Fusion
C16 detector pattern
C19 Outcome Tracking
C20 evaluation ideas
C22 outcome/status UX
C23 deployment marker/audit ideas
```

We adapt its methods, not its Java/Quarkus architecture.

---

## Hyperliquid Backtester

Primary contribution:

```text
C06 historical/replay principles
C18 backtesting engine
C19 outcome metric references
C20 evaluation metrics
C27 replay/demo reference
```

This is currently the strongest dedicated backtesting source.

---

## HyperStats

Primary contribution:

```text
C11 whale methodology
C22 whale UX
```

No code dependency.

---

## NEXUS

Primary contribution:

```text
C05 checkpoint/status pattern
C12 macro/calendar architecture
C21 API envelope
C23 checkpoint/health
C25 deployment reference
```

Do not import full stack.

---

## Keel

Primary contribution:

```text
C16 typed strategy architecture
C24 secret-scanning reference
C25 packaging/governance reference
```

Architecture is more valuable to TraID than adopting Keel as a dependency.

---

## Quant Flow

Primary contribution:

```text
C14 structured AI boundary
C20 decision replay concept
C22 evidence/uncertainty UX
C23 AI failure/replay patterns
C25 CI/Docker patterns
```

Do not import AI trade authority.

---

## Hyper Display

Primary contribution:

```text
C22 UX only
```

No backend dependency.

---

## Hyperliquid Data Layer API

Possible contribution:

```text
C03 provider taxonomy
C04 conditional endpoint reference
C11 whale discovery ideas
```

Use only if direct Hyperliquid integration leaves a measurable gap.

---

# 8. Cards That Must Be Mainly TraID-Owned

The following Cards should **not** be driven by copying external code:

```text
C01 Repository Harness
C02 Canonical Domain Models
C03 Exchange Adapter Contract
C05 Data Quality Contract
C11 Smart Money implementation
C13 News Verification
C17 Risk Gate
C20 Evaluation Registry
C21 Final API contract
C22 Final Dashboard composition
C23 Audit architecture
C24 Security boundary
C26 Golden Case
C27 Documentation
```

This is deliberate.

These Cards define TraID's architecture, trust, governance, and product identity.

---

# 9. Cards With Strongest Code-Level Adaptation Candidates

Highest-value source-code inspection/adaptation:

## Priority A

```text
C04 — Project 04 Hyperliquid connection
C07 — Project 04 orderbook/liquidity
C08 — Project 04 trade flow
C09 — Project 04 derivatives/volatility
C10 — Project 04 regime/crowding/liquidations
C18 — Hyperliquid Backtester
C19 — CryptoRadar Outcome Tracking
C15 — CryptoRadar Signal Fusion
```

## Priority B

```text
C14 — Quant Flow AI boundary
C16 — Keel typed strategy architecture
C12 — NEXUS macro providers
```

Priority B still needs more exact internal file mapping before any code adaptation.

---

# 10. Mandatory Pre-Code Source Check

Before Claude Code starts a Card classified `ADAPT`:

1. Open exact source file.
2. Confirm current branch/path.
3. Confirm license.
4. Identify exact class/function.
5. Explain algorithm in TraID terms.
6. Identify dependencies.
7. Identify provider/framework coupling.
8. Decide:
   - adapt source;
   - rewrite method;
   - reference only;
   - reject.
9. Define tests before implementation.
10. Record final source provenance in the Card.

No Card should receive a vague instruction such as:

> "Use code from Project 04."

It should instead say something like:

```text
Reference:
lewbei/hyperliquid-analytics-dashboard
signal_only/backend/orderbook_metrics.py

Inspect:
<exact functions after source verification>

Take:
multi-level depth imbalance formula

Rewrite:
accept TraID OrderBookSnapshot
remove dashboard payload coupling
add zero-depth handling
add stale-input guard

Tests:
balanced book
one-sided book
empty book
thin book
known slippage fixture
```

---

# 11. Important License Rule

Current known license states from prior audits/source verification:

```text
Hyperliquid Analytics Dashboard → Apache-2.0
CryptoRadar → MIT
Hyperliquid Backtester → MIT
Keel → MIT
```

For NEXUS and Quant Flow, license must be re-confirmed immediately before any source-code copying/adaptation if the exact code is to be incorporated.

Methodology/architecture learning is separate from copying source code.

Required license notices must be preserved whenever the final reuse mode requires them.

---

# 12. Runtime Verification Rule

At this stage:

```text
SOURCE INSPECTION ≠ RUNTIME APPROVAL
```

We have not approved any external repository as a production dependency merely because its source looks useful.

Runtime verification should be focused on the final selected code-level candidates, not all nine repositories.

Expected runtime-verification shortlist:

```text
1. Hyperliquid Analytics Dashboard selected modules
2. Hyperliquid Backtester
3. CryptoRadar algorithms translated into deterministic fixtures
4. Quant Flow AI-boundary behavior if needed
5. Keel public strategy components only if direct reuse is still considered
6. NEXUS provider functions only if source adaptation saves meaningful work
```

---

# 13. Claude Code Rule for Future Cards

Claude Code should receive only the source references relevant to the active Card.

Do not dump all nine repositories into context.

Example:

```text
C08 Trade Flow

Primary source:
Project 04 / trade_flow_tracker.py

Goal:
Understand its CVD and flow logic.

Do not:
copy dashboard architecture
change other TraID subsystems
add a new framework

Implement:
TraID-native deterministic TradeFlowEngine against canonical MarketTrade

Required:
tests for exact known sequences
```

This keeps context small, decisions traceable, and implementation coherent.

---

# 14. Final Source Strategy

The actual TraID implementation should roughly derive its engineering methods as follows:

```text
Hyperliquid connection
    ← Project 04

Canonical Data + Quality
    ← TraID

Orderbook / CVD / OI / Funding / Volatility / Slippage
    ← Project 04 methods

Whale Intelligence
    ← HyperStats methodology
    ← TraID implementation

Macro
    ← NEXUS provider methodology
    ← TraID Python implementation

News Verification
    ← TraID

AI Boundary
    ← Quant Flow methodology
    ← Bedrock TraID provider

Signal Fusion
    ← CryptoRadar methodology
    ← TraID Python implementation

Strategy Engine
    ← Keel architecture
    ← CryptoRadar detector pattern
    ← TraID implementation

Risk Gate
    ← TraID

Backtest
    ← Hyperliquid Backtester engine methods
    ← TraID integration

Outcome Tracking
    ← CryptoRadar methods
    ← TraID Python implementation

Evaluation
    ← TraID

Dashboard
    ← best UX ideas from all references
    ← TraID implementation
```

---

# 15. Final Decision

TraID V1 does **not** need code from every Card to come from another repository.

The correct implementation strategy is:

> Use external code only where it clearly saves work or provides a stronger proven method.  
> Build TraID-owned contracts and safety-critical logic ourselves.

The most likely real code/method sources are:

```text
Project 04
CryptoRadar
Hyperliquid Backtester
```

The most likely architecture/methodology sources are:

```text
HyperStats
NEXUS
Keel
Quant Flow
Hyper Display
```

And the core capabilities that make the application **TraID** remain ours:

```text
Canonical Data
Data Quality
Provenance
Smart Money Score
News Verification
Bedrock Schema
Strategy Rules
Risk Gate
Evaluation Registry
Final Product Composition
```
