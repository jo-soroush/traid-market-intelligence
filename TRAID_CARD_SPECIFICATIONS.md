# TRAID_CARD_SPECIFICATIONS.md

## 0. Purpose

This file is the canonical detailed engineering and learning contract for every TraID V1 Card.

`TRAID_V1_ROADMAP.md` owns Card identity, order, high-level dependency, Engineering Goal, and Exit Gate.

This file expands each Card into the complete bounded implementation contract.

Repository reality must be inspected before implementation.

## 1. Required 14-Section Card Contract

Every Card contains exactly:

1. Title
2. Engineering Goal
3. Learning Goal
4. Why It Exists
5. Architecture Concept
6. Current System Before Card
7. Design Decision
8. Implementation Scope
9. Out of Scope
10. Dependencies
11. Tests / Evaluation
12. Exit Gate
13. What We Learned
14. Completion Evidence

Rules:

```text
Sections 1–12 = pre-implementation contract.
Sections 13–14 = actual implementation/evidence only.
```

Never pre-fill Sections 13–14 with expected results.

## 2. Contract Authority and Safety

Before the first write for a Card:

```text
Roadmap Card identity must match.
This 14-section contract must match.
Dependencies must be evidenced COMPLETE.
Repository reality must be reconciled with Section 6.
Contract Map / Risk Map must be performed inspect-only.
ROADMAP_ALIGNMENT_GATE must PASS.
Human Card-start approval must exist.
```

If repository reality disproves Section 6 or another material assumption:

```text
PROJECT_STATE_CONFLICT or CARD_SCOPE_MISMATCH
STOP
```

Do not silently rewrite the contract during implementation.

Material changes to Engineering Goal, Architecture Concept, Design Decision, Scope, Dependencies, Tests/Evaluation, or Exit Gate require explicit human approval and canonical document reconciliation.

## 3. Cross-Card Non-Negotiables

```text
No live trade execution in V1.
No trading credentials.
No wallet private keys.
Provider-specific payloads stay behind adapters.
Data Quality and Provenance are first-class.
Unknown financially material semantics → FINANCIAL_SEMANTICS_UNVERIFIED → STOP.
AI cannot override deterministic financial controls.
Risk Gate is deterministic, fail-closed, reason-coded, mandatory, non-bypassable.
Historical evaluation is anti-lookahead.
Unresolved same-bar stop/target ambiguity → STOP FIRST unless higher-resolution proof exists.
Heuristic liquidation != authoritative liquidation.
Alignment != probability.
External content and model output are untrusted.
Unknown exact external source path → SOURCE FILE NOT YET VERIFIED.
A test is PASS only if actually executed.
No future-Card leakage.
Card COMPLETE does not authorize next Card.
```

## 4. Source Adaptation Rule

For any externally derived implementation, preserve in Evidence:

```text
Decision ID
Card ID
Source project/repository
Commit/tag/branch where relevant
Exact source file/module/symbol
License
Classification: BUILD / ADAPT / REUSE / REFERENCE ONLY / REJECT
Why selected
What TraID changed
What TraID rejected
Runtime/semantic verification
Required TraID tests
Final evidence
```

Source visibility is not runtime approval.

## 5. Learning Rule

The Learning Goal is planned before implementation.

`What We Learned` is written only afterward from actual evidence and should explain:

```text
what was wanted and why it mattered
verified system before the Card
what was built and how it works
selected design decision
alternatives actually considered and why the selected approach was chosen
relevant correctness, architecture, simplicity, maintainability, security,
governance, cost, performance, vendor-flexibility, and operational-risk tradeoffs
engineering problem
architecture before/after
important ownership
meaningful rejected approaches and why they were rejected
tests/evaluations actually run and actual results
problems discovered
diagnosis, verified root cause, and solution
why the fix is correct and whether it is permanent or a workaround
known limitations and unresolved risks
professional engineering lesson
student takeaway
Exit Gate proof
what this enables next without authorizing the next Card
```

Sections 13–14 remain evidence-only. Planned intentions, textbook filler,
unexecuted tests, unproven root causes, and assumed alternatives must remain
`Pending`, `Not verified`, `Not applicable`, or `Blocked` as appropriate.

---

# V1 CARD CONTRACTS


---

## V1-C01 — Repository Baseline & Engineering Harness

### 1. Title
Repository Baseline & Engineering Harness

### 2. Engineering Goal
Create and verify a minimal, reproducible TraID repository baseline and install the canonical engineering Harness before feature implementation.

### 3. Learning Goal
Learn how repository truth, explicit ownership, tests, CI, security, approvals, checkpoints, and evidence combine into a production-oriented coding-agent Harness.

### 4. Why It Exists
Every later Card depends on a known repository state and a development process that cannot silently change scope, invent evidence, expose secrets, or bypass financial controls.

### 5. Architecture Concept
Repository baseline + tool-neutral Harness + deterministic configuration + health/test/CI/security entry points.

### 6. Current System Before Card
TraID architecture, Roadmap, source audits, traceability plans, and Harness designs exist as planning artifacts. Actual repository/Git/runtime state must be inspected and must not be inferred from those documents.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID's own baseline. Use the AI Engineering Playbook and proven patterns from DocChat, Keel, Quant Flow, NEXUS, Project 04, CryptoRadar, and Hyperliquid Backtester as references. Do not import another repository skeleton wholesale.

### 8. Implementation Scope
- inspect Git/repository reality before writes
- establish minimal Python package and deterministic configuration
- establish FastAPI app and `/health`
- establish pytest discovery and baseline tests
- install the final ten-file Harness in canonical locations
- establish `.gitignore`, `.env.example`, secret scanning baseline, Docker/CI skeleton where required by the Roadmap Exit Gate
- record exact commands and repository evidence

### 9. Out of Scope
- market-data ingestion
- financial analytics
- Bedrock integration
- Strategy/Risk implementation
- live execution
- Redis/Kafka/Kubernetes/microservices merely for completeness

### 10. Dependencies
None.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- application import/boot
- `/health`
- configuration loading/failure
- pytest discovery
- secret/no-credential checks
- Docker build and CI syntax/job where included in the approved bounded C01 implementation
- Harness consistency checks
- content-alignment extraction and gate cases: correct ID/content, wrong ID, correct ID with wrong or Out-of-Scope content, mixed/future-owned behavior, invented requirement, incomplete dependency, project-state conflict, next-Card authorization, failed validation, and semantically disguised future work

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Repository baseline is reproducible and evidenced; app/health/config/tests work or exact blockers are recorded; final Harness is installed consistently; semantic content-alignment protection is executable and evidenced independently of Card-ID matching; no secrets/trading credentials/private keys are required; Docker/CI/security baseline required by C01 is validated; repository reality is ready for C02.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C02 — Canonical Domain Models

### 1. Title
Canonical Domain Models

### 2. Engineering Goal
Define TraID-owned provider-neutral typed contracts for market data, quality, provenance, context, and evidence.

### 3. Learning Goal
Learn why stable domain contracts prevent provider payloads, transport details, and UI/API shapes from becoming business logic.

