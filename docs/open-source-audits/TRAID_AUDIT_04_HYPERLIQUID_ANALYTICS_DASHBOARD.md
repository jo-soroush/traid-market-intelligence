# Traid Audit 04 — Hyperliquid Analytics Dashboard

**Project:** `lewbei/hyperliquid-analytics-dashboard`  
**Audit date:** 2026-09-02  
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`  
**Audit type:** Public GitHub code-level static audit  
**Runtime execution:** NOT PERFORMED  
**Repository maturity:** very early — only 2 commits observed at audit time  
**License:** Apache-2.0  
**Overall recommendation:** **ADAPT selected analytics modules; do not adopt the repository wholesale yet.**

> This repository is unusually relevant to Traid because it is Hyperliquid-first, Python/FastAPI based, React/TypeScript on the frontend, deterministic, and already implements many of the exact analytics we planned. Its main weakness is maturity: the repository had only two commits and no public adoption evidence at audit time. Therefore, useful modules deserve deeper verification, but the whole repository is not yet a production-quality base.

## Executive Finding

Among the projects audited so far, this is the **closest technical match to Traid's deterministic market analytics layer**.

The public code/repository contains modules for:

- Hyperliquid WebSocket + REST ingestion
- order-book depth and imbalance
- trade-flow windows and directional sweep detection
- liquidation tracking
- OI / funding / basis
- candle aggregation/fetching
- ATR and realized volatility
- session VWAP/high/low/volume
- crowding detection
- market-regime classification
- slippage estimation by walking the order book
- cross-asset BTC/ETH context
- data freshness and module health
- rate-limit measurement
- latency/debug tooling
- React dashboard

This is much more directly reusable for Traid than CryptoRadar's Java analytics because the language and domain fit are already close.

The correct decision is **not** “copy the project.” It is to inspect and selectively port/test individual deterministic modules.

---

## 1. Project Purpose

The project is a real-time market analytics dashboard for Hyperliquid perpetual futures.

It focuses on market microstructure and deterministic analytics rather than AI trading decisions.

**Traid implication:** Direct overlap with `Hyperliquid Data → Deterministic Analytics → Dashboard`.

**Classification:** **ADAPT**

## 2. Overall Architecture

Verified public architecture:

`Hyperliquid WebSocket + REST → FastAPI backend → analytics modules → FastAPI WebSocket → React/TypeScript dashboard`

Each frontend WebSocket connection selects a coin; the backend creates dedicated analytics resources and a Hyperliquid client for that connection. Cross-asset BTC/ETH trackers provide broader context.

**Analysis:** Simple and coherent. Much closer to Traid's desired implementation capacity than a large microservice system.

**Classification:** **ADAPT — HIGH PRIORITY**

## 3. Repository Structure

Verified important backend modules:

- `api_server.py`
- `hyperliquid_client.py`
- `transport_hyperliquid_sdk.py`
- `models.py`
- `config.py`
- `orderbook_metrics.py`
- `trade_flow_tracker.py`
- `liquidations.py`
- `market_indicators.py`
- `candle_aggregator.py`
- `candle_fetcher.py`
- `volatility.py`
- `session_context.py`
- `crowding_detector.py`
- `regime_detector.py`
- `slippage_estimator.py`
- `cross_asset_context.py`
- `price_momentum.py`
- `depth_decay.py`

Frontend includes:

- `Dashboard.tsx`
- `useWebSocket.ts`
- `types.ts`
- `App.tsx`

Repository also exposes Docker/deployment/config files.

**Classification:** **REUSE/ADAPT candidates exist at module level**

## 4. Data Ingestion

Verified design:

**WebSocket:** order book, trades, liquidations  
**REST:** candles, volume, OI, funding and other market indicators

The backend uses Hyperliquid directly rather than routing core data through an unrelated exchange.

**Traid implication:** Excellent architectural fit.

**Classification:** **ADAPT**

## 5. REST / WebSocket / Connectivity

Verified:

- FastAPI WebSocket endpoint
- Hyperliquid WebSocket client
- coin-specific subscriptions
- old connection closed when switching coins
- resources cleaned up on disconnect
- REST and WebSocket both used
- explicit rate-limit tracking tools exist
- API usage measurement scripts exist

**Not verified sufficiently:** robust reconnect/backoff/gap-replay behavior. Static search did not establish a mature reconnect policy.

**Traid implication:** Adapter is a strong reference, but reliability needs strengthening before reuse.

**Classification:** **ADAPT with reliability work**

## 6. Database and Storage

A `database/` area is described in repository documentation, but the public top-level backend listing inspected did not expose enough evidence to approve a production persistence design.

The product's main analytics are heavily in-memory/live oriented.

**Cannot verify comprehensively:**

- durable market-event history
- retention
- partitioning
- historical replay store
- recovery from process restart

**Traid implication:** Do not inherit storage assumptions. Traid needs its own explicit historical/evidence storage plan.

**Classification:** **REFERENCE ONLY**

## 7. Analytics

This is the project's strongest area.

### Order book

Verified code calculates:

`imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)`

for cumulative levels and exposes L1/L5 depth and imbalance.

It also walks book levels to calculate:

- VWAP
- slippage bps
- levels consumed
- executed USD/quantity
- fill feasibility

### Trade flow

Tracks:

- buy volume
- sell volume
- buy/sell ratio
- trade count
- largest/median/average trade
- size buckets
- multiple time windows

Directional sweep logic requires a minimum number of trades and defaults to a 65% volume-dominance threshold.

### Market indicators

Includes:

- Open Interest
- funding
- perp-spot basis

### Volatility/session

Includes:

- ATR
- realized volatility
- daily high/low
- VWAP
- distance from VWAP
- session and rolling volume

### Crowding

Uses OI trends/velocity, funding levels/trends and basis to estimate crowded longs/shorts.

### Regime

Verified classifications include:

- trend: up/down/range
- liquidity: high/normal/thin
- overall: normal/trend/chop/liquidation_event/short_squeeze/crash

Short squeeze and crash logic uses liquidation direction plus trend.

**Traid implication:** Several modules map almost directly to our planned deterministic analytics.

**Classification:** **ADAPT — VERY HIGH PRIORITY**

## 8. Signal Engine

There is no full Traid-style Signal Fusion/Strategy signal engine.

Some modules produce interpreted deterministic states such as:

- sweep direction
- crowding state
- regime
- sentiment/context

These are **features/evidence**, not final trade signals.

**Traid implication:** Correct boundary. Feed them into Traid Signal Fusion later.

**Classification:** **ADAPT evidence outputs**

## 9. Whale / Smart Money Intelligence

No HyperStats-style wallet performance or Smart Money engine is evident.

Trade flow can detect large/imbalanced market activity, but this is not wallet intelligence.

**Traid implication:** HyperStats remains the better methodology reference here.

**Classification:** **NOT IMPLEMENTED**

## 10. News / Macro / External Intelligence

No material primary-source news verification or macro engine.

Cross-asset BTC/ETH context is market context, not macro/news intelligence.

**Classification:** **NOT IMPLEMENTED**

## 11. Strategy Engine

No complete user strategy engine with formal setup rules and candidate lifecycle.

**Classification:** **NOT IMPLEMENTED**

## 12. Backtesting

No mature strategy backtesting engine was verified.

Testing/debug scripts exercise live analytics, but this is not the same as historical strategy backtesting.

**Classification:** **NOT IMPLEMENTED**

## 13. Trading Realism

The repository has unusually useful **pre-trade liquidity realism**.

Slippage estimation walks actual order-book levels and computes:

- average fill
- slippage
- fill completeness
- liquidity utilization

Documentation also describes round-trip cost including fees.

**Strong point:** This is more useful for Traid Risk than generic fixed-slippage assumptions.

**Missing:** full strategy execution simulator, latency model and funding-aware backtest.

**Classification:** **ADAPT — HIGH PRIORITY**

## 14. AI / LLM Layer

No operational LLM/AI trading layer was found in the audited architecture.

A code comment says regime information can help “AI understand” market conditions, but the analytics themselves are deterministic.

**Traid implication:** Good. Bedrock can consume structured analytics later without owning calculations.

**Classification:** **GOOD BOUNDARY / REFERENCE**

## 15. Deterministic vs AI Boundaries

The repository is primarily deterministic.

Order book, trade flow, crowding, regime, volatility and slippage are implemented as ordinary code.

**Traid implication:** Strong fit with our non-negotiable rule that financial calculations and risk controls are not delegated to an LLM.

**Classification:** **ADAPT**

## 16. Risk Management

No complete portfolio/user risk system.

However, risk-relevant analytics include:

- slippage
- liquidity utilization
- crowding
- volatility
- liquidation regime
- thin liquidity
- market regime
- data quality

**Traid implication:** These can become inputs to our Risk Gate.

**Classification:** **ADAPT inputs, not risk authority**

## 17. Risk Gate

No verified mandatory deterministic trade-blocking Risk Gate.

**Traid decision:** Build independently.

Potential inputs from this repo:

- stale feed
- thin liquidity
- excessive slippage
- crash/squeeze/liquidation regime
- abnormal volatility
- crowding

**Classification:** **NOT IMPLEMENTED**

## 18. Dashboard

The React dashboard displays real-time analytics from a single WebSocket stream.

It includes dynamic coin selection and a large number of analytic cards/status areas.

**Strength:** everything is tied directly to live deterministic market state.

**Weakness:** the main `Dashboard.tsx` is very large, indicating UI responsibilities are not sufficiently componentized.

**Classification:** **REFERENCE ONLY / selective ADAPT**

## 19. Logging

Docker logs are documented and backend debugging scripts exist.

**Cannot verify:** mature structured logging, centralized aggregation or correlation IDs.

**Classification:** **REFERENCE ONLY**

## 20. Monitoring

This is a strong area.

Verified/advertised monitoring includes:

- feed connection status
- module availability
- data freshness
- overall data quality
- message rate
- uptime
- API usage/rate-limit measurement
- latency test scripts

**Classification:** **ADAPT — HIGH PRIORITY**

## 21. Data Quality

Explicit freshness thresholds are documented:

- order book under ~5s
- trades under ~60s
- market data under ~120s

Frontend exposes:

- `OK / DEGRADED`
- `CONNECTED / DISCONNECTED`
- per-module `ok/fresh` state
- explicit error display

**Traid improvement:** convert this into our richer canonical states:

`LIVE / DELAYED / STALE / UNAVAILABLE`

**Classification:** **ADAPT — VERY HIGH PRIORITY**

## 22. Tests

Repository documentation provides a backend unittest command.

The repo also contains dedicated live/debug/measurement scripts for:

- full analytics
- enhanced analytics
- latency
- candle debugging
- API count
- REST usage
- live tracking

**Caution:** debugging scripts are not substitutes for automated tests.

**Classification:** **EVALUATE**

## 23. Test Quality / Coverage

No verified coverage percentage.

Given the financial calculations, Traid should require explicit unit tests for:

- imbalance
- VWAP
- slippage
- sweep threshold
- crowding
- regime transitions
- volatility
- freshness

**Current classification:** **INSUFFICIENTLY VERIFIED**

## 24. Deployment

Verified artifacts include:

- Dockerfile
- Dockerfile.dev
- Docker Compose
- production Compose
- deployment documentation

Architecture remains small enough for local execution.

**Traid implication:** Strong fit with local-first/cloud-ready principle.

**Classification:** **ADAPT**

## 25. Configuration

Configuration supports mainnet/testnet selection and environment variables.

Analytics thresholds are exposed in Python constructors/configuration.

**Traid implication:** Keep thresholds explicit, versioned and testable.

**Classification:** **ADAPT**

## 26. Secrets Management

Core public market-data analytics do not inherently require exchange trading credentials.

`.env.example` exists.

**Cannot verify:** full secrets lifecycle because the project is primarily public-data analytics.

**Traid implication:** Good low-privilege starting point.

**Classification:** **REFERENCE ONLY**

## 27. Dependencies and Technology Stack

Core stack:

- Python
- FastAPI
- Hyperliquid SDK / transport
- WebSocket + REST
- React
- TypeScript
- Vite
- Docker

**Traid implication:** This is much closer to our intended stack than CryptoRadar's Java/Quarkus backend.

**Classification:** **STRONG ARCHITECTURE FIT**

## 28. Code Quality

### Strengths

- analytics separated into dedicated Python modules
- dataclasses/types used for domain outputs
- deterministic formulas are visible
- configurable thresholds
- comments/docstrings explain calculations
- transport/client separation exists

### Concerns

- repository maturity is extremely low
- only two commits observed
- some files are already large
- `Dashboard.tsx` is very large
- runtime quality has not been proven
- test coverage is unknown

**Classification:** **PROMISING, NOT PRODUCTION-PROVEN**

## 29. Coupling and Modularity

Backend analytics are relatively modular:

`orderbook_metrics`, `trade_flow_tracker`, `regime_detector`, etc.

This is good for selective porting.

Frontend appears much more monolithic.

**Traid implication:** Backend modules are better reuse candidates than the dashboard as a whole.

**Classification:** **ADAPT backend modules**

## 30. Maintenance Status

At audit time:

- public repo
- 2 commits
- 0 stars
- 0 forks
- 0 open issues shown

**Interpretation:** Very early project. There is not enough history to infer long-term maintenance or community validation.

**Classification:** **EVALUATE / HIGH MATURITY RISK**

## 31. Issues and Known Problems

Public issue count was zero, but this is not evidence of production quality.

Key audit concerns:

1. only two commits
2. no adoption evidence
3. reconnect/gap recovery not verified
4. persistence/replay not established
5. coverage not established
6. UI monolith
7. thresholds may be heuristic and require calibration
8. multi-user resource scaling may be expensive because analytics resources are per connection

## 32. License

Apache License 2.0 is explicitly present.

This generally permits use, modification and distribution subject to its notice/license requirements.

**Traid implication:** Direct code adaptation is legally more feasible than with projects whose license is unclear.

**Classification:** **REUSE legally possible, technical verification still required**

## 33. Project Strengths

1. Hyperliquid-first
2. Python/FastAPI
3. React/TypeScript
4. simple architecture
5. deterministic calculations
6. real order-book analytics
7. trade-flow analytics
8. OI/funding/basis
9. crowding
10. market regimes
11. liquidations
12. volatility
13. VWAP/session context
14. slippage from actual book depth
15. explicit freshness
16. module health
17. rate-limit tooling
18. latency tooling
19. Apache-2.0
20. modular backend analytics

## 34. Project Weaknesses

1. only two commits
2. no community validation
3. runtime not verified by us
4. reconnect/recovery unclear
5. historical persistence unclear
6. no whale wallet intelligence
7. no news/macro
8. no Signal Fusion
9. no strategy engine
10. no backtester
11. no Risk Gate
12. no Outcome Tracking
13. test coverage unknown
14. large dashboard component
15. heuristic thresholds need calibration
16. per-connection resource model may not scale efficiently

## 35. Traid Comparative Assessment

### This repo currently solves better than our blank implementation

- order-book analytics
- trade-flow analytics
- live Hyperliquid ingestion pattern
- crowding
- regime
- slippage
- data-health monitoring
- session context

### Traid must add

- richer canonical data model
- durable history
- wallet/whale intelligence
- news verification
- macro
- Bedrock agents
- Signal Fusion
- Strategy
- deterministic Risk Gate
- Outcome Tracking
- stronger tests/evaluation
- governance/provenance

## 36. What We Should Take

**Highest priority candidates for code-level adaptation:**

1. `orderbook_metrics.py`
2. `trade_flow_tracker.py`
3. `slippage_estimator.py`
4. `regime_detector.py`
5. `crowding_detector.py`
6. `market_indicators.py`
7. `volatility.py`
8. `session_context.py`
9. freshness/module-health pattern
10. rate-limit/latency measurement tools
11. Hyperliquid transport/client separation

Each must be independently tested before incorporation.

## 37. What We Should Not Take

- entire repo wholesale
- frontend monolith
- uncalibrated thresholds as universal truth
- per-connection architecture without load evaluation
- undocumented assumptions
- any “sentiment” interpretation as a final trade signal
- current test maturity as sufficient for financial use

## 38. What Traid Should Build Itself

1. canonical domain models
2. durable historical store
3. wallet/whale intelligence
4. Smart Money Score
5. News Verification
6. Macro Intelligence
7. Bedrock agent layer
8. Signal Fusion
9. Strategy Engine
10. deterministic Risk Gate
11. Outcome Tracking
12. audit/provenance
13. stronger frontend component architecture

## 39. Estimated Saved Work

This repo has the highest potential engineering saving of the first four audits **inside deterministic analytics**.

If the modules pass tests, it may save roughly:

**25–40% of initial deterministic market-analytics implementation work**

because several exact modules we planned already exist in Python.

This is a **rough estimate**, not verified engineering time.

It does not save 25–40% of the entire Traid project.

## 40. UI / UX Audit

### Good ideas

- dynamic asset selector
- live status
- data-quality card
- feed-connected state
- per-module health
- separate cards for order flow, volatility, market indicators, regime and liquidity
- immediate reset of state when switching assets to avoid stale display
- dense trader-oriented information

### Weakness

`Dashboard.tsx` is extremely large, so presentation, formatting and domain display logic are too concentrated.

### Traid decision

Use its **content selection** and status concepts, but design our own cleaner UI with progressive disclosure.

**Classification:** **REFERENCE ONLY**

## 41. Security Audit

Positive:

- read-only/public market analytics reduces privilege
- no trading permission required for core analytics
- environment configuration exists

Unknown:

- dependency vulnerabilities
- API exposure hardening
- WebSocket abuse controls
- CORS/auth policies
- input limits
- DoS resistance

**Classification:** **EVALUATE**

## 42. Performance and Scalability

Documented behavior:

- analytics updates about every 1s
- order book processed on market updates
- trade windows 10s/1m/5m/15m
- indicator/volume REST updates rate-limited around 60s
- BTC/ETH context around 1–5s
- dedicated analytics/client resources per connection

### Concern

Per-connection resource creation is simple but may duplicate Hyperliquid subscriptions/work under many users.

For Traid's single-user/local-first scope this may be acceptable.

For multi-user production, shared ingestion + fan-out would likely be better.

**Classification:** **ADAPT for current scope, redesign if scale requires**

## 43. Failure Handling and Reliability

Verified useful behavior:

- resource cleanup on disconnect
- state clearing when asset changes
- feed status
- freshness checks
- module health
- error surfaced in dashboard

Not sufficiently verified:

- reconnect/backoff
- sequence gap recovery
- missed-event replay
- REST reconciliation
- restart recovery

**Traid implication:** reliability layer must be strengthened.

**Classification:** **ADAPT**

## 44. Observability

This project is strong for its size.

Visible signals include:

- data quality
- feed connectivity
- module freshness
- module availability
- message rate
- total messages
- uptime
- error
- latency measurement tooling
- REST/API usage measurement

**Traid implication:** Very good basis for our Data Status and operational health design.

**Classification:** **ADAPT — HIGH PRIORITY**

## 45. Traid Integration Map

| Project component | Traid destination | Decision | Difficulty | Benefit |
|---|---|---|---|---|
| `hyperliquid_client.py` | Hyperliquid Adapter | ADAPT | Medium | High |
| transport separation | Data Provider layer | ADAPT | Low | High |
| `orderbook_metrics.py` | Deterministic Analytics | ADAPT | Low/Medium | Very High |
| L1/L5 imbalance | Deterministic Analytics | ADAPT | Low | High |
| book-walk liquidity metrics | Analytics/Risk | ADAPT | Low/Medium | Very High |
| `trade_flow_tracker.py` | Deterministic Analytics | ADAPT | Low/Medium | Very High |
| sweep detection | Market Intelligence | ADAPT after calibration | Low | Medium/High |
| `market_indicators.py` | Deterministic Analytics | ADAPT | Low | High |
| `volatility.py` | Deterministic Analytics | ADAPT | Low | High |
| `session_context.py` | Deterministic Analytics | ADAPT | Low | High |
| `crowding_detector.py` | Market Intelligence | ADAPT after calibration | Medium | High |
| `regime_detector.py` | Market Intelligence | ADAPT after calibration | Medium | High |
| `slippage_estimator.py` | Risk Gate inputs | ADAPT | Low/Medium | Very High |
| liquidation tracker | Market Intelligence | ADAPT | Medium | High |
| candle aggregator/fetcher | Market Data | ADAPT | Low/Medium | High |
| cross-asset context | Market Intelligence | REFERENCE/ADAPT later | Medium | Medium |
| freshness thresholds | Data Quality | ADAPT | Low | Very High |
| module health | Observability | ADAPT | Low | High |
| rate-limit tracker | Data Adapter | ADAPT | Low | High |
| latency/API measurement scripts | Evaluation | ADAPT | Low | High |
| Dashboard content model | UI | REFERENCE ONLY | Medium | Medium |
| full Dashboard component | UI | REJECT direct reuse | High | Low |
| Strategy Engine | Strategy | BUILD | — | Critical |
| Risk Gate | Risk | BUILD | — | Critical |
| Whale Intelligence | Whale | BUILD/other reference | — | Critical |

# Final Decision

## Overall classification: **ADAPT selected modules — strongest deterministic analytics candidate so far**

This repository is materially more useful to Traid than its tiny commit history initially suggests.

The **architecture fit is strong**:

`Python + FastAPI + Hyperliquid + deterministic analytics + React`

But maturity is weak:

`2 commits + no adoption evidence + no runtime audit`

Therefore:

**Do not fork it as Traid.**

Instead, treat each useful analytics file as an independent candidate. For every candidate:

`inspect → write tests → compare against Hyperliquid data → benchmark → ADAPT or REJECT`

## Highest-value candidates

1. `orderbook_metrics.py`
2. `trade_flow_tracker.py`
3. `slippage_estimator.py`
4. `market_indicators.py`
5. `volatility.py`
6. `session_context.py`
7. `regime_detector.py`
8. `crowding_detector.py`
9. data freshness/module health
10. Hyperliquid transport/client pattern

## Most important new conclusion

This repo may significantly reduce the amount of **deterministic analytics code** we need to invent.

CryptoRadar remains stronger for **Outcome Tracking / signal evaluation**.

HyperStats remains stronger for **Whale Intelligence product methodology**.

This project is currently the strongest candidate for **Hyperliquid deterministic market analytics**.

---

## Audit Limitations

No clone, build, test execution or benchmark was performed.

Still unverified:

- actual test pass rate
- numerical correctness against independent reference data
- reconnect behavior
- historical gap handling
- persistence/recovery
- dependency vulnerabilities
- multi-client load behavior
- threshold calibration
- production latency
- live data correctness

The repository's very small commit history means these runtime checks are especially important before direct reuse.
