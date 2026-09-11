# TRAID_V1_ROADMAP.md

## 0. Purpose and Authority

This is the canonical **Card identity, order, dependency, engineering-goal, and Exit-Gate roadmap** for TraID V1.

It defines **where the project is going**.

It does not prove current implementation state. Repository reality and verified evidence do that.

It does not authorize a Card to start. Explicit human approval and the `ROADMAP_ALIGNMENT_GATE` do that.

It does not replace the full Card contract in `TRAID_CARD_SPECIFICATIONS.md`.

Authority rule:

```text
Roadmap defines Card identity/order/dependency/goal/Exit Gate.
Card Specifications define the full bounded contract.
Evidence proves what actually happened.
PROJECT_CONTROL records current state.
Repository/Git prove implementation reality.
Prompts request work; they do not redefine this Roadmap.
```

If a prompt conflicts with this Roadmap:

```text
CARD_MISMATCH | CARD_SCOPE_MISMATCH | CARD_DEPENDENCY_MISMATCH
STOP
```

If this Roadmap itself must materially change:

```text
ROADMAP_CHANGE_REQUEST
STOP
REQUIRE EXPLICIT HUMAN APPROVAL
```

---

## 1. V1 Mission

TraID V1 turns real Hyperliquid BTC market data and verified external evidence into transparent, reproducible, read-only decision support.

Canonical flow:

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

V1 does **not** execute live trades.

---

## 2. Scope Freeze

### In V1

```text
Python/FastAPI application baseline
typed provider-neutral domain models
Hyperliquid live REST/WebSocket BTC path
multi-exchange-ready adapter contract
Data Quality + Provenance
historical/replay foundation
deterministic market analytics
Whale Intelligence
Macro Intelligence
primary-source News Verification
Amazon Bedrock provider boundary
structured AI interpretation
Evidence Registry
Signal Fusion
one typed deterministic BTC strategy family
mandatory deterministic Risk Gate
backtest integration
Outcome Tracking
Evaluation Registry
read-only API
clean Dashboard
observability/audit/recovery
security hardening
Docker/CI release gates
Golden Case
documentation/demo
```

### Architecture-ready, not live V1 integrations

```text
Binance
Bybit
OKX
Coinbase
Kraken
```

### Explicitly deferred

```text
live trade execution
automated order placement/modification/cancellation
trading credentials/private-key architecture
extra exchanges/assets unless separately approved
ML/MLOps unless later evidence justifies it
automated strategy optimization
multi-agent orchestration
unnecessary microservices
Redis/Kafka/Kubernetes by default
LangChain/LangGraph by default
custom MCP infrastructure
custom strategy DSL without measured need
```

---

## 3. Non-Negotiable Roadmap Rules

1. One Card equals one coherent engineering goal.
2. Cards remain in the approved C01–C27 sequence unless a formally approved Roadmap change occurs.
3. Dependencies must be `COMPLETE` before dependent work starts.
4. A Card title alone is not an implementation contract.
5. The first implementation step of every new Card is inspect-only Contract Map / Risk Map.
6. No future-Card leakage.
7. No Card becomes `COMPLETE` with failed mandatory validation.
8. No Card completion automatically authorizes the next Card.
9. Financially material uncertainty fails closed.
10. AI never overrides deterministic Strategy/Risk authority.
11. Risk Gate is mandatory and non-bypassable.
12. Historical evaluation is anti-lookahead.
13. Unresolved same-bar stop/target ambiguity uses `STOP FIRST` unless higher-resolution proof exists.
14. Unknown exact external source paths are never guessed.
15. External repositories do not redefine TraID architecture.


## 3.1 Card-Start Authorization

Every Card requires:

```text
EXPLICIT HUMAN CARD-START APPROVAL
```

before implementation.

Roadmap position, dependency completion, a generated prompt, or an agent recommendation never substitutes for this approval.

## 3.2 Unknown Source Protection

For externally derived work, if the exact source file/module is not verified, record exactly:

```text
SOURCE FILE NOT YET VERIFIED
```

Never guess the source path, symbol, license, API, schema, formula, or runtime behavior.

---

