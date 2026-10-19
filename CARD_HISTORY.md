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
