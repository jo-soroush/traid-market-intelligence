# PROJECT_PROFILE.md — TraID

## 0. Role of This File

`PROJECT_PROFILE.md` defines the stable project-specific facts, boundaries, architecture, risk posture, and engineering constraints for TraID.

It answers:

```text
What are we building?
Why does it exist?
What is V1?
What is not V1?
What architecture is approved?
What must remain deterministic?
What may AI do?
Which providers are in scope?
What data must be trusted?
What are the critical invariants?
What technologies are currently justified?
What evidence is required before V1 is credible?
```

This file is not:

- the live project-state tracker;
- the Card execution procedure;
- the Card evidence log;
- a replacement for repository reality;
- permission to start a Card;
- permission to change architecture.

Current execution state belongs in `PROJECT_CONTROL.md`.

Card scope and order belong in `TRAID_V1_ROADMAP.md` and `TRAID_CARD_SPECIFICATIONS.md`.

Verified implementation proof belongs in `TRAID_CARD_EVIDENCE_MAP.md`.

---

## 1. Project Identity

```text
Project: TraID
Version Target: V1
System Type: Crypto market intelligence and decision-support platform
Primary V1 Market: BTC
Primary V1 Live Exchange: Hyperliquid
Operating Posture: Local-first, cloud-ready
Coding-Agent Posture: Tool-neutral
Decision Posture: Human-in-the-loop
Execution Posture: Read-only decision support
Live Trade Execution: NOT IN V1
```

TraID is designed as a serious engineering and portfolio project, not a demo that merely produces trading-looking output.

Its credibility depends on traceability, reproducibility, financial correctness, explicit uncertainty, and evidence.

---

## 2. Mission

TraID transforms real market data and external evidence into controlled, traceable, reproducible decision support.

Approved V1 flow:

```text
REAL DATA
→ TRUSTED DATA
→ DETERMINISTIC ANALYTICS
→ VERIFIED EVIDENCE
→ CONTROLLED AI
→ SIGNAL FUSION
→ TYPED DETERMINISTIC STRATEGY
→ MANDATORY DETERMINISTIC RISK GATE
→ HUMAN DECISION SUPPORT
→ OUTCOME TRACKING
→ BACKTEST / REPLAY
→ EVALUATION
```

The system should help a human understand:

- what happened;
- what evidence exists;
- which evidence supports a setup;
- which evidence contradicts it;
- how fresh and trustworthy the inputs are;
- what deterministic strategy conditions are satisfied;
- why the Risk Gate accepts or rejects a candidate;
- what happened after the decision;
- whether the same reasoning can be reproduced later.

---

## 3. Product Principle

TraID is not an autonomous trader.

It is an evidence and decision-support system.

The product principle is:

```text
AI may improve interpretation.
AI does not receive final financial authority.
```

An additional product principle is:

```text
Maximum Relevant Market Coverage + Explicit Coverage Gaps
```

TraID seeks the broadest justified coverage of market evidence relevant to
human decision support, not arbitrary data accumulation. Relevant categories
may include market, derivatives, liquidity, trade-flow, volatility, whale,
macro, verified news, asset-specific ETF, institutional/flow, on-chain,
sentiment, regulatory, exchange/system events, and future categories only when actual decision value
justifies them. In V1, maximum coverage means maximum justified coverage
within the approved Roadmap, technical and legal access, licensing,
reliability, cost, and other explicit constraints; it does not imply
universal or global market awareness.

### Asset-Specific ETF Intelligence

When a selected asset has relevant ETF products, ETF intelligence is part of
that asset's relevant market-evidence coverage. Applicability is determined by
an explicit asset-to-ETF coverage mapping or equivalent metadata; ETF coverage
is not hardcoded only to BTC or ETH. Relevant evidence may include authoritative
regulatory, filing, approval/rejection, issuer, and exchange/listing events, as
well as validated ETF inflow/outflow, AUM, and volume data when available.

ETF evidence retains source, event/data timestamp, freshness, availability,
provenance, and verification status. If ETF coverage is relevant but evidence
is unavailable, stale, delayed, incomplete, unverified, or unsupported by the
approved provider set, the coverage gap remains explicit. Missing ETF evidence
is not zero, neutral evidence, bullish evidence, bearish evidence, or evidence
that no event occurred. No directional inference may be made solely from the
gap. ETF evidence follows the same Evidence Registry → Signal Fusion → typed
Strategy → deterministic Risk Gate path as other evidence.

