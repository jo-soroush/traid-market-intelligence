# Hyperliquid Analytics Dashboard — TraID Reconnaissance Record

**Status:** REFERENCE + SELECTIVE ADAPT  
**Project:** TraID  
**Source repository:** `lewbei/hyperliquid-analytics-dashboard`

> This is a reconnaissance and decision-support record. It does not change the TraID roadmap, authorize implementation, or make the external repository part of TraID.

## 1. Purpose

We ran this repository locally to learn from real behavior rather than README claims alone. The goal was to identify what TraID should adapt, what must be independently verified, and what should be rejected.

This follows TraID's existing engineering posture: preserve project-owned architecture, validate important decisions with evidence, and keep financially consequential controls deterministic.

## 2. Runtime evidence observed

The application was run locally with Docker.

Observed:
- frontend on port `3000`
- backend on port `8000`
- historical candles loaded successfully
- REST-derived market context and Hyperliquid volumes populated
- frontend connected to backend
- live Hyperliquid stream initially failed
- after diagnosis and temporary SDK upgrade, live events flowed
- dashboard changed from degraded/disconnected to `Data Quality: OK` and `Feed Connected: CONNECTED`

### SDK failure found

Repository pins:

```text
hyperliquid-python-sdk==0.20.1
```

Initial backend failure:

```text
[stream_loop] error: list index out of range
```

The traceback was isolated to SDK `Info.__init__()` while processing current Hyperliquid `spotMeta`.

Current metadata contained token identifiers larger than the positional length of `spot_meta["tokens"]`. SDK `0.20.1` treated those identifiers as positional list indexes and raised `IndexError`.

A temporary in-container upgrade to:

```text
hyperliquid-python-sdk==0.24.0
```

made `Info(MAINNET_API_URL)` initialize successfully. After backend restart, live WebSocket events arrived and dashboard health became OK.

The repository dependency file itself was not permanently modified during reconnaissance.

## 3. Main architecture lesson

Useful pattern:

```text
Hyperliquid
├── REST
│   ├── historical candles
│   ├── volume/context
│   └── reference/historical information
└── WebSocket
    ├── order book
    ├── trades
    └── live market events
```

**Decision: ADAPT**

Why: REST and streaming data have different latency, recovery and failure characteristics.

Critical lesson: partial data availability must not imply full pipeline health. During the WebSocket failure, REST-derived data still populated the dashboard.

TraID therefore needs source-level and capability-level health.

# 4. ADAPT — What we want for TraID

## 4.1 REST + WebSocket separation

**Decision:** ADAPT  
**Relevant Cards:** C03, C04, C05, C06

Keep transport/provider details behind the exchange adapter. Hyperliquid SDK/JSON types must not become TraID Core models.

## 4.2 Order-book analytics

**Decision:** ADAPT  
**Relevant Card:** C07

Useful concepts:
- Best Bid / Best Ask
- Mid Price
- Spread
- L1–L5 Depth
- Order Book Imbalance
- Depth Decay
- Order Book Ladder

Why: useful deterministic market-microstructure context.

Constraint: imbalance is evidence, not directional probability. Resting orders can be cancelled or manipulated.

## 4.3 Trade-flow analytics

**Decision:** ADAPT  
**Relevant Card:** C08

Useful concepts:
- Buy Volume
- Sell Volume
- Buy Ratio
- Trade Count
- Largest Trade
- Average Trade
- Median Trade
- Sweep detection
- multiple time windows

Why: trade flow describes executed aggressive activity rather than only resting intent.

Constraint: aggressive buy/sell flow is evidence, not guaranteed future direction.

## 4.4 Multi-timeframe analytics

**Decision:** ADAPT

Useful horizons observed include short and longer windows such as:

```text
30s
1m
5m
15m
1h
```

Why: short-term pressure can contradict broader context.

TraID must explicitly define and test event-time boundaries, expiration, incomplete windows and late-event behavior.

## 4.5 Derivatives context

**Decision:** ADAPT CONCEPTS, VERIFY IMPLEMENTATION  
**Relevant Cards:** C09, C10

Useful concepts:
- Open Interest
- OI Trend
- OI Velocity
- Funding Rate
- Funding Trend
- Basis

Why: useful for leverage, positioning pressure and crowding context.

Constraint: units and financial semantics require authoritative verification.

