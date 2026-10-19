# TraID — Completed Card History

This file records completed and merged V1 Cards. Add one short entry **after** each Card is merged. GitHub PRs, commits and CI remain the authoritative evidence; do not duplicate full audit reports here.

## V1-C08 — Trade Flow & CVD

- **Status:** MERGED — 2026-10-19
- **Scope delivered:** Deterministic trade-flow analytics (buy/sell volume, net delta, rolling window and session CVD); aggressor-side preservation in canonical trades and Hyperliquid HTTP/WebSocket parsers; deduplication, point-in-time handling, quality and provenance reporting.
- **Verification:** 335 tests passed locally (2 existing dependency warnings); independent Codex review **PASS** after remediation; GitHub PR push and pull-request CI passed, including tests and secret scan.
- **Review history:** Codex found and verified fixes for historical lookahead, mixed-source deduplication, invalid trade IDs and missing aggregate provenance; a subsequent provenance-digest issue was also corrected and independently rechecked.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/18
- **Merged main commit:** `7b2dbf0` (squash merge)
- **Known limitations:** Trade identity uses `(source, symbol, tid)` instead of Hyperliquid's documented `(block_time, coin, tid)` because the available payload does not establish the equivalence of `time` and `block_time`; a potential `tid` collision fails closed. Analysis requires a single logical source; quiet markets can yield unavailable quality-gated outputs. Live-provider end-to-end behavior was not established by the independent review.

<!-- Add future completed Cards below, after their PRs merge. -->

## V1-C09 — Derivatives & Volatility

- **Status:** MERGED — 2026-10-19
- **Scope delivered:** Deterministic analytics over closed 1h candles and hourly funding: ATR, realized volatility (log-return sample standard deviation, not annualized), candle-based session VWAP approximation, bounded momentum, and signed hourly funding context (latest, cumulative, mean; not annualized). Explicit warm-up, stale and unavailable states; point-in-time receipt filtering; interval-aware freshness; order-independent duplicate/conflict handling; compact provenance with an input digest. Open interest and Basis are explicitly unavailable. The Hyperliquid adapter now accepts signed funding rates.
- **Verification:** 509 tests passed locally (2 existing dependency warnings); independent Codex review **PASS** after remediation; GitHub PR CI passed, including tests and secret scan.
- **Review history:** Codex found and verified fixes for negative funding rejection, order-dependent duplicate selection and diagnostics, and Decimal-context sensitivity of the funding cap.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/19
- **Merged main commit:** `3dbd703` (squash merge)
- **Known limitations:** C06 modeled historical availability is not yet interoperable with C09 actual-receipt evaluation: replayed history fetched after the evaluation time is excluded (no lookahead) and needs a separate explicit contract. Live funding exposes only the latest observation. Candle and funding sections share continuity/recovery inputs. VWAP is a candle approximation, not trade-level VWAP. OI and Basis remain unavailable pending verification of OI units/aggregation/timing and a canonical, timestamped mark/oracle price pair. Live-endpoint behavior was not verified end to end and candle finality is not provable from receipt time.
