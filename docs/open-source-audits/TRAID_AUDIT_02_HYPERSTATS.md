# Traid Audit 02 — HyperStats

**Project:** HyperStats (`hyperstats.org`)  
**Audit date:** 2026-09-02  
**Audit standard:** `TRAID_OPEN_SOURCE_AUDIT_RULES.md`  
**Audit type:** Public product / documentation / live-surface audit  
**Source-code audit:** NOT POSSIBLE — no confirmed public source repository for this product was found  
**Runtime execution:** NOT PERFORMED  
**Overall recommendation:** **REFERENCE ONLY**, with several high-value ideas to **ADAPT** inside Traid.

> Important identity note: `hyperstats.org` is the Hyperliquid whale/trader analytics product audited here. Other unrelated projects named “hyperstats” exist, including `hyperstats.xyz` and unrelated GitHub repositories. They must not be treated as this product's source code.

## Executive Finding

HyperStats is one of the strongest direct product references for Traid's **Hyperliquid Whale Intelligence**.

Its most valuable ideas are:

- wallet discovery separated from wallet verification
- real-time position lifecycle tracking
- realized PnL-first trader evaluation
- grade/rank separation
- quality + proof concept for Smart Money scoring
- current exposure separated from recent activity windows
- notional-based long/short bias instead of simple wallet counts
- wallet → token → live-activity drill-down
- bot-like wallet filtering
- public filtered alerts and private favourite-wallet alerts
- token terminal combining chart context, whale markers, top positions and current exposure

However, HyperStats cannot currently be a code-reuse source because its implementation is not publicly inspectable. Therefore, its contribution to Traid is primarily **methodology, product design, data model ideas and UI/UX reference**, not direct code reuse.

This matches the AI Engineering Playbook: useful product ideas may be adopted only when there is measurable benefit, but unverifiable technology must remain `UNVERIFIED` and critical financial logic must stay deterministic.

---

## 1. Project Purpose

**Evidence:** HyperStats describes itself as a free, real-time analytics platform for Hyperliquid focused on wallet activity, position changes, PnL, trader performance, whale tracking and token positioning.

**Analysis:** The product answers three main questions:

1. Which wallets are strong?
2. What are large traders doing now?
3. How is capital positioned in a specific Hyperliquid market?

**Traid implication:** Very close to the planned Whale Intelligence subsystem.

**Classification:** **REFERENCE ONLY**

---

## 2. Overall Architecture

**Observable product flow:**

`Hyperliquid public L1 + WebSocket feeds → wallet discovery / position monitoring / historical event storage → derived trader metrics → product surfaces`

Product surfaces include:

- Top Traders
- Live Activity
- Wallet Profiles
- Token Analytics
- Token Terminal
- Favourites
- Public Alerts
- RSS feeds
- Telegram alerts

**Cannot verify:** internal services, process topology, queueing, database boundaries, workers, deployment topology.

**Traid implication:** The logical pipeline is useful even though the physical implementation is unknown.

**Classification:** **REFERENCE ONLY**

---

## 3. Repository Structure

**Finding:** No confirmed public source repository for `hyperstats.org` was found.

**Cannot verify:**

- folders
- modules
- packages
- source files
- internal schemas
- tests

**Traid implication:** No direct module-level code reuse can currently be recommended.

**Classification:** **REFERENCE ONLY**

---

## 4. Data Ingestion

**Evidence:** HyperStats states that wallet addresses and trading information come from Hyperliquid's public L1 and WebSocket feeds.

It tracks:

- wallets
- current positions
- realized trading events
- token-level positioning
- alerts
- recent activity
- trade history
- PnL
- leverage
- liquidation information

**Analysis:** This confirms a Hyperliquid-native ingestion model rather than a multi-exchange abstraction.

**Traid implication:** Strong reference for our Hyperliquid-first data model.

**Classification:** **ADAPT concept**

---

## 5. REST / WebSocket / Connectivity

**Verified:** WebSocket feeds are explicitly stated as part of data provenance.

**Observed UI behavior:**

- homepage auto-refresh roughly every 30 seconds
- Top Traders auto-refresh roughly every 90 seconds
- token terminals expose live/current position context

**Cannot verify:**