Every source and category retains provenance and a quality state. Missing,
stale, delayed, unavailable, incomplete, or unverified relevant evidence stays
visible as part of decision context and may reduce decision readiness. The
system must never claim complete market awareness when relevant coverage is
incomplete, and absence of evidence is not directional evidence. The existing
evidence-authority hierarchy, analytical-only AI boundary, deterministic
Strategy/Risk boundaries, non-bypassable Risk Gate, and human final authority
remain unchanged.

Human judgment remains final.

Deterministic software owns consequential financial controls.

---

## 4. V1 Goals

V1 should establish a coherent path for:

```text
Hyperliquid BTC market ingestion
exchange-neutral canonical market models
explicit Data Quality
source provenance
historical data/replay foundation
order-book and liquidity analytics
trade-flow and CVD analytics
derivatives and volatility analytics
market-regime/crowding/liquidation context
Whale Intelligence
Macro Intelligence
primary-source News Verification
structured Bedrock Intelligence
Evidence Registry
Signal Fusion
typed deterministic Strategy Engine
non-bypassable deterministic Risk Gate
backtest integration
Outcome Tracking
Evaluation Registry
read-only Decision-Support API
usable Dashboard
observability/audit/recovery
security and secrets hardening
Docker and CI release gates
Golden Case end-to-end validation
developer and demo documentation
```

V1 is complete only when the approved Roadmap Exit Gates are actually evidenced.

---

## 5. V1 Non-Goals

V1 does not include:

```text
live order execution
autonomous trading
order placement/modification/cancellation
exchange trading credentials
wallet private-key management
custody
AI trade authorization
AI override of deterministic risk
AI-authoritative leverage selection
AI-authoritative position sizing
full live multi-exchange implementation
high-frequency trading
exchange-perfect execution simulation
institutional OMS/EMS
portfolio-management platform
copy trading
social trading
custom multi-agent framework
custom MCP infrastructure
custom strategy DSL without demonstrated need
ML added only for portfolio optics
```

Future capability must not be smuggled into V1 through unrelated Cards.

---

## 6. Human Authority

The human user retains final trading judgment.

TraID may:

```text
retrieve
normalize
validate
calculate
verify
compare
summarize
surface contradictions
measure uncertainty
evaluate deterministic strategy conditions
reject unsafe/incomplete candidates
track outcomes
replay historical decisions
evaluate system behavior
```

TraID V1 may not autonomously:

```text
place
modify
cancel
route
or execute
```

a trade.

---

## 7. Approved Core Architecture

```text
Market Data Sources
├── Hyperliquid          ← V1 live implementation
├── Binance              ← future adapter
├── Bybit                ← future adapter
├── OKX                  ← future adapter
├── Coinbase             ← future adapter
└── Kraken               ← future adapter
        ↓
Exchange Adapters
        ↓
Canonical TraID Data
        ↓
Data Quality + Provenance
        ↓
Deterministic Analytics
        ↓
External Intelligence
├── Whale Intelligence
├── Macro Intelligence
└── Verified News
        ↓
Controlled AI Provider Boundary
└── Amazon Bedrock in V1
        ↓
Evidence Registry
        ↓
Signal Fusion
        ↓
Typed Deterministic Strategy Engine
        ↓
Mandatory Deterministic Risk Gate
        ↓
Read-only Decision Support
├── API
├── Dashboard
├── Outcome Tracking
└── Backtest / Replay
        ↓
Evaluation + Observability + Audit
```

The architecture must remain modular enough to replace providers without rewriting Core domain logic.

---

## 8. Architecture Ownership

Stable ownership boundaries:

```text
providers/adapters
→ transport and provider-specific semantics

domain/core contracts
→ TraID-owned canonical data and typed artifacts

data quality/provenance
→ trust state and origin

analytics
→ deterministic financial/market calculations

external intelligence
→ whale, macro, verified news, and asset-specific ETF evidence

AI provider boundary
→ structured interpretation, never deterministic financial authority

Evidence Registry
→ evidence identity and traceability

Signal Fusion
→ support, contradiction, alignment, uncertainty

Strategy Engine
→ typed deterministic strategy evaluation

Risk Gate
→ mandatory deterministic acceptance/rejection

API/UI
→ read-only presentation and access

backtest/replay
→ historical deterministic execution/evaluation context

outcomes
→ what happened after the original decision

evaluation
→ measured quality, regression, reproducibility

observability/audit
→ traceability, failures, recovery, versions
```