### 4. Why It Exists
All later adapters, analytics, evidence, Strategy, Risk, replay, API, and evaluation require a common language with explicit time and provenance semantics.

### 5. Architecture Concept
External/provider data → normalization boundary → canonical typed TraID domain → downstream consumers.

### 6. Current System Before Card
C01 provides only the verified repository/Harness baseline. No provider-neutral domain model should be assumed to exist unless repository inspection proves it.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD canonical TraID models. External models may inform field discovery but do not own Core. Require explicit temporal/source semantics and reject provider-specific raw dictionaries in business logic.

### 8. Implementation Scope
- define `MarketTrade`, `OrderBookLevel`, `OrderBookSnapshot`, `Candle`, `FundingSnapshot`, `OpenInterestSnapshot`, `LiquidationEvent`, `PriceSnapshot`, `MarketContext`, `SourceProvenance`, `DataQualityState`, and evidence primitives required by the approved architecture
- define timezone-aware timestamp and source identity rules
- define numeric/domain constraints
- define schema/version strategy
- define serialization/round-trip behavior

### 9. Out of Scope
- Hyperliquid transport
- exchange adapter implementation
- analytics formulas
- database architecture
- API response models as Core owners
- future exchange-specific fields leaking into Core

### 10. Dependencies
C01 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- validation success/failure
- timezone awareness
- serialization round-trip
- numeric constraints
- source identity/provenance fields
- schema/version behavior
- provider-specific leakage check

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Canonical schemas are typed, tested, serializable, temporally explicit, source-aware, and provider-neutral; no external provider model owns Core contracts.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C03 — Exchange Adapter Contract

### 1. Title
Exchange Adapter Contract

### 2. Engineering Goal
Define a capability-aware exchange-neutral adapter contract that future providers can implement without changing Core, while making relevant source/category coverage and provider limitations explicit.

### 3. Learning Goal
Learn interface segregation, capability discovery, error normalization, and provider isolation for market-data systems.

### 4. Why It Exists
Hyperliquid is V1's live provider, but hard-coding its payloads into Core would create avoidable vendor coupling.

### 5. Architecture Concept
Core → exchange contract → provider adapter → provider transport.

### 6. Current System Before Card
C02 establishes canonical models only. No real exchange integration is authorized yet.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD the interface; ADAPT only useful boundary patterns. Do not assume every exchange or provider supports identical capabilities or represents the whole relevant market. Capability and availability states must be explicit.

### 8. Implementation Scope
- define connect/disconnect/health lifecycle where needed
- define typed methods for trades/order book/candles/funding/open interest/market context as capabilities
- define capability discovery
- expose source/category coverage, availability, and known provider limitations without implying universal coverage
- define normalized provider errors
- create fake/test adapter
- ensure outputs are canonical models

### 9. Out of Scope
- live Hyperliquid implementation
- Binance/Bybit/OKX/Coinbase/Kraken live adapters
- provider-specific fields in interface
- generic abstraction for hypothetical capabilities with no V1 use

### 10. Dependencies
C02 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- fake adapter contract
- capability discovery
- unsupported capability
- missing or partially covered source/category remains explicit and is not directional evidence
- provider error mapping
- canonical output types
- no Hyperliquid-specific Core types

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
A fake provider satisfies the contract; capabilities, coverage, availability, and errors are explicit; Core can consume canonical data without Hyperliquid-specific types or a false complete-coverage claim.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C04 — Hyperliquid Provider Verification & Adapter

### 1. Title
Hyperliquid Provider Verification & Adapter

### 2. Engineering Goal
Verify Hyperliquid semantics and implement the V1 real BTC REST/WebSocket adapter through C03 contracts, with explicit awareness of the provider's relevant coverage and limitations.

### 3. Learning Goal
Learn to treat provider documentation/source code as evidence that still requires semantic, license, runtime, timestamp, and failure verification.

### 4. Why It Exists
TraID cannot produce trustworthy analytics from guessed exchange semantics.

### 5. Architecture Concept
Hyperliquid REST/WebSocket/history → Hyperliquid adapter → canonical TraID data.

### 6. Current System Before Card
C03 provides an exchange contract and fake adapter. No real Hyperliquid runtime behavior is proven by that work.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
ADAPT verified patterns only after re-confirming exact source/license/behavior. Hyperliquid-specific JSON and transport remain inside the adapter.

### 8. Implementation Scope
- re-verify selected Hyperliquid source files/modules and official semantics before reuse
- implement BTC trades/order book/candles/funding/open-interest/market-context capabilities required by V1
- normalize timestamps and numeric values
- implement health/rate-limit/error mapping
- implement bounded WebSocket reconnect/recovery behavior where required
- retain provider/source provenance
- record available, delayed, stale, unavailable, and unverified source/category coverage; Hyperliquid is not treated as the whole market

### 9. Out of Scope
- multi-exchange live implementation
- trading/order endpoints
- wallet private keys
- guessing liquidation or trade-side semantics
- copying source without license/runtime verification

### 10. Dependencies
C03 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- real or controlled provider smoke where feasible
- normalization fixtures
- REST error/rate-limit mapping
- WebSocket disconnect/reconnect
- malformed payload
- unavailable provider and partial source/category coverage
- timestamp semantics
- capability behavior
- raw-provider leakage check

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Verified real BTC Hyperliquid data reaches canonical models; source/license/semantics and relevant coverage limitations are recorded; failure/reconnect/rate-limit/availability paths are tested; no provider payload escapes into Core and no complete-market claim is made.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C05 — Data Quality, Freshness & Provenance

### 1. Title
Data Quality, Freshness & Provenance

### 2. Engineering Goal
Make trust and relevant coverage state explicit so stale, delayed, malformed, gapped, recovered, partially covered, or unavailable data cannot silently become valid evidence.

### 3. Learning Goal
Learn that data quality is a first-class market-system contract rather than a logging concern.

### 4. Why It Exists
Financial analytics and decisions are unsafe when consumers cannot distinguish live data from degraded data.

### 5. Architecture Concept
Canonical data → validation/freshness/gap/recovery/provenance → trusted/degraded data context.

### 6. Current System Before Card
C04 supplies canonical Hyperliquid data and provider health, but system-wide trust semantics are not yet owned unless repository evidence proves otherwise.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID quality/provenance ownership; ADAPT useful staleness/health/checkpoint patterns without importing another project's architecture.

### 8. Implementation Scope
- implement `LIVE`, `DELAYED`, `STALE`, `UNAVAILABLE` state rules
- define data-type-specific freshness thresholds/configuration
- propagate source and timestamps
- detect malformed/missing/gap conditions
- record recovery/backfill status
- expose quality to downstream consumers
- expose source/category coverage, missing coverage, and provider availability to downstream consumers
- prevent silent zero/default substitution

### 9. Out of Scope
- analytics signals
- automatic gap fabrication
- provider fallback that hides source change
- historical replay engine
- Dashboard polish

