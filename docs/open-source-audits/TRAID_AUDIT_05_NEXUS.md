# Traid Audit 05 — NEXUS

**Project:** `oyi77/1ai-nexus`  
**Audit date:** 2026-09-02  
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`  
**Audit type:** Public GitHub static audit  
**Runtime execution:** NOT PERFORMED  
**License:** MIT  
**Overall recommendation:** **REFERENCE ONLY + selective ADAPT**, especially for Macro Intelligence, Cross-Asset Context, Entity Mapping, Alerts, API envelopes, checkpoints and data-source health.

> NEXUS is broader than Traid. It is a cross-asset finance intelligence platform spanning crypto, macro, forex, commodities, equities, options, prediction markets, DeFi, whales and memecoins. That breadth is useful for reference but is also the main reason not to adopt it wholesale.

## Executive Finding

NEXUS contains several concepts that fit Traid very well:

- FRED / Treasury / World Bank macro endpoints
- real economic calendar and central-bank schedule
- cross-asset terminal
- correlations and dislocation/gap monitoring
- Deribit BTC/ETH options chains with IV/Greeks/OI
- multi-chain whale/entity mapping
- structured alerts
- `IndexerCheckpoint` for resumable ingestion
- common REST envelope `{ data, meta, error }`
- health/status endpoint
- Zod validation
- Redis event publisher/subscriber separation
- explicit authentication for protected WebSocket namespaces

Its weaknesses for Traid are equally clear:

- not Hyperliquid-first
- JavaScript/TypeScript/Next.js backend rather than our preferred Python backend
- very broad scope
- blockchain whale model is different from Hyperliquid position intelligence
- “AI-powered” Smart Money claims are not transparent enough to become a trusted score
- no verified Traid-style Strategy Engine
- no mandatory deterministic Risk Gate
- no primary-source News Verification design equivalent to Traid
- infrastructure is heavier than necessary for our current single-user/local-first scope

The best use of NEXUS is as a **source of patterns and selected logic for Macro/External Intelligence, entity schemas, alerts, checkpoints and cross-asset context**.

---

## 1. Project Purpose

NEXUS is an open-source finance intelligence terminal intended to unify:

- crypto
- macro
- forex
- commodities
- global equities
- options
- prediction markets
- DeFi
- whale/smart-money information

The project aims to eliminate the need to stitch together many separate data terminals.

**Traid implication:** Relevant to Market Intelligence, but far broader than our BTC/Hyperliquid-focused scope.

**Classification:** **REFERENCE ONLY**

---

## 2. Overall Architecture

Documented architecture:

`External APIs / blockchain nodes → Blockchain Indexer + Next.js API routes → Redis Pub/Sub → Prisma/PostgreSQL → Next.js dashboard + Socket.io sidecar`

Major runtime components:

- `web` — Next.js application
- `ws` — Socket.io WebSocket sidecar
- `indexer` — multi-chain indexer
- PostgreSQL
- Redis
- one-time DB initialization service

**Analysis:** Clear logical separation between indexing, storage, API/UI and real-time delivery.

**Traid implication:** Good architectural ideas, but the complete deployment is heavier than needed for Traid V1.

**Classification:** **ADAPT concepts**

---

## 3. Repository Structure

Important documented areas:

### Application

- `src/app/`
- `src/app/api/`
- `src/app/dashboard/`
- `src/app/entities/`
- `src/app/smart-money/`
- `src/app/flows/`
- `src/app/predictions/`
- `src/app/tokens/`
- `src/app/alerts/`

### Components

- `src/components/domain/`
- `src/components/entity/`
- `src/components/predictions/`
- `src/components/ui/`

### Shared logic

- `src/lib/alerts/`
- `src/lib/api/`
- `src/lib/events/`
- `src/lib/ws/`

### Indexer

- `indexer/chains/`
- `indexer/processors/`
- `indexer/publisher.ts`

### WebSocket service

- `ws-server/server.ts`
- `ws-server/auth.ts`
- `ws-server/score.ts`
- `ws-server/subscriber.ts`
- `ws-server/__tests__/`

### Data

- `prisma/schema.prisma`
- `prisma/seed.ts`

**Analysis:** Repository responsibilities are relatively clear.

**Classification:** **REFERENCE ONLY**

---

## 4. Data Ingestion

Documented sources include:

### Blockchain

- Ethereum via WebSocket JSON-RPC
- Arbitrum
- Base
- Optimism
- Solana WebSocket
- Bitcoin through Blockstream REST polling

### Optional enhanced sources

- Alchemy
- Etherscan
- Helius
- Jupiter

### Market / intelligence

- DeFiLlama
- CoinGecko
- DexScreener
- Polymarket
- FRED
- Treasury
- World Bank
- Deribit

**Analysis:** Strong multi-provider ingestion breadth.

**Weakness for Traid:** no Hyperliquid-first ingestion model.

**Classification:** **REFERENCE ONLY / ADAPT external providers**

---

## 5. REST / WebSocket / Connectivity

Verified design:

- REST API v1
- Socket.io sidecar
- public and protected WebSocket namespaces
- Bearer-token authentication for protected namespaces
- chain listeners using WebSocket where supported
- Bitcoin uses REST polling

Protected namespaces include:

- trades
- alerts
- prices
- flows
- orderbook
- derivatives
- liquidations

**Cannot verify exhaustively:** retry/backoff, reconnect, gap recovery and every provider's rate-limit strategy.

**Traid implication:** namespace separation and authenticated streams are useful patterns.

**Classification:** **ADAPT**

---

## 6. Database and Storage

Documented database stack:

- PostgreSQL 16
- Prisma 6 ORM
- Redis 7

Documented 12-model schema:

1. Entity
2. Wallet
3. Trade
4. Flow
5. Signal
6. PredictionMarket
7. MarketPosition
8. Alert
9. AlertDelivery
10. IndexerCheckpoint
11. Token
12. User

**Very useful concept:** `IndexerCheckpoint` stores sync state per chain.

**Traid implication:** Checkpointing is highly relevant to reliable ingestion.

**Classification:** **ADAPT selected schema concepts**

---

## 7. Analytics

Documented derived intelligence includes:

- smart-money signals/scores
- capital flow
- fear/greed composite
- cross-asset correlations
- cross-venue dislocations
- stablecoin peg monitoring
- macro indicators
- token scoring
- options IV / Greeks / OI
- DeFi metrics

**Cannot verify completely:** formulas for every score and derived metric.

**Traid implication:** Most analytics are reference only; macro/correlation/dislocation concepts have higher relevance.

**Classification:** **REFERENCE / selective ADAPT**

---

## 8. Signal Engine

NEXUS exposes `Signal` entities and smart-money signals.

It also exposes token risk/hype scoring.

**Problem:** no verified equivalent of Traid's deterministic multi-source Signal Fusion architecture.

**Traid implication:** use signals as evidence sources only.

**Classification:** **REFERENCE ONLY**

---

## 9. Whale / Smart Money Intelligence

Documented capabilities:

- whale wallet tracking
- six blockchain networks
- entity mapping
- accumulation/distribution/exit patterns
- capital flows
- smart-money scoring
- wallet-to-entity linking

**Strength:** entity mapping is useful.

**Weakness:** this model focuses largely on on-chain wallets and transaction flows, whereas Traid needs Hyperliquid-specific:

- open position
- entry
- leverage
- liquidation price
- unrealized PnL
- realized PnL
- position lifecycle
- account performance

**Decision:** use entity/flow patterns, not the scoring authority.

**Classification:** **REFERENCE ONLY / ADAPT entity model**

---

## 10. News / Macro / External Intelligence

This is one of the strongest areas for Traid.

Documented endpoints:

- `/api/v1/macro`
- `/api/v1/calendar`
- `/api/v1/global-macro`
- `/api/v1/forex`
- `/api/v1/commodities`
- `/api/v1/equities`
- `/api/v1/correlations`
- `/api/v1/gaps`
- `/api/v1/stablecoins`
- `/api/v1/news`

Macro sources include FRED, Treasury and World Bank.

Economic calendar includes FRED releases and central-bank schedules.

**Traid implication:** Excellent source of provider and schema ideas for Macro Intelligence.

**Important limitation:** news aggregation is not equivalent to primary-source claim verification.

**Classification:** **ADAPT Macro / REFERENCE news**

---

## 11. Strategy Engine

No verified comprehensive Strategy Engine that evaluates user-defined trading setups and emits `LONG SETUP / SHORT SETUP / NO SETUP`.

**Classification:** **NOT IMPLEMENTED for Traid purposes**

---

## 12. Backtesting

No mature Traid-style historical strategy backtester was verified from the inspected repository material.

**Classification:** **NOT FOUND / NOT CORE**

---

## 13. Trading Realism

Since no primary strategy backtester was verified, fee/funding/slippage/lookahead controls cannot be treated as a validated framework.

Options data provides real bid/ask and Greeks, but that is market data rather than backtest realism.

**Classification:** **NOT APPLICABLE / Cannot verify**

---

## 14. AI / LLM Layer

README describes Smart Money Detection as “AI-powered scoring”.

**Problem:** exact model, features, training/evaluation, explainability and governance were not sufficiently transparent in inspected evidence.

**Traid implication:** Do not import this as an intelligence authority.

Our Bedrock layer should remain separate and evidence-grounded.

**Classification:** **REJECT direct use / REFERENCE ONLY**

---

## 15. Deterministic vs AI Boundaries

The public architecture mixes deterministic data feeds with some “AI-powered” scoring claims.

Because the AI boundary is not sufficiently explicit, it does not meet Traid's standard for consequential decision logic.

**Traid decision:** deterministic financial calculations remain outside Bedrock/AI.

**Classification:** **ADAPT only deterministic pieces**

---

## 16. Risk Management

NEXUS includes risk scoring in some token/scanner surfaces and structured alerts.

No verified complete position-level trading risk management framework.

**Classification:** **REFERENCE ONLY**

---

## 17. Risk Gate

No verified mandatory deterministic non-bypassable Traid-style Risk Gate.

**Traid decision:** build independently.

**Classification:** **NOT IMPLEMENTED**

---

## 18. Dashboard

NEXUS uses a terminal-style dashboard with dedicated sections for:

- dashboard
- entities
- smart money
- flows
- predictions
- tokens
- alerts
- macro
- forex
- commodities
- equities
- derivatives/options
- scanner

**Strength:** strong separation by research task.

**Weakness:** enormous breadth risks information overload.

**Classification:** **REFERENCE ONLY**

---

## 19. Logging

A `LOG_LEVEL` configuration exists for the indexer.

Alert delivery is persisted through `AlertDelivery`, which provides some operational traceability.

**Cannot verify:** centralized structured logging architecture and correlation IDs.

**Classification:** **REFERENCE ONLY**

---

## 20. Monitoring

NEXUS exposes `/api/v1/status` for infrastructure/data-source health.

This is a useful production pattern.

**Cannot verify:** full metrics/tracing/alerting stack.

**Traid implication:** health endpoint + data-source health should be adapted.

**Classification:** **ADAPT**

---

## 21. Data Quality

Positive architecture elements:

- Zod validation
- standard API envelope
- `IndexerCheckpoint`
- health/status endpoint
- source-specific adapters
- distinct market/macro endpoints

**Cannot verify:** universal freshness contract, reconciliation and stale-state semantics.

**Traid improvement:** enforce canonical:

`LIVE / DELAYED / STALE / UNAVAILABLE`

plus source timestamps and provenance.

**Classification:** **ADAPT selected patterns**

---

## 22. Tests

README instructs contributors to run `npm test`.

A documented `ws-server/__tests__/` directory contains unit tests for the token score engine.

**Cannot verify:** complete test suite across all modules.

**Classification:** **EVALUATE**

---

## 23. Test Quality / Coverage

A unit-tested score engine is positive.

However:

- no coverage percentage verified
- macro provider correctness tests not established
- end-to-end ingestion recovery tests not established
- smart-money score evaluation not established

**Classification:** **INSUFFICIENTLY VERIFIED**

---

## 24. Deployment

Documented deployment is strong:

- Docker Compose
- multi-stage builds
- self-host guide
- PostgreSQL
- Redis
- web
- WebSocket sidecar
- indexer
- backup command

Minimum resources are documented.

**Traid implication:** Good reference for later self-host packaging.

**Classification:** **REFERENCE ONLY initially**

---

## 25. Configuration

Configuration is environment-variable based.

Documented variables include:

- database
- Redis
- NextAuth secret
- API keys
- RPC endpoints
- log level
- optional provider keys

RPC endpoints can be overridden.

**Traid implication:** portable provider configuration is useful.

**Classification:** **ADAPT**

---

## 26. Secrets Management

Positive:

- `.env` pattern
- documented generation of random `NEXTAUTH_SECRET`
- generated PostgreSQL password
- generated `NEXUS_API_KEYS`
- optional provider keys kept in environment variables

Concern:

- local development defaults include weak example/dev secrets such as `nexus-dev-secret`, `nexus-dev-key`, and default admin credentials.

**Traid implication:** production startup should reject insecure defaults.

**Classification:** **ADAPT pattern, strengthen controls**

---

## 27. Dependencies and Technology Stack

Documented stack:

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Recharts
- Socket.io
- Next.js API routes
- Prisma 6
- Zod
- PostgreSQL 16
- Redis 7
- NextAuth.js
- Docker Compose
- blockchain JSON-RPC/WebSockets
- multiple external public APIs

**Traid implication:** frontend ideas are compatible; backend stack is not aligned with our preferred Python/FastAPI core.

**Classification:** **REFERENCE ONLY**

---

## 28. Code Quality

Positive signals:

- logical project structure
- separate indexer
- separate WebSocket sidecar
- validation with Zod
- explicit DB schema
- API middleware
- separate alerts/events/ws libraries
- checkpoint model
- documented deployment

Concerns:

- breadth creates maintenance burden
- many external providers increase failure surface
- code-level quality of every module could not be exhaustively audited

**Classification:** **GOOD STRUCTURE, selective reuse only**

---

## 29. Coupling and Modularity

Strong logical modules:

- indexer
- web/API
- WebSocket
- alerts
- events
- database
- provider categories

Redis Pub/Sub provides event decoupling.

**Concern:** Redis is mandatory infrastructure even if Traid does not need distributed components yet.

**Traid implication:** preserve module boundaries without necessarily introducing separate processes/Redis early.

**Classification:** **ADAPT logical design**

---

## 30. Maintenance Status

The repository was publicly available and recently crawled in 2026.

Public result showed zero forks and no meaningful community adoption evidence.

**Interpretation:** active-looking but community maturity is not established.

**Classification:** **EVALUATE**

---

## 31. Issues and Known Problems

Key risks identified:

1. scope is extremely broad
2. many external free APIs can change/rate-limit
3. public RPC reliability can vary
4. AI Smart Money methodology is insufficiently transparent
5. no Hyperliquid-first position intelligence
6. default development credentials are unsafe for production
7. no Traid-style Risk Gate
8. no verified strategy/outcome framework
9. multi-provider maintenance burden
10. no verified primary-source news claim verification

---

## 32. License

README states MIT License.

**Implication:** code reuse/modification is generally permitted subject to MIT notice requirements.

**Classification:** **REUSE legally possible**, technical compatibility still required.

---

## 33. Project Strengths

1. broad cross-asset coverage
2. Macro Intelligence
3. FRED/Treasury/World Bank
4. economic calendar
5. Deribit options
6. entity mapping
7. multi-chain indexer
8. capital flows
9. structured alerts
10. `IndexerCheckpoint`
11. API health endpoint
12. standard REST envelope
13. Zod validation
14. authenticated WebSocket namespaces
15. local Docker deployment
16. explicit database schema
17. Redis event architecture
18. provider configurability

---

## 34. Project Weaknesses

1. not Hyperliquid-first
2. scope much larger than Traid
3. TypeScript backend mismatch
4. infrastructure heavier than current need
5. whale model not Hyperliquid-position-centric
6. opaque AI smart-money scoring
7. no deterministic Risk Gate
8. no Traid-style Strategy Engine
9. no verified Outcome Tracking
10. news is not authoritative claim verification
11. many third-party APIs
12. public RPC reliability risk
13. community maturity unclear
14. insecure development defaults if misused

---

## 35. Traid Comparative Assessment

### NEXUS currently does better

- Macro provider breadth
- economic calendar
- cross-asset terminal
- entity mapping
- blockchain capital flows
- structured alerts
- Deribit options
- checkpoint schema
- multi-chain indexer
- API health/status
- cross-asset correlations/dislocations

### Traid is designed to do better

- Hyperliquid market intelligence
- Hyperliquid wallet positions
- deterministic order flow/OI/funding analytics
- verified primary-source news
- governed Bedrock agents
- transparent Signal Fusion
- user-defined Strategy Engine
- deterministic Risk Gate
- Outcome Tracking
- simpler scope
- explicit data freshness/provenance

---

## 36. What We Should Take

High-value candidates:

1. FRED/Treasury/World Bank provider patterns
2. economic calendar schema
3. cross-asset correlation concept
4. market dislocation/gap concept
5. Deribit options normalization
6. `Entity` / `Wallet` separation
7. `Flow` model
8. `IndexerCheckpoint`
9. `Alert` and `AlertDelivery` model
10. standard `{ data, meta, error }` API envelope
11. `/status` health endpoint
12. Zod-like boundary validation principle
13. Redis-style event publisher abstraction, without necessarily using Redis
14. public/protected stream separation
15. source/provider configuration

**Classification:** mostly **ADAPT**

---

## 37. What We Should Not Take

1. whole NEXUS architecture
2. memecoin scanner
3. DEX sniper
4. broad multi-chain indexing in V1
5. Indonesia-specific macro modules
6. global-equity terminal unless needed later
7. AI Smart Money score
8. provider-specific schemas in Traid core
9. Redis just because NEXUS uses it
10. default admin credentials
11. every free API integration
12. full DeFi feature set

---

## 38. What Traid Should Build Itself

1. Hyperliquid adapter
2. canonical market data model
3. Hyperliquid whale intelligence
4. transparent Smart Money Score
5. deterministic analytics
6. primary-source news verification
7. Bedrock agent layer
8. Signal Fusion
9. Strategy Engine
10. deterministic Risk Gate
11. Outcome Tracking
12. provenance/freshness
13. Traid-specific UI

---

## 39. Estimated Saved Work

NEXUS will not save much work in Hyperliquid core analytics.

It can reduce design/implementation effort in **Macro / External Intelligence / Alerts**.

Rough estimate if selected patterns are adapted:

**15–30% of Macro/External Intelligence design work**

and perhaps

**5–10% of total Traid implementation work**.

These are planning estimates, not measured engineering-time facts.

---

## 40. UI / UX Audit

### Strengths

- terminal-style domain navigation
- separate pages by research job
- entity explorer
- flows view
- smart-money view
- prediction view
- alerts management
- cross-asset dashboard
- macro/forex/commodity/equity separation

### Useful Traid lesson

Do not put every intelligence stream on one page.

Use:

`Overview → Market → Whales → Macro → News → Strategy/Risk → Outcomes`

with progressive disclosure.

### Weakness for our project

NEXUS breadth is too large and can become a Bloomberg-like navigation tree.

**Traid decision:** adapt information architecture, not feature count.

**Classification:** **REFERENCE ONLY**

---

## 41. Security Audit

Positive:

- NextAuth
- protected WebSocket namespaces
- Bearer token
- environment secrets
- Zod validation
- API middleware

Concerns:

- documented local default `admin/admin`
- default development secrets
- public namespaces
- many external provider surfaces
- dependency vulnerability state not verified
- authorization granularity not fully audited

**Traid implication:** production fail-closed configuration is mandatory.

**Classification:** **REFERENCE / strengthen**

---

## 42. Performance and Scalability

Positive design:

- indexer separated from web
- Redis Pub/Sub decouples producers/consumers
- WebSocket sidecar separates real-time load
- PostgreSQL persistence
- checkpointing supports resumability

Potential cost:

- multiple services
- Redis operational dependency
- large number of provider calls
- multi-chain subscriptions
- high API maintenance burden

**Traid implication:** logical separation is useful; distributed deployment is unnecessary until scale proves it.

**Classification:** **REFERENCE ONLY**

---

## 43. Failure Handling and Reliability

Positive:

- `IndexerCheckpoint` supports resume/state tracking
- alert delivery is persisted
- status endpoint exists
- provider abstraction implied by many sources

Cannot fully verify:

- reconnect/backoff
- missed-event replay
- provider failover
- rate-limit fallback
- circuit breakers
- dead-letter handling

**Traid implication:** checkpoint pattern is high value.

**Classification:** **ADAPT checkpoint/recovery concept**

---

## 44. Observability

Useful observable concepts:

- `/api/v1/status`
- infrastructure health
- data-source health
- `LOG_LEVEL`
- persisted `AlertDelivery`
- checkpoint state

Missing/unverified:

- distributed tracing
- detailed ingestion lag
- per-provider freshness
- score/version provenance
- decision outcome evaluation

**Traid implication:** adopt health/status contract and extend it with freshness/provenance/outcome observability.

**Classification:** **ADAPT**

---

## 45. Traid Integration Map

| NEXUS component/concept | Traid destination | Decision | Difficulty | Benefit |
|---|---|---|---|---|
| FRED macro adapter | Macro Intelligence | ADAPT | Low/Medium | Very High |
| Treasury/World Bank adapters | Macro Intelligence | ADAPT selectively | Medium | Medium |
| Economic calendar | Macro Intelligence | ADAPT | Medium | Very High |
| Central bank schedule | Macro Intelligence | ADAPT | Low/Medium | High |
| Forex monitoring | Cross-Asset Context | REFERENCE/ADAPT later | Low | Medium |
| Commodities | Cross-Asset Context | REFERENCE later | Low | Medium |
| Equities/indices | Cross-Asset Context | REFERENCE later | Low | Medium |
| Correlations | Signal/Market Context | ADAPT | Low/Medium | High |
| Cross-venue gaps | Market Intelligence | ADAPT concept | Medium | Medium |
| Stablecoin monitor | Market Intelligence | REFERENCE later | Low | Medium |
| Deribit options | Derivatives Intelligence | ADAPT later | Medium | High |
| Entity model | Whale Intelligence | ADAPT | Low | High |
| Wallet→Entity mapping | Whale Intelligence | ADAPT concept | Medium/High | High |
| Flow model | Market Intelligence | ADAPT | Low/Medium | High |
| Smart-money score | Whale Intelligence | REJECT opaque score | — | — |
| `IndexerCheckpoint` | Data Ingestion | ADAPT | Low | Very High |
| Alert model | Alerts | ADAPT | Low | High |
| AlertDelivery | Audit/Alerts | ADAPT | Low | High |
| API envelope | Backend API | ADAPT | Low | Medium |
| Zod validation pattern | API boundaries | ADAPT principle | Low | High |
| `/status` endpoint | Observability | ADAPT | Low | Very High |
| Redis Pub/Sub | Infrastructure | REFERENCE ONLY | Medium | Low now |
| Socket.io sidecar | Real-time delivery | REFERENCE ONLY | Medium | Low now |
| Multi-chain indexer | Core Traid | REJECT V1 | High | Low |
| Next.js API backend | Core Traid | REJECT as base | High | Negative |
| News feed | News Verification | REJECT as substitute | — | Low |
| Risk Gate | Risk | BUILD | — | Critical |
| Strategy Engine | Strategy | BUILD | — | Critical |
| Outcome Tracking | Evaluation | BUILD / CryptoRadar pattern | — | Critical |

# Final Decision

## Overall classification: **REFERENCE ONLY + selective ADAPT**

NEXUS should **not** become the base for Traid.

Its best contribution is not its crypto scanner or AI scoring. Its best contribution is the infrastructure and modeling around:

1. **Macro Intelligence**
2. **Economic Calendar**
3. **Cross-Asset Context**
4. **Entity / Flow Modeling**
5. **Indexer Checkpoints**
6. **Structured Alerts**
7. **Health / Status**
8. **API validation/contracts**
9. **Deribit options reference**

## Strongest Traid reuse candidates

### High priority

- FRED macro provider pattern
- economic calendar
- `IndexerCheckpoint`
- `/status` health contract
- Alert + AlertDelivery
- Entity / Wallet / Flow schemas

### Medium priority

- correlations
- cross-venue gaps
- Deribit options
- public/protected real-time stream patterns

### Reject for current scope

- whole NEXUS stack
- memecoin scanner
- DEX sniper
- broad multi-chain indexer
- AI Smart Money score
- Redis/micro-process complexity without demonstrated need

## Key lesson

NEXUS shows how to build **external context around a crypto system**.

It does **not** replace the Hyperliquid core.

The correct Traid relationship is:

`Traid Hyperliquid Core + selected NEXUS-style Macro/External adapters`

not:

`Traid = fork NEXUS`.

---

## Audit Limitations

This is a static public GitHub audit.

Not verified by runtime:

- build success
- test pass rate
- coverage
- provider latency
- provider failure behavior
- rate-limit resilience
- blockchain reconnect/replay correctness
- smart-money scoring accuracy
- exact AI implementation
- production authentication hardening
- dependency vulnerabilities
- PostgreSQL/Redis load behavior

Any adopted component must still pass Traid-specific tests before being treated as production-ready.

## Public Sources Consulted

- GitHub repository `oyi77/1ai-nexus`
- repository README / architecture / API / schema / configuration documentation