Do not create duplicate owners for the same responsibility.

---

## 9. Provider Isolation

Provider-specific details must remain behind adapters.

Core must not depend directly on:

- Hyperliquid response dictionaries;
- Hyperliquid-specific field names;
- Bedrock-specific response objects;
- another repository's internal models;
- frontend/API transport models.

Preferred dependency direction:

```text
Application / Product
→ TraID Domain Logic
→ Provider Contracts
→ Provider Adapters
→ External Service
```

This supports vendor flexibility and future exchange/provider replacement.

---

## 10. Canonical Market/Data Boundary

Planned canonical entities include:

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

Exact schemas are owned by their Card and must not be invented early.

Canonical models should preserve enough information to determine, where applicable:

```text
exchange/provider
source
source identifier
source timestamp
received timestamp
age/freshness
validation status
gap status
recovery status
schema/version
```

No provider-specific response object may become the Core domain model.

---

## 11. Hyperliquid V1 Provider Strategy

Hyperliquid is the only live exchange implementation required for V1.

The Hyperliquid boundary must isolate and verify:

```text
transport behavior
WebSocket behavior
REST behavior
payload schemas
rate limits
timestamps
candle semantics
trade-side semantics
order-book semantics
funding semantics
mark/oracle/mid semantics
open-interest semantics
liquidation semantics
historical-data constraints
disconnect/recovery behavior
```

Provider failure, rate limiting, disconnects, gaps, and stale data must remain observable.

Future exchange adapters must reuse canonical contracts rather than force Hyperliquid semantics into Core.

---

## 12. Historical Data Strategy

Historical/replay data is part of V1 because TraID must be evaluable, not merely live-looking.

For BTC, historical sources may include verified official/provider data such as:

```text
Hyperliquid official archive
Hyperliquid historical API capabilities
other approved sources when a Card explicitly verifies them
```

Historical data must preserve:

```text
source
coverage
time range
timestamp semantics
gaps
publication/availability limitations
normalization version
dataset identity/version where feasible
```

An archive is not assumed complete merely because it is official.

---

## 13. Data Quality Contract

Canonical quality states:

```text
LIVE
DELAYED
STALE
UNAVAILABLE
```

Data quality is part of decision context, not an implementation detail.

Rules:

- freshness thresholds are explicit and data-type-specific;
- stale required data cannot silently become `LIVE`;
- delayed data remains distinguishable from live;
- unavailable data is not silently converted to zero;
- recovered/backfilled data retains gap/recovery evidence;
- critical consumers define behavior for degraded states;
- timestamp semantics must be verified before trusted use.

---

## 14. Provenance Contract

Consequential data/evidence should be traceable to origin.

Required concepts, where applicable:

```text
source
provider/exchange
source identifier
source timestamp
received timestamp
validation status
quality state
gap/recovery status
schema/version
evidence reference
```

External-source adaptation additionally tracks:

```text
source project
repository
commit/tag/branch
exact file
exact symbol
license
classification
runtime status
TraID modification
```

Unknown exact source is recorded as:

```text
SOURCE FILE NOT YET VERIFIED
```

Never guess provenance.

---

## 15. Deterministic Analytics Boundary

Financially material calculations belong in deterministic software.

Examples:

```text
order-book/liquidity metrics
depth
imbalance
slippage
trade flow
CVD
open-interest analytics
funding calculations
basis
volatility
regime inputs
crowding metrics
liquidation context calculations
strategy rules
risk rules
backtest accounting
Outcome Tracking metrics
```

Every financially material formula must have verified:

```text
units
sign conventions
timestamp semantics
provider semantics
edge cases
failure behavior
tests
```

External implementations are evidence/adaptation sources, not automatic truth.

---

## 16. Liquidation Semantics

TraID must distinguish:

```text
AUTHORITATIVE_LIQUIDATION_EVENT
HEURISTIC_LIQUIDATION_PRESSURE
UNKNOWN
```

Never conflate:

- authoritative liquidation event;
- large aggressive trade;
- cascade heuristic;
- suspected forced flow;
- liquidation-pressure estimate.