### 10. Dependencies
C04 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- quality-state transitions
- freshness boundaries
- missing/malformed input
- gap detection
- recovery/backfill labeling
- unavailable behavior
- missing source, partial category coverage, and unavailable-provider behavior
- recovery after coverage degradation
- provenance preservation
- no false complete-coverage claim and no directional inference solely from missing evidence
- stale-required-data rejection

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Quality/provenance/coverage behavior is deterministic and tested; consumers can identify origin, freshness, gaps, recovery, and missing categories; degraded data cannot silently become trusted/live or be presented as complete coverage.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C06 — Historical Data & Replay Foundation

### 1. Title
Historical Data & Replay Foundation

### 2. Engineering Goal
Create versioned canonical historical BTC datasets and deterministic replay primitives before strategy/backtesting, with dataset coverage and historical gaps explicit.

### 3. Learning Goal
Learn temporal integrity, dataset identity, reproducible replay, and why historical availability differs from present-day knowledge.

### 4. Why It Exists
Backtests and outcome analysis are meaningless without deterministic, traceable historical inputs and explicit gaps.

### 5. Architecture Concept
Verified historical source → canonical dataset → quality/provenance → deterministic replay stream.

### 6. Current System Before Card
C05 defines live/canonical trust semantics. Historical ingestion/replay is not yet a backtest engine.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
ADAPT strong replay/sync patterns after verification; preserve source coverage and gaps rather than silently manufacturing continuity.

### 8. Implementation Scope
- verify approved historical BTC source capabilities/limitations
- normalize historical data to canonical models
- define dataset identity/version/hash strategy
- record coverage/gaps
- expose source/category coverage, availability limitations, and missing history explicitly
- handle duplicates and incomplete bars explicitly
- implement deterministic replay ordering and clock semantics

### 9. Out of Scope
- strategy evaluation
- trade fills/P&L
- future-data access
- automatic gap interpolation without explicit policy
- full backtest engine

### 10. Dependencies
C02 + C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- dataset reproducibility
- duplicate handling
- gap/incomplete-bar behavior
- partial dataset coverage and unavailable-history behavior
- event ordering
- deterministic replay rerun
- timestamp/availability semantics
- no silent fill

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
A versioned BTC canonical dataset can be replayed deterministically with source/category coverage, gaps, and availability limitations explicit and without silently filling or interpolating missing information.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C07 — Order Book & Liquidity Analytics

### 1. Title
Order Book & Liquidity Analytics

### 2. Engineering Goal
Implement deterministic order-book and liquidity analytics over trusted canonical snapshots.

### 3. Learning Goal
Learn to verify financial formulas, units, depth windows, edge cases, and quality propagation.

### 4. Why It Exists
Liquidity structure is core market evidence but can be misleading if formulas or stale books are hidden.

### 5. Architecture Concept
Trusted order book → deterministic liquidity metrics → typed evidence.

### 6. Current System Before Card
C05 supplies trusted/degraded canonical order books; no liquidity signal is assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD/ADAPT only verified deterministic formulas. AI has no calculation role.

### 8. Implementation Scope
- spread/mid where semantically valid
- depth by configured bands
- imbalance
- concentration
- depth decay
- slippage estimates for explicit hypothetical sizes
- typed outputs with source/quality/version

### 9. Out of Scope
- trade execution
- AI liquidity scoring
- strategy/risk decisions
- unverified liquidation inference
- opaque composite confidence

### 10. Dependencies
C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- balanced/one-sided/empty/thin/extreme books
- known-value formula fixtures
- unit/side conventions
- stale/degraded propagation
- invalid book levels
- determinism

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Liquidity metrics match verified fixtures, preserve units/quality/provenance, handle edge cases, and remain deterministic.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C08 — Trade Flow & CVD

### 1. Title
Trade Flow & CVD

### 2. Engineering Goal
Implement deterministic aggressive-flow, net-flow, and CVD evidence with explicit windows and lifecycle semantics.

### 3. Learning Goal
Learn how trade-side semantics, duplicates, late events, reset windows, and state restoration affect flow indicators.

### 4. Why It Exists
CVD/flow is only useful if side classification and accumulation behavior are reproducible.

### 5. Architecture Concept
Trusted canonical trades → ordered flow state → CVD/net/aggression metrics → evidence.

### 6. Current System Before Card
C05 provides trusted trades; no validated CVD accumulator should be assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
Use verified provider side semantics. Keep accumulation deterministic and explicitly versioned/configured.

### 8. Implementation Scope
- verify maker/taker/aggressor semantics
- implement buy/sell volume and delta
- implement configured rolling/session CVD
- define duplicate/late/reset behavior
- preserve quality/provenance

### 9. Out of Scope
- sentiment inference
- strategy decisions
- AI calculation
- hidden backfill of missed trades

### 10. Dependencies
C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- known trade sequences
- side semantics
- duplicates
- late/out-of-order events
- reset/window boundaries
- restart/state behavior where applicable
- stale/degraded input
- deterministic rerun

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Known trade sequences produce expected flow/CVD values with explicit side/window/reset behavior and no AI calculation path.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C09 — Derivatives & Volatility

### 1. Title
Derivatives & Volatility

### 2. Engineering Goal
Implement verified deterministic derivatives, volatility, VWAP/session, and momentum context required by V1.

### 3. Learning Goal
Learn to separate provider semantics from derived formulas and to make warm-up/units/intervals explicit.

### 4. Why It Exists
OI, funding, basis and volatility are financially material inputs whose sign/interval mistakes can reverse interpretation.

### 5. Architecture Concept
Trusted candles/price/funding/OI → deterministic derived context → evidence.

### 6. Current System Before Card
C05/C06 provide trusted current and historical primitives. No derived derivatives/volatility truth is assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD/ADAPT formulas only after verifying provider units/signs/timestamps; fail closed on unknown semantics.

### 8. Implementation Scope
- open-interest change/context
- funding normalization with explicit interval
- basis only where required inputs/semantics are verified
- ATR
- realized volatility
- VWAP/session context
- bounded momentum measures required by later Cards
- warm-up state

### 9. Out of Scope
- option analytics
- AI forecasts
- strategy decisions
- guessed annualization/funding semantics
- future-data indicators

### 10. Dependencies
C05 + C06 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- known-value fixtures
- funding sign/interval
- OI units
- volatility/ATR/VWAP fixtures
- warm-up/missing data
- stale propagation
- timestamp boundaries
- determinism

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Required metrics match verified fixtures; units/signs/intervals/warm-up are explicit; unknown semantics never become trusted values.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C10 — Market Regime, Crowding & Liquidation Context

### 1. Title
Market Regime, Crowding & Liquidation Context

### 2. Engineering Goal
Build deterministic interpretable higher-level market-state evidence from C07–C09 without hiding uncertainty.

### 3. Learning Goal
Learn to compose indicators into versioned rules while distinguishing measured facts from heuristics.

### 4. Why It Exists
Regime/crowding/liquidation context can improve interpretation, but opaque scores create false certainty.

### 5. Architecture Concept
Liquidity + flow + derivatives/volatility → deterministic rule engine → regime/crowding/liquidation-context evidence.