- reconnect logic
- retry policy
- WebSocket subscriptions
- rate-limit handling
- REST fallback
- timeout policy
- backoff
- deduplication

**Classification:** **REFERENCE ONLY**

---

## 6. Database and Storage

**Evidence:** HyperStats says it combines live position monitoring with **historical event storage**.

**Inferred stored entities likely include:**

- wallet
- position
- position events
- realized trade events
- trader metrics
- token exposure
- activity windows
- favourites
- alerts

**Cannot verify:**

- database technology
- schemas
- indexes
- retention
- time-series storage
- cache
- event log design

**Classification:** **REFERENCE ONLY**

---

## 7. Analytics

**Observable deterministic analytics include:**

- realized PnL windows: 24H / 7D / 30D / all-time
- win rate
- account value
- average margin
- current position count
- long/short exposure
- maximum drawdown field in leaderboard
- current notional
- average leverage
- trader counts
- long notional
- short notional
- long/short notional ratio
- current position bias
- recent opening/closing activity
- activity value
- trader grade
- closed-risk/proof concepts

**Important design decision:** long/short bias uses **notional capital**, not just number of wallets.

**Traid implication:** High-value analytics reference.

**Classification:** **ADAPT — HIGH PRIORITY**

---

## 8. Signal Engine

**Finding:** No conventional trading Signal Engine was found.

HyperStats intentionally presents:

- ranked traders
- live events
- wallet quality
- current exposure
- token bias

It does **not** appear to convert these into `BUY / SELL` trade recommendations.

**Analysis:** This is positive for Traid governance. Whale intelligence should be evidence, not a direct trade signal.

**Classification:** **REFERENCE ONLY**

---

## 9. Whale / Smart Money Intelligence

This is HyperStats' strongest area.

### Observable capabilities

- tracks ~100K wallets
- leaderboard of qualified/tracked traders
- current positions
- entry price
- mark price
- liquidation price
- margin
- leverage
- unrealized PnL
- realized PnL
- trade history
- recent position activity
- largest wins/losses
- preferred tokens
- leverage patterns
- token concentration
- open/increase/reduce/close/liquidation events
- favourite wallets
- wallet ranking
- S+ to F grades
- bot-like wallet filtering
- large-event alerts

### Best idea for Traid

Do **not** equate “large wallet” with “smart money”.

HyperStats separates:

**size → performance → risk → proof → current behaviour**

This is directly applicable to Traid's Smart Money model.

**Classification:** **ADAPT — VERY HIGH PRIORITY**

---

## 10. News / Macro / External Intelligence

**Finding:** Not found as a material product capability.

The external communication channels include RSS, Telegram and X, but these distribute HyperStats' own whale/activity information rather than perform macro/news verification.

**Traid implication:** No replacement for our News Verification or Macro Intelligence.

**Classification:** **REJECT as substitute**

---

## 11. Strategy Engine

**Finding:** Not implemented / not publicly exposed.

HyperStats is research and monitoring software, not an explicit strategy engine.

**Traid implication:** Strategy remains our responsibility.

**Classification:** **NOT IMPLEMENTED**

---

## 12. Backtesting

**Finding:** Not found.

There is historical wallet/trade information, but no verified user-strategy backtesting engine.

**Classification:** **NOT IMPLEMENTED**

---

## 13. Trading Realism

Because there is no verified strategy/backtest engine, conventional backtest realism controls cannot be assessed.

**Observable useful risk context:**

- leverage
- liquidation
- realized versus unrealized PnL
- closed history
- risk-adjusted quality concept

**Cannot verify:** fee treatment, funding effects, execution slippage, latency, fill assumptions.

**Classification:** **REFERENCE ONLY**

---

## 14. AI / LLM Layer

**Finding:** No material user-facing AI/LLM decision layer was found.

The site's “AI Access” page concerns crawlability and machine-readable access for AI systems, not an internal AI trading agent.

**Traid implication:** HyperStats does not replace Bedrock Agents.

**Classification:** **NOT IMPLEMENTED / NOT FOUND**

---

## 15. Deterministic vs AI Boundaries

Because no AI decision layer is evident, the public product is largely analytics/data-driven.

**Positive design lesson:** trader ranking and whale analytics appear as structured metrics, while the user remains responsible for interpretation.