## 4. Card States

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
COMPLETE
DEFERRED
```

`COMPLETE` requires:

```text
scope satisfied
required validation actually run and PASS
critical failure paths tested
applicable financial/data/AI/security invariants PASS
exact Exit Gate proven
Evidence updated
PROJECT_CONTROL consistent
Card Quality Gate PASS
human closure/transition approval
```

---

## 5. Engineering Gates

```text
GATE A — Foundation & Contracts        C01–C03
GATE B — Trusted Market Data           C04–C06
GATE C — Deterministic Intelligence    C07–C10
GATE D — External Evidence & AI        C11–C14
GATE E — Strategy, Risk & Evaluation   C15–C20
GATE F — Product Integration & Release C21–C27
```

A gate label groups work. It does not authorize parallel execution.


---

# FOUNDATION & CONTRACTS

## V1-C01 — Repository Baseline & Engineering Harness

**Engineering Goal:** Create the controlled, reproducible TraID repository baseline, install the final engineering Harness, and prove semantic Card content-alignment protection before implementation writes.

**Dependencies:** None

**Exit Gate:** App boots locally; `/health` works; configuration is deterministic; tests are discoverable; semantic `CONTENT_ALIGNMENT_GATE` cases are executable and evidenced independently of Card-ID matching; baseline CI/Docker/security checks are defined and pass where required; no secrets or trading credentials are required.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C02 — Canonical Domain Models

**Engineering Goal:** Define TraID-owned, provider-neutral typed domain contracts used by all later components.

**Dependencies:** C01

**Exit Gate:** Canonical schema tests pass; timestamps/validation/serialization are proven; provider-specific payloads do not leak into Core.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C03 — Exchange Adapter Contract

**Engineering Goal:** Define an exchange-neutral capability contract without prematurely implementing multiple exchanges.

**Dependencies:** C02

**Exit Gate:** A fake adapter satisfies the contract; capability discovery/error mapping are explicit; no Hyperliquid-specific types appear in the Core interface.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.



---

# TRUSTED MARKET DATA

## V1-C04 — Hyperliquid Provider Verification & Adapter

**Engineering Goal:** Verify Hyperliquid semantics and connect real BTC REST/WebSocket data through the canonical adapter.

**Dependencies:** C03

**Exit Gate:** Verified real BTC data is normalized to canonical models; provider semantics/source/license are recorded; reconnect, malformed input, failure and rate-limit behavior are tested; raw provider payloads stay outside Core.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C05 — Data Quality, Freshness & Provenance

**Engineering Goal:** Prevent stale, malformed, missing, gapped, or unavailable data from silently becoming trusted evidence.

**Dependencies:** C04

**Exit Gate:** `LIVE/DELAYED/STALE/UNAVAILABLE` transitions, provenance, gaps, recovery and malformed-data behavior are tested; downstream consumers can determine trust state.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C06 — Historical Data & Replay Foundation

**Engineering Goal:** Create deterministic historical canonical datasets and replay primitives before strategy/backtesting.

**Dependencies:** C02 + C05

**Exit Gate:** Dataset identity/version is reproducible; duplicates/incomplete bars/gaps are explicit; identical input replays deterministically; no silent filling.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.



---

# DETERMINISTIC INTELLIGENCE

## V1-C07 — Order Book & Liquidity Analytics

**Engineering Goal:** Implement deterministic spread, imbalance, depth, concentration, decay and slippage analytics.

**Dependencies:** C05

**Exit Gate:** Financial fixtures cover balanced/one-sided/empty/thin/extreme books; units and formulas are verified; degraded quality propagates.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C08 — Trade Flow & CVD

**Engineering Goal:** Implement deterministic aggressive-flow, net-flow and CVD analytics with explicit windows/restart semantics.

**Dependencies:** C05

**Exit Gate:** Known trade sequences produce expected results; duplicate/late/reset behavior is defined and tested; no AI calculation path exists.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C09 — Derivatives & Volatility

**Engineering Goal:** Implement verified OI, funding, basis where supported, ATR, realized volatility, VWAP/session and momentum context.

**Dependencies:** C05 + C06

**Exit Gate:** Formula fixtures pass; units/signs/intervals are verified; warm-up/missing/stale states are explicit; no guessed provider semantics.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C10 — Market Regime, Crowding & Liquidation Context

**Engineering Goal:** Build interpretable deterministic higher-level market-state evidence while preserving liquidation truth labels.

**Dependencies:** C07 + C08 + C09

**Exit Gate:** Regime/crowding rules are deterministic/versioned; insufficient data yields `UNKNOWN`; heuristic liquidation cannot become authoritative truth; no hidden probability.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.



---

# EXTERNAL EVIDENCE & AI

## V1-C11 — Whale Intelligence Foundation

**Engineering Goal:** Track a curated Hyperliquid wallet set, lifecycle events, current exposure and transparent Smart Money evidence.

**Dependencies:** C04 + C05

**Exit Gate:** OPEN/INCREASE/REDUCE/CLOSE/FLIP/LIQUIDATION transitions are tested; realized/unrealized and current/activity views are separated; scoring is transparent/versioned; whales cannot authorize trades.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C12 — Macro Intelligence

**Engineering Goal:** Normalize bounded authoritative macro and asset-specific ETF institutional/market evidence into traceable, freshness-aware evidence, including explicit asset-to-ETF applicability metadata.

**Dependencies:** C02 + C05

**Exit Gate:** Source/timezone/actual/forecast/previous/revision and applicable ETF event/flow/AUM/volume handling are tested; duplicates/missing/stale/unavailable/unverified states and coverage gaps are explicit; macro or ETF evidence cannot bypass Risk Gate. Exact ETF flow providers remain pending until separately verified.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C13 — Primary-Source News Verification

**Engineering Goal:** Separate market claims and official ETF regulatory/issuer/listing events from verified facts using primary-source evidence and explicit verification states.

**Dependencies:** C02 + C05

**Exit Gate:** Fixtures prove CONFIRMED/PARTIALLY_CONFIRMED/UNVERIFIED/MISLEADING/FALSE/OUTDATED behavior for claims and applicable ETF official events; provenance is retained; external instructions cannot alter policy; numerical ETF flow/AUM/volume data is not misclassified as news.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C14 — Bedrock Provider & Structured Intelligence

**Engineering Goal:** Add Amazon Bedrock behind a provider-neutral structured AI boundary for evidence interpretation only.

**Dependencies:** C11 + C12 + C13

**Exit Gate:** Valid/malformed/timeout/provider-error/missing-evidence cases are tested; output is schema-validated and evidence-linked; failures are explicit/fail-closed; AI cannot create or override risk authority.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.



---

# STRATEGY, RISK & EVALUATION

## V1-C15 — Evidence Registry & Signal Fusion

**Engineering Goal:** Create traceable evidence identity and deterministic fusion that preserves support, contradiction, missing evidence, applicable ETF coverage gaps, and uncertainty.

**Dependencies:** C07–C14

**Exit Gate:** Same evidence yields same fusion result; stale/missing/contradicting evidence and relevant ETF coverage gaps remain visible; every contribution is traceable; `Alignment != probability`; missing ETF evidence is never directional evidence.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C16 — Typed Strategy Engine

**Engineering Goal:** Implement one explicit versioned BTC strategy family as deterministic typed rules that derives market-valid Entry/invalidation/Stop/Target structure without forcing values to satisfy downstream percentages.

**Dependencies:** C15

**Exit Gate:** Identical controlled inputs produce identical outputs; insufficient/stale required evidence, including applicable ETF gaps, yields `NO_SETUP`; market-valid Entry/invalidation/Stop/Target structure is preserved; rules/config are tested; no Bedrock call exists inside deterministic evaluation.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C17 — Deterministic Risk Gate

**Engineering Goal:** Make promotion to `TRADE_CANDIDATE` possible only through a mandatory deterministic fail-closed Risk Gate that enforces fixed 2x setup leverage, maximum Net Loss `<= 10%`, and minimum Net Profit Target `>= 20%` on the hypothetical position after applicable verified costs.

**Dependencies:** C16

**Exit Gate:** Every rejection/boundary path, including fixed-2x/10%/20% policy and required-cost failures, is tested; stale/missing/invalid configuration fails closed; bypass tests pass; output is `TRADE_CANDIDATE|NO_TRADE` with existing reason codes and versioned policy; account balance and position sizing remain outside V1.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C18 — Backtest Engine Integration

**Engineering Goal:** Replay the same Strategy, Risk, and Setup Risk Policy semantics over historical canonical data with structural anti-lookahead and cost-inclusive Net P&L accounting.

**Dependencies:** C06 + C16 + C17

**Exit Gate:** Tests prove no future access, explicit fill timing, fixed-policy reuse, fees, funding, slippage, applicable execution-cost handling, liquidation, `STOP FIRST`, cost-inclusive Net P&L reconciliation, deterministic rerun, gaps and incomplete-bar handling.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C19 — Outcome Tracking

**Engineering Goal:** Measure what happened after original candidates without rewriting historical decision context.

**Dependencies:** C17 + C18

**Exit Gate:** Candidate-to-outcome linkage, MFE/MAE and result fixtures pass; versions/evidence/config are retained; open/unresolved outcomes are explicit; original context is immutable.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C20 — Evaluation Registry

**Engineering Goal:** Create a versioned evaluation record for data, analytics, AI, strategy, risk and system quality.

**Dependencies:** C18 + C19

**Exit Gate:** One evaluation run identifies versions/data/config and measured results; failure/rejection/latency/cost/reproducibility metrics are recordable; evaluation is not anecdotal.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.



---

# PRODUCT INTEGRATION & RELEASE

## V1-C21 — Decision-Support API

**Engineering Goal:** Expose stable typed read-only application contracts to UI/clients without duplicating Core logic, including relevant ETF evidence and explicit coverage gaps.

**Dependencies:** C05–C20

**Exit Gate:** Contract/degraded/invalid-request tests pass; provenance/quality/risk reasons and relevant ETF evidence/coverage gaps are available where relevant; no write/trade-execution endpoint exists.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C22 — Dashboard

**Engineering Goal:** Provide a clean human decision-support view with progressive disclosure of evidence, uncertainty, risk state, relevant ETF intelligence, and ETF coverage gaps.

**Dependencies:** C21

**Exit Gate:** User can understand selected-asset state without raw logs/JSON; relevant ETF evidence and explicit ETF gaps, degraded state, contradiction, provenance and NO_TRADE reasons are visible; no execution controls exist.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C23 — Observability, Audit & Failure Recovery

**Engineering Goal:** Make consequential decisions and operational failures diagnosable, traceable and recoverable.

**Dependencies:** C04–C22

**Exit Gate:** Disconnect/provider/AI/source/stale/process-restart failure scenarios are observable; decision audit links evidence/versions/results/reasons; recovery is bounded and does not hide degraded state.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C24 — Security & Secrets Hardening

**Engineering Goal:** Enforce least privilege, secret isolation, untrusted-content controls and the read-only V1 boundary.

**Dependencies:** C13 + C14 + C21

**Exit Gate:** Secret scan/redaction/input/prompt-injection/permission tests pass; no trading credentials/private keys/execution endpoints exist; external/model content cannot become system authority.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C25 — Docker, CI & Release Gate

**Engineering Goal:** Produce a reproducible release candidate with blocking automated quality gates.

**Dependencies:** C01–C24

**Exit Gate:** Clean checkout builds/runs; Docker and CI pass required test/lint/type/security suites; financial/Risk/anti-lookahead/AI fail-closed failures block release; setup is documented.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C26 — Golden Case End-to-End Validation

**Engineering Goal:** Prove TraID as one coherent system using a controlled BTC success case plus degraded/failure path.

**Dependencies:** C25

**Exit Gate:** Stored evidence answers the ten Golden Case traceability questions; source→quality→analytics→evidence→AI→fusion→strategy→risk→UI→outcome→evaluation is replayable; degraded path fails safely.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


## V1-C27 — V1 Documentation & Demo

**Engineering Goal:** Make V1 reproducible, teachable and demonstrable to a new developer and portfolio reviewer.

**Dependencies:** C26

**Exit Gate:** A new developer can set up, run, verify and understand V1 from repository docs; demo covers live data, quality, analytics, evidence, AI, fusion, strategy, risk, replay/backtest and outcomes; limitations are explicit.

**Start Rule:** Explicit human Card-start approval + dependency proof + `ROADMAP_ALIGNMENT_GATE: PASS`.

**Closure Rule:** Full Card contract satisfied + required evidence + `CARD_QUALITY_GATE: PASS` + human closure/transition approval.


---

# 6. Critical Dependency Path

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
├──────────────┬──────────────────┬──────────────────┐
↓              ↓                  ↓                  ↓
C06          C07–C10            C11–C13        trusted shared data
│              │                  │
│              └──────────┬───────┘
│                         ↓
│                        C14
│                         ↓
└──────────────────────→ C15
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
                      C23 + C24
                          ↓
                         C25
                          ↓
                         C26
                          ↓
                         C27
```