### 6. Current System Before Card
C07–C09 provide tested component metrics. No higher-level regime or liquidation truth exists automatically.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
Use explicit versioned thresholds/rules. Preserve authoritative liquidation events separately from heuristic liquidation pressure.

### 8. Implementation Scope
- define regime states needed by V1
- define crowding context
- define liquidation-context categories
- preserve `AUTHORITATIVE_LIQUIDATION_EVENT` vs `HEURISTIC_LIQUIDATION_PRESSURE` vs `UNKNOWN`
- return `UNKNOWN` when evidence is insufficient
- retain contributing evidence

### 9. Out of Scope
- probability of price direction
- AI regime authority
- hidden confidence score
- promoting large trades/cascade heuristics to authoritative liquidation

### 10. Dependencies
C07 + C08 + C09 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- boundary thresholds
- insufficient evidence
- contradictory inputs
- regime transitions
- authoritative vs heuristic liquidation separation
- stale input
- determinism/versioning

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Regime/crowding/liquidation context is deterministic, interpretable, evidence-linked, versioned, returns UNKNOWN when required, and never converts heuristic liquidation into authoritative truth.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C11 — Whale Intelligence Foundation

### 1. Title
Whale Intelligence Foundation

### 2. Engineering Goal
Track a curated Hyperliquid BTC wallet set, lifecycle changes, exposure, and transparent Smart Money evidence.

### 3. Learning Goal
Learn why wallet size, realized performance, current exposure, and activity lifecycle must be separated.

### 4. Why It Exists
Whale behavior is valuable evidence but becomes dangerous when a large wallet is automatically treated as smart or predictive.

### 5. Architecture Concept
Verified wallet/watchlist source → normalized position/activity → lifecycle events → transparent scoring/exposure evidence.

### 6. Current System Before Card
C04/C05 provide provider access and quality semantics. No universal whale discovery or Smart Money truth is assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD a bounded curated V1 watchlist. ADAPT HyperStats methodology only as reference because its source code is not verified. Scoring must be transparent/versioned.

### 8. Implementation Scope
- curated wallet source/provenance
- normalize positions/activity
- OPEN/INCREASE/REDUCE/CLOSE/FLIP/LIQUIDATION lifecycle
- separate current exposure from recent activity
- realized/unrealized metrics where semantics are verified
- transparent Smart Money methodology
- aggregate BTC long/short/notional context

### 9. Out of Scope
- universal wallet discovery
- hidden grades
- copy trading
- wallet count as capital bias
- whale score as trade authority

### 10. Dependencies
C04 + C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- lifecycle transitions
- position/PnL fixtures where supported
- current vs activity windows
- score transparency/version
- source provenance
- stale/unavailable data
- no whale-to-trade bypass

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Curated whale state and lifecycle are reproducible and source-aware; scoring is transparent/versioned; large wallet is not equated with smart money; whale evidence cannot authorize trades.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C12 — Macro Intelligence

### 1. Title
Macro Intelligence

### 2. Engineering Goal
Normalize a bounded set of authoritative macro releases/events into traceable market evidence.

### 3. Learning Goal
Learn event-time normalization, revisions, source authority, and how macro facts differ from interpretation.

### 4. Why It Exists
Macro releases can materially affect crypto, but scraped or time-misaligned values can create false narratives.

### 5. Architecture Concept
Authoritative macro sources and applicable ETF institutional/market sources → normalized event/data contracts → verification/freshness → evidence.

### 6. Current System Before Card
C02/C05 provide typed/provenance foundations. No macro provider or broad economic calendar is assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD a small authoritative-source path first; ADAPT provider patterns only when they reduce work without weakening provenance.

### 8. Implementation Scope
- bounded V1 macro event types
- explicit asset-to-ETF applicability/coverage mapping metadata
- applicable ETF inflow/outflow, AUM, and volume data when an approved provider path exists
- source identity
- release/event timestamps and timezone normalization
- actual/consensus/previous/revision where available
- duplicate/revision handling
- freshness/availability
- evidence output
- explicit unsupported/unavailable/unverified ETF provider state without invented values

### 9. Out of Scope
- broad macro terminal
- AI-generated macro facts
- directional trade authority
- silent third-party substitution for primary facts

### 10. Dependencies
C02 + C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- timezone/release-time fixtures
- actual/forecast/previous/revision parsing
- duplicate/revision behavior
- missing/stale source
- provenance
- no macro-to-risk bypass

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Selected macro events and applicable ETF institutional/market data are normalized, time-correct, source-traceable and degradation-aware; revisions/duplicates and ETF coverage gaps are explicit; macro or ETF evidence cannot bypass Risk Gate. Exact ETF flow providers require separate verification before use.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C13 — Primary-Source News Verification

### 1. Title
Primary-Source News Verification

### 2. Engineering Goal
Separate incoming claims from verified facts using authoritative evidence and explicit verification states.

### 3. Learning Goal
Learn claim verification, temporal provenance, contradiction handling, and prompt-injection resistance for external content.

### 4. Why It Exists
Market rumors can move prices quickly; treating social/news text as fact would corrupt Signal Fusion and strategy evidence.

### 5. Architecture Concept
Claim or official ETF event → source search/verification → fact vs interpretation → verification state → evidence.

### 6. Current System Before Card
C02/C05 provide typed/provenance foundations. No claim is trusted merely because it is published.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD primary-source verification. Prioritize Federal Reserve, BLS, BEA, SEC and other Card-approved authorities for relevant high-impact claims.

### 8. Implementation Scope
- claim identity
- verification states `CONFIRMED/PARTIALLY_CONFIRMED/UNVERIFIED/MISLEADING/FALSE/OUTDATED`
- source/publication/event time
- official ETF regulatory, filing, issuer, and exchange/listing event verification where applicable
- supporting/contradicting primary evidence
- fact vs interpretation separation
- untrusted-content isolation
- bounded failure behavior
- numerical ETF inflow/outflow, AUM, and volume data remain outside news verification and require a separately verified provider path

### 9. Out of Scope
- general news sentiment as verification substitute
- social post as automatic fact
- directional trade signal from unverified news
- following instructions embedded in retrieved content

### 10. Dependencies
C02 + C05 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- fixture for every verification state
- conflicting evidence
- outdated claim
- source unavailable
- time/provenance
- malicious embedded instructions
- no unverified-to-confirmed promotion

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Verification-state fixtures pass; provenance and contradiction remain visible; applicable ETF official events remain source-verified or explicitly unverified; numerical ETF market data is not treated as news; external instructions cannot change policy; unverified high-impact claims remain uncertainty rather than directional truth.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C14 — Bedrock Provider & Structured Intelligence

### 1. Title
Bedrock Provider & Structured Intelligence

### 2. Engineering Goal
Add Amazon Bedrock behind a provider-neutral contract for structured evidence interpretation, never financial authority.

### 3. Learning Goal
Learn provider isolation, schema-constrained LLM output, bounded retries, failure handling, evidence grounding, latency and cost visibility.

