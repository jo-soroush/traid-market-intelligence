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

## V1-C10 — Market State & Evidence Engine

- **Status:** MERGED — 2026-10-21
- **Scope delivered:** Deterministic, versioned market-state classification combining C07 liquidity, C08 trade flow and C09 derivatives evidence. Independent direction, volatility, liquidity, aggressive-flow, funding, crowding and liquidation dimensions with a conservative composite regime. Point-in-time consistency checks, source provenance, dimension-level trust, explicit UNKNOWN states, configurable thresholds, and deterministic liquidation deduplication.
- **Verification:** 711 tests passed locally (2 existing dependency warnings); independent Codex review **PASS** after remediation; GitHub push and pull-request CI passed, including tests and secret scan.
- **Review history:** Codex identified and verified fixes for internally inconsistent timestamps and C09 provenance, order-dependent liquidation serialization, future-received event contamination, and incorrect evidence selectors.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/20
- **Merged main commit:** `ea35f9b` (squash merge)
- **Known limitations:** Thresholds remain uncalibrated; without configured thresholds, corresponding classifications remain UNKNOWN. Crowding remains UNKNOWN pending verified Open Interest/Basis. No verified market-wide liquidation source is integrated, and heuristic liquidation pressure is inactive. Source verification and some units remain caller-asserted. C06/C09 historical replay compatibility remains unresolved. Live-feed end-to-end behavior was not independently verified.

## V1-C11 — Whale Intelligence Foundation

- **Status:** MERGED — 2026-10-21
- **Scope delivered:** Curated Hyperliquid BTC wallet tracking with a read-only account client, normalized positions and fills, deterministic OPEN/INCREASE/REDUCE/CLOSE/FLIP/LIQUIDATION lifecycle evidence, position reconciliation, current long/short exposure, activity and performance evidence, and transparent versioned Smart Money methodology.
- **Verification:** 858 tests passed locally (2 existing dependency warnings); independent Codex review **PASS** after remediation; GitHub push and pull-request CI passed.
- **Review history:** Codex identified and verified fixes for Decimal precision, continuity-gap eligibility, ambiguous same-millisecond fill ordering, duplicate serialization, partial scoring weights and direction-label contradictions. Fill-fragmentation sensitivity is explicitly disclosed.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/21
- **Merged main commit:** `9832b19` (squash merge)
- **Known limitations:** Provider history is capped at 10,000 recent fills; long performance windows may be incomplete. Net PnL composition and some liquidation semantics remain unverified. Smart Money scores are descriptive, fill-based, sensitive to fragmentation and not evidence of predictive skill. No universal wallet discovery or trading authority is provided.

## V1-C12 — Macro Intelligence

- **Status:** MERGED — 2026-10-22
- **Scope delivered:** Source-aware BLS CPI and employment data, Federal Reserve FOMC statements and schedules, deterministic macro evidence, point-in-time safeguards, revision and conflict handling, and provider-neutral BTC ETF identity, applicability and coverage contracts.
- **Verification:** 1,067 tests passed locally, including 209 C12 tests; independent Codex audit PASS; GitHub push and pull-request CI PASS.
- **Review history:** Corrected original-release vintage claims, FOMC statement parsing and freshness, Decimal precision, simultaneous BLS conflicts, ETF mapping lookahead, payroll units, announcement matching, conflicting schedules and policy-continuity validation.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/22
- **Merged main commit:** `121c3cd` (squash merge)
- **Known limitations:** PCE and GDP unavailable without BEA credentials; no approved ETF numeric or consensus provider; BLS original-release vintages unavailable; schedules require curated evidence; historical FOMC statement parsing is bounded and unrecognized wording fails closed. Macro and ETF evidence has no trading authority.

## V1-C13 — Primary-Source News Verification