This diagram expresses dependency logic, not permission for autonomous parallel Card starts.

---

# 7. Source / Build Strategy by Card

Canonical classifications:

```text
BUILD
ADAPT
REUSE
REFERENCE ONLY
REJECT
```

High-level direction:

| Card | Primary direction |
|---|---|
| C01 | BUILD from TraID + Playbook + proven harness patterns |
| C02 | BUILD TraID-owned canonical contracts |
| C03 | BUILD + ADAPT provider-boundary patterns |
| C04 | ADAPT only after exact Hyperliquid source/license/behavior verification |
| C05 | BUILD + ADAPT data-health/provenance patterns |
| C06 | ADAPT deterministic replay ideas after verification |
| C07–C10 | BUILD/ADAPT verified deterministic analytics, never blind copy |
| C11 | BUILD + methodological ADAPT from verified whale patterns |
| C12 | BUILD + ADAPT authoritative macro/provider patterns |
| C13 | BUILD primary-source verification |
| C14 | BUILD provider-neutral AI boundary + ADAPT fail-closed patterns |
| C15 | BUILD + ADAPT evidence/fusion methodology |
| C16 | BUILD TraID strategy + ADAPT typed validation patterns |
| C17 | BUILD TraID-owned deterministic Risk Gate |
| C18 | ADAPT strong backtest invariants into TraID contracts |
| C19 | BUILD + ADAPT Outcome methodology |
| C20 | BUILD TraID Evaluation Registry |
| C21 | BUILD read-only API |
| C22 | BUILD UI from REFERENCE ONLY UX patterns |
| C23 | BUILD + ADAPT observability/recovery patterns |
| C24 | BUILD security boundary |
| C25 | BUILD + ADAPT DevOps patterns |
| C26 | BUILD TraID Golden Case |
| C27 | BUILD documentation/demo |