### 4. Why It Exists
AI can synthesize whale/macro/news evidence, but free-form output or direct trade authority would make the system non-deterministic and hard to govern.

### 5. Architecture Concept
TraID evidence → AI provider contract → Bedrock adapter → validated structured intelligence → downstream evidence/fusion.

### 6. Current System Before Card
C11–C13 produce external evidence. No model output is trusted or required for deterministic financial calculations.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID provider contract and Bedrock adapter. ADAPT Quant Flow-style structured/fail-closed patterns. Core must not depend on a specific model family.

### 8. Implementation Scope
- provider-neutral request/response contract
- Bedrock adapter
- structured schema with supporting factors, contradicting factors, uncertainty, missing information, evidence refs
- timeout and bounded retry
- malformed/schema-invalid handling
- model/provider/prompt/schema metadata
- latency/token/cost capture where available
- explicit `AI_UNAVAILABLE`/failure state

### 9. Out of Scope
- AI leverage/position sizing
- AI Risk override
- direct model calls from Strategy/Risk
- unbounded agent loops
- invented evidence
- multi-agent orchestration

### 10. Dependencies
C11 + C12 + C13 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- valid structured response
- malformed JSON/schema
- timeout
- provider error
- missing evidence refs
- bounded retry
- prompt-injection/untrusted content
- AI failure cannot create trade authority

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Bedrock is replaceable behind a TraID contract; structured outputs are validated/evidence-linked; failures are explicit and fail closed; AI cannot authorize or override deterministic financial controls.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C15 — Evidence Registry & Signal Fusion

### 1. Title
Evidence Registry & Signal Fusion

### 2. Engineering Goal
Create addressable evidence and deterministic fusion that preserves support, contradiction, quality, relevant coverage gaps, missing information, and uncertainty.

### 3. Learning Goal
Learn why aggregation must retain provenance and why alignment is not calibrated probability.

### 4. Why It Exists
Without an Evidence Registry, explanations become untraceable; without controlled fusion, contradictory sources can disappear inside an opaque score.

### 5. Architecture Concept
Analytics + whale + macro + verified news + validated applicable ETF evidence + AI evidence → Evidence Registry → deterministic Signal Fusion → typed fused context.

### 6. Current System Before Card
C07–C14 produce independent evidence. No unified score should be assumed.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID registry/fusion; selectively ADAPT CryptoRadar alignment/contradiction ideas. Semantic rule: `Alignment != probability.`

### 8. Implementation Scope
- evidence IDs/types/source/time/quality/version
- selected asset and ETF-coverage applicability/mapping metadata
- ETF regulatory/issuer/listing evidence and validated ETF flow/AUM/volume evidence when available
- supporting and contradicting roles
- missing evidence representation
- missing-information and coverage-gap state, distinct from supporting or contradicting evidence
- fusion configuration/version
- deterministic alignment/strength only where explicitly defined
- retain every contributing evidence reference
- quality/freshness weighting only if transparent/tested

### 9. Out of Scope
- win probability without calibration
- LLM-only fusion
- dropping contradictions
- Risk/Strategy decisions
- hidden confidence formula

### 10. Dependencies
C07–C14 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- same input same result
- support/contradiction fixtures
- stale/missing evidence
- partial category coverage, unavailable provider, and recovery fixtures
- relevant ETF coverage applicable/unavailable/stale/delayed/incomplete/unverified fixtures
- absence of evidence is neither positive nor negative evidence; incomplete high-impact coverage can reduce decision readiness
- source traceability
- version/config behavior
- no evidence loss
- alignment-not-probability contract

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Every fused contribution is traceable; support, contradiction, missing/stale evidence, and coverage gaps including relevant ETF gaps remain visible; identical evidence/config produces identical result; alignment is never mislabeled as probability and missing evidence is never directional evidence.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C16 — Typed Strategy Engine

### 1. Title
Typed Strategy Engine

### 2. Engineering Goal
Implement one explicit versioned deterministic BTC strategy family using validated fused evidence and market-valid setup structure.

### 3. Learning Goal
Learn to separate candidate-generation rules from risk authorization and to make strategy behavior replayable.

### 4. Why It Exists
TraID needs a concrete decision rule to evaluate, but multiple opaque strategies would add complexity before measurement.

### 5. Architecture Concept
Fused context → typed deterministic Strategy Engine → market-valid Entry/invalidation/Stop/Target setup or `NO_SETUP` → Risk Gate later.

### 6. Current System Before Card
C15 supplies traceable fused evidence. No strategy may infer permission to trade.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD one bounded strategy family. ADAPT typed detector/registry patterns only where useful. No Bedrock call inside deterministic evaluation.

### 8. Implementation Scope
- typed strategy input/output
- explicit rule/config thresholds
- strategy version
- required evidence/quality conditions
- support/contradiction handling
- `NO_SETUP` reason codes
- evidence references
- required coverage/quality policy is explicit per Strategy/configuration; insufficient required evidence remains `NO_SETUP`
- applicable ETF coverage policy is explicit; relevant missing/stale/unavailable/unverified ETF evidence remains `NO_SETUP` without directional inference
- Entry, invalidation/Stop, and Target come from the valid deterministic market/strategy structure

### 9. Out of Scope
- Risk approval
- live execution
- AI strategy authority
- automatic optimization
- many strategies before baseline evaluation
- hidden mutable thresholds
- moving or fabricating Stop/Target merely to satisfy a downstream percentage policy

### 10. Dependencies
C15 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- rule truth tables
- threshold boundaries
- missing/stale evidence
- contradictory evidence
- identical-input determinism
- version/config behavior
- missing, stale, unavailable, and unverified required evidence fail closed without directional inference
- applicable ETF evidence follows the same fail-closed quality/provenance policy
- market-valid setup structure is preserved; no Stop/Target is forced to a percentage distance
- no AI call
- no direct `TRADE_CANDIDATE` bypass

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
One BTC strategy family is typed, deterministic, versioned, evidence-linked and fully covered at boundaries; explicit coverage policy including applicable ETF evidence is respected; market-valid Entry/Stop/Target structure is preserved; insufficient/stale/unavailable required evidence yields the existing `NO_SETUP` contract; it cannot bypass Risk.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C17 — Deterministic Risk Gate

### 1. Title
Deterministic Risk Gate

### 2. Engineering Goal
Make promotion from valid setup to `TRADE_CANDIDATE` possible only through a mandatory deterministic fail-closed Risk Gate that enforces the versioned V1 Setup Risk Policy.

### 3. Learning Goal
Learn to design non-bypassable consequential controls with explicit reason codes and boundary tests.

### 4. Why It Exists
This is TraID's most important financial authority boundary. AI, whales, news, fusion, Strategy, API, or UI must never promote a candidate independently.

### 5. Architecture Concept
Typed Strategy Candidate + required trusted context + versioned V1 Setup Risk Policy → deterministic Risk Gate → `TRADE_CANDIDATE | NO_TRADE` + reasons.

