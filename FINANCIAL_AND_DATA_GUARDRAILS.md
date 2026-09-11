# FINANCIAL_AND_DATA_GUARDRAILS.md

## 0. Purpose

TraID V1 canonical financial, market-data, temporal-integrity, and consequential-decision guardrails. These are executable invariants. `AI MAY INTERPRET. DETERMINISTIC SOFTWARE OWNS FINANCIAL TRUTH. UNKNOWN MATERIAL SEMANTICS FAIL CLOSED.` V1 is read-only and never executes live trades.

---

## 1. Authority

This file owns cross-Card financial/data invariants. Card specs may make rules more specific but never silently weaker. Evidence proves tests; the Harness owns STOP behavior. Material changes require rationale, versioning, regression, Evidence, and applicable human approval.

---

## 2. Core Safety Invariants

```text
G01 No live trade execution in V1.
G02 No trading credentials or wallet private keys.
G03 Normalize provider payloads before Core financial logic.
G04 STALE/UNAVAILABLE required data cannot silently become trusted.
G05 Missing values cannot silently become meaningful zero/defaults.
G06 Material units/signs/timestamps must be explicit and verified.
G07 AI/model output cannot define financial truth.
G08 Strategy cannot bypass deterministic Risk Gate.
G09 Risk Gate is mandatory, deterministic, reason-coded, fail-closed, non-bypassable.
G10 Historical evaluation cannot access future information.
G11 Unresolved same-bar stop/target ambiguity uses STOP FIRST.
G12 Financial accounting must reconcile.
G13 Heuristic liquidation pressure is not authoritative liquidation truth.
G14 Alignment is not probability.
G15 Unverified high-impact news is uncertainty, not directional fact.
G16 Large wallet is not smart money.
G17 Silent financial fallback is prohibited.
G18 Critical guardrail failure blocks Card/release completion.
```

---

## 3. Canonical Numeric Rules

Define unit, asset/currency, sign, precision, range, zero/null meaning, timestamp basis, window, source, and version. Never infer semantics from names. Choose Decimal/fixed-point where exact accounting requires it. Expected test values must be independently derived.

---

## 4. Missing / Zero / Null / NaN / Infinity

`0`, null, missing, NaN, infinities, unavailable, N/A, and unknown are distinct. Missing required input → invalid/unavailable. NaN/Infinity in consequential calculation → reject/fail closed. Never map provider failure to plausible financial zero.

---

## 5. Time Semantics

Explicitly distinguish event/source, exchange, bar open/close, received, processed, decision, fill, publication, release, and outcome times. Use timezone-aware canonical timestamps and deterministic tie ordering.

---

## 6. Data Quality States

Canonical states: `LIVE / DELAYED / STALE / UNAVAILABLE`. Thresholds are versioned configuration. Downstream sees state. No relabeling STALE/UNAVAILABLE as LIVE.

---

## 7. Provenance

Retain source/provider, exchange, instrument, source/received timestamps, freshness, validation, gap/recovery, schema, dataset/hash, configuration version. Missing consequential provenance → `PROVENANCE_INCOMPLETE` and fail closed/mark unusable.

## 7.1 Relevant Coverage Integrity

TraID must not represent incomplete relevant coverage as complete market
awareness. Required missing, stale, delayed, unavailable, incomplete, or
unverified evidence retains explicit status and remains visible in decision
context. Missing data must not silently become zero, neutral, bullish,
bearish, or `no event`; unavailable evidence must not be fabricated by AI or
deterministic code.

Source substitution or fallback is allowed only when it is explicit,
semantically compatible, provenance-preserving, and covered by the applicable
quality policy. If a decision requires evidence that does not meet its
configured quality or coverage policy, existing fail-closed Strategy/Risk
behavior applies. Coverage requirements may differ by Strategy/configuration
and must be explicit rather than assumed globally. Broad collection does not
override source authority hierarchy or deterministic financial semantics.

Use existing reason codes where applicable, including
`DATA_STALE`, `DATA_UNAVAILABLE`, `DATA_INVALID`,
`PROVENANCE_INCOMPLETE`, and `INSUFFICIENT_EVIDENCE`; no new reason code is
introduced by this guardrail.

---

## 8. Duplicate / Gap / Late / Out-of-Order