Exact source provenance belongs in Card Specifications/Evidence and must be re-verified before implementation.

---

# 8. P0 / P1 / P2 Scope Protection

Time pressure never authorizes weakening critical controls.

## P0 — Must Survive

```text
canonical provider-neutral data
Data Quality + Provenance
verified Hyperliquid semantics
deterministic analytics
typed Strategy
deterministic non-bypassable Risk Gate
anti-lookahead
backtest financial invariants
critical observability
security boundary
release gates
Golden Case traceability
```

## P1 — Reduce Breadth, Not Truth

```text
number of watched whales
macro event breadth
news-source breadth
Bedrock task breadth
Outcome UI depth
Dashboard polish
```

Examples:

```text
curated whale set instead of universal discovery
few authoritative macro event types instead of broad macro coverage
Federal Reserve/BLS/BEA/SEC before many news providers
one structured Bedrock task before multiple AI workflows
one strong BTC strategy before many strategies
```

## P2 — Defer First

```text
extra exchanges
extra assets
advanced alerts/visualizations
broad wallet discovery
cross-chain intelligence
ML/MLOps
automated strategy optimization
live execution
```

---

# 9. V1 Quality Gates

## Q1 — Data Trust

Must prove normalization, provenance, freshness, degradation, failure visibility, reconnect/recovery.