### 6. Current System Before Card
C16 creates strategy setups only. No component is authorized to produce a trade candidate before this Card.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID-owned Risk Gate. It is mandatory, deterministic, versioned, reason-coded, fail-closed and structurally non-bypassable. The V1 Setup Risk Policy fixes setup leverage at 2x, permits Net Loss only when `<= 10%` of the hypothetical position, and requires Net Profit Target `>= 20%` of the hypothetical position. These are Net P&L thresholds after applicable verified costs, not raw price-distance rules.

### 8. Implementation Scope
- typed risk input/output
- required quality/evidence checks
- risk policy/config validation
- financial bounds required by approved strategy design
- fixed 2x setup leverage
- maximum Net Loss `<= 10%` and minimum Net Profit Target `>= 20%`
- Net P&L accounting for applicable verified fees, funding, slippage, and execution costs
- rejection with existing `RISK_REJECTED` semantics when numeric policy or required cost inputs fail
- reason codes
- invalid/missing/stale failure behavior
- required coverage-policy failure remains explicit and fail-closed using existing reason semantics
- single promotion path
- audit/version metadata

### 9. Out of Scope
- order execution
- AI override
- whale/news override
- silent default risk config
- unbounded leverage/sizing
- account balance, account-level risk, or position-size decisions
- moving/fabricating Entry, Stop, or Target to satisfy the policy
- UI/API alternative promotion path

### 10. Dependencies
C16 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- every rejection path
- boundary values
- invalid/missing config
- stale/missing required evidence
- AI unavailable where relevant
- bypass/alternate-path tests
- determinism
- reason codes
- fixed-2x, 10% Net Loss, and 20% Net Profit Target boundary cases
- cost-inclusive Net P&L and unavailable/unverified required-cost failure
- policy pass does not guarantee `TRADE_CANDIDATE` when other Risk checks fail
- missing/stale/untrusted required context remains rejectable; no coverage gap is converted into directional approval
- promotion only through gate

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
All promotion paths require the Risk Gate; bypass tests pass; invalid/stale/missing/insufficient required inputs and policy failures fail closed to `NO_TRADE` using existing reason semantics; valid output is reason-coded/versioned and deterministic. The policy accepts only fixed 2x leverage, Net Loss `<= 10%`, and Net Profit Target `>= 20%` after applicable verified costs; it does not force raw price distances or guarantee `TRADE_CANDIDATE`.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C18 — Backtest Engine Integration

### 1. Title
Backtest Engine Integration

### 2. Engineering Goal
Replay the same Strategy and Risk semantics over historical canonical data with structural anti-lookahead and explicit financial accounting.

### 3. Learning Goal
Learn how event timing, fills, fees, funding, liquidation, ambiguity, and P&L reconciliation determine whether a backtest is trustworthy.

### 4. Why It Exists
A profitable but temporally invalid or financially inconsistent backtest is worse than no backtest.

### 5. Architecture Concept
Historical replay → point-in-time evidence → same Strategy → same Risk Gate → deterministic execution simulation → accounting/evaluation records.

### 6. Current System Before Card
C06 provides replay data; C16/C17 provide deterministic decision logic. No historical engine may use future outcomes as inputs.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
ADAPT strong Hyperliquid Backtester invariants into TraID contracts; do not copy semantics without verification.

### 8. Implementation Scope
- point-in-time context construction
- structural anti-lookahead
- explicit decision/fill timing
- fees
- funding
- slippage model if approved
- stop/target handling
- same-bar `STOP FIRST` unless higher-resolution proof
- liquidation assumptions
- P&L reconciliation
- deterministic rerun
- dataset/config/engine/strategy/risk versions
- the same versioned Setup Risk Policy and Net P&L cost semantics used by decision-support evaluation

### 9. Out of Scope
- optimistic ambiguous fills
- future news/macro revisions
- automatic parameter optimization
- institutional execution simulator
- live execution

### 10. Dependencies
C06 + C16 + C17 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- future-access/lookahead blockers
- next-event/fill timing
- fee fixtures
- funding fixtures
- liquidation fixtures
- same-bar STOP FIRST
- P&L reconciliation
- fixed-2x/10%/20% policy boundary and rejection behavior
- fees, funding, slippage, and applicable execution-cost availability; required unknown costs fail closed
- gap/incomplete-bar behavior
- deterministic rerun

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Backtest uses the same Strategy/Risk semantics and Setup Risk Policy, cannot access future data, resolves ambiguity pessimistically, reconciles cost-inclusive Net P&L accounting, records versions, and reproduces identical controlled runs.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C19 — Outcome Tracking

### 1. Title
Outcome Tracking

### 2. Engineering Goal
Measure post-candidate outcomes without rewriting the original decision context.

### 3. Learning Goal
Learn closed-loop evaluation using MFE, MAE, realized/simulated results, horizons, and immutable decision provenance.

### 4. Why It Exists
TraID cannot learn whether its evidence/strategy/risk process is useful without tracking what happened afterward.

### 5. Architecture Concept
Original candidate snapshot → later market observations → Outcome record → evaluation.

### 6. Current System Before Card
C17/C18 produce live-candidate semantics and historical simulated outcomes. Original decision context must remain immutable.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID outcome ownership; ADAPT CryptoRadar's MFE/MAE/outcome-ledger methodology, not its architecture.

### 8. Implementation Scope
- candidate/outcome linkage
- original timestamp/evidence/version/config references
- MFE/MAE
- target/stop observations where defined
- realized/simulated result
- evaluation horizon
- open/unresolved state
- data-quality context

### 9. Out of Scope
- rewriting original evidence
- using future outcome in original Strategy/Risk
- performance-based hidden strategy mutation
- UI polish

### 10. Dependencies
C17 + C18 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- candidate linkage
- MFE/MAE fixtures
- open/unresolved outcomes
- horizon boundaries
- immutable original context
- version/provenance retention
- historical/live separation

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Outcomes are linked, reproducible and version-aware; MFE/MAE/result fixtures pass; unresolved outcomes are explicit; original decision inputs remain immutable.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C20 — Evaluation Registry

### 1. Title
Evaluation Registry

### 2. Engineering Goal
Create a versioned registry for measured data, analytics, AI, strategy, risk, backtest, outcome, system, latency, cost, and regression results.

### 3. Learning Goal
Learn evaluation-before-complexity and how to compare versions without anecdotal conclusions.

### 4. Why It Exists
Without a registry, later tuning or ML adoption would be driven by impressions rather than measurable evidence.

### 5. Architecture Concept
Versioned runs + datasets/config + component metrics/failures → Evaluation Registry → comparable evidence.

### 6. Current System Before Card
C18/C19 provide replay and outcome records. No single metric proves system quality.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID's registry. Measure correctness/failures/reproducibility as well as market-performance metrics.

### 8. Implementation Scope
- evaluation run identity
- dataset/config/component versions
- candidate/trade/NO_TRADE counts and reasons
- return/win rate/profit factor/expectancy/drawdown/average R where meaningful
- fees/funding/liquidations
- MFE/MAE distributions
- data/provider/AI/Risk failures
- latency/cost where available
- regression/reproducibility fields

