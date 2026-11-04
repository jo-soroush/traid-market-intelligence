# TraID — Completed Card History

This file records completed and merged V1 Cards. Add one short entry **after** each Card is merged. GitHub PRs, commits and CI remain the authoritative evidence; do not duplicate full audit reports here.

## V1-C01 — Repository Baseline & Engineering Harness

- **Status:** MERGED — 2026-09-11 (entry added retrospectively; history reconciled against Git and GitHub CI)
- **Scope delivered:** Controlled repository baseline: FastAPI application with `/health`, deterministic configuration, Dockerfile, CI workflow, secret-scan script, test discovery, and the then-current engineering Harness (Card-alignment and lifecycle checks). The Harness was later removed (see C07 and PR #17).
- **Verification:** Push CI succeeded on feature commit `a304f51` and on merge commit `7460443`. Delivery verification: 25 passed, 2 warnings (recorded in `TRAID_CARD_EVIDENCE_MAP.md` at `a304f51` and `c508ab9`; a later PR #7 report separately lists 20 C01 regression tests).
- **PR:** none (integrated by a merge commit; no pull request exists for C01)
- **Merged main commit:** `7460443` (merge of `a304f51`; delivery state reconciled in `c508ab9`)
- **Known limitations:** No independent-review record is retained in the repository for this Card (NOT VERIFIED); the test result above is delivery evidence, not independent verification. The Harness it installed is no longer part of the project.

## V1-C02 — Canonical Domain Models

- **Status:** MERGED — 2026-09-14 (entry added retrospectively)
- **Scope delivered:** TraID-owned, provider-neutral typed domain models in `src/traid/domain/models.py`: source provenance, data-quality state, trades, order-book snapshots, candles, funding, open interest, liquidation events, prices, market context and the small `EvidenceReference` link, with timezone normalization and validation.
- **Verification:** Historical evidence at `400358e` reports 94 passed locally, 2 warnings (`TRAID_CARD_EVIDENCE_MAP.md`; PR #7 later reports 17 C02 regression tests). **CI on the delivery commits failed:** push CI for card commit `400358e` and for main commit `ef35af1` (2026-09-14) failed two Harness-checker tests with `FileNotFoundError` in the hosted environment (hosted CI: 92 passed, 2 failed). The next main commit, PR #1 (`c957bd4`, branch `maintenance/ci-python-portability`), passed CI; that this change was the specific fix is NOT VERIFIED.
- **PR:** none (integrated by a merge commit)
- **Merged main commit:** `f89af6d` (merge of `400358e`; delivery state reconciled in `ef35af1`). No CI run is recorded for the merge commit itself.
- **Known limitations:** Domain models are canonical contracts only; provider semantics and units are verified by later Cards. The `EvidenceReference` registry behavior was left to C15.

## V1-C03 — Exchange Adapter Contract

- **Status:** MERGED — 2026-09-16
- **Scope delivered:** Provider-neutral, capability-aware exchange adapter boundary over the C02 models: capability discovery, explicit coverage/availability/limitations, canonical output enforcement, normalized provider/internal errors, lifecycle enforcement and a deterministic fake adapter for tests.
- **Verification:** PR #2 reports 20 C03 tests and a full suite of 123 passed (2 existing dependency warnings), `CARD_QUALITY_GATE` PASS and independent audits of the boundary; PR checks and push CI on the merged commit succeeded.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/2
- **Merged main commit:** `133d064`
- **Known limitations:** No provider transport, real provider semantics or freshness in this Card; existing FastAPI/Starlette deprecation warnings.

## V1-C04 — Hyperliquid Provider Verification & Adapter

- **Status:** MERGED — 2026-09-17
- **Scope delivered:** Public read-only Hyperliquid BTC market-data adapter behind the C03 boundary: bounded REST mappings (trades, order book, candles, funding, market context), bounded WebSocket subscriptions with reconnect/resubscription and retry exhaustion, normalized errors and provenance. No trading, account mutation or credentials.
- **Verification:** PR #6 reports 165 passed (2 existing dependency warnings) and `CARD_QUALITY_GATE` PASS; PR checks and push CI on the merged commit succeeded.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/6
- **Merged main commit:** `50165e3`
- **Known limitations:** Open interest remained unavailable/unverified (deferred as D-OI-001). Live-provider behavior beyond the bounded tests is NOT VERIFIED here.

## V1-C05 — Data Quality, Freshness & Provenance

- **Status:** MERGED — 2026-09-17
- **Scope delivered:** Versioned `QualityPolicy` and deterministic `QualityAssessment` (LIVE, DELAYED, STALE, UNAVAILABLE) that keep source and receipt timestamps distinct and expose provenance quality, coverage, continuity, recovery, reasons and `trusted_for_current_use`.
- **Verification:** PR #7 reports 46 C05 tests and a full suite of 211 passed (2 existing dependency warnings), `CARD_QUALITY_GATE` PASS; PR checks and push CI on the merged commit succeeded.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/7
- **Merged main commit:** `efc8ef6`
- **Known limitations:** Open interest stays unavailable (D-OI-001); no replay or backfill in this Card.

## V1-C06 — Historical Data & Replay Foundation

- **Status:** MERGED — 2026-10-11 (post-merge fixture and policy maintenance followed in PRs #11 and #12)
- **Scope delivered:** Versioned canonical BTC historical datasets (1h candles and funding), a bounded Hyperliquid public history provider, integrity-checked storage and deterministic replay primitives with explicit coverage, gaps, provenance and modeled availability. The bounded acceptance window (2026-10-01 to 2026-10-08 UTC) produced 168 candles, 168 funding snapshots and 336 replay events; datasets stay outside Git.
- **Verification:** PR #10 reports 52 C06 tests and a full suite of 328 passed (2 existing dependency warnings), an independent bounded re-audit of **PASS_WITH_GAPS** and `CARD_QUALITY_GATE` PASS; PR checks and push CI on the merged commit succeeded.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/10
- **Merged main commit:** `1c40b3a`
- **Known limitations:** Availability uses explicit 60-second inferred policy offsets; provider publication latency, historical revisions, funding cadence and data redistribution permission are NOT VERIFIED. C06 accepts negative funding values that the C04 converter rejects. Explicit close-minus-1ms boundary assertions were missing (accepted as minor at delivery).

## V1-C07 — Order Book & Liquidity Analytics

- **Status:** MERGED — 2026-10-15
- **Scope delivered:** Deterministic order-book and liquidity analytics over trusted canonical snapshots: best bid/ask, mid, spread, cumulative band depth, imbalance, concentration, ring density and hypothetical displayed-depth VWAP/slippage, with C05 quality re-assessed at an explicit evaluation time and unavailable reasons preserved.
- **Verification:** PR #15 reports 70 C07 tests and a full suite of 507 passed (2 existing dependency warnings), an independent re-audit recorded as **PASS** (by Claude Code, per the PR) and `CARD_QUALITY_GATE` PASS; PR checks succeeded. **Post-merge push CI on `b86a265` failed** at the legacy `harness_consistency_check.py` step (`GIT_BRANCH_STATE_MISMATCH`, `V1-C07:AUDITED_CANDIDATE_BRANCH_MISMATCH`); the test step was not the failing step. The Harness was removed in PR #17 (`1df2f8f`), after which CI on `main` passed.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/15
- **Merged main commit:** `b86a265` (squash merge)
- **Known limitations:** Units are caller-asserted, not provider-verified (`UNITS_CALLER_ASSERTED_NOT_PROVIDER_VERIFIED`); the disclosure is report-level. Very large accepted books can take tens of seconds (capped at 100,000 levels, 8 bands, 16 orders, no latency SLA). Some bounds tests import constants rather than pinning literals.

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

- **Status:** MERGED — 2026-10-29 (code delivered and independently audited offline; the narrative validation was later replaced by PR #27, see the F6 entry below; documentation PR #26, `173d38d`, recorded this entry originally)
- **Scope delivered:** Provider-neutral `AIProvider` contract and an Amazon Bedrock adapter (Nova Pro via Converse with a forced `submit_interpretation` tool; boto3 imported lazily and only in `bedrock.py`, pinned at 1.43.121). Deterministic evidence selection for a C10-anchored BTC market-state task and a C12-anchored macro-context task (ETF context only), admitted on provenance receipt times. Strict local validation of the model output: schema, references, section and task scope, a prohibited-trade-word list (subsequently replaced by the F6 remediation below) and a whole-token statement grammar (`grammar.py`, which remains present; numbers only as declared copies of cited displays; whole-statement unit checks). 65 s monotonic deadline with atomic finalization, no SDK retries, exclusive 0600 record persistence with credential scanning, and outcomes `VALID` / `AI_INVALID` / `AI_UNAVAILABLE` / `AI_NOT_REQUESTED`; only a validated, recorded `VALID` interpretation is released.
- **Verification:** 1,927 tests passed locally (2 existing dependency warnings), including 373 C14 tests (98 unit-validation tests); independent Codex audit **PASS**; GitHub push and pull-request CI on the PR head `a7dfadb` and push CI on the merged main commit passed (1,927 passed, secret scan passed). All tests are offline.
- **Review history:** Codex found and verified fixes for deadline finalization races, evidence received after the evaluation time, future-dependent FOMC metadata, silent claim truncation, out-of-scope ETF references in the macro task, and wrong units in numeric statements (separated or displaced units, BTC/bitcoin used as a unit, and asset denomination wording).
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/25
- **Merged main commit:** `89c8ccd` (squash merge of `a7dfadb`; identical tree)
- **Known limitations:** At delivery (PR #25) no live Bedrock call had been made (see the live status in the F6 entry below): model, region, inference profile, throttling, token and cost behavior are unverified, and unknowns U1–U14 remain open. Retries stay disabled until U-R1/U-R2 are verified. (Historical; the prohibited-trade-word list was replaced by PR #27, while the whole-token statement grammar remains present:) The validation was lexical and deliberately conservative: some legitimate wording (prose unit words, payroll values with a unit, BTC/bitcoin outside an opening descriptor, or beside unit-attribution words) is rejected as `AI_INVALID`. No AI outcome has trading authority; production configuration, credentials and IAM are out of scope.

## V1-C14 (post-merge) — F6 Narrative-Validation Remediation

- **Status:** MERGED — 2026-11-03
- **Trigger:** An owner-reported first live Nova Pro smoke test (see Live Bedrock status) was rejected as `AI_INVALID` for ordinary market wording, and review showed the original word list also accepted instructions it did not name.
- **Scope delivered:** The forbidden-word screen was replaced by default-deny, evidence-bound validation of every model-written statement: each clause must match an approved construction (states, classification, funding payer, side pressure, the exact observed-direction bullish/bearish form, availability and category status, claim/fact/anchor statements, numbers) bound to eligible cited evidence of the right subject, state, category and source. C13 claim/fact ownership is enforced, source and category suffixes may name only the supporting evidence, and numeric statements bind metric words, units and the hourly-funding interval to the value's own source. Prompt `c14-prompt-5` and narrative policy `c14-narrative-policy-5` (the policy version is part of the prompt digest). G1–G5 and the C14 schema are unchanged.
- **Verification:** 2,261 tests passed locally (2 existing dependency warnings); both PR #27 CI checks succeeded, as did push CI on the merged commit; the independent Codex release gate PASS is recorded in the PR #27 description. All tests are offline.
- **PR:** https://github.com/jo-soroush/traid-market-intelligence/pull/27
- **Merged main commit:** `9038c6d` (squash merge)
- **Live Bedrock status:** One real Nova Pro request was executed earlier (owner-reported; the persisted record is not retained in the repository). The AWS call succeeded technically and the model returned exactly one `submit_interpretation` call, but the validator delivered by PR #25 returned `AI_INVALID` (first reason `PROHIBITED_TRADE_LANGUAGE` for `buy-dominant`; an offline probe also found `TOKEN_INVALID` for `C10`), so no interpretation was released. **No live request has been made with prompt version 5 / policy version 5: live compatibility and a live `VALID` result are NOT VERIFIED.**
- **Known limitations:** Free prose, periods or timestamps beside values, and category-word source suffixes are no longer accepted; statements must use the prompt's constructions. Whether the model follows the stricter prompt is unmeasured. Model, region, throttling, token and cost behavior remain unverified.