Use deterministic dedup identity. Record gaps and recovery. Late/out-of-order policy must explicitly reorder in bounded window, reject, recompute bounded state, or mark degraded. Never rewrite original point-in-time decision context silently.

---

## 9. Recovery / Backfill

Preserve original failure, recovery source/interval/time, quality transition, remaining gaps. Recovered data does not prove it existed at the original decision time.

---

## 10. Provider Isolation

Provider semantics stay in adapters until verified/normalized. Core cannot depend on raw Hyperliquid names, JSON, errors, timestamp quirks, or SDK classes.

---

## 11. Instrument Identity

Do not join solely by display symbol. Distinguish venue/provider, base, quote, product type, identifier. BTC spot/perpetual are not interchangeable.

---

## 12. Price Semantics

Last, mid, bid, ask, mark, oracle, index, close, VWAP, and fill price are distinct. Strategy/Risk/P&L must name required semantic. Unknown → `FINANCIAL_SEMANTICS_UNVERIFIED` + STOP.

---

## 13. Order Book Integrity

Validate side, positive price, nonnegative size, ordering, duplicate-level policy, crossed/locked policy, snapshot/update identity, timestamp, quality. Invalid book cannot produce trusted liquidity metrics.

---

## 14. Slippage Estimates

Hypothetical only. Record snapshot, side, size, reference price, depth consumed, insufficient-depth behavior, timestamp/quality. Never invent liquidity.

---

## 15. Trade Flow / CVD

Verify aggressor-side semantics. Define aggressive buy/sell, signed volume, dedup, window/session, reset, late/order behavior, restart state. Unknown semantics → STOP. CVD is evidence, not authority.

---

## 16. Candles / Bars

Define interval/boundaries/timezone/OHLCV/completeness/gaps. Incomplete bar is not completed history. Historical indicators use only available bars.

---

## 17. Funding

Verify meaning, sign, payer/receiver, interval, timestamp, realized/current/predicted state, annualization. Unknown → `FINANCIAL_SEMANTICS_UNVERIFIED` + STOP.

---

## 18. Open Interest

Verify unit, asset/notional convention, aggregation, timestamp, instrument, change calculation. Do not compare incompatible units or infer direction from OI alone.

---

## 19. Basis / Mark / Oracle / Index

Use only verified semantics. Never substitute price types because intended data is missing. `NO SILENT FALLBACK`.

---

## 20. Volatility / ATR / VWAP / Momentum

Define formula/window/warm-up/price input/bar completeness/session/missing behavior/version. Insufficient warm-up is explicit. Known-value tests required.

---

## 21. Regime / Crowding

Deterministic versioned classifications with inputs, thresholds, boundary behavior, UNKNOWN. Not probability. Threshold changes require governed evaluation/versioning.

---

## 22. Liquidation Truth

Canonical: `AUTHORITATIVE_LIQUIDATION_EVENT / HEURISTIC_LIQUIDATION_PRESSURE / UNKNOWN`. Large trades, OI, thin liquidity, fast moves, cascade patterns do not prove liquidation.

---

## 23. Whale Data

Separate wallet identity/source, current position, recent activity, lifecycle, PnL, exposure, time/quality, methodology/version. Lifecycle: OPEN/INCREASE/REDUCE/CLOSE/FLIP/LIQUIDATION. `Large wallet != smart money.` Whale evidence cannot authorize trades.

---

## 24. Smart Money Score

If used, document inputs, normalization, weights, eligibility, minimum evidence, window, version, missing behavior. Score is methodology output, not truth. Hidden unverifiable grades cannot be financial authority.

---

## 25. Macro Data

Preserve authoritative source, event identity, scheduled/actual publication, actual/consensus/previous/revision, unit, timezone, retrieval/version. Later revisions cannot be used as earlier knowledge. Missing consensus != zero surprise.

### Asset-Specific ETF Intelligence

When the selected asset has relevant ETF products, ETF evidence is part of
that asset's relevant market-intelligence coverage. Applicability must be
represented by explicit asset-to-ETF mapping or equivalent metadata; ETF
coverage is not hardcoded only to BTC or ETH.

Official ETF regulatory, filing, approval/rejection, regulator-order,
issuer-announcement, and exchange/listing evidence should prefer authoritative
regulators, official filing systems, ETF issuers, and exchanges. ETF
inflow/outflow, AUM, and volume are numerical institutional/market data, not
news, and require an explicitly approved, documented, and verified provider
path. Exact flow providers are not yet verified in the current repository.