## 4.6 Volatility analytics

**Decision:** ADAPT

Useful concepts:
- ATR
- Realized Volatility
- multiple horizons
- volatility percentile
- volatility regime

Why: risk and execution conditions change across volatility regimes.

Constraint: regime labels need transparent, deterministic, versioned and tested rules.

## 4.7 Slippage and execution-cost estimation

**Decision:** STRONG ADAPT AFTER VERIFICATION  
**Relevant Cards:** C07, C16, C17, C18 where approved

Concept:

```text
Order size
→ consume book depth
→ expected average execution price
→ slippage
→ liquidity consumed
```

Why: a setup may look attractive but be poor to execute at the intended size. This can become deterministic evidence for Strategy/Risk.

No external formula is trusted without fixtures and financial-invariant tests.

## 4.8 Feed/event telemetry

**Decision:** ADAPT  
**Relevant Cards:** C05, C23

Useful telemetry:
- feed connected/disconnected
- total events
- order-book updates
- trade events
- market updates
- messages per minute
- uptime
- module status

Why: telemetry exposed the broken stream immediately and later proved recovery.

## 4.9 Module-level Data Quality

**Decision:** ADAPT AND STRENGTHEN

TraID target:

```text
Source
→ source_timestamp
→ received_timestamp
→ age
→ freshness
→ gap detection
→ validation
→ recovery status
→ LIVE / DELAYED / STALE / UNAVAILABLE
→ module health
```

One healthy source must never hide another failed source.

## 4.10 Diagnostic dashboard

**Decision:** ADAPT CONCEPT, NOT LAYOUT  
**Relevant Card:** C22

The dashboard is useful for engineering/debugging because pipeline health is visible.

TraID's primary decision-support UI should be cleaner, with progressive disclosure. A separate dense diagnostic view can exist if useful.

# 5. VERIFY BEFORE ADOPTION

These capabilities are interesting but are not accepted as financially correct just because the dashboard displays a value.

## 5.1 Open Interest units and semantics

**Status:** VERIFY

An observed SOL Open Interest display was suspicious enough to require code and provider-semantic verification.

Must prove:
- contracts, coin quantity or USD notional?
- conversion price?
- timestamp?
- market-wide or another scope?
- is the UI applying `$` to a non-currency quantity?

## 5.2 OI Trend and OI Velocity

**Status:** VERIFY

Must establish:
- formula
- time window
- sampling
- missing-data behavior
- restart behavior
- units
- stale-data behavior

## 5.3 Position Crowding

**Status:** VERIFY / POSSIBLY REIMPLEMENT

TraID requires:
- transparent inputs
- explicit formula
- deterministic thresholds
- versioned configuration
- tests
- no hidden score
- no certainty implied by labels

## 5.4 Market Regime

**Status:** VERIFY / REIMPLEMENT

Must establish:
- features
- thresholds
- lookback windows
- transition behavior
- stale/missing behavior
- deterministic reproducibility

## 5.5 Liquidity Regime

**Status:** VERIFY / REIMPLEMENT

Labels such as `THIN` and `NORMAL` are useful only when their definitions are measurable and tested.

## 5.6 Trade-flow window semantics

**Status:** VERIFY

During runtime inspection, total event counters and some displayed trade-flow windows did not always visually align. This does not prove a bug, but it means semantics must be inspected.

Verify:
- event-time vs processing-time
- exact boundaries
- expiration
- aggregation
- refresh cadence
- restart behavior
- late events

## 5.7 Sweep detection

**Status:** VERIFY

Need exact definition:
- number of levels
- time threshold
- minimum size/notional
- side classification
- duplicate handling

## 5.8 Liquidation detection

**Status:** VERIFY WITH HIGH SCRUTINY

TraID must distinguish authoritative liquidation events from inferred/heuristic liquidation estimates. Heuristics must never be promoted to authoritative truth.

## 5.9 Slippage formula

**Status:** VERIFY BEFORE FINANCIAL USE

Must prove:
- correct side of book
- level consumption
- average fill price
- insufficient-depth behavior
- units
- fee inclusion/exclusion
- snapshot freshness
- deterministic fixtures

# 6. REJECT — What we do not want

## 6.1 Repository as TraID architecture/base

**Decision:** REJECT