Heuristic evidence may be useful.

It must remain labeled as heuristic.

---

## 17. Whale Intelligence

V1 Whale Intelligence should support transparent BTC wallet/position evidence.

Initial direction:

```text
curated wallet/watchlist inputs
→ normalized wallet/position state
→ deterministic lifecycle events
→ transparent Smart Money methodology
→ aggregate whale evidence
→ Signal Fusion
```

Lifecycle concepts include:

```text
OPEN
INCREASE
REDUCE
CLOSE
FLIP
LIQUIDATION
```

Rules:

- large wallet != smart money;
- wallet/source provenance is retained;
- score methodology is transparent and versioned;
- hidden grade formulas are rejected;
- whale evidence cannot bypass Strategy or Risk.

---

## 18. Macro Intelligence

Macro Intelligence should convert relevant economic/central-bank evidence into traceable structured context.

V1 should preserve, where relevant:

```text
indicator/event identity
period
actual
consensus
previous
revision
release time
source
unit
verification status
```

High-impact macro facts should prefer authoritative sources.

Macro context is evidence.

It is not independent trade authority.

---

## 19. News Verification

TraID must separate claim ingestion from claim verification.

Canonical verification states:

```text
CONFIRMED
PARTIALLY_CONFIRMED
UNVERIFIED
MISLEADING
FALSE
OUTDATED
```

V1 primary-source priorities include, where relevant:

```text
Federal Reserve
BLS
BEA
SEC
other Card-approved authoritative sources
```

Rules:

- fact is separated from interpretation;
- source/publication/event time is retained;
- conflicting evidence remains visible;
- high-impact unverified news increases uncertainty rather than becoming automatic direction;
- social/media content is untrusted input;
- primary-source verification is preferred for material claims.

### 19.1 Asset-Specific ETF Intelligence

Official ETF regulatory, filing, issuer, and exchange/listing events use the
primary-source verification boundary above. ETF inflow/outflow, AUM, and
volume are numerical institutional/market data, not news; they require an
explicitly approved, documented, and verified provider path. Exact ETF flow
providers are not yet selected or verified in the current repository, so that
provider verification remains pending.

The asset-to-ETF applicability mapping and ETF coverage status are explicit
metadata. ETF ingestion, source validation, timestamps, freshness, and basic
numeric validation are deterministic and do not require AI.

---

## 20. AI Provider Strategy

AI is isolated behind a TraID-owned provider contract.

V1 planned provider:

```text
Amazon Bedrock
```

Possible model choice may include Bedrock-supported models, but Core logic must not depend on one model family.

Preferred boundary:

```text
TraID
→ AI Provider Contract
→ Bedrock Adapter
→ selected Bedrock model
```

Required AI behavior includes:

```text
structured output
schema validation
bounded retries
timeouts
explicit provider failure
explicit malformed-output failure
evidence references
supporting factors
contradicting factors
uncertainty
missing information
model/provider metadata
prompt/schema version
```

AI failure must be visible and fail closed where required.

---

## 21. AI Authority Boundary

AI may:

```text
summarize evidence
compare evidence
identify contradictions
structure narrative information
surface uncertainty
surface missing information
explain deterministic results
```

AI may not:

```text
authorize a trade candidate
override NO_TRADE
bypass Strategy
bypass Risk Gate
be authoritative for leverage
be authoritative for position size
invent market evidence
fabricate ETF data or infer numerical ETF flows from prose
override ETF source validation or coverage applicability
convert unverified news into fact
override deterministic financial calculations
```

Model output is untrusted until validated.

---

## 22. Evidence Registry

The Evidence Registry should make consequential evidence addressable and traceable.

Evidence should be able to retain, as relevant:

```text
evidence ID
type
source/provenance
timestamp
quality/verification state
support/contradiction role
related market/entity
selected asset and ETF-coverage applicability/mapping version
version
raw/normalized reference
```

The Registry should support explanation and replay without becoming an opaque second source of truth.

---

## 23. Signal Fusion

Signal Fusion combines evidence without erasing disagreement.

It should preserve:

```text
supporting factors
contradicting factors
evidence references
quality/freshness
source identity
uncertainty
versioned logic
applicable ETF evidence and explicit ETF coverage gaps
```

A fused output may express:

```text
alignment
strength
support
contradiction
```

Core semantic rule:

```text
Alignment != probability.
```