- **Status:** MERGED — 2026-10-26
- **Scope delivered:** Six-state claim verification (CONFIRMED / PARTIALLY_CONFIRMED / UNVERIFIED / MISLEADING / FALSE / OUTDATED) over human curations of untrusted claim text, with fact/interpretation separation and embedded instructions ignored. SEC rule-change events in the Federal Register qualify only through a human verification of the rendered GovInfo PDF bound to its SHA-256, cross-checked against GovInfo HTML, MODS and FR metadata. Fund subjects resolve only through evidence-backed file-number links, by exact ticker or exact filing name. Layered point-in-time availability; numerical ETF data is excluded from news; bounded credential-free source client; optional read-only C12 macro adapter.
- **Verification:** 1,554 tests passed locally (2 existing dependency warnings), including 487 C13 tests; GitHub push and pull-request CI on the final PR head passed (1,554 passed, secret scan passed); independent Codex final review **PASS** after remediation; `CARD_QUALITY_GATE: PASS` recorded in the PR.
- **Review history:** Codex found and verified fixes for unbound and cyclic manual-record supersession, non-canonical fund provenance, premature HTTP EOF and ambiguous Transfer-Encoding framing, exclusion-count determinism under duplicated inputs, and curation supersession cycles hidden by an independent head.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/23
- **Merged main commit:** `3c80d12` (squash merge)
- **Known limitations:** Production enables no operative pattern and the repository holds no human-record store, so ETF official events remain UNVERIFIED in production. Four human PDF verification records (one verifier) and the curated IBIT fund link exist only outside the repository; they are not used by tests or production. The IBIT identity receipt time rests on mutable filesystem metadata, and ticker and CIK are curated values the engine does not cross-check. Close-delimited HTTP bodies are accepted; FR correction metadata is caller-supplied; live endpoints were not exercised. News evidence has no trading authority.

## V1-C14 — Bedrock Provider & Structured Intelligence

- **Status:** MERGED — 2026-10-29 (code delivered and independently audited; live AWS verification pending)
- **Scope delivered:** Provider-neutral `AIProvider` contract and an Amazon Bedrock adapter (Nova Pro via Converse with a forced `submit_interpretation` tool; boto3 imported lazily and only in `bedrock.py`, pinned at 1.43.121). Deterministic evidence selection for a C10-anchored BTC market-state task and a C12-anchored macro-context task (ETF context only), admitted on provenance receipt times. Strict local validation of the model output: schema, references, section and task scope, prohibited trade language and a whole-token statement grammar (numbers only as declared copies of cited displays; whole-statement unit checks). 65 s monotonic deadline with atomic finalization, no SDK retries, exclusive 0600 record persistence with credential scanning, and outcomes `VALID` / `AI_INVALID` / `AI_UNAVAILABLE` / `AI_NOT_REQUESTED`; only a validated, recorded `VALID` interpretation is released.
- **Verification:** 1,927 tests passed locally (2 existing dependency warnings), including 373 C14 tests (98 unit-validation tests); independent Codex audit **PASS**; GitHub push and pull-request CI on the PR head `a7dfadb` and push CI on the merged main commit passed (1,927 passed, secret scan passed). All tests are offline.
- **Review history:** Codex found and verified fixes for deadline finalization races, evidence received after the evaluation time, future-dependent FOMC metadata, silent claim truncation, out-of-scope ETF references in the macro task, and wrong units in numeric statements (separated or displaced units, BTC/bitcoin used as a unit, and asset denomination wording).
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/25
- **Merged main commit:** `89c8ccd` (squash merge of `a7dfadb`; identical tree)
- **Known limitations:** No live Bedrock call has been made: model, region, inference profile, throttling, token and cost behavior are unverified, and unknowns U1–U14 remain open. Retries stay disabled until U-R1/U-R2 are verified. The statement grammar is lexical and deliberately conservative: some legitimate wording (prose unit words, payroll values with a unit, BTC/bitcoin outside an opening descriptor, or beside unit-attribution words) is rejected as `AI_INVALID`. No AI outcome has trading authority; production configuration, credentials and IAM are out of scope.