## Q2 — Financial Correctness

Must prove units, signs, formulas, accounting invariants, deterministic calculations and reproducibility.

## Q3 — AI Boundary

Must prove structured output, schema validation, bounded failure behavior, evidence grounding and no financial authority.

## Q4 — Strategy & Risk

Must prove deterministic Strategy, explicit rules, mandatory deterministic Risk Gate and bypass resistance.

## Q5 — Backtest Integrity

Must prove anti-lookahead, execution timing, fees, funding, liquidation, `STOP FIRST`, P&L reconciliation and deterministic replay.

## Q6 — End-to-End Traceability

Must prove:

```text
source → quality → evidence → strategy → risk → result → outcome → evaluation
```

---

# 10. Validation Strategy

Across owning Cards, progressively establish:

```text
unit tests
schema/contract tests
provider tests
Data Quality tests
integration tests
financial invariant tests
failure tests
AI schema/fail-closed tests
Risk Gate bypass tests
anti-lookahead tests
replay/regression tests
security tests
Golden Case tests
Docker/CI release tests
```

A test is evidence only if it actually ran.

Do not weaken a valid failing test to make a Card green.

---

# 11. V1 Data Authority Hierarchy

When sources conflict:

```text
1. authoritative primary source for macro/regulatory facts
2. direct exchange/provider evidence for exchange market state
3. verified deterministic TraID calculation
4. verified external evidence
5. AI interpretation
```