It must not be presented as calibrated win probability unless a separate evaluation/calibration process proves that interpretation.

---

## 24. Strategy Engine

The Strategy Engine is a TraID-owned deterministic control boundary.

It should be:

```text
typed
versioned
testable
evidence-linked
replayable
deterministic for identical controlled inputs
```

The Strategy Engine converts validated context/evidence into a typed strategy candidate or equivalent deterministic artifact.

It does not place trades.

---

## 25. Deterministic Risk Gate

Every strategy candidate must pass through the mandatory Risk Gate.

Canonical conceptual contract:

```text
Strategy Candidate
+ required verified evidence
+ validated configuration
→ Deterministic Risk Gate
→ TRADE_CANDIDATE | NO_TRADE
→ reason codes
```

The Risk Gate must be:

```text
mandatory
deterministic
non-bypassable
reason-coded
fail-closed
testable
```

No AI, Whale, Macro, News, Signal Fusion, API, UI, or Strategy path may bypass it.

### V1 Setup Risk Policy

The deterministic, versioned V1 Setup Risk Policy is enforced by the Risk
Gate. Setup leverage is fixed at 2x. A setup passes this specific numeric
policy only when Net Loss is `<= 10%` and Net Profit Target is `>= 20%` of the
hypothetical leveraged position after applicable verified fees, funding,
slippage, and execution costs. Numeric failure uses existing `RISK_REJECTED`
semantics and does not by itself guarantee `TRADE_CANDIDATE`.

Strategy derives market-valid Entry, invalidation/Stop, and Target. It must
not move or fabricate them to satisfy the percentages, and the thresholds are
not raw price-distance rules. TraID does not know account balance, choose
capital allocation, calculate account-level risk, or determine position size.
AI cannot change leverage, thresholds, Stop, Target, Strategy, or Risk Gate;
human final authority remains unchanged.

---

## 26. Historical Evaluation and Anti-Lookahead

At historical decision time `t`, TraID may only use information available by `t` under the documented data-arrival model.

Future information must not enter historical decision context.

This includes:

```text
future candle values
future outcomes
future news resolution
future macro revisions
later OI/funding state
later recovered data if it was not available at t
```

Anti-lookahead must become executable test coverage.

---

## 27. Backtest / Replay Policy

Backtest/replay must explicitly define:

```text
decision timing
fill timing
fees
funding
slippage
stop/target semantics
same-bar ambiguity
liquidation assumptions
dataset version
configuration version
strategy version
risk version
engine version
```

If stop and target are both touched within one bar and lower-resolution data cannot prove event order:

```text
STOP FIRST
```

unless higher-resolution evidence resolves the ordering.

Profitability never substitutes for correctness.

---

## 28. Outcome Tracking

Outcome Tracking records what happened after an original decision without rewriting the original decision.

Expected concepts include:

```text
decision ID
original timestamp
original evidence refs
strategy version
risk version
entry/reference state
MFE
MAE
target/stop observations
realized or simulated result
evaluation horizon
data-quality context
```

Outcome evaluation may append later evidence.

It must not rewrite historical decision inputs.

---

## 29. Evaluation Strategy

Evaluation comes before additional complexity.

V1 should measure the system and its failure modes, not only trading-looking performance.

Evaluation Registry may track, as applicable:

```text
strategy version
risk version
fusion version
analytics version
dataset version
configuration version
trade/candidate count
NO_TRADE count/reasons
net return
win rate
profit factor
expectancy
max drawdown
average R
fees
funding
liquidations
MFE/MAE distributions
data-quality failures
provider failures
AI failures
Risk Gate rejections
regressions
reproducibility
latency
cost where relevant
```

Metrics must be interpreted in context.

A profitable backtest is not proof of a correct system.

---

## 30. ML Posture

Machine learning is not required merely to make TraID look more advanced.

ML may be evaluated later only if:

```text
sufficient outcome data exists
a deterministic baseline exists
the target is explicit
leakage-safe evaluation exists
walk-forward evaluation is appropriate and defined
error analysis exists
the model materially improves the baseline
complexity/cost is justified
rollback is possible
```

Possible future candidates may include models such as gradient boosting or sequence models.

No ML model may replace the deterministic Risk Gate.

---

## 31. Critical Project Invariants

As owning Cards arrive, these must become executable tests.

