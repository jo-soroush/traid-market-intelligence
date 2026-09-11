# Hyperliquid Backtester → TraID Engineering Reconnaissance

**Source repository:** `Crypto-Data-API/hyperliquid-backtester`  
**License observed:** MIT  
**TraID decision:** `REFERENCE ONLY + selective ADAPT`  
**Primary relevance:** Backtest correctness, anti-lookahead, event ordering, costs, accounting reconciliation, validation methodology

## 1. Executive Summary

Hyperliquid Backtester is valuable to TraID mainly as a correctness and evaluation reference. It should not become the TraID base and should not be copied wholesale. TraID is broader: market data, quality/provenance, analytics, whale intelligence, macro/news, Bedrock intelligence, signal fusion, typed strategy logic, deterministic Risk Gate, decision support, outcome tracking, and replay.

The strongest lesson is simple:

> A credible backtest makes timing, costs, liquidation assumptions, ambiguity policy, and future-data boundaries explicit and testable.

TraID should therefore build its own backtest/replay module and selectively adapt verified patterns.

## 2. What Was Inspected

The local clone included:

```text
README.md
docs/
pyproject.toml
src/
strategies/
tests/
```

Directly inspected:

- `README.md`
- `src/hlbt/backtester.py`
- `tests/test_engine.py`
- `docs/VALIDATION.md`
- CLI installation and `hlbt --help`
- direct synthetic engine execution

No TraID implementation was taken from this repository.

## 3. Core Engine Ordering

Observed per-bar order:

```text
1. Fill pending order at current open
2. Apply funding
3. Check liquidation against adverse extreme
4. Check stop
5. Check target
6. Evaluate strategy exit at close
7. Call strategy on sliced current context
8. Queue new order for next bar
```

This ordering is important because it prevents a strategy from seeing a completed bar and pretending it filled inside that already-known bar.

**TraID classification:** ADAPT.

## 4. Structural Anti-Lookahead

The strategy receives sliced arrays equivalent to `[:i+1]`. Future bars are structurally unavailable in the normal strategy path.

**TraID classification:** ADAPT strongly.

TraID must extend this beyond candles to:

- funding
- OI
- liquidations
- macro/news timestamps
- whale events
- data revisions/backfills
- features
- regime
- historical AI annotations if replayed

Required invariant:

```text
Decision at T may use only evidence legally available at T.
```

## 5. Next-Bar Fill Discipline

Orders generated from a completed bar are filled at the next bar open.

**TraID classification:** ADAPT.

For bar-close strategies:

```text
decision at bar close
→ earliest eligible fill = next tradable event
```

If TraID later supports event/tick replay, the timing policy can evolve, but it must stay explicit and deterministic.

## 6. Same-Bar Stop/Target Ambiguity

If both stop and target occur inside one unresolved OHLC bar, the repository uses:

```text
STOP FIRST
```

This is conservative because OHLC does not reveal intrabar sequence.

**TraID classification:** ADAPT as a financial invariant.

TraID rule:

> Same-bar stop/target ambiguity resolves to `STOP FIRST` unless higher-resolution evidence proves the actual sequence.

## 7. Fees and Slippage

The engine models trading costs instead of reporting frictionless PnL.

Observed behavior includes:

- entry fee
- exit fee
- adverse slippage
- funding
- zero-cost vs costed comparison

**TraID classification:** ADAPT concept, VERIFY exact semantics.

TraID should separate:

```text
MODELED_COST
OBSERVED_COST
EXCHANGE_VERIFIED_COST
UNKNOWN
```

and store fee, slippage, funding, and other costs independently.

## 8. Funding

The repository supports funding and tests that positive funding charges longs and that funding can be disabled.

**TraID classification:** VERIFY.

Before trusted use, TraID must independently verify:

- sign convention
- interval
- timestamp alignment
- source units
- application order
- historical completeness

Unknown financially material semantics must not be guessed.

## 9. Liquidation

The engine contains leverage-aware liquidation logic, but it is approximate.

**TraID classification:** REFERENCE ONLY / VERIFY.

Do not treat simplified liquidation as authoritative Hyperliquid behavior. TraID must preserve:

```text
HEURISTIC_LIQUIDATION != AUTHORITATIVE_LIQUIDATION
```

Potentially missing or simplified exchange semantics include maintenance tiers, exact mark-price behavior, cross/isolated margin effects, portfolio interactions, and fees.

## 10. Ledger and Equity Reconciliation

The engine closes remaining positions at the final available close and reconciles trade PnL with final equity. The tests include net-PnL/equity reconciliation.

**TraID classification:** ADAPT strongly.

TraID should require reconciliation across:

```text
trade ledger
position state
cash/equity
fees
funding
realized PnL
final equity
```

A mismatch should block a backtest result.

## 11. High-Value Tests

`tests/test_engine.py` verified behavior including:

1. no future-data access
2. next-bar open fill
3. fees on both legs
4. costed vs zero-cost comparison
5. positive funding charges longs
6. funding disable path
7. stop-first same-bar ambiguity
8. end-of-data close
9. leverage liquidation path
10. no-trades summary
11. trade PnL/equity reconciliation
12. one equity point per bar
13. warmup error
14. unknown parameter rejection
15. indicator warmup `NaN`
16. SMA hand-check
17. RSI monotonic behavior

The most transferable asset is the test philosophy:

> Every financially material assumption should become an executable invariant.

## 12. Validation Methodology

`docs/VALIDATION.md` contains strong evaluation discipline:

