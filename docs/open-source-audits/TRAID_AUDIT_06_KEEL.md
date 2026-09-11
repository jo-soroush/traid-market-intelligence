# Traid Audit 06 — Keel

**Project:** `keel-trade/keel-trade`  
**Audit date:** 2026-09-02  
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`  
**Audit type:** Public GitHub static audit  
**Runtime execution:** NOT PERFORMED  
**License:** MIT  
**Repository maturity:** Alpha / public mirror; 13 commits observed during prior inspection  
**Overall recommendation:** **REFERENCE ONLY + selective ADAPT**, with very high architectural value for Traid's Strategy Engine, deterministic execution boundary, backtesting/live parity and safety controls.

> Keel is particularly important because its core philosophy closely matches Traid: agents may help create or compose strategies, but deterministic software compiles, validates, backtests and executes them. This is much closer to our governance model than systems where an LLM directly owns trade authorization.

## Executive Finding

Keel is an agent-native quantitative trading framework focused on composing trading strategies from typed components and compiling them into deterministic artifacts.

Its strongest architectural idea is:

`Agent/User Intent → Typed Strategy Graph → Validation/Compilation → Deterministic Strategy Artifact → Backtest or Live Execution`

The same compiled strategy artifact is intended to be used in backtesting and live execution.

This matters to Traid because it addresses a major failure mode in AI trading systems: letting an LLM generate or alter execution logic at runtime.

Keel also exposes:

- Hyperliquid-oriented trading support
- real funding / price / slippage considerations
- walk-forward analysis
- Monte Carlo analysis
- typed strategy composition
- MCP / CLI / SDK interfaces
- explicit opt-in for live-write operations
- local arming before live writes
- mirror allowlist/denylist governance files
- tests and security-oriented repository files

However, the public repository is an **alpha public mirror**, and documentation indicates that parts of the underlying engine/component ecosystem are actively developed elsewhere/private. Therefore we cannot assume that every advertised capability is fully available in the public repo.

For Traid, Keel is currently the **strongest architecture reference for Strategy Engine boundaries**, but not yet an approved base dependency.

---

## 1. Project Purpose

Keel aims to make quantitative strategy construction usable by both humans and agents while keeping actual trading behavior deterministic.

Its design focuses on:

- composing strategy components
- compiling strategy graphs
- deterministic backtesting
- live execution
- agent/tool interfaces
- safety around live writes

**Traid implication:** Direct overlap with Strategy Engine and governed agent boundaries.

**Classification:** **REFERENCE ONLY / ADAPT**

---

## 2. Overall Architecture

Core conceptual architecture:

`User / Agent / MCP / CLI / SDK → Strategy Composition → Typed Graph → Compiler → Deterministic Artifact → Backtest / Live Engine`

The key separation is between:

- **strategy authoring/composition**
- **strategy execution**

The agent is not supposed to be the execution engine.

**Traid implication:** Excellent match.

Our equivalent should be:

`Bedrock Agent → structured evidence/strategy proposal → deterministic Strategy Engine → deterministic Risk Gate`

**Classification:** **ADAPT — VERY HIGH PRIORITY**

---

## 3. Repository Structure

Previously observed public repository areas include:

- `keel/`
- `pipeline_engine/`
- `scripts/`
- `tests/`
- `pyproject.toml`
- `.gitleaks.toml`
- mirror allowlist/denylist files
- `AGENTS.md`

The repository is presented as a public mirror of a Python package/project ecosystem.

**Concern:** some underlying engine/component development is associated with a private monorepo.

**Traid implication:** We must distinguish public reusable implementation from product claims.

**Classification:** **EVALUATE**

---

## 4. Data Ingestion

Keel is not primarily a general market-data warehouse.

Its documented trading/backtest functionality uses real market inputs including:

- Hyperliquid pricing
- funding
- slippage-related data

**Cannot verify comprehensively:** full raw ingestion architecture, WebSocket event storage, historical data coverage and data-gap handling.

**Traid implication:** Not a replacement for our Hyperliquid Data Layer.

**Classification:** **REFERENCE ONLY**

---

## 5. REST / WebSocket / Connectivity

Keel provides interfaces through:

- MCP
- CLI
- SDK

Live exchange connectivity exists conceptually for trading.

**Cannot verify sufficiently:** detailed Hyperliquid WebSocket reconnect/backoff, REST fallback, gap recovery and rate-limit handling.

**Classification:** **Cannot verify / not primary reuse target**

---

## 6. Database and Storage

Keel's main public design focus is strategy artifacts/pipelines rather than a Traid-style market intelligence store.

**Cannot verify comprehensively:**

- durable market data schema
- event history
- position-history database
- audit database
- retention

**Traid implication:** Traid must own its data/evidence storage.

**Classification:** **REFERENCE ONLY**

---

## 7. Analytics

Keel supports strategy components and quantitative analysis, but it is not the strongest source in our audit set for market microstructure analytics.

For Traid:

- Project 4 remains stronger for order book / flow / volatility / regime.
- Keel is stronger for strategy representation and evaluation.

**Classification:** **REFERENCE ONLY**

---

## 8. Signal Engine

Signals are expressed through typed strategy components/graphs rather than free-form LLM prose.

**Analysis:** This is highly valuable.

A signal/setup should become a typed object that can be validated, tested and replayed.

**Traid implication:** Our Strategy Engine should accept structured evidence and deterministic rules rather than natural-language trade instructions.

**Classification:** **ADAPT — HIGH PRIORITY**

---

## 9. Whale / Smart Money Intelligence

No major HyperStats-style whale intelligence system is central to Keel.

**Classification:** **NOT IMPLEMENTED / not a reuse target**

---

## 10. News / Macro / External Intelligence

No major primary-source News Verification or Macro Intelligence layer is central to Keel.

**Classification:** **NOT IMPLEMENTED for Traid purposes**

---

## 11. Strategy Engine

This is Keel's strongest area.

### Key concepts

- typed strategy composition
- strategy graph
- compile step
- deterministic compiled artifact
- same artifact used for backtest/live
- components rather than arbitrary free-form code
- agent-friendly interfaces without giving the agent unrestricted execution semantics

### Why this matters

A strategy should be:

- explicit
- versioned
- testable
- reproducible
- serializable
- auditable
- executable without LLM interpretation

**Traid implication:** Very strong pattern for our Strategy Engine.

**Classification:** **ADAPT — VERY HIGH PRIORITY**

---

## 12. Backtesting

Documented capabilities include:

- backtesting
- walk-forward analysis
- Monte Carlo analysis
- deterministic execution of compiled strategy artifacts

Most important architectural claim:

**the same compiled strategy artifact is used for backtest and live.**

This reduces research/live drift.

**Cannot verify by runtime:** exact correctness, lookahead protections and all simulation assumptions.

**Classification:** **ADAPT pattern, verify implementation**

---

## 13. Trading Realism

Keel explicitly emphasizes real-world considerations such as:

- funding
- price
- slippage

and attempts to keep backtest/live semantics aligned.

**Strong point:** This is much better than a toy backtester using only candle-close prices.

**Cannot verify:** exact fee/fill/latency/liquidation implementation in this audit.

**Classification:** **REFERENCE / ADAPT after tests**

---

## 14. AI / LLM Layer

Keel is designed to be agent-native.

Agents can interact through MCP/tools and compose strategies.

But the critical principle is that agent output is converted into typed/deterministic artifacts rather than allowing an LLM to directly control execution logic.

**Traid implication:** Excellent fit with Bedrock Agents.

**Classification:** **ADAPT architecture pattern**

---

## 15. Deterministic vs AI Boundaries

This is arguably Keel's most valuable contribution.

### Keel pattern

`Agent creates/composes → compiler validates → deterministic engine executes`

### Traid desired pattern

`Bedrock analyzes evidence → Signal Fusion/Strategy receives structured data → deterministic Strategy Engine evaluates → deterministic Risk Gate authorizes/blocks`

**Decision:** Strongly adopt the boundary principle.

**Classification:** **ADAPT — CRITICAL**

---

## 16. Risk Management

Keel includes strategy/execution constraints and live-operation safety concepts.

The typed/compiled approach itself reduces risk from arbitrary agent behavior.

**Cannot verify:** complete portfolio-level risk management framework equivalent to Traid's leverage/position/stop/RR/freshness/volatility gate.

**Classification:** **REFERENCE ONLY**

---

## 17. Risk Gate

Keel has important safety controls but no verified exact equivalent of Traid's mandatory deterministic Risk Gate.

Live-write operations require explicit opt-in/local arming, which is valuable operational governance.

But Traid's gate must independently evaluate:

- leverage
- position risk
- stop
- R/R
- volatility
- liquidity
- slippage
- data freshness
- abnormal market state

**Classification:** **BUILD Traid Risk Gate; ADAPT arming pattern**

---

## 18. Dashboard

Keel is not primarily a dashboard/product-UI reference.

Its value is developer/agent/strategy infrastructure.

**Classification:** **LOW PRIORITY / REFERENCE ONLY**

---

## 19. Logging

Repository/project tooling suggests engineering-oriented operation, but comprehensive structured logging was not established in this static audit.

**Classification:** **Cannot verify comprehensively**

---

## 20. Monitoring

Walk-forward/backtest/evaluation capabilities support strategy-performance monitoring conceptually.

**Cannot verify:** production infrastructure monitoring stack.

**Traid implication:** Outcome monitoring remains better informed by CryptoRadar's explicit outcome ledger.

**Classification:** **REFERENCE ONLY**

---

## 21. Data Quality

Keel's deterministic compilation does not by itself solve market-data quality.

**Cannot verify:** canonical freshness states, source provenance and gap detection equivalent to Traid requirements.

**Traid implication:** Data quality must remain upstream and independent.

**Classification:** **BUILD in Traid**

---

## 22. Tests

A `tests/` directory is present in the public repository.

**Positive:** The framework's typed/deterministic philosophy is naturally testable.

**Cannot verify:** complete test inventory and runtime pass rate in this audit.

**Classification:** **EVALUATE**

---

## 23. Test Quality / Coverage

No verified coverage percentage.

Before adapting any strategy compiler/execution code, Traid should require tests for:

- deterministic compilation
- serialization round-trip
- identical backtest/live semantics
- invalid graph rejection
- unsupported component rejection
- risk-boundary enforcement
- agent malformed-output rejection

**Classification:** **INSUFFICIENTLY VERIFIED**

---

## 24. Deployment

Keel exposes Python package/tooling interfaces and is intended to work through CLI/SDK/MCP.

**Cannot verify:** full production deployment architecture.

**Traid implication:** Its library-oriented approach is more attractive than importing a large distributed service.

**Classification:** **REFERENCE / ADAPT**

---

## 25. Configuration

Configuration exists through project/package mechanisms and strategy definitions.

Typed configuration is preferable to free-form prompts.

**Traid implication:** Strategy thresholds and parameters should be explicit, versioned and validated.

**Classification:** **ADAPT**

---

## 26. Secrets Management

Positive repository evidence:

- `.gitleaks.toml`
- explicit live-write arming/opt-in philosophy

This shows attention to secret leakage and dangerous operations.

**Cannot verify:** complete secret storage/encryption/rotation.

**Traid implication:** Adopt secret scanning and explicit live-operation enablement.

**Classification:** **ADAPT**

---

## 27. Dependencies and Technology Stack

Core public direction:

- Python
- typed strategy components
- CLI
- SDK
- MCP
- Hyperliquid-oriented execution/backtesting

**Traid implication:** Strong stack compatibility with our Python direction.

**Classification:** **STRONG FIT**

---

## 28. Code Quality

Positive indicators:

- typed composition
- compiler/artifact model
- separation between pipeline engine and interface
- tests directory
- security tooling
- agent instructions
- mirror governance files

Concerns:

- alpha status
- small public commit history
- public mirror may not contain full underlying engine
- runtime quality unverified

**Classification:** **PROMISING, NOT PRODUCTION-PROVEN**

---

## 29. Coupling and Modularity

The component/graph/compiler approach is highly modular by design.

This is better than embedding strategy logic inside one large agent prompt or one large Python conditional file.

**Traid implication:** Strongly relevant.

**Classification:** **ADAPT**

---

## 30. Maintenance Status

Previously observed:

- public repo
- approximately 13 commits
- alpha status
- public mirror
- active development context

**Interpretation:** Interesting and modern, but not mature enough to become a critical dependency without runtime validation.

**Classification:** **EVALUATE / MATURITY RISK**

---

## 31. Issues and Known Problems

Important audit risks:

1. alpha project
2. public mirror may be incomplete
3. some underlying engine/component work may be private
4. runtime behavior not verified
5. exact backtest realism not verified
6. market-data quality not its primary focus
7. no Traid-equivalent Risk Gate
8. no whale intelligence
9. no macro/news verification
10. limited public maturity evidence

---

## 32. License

Public repository is MIT licensed.

**Implication:** Public code can generally be used/modified subject to MIT notice obligations.

**Important:** License applies to the public code actually distributed under it; it does not automatically grant access to private/non-published components.

**Classification:** **REUSE legally possible for public code**

---

## 33. Project Strengths

1. agent-native without agent-owned execution
2. typed strategy composition
3. deterministic compilation
4. deterministic artifacts
5. backtest/live artifact parity
6. Python fit
7. Hyperliquid relevance
8. walk-forward analysis
9. Monte Carlo analysis
10. funding/slippage awareness
11. MCP interface
12. CLI/SDK
13. explicit live-write opt-in
14. local arming
15. secret scanning
16. modular strategy components

---

## 34. Project Weaknesses

1. alpha
2. only small public history
3. public mirror limitations
4. potentially private underlying components
5. runtime not audited
6. no Hyperliquid intelligence data layer
7. no whale system
8. no macro/news system
9. no explicit Traid Risk Gate
10. no primary dashboard value
11. exact backtest assumptions not verified
12. data-quality/freshness model unclear

---

## 35. Traid Comparative Assessment

### Keel currently gives us better design references for

- strategy representation
- typed strategy composition
- compilation
- backtest/live parity
- agent-to-deterministic-engine boundary
- live-write arming
- agent-facing tool interface

### Traid must remain responsible for

- Hyperliquid Data
- deterministic analytics
- Whale Intelligence
- Macro
- News Verification
- Bedrock evidence analysis
- Signal Fusion
- Risk Gate
- dashboard
- outcome tracking

---

## 36. What We Should Take

Highest-value patterns:

1. typed strategy graph
2. compile-before-execute
3. deterministic strategy artifact
4. same artifact for backtest/live
5. component registry
6. validation before execution
7. MCP/agent interface separated from engine
8. explicit live-write opt-in
9. local arming
10. secret scanning
11. walk-forward evaluation concept
12. Monte Carlo robustness testing

**Classification:** **ADAPT — HIGH VALUE**

---

## 37. What We Should Not Take

1. assume alpha code is production-ready
2. depend on private/non-public engine pieces
3. copy entire framework before proving need
4. let agent-generated strategy bypass Traid Risk Gate
5. treat backtest results as sufficient without independent validation
6. import execution complexity into initial Traid scope
7. let MCP tools have unrestricted live-write authority

---

## 38. What Traid Should Build Itself

1. Hyperliquid data layer
2. deterministic analytics
3. Whale Intelligence
4. Smart Money Score
5. Macro Intelligence
6. News Verification
7. Bedrock Agents
8. Signal Fusion
9. Traid-specific Strategy rules/artifacts
10. deterministic Risk Gate
11. Outcome Tracking
12. audit/provenance
13. UI

---

## 39. Estimated Saved Work

Keel is unlikely to eliminate large amounts of Traid coding immediately because we should not adopt an alpha framework wholesale.

But it may save significant **architecture/design work** in Strategy Engine and backtesting.

Potential saving if selected patterns/components prove reusable:

**20–35% of Strategy Engine / strategy-evaluation design work**

and roughly

**5–10% of total Traid project work**.

These are planning estimates, not measured engineering-time facts.

---

## 40. UI / UX Audit

Keel is not a primary trader-dashboard reference.

Its important UX is developer/agent operational UX:

- CLI
- SDK
- MCP tools
- explicit live-write arming
- deterministic artifacts users/agents can reason about

**Traid implication:** Use other audited projects for dashboard UI.

**Classification:** **REFERENCE ONLY**

---

## 41. Security Audit

Positive:

- `.gitleaks.toml`
- explicit live-write opt-in
- local arming
- typed/validated actions reduce arbitrary agent behavior
- allowlist/denylist governance concepts in mirror tooling

Risks:

- live trading inherently high impact
- MCP/tool permissions must be constrained
- private/public component boundary requires scrutiny
- dependency vulnerabilities not scanned by us
- secret lifecycle not fully verified

**Traid implication:** The arming concept is excellent for any future execution mode.

**Classification:** **ADAPT safety patterns**

---

## 42. Performance and Scalability

A compiled deterministic strategy artifact should be cheaper and more predictable than invoking an LLM on every execution decision.

This is a major architectural advantage.

**Cannot verify:** throughput, latency, multi-strategy scaling and exchange execution load.

**Traid implication:** Keep AI out of latency-sensitive execution loops.

**Classification:** **ADAPT principle**

---

## 43. Failure Handling and Reliability

The compile/validate boundary prevents some malformed strategies from reaching execution.

Live-write arming prevents accidental activation.

**Cannot verify comprehensively:**

- exchange outage handling
- reconnect
- partial fills
- order reconciliation
- restart recovery
- idempotency
- state restoration

**Classification:** **REFERENCE ONLY / runtime verification required**

---

## 44. Observability

Strategy artifacts and deterministic execution improve auditability because the exact strategy version can be recorded and replayed.

Walk-forward and Monte Carlo provide evaluation observability.

**Missing/unverified:** full production telemetry.

**Traid implication:** Every Strategy candidate should record:

- strategy artifact/version
- input evidence
- parameters
- Risk Gate result
- later outcome

**Classification:** **ADAPT**

---

## 45. Traid Integration Map

| Keel concept | Traid destination | Decision | Difficulty | Benefit |
|---|---|---|---|---|
| Typed strategy graph | Strategy Engine | ADAPT | Medium | Very High |
| Component registry | Strategy Engine | ADAPT | Medium | High |
| Compile step | Strategy Engine | ADAPT | Medium | Very High |
| Deterministic artifact | Strategy Engine | ADAPT | Medium | Very High |
| Backtest/live same artifact | Strategy/Evaluation | ADAPT | Medium/High | Very High |
| Validation before execution | Strategy/Risk | ADAPT | Low/Medium | Critical |
| MCP interface | Bedrock/Tools | REFERENCE/ADAPT | Medium | High |
| CLI | Developer tooling | REFERENCE | Low | Medium |
| SDK | Internal API | REFERENCE | Medium | Medium |
| Walk-forward | Evaluation | ADAPT | Medium | High |
| Monte Carlo | Evaluation | ADAPT later | Medium | High |
| Funding realism | Backtesting | ADAPT after verification | Medium | High |
| Slippage realism | Backtesting/Risk | ADAPT after verification | Medium | High |
| Live-write opt-in | Governance | ADAPT | Low | Critical if execution added |
| Local arming | Governance | ADAPT | Low | Critical if execution added |
| Gitleaks config | Security | ADAPT | Low | High |
| Hyperliquid execution | Execution | REFERENCE later | High | Out of current core |
| Risk Gate | Traid Risk | BUILD | — | Critical |
| Market Data Layer | Traid Data | BUILD/other repo | — | Critical |
| Whale Intelligence | Traid Whale | BUILD/HyperStats reference | — | Critical |
| Macro/News | Market Intelligence | BUILD/NEXUS reference | — | Critical |

# Final Decision

## Overall classification: **REFERENCE ONLY + selective ADAPT**

Keel should **not** become the Traid base today.

But architecturally it is one of the most valuable projects we have audited.

### The key pattern worth carrying into Traid

**AI/Agent proposes or composes. Deterministic software validates and executes.**

For Traid:

`Bedrock Agent`
→ structured analysis/evidence  
→ `Signal Fusion`  
→ typed `Strategy Candidate`  
→ deterministic `Strategy Engine`  
→ deterministic `Risk Gate`  
→ candidate/blocked result

If live execution is ever added:

→ explicit user enablement / arming  
→ deterministic execution adapter

### Highest-priority ideas

1. Typed Strategy Graph
2. Compile-before-execute
3. Deterministic Strategy Artifact
4. Same artifact for backtest and live
5. Validation before execution
6. Walk-forward testing
7. Monte Carlo robustness
8. Explicit live-write arming
9. MCP interface separated from execution engine
10. Secret scanning

### Important caution

Keel is still alpha and the public repository is a mirror. We should take its **architecture seriously**, but not assume the public implementation is mature or complete.

---

## Audit Limitations

No clone, build, runtime tests or benchmark were performed.

Still unverified:

- actual test pass rate
- test coverage
- compiler correctness
- public/private component completeness
- Hyperliquid execution reliability
- fee/funding/slippage correctness
- lookahead prevention
- partial-fill behavior
- restart recovery
- latency
- dependency vulnerabilities
- live safety under failure

Any direct code reuse requires a later runtime audit.