**Traid implication:** Consistent with our human-in-the-loop and deterministic critical-control design.

**Classification:** **REFERENCE ONLY**

---

## 16. Risk Management

HyperStats exposes risk information rather than enforcing user trading risk.

Useful fields/context:

- leverage
- liquidation price
- margin
- position concentration
- realized performance
- closed risk
- maximum drawdown
- leverage patterns
- large losses

**Finding:** no user-level position sizing or trade authorization layer verified.

**Classification:** **REFERENCE ONLY**

---

## 17. Risk Gate

**Finding:** No Traid-equivalent deterministic Risk Gate.

HyperStats provides evidence; it does not appear to authorize trades.

**Traid implication:** Traid must build this itself.

**Classification:** **NOT IMPLEMENTED**

---

## 18. Dashboard

Main product surfaces:

1. **Top Traders**
2. **Live Activity**
3. **Wallet Profile**
4. **Token Analytics**
5. **Token Terminal**
6. **Favourites**
7. **Public alerts**
8. **Daily recaps**

**Analysis:** The strongest design choice is task separation. Each page answers a different question rather than showing everything simultaneously.

**Classification:** **ADAPT product pattern**

---

## 19. Logging

**Cannot verify.**

No public source code or operational logging documentation was found.

**Classification:** **Cannot verify**

---

## 20. Monitoring

**User-visible monitoring:**

- auto-refresh
- live activity
- live/current positions
- current wallet context

**Cannot verify:**

- internal metrics
- service health
- infrastructure monitoring
- alerting
- tracing

**Classification:** **Cannot verify**

---

## 21. Data Quality

### Positive observable choices

- realized and unrealized PnL are clearly separated
- current positions are distinguished from historical activity windows
- current notional is distinguished from trader counts
- bot-like wallets are filtered from some surfaces
- public alerts are filtered rather than raw firehose
- documentation warns users to verify live values because values continuously change
- wallet research is explicitly designed as discovery → verification

### Important weakness

There is no visible universal data-state contract such as:

`LIVE / DELAYED / STALE / UNAVAILABLE`

**Traid implication:** Adopt semantic distinctions, but keep Traid's stronger freshness contract.

**Classification:** **ADAPT**

---

## 22. Tests

**Cannot verify.**

No source repository means no test suite can be inspected.

---

## 23. Test Quality / Coverage

**Cannot verify.**

No test coverage or testing methodology is publicly verifiable.

---

## 24. Deployment

**Cannot verify.**

The application is live as a hosted web platform, but Docker, CI/CD, cloud architecture, hosting and operational topology are not publicly established.

---

## 25. Configuration

**Cannot verify.**

No source-level configuration system is publicly available.

---

## 26. Secrets Management

### Positive public statement

HyperStats says it does not expose:

- private keys
- signed messages
- account-bound personal data

Wallet addresses are treated as public on-chain identifiers.

**Cannot verify:** server-side secrets, encryption, key rotation, auth secrets, Telegram credential handling.

**Classification:** **REFERENCE ONLY**

---

## 27. Dependencies and Technology Stack

**Cannot verify confidently.**

The public website technology is not sufficient evidence of the complete backend stack.

**Rule:** Do not infer internal architecture from browser/frontend fingerprints.

**Classification:** **Cannot verify**

---

## 28. Code Quality

**Cannot verify.**

There is no confirmed public implementation to inspect.

**Product-quality signal only:** terminology and workflow documentation are unusually careful about distinctions such as realized vs unrealized PnL and current exposure vs activity windows.

---

## 29. Coupling and Modularity

**Source-level coupling:** Cannot verify.

**Product-level modularity:** Strong.

Pages are separated by research job:

- discovery
- event detection
- wallet verification
- market context
- watchlist/alerts

**Traid implication:** This is a very good UI/product architecture pattern.

**Classification:** **ADAPT**

---

## 30. Maintenance Status

**Evidence:** HyperStats is currently live, has recent documentation/guides, live market pages and active alert/social channels.

The product reports approximately:

- 100K tracked wallets
- ~65K trades/hour
- ~46K active/open positions at observation time

These are live changing values and should not be treated as permanent constants.

**Classification:** **ACTIVE PRODUCT**

---

## 31. Issues and Known Problems