### 9. Out of Scope
- automatic optimization
- ML training pipeline
- declaring strategy good from one metric
- changing Strategy/Risk during evaluation

### 10. Dependencies
C18 + C19 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- registry schema
- version linkage
- metric calculation fixtures where owned
- missing metric handling
- repeated-run comparability
- failure/rejection recording
- reproducibility identity

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
At least one evaluation run can identify its data/config/component versions and measured results/failures; comparisons are reproducible and do not rely on anecdotal claims.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C21 — Decision-Support API

### 1. Title
Decision-Support API

### 2. Engineering Goal
Expose stable typed read-only application contracts without duplicating Core Strategy/Risk logic, including relevant ETF evidence and explicit coverage gaps.

### 3. Learning Goal
Learn API boundary design, degraded-state representation, schema stability, and capability restriction.

### 4. Why It Exists
The Dashboard and clients need a clean access layer, but an API must not become a second business-logic or execution engine.

### 5. Architecture Concept
Core/application services → typed FastAPI read-only contracts → clients.

### 6. Current System Before Card
C05–C20 provide Core capabilities. No API endpoint is authorized to place/modify/cancel orders.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD FastAPI contracts; optionally ADAPT simple response-envelope ideas. Keep provider-specific payloads and execution capabilities out.

### 8. Implementation Scope
- status/market/analytics/whales/macro/news/ETF/intelligence/signals/strategy/risk/outcomes/evaluations surfaces as needed
- typed schemas
- degraded/quality/provenance/reason exposure
- explicit source/category coverage gaps and availability state without implying complete market coverage
- relevant ETF evidence, applicability metadata, provenance/quality, and explicit ETF coverage gaps where applicable
- validation/error responses
- read-only capability checks

### 9. Out of Scope
- order endpoints
- wallet operations
- live leverage/position-size mutation
- duplicate Strategy/Risk logic
- one giant untyped payload

### 10. Dependencies
C05–C20 required capabilities COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- schema/contract tests
- bad requests
- degraded responses
- provenance/quality visibility
- risk reason visibility
- missing source, partial coverage, unavailable provider, and recovery visibility
- provider-neutral responses
- no write/execution routes

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Required read-only contracts are typed and tested; degraded/provenance/coverage/risk state and relevant ETF evidence/gaps are accessible; Core logic is not duplicated; no execution/write capability or complete-market claim exists.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C22 — Dashboard

### 1. Title
Dashboard

### 2. Engineering Goal
Build a clean human decision-support Dashboard with progressive disclosure of evidence, uncertainty, quality, Strategy/Risk, outcomes, relevant ETF intelligence, and ETF coverage gaps.

### 3. Learning Goal
Learn information hierarchy for high-density market intelligence without hiding uncertainty or overwhelming the user.

### 4. Why It Exists
A correct backend is not useful if the human cannot quickly understand what is known, degraded, supporting, contradicting, or rejected.

### 5. Architecture Concept
Read-only API → overview → drill-down evidence/context/outcomes/status.

### 6. Current System Before Card
C21 exposes typed read-only data. UI must not invent new financial logic.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID UI from audited UX patterns; do not copy entire dashboards or introduce desktop frameworks without need.

### 8. Implementation Scope
- BTC overview
- data/feed quality
- key deterministic analytics
- whale/macro/news/asset-specific ETF evidence
- support/contradiction/uncertainty
- Strategy result
- Risk Gate result/reasons
- outcome/evaluation/status drill-down
- provenance reachable through progressive disclosure
- relevant ETF applicability, evidence, and coverage gaps reachable through progressive disclosure

### 9. Out of Scope
- execution controls
- UI-calculated Strategy/Risk
- giant terminal with every metric
- Tauri by default
- hidden degraded state

### 10. Dependencies
C21 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- degraded state obvious
- NO_TRADE reasons visible
- provenance reachable
- contradictions visible
- no execution controls
- basic interaction/responsiveness/accessibility where practical

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
A human can understand selected-asset context and why a setup was accepted/rejected without raw logs; relevant ETF evidence/gaps, uncertainty/degradation/provenance are visible; no execution controls or duplicate decision logic exist.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C23 — Observability, Audit & Failure Recovery

### 1. Title
Observability, Audit & Failure Recovery

### 2. Engineering Goal
Make consequential decisions, provider failures, degraded data, AI failures, and process recovery diagnosable and traceable.

### 3. Learning Goal
Learn lightweight observability, audit correlation, bounded recovery, checkpoints, and failure-state preservation.

### 4. Why It Exists
A market system that silently reconnects, drops evidence, or loses decision context cannot be trusted.

### 5. Architecture Concept
Components/providers → structured health/events/audit → bounded recovery/checkpoint → observable state.

### 6. Current System Before Card
C04–C22 create operational components. Their individual logs do not automatically form coherent system observability.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD a lightweight TraID-owned layer; ADAPT useful health/checkpoint patterns. Avoid a heavy observability stack until measured need exists.

### 8. Implementation Scope
- status/last_success/last_failure/latency/error_count/data_age/source/version
- source/category availability, freshness, coverage degradation/recovery, and coverage-related decision reasons
- decision audit with evidence/strategy/risk/AI/dataset/config refs
- bounded provider reconnect visibility
- AI/source failure visibility
- process restart/checkpoint recovery where required
- degraded state preservation

### 9. Out of Scope
- Kubernetes/large telemetry stack by default
- silent fallback
- infinite retries
- rewriting failed history

### 10. Dependencies
Relevant C04–C22 capabilities COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- WebSocket disconnect
- REST/provider outage
- Bedrock outage
- macro/news outage
- stale data
- missing/partial coverage and unavailable provider
- process restart
- bounded recovery
- audit correlation
- failure remains visible

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Required failure scenarios are observable; decision audit links consequential inputs/versions/results; coverage degradation/recovery is visible; recovery is bounded and cannot hide degraded state or invent missing evidence.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C24 — Security & Secrets Hardening

### 1. Title
Security & Secrets Hardening

### 2. Engineering Goal
Enforce least privilege, secret isolation, untrusted-content controls, prompt-injection defenses, redaction, and the read-only V1 capability boundary.

### 3. Learning Goal
Learn why AI/data security is architectural: capabilities and authorization matter more than prompt wording alone.

### 4. Why It Exists
TraID consumes untrusted external content and cloud/provider credentials; security failure could leak secrets or expand capability beyond V1.

### 5. Architecture Concept
Untrusted inputs → validation/isolation → least-privilege services → read-only capabilities → audited failures.

### 6. Current System Before Card
C13/C14/C21 establish external content, AI and API surfaces. Security must verify the whole V1 boundary rather than assume each component is safe.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID security controls using Playbook principles; use standard secure AWS credential mechanisms; no trading credentials/private keys.

### 8. Implementation Scope
- secret scanning
- `.env` exclusion and safe examples
- credential/log redaction
- least-privilege provider access
- input validation
- prompt-injection/adversarial external-content tests
- path/URL/redirect controls where applicable
- read-only API capability verification

