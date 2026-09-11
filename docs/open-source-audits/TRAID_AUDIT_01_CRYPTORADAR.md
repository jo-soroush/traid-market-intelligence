# Traid Open Source Audit 01 --- CryptoRadar

**Project:** `artyomsv/crypto-radar`\
**Audit date:** 2026-09-02\
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`\
**Audit type:** Public GitHub code-level static audit\
**Runtime execution:** NOT PERFORMED\
**Benchmarking:** NOT PERFORMED\
**Overall recommendation:** **REFERENCE ONLY + selective ADAPT**, not a
base fork for Traid.

> Important: this audit distinguishes repository/code evidence from
> README claims. Where public browsing did not expose enough
> implementation detail, the answer is explicitly marked
> `Cannot verify`.

## Executive finding

CryptoRadar is much closer to Traid than a normal crypto dashboard. It
already separates market data, analytics, whale data, derivatives,
signals and execution into services; implements deterministic
six-dimension signal scoring; tracks live signal outcomes; adjusts
thresholds by market regime; includes pluggable setup detectors; and has
a substantial trader-oriented React dashboard.

Its strongest ideas for Traid are **Signal Outcome Tracking**,
**alignment/contradiction scoring**, **market-regime-aware thresholds**,
**pluggable deterministic setup detectors**, **deployment markers**,
**data/status visibility patterns**, and selected UI patterns.

However, I do **not** recommend making CryptoRadar the Traid base
architecture. Its backend is Java 21 + Quarkus microservices, while
Traid is intended to remain simpler and Python-oriented. It is
Binance/Bybit-centric rather than Hyperliquid-first. Its AI integration
gives Gemini a direct BUY/SELL/HOLD trade-evaluation role, which
conflicts with Traid's stronger governance boundary. It also does not
provide the deterministic non-bypassable Traid Risk Gate we require.

The Playbook principle applied here is: preserve a coherent
architecture, avoid complexity without measurable benefit, keep critical
financial controls deterministic, and evaluate reuse against integration
cost.

------------------------------------------------------------------------

## 1. Project Purpose

**Question:** What does it actually solve?

**Evidence:** The repository describes CryptoRadar as a real-time
cryptocurrency monitoring and trading-signal platform. It combines live
market data, technical analytics, whale activity, derivatives,
sentiment, order book and macro information.

**Analysis:** It is not just a chart dashboard. It is an end-to-end
market-intelligence and signal platform, with optional live execution.

**Traid implication:** Strong architectural/product reference because
the problem overlaps heavily with Traid.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 2. Overall Architecture

**Evidence:** Public repository structure and README show:

`React/Vite Frontend → Quarkus API Gateway → market-data / news / analytics / whale / derivatives / signal / options / trade-execution services`

Shared infrastructure includes TimescaleDB, PostgreSQL and Redis
pub/sub.

**Analysis:** Clear domain-oriented microservice separation. This is
production-shaped but heavy for Traid's current scope.

**Traid implication:** Copy the **domain boundaries**, not necessarily
the microservice deployment topology.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 3. Repository Structure

Important top-level areas found:

-   `frontend/`
-   `services/`
-   `shared-trade-core/`
-   `db/`
-   `devops/`
-   `docs/`
-   `techdebt/`
-   `.env.example`
-   `docker-compose.yml`
-   `CLAUDE.md`

Services found:

-   `analytics-service`
-   `api-gateway`
-   `derivatives-service`
-   `market-data-service`
-   `news-service`
-   `options-service`
-   `signal-service`
-   `trade-execution-service`
-   `whale-service`

`signal-service` further separates `backtest`, `config`, `detector`,
`event`, `model`, `repository`, `resource`, `scheduler`, `service`, and
`util`.

**Analysis:** This is one of the repo's strongest characteristics.
Domain separation is explicit and useful.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 4. Data Ingestion

**Evidence:** Documented sources include Binance REST/WebSocket, Binance
Futures, OKX, Bybit, Coinbase, Kraken, Bitfinex, CoinDesk, CoinGecko,
DefiLlama, Alternative.me, Whale Alert and Gemini.

`market-data-service` owns price/candle ingestion and backfill.
`whale-service` consumes multiple exchange streams.
`derivatives-service` handles funding/OI/liquidations.

**Weakness:** Hyperliquid is not the primary market-data source.

**Traid implication:** The adapter separation is useful; the concrete
exchange integrations are mostly unsuitable as Traid's core.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 5. REST / WebSocket / Connectivity

**Evidence:** Quarkus RESTEasy Reactive and WebSocket are part of the
backend. Exchange streams are used extensively. Frontend execution state
uses WebSocket plus a documented 15-second REST polling fallback and
staleness counter.

**Cannot verify:** Full retry/backoff/reconnect/rate-limit behavior
across every exchange adapter was not exhaustively inspectable through
the public browsing interface.

**Traid implication:** Reuse the reliability pattern: WebSocket
primary + REST fallback + explicit staleness.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 6. Database and Storage

**Evidence:**

-   TimescaleDB for time-series market/trade/liquidation/signal outcome
    data
-   PostgreSQL for news/metadata
-   Redis pub/sub
-   Timescale hypertables
-   documented compression after 7 days
-   `deployment_markers`
-   persisted signal outcomes

**Analysis:** Strong time-series architecture, but three persistence
technologies may be unnecessary for early Traid.

**Traid implication:** Timescale-style schemas and outcome persistence
are valuable references. Do not import infrastructure complexity
automatically.

**Classification:** **REFERENCE ONLY / ADAPT**

------------------------------------------------------------------------

## 7. Analytics

**Evidence:** Technical analytics include RSI, MACD, Bollinger Bands,
EMA/SMA, ATR, support/resistance, correlation and volatility. Signal
code explicitly scores RSI, MACD, SMA200, support/resistance, Bollinger
and volume confirmation.

**Analysis:** Core calculations are deterministic, which matches Traid's
design principles.

**Traid implication:** Indicator logic and normalization/scoring
approaches are worth studying, but Traid should prioritize
OI/CVD/funding/order-flow analytics relevant to Hyperliquid.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 8. Signal Engine

**Evidence from `SignalEngine.java`:**

Six dimensions are explicitly computed:

1.  Technical
2.  Whale
3.  Derivatives
4.  Sentiment
5.  Order Book
6.  Macro

Each receives a score and weight. Weighted overall score is computed,
followed by an alignment score. Final labels are `STRONG_BUY`, `BUY`,
`NEUTRAL`, `SELL`, `STRONG_SELL`.

The alignment calculation penalizes strong contradictory dimensions.

The source explicitly warns that alignment is **not
probability/confidence of winning** because outcome analysis showed
inverse correlation with actual results.

**Analysis:** This is one of CryptoRadar's best components.

**Traid implication:** The idea of evidence dimensions + weighted
score + contradiction/alignment is highly relevant to Traid's Signal
Fusion.

**Classification:** **ADAPT --- HIGH PRIORITY**

------------------------------------------------------------------------

## 9. Whale / Smart Money Intelligence

**Evidence:** Real-time large-trade detection across Binance, Coinbase,
Kraken, OKX, Bybit and Bitfinex plus Whale Alert. Thresholds are tiered
by market cap.

**Weakness:** This is primarily **large-trade/transfer detection**, not
the richer Hyperliquid wallet intelligence Traid wants: wallet position
lifecycle, entry, leverage, liquidation price, wallet performance and
transparent Smart Money Score.

**Traid implication:** Use its multi-source event normalization ideas,
not its whale model as the final Traid implementation.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 10. News / Macro / External Intelligence

**Evidence:** CoinDesk + RSS news aggregation, sentiment scoring,
CoinGecko, DefiLlama, Alternative.me and macro dimension inputs.

**Weakness:** No evidence of Traid-style primary-source claim
verification with
`CONFIRMED / PARTIALLY CONFIRMED / UNVERIFIED / MISLEADING / FALSE / OUTDATED`.

**Traid implication:** Traid should build its own verified-event
intelligence.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 11. Strategy Engine

**Evidence:** `TradeSetupEngine` plus pluggable `TradeSetupDetector`
interface. Detectors found include:

-   `TrendContinuationDetector`
-   `LiquiditySweepDetector`

New detectors are designed to register independently.

**Analysis:** Excellent pattern: strategies/setups are independent
deterministic modules instead of one giant conditional engine.

**Traid implication:** Strong candidate pattern for Traid's Strategy
Engine.

**Classification:** **ADAPT --- HIGH PRIORITY**

------------------------------------------------------------------------

## 12. Backtesting

**Evidence:** `signal-service/backtest` contains:

-   `BacktestRepository`
-   `BacktestRun`
-   `BacktestScorer`
-   `BacktestService`
-   `BacktestTrade`

The project also performs live forward outcome tracking against 1-minute
candles.

**Cannot verify:** Full historical replay integrity and all
lookahead-prevention mechanics were not proven in this static audit.

**Traid implication:** Backtest structure is useful, but Traid should
independently verify no-lookahead and realistic execution before reuse.

**Classification:** **REFERENCE ONLY pending runtime/code audit**

------------------------------------------------------------------------

## 13. Trading Realism

**Evidence:** Outcome evaluation subtracts configured round-trip fees
from realized R. The code converts fees in basis points into R-units.
Dynamic trailing stops and explicit exit reasons are tracked.

**Verified:** Fees are explicitly accounted for in outcome metrics.

**Cannot verify:** Complete slippage, latency, funding and fill-model
realism across backtesting.

**Traid implication:** Fee-in-R and explicit exit-reason attribution are
worth adopting. Full realism needs Traid-specific
implementation/testing.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 14. AI / LLM Layer

**Evidence:** `GeminiAnalysisService.java` sends structured market data
to Gemini. It has request timeout, cache, cooldown and limited executor
threads.

Prompt instructs Gemini to return `BUY|SELL|HOLD` with minimum 3:1
reward:risk.

**Analysis:** Technically separated from deterministic scoring, but the
prompt gives the LLM too much trading-judgment responsibility for
Traid's governance model.

**Traid implication:** Replace Gemini with a provider
abstraction/Bedrock adapter and restrict AI to evidence synthesis,
contradiction analysis, uncertainty and explanation.

**Classification:** **REJECT direct design / ADAPT integration pattern**

------------------------------------------------------------------------

## 15. Deterministic vs AI Boundaries

**Positive:** Six-dimension scoring and setup detectors are
deterministic.

**Problem:** Gemini is explicitly prompted as an expert trader and asked
for BUY/SELL/HOLD plus entry/stop/target.

**Traid rule:** AI may analyze but may not own critical deterministic
trade authorization.

**Classification:** **ADAPT REQUIRED**

------------------------------------------------------------------------

## 16. Risk Management

**Evidence:** Project documents ATR-based stop sizing, R:R rules,
trailing-stop ladder, daily-loss halt, native TP/SL, flip-close policy
and execution controls.

**Analysis:** Stronger than many hobby trading repos.

**Weakness:** Risk controls are distributed between signal generation,
AI prompt and execution service rather than represented as one mandatory
Traid-style risk authority.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 17. Risk Gate

**Finding:** **No verified Traid-equivalent deterministic non-bypassable
Risk Gate was found.**

There are execution safety controls such as kill switch and daily-loss
halt, but this is not the same as:

`Candidate → mandatory deterministic validation → TRADE CANDIDATE / NO TRADE`

with every upstream intelligence component unable to bypass it.

**Traid implication:** Traid must build this itself.

**Classification:** **REJECT as substitute for Traid Risk Gate**

------------------------------------------------------------------------

## 18. Dashboard

**Evidence:** Dashboard includes market overview, signals, whale
activity, derivatives/leverage, screener, portfolio, AI analysis,
outcome ledger and execution-account state.

**Analysis:** Feature-rich trader workspace.

**Classification:** **REFERENCE ONLY / selective UI ADAPT**

------------------------------------------------------------------------

## 19. Logging

**Evidence:** Java services use structured application logging patterns
such as Quarkus/JBoss `Logger`, including explicit outcome-close logs.

**Cannot verify:** Central log aggregation architecture for all
environments.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 20. Monitoring

**Evidence:** Service-oriented deployment, execution connection
indicator, status/staleness handling, and documented health-related UI
patterns.

**Cannot verify:** Complete Prometheus/Grafana/trace setup from
inspected evidence.

**Traid implication:** Explicit component health is useful.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 21. Data Quality

**Evidence:** Frontend execution connection status includes
green/amber/red state and staleness. Market data backfill exists.

**Cannot verify:** A comprehensive market-wide freshness contract
equivalent to Traid's `LIVE / DELAYED / STALE / UNAVAILABLE`.

**Traid implication:** Traid should formalize data quality centrally.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 22. Tests

**Evidence:** Test trees exist at least for:

-   signal service
-   market-data service
-   whale service
-   trade-execution service
-   frontend uses Vitest

Source comments deliberately expose pure/package-private functions for
unit tests, including fee calculations and regime threshold logic.

**Classification:** **ADAPT testing patterns**

------------------------------------------------------------------------

## 23. Test Quality / Coverage

**Positive evidence:** Financial/scoring logic has deliberately testable
pure functions.

**Cannot verify:** Numerical coverage percentage and full end-to-end
coverage were not established.

**Traid implication:** Copy the principle of testing deterministic
financial logic directly.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 24. Deployment

**Evidence:**

-   Dockerfiles
-   Docker Compose
-   Nginx
-   Kustomize
-   CloudNativePG
-   Barman Cloud
-   k3s deployment documentation

**Analysis:** Mature for a personal/open-source project, but overbuilt
for initial Traid.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 25. Configuration

**Evidence:** `.env.example`; service configuration; signal constants
are read from active `SignalConfig`. Signal engine comments state
numeric constants can be hot-reloaded without service restart.

**Traid implication:** Externalized strategy/signal configuration is
valuable, provided risk-critical configuration remains controlled and
auditable.

**Classification:** **ADAPT**

------------------------------------------------------------------------

## 26. Secrets Management

**Evidence:** Optional Gemini and Whale Alert keys come from environment
configuration. Live execution is documented as using encrypted
credentials and rejecting withdrawal permission.

**Cannot verify:** Full cryptographic implementation and key lifecycle
in this static pass.

**Classification:** **REFERENCE ONLY pending deeper security test**

------------------------------------------------------------------------

## 27. Dependencies and Technology Stack

**Backend:** Java 21, Quarkus 3.17, RESTEasy Reactive, WebSocket,
scheduled tasks\
**Frontend:** React 19, TypeScript, Vite 6, Tailwind CSS, TradingView
Lightweight Charts\
**Data:** TimescaleDB, PostgreSQL, Redis\
**Infrastructure:** Docker Compose, Nginx, Kustomize, CloudNativePG,
Barman Cloud, k3s\
**AI:** Gemini\
**External data:** multiple exchanges/news/macro services

**Traid implication:** Frontend stack is compatible with Traid ideas.
Backend stack is not aligned with our preferred Python implementation.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 28. Code Quality

**Positive evidence:**

-   domain-separated services
-   typed Java
-   explicit config objects
-   dedicated models/repositories/services
-   pluggable detectors
-   test directories
-   comments explaining non-obvious financial semantics
-   explicit correction of misleading `confidence` terminology to
    `alignment`

**Concern:** `SignalEngine.java` is roughly 766 lines / 648 LOC and
carries substantial scoring responsibility.

**Traid implication:** Good engineering ideas, but avoid copying large
Java classes wholesale.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 29. Coupling and Modularity

**Strength:** Strong service boundaries and detector plugin pattern.

**Concern:** Distributed microservices + Redis + multiple databases
create operational coupling and integration overhead.

**Traid implication:** Preserve logical modules while initially
deploying fewer processes.

**Classification:** **ADAPT architecture pattern**

------------------------------------------------------------------------

## 30. Maintenance Status

**Evidence:** Repository showed approximately 150 commits at audit time
and extensive recent feature evolution in public documentation. It has
zero public stars/forks at inspection time.

**Interpretation:** Active codebase, but not community-validated by
adoption.

**Classification:** **EVALUATE**

------------------------------------------------------------------------

## 31. Issues and Known Problems

**Evidence:** GitHub displayed zero open issues at audit time.

**Important:** Zero issues does **not** prove zero problems.

The repository contains a `techdebt/` directory, which suggests the
author explicitly tracks technical debt internally.

**Cannot verify:** Complete defect history.

**Classification:** **EVALUATE**

------------------------------------------------------------------------

## 32. License

**Evidence:** MIT license.

**Implication:** Generally permissive for use, modification and
redistribution subject to preservation of required copyright/license
notice.

**Classification:** **REUSE legally possible**, subject to preserving
license obligations.

------------------------------------------------------------------------

## 33. Project Strengths

1.  Clear domain separation
2.  Real-time multi-source ingestion
3.  Deterministic six-dimension signal engine
4.  Explicit contradiction/alignment scoring
5.  Honest correction of "confidence" terminology after outcome evidence
6.  Market-regime-aware signal thresholds
7.  Pluggable setup detectors
8.  Live signal outcome tracking
9.  MFE/MAE and R-multiple measurement
10. Fee-aware outcome evaluation
11. Trailing-stop attribution
12. Deployment markers for before/after comparison
13. Rich trader UI
14. Execution kill switch and daily-loss halt
15. Tests around deterministic logic

------------------------------------------------------------------------

## 34. Project Weaknesses

1.  Not Hyperliquid-first
2.  Java/Quarkus backend mismatches Traid's simpler Python direction
3.  Microservice topology is heavy for our current scope
4.  Whale intelligence is less wallet-centric than Traid requires
5.  News is aggregation/sentiment rather than authoritative claim
    verification
6.  Gemini is allowed to produce directional trade verdicts
7.  No verified mandatory deterministic Traid-style Risk Gate
8.  Full backtest realism not verified
9.  Full data-quality contract not verified
10. Low public adoption/community evidence
11. Some important runtime/security claims remain unverified without
    local execution

------------------------------------------------------------------------

## 35. Traid Comparative Assessment

### CryptoRadar currently does better

-   outcome tracking
-   deployment-change measurement
-   existing signal scoring implementation
-   existing UI breadth
-   existing execution controls
-   pluggable setup detector implementation
-   operational service separation

### Traid is designed to do better

-   Hyperliquid-first data
-   Hyperliquid wallet/position intelligence
-   primary-source news verification
-   explicit fact vs interpretation
-   governed Bedrock analytical agents
-   deterministic critical boundaries
-   mandatory non-bypassable Risk Gate
-   simpler architecture suited to our implementation capacity
-   explicit data freshness states

------------------------------------------------------------------------

## 36. What We Should Take

### A. Signal Outcome Tracking --- **ADAPT, highest priority**

Concepts to reproduce:

-   persist every actionable candidate
-   entry / stop / target
-   MFE
-   MAE
-   time-to-MFE
-   time-to-MAE
-   realized R
-   exit reason
-   strategy/detector identity
-   signal alignment
-   market regime

**Why:** It gives Traid measurable evidence about whether its signals
actually work.

### B. Deployment Markers --- **ADAPT**

Record when strategy/scoring versions change so performance can be
compared before/after.

### C. Alignment + contradiction scoring --- **ADAPT**

Use as part of Traid Signal Fusion, but calibrate weights with Traid
data rather than copying constants.

### D. Pluggable `TradeSetupDetector` pattern --- **ADAPT**

Each strategy/setup should be independently testable and measurable.

### E. Market Regime threshold modulation --- **ADAPT**

Counter-trend candidates require stronger evidence.

### F. Fee-aware R metrics --- **ADAPT**

Track net rather than gross strategy quality.

### G. Exit-reason attribution --- **ADAPT**

Separate target, initial stop, trailing stop, expiry.

### H. UI feedback loop --- **REFERENCE / ADAPT**

Show signal → pending → closed → measured outcome.

### I. Connection/staleness indicator --- **ADAPT**

Useful for Traid's explicit data-health design.

------------------------------------------------------------------------

## 37. What We Should Not Take

-   Whole Java/Quarkus backend
-   Full microservice topology
-   Binance-centric market adapters as Traid core
-   Gemini-specific implementation
-   Gemini BUY/SELL/HOLD authority
-   live Bybit execution service in early Traid
-   full multi-exchange breadth before Hyperliquid core is stable
-   all infrastructure components simply because they exist

**Reason:** Integration/maintenance cost would likely exceed saved work
for the current Traid scope.

------------------------------------------------------------------------

## 38. What Traid Should Build Itself

1.  Hyperliquid Data Adapter
2.  Hyperliquid historical-data handling
3.  Hyperliquid Whale/Wallet Intelligence
4.  Smart Money Score
5.  News Claim Verification
6.  Primary-source macro verification
7.  Bedrock provider/agent layer
8.  Traid Signal Fusion calibrated to our evidence
9.  Traid Strategy Engine in Python
10. Mandatory deterministic Risk Gate
11. Unified data freshness contract
12. Traid-specific audit/provenance model

------------------------------------------------------------------------

## 39. Estimated Saved Work

### Verified conceptual savings

CryptoRadar gives us tested design directions for:

-   signal fusion/scoring structure
-   outcome tracking schema
-   outcome metrics
-   setup-detector architecture
-   regime-aware thresholds
-   fee-aware R calculations
-   deployment markers
-   trader dashboard information architecture

### Rough estimate

If we **port only selected patterns** rather than fork the platform, it
could remove roughly **15--25% of design/experimentation work** in the
signal/outcome/UI parts of Traid.

This is **not** a measured engineering-time saving yet. Actual savings
require implementation benchmarking.

Forking the whole repo may save **less**, because Java→Python,
Binance→Hyperliquid and architecture simplification would create
substantial conversion work.

------------------------------------------------------------------------

## 40. UI / UX Audit

**Evidence from frontend structure/documentation:**

-   React + TypeScript + Tailwind
-   TradingView Lightweight Charts
-   `SignalDashboard`
-   `RegimeBadge`
-   alignment gauge
-   signal distribution
-   top opportunity
-   `TradeLedger`
-   `TradeChartModal`
-   `AiAnalysisModal`
-   portfolio/exchange cards
-   equity summary
-   open positions table
-   trailing-stop indicators
-   position row menu
-   first-time auto-trade modal
-   kill-switch banner
-   slide-in settings panel
-   green/amber/red connection indicator with staleness
-   closed-loop signal feedback card

### Good for Traid

-   trader-centric information hierarchy
-   separate status badges
-   visual market regime
-   explicit data/connection health
-   outcome ledger
-   modal/detail progressive disclosure
-   charts tied to outcomes
-   visible risk/execution state

### Avoid

Do not copy every panel into Traid V1. It would recreate the scope
problem we are trying to avoid.

**Classification:** **REFERENCE ONLY + selective ADAPT**

------------------------------------------------------------------------

## 41. Security Audit

**Positive evidence:**

-   environment-based external API keys
-   documented encrypted execution credentials
-   withdrawal-permission rejection
-   kill switch
-   daily-loss halt

**Risks / Cannot verify:**

-   encryption implementation not runtime-tested
-   dependency vulnerabilities not scanned in this audit
-   authentication/authorization boundaries were not fully established
-   public API exposure hardening not verified
-   secret rotation not verified

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 42. Performance and Scalability

**Positive architecture:**

-   domain services can scale separately
-   Redis pub/sub decouples events
-   TimescaleDB suits time-series workloads
-   compression after seven days reduces storage pressure
-   AI calls use cache/cooldown and a small executor pool

**Potential costs:**

-   many services increase memory/ops overhead
-   Redis and two PostgreSQL-family stores increase failure surface
-   multi-exchange WebSocket fanout increases operational complexity

**Traid implication:** Do not inherit distributed deployment until Traid
volume proves it necessary.

**Classification:** **REFERENCE ONLY**

------------------------------------------------------------------------

## 43. Failure Handling and Reliability

**Evidence:**

-   execution UI WebSocket has REST polling fallback
-   staleness counter
-   Gemini request timeout
-   Gemini cache/cooldown
-   optional AI can be disabled if API key absent
-   service isolation reduces some blast radius

**Cannot verify comprehensively:**

-   all exchange reconnect strategies
-   dead-letter handling
-   Redis outage recovery
-   DB failover behavior in local deployment
-   idempotency across all event consumers

**Classification:** **ADAPT selected patterns**

------------------------------------------------------------------------

## 44. Observability

**Evidence:**

-   application logging
-   explicit execution connection status
-   signal outcome metrics
-   performance breakdowns
-   deployment markers
-   exit reason attribution
-   current market regime surfaced in metrics

**Major insight:** CryptoRadar's strongest observability is not
infrastructure tracing; it is **decision-performance observability**. It
can answer whether signals fired, what happened afterward and how engine
changes affected outcomes.

**Traid implication:** This should become a core Traid capability.

**Classification:** **ADAPT --- HIGH PRIORITY**

------------------------------------------------------------------------

## 45. Traid Integration Map

  ---------------------------------------------------------------------------------------
  CryptoRadar concept       Traid            Decision       Difficulty     Benefit
                            destination                                    
  ------------------------- ---------------- -------------- -------------- --------------
  Six-dimension scoring     Signal Fusion    ADAPT          Medium         High
  structure                                                                

  Alignment/contradiction   Signal Fusion    ADAPT          Low/Medium     High
  algorithm                                                                

  Outcome Tracker           Evaluation /     ADAPT          Medium         Very High
                            Outcome Tracking                               

  MFE/MAE/R metrics         Evaluation       ADAPT          Low/Medium     Very High

  Deployment markers        Evaluation /     ADAPT          Low            High
                            Governance                                     

  TradeSetupDetector        Strategy Engine  ADAPT          Low/Medium     High
  interface                                                                

  Trend continuation        Strategy Engine  REFERENCE ONLY Medium         Medium
  detector                                   initially                     

  Liquidity sweep detector  Strategy Engine  REFERENCE ONLY Medium         Medium
                                             initially                     

  Regime-aware thresholds   Strategy Engine  ADAPT          Low/Medium     High
                            / Signal Fusion                                

  Fee-in-R calculation      Evaluation       ADAPT          Low            High

  Trailing-stop ladder      Risk/Strategy    REFERENCE ONLY Medium         Medium
                            research                                       

  Multi-exchange whale      Whale            REFERENCE ONLY High           Low for
  ingestion                 Intelligence                                   current scope

  Whale Alert integration   External         REFERENCE ONLY Low            Low/Medium
                            Intelligence                                   

  News sentiment            News             REJECT as      Low            Low
  aggregation               Intelligence     verification                  
                                             substitute                    

  Gemini analysis           Bedrock Agent    REJECT direct  Medium         Medium
                            Layer            / ADAPT                       
                                             pattern                       

  Kill switch               Risk/Execution   ADAPT concept  Low            High if
                                                                           execution
                                                                           added

  Daily-loss halt           Risk Gate        ADAPT concept  Low            High

  React dashboard structure Dashboard        REFERENCE ONLY Medium         High

  Outcome ledger            Dashboard        ADAPT          Low/Medium     High

  Regime badge              Dashboard        ADAPT          Low            Medium

  Connection/staleness      Data Quality +   ADAPT          Low            High
  status                    Dashboard                                      

  Timescale hypertables     Storage          EVALUATE later Medium         Medium

  Redis pub/sub             Infrastructure   REJECT for V1  Medium         Low now
                                             unless needed                 

  Quarkus microservices     Backend          REJECT as      High           Negative now
                            architecture     Traid base                    

  Bybit execution service   Execution        REJECT for     High           Out of scope
                                             current core                  
  ---------------------------------------------------------------------------------------

------------------------------------------------------------------------

# Final Decision

## Overall classification: **REFERENCE ONLY + selective ADAPT**

CryptoRadar should **not** become the Traid base repo.

The best strategy is to treat it as a mature design/code reference and
port only the pieces that demonstrably reduce our work.

## Highest-value ideas to carry into Traid

1.  **Outcome Tracking**
2.  **MFE / MAE / realized R / exit-reason metrics**
3.  **Deployment Markers**
4.  **Alignment + contradiction scoring**
5.  **Pluggable deterministic setup detectors**
6.  **Market-regime-aware thresholds**
7.  **Decision-performance observability**
8.  **Data staleness/connection status**
9.  **Outcome-focused dashboard patterns**

## Critical components Traid must keep independent

1.  Hyperliquid-first Data Layer
2.  Hyperliquid Whale Intelligence
3.  Primary-source News Verification
4.  Bedrock analytical agents
5.  Traid Strategy Engine
6.  **Mandatory deterministic Risk Gate**

## Why this decision fits the AI Engineering Playbook

The Playbook requires evaluation before complexity, measurable benefit
before architecture change, deterministic controls for consequential
financial decisions, observability, vendor neutrality where practical,
and preservation of a coherent existing architecture.

CryptoRadar provides excellent patterns, but adopting its complete Java
microservice stack would add complexity without yet demonstrating
proportional benefit for Traid.

------------------------------------------------------------------------

## Audit Limitations

This is a **static public GitHub audit**. The repository was not cloned
or executed in this environment.

Therefore these remain unverified until a later runtime audit:

-   actual build success
-   full test pass rate
-   numerical test coverage
-   live WebSocket resilience
-   rate-limit behavior
-   database performance
-   dependency vulnerabilities
-   secret encryption correctness
-   live execution safety
-   backtest lookahead integrity
-   real latency and resource usage

These limitations must remain attached to this audit until runtime
evidence exists.