No public GitHub issue tracker for this product was found.

### Observable limitations

- public token product intentionally does not expose funding/OI on every token page
- some wallet/event surfaces filter bot-like behavior
- auto-refresh intervals mean not every screen is event-by-event instantaneous
- grading formula is described conceptually but not fully disclosed
- source implementation cannot be audited

**Classification:** **EVALUATE**

---

## 32. License

**Critical finding:** No open-source license for the `hyperstats.org` product source code was found because no confirmed source repository was found.

**Implication:**

We may learn from public product behavior and general ideas.

We must **not** treat its hidden implementation as reusable code.

**Classification:** **REFERENCE ONLY**

---

## 33. Project Strengths

1. Hyperliquid-first
2. Large wallet universe
3. Wallet performance ranking
4. Realized PnL emphasis
5. Quality + proof grading philosophy
6. Risk context in wallet assessment
7. Position lifecycle monitoring
8. Current positions plus historical activity
9. Notional-based market bias
10. Token-level whale context
11. Bot/noise filtering
12. Discovery → verification workflow
13. Favourites/private alerts
14. Public high-signal alerts
15. Strong trader-oriented UI information hierarchy
16. Does not appear to present opaque AI trade decisions
17. Clear distinction between one whale and broader market context

---

## 34. Project Weaknesses

1. No public code for audit/reuse
2. Exact grading formula not transparent
3. Database/storage architecture unknown
4. Test quality unknown
5. Reliability/reconnect behavior unknown
6. Security implementation unknown
7. No News Verification
8. No Macro Intelligence
9. No strategy engine
10. No backtesting
11. No deterministic Risk Gate
12. Limited public derivatives metrics compared with Traid plans
13. No verified OI/funding/CVD/order-book analytics as a core surface
14. No Bedrock/agent layer
15. No outcome evaluation of Traid-style signals

---

## 35. Traid Comparative Assessment

### HyperStats currently does better

- wallet discovery
- wallet performance presentation
- whale UX
- position lifecycle visibility
- trader leaderboard
- Smart Money product design
- token-level top-position context
- favourites and alerts
- large wallet universe
- clear research workflow

### Traid is designed to do better

- deterministic market analytics
- OI / funding / CVD / order book
- verified news
- macro context
- Bedrock evidence synthesis
- Signal Fusion
- Strategy Engine
- deterministic Risk Gate
- signal outcome tracking
- data freshness contract
- explanation/provenance across multiple intelligence sources

---

## 36. What We Should Take

### A. Quality + Proof Smart Money model — **ADAPT**

Do not rank wallets from PnL alone.

Conceptual factors:

- realized PnL
- win rate
- drawdown/risk
- position sizing
- trade count
- meaningful closed exposure
- consistency
- recent performance
- evidence depth

### B. Realized-first ranking — **ADAPT**

Realized outcomes should be stronger evidence than temporary unrealized gains.

### C. Wallet research workflow — **ADAPT**

`Discovery → Wallet Verification → Token Context → Live Activity`

### D. Position lifecycle events — **ADAPT**

Normalize:

- OPEN
- INCREASE
- REDUCE
- CLOSE
- FLIP
- LIQUIDATION

### E. Notional-based long/short bias — **ADAPT**

Capital exposure matters more than raw trader count.

### F. Current snapshot vs activity window separation — **ADAPT**

Never mix “where traders are now” with “what happened in the last X hours”.

### G. Bot-like wallet filtering — **ADAPT**

Low-signal machine activity should not dominate whale intelligence.

### H. Top Positions — **ADAPT**

Show who controls the largest current exposure for BTC.

### I. Favourite wallet alerts — **ADAPT later**

User-specific watchlists are more useful than indiscriminate alerts.

### J. Token Terminal UI concept — **REFERENCE / ADAPT**

Chart + whale markers + top positions + current bias + recent activity.

---

## 37. What We Should Not Take

- any undisclosed grading formula as if verified
- UI copied pixel-for-pixel
- hidden/proprietary implementation
- assumption that S+ grade automatically means trade signal
- all 100K wallets in early Traid
- every listed token
- alerts without our own deterministic filters
- leaderboard rank as a trading recommendation

---

## 38. What Traid Should Build Itself