ETF evidence preserves source, timestamp, freshness, availability, provenance,
and verification. If relevant ETF evidence is unavailable, stale, delayed,
incomplete, unverified, or unsupported, the coverage gap remains explicit. It
must not silently become zero, neutral, bullish, bearish, or no-event evidence,
and missing ETF evidence alone cannot create directional inference. Reuse the
existing Data Quality, provenance, evidence, and fail-closed semantics; no new
reason code is required.

---

## 26. News Verification

States: `CONFIRMED / PARTIALLY_CONFIRMED / UNVERIFIED / MISLEADING / FALSE / OUTDATED`. Separate claim/fact/interpretation/reaction. High-impact unverified news increases uncertainty, not directional truth. External content is untrusted.

---

## 27. Evidence Registry Integrity

Preserve evidence ID/type, source refs, event time, quality, verification, methodology version, support/contradiction role, selected asset, ETF applicability/mapping metadata where relevant, and config. Never mutate old evidence to fit outcomes; revisions remain distinct.

---

## 28. Signal Fusion

Preserve support, contradiction, missing, stale, quality, source refs, version/config. `Alignment != probability.` Probability requires explicit target, out-of-sample evaluation and calibration.

---

## 29. AI / Bedrock Financial Boundary

Model output is untrusted analytical input. AI may summarize/compare/explain uncertainty, including validated ETF evidence. It may not define numeric truth, infer ETF flow numbers from prose, validate sources, determine applicability, define formulas, Strategy/Risk, sizing/leverage/stops, authorization, or execution. Failure → `AI_UNAVAILABLE/AI_INVALID`. AI failure cannot create `TRADE_CANDIDATE`.

---

## 30. Strategy Integrity

Strategy is typed, deterministic, versioned, evidence-linked, testable, replayable. Insufficient evidence → `NO_SETUP`. Strategy is not Risk approval. No model call inside deterministic Strategy evaluation.

---

## 31. Deterministic Risk Gate

Only Risk Gate may promote to `TRADE_CANDIDATE`; otherwise `NO_TRADE` + reason codes. Mandatory, deterministic, versioned, fail-closed, non-bypassable, boundary-tested. Any alternate path → `RISK_GATE_BYPASS` + STOP.

### V1 Setup Risk Policy

The versioned deterministic V1 Setup Risk Policy is one part of the full Risk
Gate and does not guarantee `TRADE_CANDIDATE` by itself:

```text
setup leverage: fixed 2x
maximum permitted Net Loss: <= 10% of the hypothetical position
minimum permitted Net Profit Target: >= 20% of the hypothetical position
numeric policy failure: NO_TRADE using existing RISK_REJECTED semantics
```

Net Loss and Net Profit Target are Net P&L measures on the hypothetical
leveraged position, after all applicable verified trading fees, funding,
slippage, and execution costs. Required costs that are unavailable or
unverified cannot silently be treated as zero; the setup fails closed.

Entry, invalidation/Stop, and Target must come from the valid deterministic
market/Strategy structure. The Risk Gate evaluates that setup and must not
move or fabricate Stop/Target to satisfy the percentages. The policy does not
encode a mandatory raw price distance such as a 5% stop or 10% target.

For example, Net Loss 7%, Net Profit Target 24%, and leverage 2x may pass this
specific policy; Net Loss 10.5% or Net Profit Target 18% fails it. Other
evidence, quality, provenance, financial, and Risk checks remain mandatory.

---

## 32. Risk Configuration

Schema/range validation, version, effective time where relevant, safe failure, tests. No permissive silent defaults. Never change limits solely to improve backtests.

---

## 33. Position Size / Leverage Boundary

V1 executes nothing. The Setup Risk Policy's fixed 2x leverage is a
deterministic configured setup constraint, not account-level advice. TraID does
not know account balance, does not calculate account-level risk, and does not
decide capital allocation or position size. The human decides whether and how
to allocate capital or execute; V1 remains decision-support only. AI cannot
choose or change leverage, size, Stop, Target, or Risk policy thresholds.

---

## 34. Historical Point-in-Time Rule

