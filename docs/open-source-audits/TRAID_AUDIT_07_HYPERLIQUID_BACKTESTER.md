# Traid Audit 07 — Hyperliquid Backtester

**Project:** `Crypto-Data-API/hyperliquid-backtester`  
**Audit date:** 2026-09-02  
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`  
**Audit type:** Public GitHub static audit  
**Runtime execution:** NOT PERFORMED  
**License:** MIT  
**Repository history observed previously:** ~25 commits  
**Overall recommendation:** **ADAPT selected engine/evaluation patterns**, subject to runtime verification. This is currently the strongest dedicated backtesting candidate in the audit set.

## Executive Finding

This project is directly relevant to Traid's future strategy evaluation layer because it focuses on avoiding several common fake-backtest errors.

The public design includes:

- bar-by-bar event loop
- next-bar-open fills
- fees on both legs
- per-bar funding
- leverage-aware liquidation
- structural prevention of lookahead by slicing arrays to the present
- incremental 1-minute data sync
- dropping the incomplete trailing candle
- local timeframe resampling
- deterministic strategy interface
- metrics including profit factor, expectancy, Sharpe, drawdown, fees, funding and liquidations
- tests around engine invariants, fill timing, lookahead, costs, P&L reconciliation and liquidation

For Traid, this is much more valuable than writing a naive candle backtester from scratch.

The main caution is data dependency: the sync path is associated with CryptoDataAPI, so Traid should separate the **backtest engine** from the **data provider** and feed it our own canonical Hyperliquid historical data where possible.

---

## 1. Project Purpose

A Python backtesting framework specifically aimed at Hyperliquid strategies.

Its purpose is to evaluate strategies with more realistic exchange mechanics than simplistic close-to-close simulations.

**Traid implication:** Directly relevant to Strategy Evaluation.

**Classification:** **ADAPT**

---

## 2. Overall Architecture

Conceptual architecture:

`Historical market/funding data → Strategy Context → bar-by-bar Backtester → fills/costs/liquidation → trades/equity → metrics`

Supporting modules include data sync, indicators, strategy abstraction, metrics and demo/replay export.

**Analysis:** Small, focused architecture. Good fit for selective reuse.

**Classification:** **ADAPT — HIGH PRIORITY**

---

## 3. Repository Structure

Previously verified important paths:

- `src/hlbt/backtester.py`
- `src/hlbt/strategy.py`
- `src/hlbt/sync.py`
- `src/hlbt/indicators.py`
- `src/hlbt/metrics.py`
- `src/hlbt/demo.py`
- `strategies/`
- `tests/`
- `docs/`
- `attachments/`
- `pyproject.toml`

**Analysis:** Responsibilities are separated cleanly.

**Classification:** **ADAPT**

---

## 4. Data Ingestion

`sync.py` handles incremental data synchronization.

Documented behavior includes:

- 1-minute klines
- funding data
- local resampling to larger timeframes
- incomplete trailing candle removed

**Important:** Removing the partial trailing bar prevents a subtle source of unrealistic information.

**Concern:** sync relies on CryptoDataAPI/service access.

**Traid implication:** Keep engine/provider separation and substitute our canonical historical source.

**Classification:** **ADAPT pattern; provider dependency EVALUATE**

---

## 5. REST / WebSocket / Connectivity

The project is a historical backtester rather than a live WebSocket analytics system.

REST/API data synchronization is the relevant connectivity path.

**Cannot verify comprehensively:** provider retry, rate-limit, outage and historical-gap handling.

**Classification:** **REFERENCE ONLY**

---

## 6. Database and Storage

The project uses synchronized historical datasets/local data rather than presenting a large database architecture as its core.

**Cannot verify:** production-grade time-series database, retention or centralized evidence store.

**Traid implication:** Backtester should consume Traid's historical canonical dataset rather than own core storage.

**Classification:** **REFERENCE ONLY**

---

## 7. Analytics

`indicators.py` provides common deterministic indicators:

- SMA
- EMA
- WMA
- HMA
- ALMA
- RSI
- ATR
- standard deviation
- Bollinger Bands

**Traid implication:** Useful but not unique. Project 4 remains more valuable for microstructure analytics.

**Classification:** **REFERENCE / selective ADAPT**

---

## 8. Signal Engine

Strategies derive signals through a `Strategy` abstraction and `Context`.

This is not a general intelligence fusion engine.

**Traid implication:** Traid's Strategy Engine can potentially expose a compatible deterministic interface for backtesting.

**Classification:** **ADAPT interface pattern**

---

## 9. Whale / Smart Money Intelligence

Not a core capability.

**Classification:** **NOT IMPLEMENTED**

---

## 10. News / Macro / External Intelligence

Not a core capability.

**Classification:** **NOT IMPLEMENTED**

---

## 11. Strategy Engine

The `Strategy` base class and `Context` provide a deterministic strategy contract.

The most important design property is that strategy logic receives only information available up to the current simulated point.

**Traid implication:** Strong foundation pattern for replaying Traid Strategy rules.

**Classification:** **ADAPT**

---

## 12. Backtesting

This is the project's strongest area.

Documented engine behavior:

- bar-by-bar loop
- deterministic order processing
- next-bar-open execution
- long/short handling
- position lifecycle
- fees
- funding
- leverage
- liquidation
- trade/equity accounting

**Traid implication:** Strong candidate to reduce backtester implementation work.

**Classification:** **ADAPT — VERY HIGH PRIORITY**

---

## 13. Trading Realism

Excellent relative to typical hobby backtesters.

### Verified design principles

**Next-bar-open fills:** prevents a strategy from seeing a candle close and magically filling at the same already-known close.

**Fees both legs:** entry and exit costs included.

**Funding:** charged/credited through the simulation.

**Liquidation:** leverage-aware liquidation behavior exists.

**Incomplete bar removal:** partial future-ish candle is excluded.

**P&L reconciliation tests:** accounting consistency is tested.

### Still unverified

- exact Hyperliquid fee tiers
- dynamic fee schedules
- real order-book slippage
- partial fills
- latency
- queue position
- mark/oracle liquidation semantics
- extreme gap behavior

**Classification:** **ADAPT, then extend**

---

## 14. AI / LLM Layer

No AI/LLM layer is required for the engine.

**Traid implication:** Positive. Backtesting should remain deterministic.

**Classification:** **GOOD BOUNDARY**

---

## 15. Deterministic vs AI Boundaries

The backtester is deterministic code.

This strongly matches Traid's architecture.

Bedrock may later explain results or compare scenarios, but it should not calculate P&L, fills, funding or liquidation.

**Classification:** **ADAPT principle**

---

## 16. Risk Management

The engine models leverage and liquidation and can evaluate stop/strategy behavior through simulated trades.

It is not itself Traid's live Risk Gate.

**Traid implication:** Useful for testing whether risk rules would have behaved historically.

**Classification:** **ADAPT evaluation support**

---

## 17. Risk Gate

No mandatory live Traid-style Risk Gate.

**Important opportunity:** Once Traid's Risk Gate exists, historical candidates should be replayed through the **same deterministic gate**.

**Classification:** **BUILD in Traid**

---

## 18. Dashboard

No major production trader dashboard is central to this repo.

`demo.py` supports replay/demo export.

**Classification:** **LOW PRIORITY / REFERENCE ONLY**

---

## 19. Logging

Not a major documented strength.

**Cannot verify:** structured logging and production aggregation.

**Classification:** **Cannot verify**

---

## 20. Monitoring

This is an offline evaluation framework, not an infrastructure-monitoring system.

Its strongest monitoring contribution is performance metrics.

**Classification:** **REFERENCE ONLY**

---

## 21. Data Quality

Positive:

- incremental sync
- incomplete trailing bar dropped
- local timeframe resampling from 1m source
- structural current-time slicing

Missing/unverified:

- gap detection
- duplicate detection
- source freshness states
- provenance contract
- cross-source reconciliation

**Traid implication:** Historical dataset validation must happen before backtest.

**Classification:** **ADAPT selected controls**

---

## 22. Tests

Previously documented test suite includes **17 tests** covering important engine behavior.

Areas include:

- engine invariants
- lookahead prevention
- fill timing
- cost accounting
- P&L reconciliation
- liquidation

**Analysis:** This is exactly where tests matter in financial simulation.

**Classification:** **STRONG POSITIVE**

---

## 23. Test Quality / Coverage

Although a numerical coverage percentage was not verified, the chosen test targets are high-value.

Testing lookahead, timing and reconciliation is more important than superficial line coverage.

**Still needed before Traid reuse:**

- property/invariant tests
- funding edge cases
- short liquidation cases
- zero-liquidity/slippage extension
- gap candles
- deterministic replay
- reference-result fixtures

**Classification:** **GOOD TARGETING, extend before production**

---

## 24. Deployment

Python package/project structure via `pyproject.toml`.

No large infrastructure is required.

**Traid implication:** Easy to keep as an internal library rather than separate service.

**Classification:** **ADAPT**

---

## 25. Configuration

Strategy and backtest parameters are programmatic/configurable.

**Traid requirement:** record every backtest configuration with results:

- data range
- strategy version
- parameters
- fee assumptions
- funding source
- leverage
- slippage model
- engine version

**Classification:** **ADAPT**

---

## 26. Secrets Management

Core engine does not require trading secrets.

Data sync may require CryptoDataAPI credentials.

**Traid implication:** isolate provider key from backtest engine.

**Classification:** **LOW RISK / provider secret required**

---

## 27. Dependencies and Technology Stack

Core direction:

- Python
- local historical data
- deterministic backtest engine
- strategy abstractions
- indicator library
- CryptoDataAPI sync integration

**Traid implication:** Excellent language fit.

**Classification:** **STRONG FIT**

---

## 28. Code Quality

Positive design signals:

- focused scope
- separated modules
- deterministic engine
- explicit strategy contract
- structural lookahead prevention
- tests for financial invariants
- metrics separated from engine
- sync separated from engine

**Concern:** runtime/code quality has not been independently executed by us.

**Classification:** **PROMISING**

---

## 29. Coupling and Modularity

Strong separation:

`Data Sync ≠ Strategy ≠ Engine ≠ Indicators ≠ Metrics`

This is exactly what we want.

The main coupling risk is the CryptoDataAPI sync provider.

**Traid decision:** retain engine modularity, replace/abstract provider.

**Classification:** **ADAPT — HIGH PRIORITY**

---

## 30. Maintenance Status

Previously observed:

- public GitHub repository
- ~25 commits
- MIT license

Community maturity remains limited compared with established backtesting frameworks.

**Classification:** **EVALUATE**

---

## 31. Issues and Known Problems

Audit risks:

1. external data-provider dependency
2. no verified order-book slippage model
3. no partial fills
4. latency not modeled
5. exact Hyperliquid fee/liquidation semantics require verification
6. runtime tests not executed by us
7. community maturity limited
8. no Traid Risk Gate
9. no live outcome tracking
10. historical data quality depends on provider

---

## 32. License

MIT.

**Implication:** Public code is generally reusable/modifiable subject to MIT notice requirements.

**Classification:** **REUSE legally possible**

---

## 33. Project Strengths

1. Hyperliquid-specific
2. Python
3. focused scope
4. bar-by-bar engine
5. next-bar-open fills
6. structural lookahead prevention
7. fees both legs
8. funding
9. leverage-aware liquidation
10. incomplete candle removal
11. incremental sync
12. local resampling
13. P&L reconciliation
14. meaningful tests
15. clean module separation
16. useful metrics

---

## 34. Project Weaknesses

1. CryptoDataAPI dependency
2. runtime not verified
3. no order-book slippage
4. no partial-fill model
5. no latency model
6. exact exchange mechanics need independent verification
7. no Whale Intelligence
8. no Macro/News
9. no Signal Fusion
10. no Risk Gate
11. no Outcome Tracking/live feedback
12. limited maturity evidence

---

## 35. Traid Comparative Assessment

### This project can give Traid

- backtest engine structure
- anti-lookahead pattern
- fill timing
- fee/funding accounting
- liquidation modeling
- performance metrics
- financial invariant tests

### Traid must add

- canonical historical Hyperliquid dataset
- order-book/slippage model
- Strategy Engine integration
- Risk Gate replay
- Outcome Tracking
- analytics/whales/macro/news/Bedrock
- provenance/versioning

---

## 36. What We Should Take

Highest-value candidates:

1. `backtester.py` architecture
2. `strategy.py` context slicing
3. next-bar-open fill rule
4. fee accounting
5. funding accounting
6. liquidation logic after verification
7. P&L reconciliation
8. test cases/invariants
9. metrics
10. incomplete trailing-bar removal
11. local resampling pattern
12. provider/engine separation

**Classification:** **ADAPT — VERY HIGH VALUE**

---

## 37. What We Should Not Take

1. hard dependency on CryptoDataAPI
2. assumptions without matching Hyperliquid official semantics
3. simplistic fills for strategies where order-book liquidity matters
4. backtest results without provenance
5. historical results as evidence of future profitability
6. any logic that bypasses Traid Risk Gate
7. provider-specific models in core strategy code

---

## 38. What Traid Should Build Itself

1. canonical historical-data provider
2. data-quality validation
3. order-book/slippage extension
4. strategy artifact integration
5. Risk Gate replay
6. outcome tracker
7. evaluation registry
8. provenance/versioning
9. walk-forward evaluation
10. Monte Carlo robustness layer if later justified

---

## 39. Estimated Saved Work

If the engine passes runtime verification, it may save approximately:

**35–50% of initial backtesting-engine implementation work**

because many of the hard correctness decisions already have concrete implementations/tests.

Across the entire Traid project, this is much smaller:

roughly **5–10% total project work**.

These are planning estimates, not measured engineering time.

---

## 40. UI / UX Audit

Not a primary UI reference.

Potentially useful:

- replay/demo export
- metrics presentation

For Traid UI, CryptoRadar/HyperStats remain stronger references.

**Classification:** **REFERENCE ONLY**

---

## 41. Security Audit

Positive:

- backtesting is offline/deterministic
- no exchange trading permission needed
- provider key can be isolated

Risks:

- dependency supply chain
- provider key exposure
- malicious/corrupt historical data
- unsafe strategy code if arbitrary Python strategies are loaded

**Traid control:** only load trusted/versioned strategy artifacts.

**Classification:** **ADAPT with sandbox/trust controls if needed**

---

## 42. Performance and Scalability

Bar-by-bar Python is appropriate for BTC strategy research at our current scale.

Potential bottlenecks:

- very long 1m history
- many parameter sweeps
- Monte Carlo/walk-forward expansion
- multi-asset runs later

**Traid implication:** Optimize only after profiling. Do not add distributed infrastructure prematurely.

**Classification:** **GOOD CURRENT FIT**

---

## 43. Failure Handling and Reliability

Positive correctness safeguards:

- structural lookahead prevention
- incomplete-bar removal
- accounting reconciliation tests
- liquidation tests

Still needed:

- corrupt file handling
- missing funding periods
- data gaps
- duplicate bars
- invalid timestamps
- provider outage
- deterministic run reproducibility

**Classification:** **ADAPT and strengthen**

---

## 44. Observability

Backtest outputs can expose:

- P&L
- fees
- funding
- liquidations
- profit factor
- expectancy
- Sharpe
- max drawdown
- trade history

Traid should extend each run with:

- run ID
- strategy version
- Risk Gate version
- data snapshot/hash
- configuration
- engine version
- timestamp
- outcome metrics

**Classification:** **ADAPT**

---

## 45. Traid Integration Map

| Backtester component | Traid destination | Decision | Difficulty | Benefit |
|---|---|---|---|---|
| `backtester.py` event loop | Backtesting | ADAPT | Medium | Very High |
| `Strategy` base | Strategy Engine bridge | ADAPT | Low/Medium | High |
| sliced `Context` | Anti-lookahead | ADAPT | Low | Critical |
| next-bar-open fills | Execution simulation | ADAPT | Low | Critical |
| fee accounting | Backtesting | ADAPT | Low | High |
| funding accounting | Backtesting | ADAPT | Medium | High |
| liquidation model | Backtesting/Risk | ADAPT after verification | Medium | High |
| P&L reconciliation | Evaluation tests | ADAPT | Low | Very High |
| incomplete-bar removal | Data Quality | ADAPT | Low | High |
| incremental sync | Historical Data | REFERENCE/ADAPT | Medium | Medium |
| CryptoDataAPI dependency | Data Provider | REJECT as mandatory | — | Negative |
| local resampling | Historical Data | ADAPT | Low | High |
| indicators | Analytics | REFERENCE | Low | Medium |
| metrics | Evaluation | ADAPT | Low | High |
| existing tests | Evaluation | ADAPT/extend | Low | Very High |
| replay export | Dashboard/Evaluation | REFERENCE | Low | Medium |
| order-book slippage | Risk/Backtest | BUILD / Project 4 pattern | Medium | Critical |
| Risk Gate replay | Risk | BUILD | Medium | Critical |
| Outcome Tracking | Evaluation | BUILD / CryptoRadar pattern | Medium | Critical |

# Final Decision

## Overall classification: **ADAPT selected engine and test patterns**

This is currently the **strongest dedicated backtesting candidate** in our audit list.

It should not become a data dependency for Traid.

The preferred architecture is:

`Traid Historical Data → Traid Strategy Artifact → adapted deterministic Backtester → Traid Risk Gate replay → Evaluation Metrics`

not:

`CryptoDataAPI → opaque backtest → trust result`

## Highest-priority things to preserve

1. structural lookahead prevention
2. next-bar-open execution
3. fees on both legs
4. funding
5. leverage/liquidation
6. P&L reconciliation
7. incomplete trailing-bar removal
8. deterministic strategy interface
9. financial invariant tests
10. provider/engine separation

## Important combined insight from audits 4, 6 and 7

We are beginning to see a coherent Traid architecture without inventing everything:

- **Project 4** → deterministic Hyperliquid analytics
- **Keel** → typed Strategy/Agent boundary
- **Project 7** → deterministic backtesting mechanics
- **CryptoRadar** → Outcome Tracking

These should remain **selected components/patterns inside one Traid architecture**, not four merged applications.

---

## Audit Limitations

No clone, build or runtime tests were performed.

Still unverified:

- current test pass rate
- exact source implementation at latest commit
- fee correctness against current Hyperliquid rules
- funding timestamp semantics
- liquidation formula accuracy
- short-side edge cases
- data-provider completeness
- latency
- slippage
- partial fills
- performance on multi-year BTC data
- dependency vulnerabilities

Runtime verification is mandatory before direct code reuse.