1. Hyperliquid data adapter
2. position-event normalizer
3. wallet state store
4. wallet historical-performance store
5. transparent Smart Money Score
6. explicit scoring formula and versioning
7. BTC-focused whale aggregation
8. Whale Bias
9. deterministic analytics
10. verified News Intelligence
11. Macro Intelligence
12. Bedrock Agents
13. Signal Fusion
14. Strategy Engine
15. deterministic Risk Gate
16. Outcome Tracking
17. data freshness/status model

---

## 39. Estimated Saved Work

Because HyperStats source code is unavailable, **direct engineering work is not eliminated**.

What it does save is **product-design and methodology experimentation**.

### Potential conceptual/design saving

Roughly **5–15% of design work** in the Whale Intelligence + UI portion of Traid could be shortened because HyperStats already demonstrates useful product patterns.

This is not code saved.

The actual ingestion, scoring, storage and analytics still need implementation.

---

## 40. UI / UX Audit

This is one of HyperStats' strongest contributions.

### A. Top Traders page

Useful columns observed:

- trader
- account value
- 7D chart
- main token
- average margin
- positions
- grade
- long/short
- win rate
- max drawdown
- 24H realized
- 7D realized
- 30D realized
- all-time realized

**Good:** high-density table for discovery.

### B. Wallet drill-down

The workflow encourages opening a wallet before trusting the leaderboard.

Useful context:

- positions
- entries
- exits
- liquidation
- PnL
- history
- concentration
- leverage pattern

**Good:** progressive disclosure instead of overloading the main screen.

### C. Live Activity

Filters by:

- event type
- margin/value threshold
- opens
- increases
- reductions
- closes
- liquidations

**Good:** event feed is a trigger surface, not the final analysis screen.

### D. Token Analytics

Uses current capital exposure across markets.

**Good:** fast comparison before opening a detailed token.

### E. Token Terminal

Combines:

- price chart
- large wallet markers
- top positions
- current long/short notional
- average leverage
- recent activity window

**Very useful for Traid BTC dashboard.**

### F. Navigation philosophy

`Leaderboard → Wallet → Token → Activity`

This is more useful than one giant dashboard.

### Traid recommendation

Adapt the **information architecture**, not the visual design wholesale.

**Classification:** **ADAPT — HIGH PRIORITY**

---

## 41. Security Audit

### Positive public evidence

Data is described as public on-chain data from Hyperliquid.

The platform states that it does not expose:

- private keys
- signed messages
- private user accounts
- off-chain identity linkage

### Cannot verify

- authentication implementation
- authorization
- backend secret management
- dependency vulnerabilities
- Telegram account-linking security
- session management
- database exposure
- server configuration

**Classification:** **Cannot verify internally**

---

## 42. Performance and Scalability

### Observable scale

The live product claims approximately:

- ~100K wallets
- tens of thousands of active positions
- tens of thousands of trades/hour

This suggests meaningful ingestion and aggregation scale.

### Cannot verify

- infrastructure
- database performance
- worker model
- queue system
- caching
- horizontal scaling
- latency distribution
- cost

**Traid implication:** Useful evidence that the product model can scale, but not an implementation blueprint.

**Classification:** **REFERENCE ONLY**

---

## 43. Failure Handling and Reliability

**Cannot verify internally.**

Observable client behavior includes periodic refresh and continuously changing live surfaces.

Unknown:

- WebSocket reconnect
- missed-event recovery
- replay
- gap detection
- deduplication
- API outage behavior
- stale data state
- database recovery
- alert delivery retry

**Traid implication:** We must implement explicit reliability contracts ourselves.

**Classification:** **Cannot verify**

---

## 44. Observability

### Product-level observability

HyperStats lets the user see:

- wallet state
- current exposure
- position changes
- realized performance
- recent activity
- token bias
- top positions

### Missing / unverified

No public evidence for:

- infrastructure traces
- service metrics
- ingestion lag
- source health
- stale-data status
- event processing latency
- score-version audit trail

### Traid improvement

Expose both:

1. **market intelligence observability**
2. **system/data observability**

**Classification:** **REFERENCE ONLY**

---

## 45. Traid Integration Map