At time t use only information contractually available by t. No future candles/fills/outcomes, later revisions/news verification/wallet state/recovery/AI/Evidence. Structural prevention preferred.

---

## 35. Anti-Lookahead Tests

Test future candle/outcome injection, decision/fill ordering, macro/news/ETF timing, wallet timing, slicing, incomplete bars, replay ordering. Profitability is not proof. Future access → `LOOKAHEAD_VIOLATION` + STOP.

---

## 36. Decision / Fill Timing

Define evidence availability, Strategy time, Risk time, candidate time, earliest fill, fill-price semantic. A bar close cannot imply an earlier same-bar fill without proof.

---

## 37. Same-Bar Ambiguity

If stop and target both touch and ordering is unknown: `STOP FIRST`, unless higher-resolution authoritative data proves order. Never choose target-first for performance.

---

## 38. Fees

Define basis, maker/taker, rate, currency, timing, entry/exit, version/source. Apply consistently. Zero fees only in explicit zero-fee scenario.

---

## 39. Funding in Backtest

Define timestamps, source/rate, sign, exposure, payment formula, missing behavior. Never apply future-known rates. Accounting must reconcile.

---

## 40. Slippage / Fill Model

State market/limit assumption, reference, slippage, depth/liquidity, partial-fill, gaps, version. Do not overclaim realism. Prefer simple conservative semantics.

---

## 41. Liquidation in Backtest

Define verified price reference, margin/leverage, fees/funding, threshold/formula, gaps, version. Unverified provider mechanics cannot be presented as authoritative.

---

## 42. P&L Reconciliation

Per trade: gross P&L, fees, funding, modeled costs, net P&L. Aggregate net P&L must reconcile to equity change within documented tolerance. Failure → `FINANCIAL_INVARIANT_FAILED` + STOP.

---

## 43. Return / Risk Metrics

Document definitions/denominators/edge cases for return, win rate, profit factor, expectancy, average R, drawdown, Sharpe-like metrics, MFE, MAE. Undefined stays undefined. One metric never proves quality.

---

## 44. Outcome Tracking

Original candidate/evidence/Strategy/Risk/data/config/result remain immutable. Later outcome is separate. Track MFE/MAE, target/stop, resolved state, horizon, observed/simulated result. Future outcome never rewrites original context.

---

## 45. Evaluation Integrity

Runs identify dataset/hash/time range/config/analytics/fusion/Strategy/Risk/backtest versions, AI metadata where relevant, metric definitions, failures/rejections. Compare like with like. Evaluation before complexity.

---

## 46. Probability / Calibration

Future probability requires explicit target, train/eval separation, out-of-sample/walk-forward, calibration analysis, reliability/Brier or suitable metric, versioning, drift monitoring. Never rename alignment/confidence as probability.

---

## 47. Determinism / Reproducibility

Identical controlled inputs/config/version → identical deterministic analytics, Fusion, Strategy, Risk and replay/backtest within defined tolerance. Randomness must be justified, seeded, versioned.

---

## 48. Fail-Closed Matrix

| Condition | Required behavior |
|---|---|
| STALE/UNAVAILABLE required data | no trusted consequential promotion |
| malformed numeric input | reject/invalid |
| unknown unit/sign/time | `FINANCIAL_SEMANTICS_UNVERIFIED` + STOP |
| provider failure → plausible zero | prohibited |
| invalid Risk config | `NO_TRADE` |
| AI failure | `AI_UNAVAILABLE/AI_INVALID`; no promotion |
| unverified high-impact news | uncertainty only |
| relevant ETF evidence unavailable/stale/unverified | explicit coverage gap; no directional promotion |
| insufficient Strategy evidence | `NO_SETUP` |
| Risk rejection | `NO_TRADE` |
| Risk bypass | `RISK_GATE_BYPASS` + STOP |
| future access | `LOOKAHEAD_VIOLATION` + STOP |
| unresolved same-bar | `STOP FIRST` |
| P&L mismatch | `FINANCIAL_INVARIANT_FAILED` + STOP |
| heuristic liquidation | never authoritative |
| undefined metric | report undefined |
| secret/trading credential exposure | STOP + security response |

---

## 49. Guardrail Test Classes