```text
Risk Gate cannot be bypassed.
AI failure cannot authorize a trade candidate.
AI cannot directly authorize leverage or position size.
Provider-specific payloads cannot leak into Core contracts.
Required stale evidence cannot silently become trusted.
Unknown financial semantics cannot be treated as verified truth.
Future data cannot enter historical strategy context.
Ambiguous intrabar ordering cannot be resolved optimistically without proof.
Unverified news cannot become confirmed evidence.
Heuristic liquidation cannot become authoritative liquidation.
Identical deterministic inputs/config/version reproduce identical expected output.
Outcome evaluation cannot rewrite original decision context.
V1 cannot require exchange trading credentials.
V1 cannot require wallet private keys.
V1 cannot expose live trade execution capability.
```

These are release-critical project truths.

---

## 32. Security Posture

V1 security baseline:

```text
no real secrets in Git
.env ignored
.env.example contains no real secrets
secret scanning
least privilege
provider credential isolation
log redaction
external content treated as untrusted
model output treated as untrusted
prompt-injection controls
no exchange trading credentials
no wallet private keys
no live execution endpoint
```

When Bedrock is introduced, use secure standard AWS credential mechanisms rather than embedding credentials in code.

Security is part of architecture, not an afterthought.

---

## 33. Observability

Start lightweight and structured.

Runtime information should make it possible to determine:

```text
what happened
which component/provider was involved
when it happened
whether it succeeded
latency
failure type
data freshness
retry/recovery state
```

As V1 grows, consequential outputs should be traceable to:

```text
decision ID
source/evidence references
analytics version
fusion version
strategy version
risk version
AI model/provider/prompt version
dataset/configuration version
```

A heavy observability platform is not required unless a measurable need appears.

---

## 34. Failure and Recovery Posture

Expected failure classes include:

```text
WebSocket disconnect
REST/provider outage
rate limiting
malformed provider payload
data gap
stale data
historical coverage gap
Bedrock outage
invalid AI output
macro/news source outage
invalid configuration
failed invariant
process restart
partial Card implementation
corrupt local state
Docker/CI failure
```

Recovery must:

- remain bounded;
- preserve failure evidence;
- preserve degraded state;
- avoid silent fallback;
- avoid inventing missing data;
- return to a known validated checkpoint when necessary.

---

## 35. Versioning and Reproducibility

Consequential outputs should be reproducible against relevant versions.

Expected versioned concepts include:

```text
canonical schema
provider adapter
analytics
whale methodology
news verification
prompt/schema
AI model ID
Signal Fusion
Strategy
Risk Gate
backtest engine
dataset
configuration
evaluation definition
```

Versioning exists to support explanation, replay, comparison, and audit.

---

## 36. API Posture

The V1 API is read-only decision support.

It may expose:

```text
market/context state
data-quality state
evidence
verified intelligence
strategy/risk result
reason codes
outcomes
evaluation/status information
```

It must not expose:

```text
place order
modify order
cancel order
set live leverage
transfer funds
sign transaction
wallet operation
```

API boundaries must preserve Core ownership rather than duplicate business logic.

---

## 37. Dashboard Posture

The Dashboard should help a human inspect the decision context.

It should make important uncertainty visible, including:

```text
freshness
source
verification state
support
contradiction
AI availability
strategy result
Risk Gate result/reasons
outcome/evaluation state
system/provider health
```

The UI must not hide degraded data behind a normal-looking signal.

The UI does not become a second Strategy or Risk engine.

---

## 38. Development Model

TraID is built through bounded Cards.

Approved V1 sequence:

```text
V1-C01 Repository Baseline & Engineering Harness
V1-C02 Canonical Domain Models
V1-C03 Exchange Adapter Contract
V1-C04 Hyperliquid Provider Verification & Adapter
V1-C05 Data Quality, Freshness & Provenance
V1-C06 Historical Data & Replay Foundation
V1-C07 Order Book & Liquidity Analytics
V1-C08 Trade Flow & CVD
V1-C09 Derivatives & Volatility
V1-C10 Market Regime, Crowding & Liquidation Context
V1-C11 Whale Intelligence Foundation
V1-C12 Macro Intelligence
V1-C13 Primary-Source News Verification
V1-C14 Bedrock Provider & Structured Intelligence
V1-C15 Evidence Registry & Signal Fusion
V1-C16 Typed Strategy Engine
V1-C17 Deterministic Risk Gate
V1-C18 Backtest Engine Integration
V1-C19 Outcome Tracking
V1-C20 Evaluation Registry
V1-C21 Decision-Support API
V1-C22 Dashboard
V1-C23 Observability, Audit & Failure Recovery
V1-C24 Security & Secrets Hardening
V1-C25 Docker, CI & Release Gate
V1-C26 Golden Case End-to-End Validation
V1-C27 V1 Documentation & Demo
```