| HyperStats concept | Traid destination | Decision | Difficulty | Benefit |
|---|---|---:|---:|---:|
| Wallet discovery | Whale Data Layer | ADAPT | Medium | High |
| Wallet state tracking | Whale Store | ADAPT | Medium | Very High |
| OPEN/ADD/REDUCE/CLOSE events | Whale Intelligence | ADAPT | Medium | Very High |
| Liquidation events | Whale Intelligence | ADAPT | Medium | High |
| Realized-first performance | Smart Money Score | ADAPT | Low/Medium | Very High |
| Quality + Proof concept | Smart Money Score | ADAPT | Medium | Very High |
| Grade tiers S+→F | UI / Smart Money presentation | REFERENCE ONLY | Low | Medium |
| Win rate | Wallet Analytics | ADAPT | Low | High |
| Max drawdown | Wallet Analytics | ADAPT | Medium | High |
| Closed risk / evidence depth | Smart Money Score | ADAPT | Medium | High |
| Bot-like wallet filter | Whale Intelligence | ADAPT | Medium | High |
| Notional L/S bias | Whale Aggregation | ADAPT | Low | Very High |
| Trader counts | Whale Aggregation | ADAPT | Low | Medium |
| Current vs activity window | Data Model + UI | ADAPT | Low | Very High |
| Top Positions | BTC Market Intelligence | ADAPT | Low/Medium | High |
| Token Terminal pattern | Dashboard | ADAPT | Medium | High |
| Live Activity feed | Dashboard | ADAPT | Medium | High |
| Favourite wallets | Watchlist | ADAPT later | Medium | Medium |
| Telegram alerts | Alerting | REFERENCE ONLY initially | Medium | Low now |
| Public filtered alerts | Alerting | REFERENCE ONLY | Medium | Medium |
| Grade formula | Smart Money Score | REJECT direct copy | Unknown | — |
| Hidden backend code | Traid backend | REJECT | — | — |

---

# Final Decision

## Overall classification: **REFERENCE ONLY + methodological ADAPT**

HyperStats should **not** be treated as a code source.

It should be treated as our strongest current **product and methodology benchmark for Hyperliquid Whale Intelligence**.

## Highest-value ideas for Traid

1. **Quality + Proof Smart Money scoring**
2. **Realized-first wallet evaluation**
3. **Wallet position lifecycle**
4. **Notional-based long/short bias**
5. **Current exposure vs recent activity separation**
6. **Bot/noise filtering**
7. **Top Positions**
8. **Discovery → Verification → Token Context workflow**
9. **Token Terminal UI structure**
10. **Favourite-wallet alerting later**

## Most important design lesson

A whale is not smart money merely because it is large.

Traid should score:

`performance + risk + consistency + evidence + current behaviour`

and then use that as **one evidence source**, not as trade authorization.

## What HyperStats does NOT remove from our build

We still need to build:

- data ingestion
- storage
- Smart Money algorithm
- analytics
- News Verification
- Macro
- Bedrock
- Signal Fusion
- Strategy
- Risk Gate
- Outcome Tracking

So HyperStats helps us make the **Whale Intelligence design better**, but it does not substantially replace engineering work.

---

## Audit Limitations

This audit is based on public HyperStats product pages, documentation, guides, machine-readable/public policy surfaces, and currently visible live pages.

Because no confirmed public source repository exists for `hyperstats.org`, the following cannot be code-audited:

- backend architecture
- source code
- database schemas
- tests
- dependencies
- retry logic
- WebSocket implementation
- authentication
- secrets
- CI/CD
- performance implementation
- security implementation
- exact grading formula

These limitations are permanent for this audit unless HyperStats publishes source code or provides technical documentation.

---

## Public Sources Consulted

- https://hyperstats.org/
- https://hyperstats.org/docs
- https://hyperstats.org/guides
- https://hyperstats.org/ai-access
- https://hyperstats.org/traders
- https://hyperstats.org/token-terminal/btc
- https://hyperstats.org/guides/how-hyperstats-tracks-hyperliquid-traders
- https://hyperstats.org/guides/how-hyperstats-trader-grade-works
- https://hyperstats.org/guides/hyperliquid-token-analytics
- https://hyperstats.org/guides/how-to-use-hyperstats-live-activity
- https://hyperstats.org/guides/hyperliquid-long-short-bias