Reason: TraID remains a TraID-owned system. This repository does not cover TraID's full evidence, news, macro, AI, Signal Fusion, Strategy, deterministic Risk Gate, outcome/evaluation and governance architecture.

## 6.2 Provider-specific models in Core

**Decision:** REJECT

Reason: Hyperliquid payloads and SDK types stay at adapter boundaries. Core must remain provider-neutral and future multi-exchange capable.

## 6.3 Trusting UI financial values without verification

**Decision:** REJECT

Reason: polished presentation does not prove units, timing, formulas or accounting.

Especially relevant to OI, liquidation, basis, crowding, slippage and regime metrics.

## 6.4 Opaque composite scores

**Decision:** REJECT

Reason: financially consequential logic requires transparent deterministic rules.

## 6.5 Imbalance as probability

**Decision:** REJECT

Reason: resting liquidity can disappear. Order-book imbalance is context/evidence, not calibrated probability.

## 6.6 Buy Ratio as future direction

**Decision:** REJECT

Reason: aggressive buying can be absorbed by passive sellers. Price response and broader evidence matter.

## 6.7 Dense dashboard as primary TraID UX

**Decision:** REJECT

Reason: useful for engineering inspection, but too much simultaneous information for TraID's main decision-support workflow.

## 6.8 One global Connected state

**Decision:** REJECT

Reason: REST remained healthy while WebSocket was dead. Health must be source/capability specific.

## 6.9 Blind dependency pinning

**Decision:** REJECT AS ENGINEERING PRACTICE

Reason: the runtime incident proved a pinned SDK can become incompatible with evolving provider metadata.

# 7. Engineering lessons from the SDK incident

### A. Build PASS does not mean provider integration PASS

Docker built and services started while the live path was broken.

```text
build PASS ≠ provider integration PASS
```

### B. Partial success can be dangerous

REST data made the application look partly alive while time-sensitive streaming was unavailable.

TraID must expose degraded capability and fail closed when required data is unavailable/stale.

### C. Real provider contract tests are needed

Mocks cannot detect every provider metadata/API evolution.

TraID should have bounded, public/read-only provider smoke/contract tests in addition to deterministic unit tests.

### D. Diagnose before patching

Observed investigation path:

```text
Dashboard DEGRADED
→ backend stream error
→ connect_and_subscribe
→ SDK Info initialization
→ spotMeta indexing
→ pinned SDK version
→ temporary upgrade
→ initialization PASS
→ live stream PASS
```

Reusable engineering pattern:

```text
observe
→ isolate
→ reproduce
→ identify boundary
→ test smallest hypothesis
→ verify recovery
```

### E. Dependency upgrade is not automatic adoption

The temporary `0.24.0` upgrade solved the observed failure. It does not authorize TraID to blindly pin that version later. C04 must inspect current official behavior when implementation actually begins.

# 8. Mapping to existing TraID Cards

This reconnaissance does not require roadmap restructuring.

| Finding | Card |
|---|---|
| Provider isolation | C03 |
| Hyperliquid REST/WebSocket | C04 |
| Freshness, provenance, health | C05 |
| Historical/replay concerns | C06 |
| Depth, spread, imbalance, slippage | C07 |
| Trade flow and sweeps | C08 |
| OI, funding, basis, volatility | C09 |
| Regime, crowding, liquidity | C10 |
| Typed Strategy evidence | C16 |
| Deterministic execution/liquidity risk | C17 |
| Historical slippage/accounting | C18 |
| Signal evaluation | C20 |
| Dashboard | C22 |
| Feed telemetry/failure/recovery | C23 |
| Provider regression/release checks | C25/C26 |

No Card is authorized by this mapping.

# 9. TraID target pattern

```text
Hyperliquid
        ↓
Hyperliquid Adapter
├── REST ingestion
└── WebSocket ingestion
        ↓
Canonical TraID Data
        ↓
Data Quality + Provenance
├── source timestamp
├── received timestamp
├── freshness
├── gap state
├── validation state
└── recovery state
        ↓
Deterministic Analytics
├── Order Book
├── Trade Flow
├── Derivatives
├── Volatility
├── Liquidity
└── Execution Cost
        ↓
Evidence / Signal Fusion
        ↓
Typed Deterministic Strategy
        ↓
Mandatory Deterministic Risk Gate
        ↓
Decision Support
```

The external repository informs selected analytics and operational patterns. It owns no TraID layer.