This list summarizes approved project structure.

It does not authorize implementation.

`TRAID_V1_ROADMAP.md`, Card Specifications, Project Control, repository reality, and explicit user approval determine actual execution state.

---

## 39. Card Gates

The V1 sequence may be understood through six engineering gates:

```text
GATE A — Foundation & Contracts
GATE B — Trusted Market Data
GATE C — Deterministic Market Intelligence
GATE D — External Evidence & Controlled AI
GATE E — Strategy, Risk & Evaluation
GATE F — Product Integration & Release
```

Cards must respect dependency order.

Parallel work is not the default.

It is allowed only if the Roadmap, dependencies, ownership, and user authorization make it safe.

---

## 40. External Open-Source Strategy

TraID is not a merge of external repositories.

Principle:

```text
TAKE THE STRONGEST VERIFIED IDEA OR IMPLEMENTATION
→ REMOVE UNNECESSARY COMPLEXITY
→ ADAPT TO TRAID CONTRACTS
→ VERIFY SEMANTICS
→ TEST IN TRAID
→ RETAIN PROVENANCE
```

Classification:

```text
BUILD
ADAPT
REUSE
REFERENCE ONLY
REJECT
```

Every actual adaptation remains subject to:

```text
exact source verification
license verification
behavior verification
dependency review
financial/data semantic verification
TraID-specific tests
runtime verification where required
```

---

## 41. Current External Reference Roles

Current audited source roles:

```text
Hyperliquid Analytics Dashboard
→ market-data and deterministic analytics patterns

HyperStats
→ Whale / Smart Money methodology and UX reference

Hyperliquid Data Layer API
→ provider taxonomy/reference unless exact source/runtime is verified

NEXUS
→ macro/calendar/provider and operational patterns

Quant Flow
→ structured AI, bounded retry, fail-closed AI patterns

CryptoRadar
→ Signal Fusion, detector, regime, Outcome methodology

Keel
→ typed strategy, validation/registry, agent-safety/harness patterns

Hyperliquid Backtester
→ deterministic replay, anti-lookahead, fill/accounting patterns

Hyper Display
→ UX reference
```

No source repository is TraID's base architecture.

Exact Card-level source decisions belong in the source map/evidence workflow.

---

## 42. Technology Posture

Preferred V1 baseline:

```text
Python 3.11+
FastAPI
Pydantic
pytest
ruff
mypy or pyright
Docker
GitHub Actions
gitleaks
Amazon Bedrock when its Card arrives
```

This is a baseline, not permission to install everything immediately.

Only the active Card may introduce what it actually needs.

---

## 43. Technology Restraint

Do not introduce by default:

```text
Redis
Kafka
Kubernetes
LangChain
LangGraph
MLflow
multi-agent frameworks
custom MCP infrastructure
custom event bus
custom strategy DSL
```

Before a significant technology addition, evaluate:

```text
problem
current limitation
measurable benefit
architecture fit
complexity
cost
vendor lock-in
security/governance impact
evaluation method
rollback
```

Use:

```text
ADOPT
EVALUATE
WATCH
REJECT
```

Technology novelty is not a project goal.

---

## 44. Local-First, Cloud-Ready

Development should remain practical locally.

Provider-specific cloud functionality must be isolated.

Principles:

```text
local development where practical
no unnecessary cloud dependency
replaceable provider boundary
configuration rather than hard-coding
container-ready execution
future deployment without Core rewrite
```

Amazon Bedrock is a V1 AI provider choice.

It does not make TraID's Core AWS-specific.

---

## 45. Tool Neutrality

Project governance must survive a coding-agent change.

Stable authority lives in:

```text
AGENTS.md
PROJECT_PROFILE.md
PROJECT_CONTROL.md
TRAID_V1_ROADMAP.md
TRAID_CARD_SPECIFICATIONS.md
TRAID_CARD_EVIDENCE_MAP.md
GIT_WORKFLOW.md
TRAID_ENGINEERING_HARNESS.md
FINANCIAL_AND_DATA_GUARDRAILS.md
project tests
```