### 9. Out of Scope
- wallet private-key architecture
- exchange trading permissions
- production secrets in repository
- model instructions overriding system policy
- unnecessary security platform

### 10. Dependencies
C13 + C14 + C21 and relevant V1 surfaces COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- secret scan
- redaction
- malicious external instructions
- invalid input
- permission/capability boundary
- no execution endpoint
- credential mechanism/config checks

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Security tests pass; no real secrets/trading credentials/private keys/execution endpoints are required; untrusted/model content cannot become system authority; least privilege is evidenced.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C25 — Docker, CI & Release Gate

### 1. Title
Docker, CI & Release Gate

### 2. Engineering Goal
Create a reproducible release candidate whose automated gates block regressions in critical financial, data, AI, security and governance invariants.

### 3. Learning Goal
Learn how CI turns project rules into executable release policy.

### 4. Why It Exists
Manual confidence is insufficient for a portfolio-quality financial intelligence system.

### 5. Architecture Concept
Clean checkout → build/container → lint/type/test/security/invariants → blocking release decision.

### 6. Current System Before Card
C01–C24 establish implementation and tests. Release automation must consume those tests rather than invent a separate truth.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD minimal Docker/GitHub Actions release path; ADAPT useful DevOps patterns only. Critical tests are blocking.

### 8. Implementation Scope
- Dockerfile and minimal compose only if useful
- clean dependency/install path
- GitHub Actions
- test/lint/type/security jobs
- critical financial/Risk/anti-lookahead/AI fail-closed blockers
- documented local equivalent commands
- artifact/version identification

### 9. Out of Scope
- five-service topology
- Redis/Kafka for CI
- nonblocking critical tests
- deployment platform expansion without need

### 10. Dependencies
C01–C24 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- clean checkout/install
- Docker build/run
- CI workflow
- full required suite
- secret scan
- critical gate failure simulation where practical
- documented local commands

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Clean checkout builds and runs; Docker/CI execute required quality/security suites; failures in financial invariants, Risk bypass, anti-lookahead, AI fail-closed or security block release; setup is reproducible.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C26 — Golden Case End-to-End Validation

### 1. Title
Golden Case End-to-End Validation

### 2. Engineering Goal
Prove TraID as one coherent traceable BTC system with a controlled success path and at least one degraded/failure path.

### 3. Learning Goal
Learn end-to-end validation: local component PASS results are insufficient until the full chain is reproducible.

### 4. Why It Exists
The Golden Case is the strongest V1 evidence that architecture, data trust, AI boundary, Strategy, Risk, outcome and evaluation work together.

### 5. Architecture Concept
Source → Canonical Data → Quality → Analytics → External Evidence → AI → Registry/Fusion → Strategy → Risk → API/UI → Outcome → Evaluation.

### 6. Current System Before Card
C25 produces a release candidate with blocking automated gates. End-to-end product trace still needs explicit proof.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD TraID-owned Golden Case; no external repository owns acceptance.

### 8. Implementation Scope
- one controlled BTC success case
- one degraded/failure case
- capture source/data snapshot identity
- capture quality/provenance
- capture supporting/contradicting evidence
- capture AI contribution/failure state
- capture Strategy rules
- capture Risk reasons
- capture versions/config
- capture outcome/evaluation
- prove replay

### 9. Out of Scope
- cherry-picking only profitable examples
- manual undocumented steps
- live trade execution
- changing rules to make Golden Case pass

### 10. Dependencies
C25 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- answer all ten Golden Case traceability questions
- end-to-end replay
- degraded/failure path
- version/config/data identity
- Risk/no-bypass proof
- UI/API visibility

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
Stored evidence answers all ten Golden Case questions; the consequential path is replayable; at least one degraded/failure path fails safely and remains observable; no rules were weakened to obtain PASS.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

## V1-C27 — V1 Documentation & Demo

### 1. Title
V1 Documentation & Demo

### 2. Engineering Goal
Make TraID V1 reproducible, teachable, reviewable and demonstrable by a new developer or portfolio reviewer.

### 3. Learning Goal
Learn to communicate architecture, limitations, evidence, setup, evaluation and safety without overstating capability.

### 4. Why It Exists
A production-oriented portfolio project must be understandable and reproducible by someone who did not build it.

### 5. Architecture Concept
Verified repository/evidence → durable developer docs + architecture/demo narrative + reproducible runbook.

### 6. Current System Before Card
C26 provides final validated system evidence. Documentation must describe that reality, not planned features.

Repository reality must be re-inspected when this Card actually starts. This section is a planned dependency-state contract, not permission to ignore contradictory repository evidence.

### 7. Design Decision
BUILD docs from verified repository state and evidence only. Preserve known limitations and read-only scope.

### 8. Implementation Scope
- README/setup/run/test instructions
- architecture and component ownership
- data/source/provenance explanation
- AI/Strategy/Risk authority boundaries
- backtest/outcome/evaluation explanation
- Golden Case demo steps
- known limitations/deferred work
- security/read-only statement
- new-developer verification path

### 9. Out of Scope
- marketing claims unsupported by evidence
- future features presented as implemented
- live execution demo
- hiding blockers/limitations

### 10. Dependencies
C26 COMPLETE.

All dependencies must be proven from canonical Evidence/repository reality before implementation.

### 11. Tests / Evaluation
- fresh-developer setup walkthrough where feasible
- documented command verification
- link/path checks
- demo reproduction
- consistency against repository/Evidence/Golden Case
- no unsupported capability claims

Required rule: run the narrowest relevant tests during bounded implementation, then all relevant regression/financial/data/AI/security tests required by affected contracts before closure. Do not claim PASS for an unexecuted test.

### 12. Exit Gate
A new developer can set up, run, test, verify and understand V1 from repository docs; the demo reproduces the validated path; limitations and read-only boundaries are explicit; documentation matches evidence.

Closure additionally requires `CARD_QUALITY_GATE: PASS`, Evidence update, repository/Git review, and applicable human approval.

### 13. What We Learned
`Pending — fill only from actual implementation and validation evidence.`

### 14. Completion Evidence
`Pending — fill only after the exact Exit Gate is proven.`


---

# Final Contract Rule

For every Card:

```text
READ ROADMAP
→ READ ALL 14 SECTIONS
→ INSPECT REPOSITORY + EVIDENCE
→ RECONCILE CURRENT SYSTEM
→ INSPECT-ONLY CONTRACT MAP / RISK MAP
→ HUMAN START APPROVAL
→ ROADMAP_ALIGNMENT_GATE
→ ONE BOUNDED STEP
→ IMPLEMENT
→ FOCUSED VALIDATION
→ RELEVANT REGRESSION / INVARIANTS
→ EVIDENCE
→ CHECKPOINT
→ REPEAT IF CARD STILL IN SCOPE
→ EXIT GATE
→ CARD_QUALITY_GATE
→ LEARNING RECORD
→ HUMAN CLOSURE / DELIVERY APPROVAL
→ STOP
```

Prompt text, chat memory, an external repository, or a successful-looking output never overrides this contract.