# 10. Reuse acceptance rules

Before adapting any implementation idea from this repository:

1. Identify the exact owning TraID Card.
2. Re-inspect the current external implementation.
3. Verify license/source provenance before copying code.
4. Verify official Hyperliquid semantics for financially material fields.
5. Define TraID-owned typed contracts.
6. Define units and timestamps explicitly.
7. Define stale/missing/invalid behavior.
8. Build deterministic fixtures.
9. Test boundaries and failure paths.
10. Run provider integration validation where required.
11. Record exact evidence.
12. Never bypass Strategy/Risk ownership.
13. Never start a future Card early because reference code exists.

# 11. Decision matrix

| Capability | Decision | Reason |
|---|---|---|
| REST + WebSocket separation | ADAPT | Good failure isolation |
| Order-book depth/spread | ADAPT | Deterministic microstructure |
| Order-book imbalance | ADAPT AS EVIDENCE | Not directional probability |
| Depth decay | ADAPT AFTER VERIFY | Useful liquidity structure |
| Trade-flow windows | ADAPT AFTER VERIFY | Useful executed-flow context |
| Buy/Sell volume and ratio | ADAPT | Aggressive-flow evidence |
| Sweep detection | VERIFY | Detector semantics matter |
| Multi-timeframe analytics | ADAPT | Shows horizon disagreement |
| OI | VERIFY | Units/semantics critical |
| OI trend/velocity | VERIFY | Formula/window required |
| Funding | ADAPT AFTER OFFICIAL VERIFY | Financial semantics matter |
| Basis | ADAPT AFTER OFFICIAL VERIFY | Formula/source explicit |
| ATR / realized volatility | ADAPT | Useful deterministic metrics |
| Volatility regime | VERIFY / REIMPLEMENT | Transparent thresholds required |
| Position crowding | VERIFY / REIMPLEMENT | No opaque score |
| Market regime | VERIFY / REIMPLEMENT | Deterministic rules required |
| Liquidity regime | VERIFY / REIMPLEMENT | Measurable thresholds |
| Slippage simulation | STRONG ADAPT AFTER VERIFY | Valuable Strategy/Risk input |
| Event counters | ADAPT | Strong observability |
| Module health | ADAPT + STRENGTHEN | Partial failure visibility |
| Dense dashboard primary UX | REJECT | Too much simultaneous information |
| Diagnostic dashboard concept | ADAPT | Excellent engineering visibility |
| Provider-specific Core models | REJECT | Violates provider neutrality |
| Hidden scores | REJECT | Not financially defensible |
| One global connection state | REJECT | Hides partial failures |
| Blind dependency pinning | REJECT | Runtime failure proved risk |
| Repository as TraID base | REJECT | TraID architecture remains owned |

# 12. Final decision

Repository role:

```text
REFERENCE
+
SELECTIVE ADAPT
+
INDEPENDENT FINANCIAL VERIFICATION
```

Highest-value lessons:

1. REST/WebSocket ingestion separation.
2. Market-microstructure analytics.
3. Trade-flow and multi-timeframe context.
4. Derivatives and volatility concepts.
5. Slippage/liquidity analysis.
6. Feed/event/module telemetry.
7. Explicit degraded-state handling.
8. Real provider integration testing.
9. Never trust UI labels or external financial semantics without proof.
10. Keep TraID canonical data, evidence, Strategy, Risk Gate and governance independent.

The reconnaissance supports the existing TraID architecture rather than providing a reason to replace it.

# 13. Evidence status

## Runtime-verified during reconnaissance

- Docker frontend/backend startup
- REST-derived historical/context data available
- initial live stream failure
- repository pin `hyperliquid-python-sdk==0.20.1`
- `IndexError` during SDK `Info` initialization
- problematic current `spotMeta` identifier/index assumption observed
- temporary in-container upgrade to `0.24.0`
- successful Mainnet `Info` initialization after temporary upgrade
- backend restart
- live WebSocket connection
- dashboard `Data Quality: OK`
- non-zero live event counters

## Not yet independently verified

- exact OI semantics
- OI velocity formula
- crowding formula
- regime formulas
- liquidity thresholds
- trade-window implementation semantics
- sweep detector
- liquidation detector
- slippage formula
- every dashboard metric's financial correctness

These remain explicitly untrusted until their owning TraID Card performs the required inspection and validation.