The Card-execution Skill is also project-owned:

```text
.agents/skills/traid-card-execution/SKILL.md
```

Claude Code, Codex, Cursor, or a future coding agent may use a thin adapter later.

No tool-specific file may become the only copy of a critical TraID rule.

---

## 46. Harness Philosophy

TraID uses:

```text
Prompt Engineering
→ instruction quality

Context Engineering
→ relevant information quality

Harness Engineering
→ state, permissions, Cards, validation, evidence,
  checkpoints, rollback, approvals, security, observability
```

A stronger model does not replace controlled engineering.

The project should increase autonomy only when the Harness can measure and constrain it.

---

## 47. Test and Evaluation Posture

The project should progressively establish:

```text
unit tests
provider/contract tests
integration tests
financial invariant tests
Data Quality tests
AI failure/schema tests
Risk Gate bypass tests
anti-lookahead tests
regression tests
Golden Case tests
security checks
```

A Card's exact required validation is defined by its contract.

Do not postpone critical invariants to the end of V1 when their owning Card can establish them earlier.

---

## 48. Golden Case

V1 must end with at least one controlled BTC Golden Case spanning the consequential path:

```text
Source
→ Canonical Data
→ Quality
→ Analytics
→ External Evidence
→ AI
→ Evidence Registry
→ Fusion
→ Strategy
→ Risk
→ Decision Support
→ Outcome
→ Evaluation
```

The Golden Case should make it possible to answer:

1. What data was used?
2. Was it fresh and valid?
3. What supported the setup?
4. What contradicted it?
5. What did AI contribute?
6. What deterministic strategy rules fired?
7. Which Risk checks passed or failed?
8. What versions/configuration were active?
9. What happened afterward?
10. Can the case be replayed?

At least one degraded/failure path must also be demonstrated.

---

## 49. V1 Release Credibility

A credible V1 requires evidence that:

```text
real Hyperliquid BTC data can enter the system
provider data becomes canonical TraID data
freshness/provenance are visible
degraded data fails safely
deterministic analytics are tested
external evidence remains traceable
AI is structured and fail-closed
Signal Fusion preserves support/contradiction
Strategy is typed and deterministic
Risk Gate cannot be bypassed
historical evaluation has no lookahead
backtest accounting reconciles
Outcome Tracking preserves original context
evaluation is reproducible
API remains read-only
Dashboard exposes uncertainty/risk state
failures/recovery are observable
secrets/security gates pass
Docker/CI gates pass
Golden Case passes
documentation is usable by a new developer
no live execution capability exists
```

No single performance metric substitutes for this evidence.

---

## 50. Project-Level STOP Conditions

TraID development must stop and reconcile when any of these become material:

```text
architecture conflict
Card/scope conflict
unknown financially material semantics
source/license uncertainty for copied code
provider semantics cannot be verified
critical Data Quality invariant failure
Risk Gate bypass
AI financial-authority bypass
lookahead
optimistic unresolved same-bar handling
unverified news promoted to fact
heuristic liquidation promoted to authoritative truth
secret/trading credential exposure
destructive action without approval
required validation failure
repository state uncertainty
```

Detailed execution behavior belongs in `AGENTS.md` and the Card Skill.

---

## 51. Success Standard

TraID V1 succeeds when it is:

```text
useful
traceable
reproducible
financially defensible
data-quality aware
provider-isolated
AI-controlled
risk-gated
observable
secure
testable
maintainable
portfolio-credible
```

It does not need maximum architectural complexity.

It needs strong engineering evidence.

---

## 52. Final Project Principle

```text
REAL DATA BEFORE SIGNALS.
TRUSTED DATA BEFORE FINANCIAL INFERENCE.
RELEVANT COVERAGE BEFORE CLAIMING MARKET AWARENESS.
MISSING EVIDENCE MUST REMAIN VISIBLE.
DETERMINISTIC CONTROLS BEFORE AI AUTHORITY.
EVIDENCE BEFORE CONFIDENCE.
RISK GATE BEFORE DECISION SUPPORT.
EVALUATION BEFORE COMPLEXITY.
HUMAN JUDGMENT REMAINS FINAL.
```