AI interpretation is never authoritative for a factual numeric market value.

---

# 12. Failure Philosophy

Examples:

```text
Hyperliquid disconnect
→ bounded recovery where valid
→ degraded state remains visible
→ never pretend LIVE

Bedrock unavailable/malformed
→ explicit AI_UNAVAILABLE / invalid state
→ no manufactured AI authority

Primary news source unavailable
→ UNVERIFIED / unavailable
→ no promotion to confirmed fact

Required evidence stale
→ NO_SETUP and/or NO_TRADE according to owning contract

Unknown financial semantics
→ FINANCIAL_SEMANTICS_UNVERIFIED
→ STOP

Risk configuration invalid
→ NO_TRADE

Future data detected in historical context
→ LOOKAHEAD_VIOLATION
→ STOP
```

---

# 13. Versioning Expectations

As owning Cards arrive, retain relevant versions:

```text
canonical_schema_version
provider_adapter_version
analytics_version
whale_methodology_version
news_verification_version
prompt/schema_version
AI_model_id
signal_fusion_version
strategy_version
risk_gate_version
backtest_engine_version
dataset_version/hash
configuration_version
evaluation_definition_version
```

A consequential result without its relevant versions is incomplete evidence.

---

# 14. Golden Case Requirement

C26 must prove at least one controlled BTC success path and one degraded/failure path.

For the final decision-support result, stored evidence must answer:

1. What source/data was used?
2. Was it fresh and valid?
3. What supported the setup?
4. What contradicted it?
5. What did AI contribute?
6. Which deterministic Strategy rules fired?
7. Which Risk Gate checks passed or failed?
8. Which versions/configuration/data snapshot were active?
9. What happened afterward?
10. Can the result be replayed?

---

# 15. Roadmap Change Control

A material change to Card identity, order, dependency, Engineering Goal, or Exit Gate is a governed change.

Required record:

```text
ROADMAP_CHANGE_REQUEST
Affected Card(s):
Observed Problem:
Evidence:
Why Current Roadmap Is Insufficient:
Smallest Proposed Change:
Dependency Impact:
Architecture Impact:
Financial/Data Risk:
Test/Evaluation Impact:
Migration/Compatibility Impact:
Rollback:
Human Approval:
```

Until approved:

```text
STOP
USE CURRENT CANONICAL ROADMAP
```

Do not let implementation silently rewrite its own specification.

---

# 16. End-of-Card Rule

After a Card becomes `COMPLETE` or `BLOCKED`:

```text
update Evidence
update PROJECT_CONTROL
report actual result
report limitation/blocker
STOP
```

Never automatically:

```text
start next Card
commit
push
open PR
merge
deploy
release
```

Those actions require their applicable approval.

---

# 17. Final Roadmap Rule

```text
BUILD IN DEPENDENCY ORDER.
TRUST DATA BEFORE ANALYTICS.
VERIFY EVIDENCE BEFORE AI.
KEEP FINANCIAL AUTHORITY DETERMINISTIC.
PROVE RISK BEFORE PROMOTION.
EVALUATE BEFORE COMPLEXITY.
RECORD EVIDENCE BEFORE CLAIMS.
COMPLETE ONE CARD.
STOP.
WAIT FOR HUMAN APPROVAL.
```