- profitable backtest is weak evidence alone
- trial count matters
- multiple comparisons inflate false discoveries
- record how many variants were tried
- use economically motivated hypotheses
- prefer parameter plateaus over isolated spikes
- define holdout before looking
- repeated holdout tuning turns holdout into training data
- win rate alone is weak
- inspect expectancy, profit factor, drawdown, fees, Sharpe, trade count
- small samples are hypothesis-generating, not conclusive
- stress-test costs/slippage
- paper trade after historical validation

Useful sequence:

```text
Hypothesis
→ Plain implementation
→ Development window
→ Costs/trade count
→ Parameter plateau
→ Record all trials
→ One-time holdout
→ Replay
→ Paper trade
```

**TraID classification:** ADAPT as evaluation policy.

## 13. Experiment Governance for TraID

Recommended evaluation metadata:

```text
experiment_id
strategy_version
config_version
risk_gate_version
data_version
time_range
development_or_holdout
trial_family_id
trial_index
total_trials
cost_model_version
assumption_set
metrics
failure_flags
created_at
```

Key rule:

> A holdout that influenced design is no longer pristine holdout data.

## 14. What This Repository Does Not Solve

It is not a complete TraID platform. It does not solve:

- order-book replay
- partial fills
- market impact
- queue position
- live data quality/provenance
- multi-source intelligence
- whale/entity intelligence
- verified macro/news
- AI analysis
- signal fusion
- deterministic Risk Gate
- production decision support

That is why it should not become the TraID base.

## 15. Data Dependency

The repository documents a bulk historical sync path involving CryptoDataAPI and a paid plan.

**TraID classification:** REJECT as mandatory dependency.

TraID should preserve provider independence.

## 16. Local Execution Findings

The package was installed locally in an isolated environment. `hlbt --help` worked, and CLI commands included:

```text
sync
run
demo
index
```

A direct synthetic engine run produced valid metrics including trades, win/loss counts, profit factor, expectancy, return, Sharpe, drawdown, equity, fees, and liquidation count.

The demo command expected a local candle file, so CLI presence alone did not prove full demo reproducibility.

## 17. Decision Matrix

| Capability | Decision | Why | TraID treatment |
|---|---|---|---|
| Structural anti-lookahead | ADAPT | Prevents future leakage | Extend to all point-in-time evidence |
| Next-bar fill | ADAPT | Honest bar timing | Explicit fill policy |
| Same-bar `STOP FIRST` | ADAPT | Conservative ambiguity | Financial invariant |
| Fee accounting | ADAPT | Avoids gross-only bias | Separate cost components |
| Adverse slippage | ADAPT | Better than frictionless fills | Calibrate later |
| Funding | VERIFY | Required but semantic-sensitive | Verify interval/sign/source |
| Simplified liquidation | REFERENCE ONLY | Not exchange truth | Build verified/heuristic distinction |
| PnL/equity reconciliation | ADAPT | Detects accounting bugs | Blocking invariant |
| Validation methodology | ADAPT | Protects against overfitting | C20 evaluation governance |
| Paid historical sync | REJECT as dependency | Avoid coupling | TraID provider adapters |
| Whole repo as TraID base | REJECT | Too narrow | TraID-owned module |

## 18. Mapping to TraID Cards

### V1-C06 — Historical Data & Replay Foundation

Carry forward:

- point-in-time discipline
- immutable ordering
- warmup handling
- deterministic replay

### V1-C18 — Backtest Engine Integration

Highest-value lessons:

- anti-lookahead
- next-event fill
- same-bar pessimism
- explicit fees/slippage/funding assumptions
- deterministic replay
- accounting reconciliation
- versioned assumptions

### V1-C20 — Evaluation Registry

Carry forward:

- trial count
- development vs holdout
- cost stress
- sample-size warnings
- parameter plateau analysis
- holdout reuse tracking

### V1-C23 — Observability

Record data/config/strategy/risk versions, assumptions, failures, and reconciliation status.

### V1-C26 — Golden Case

Golden replay should prove:

```text
no future data
deterministic result
same-bar policy
cost accounting
Risk Gate behavior
reproducible final ledger
```

## 19. TraID Invariants Derived from This Audit

```text
BT01 Future data MUST NOT be visible to a historical decision.
BT02 Decision and fill timing MUST be explicit.
BT03 Same-bar ambiguity MUST be pessimistic unless sequence evidence exists.
BT04 Fees MUST be explicit.
BT05 Slippage assumptions MUST be versioned.
BT06 Funding semantics MUST be verified.
BT07 Heuristic liquidation MUST NOT be authoritative.
BT08 Trade ledger and equity MUST reconcile.
BT09 Every run MUST record data/config/strategy/risk versions.
BT10 Holdout reuse MUST invalidate pristine-holdout status.
BT11 Trial count MUST be retained.
BT12 Small samples MUST NOT be presented as strong evidence.
BT13 Backtest success MUST NOT bypass Risk Gate.
BT14 Identical replay inputs MUST produce deterministic results.
```

## 20. Final Decision

**Repository decision:** `REFERENCE ONLY + selective ADAPT`

Strongly adapt:

- anti-lookahead
- explicit event ordering
- next-event fill discipline
- pessimistic same-bar policy
- cost-aware accounting
- ledger reconciliation
- deterministic replay
- executable financial invariants
- trial/holdout governance

Do not copy blindly:

- simplified liquidation
- paid data dependency
- entire engine/platform shape
- any exchange semantic not independently verified

**Primary TraID influence:** `C18 Backtest Engine Integration` and `C20 Evaluation Registry`.