`UNIT_SEMANTICS, SCHEMA_VALIDATION, DATA_QUALITY, PROVENANCE, TIMESTAMP_ORDERING, NUMERIC_BOUNDARY, FINANCIAL_FORMULA, FINANCIAL_RECONCILIATION, PROVIDER_FAILURE, AI_FAIL_CLOSED, RISK_GATE_BOUNDARY, RISK_GATE_BYPASS, ANTI_LOOKAHEAD, REPLAY_DETERMINISM, SECURITY_BOUNDARY, GOLDEN_CASE`. Critical applicable tests become release-blocking by C25.

---

## 50. Independent Expected Values

Do not compute expected with the same production formula. Prefer hand-checkable fixtures, documented arithmetic, independent reference implementation where justified, edge/property/invariant tests.

---

## 51. Boundary Testing

Test below/exact/above threshold, zero, invalid negative, min/max valid, missing, NaN/Infinity, stale/time boundaries, empty/single, extreme valid. Risk/financial boundaries must be exact.

---

## 52. Metamorphic / Invariant Tests

Where valid: equal added buy/sell leaves net delta unchanged; higher fees/cost cannot improve net P&L/return; same replay stays same; STALE cannot be safer than identical LIVE; Risk rejection cannot become TRADE_CANDIDATE without relevant validated change.

---

## 53. Data Fixtures

Small, explicit, versioned, source-labeled, deterministic, inspectable, secret-free, licensed/allowed. Prefer synthetic unit fixtures for clear expected values. Real captures require provenance/data-rights review.

---

## 54. Configuration Versioning

Version freshness thresholds, analytics windows, regime/fusion rules, Strategy thresholds, Risk limits, fee/funding/fill/slippage assumptions, evaluation horizons. Never silently change config between compared runs.

---

## 55. Error / Reason Codes

Use stable typed codes: `DATA_STALE, DATA_UNAVAILABLE, DATA_INVALID, PROVENANCE_INCOMPLETE, FINANCIAL_SEMANTICS_UNVERIFIED, INSUFFICIENT_EVIDENCE, AI_UNAVAILABLE, AI_INVALID, NO_SETUP, RISK_CONFIG_INVALID, RISK_REJECTED, RISK_GATE_BYPASS, LOOKAHEAD_VIOLATION, FINANCIAL_INVARIANT_FAILED, SECURITY_BOUNDARY_VIOLATION`.

---

## 56. Observability for Consequential Decisions

Retain enough to answer what data/source/time/quality/evidence/formulas/versions/Strategy/Risk/config/AI/result/reasons/outcome. Never log secrets. Observability does not replace Evidence.

---

## 57. Security Boundary

No path requires exchange trading permission, wallet key, seed phrase, or live execution credential. External data/model output are untrusted. Least privilege. Unexpected write/execution or secret exposure → `SECURITY_BOUNDARY_VIOLATION` + STOP.

---

## 58. Guardrail Change Procedure

Record Guardrail ID, current rule, problem/evidence, proposal, rationale, financial/data and historical-comparability impact, affected Cards, new/regression tests, version, migration/replay, rollback, approval. Never weaken solely to improve win rate/profit factor, reduce NO_TRADE, pass Golden Case/test, or match an external repo.

---

## 59. Card / Release Enforcement

A Card changing a guardrail cannot COMPLETE until applicable guardrail tests ran and PASS, degraded paths are covered, Evidence is actual, and `CARD_QUALITY_GATE: PASS`. C25 blocks release on critical tests; C26 proves success+failure paths; C27 documents verified semantics/limitations.

---

## 60. Final Rule

```text
REAL DATA BEFORE SIGNALS.
TRUSTED DATA BEFORE FINANCIAL INFERENCE.
EXPLICIT SEMANTICS BEFORE CALCULATION.
DETERMINISTIC CALCULATION BEFORE AI INTERPRETATION.
VERIFIED EVIDENCE BEFORE STRATEGY.
STRATEGY BEFORE RISK.
RISK BEFORE TRADE_CANDIDATE.
NO FUTURE DATA IN HISTORICAL DECISIONS.
NO OPTIMISTIC AMBIGUITY.
NO SILENT FALLBACK.
NO AI OVERRIDE.
NO GUARDRAIL BYPASS.
NO EVIDENCE → NO FINANCIAL CLAIM.
UNKNOWN MATERIAL SEMANTICS → STOP.
```

---
