# TraID V1-C15 Phase 1 — Approved Design Contract (v3.8: methodology identity)

**Version identifier:** `C15-P1-CONTRACT-v3.8` (owner-approved design promotion: 2026-11-25)
**v3.8 status: OWNER-APPROVED DESIGN / INDEPENDENT AUDIT FINAL_VERDICT: PASS (reported by the owner).** The owner approved this corrected design after B1–B3 resolution and N1–N3 correction verification; N4–N8 remain nonblocking, disclosed future considerations. This official copy promotes the approved proposal without changing its technical requirements, projections, fixtures or deferred gates. v3.8 supersedes v3.6 as the Phase 1 design baseline; the historical v3.6 contract and original proposal remain unchanged. This is an agent-audit result, not a GitHub-native review. C15 remains OPEN and Phase 1 partial. Contract approval does not authorize implementation: Slice 6 requires separate explicit owner authorization. Slice 7, C16 and Phase 2 are not authorized. No mapping, C13 routing, relation, adapter, runtime equivalence or assessment functionality is activated. Codex authored the remediation and does not claim independent approval of its own changes.

**Promotion metadata precedence:** Carried-over PROPOSED labels describe the design as drafted; its approved requirements are normative in this official copy. Historical amendment records and drafting disclosures are preserved as history, not current approval status. The §25.17 checklist is retained as the pre-approval record, not an authorization checklist newly completed by this promotion. All unresolved [O]/[U] items, illustrative/unapproved mappings and explicit future activation gates remain unresolved or inactive. No owner option or source-mapping decision is silently selected.
**Historical v3.7 drafting note (that draft subsequently received an independent FAIL; retained as history, not current approval):** this file is a complete copy of `TRAID_C15_PHASE1_CONTRACT_v3_6.md` with one amendment added as §25 and a change table in §26. §25 covers methodology identity only: the closed seven-field `Methodology` model, `methodology_id`, their validation and serialization rules, and the methodology-equivalence safeguards that future comparison rules must obey. It also covers the requirements for future source mappings, with an **EMPTY** mapping registry, and golden vectors. Pointer sentences are appended to these inherited lines, and no other inherited text is edited:
- the §3.2 L6 row and the §3.2 `methodology_id` line;
- the §3.4 reason-code bullet;
- the §5.3 columns line;
- two §7 bullets;
- the §12 preamble.

`TRAID_C15_PHASE1_CONTRACT_v3_6.md` is **not modified**. This owner-approved v3.8 design is the successor baseline referenced by Spec §7; implementation still requires separate explicit owner authorization.

Drafting this file does **not**:
- authorize any implementation;
- activate any deferred component;
- approve or activate any source mapping;
- select any new relation label.

C15 stays OPEN and C16 is not authorized. The v3.6 note below describes v3.6 and is kept unchanged as history.
**v3.6 note (OWNER-APPROVED, BOUNDED; INDEPENDENT AUDIT FINAL_VERDICT: PASS):** this file is a complete copy of `TRAID_C15_PHASE1_CONTRACT_v3_5.md` with one amendment added as §23 (`observation_id` only: a typed, keyword-only composition of the existing public identity functions, its validation policy and six golden vectors) and a change table in §24. One line in §3.2 (the `observation_id` derived-identifier line) gains a pointer to §23. Every other clause is unchanged, including all of §19 and §21. `TRAID_C15_PHASE1_CONTRACT_v3_5.md` is **not modified**. The owner approved the bounded v3.6 §23 design on 2026-11-15, and the Spec §7 pointer was updated from v3.5 to v3.6 in the activation change. The approval is bounded to the items in §23.13 and is binding for those items only. **§23 supersedes the `observation_id` restrictions in §19.9, §21.1, §21.10 and §21.11 for `observation_id` only and only at the contract level.** Every other item those sections prohibit or defer stays prohibited or deferred. **The approval does not authorize implementation.** Implementing `observation_id` needs a separate owner authorization. C15 stays OPEN and C16 is not authorized. The proposal file `TRAID_C15_PHASE1_CONTRACT_v3_6_PROPOSED.md` is kept unchanged as history. The v3.5 note below describes v3.5 and is kept unchanged as history.
**v3.5 note (OWNER-APPROVED, BOUNDED; INDEPENDENT DESIGN AUDIT PASSED WITH CONDITIONS, EDITORIAL CORRECTIONS APPLIED):** this file is a complete copy of `TRAID_C15_PHASE1_CONTRACT_v3_4.md` with one amendment added as §21 (L5 input identity: `Delivery`, `InputSetRef`, `input_set_id`) and a change table in §22. One table row in §3.2 (L5) gains a pointer to §21. Every other clause is unchanged, including all of §19. `TRAID_C15_PHASE1_CONTRACT_v3_4.md` is **not modified**. The owner approved the bounded v3.5 L5 identity design on 2026-11-13, and the Spec §7 pointer was updated from v3.4 to v3.5 in the activation change. The approval is bounded to the items in §21.1 and §21.12 and is binding for those items only. The proposal file `TRAID_C15_PHASE1_CONTRACT_v3_5_PROPOSED.md` is kept unchanged as history. The v3.4 note below describes v3.4 and is kept unchanged as history. The amendment covers `input_set_id` only; `observation_id` is deferred. It authorizes no implementation; implementing it needs a separate owner authorization. C15 stays OPEN and C16 is not authorized.
**v3.4 note (OWNER-APPROVED, BOUNDED; INDEPENDENT DESIGN AUDIT PASSED):** this file is a complete copy of `TRAID_C15_PHASE1_CONTRACT_v3_3.md` with the Slice 3 identity amendment added as §19 and a change table in §20. Three table rows in §3.2 (L1, L2, L4) gain a pointer to §19. Every other clause is unchanged. v3.3 is **not modified** and remains the governing contract, and is historical. The Spec §7 pointer now names this file. The owner approved this file after independent audit. The approval covers only the reduced Slice 3 identity contract of §19.1 (the six-field `SeriesKey` with its dotted-token mapping, the four tagged `Slot` forms, canonically sorted unique `MetricObservation` tuples, string-value projection of `Basis` and `MetricState`, the exact projections of `series_id`, `slot_id` and `exposed_content_id`, and the seven golden vectors and two `ID_JSON` fixtures). Everything else stays deferred, as §19.9 and §19.11 state. This file is derived from the audited `TRAID_C15_PHASE1_CONTRACT_v3_4_PROPOSED.md`, which is retained unchanged for audit history; the two differ only in approval and status metadata. The amendment covers `series_id`, `slot_id` and `exposed_content_id` only. It does not remove the ETF or FOMC rows from the C15 contract, and it authorizes no implementation; implementation needs a separate owner authorization (§19.9). C15 stays OPEN and C16 is not authorized.
**v3.3 note (owner-approved documentation erratum):** this file is a complete copy of `TRAID_C15_PHASE1_CONTRACT_v3_2.md` with exactly two corrections: **C-1** (§5.2 step 6 and §10: `ELIGIBLE` removed from the role-precedence chain; `EvidenceRole` keeps exactly five members) and **C-2** (§9 and AT-PRIV-2: the blanket `support`/`contradict` name prohibition is replaced by a precise rule with named exemptions). It changes no behavior of the Slice 1 serializer or of the Slice 2 leaf models, which already conform. `TRAID_C15_PHASE1_CONTRACT_v3_2.md` is historical and is **not modified**; where v3.3 and v3.2 differ, v3.3 governs. The changes are listed in §18. Nothing here authorizes any further slice or C16.
**Derived from:** `TRAID_C15_PHASE1_CONTRACT_v3_1.md` (v3.1, independently audited, merged in PR #30 at `ed8951f`). That file is **not modified**. Where v3.2 and v3.1 differ, v3.2 governs, and only §4 (serialization), §12 (the AT-SER rows) and the new §17 differ. Every other clause is carried over unchanged.
**v3.2 scope (owner decision):** replace open-ended hardening of arbitrary Python subclasses with a **bounded deterministic type policy** for `ID_ENC`, after three independently reproduced blockers in the Slice 1 serializer: F1 (an `Enum` whose `value` is overridden makes distinct members encode identically), F2 (an `Unordered` subclass hides its stored contents) and F3 (a stateful custom `tzinfo` yields a different identity on every call). The policy is §4.2b. This is a contract change limited to Slice 1 identity serialization. It does not authorize Slice 2.
**Historical sections:** §1 (baseline), §14 (verdict), §15 (audit handoff) and §16 (v3.0→v3.1 changes) are v3.1 text and describe v3.1, not v3.2. The v3.2 changes are listed in §17.
**Supersedes:** `TRAID_C15_PHASE1_CONTRACT_v3_AFTER_AUDIT_FAIL.md` (v3.0) and `TRAID_C15_PHASE1_CONTRACT_FOR_CODEX.md` (v2). Both are left untouched and are NOT the contract. Where they differ from v3.1, v3.1 governs.
**v3.1 scope:** a bounded remediation of exactly two blocking defects reproduced by Codex's v3 audit (R4 methodology mismatch; Enum type collisions) plus one clarification (ETF mapping versus source reports). Every changed clause is listed in §16. All other clauses are carried unchanged from v3.0. The two reproduced defects are described here from the task statement; I do not hold Codex's audit text.
**Baseline:** `main` at `c08bd61` (verified: `HEAD` = `c08bd61`; the only untracked file before this task was the v2 contract).
**Status:** proposed contract change, **not independently audited**. Written by the implementer (Claude Code); it is not a self-approval. The Slice 1 code that implements it is a separate, uncommitted working-tree change.
**Author role:** Claude Code (design). **Reviewer role:** Codex (independent). Nothing here is a self-approval.

Labels: **[F]** verified repository fact, with file reference. **[P]** proposed rule. **[O]** owner decision not yet granted.

**Disclosure about the audit input.** I do not have Codex's FAIL audit text. The task names B1, B2, B3 and "the three C09 candle counterexamples supplied by Codex", but the counterexamples themselves were not in my context. In §3.6 and §12 I reconstruct three counterexamples **from the B1 requirement list**. They are my reconstruction. Codex must confirm or replace them. Every fixture is parameterized on exposed fields, so a replaced counterexample changes data, not rules.

---

## 1. VERIFIED_BASELINE

Read in this task (full lines inspected):

- **[F]** `src/traid/derivatives/analytics.py:138-148` — `InputProvenance`: `source`, `source_types`, `contributing_count`, `earliest_time`, `latest_time`, `newest_record_provenance`, `input_digest`, `digest_algorithm`.
- **[F]** `derivatives/analytics.py:155-181,184-203` — `_Section` carries `latest_start`, `retained_count`, `bars_behind`, `trusted_for_current_use`, `reasons`. `CandleIndicators` has `atr`, `realized_volatility`, `vwap`, `vwap_session_volume`, `momentum`. `FundingContext` has `latest_rate`, `cumulative_funding`, `mean_hourly_funding`, `lookback_hours`.
- **[F]** `derivatives/analytics.py:297-305` — `_provenance`: `input_digest = sha256(json.dumps(rows))` over the canonical row lists. `derivatives/analytics.py:~424` — candle rows include `source`, `source_type`, `source_id`, `source_timestamp`, `received_timestamp` plus OHLCV. So **the digest covers receipt and transport fields**.
- **[F]** `derivatives/analytics.py:315-355` — `_provenance_order`/`_dedupe`: "source_id is provider record metadata, not part of a candle's or funding hour's identity: observations that agree on content but differ in source_id (or transport/receipt time) are one observation". C09 itself treats receipt-only differences as the same observation, while the digest differs.
- **[F]** `derivatives/analytics.py:~411-423` — metrics are withheld (`value=None`, `reason`) when quality is untrusted. A withheld metric is **absent**, not zero.
- **[F]** `ai/selection.py:71-80,82-96,118-119,135-136,892-941,952-985` — `EvidenceInputs`, `RequestContext`, `canonical_json`, `report_sha256`, `select(task, evaluation_time, inputs)`, `_context`. `select` "never mutates the reports" and returns `Selection(request, request_sha256, bindings, context, excluded, skip)`.
- **[F]** `ai/validation.py:93-122,125-156,158-197,200-232` — `validate_reply`, `_kind`, `_check_refs`, `_sections`, `_cited`, `check_output`. `check_output` rejects, per section: unknown refs (`UNKNOWN_REFERENCE`), claims cited as facts in summary and anchor assessments (`CLAIM_CITED_AS_FACT`), unknown anchors, unknown `NumberRef.value_id`, incomplete anchor or claim coverage.
- **[F]** `ai/validation.py:874-938` — `adapt(output, ctx, analysis_timestamp)` is a pure projection. `evidence` is derived from every section's cited refs plus anchor evidence ids plus claim-note claim ids. `source_references` and `annotations` are derived from `ctx`. `supporting_factors` and `contradicting_factors` come from the **model's own anchor stances**.
- **[F]** `ai/models.py:418-441,472-488` — `ReportDigest`, `HandleSource`, `PrivateBindings` ("Owner-only replay bindings"), `AIAnalysisRecord`, `AIResult` (an interpretation is released only for committed VALID).
- **[F]** `tests/test_ai_validation.py:109-112` — `E999` in `summary.refs` returns `UNKNOWN_REFERENCE`. `tests/test_ai_validation.py:270` — `E999.V1` as a `NumberRef.value_id` returns `UNKNOWN_REFERENCE`.
- **[F]** `whales/models.py:29,48-61`, `macro/models.py:39,51-68`, `regime/engine.py:180-190` — repository canonical converters. Decimals are normalized with `Decimal.normalize(Context(prec=8192, ...))`. **This rounds any Decimal above 8,192 significant digits**, and `format(Decimal("-0").normalize(ctx), "f")` is `"-0"`. They differ on dates: `whales` and `regime` do not handle `date`; `macro` uses `isoformat()`. `datetime` is emitted via `isoformat()` **without UTC normalization** in `whales` and `regime`.
- **[F]** Report classes: `FlowReport` (`flow/analytics.py:128`), `DerivativesReport` (`derivatives/analytics.py:205`), `LiquidityReport` (`liquidity/analytics.py:132`), `MarketStateReport` (`regime/engine.py:422`), `WhaleReport` (`whales/analytics.py:399`), `MacroEvidenceReport` (`macro/evidence.py:185`), `EtfEvidenceReport` (`macro/etf.py:285`), `VerificationReport` (`news/models.py:771`).
- **[F]** Canonical documents: `TRAID_CARD_SPECIFICATIONS.md` C15 section: scope lists "supporting and contradicting roles" and "deterministic alignment/strength only where explicitly defined"; Exit Gate "support, contradiction, missing/stale evidence, and coverage gaps ... remain visible". `TRAID_V1_ROADMAP.md:417-428`.

Facts carried from earlier sessions (read before the context reset; **re-verify at implementation start**): `news/models.py:81-82,333-356` (`text_digest`, `claim_id_for`), `news/engine.py:478-501` (`VerificationResult.input_digest` composition), `news/macro_adapter.py:89-224` (`series[...]`, `fomc...` paths), `macro/evidence.py:650-665` (report-level `input_digest`), `regime/engine.py:263-282,475-486,618-623` (`SourceRef`, book reference digest `None`), `flow/analytics.py:114-125,188-204,240` (`FlowProvenance`, receipt filter), `liquidity/analytics.py:132-147` (no raw levels).

Not verified in this task: that `traid.ai.selection.select` is deterministic across repeated calls and free of I/O, clock, network and AWS access. The whole file was not read. **This is an implementation-start gate (AT-AI-0).**

---

## 2. B1_B2_B3_RESOLUTION_MATRIX

| Finding | Defect in v2 | v3 resolution | Section |
|---|---|---|---|
| **B1** | One `content_fingerprint` mixed coordinates, coverage and receipt metadata. "EF equal and comparison values absent" was treated as safe. Absent values were implicitly EQUAL. Candle price changes were invisible. | Coverage is a separate field. Economic metrics are separate typed observations with a window id. A three-valued comparison (`EQUAL`/`DIFFERENT`/`UNKNOWN`) is applied only under equal methodology and equal window. Absent means `UNKNOWN`. Receipt and coverage differences are informational flags, never conflicts. Four relation families are kept separate. | 3, 5, 6 |
| **B2** | `ID_JSON` rounded above 8,192 digits, collapsed nothing about `-0`, had no `date` rule, did not normalize timezones, and decoded enums non-recursively. | Typed, tagged, exact encoding (`ID_ENC`). No Decimal context. Signed zero collapses to `0` by explicit rule. UTC-normalized datetimes. `date` distinct. Exact timedelta. Recursive enum. Ordered `seq` versus sorted `bag`/`set`. Explicit rejection set. | 4 |
| **B3** | V1–V10 checked a canonical evidence list and a few fields; it did not replay validation, so a forged `E999` in an output section could pass. | Replay: C15 re-runs `select`, compares request, digest, private bindings and excluded items, then re-runs `check_output` and `adapt` on the original output and requires full equality with the record's interpretation. Any failure withholds the commentary. | 8 |
| C13 | Optional `news_claims` changed identity. A non-null `source_id` was treated as revision evidence. | `news_claims` removed from Phase 1. Identity depends only on the report. No revision is inferred. | 7 |
| Lineage | Equal EF was used as a lineage token. | Equal coordinates are a `COORDINATE_ASSOCIATION` only. Lineage edges require a verified shared digest, a verified derivation digest, or a resolved citation. | 6 |
| Exit Gate | — | Phase 1 stays partial, C15 stays OPEN, C16 is not authorized. Required owner approvals are listed before implementation. | 10, 13 |

---

## 3. FINAL_IDENTITY_AND_COVERAGE_CONTRACT

### 3.1 Principles [P]

1. **Coordinates, coverage, economic metrics, input-set reference and assessment are five different things.** None may stand in for another.
2. A source digest identifies **an input set as delivered**, including receipt and transport fields. A different digest never proves different economic content. An equal digest never proves a correct assessment.
3. Absence of a comparison value is `UNKNOWN`, never `EQUAL`, never `DIFFERENT`.
4. A difference in coverage alone is never an economic contradiction.
5. Every variant is preserved. No winner is ever selected. Retention is not endorsement.
6. C15 invents no identity the source does not expose. Where raw content is not exposed, C15 says so (`raw_identity`) and never claims raw equality.
7. **Matching timestamps and counts never imply raw candle equality.**

### 3.2 Layers [P]

All hashes use `HID(tag, value) = sha256(ID_JSON({"tag": tag, "v": ID_ENC(value)}))` from §4.

| Layer | Field | Content | Receipt-sensitive? | Hashed into |
|---|---|---|---|---|
| L1 | `series_key` | what is observed, without time slot: `{kind, symbol, interval, source, section}` **[v3.4: six-field `SeriesKey`, see §19.2]** | no | `series_id` |
| L2 | `slot` | one observation slot of the series: `series_key` plus `slot_time` (C09: `latest_start`; C07: `snapshot_timestamp`; C08: `(window_start, session_start)`) **[v3.4: four tagged slot forms, see §19.3]** | no | `slot_id` |
| L3 | `coverage` | history actually behind the slot: `{earliest_time, latest_time, contributing_count, interval}` where exposed | no | `coverage_id` |
| L4 | `metrics` | tuple of `MetricObservation` (below). Source-exposed material economic metrics **[v3.4: ascending, unique, see §19.4]** | no | `metrics_id` |
| L5 | `input_set_ref` | `{digest: [algorithm, sha256] or null, delivery: {source_type, source_id, received_timestamp, ...}}` **[v3.5: closed `InputSetRef`, see §21]** | **yes** | `input_set_id` |
| L6 | `methodology` | `MI`: engine and schema version, source-exposed config, rule/mapping digests, quality-policy version, hidden-input codes **[v3.7 PROPOSED: closed seven-field `Methodology`, see §25.3]** | no | `methodology_id` |
| L7 | `assessment_content` (`AC`) | every other exposed field (states, reasons, quality verdicts, limitations) | no | `ac_id` |

Derived identifiers [P]:

- `series_id = "sr1:" + HID("c15.series.v1", series_key)` — **association only**.
- `slot_id = "sl1:" + HID("c15.slot.v1", slot)`.
- `exposed_content_id = "xc1:" + HID("c15.xc.v1", {"slot": slot_id, "coverage": coverage, "metrics": metrics, "basis": basis})` — everything economic that is exposed, **excluding L5**. Equal value means equal exposed projection only.
- `input_set_id = "is1:" + HID("c15.is.v1", input_set_ref)`.
- `observation_id = "ob1:" + HID("c15.ob.v1", {"slot": slot_id, "xc": exposed_content_id, "is": input_set_id})` — one delivered observation (one delivered input set projected to one slot). **[v3.6: typed composition API, see §23]**
- `methodology_id = "mt1:" + HID("c15.mt.v1", MI)`. **[v3.7 PROPOSED: explicit projection, API and structural-equality limits, see §25.6 and §25.7]**
- `assessment_id = "as1:" + HID("c15.as.v1", {"ob": observation_id, "mt": methodology_id, "t": T, "ac": ac_id})`.

`basis ∈ {SOURCE_INPUT_DIGEST, EXPOSED_FIELDS, NO_OBSERVATION}`.
`raw_identity ∈ {VERIFIED_BY_SOURCE_DIGEST, EXPOSED_CONTENT_COMPLETE, EXPOSED_CONTENT_PARTIAL}`.

The v2 names `economic_fingerprint` (EF) and `content_fingerprint` are **removed**. Their role is split: `series_id` and `slot_id` (association), `exposed_content_id` (exposed projection) and `input_set_id` (delivery).

### 3.3 MetricObservation [P]

```
MetricObservation:
  name: str                        # e.g. "atr", "latest_rate", "mid"
  state: PRESENT | WITHHELD | NOT_AVAILABLE
  value: Decimal | None            # None unless PRESENT
  unit: str
  window_id: str | None            # see below; None means "no verified window rule"
  reason: str | None               # source reason when not PRESENT
```

- `PRESENT` only when the source metric has `value is not None`. A source metric with `value=None` is `WITHHELD` (quality) or `NOT_AVAILABLE` (source says unavailable). Neither is a number.
- `window_id` is defined **only** for metric classes whose window rule C15 has verified against the source formula at implementation start. Otherwise `None`, and the comparison is `UNKNOWN`.
- Proposed window rules (each requires a read of the corresponding `_candle_section`/`_funding_section` code before it is enabled; **not verified in this task**):
  - `atr`: `("atr", atr_period, slot_time)`. A `PRESENT` ATR implies the last `atr_period+1` bars were one consecutive hourly run (`_tail`, `derivatives/analytics.py:360`).
  - `realized_volatility`, `momentum[k]`: analogous, from config and `slot_time`.
  - `vwap`, `vwap_session_volume`: `("vwap", session_start, slot_time)` and comparable **only** if both reports expose `coverage.earliest_time <= session_start`; otherwise `None`.
  - `latest_rate`: `("latest_rate", slot_time)`.
  - `cumulative_funding`, `mean_hourly_funding`: `None` in Phase 1 (comparison `UNKNOWN`), because the dependence on coverage has not been verified.

### 3.4 Three-valued metric comparison [P]

```
cmp(a, b) ->
  UNKNOWN  if methodology_id differs
  UNKNOWN  if a.name != b.name or a.unit != b.unit
  UNKNOWN  if a.state != PRESENT or b.state != PRESENT
  UNKNOWN  if a.window_id is None or b.window_id is None or a.window_id != b.window_id
  EQUAL    if ID_ENC(a.value) == ID_ENC(b.value)          # exact Decimal equality, §4
  DIFFERENT otherwise
```

Summaries over a pair of observations:

- `compared`: metric names with a verdict other than `UNKNOWN`.
- `uncompared`: metric names whose verdict is `UNKNOWN`, each with a reason code: `METHODOLOGY_DIFFERS`, `NOT_PRESENT`, `WINDOW_NOT_VERIFIED`, `WINDOW_DIFFERS`, `UNIT_DIFFERS`. **[v3.7 PROPOSED: §25.12.1 amends the first `cmp` line and narrows `METHODOLOGY_DIFFERS`. It also adds `METHODOLOGY_NOT_ESTABLISHED`.]**
- `any_different`, `all_compared_equal`, `none_compared`.

A report exposing **no metrics at all** (for example C09 open interest and basis, always unavailable at `derivatives/analytics.py`) has `basis = NO_OBSERVATION`. It cannot be compared and never forms a relation.

### 3.5 Coverage relation [P]

Computed from `coverage` only. It is **informational** and never changes eligibility by itself.

`SAME` (all four fields equal), `NESTED` (one `[earliest, latest]` interval contains the other, same `latest_time`), `OVERLAPPING`, `DISJOINT`, `UNKNOWN` (a field missing).
Contributing counts are shown, never used to infer equality of records.

### 3.6 Regression fixtures for the three C09 candle counterexamples [P]

These three are my reconstruction from the B1 requirement list (see disclosure). Each fixture is two `DerivativesReport` candle sections at one T, one slot (`latest_start` equal), structurally equal methodology (`config` equal), `symbol` and `source` equal. The Expected column is conditional on `ESTABLISHED_EQUAL`, not on structural equality alone. With `NOT_ESTABLISHED`, every metric is `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED`; the differing-digest pairs CX-1 through CX-6 follow R8 as `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`, without a conflict or compared-metric equivalence. Receipt and coverage variants remain informational. These are contract acceptance requirements, not authorization to implement comparison.

| ID | Construction | Expected |
|---|---|---|
| **CX-1** same coordinates, different prices | `earliest_time`, `latest_time`, `contributing_count`, `latest_start` identical. Candle OHLC differ in the last `atr_period+1` bars, so `atr` differs. `input_digest` differs. | `any_different` on `atr` ⇒ `CONFLICTING_OBSERVATION`. Both retained. Neither selected. Coverage `SAME`. |
| **CX-2** same economic content, different receipt metadata | Identical OHLCV. `received_timestamp` and/or `source_id` differ on some candles. `input_digest` differs. All metrics equal. | `EQUIVALENT_ON_COMPARED_METRICS` plus flag `RECEIPT_VARIANT`. **Not** `CONFLICTING_OBSERVATION`. Not an exact duplicate. `raw_identity=VERIFIED_BY_SOURCE_DIGEST` is **not** claimed for the pair. |
| **CX-3** compatible but different coverage | Report B holds more history than report A (`earliest_time` and `contributing_count` differ; `latest_time`, `latest_start` equal). `atr`, `realized_volatility` equal and `PRESENT`. `vwap` windows not comparable (A's `earliest_time` after `session_start`). | Compared metrics equal ⇒ `EQUIVALENT_ON_COMPARED_METRICS` plus `COVERAGE_VARIANT`. `vwap` listed as `uncompared: WINDOW_NOT_VERIFIED`. No conflict. Raw equality not claimed. |
| CX-4 (extra) genuine conflict at a comparable window | CX-3 construction but B's `atr` differs. | `CONFLICTING_OBSERVATION`; coverage difference does not mask or cause it. |
| CX-5 (extra) same timestamps and counts, withheld metrics | Both reports untrusted, all metrics `WITHHELD`, digests differ. | `UNRESOLVED_INPUT_SET_DIFFERENCE`; `none_compared`. **Never** `EQUIVALENT`. |
| CX-6 (extra) one side metrics, one side withheld | A `PRESENT`, B `WITHHELD`, digests differ. | `UNRESOLVED_INPUT_SET_DIFFERENCE`. Absent is not equal. |

Limit that must be disclosed in the output [P]: when all compared metrics are equal, price differences in candles **outside every metric window** are undetectable. The output carries `RAW_CANDLES_NOT_EXPOSED` and the relation is named "equivalent on compared metrics", never "identical".

### 3.7 Per-source slot and metric table [P]

Source classes use only fields the report models expose. Fields marked "to confirm" must be read at implementation start.

| Unit | `series_key` | `slot_time` | coverage | metrics (L4) | L5 digest | raw_identity |
|---|---|---|---|---|---|---|
| C07 book | `{LIQ.book, symbol, source}` | `snapshot_timestamp` | none | `best_bid`, `best_ask`, `mid`, `spread_absolute`, `spread_bps` (window = the snapshot instant; withheld when untrusted) | none; delivery `{source_type, source_id, received_timestamp}` | **PARTIAL** (raw levels not exposed) |
| C08 flow | `{FLOW.window, symbol, source}` | `(window_start, session_start)` | `earliest_event_time`, `latest_event_time`, `contributing_trade_count` | window and session volumes and deltas (window rule to confirm) | `FlowProvenance.input_digest` | digest-verified |
| C09 candles | `{DER.candles, symbol, "1h", source}` | `latest_start` | `earliest_time`, `latest_time`, `contributing_count` | `atr`, `realized_volatility`, `vwap`, `vwap_session_volume`, `momentum[k]` | `InputProvenance.input_digest` | digest-verified; `NO_OBSERVATION` if `provenance is None` |
| C09 funding | `{DER.funding, symbol, "1h", source}` | `latest_start` | same | `latest_rate`; others window `None` | same | same |
| C09 OI, basis | — | — | — | none | none | `NO_OBSERVATION` |
| C10 dimension | `{REGIME.dim, symbol, dimension}` | newest `SourceRef.source_timestamp` | none | none (classifier states are assessment content) | each `SourceRef.input_digest` | digest where present, else PARTIAL |
| C11 wallet | `{WHALE.wallet, wallet_ref}` | snapshot time | none | position and account value as exposed | none; delivery = snapshot provenance | COMPLETE for snapshot |
| C12 series | `{MACRO.series, series_id}` | `reference_period` | none | `known_value`, `previous_known`, revisions | none | COMPLETE |
| C12 FOMC, ETF | per v2 §4, unchanged | — | — | as exposed | none | COMPLETE |
| C13 result | `{NEWS.result}` | `claim_id` | none | none | **none** (see §7) | EXPOSED_FIELDS |
| C14 commentary | not registered as an observation | — | — | — | — | — |

---

## 4. EXACT_SERIALIZATION_CONTRACT

### 4.1 Two serializers, never mixed [P]

- **`ID_ENC` / `ID_JSON`** (this section): used **only** for C15 identities and C15's own two output digests' *identity fields*. Never used to recompute any upstream digest.
- **`REPORT_JSON`**: the C14-compatible serialization, used for source-report digests and for the `report_digest` and `deterministic_digest` of C15 outputs.
  - **[F]** `ai/selection.py:118-119,135-136`: `canonical_json(value) = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)` and `report_sha256(report) = sha256(canonical_json(report.model_dump(mode="json")))`.
  - **[P]** C15 **imports** `traid.ai.selection.canonical_json` and `report_sha256` for source-report digests. It does not reimplement them. C15's own output digests use the same `canonical_json` over `model_dump(mode="json")`.
  - Because `mode="json"` keeps Decimal spelling, a spelling change changes the C14-compatible digest. This is required: the AI binding must match C14's own digest.

### 4.2 `ID_ENC` encoding [P]

`ID_ENC(v)` maps a value to a JSON structure. Unsupported input raises `IdentityEncodingError` (never coerces).

| Python type | Encoding |
|---|---|
| `None` | `null` |
| `bool` (checked **before** `int`) | `true` / `false` |
| `str` | JSON string, exact, no normalization |
| `int` | `{"$":"int","v":"<base-10 string>"}` |
| `Decimal` | **exact `Decimal` type**; see 4.3 |
| `datetime` (checked **before** `date`) | **exact `datetime` type**; requires an aware value whose `tzinfo` is one of the accepted timezone types (§4.2b); the offset is read once with the base-class `datetime.utcoffset` and subtracted from the wall-clock fields; `{"$":"dt","v":"YYYY-MM-DDTHH:MM:SS.ffffffZ"}` always with six fractional digits |
| `date` (not `datetime`) | **exact `date` type**; `{"$":"date","v":"YYYY-MM-DD"}` |
| `timedelta` | **exact `timedelta` type**; `{"$":"td","v":"<total microseconds as base-10 string>"}`, computed as `days*86400*10**6 + seconds*10**6 + microseconds`, sign preserved |
| `Enum` (any subclass, including `StrEnum`, `IntEnum`, `IntFlag`) | `{"$":"enum","c":"<type.__module__>:<type.__qualname__>","v":ID_ENC(member.value)}`, **recursive** (the value may itself be an enum, tuple or Decimal). **Dispatched before** `bool`, `str`, `int` and every other primitive, because an Enum may subclass them. `member.value` means the stored `_value_`, and enums with nonstandard value access are rejected (§4.2b) |
| ordered sequence (**exact** `tuple`, **exact** `list`) | `{"$":"seq","v":[ID_ENC(x), ...]}` in the original order |
| **exact** `set`, **exact** `frozenset` | `{"$":"set","v":[...]}` sorted by `json.dumps` of the encoded element; duplicate encoded elements raise |
| adapter-declared unordered multiset (**exact** `Unordered(items)` wrapper) | `{"$":"bag","v":[...]}` sorted likewise, duplicates kept |
| **exact** `dict` | `{"$":"map","v":[[ID_ENC(k), ID_ENC(v)], ...]}` sorted by encoded key; keys must be `str` |
| `float`, `bytes`, `datetime.time`, NaN or infinite Decimal, naive datetime, a subclass of any exact-type row above, an unaccepted timezone, a nonstandard enum, any other type | **rejected** |

Rules:

- Every non-primitive is a tagged object, so no value of one type can collide with another type's encoding. A user dict containing the key `"$"` is still emitted as a `map` entry list, so it cannot collide with a tagged form.
- `seq` versus `bag`/`set`: **meaningful order is preserved** (price series, candle series, ordered reasons). Collections whose order is arbitrary are declared unordered by the adapter, never inferred. The adapter table (§3.7) must name each field's class; a field not classified raises at build time.
- **Pydantic models** are converted by the adapter into plain dict/seq/bag structures (not auto-dumped) so that ordering classes are explicit.
- Output string: `json.dumps(ID_ENC(v), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`.
- `datetime.time` is rejected. `macro/models.py:canonical_json` does handle `time`; **no source field needing it was found**. If an adapter meets one at implementation, stop and report; do not coerce.

### 4.2a Dispatch order and Enum type identity [P] (new in v3.1)

**Dispatch order (normative):** `None` → `Enum` → `bool` → `str` → `int` → `Decimal` → `datetime` → `date` → `timedelta` → `set`/`frozenset` → `Unordered` → `dict` → `tuple`/`list` → reject. The `Enum` test is `isinstance(v, enum.Enum)`. It precedes `str` and `int` so that a `StrEnum` or `IntEnum` member is never encoded as its bare string or integer. `datetime` precedes `date` (unchanged from v3.0).

**Enum type identity** is `module:qualname`, where `module = type(v).__module__` and `qualname = type(v).__qualname__`. Two enum classes named `State` in different modules therefore encode differently even with equal member values.

**Ambiguity validation (fail closed):**
1. A `qualname` containing `<locals>`, or a `module` equal to `__main__`, is rejected (`AmbiguousEnumTypeError`): such a name does not identify one class across runs.
2. `ID_ENC` keeps a process-local registry `{"module:qualname" → class object}`. The first class encoded under a key is registered. Encoding a **different class object** under an already-registered key raises `AmbiguousEnumTypeError`. This covers module reloads and dynamically created duplicates. It never silently merges them.
3. Enum values are encoded through `ID_ENC(member.value)` (recursively, with the same registry), so a nested enum, a tuple of enums, a `Decimal` or a `StrEnum` value is covered.
4. `Flag` composites: encoded by `member.value` (an int) with the type key above; no member-name decoding is used.

**Stability.** The encoding depends only on `module`, `qualname` and `value`, never on object ids, hash seeds, member order or import order. Moving or renaming an enum class changes identities; this is an intended, versioned break (`HID` tags carry `.v1`). The registry is process-local and holds no persistent state.

**Unchanged from v3.0:** exact Decimal normalization (4.3), signed-zero collapse, UTC-normalized datetimes, distinct `date`, exact timedelta, `seq`/`set`/`bag`/`map` handling, rejection set, and `REPORT_JSON` (C14-compatible serialization). The enum change touches only `ID_ENC`.

### 4.2b Bounded type policy [P] (new in v3.2)

**Principle.** `ID_ENC` accepts the smallest set of types that the real C07–C14 `model_dump(mode="python")` outputs and C15 adapters produce, and rejects every other type by default. A rejected value raises `IdentityEncodingError`; it is never coerced, repaired or encoded "as its base type".

**Why subclasses are rejected.** A subclass can override an accessor (`Decimal.as_tuple`, `datetime.year`), an iterator (`list.__iter__`, `dict.items`) or a conversion (`timedelta.__floordiv__`), so two different underlying values can receive one identity, or one value different identities. Hardening each accessor one by one is open-ended; an exact-type test is closed and checkable.

**Accepted types (exact, tested with `type(v) is T`):**

| Group | Accepted | Rejected |
|---|---|---|
| Primitives | `None`, `bool`, `str`, `int` | `float`, `bytes`, `complex`, `time` |
| `str`, `int` subclasses | accepted: the base value is read with `str.__str__` / `int.__int__`, which no override can reach | — |
| Numeric / temporal | exact `Decimal`, exact `datetime`, exact `date`, exact `timedelta` | any subclass of these |
| Collections | exact `list`, `tuple`, `dict`, `set`, `frozenset`, exact `Unordered` | any subclass: `namedtuple`, `OrderedDict`, `defaultdict`, `Counter`, a user `list`/`dict` subclass, a user `Unordered` subclass |
| `Enum` | any `Enum` class meeting the Enum policy below | an enum failing the policy |

`bool` is a subclass of `int` and is dispatched first; it is not an "int subclass" for this policy. Pydantic models are not accepted directly (adapters convert them, §4.2).

**Enum policy.** An enum member is accepted only if all hold:
1. No class in the enum's MRO, other than classes defined in the standard `enum` module or in `builtins`, defines the names `value` or `_value_` in its own namespace. This rejects an overridden `value` property and a member named `value`.
2. The stored value is read with `object.__getattribute__(member, "_value_")`, which bypasses `value` and any `__getattribute__` override.
3. The declared value resolves to its own member: `type(member)(stored) is member`. This holds for ordinary members, aliases (an alias is its canonical member), members built through a custom `__new__` that sets `_value_`, and `Flag` composites. It fails closed for anything else, including a lookup that raises.

Rejection code: `ID_ENUM_NONSTANDARD`. `StrEnum`, `IntEnum`, `IntFlag`, plain `Enum`, and enums whose values are enums, tuples or `Decimal` remain supported (§4.2a is unchanged).

**Timezone policy.** A `datetime` is accepted only if it is exact `datetime`, aware, and `type(tzinfo)` is exactly one of:
- `datetime.timezone` (this includes `timezone.utc` and fixed offsets);
- `zoneinfo.ZoneInfo`;
- `pydantic_core.TzInfo` (the fixed-offset type pydantic produces when it parses ISO text with an offset; verified for `Z` and `+02:00`).

Any other `tzinfo`, including a subclass of the three above and any user-defined `tzinfo`, is rejected with `ID_TZ_UNSUPPORTED`, because its offset may depend on state or on the number of calls. The offset is evaluated **once**, with the base-class `datetime.utcoffset(value)`, so a `ZoneInfo` honours `fold`: `2026-11-01T01:30` in `America/New_York` is `05:30Z` with `fold=0` and `06:30Z` with `fold=1`. A `ZoneInfo` result depends on the installed time-zone database; that dependency is disclosed in §4.2c.

**Failure codes (`IdentityEncodingError.code`):**

| Code | Raised for |
|---|---|
| `ID_TYPE_SUBCLASS_REJECTED` | a subclass of `Decimal`, `datetime`, `date`, `timedelta`, `list`, `tuple`, `dict`, `set`, `frozenset` or `Unordered` |
| `ID_TZ_UNSUPPORTED` | an aware datetime whose `tzinfo` type is not accepted |
| `ID_ENUM_NONSTANDARD` | an enum failing the Enum policy |
| `ID_ENCODING` | every other rejection (default): float, bytes, time, naive datetime, non-finite Decimal, non-`str` key, key collision, depth, unsupported type |
| (`AmbiguousEnumTypeError`) | unchanged from §4.2a: `<locals>`, `__main__`, or two classes under one key; it is a subclass of `IdentityEncodingError` |

### 4.2c Honest limits of the policy [P]
- `tzinfo` objects of the three accepted types are treated as trustworthy data. A `ZoneInfo` depends on the host time-zone database, so two hosts with different database versions could in principle disagree about a historical or future offset.
- The enum registry stays process-local (§4.2a).
- Integer size is unbounded and costs time and memory proportional to its size.
- The policy covers `ID_ENC` only. `REPORT_JSON` is unchanged.

### 4.3 Decimal encoding [P]

Exact, finite, no context, no rounding, no precision ceiling:

1. `d.is_finite()` is required, else reject.
2. `sign, digits, exp = d.as_tuple()`.
3. If every digit is `0`: emit `{"$":"dec","v":"0"}`. **Signed zero collapses to `"0"`** (explicit rule, below).
4. Otherwise strip trailing `0` digits from `digits`, adding one to `exp` for each stripped digit.
5. Emit `{"$":"dec","v":"<'-' if sign else ''><''.join(digits)>e<exp>"}`.

No `int()` or `str(int)` conversion is applied to the coefficient, so Python's integer string-conversion digit limit is not involved. No `format(..., "f")` is used, so a large exponent (`Emax` 999999) cannot produce a gigantic string.

Examples: `1.0` → `1e0`; `1.00` → `1e0`; `1E+2` → `1e2`; `100` → `1e2`; `0.00` → `0`; `-0` → `0`; `-1.50` → `-15e-1`.

**Signed-zero rule.** `Decimal("-0") == Decimal("0")` in Python, and C10's funding classifier compares by value (`rate == 0` is `ZERO`; `regime/engine.py` `_funding`). So an economic identity must not differ between `-0` and `0`. Therefore `ID_ENC` collapses them.
**Divergence disclosed:** the repository's `canonical_json` emits `"-0"` for negative zero (`format(Decimal("-0").normalize(ctx), "f")`). `ID_ENC` is C15-only and never reproduces those digests; `REPORT_JSON` keeps the repository spelling (`"-0"`). A test pins both behaviours (AT-SER-4).

**Rounding divergence disclosed.** The repository converters round above 8,192 digits (`Context(prec=8192)`). `ID_ENC` does not. Two Decimals that the repository would merge by rounding remain distinct under `ID_ENC`. This is intentional and tested (AT-SER-1).

### 4.4 Hash framing [P]

`HID(tag, value) = sha256(ID_JSON({"tag": tag, "v": ID_ENC(value)})).hexdigest()`. Tags are versioned strings (`c15.series.v1`, …). A tag change is a deliberate identity break.

---

## 5. FINAL_CONFLICT_DECISION_TABLE

### 5.1 Four relation families [P]

They are recorded separately and must not be conflated.

| Family | Meaning | May form a "lineage group"? |
|---|---|---|
| **A. Coordinate association** | Same `series_id` (and possibly `slot_id`). Says only "these observe the same thing". | **No** |
| **B. Exposed-content relation** | `EXACT_DUPLICATE`, `EQUIVALENT_ON_COMPARED_METRICS`, `EQUIVALENT_AS_EXPOSED`, `CONFLICTING_OBSERVATION`, `UNRESOLVED_INPUT_SET_DIFFERENCE`, `DIFFERENT_SLOT_SAME_SERIES` | no (content relations are not lineage) |
| **C. Shared input** | Equal `input_digest` with equal `digest_algorithm` and equal section kind. Verified identical delivered input rows. | **Yes** |
| **D. Derivation lineage** | A C10 `SourceRef.input_digest` equal to a supplied C08/C09 section digest. | **Yes** |

Informational flags that never change a relation: `RECEIPT_VARIANT`, `COVERAGE_VARIANT`, `TRANSPORT_VARIANT`, `RAW_CANDLES_NOT_EXPOSED`.

### 5.2 Algorithm [P]

Inputs: all admitted units (after §6.3 temporal exclusion). One T. Deterministic and order-independent.

1. Group by `slot_id`. Units with `basis=NO_OBSERVATION` form no relation.
2. Within a slot group, partition by `observation_id`.
3. Single partition: apply the within-partition rules (R1–R3).
4. Multiple partitions: compare every pair, apply R4a–R10a below, in the order given under "Rule ordering".
5. Across slots with equal `series_id`: record `DIFFERENT_SLOT_SAME_SERIES` as association only (family A and B). Never a conflict, never compared (windows differ ⇒ all `UNKNOWN`).
6. Eligibility is the worst-of across the unit's relations with precedence `INELIGIBLE > MISSING > STALE > UNVERIFIED > DESCRIPTIVE_ONLY`, where the roles are the inactive-only set (§10). `DESCRIPTIVE_ONLY` is the normal, inactive, descriptive role of a unit with no missing, stale, unverified or ineligible finding. It is not independent confirmation, not supporting evidence and not decision readiness. There is no `ELIGIBLE` role.

### 5.3 Decision table

Columns: **D** = `input_digest` comparison, **M** = `methodology_id`, **Cmp** = metric comparison summary (§3.4). "Same observation" means equal `observation_id`. **[v3.7 PROPOSED: M becomes the three-state methodology comparison of §25.9. §25.12.2 amends rows R3–R8 and R10, the rule ordering and §5.4.]**

| # | Condition | Relation | Eligibility effect | Notes |
|---|---|---|---|---|
| R1 | same `observation_id`, same `assessment_id`, `raw_identity ∈ {VERIFIED_BY_SOURCE_DIGEST, EXPOSED_CONTENT_COMPLETE}` | `EXACT_DUPLICATE` | none | merge; keep occurrence count |
| R2 | same `observation_id`, same `assessment_id`, `raw_identity = EXPOSED_CONTENT_PARTIAL` | `EQUIVALENT_AS_EXPOSED` | none | **never** called duplicate, identical or distinct (C07); `raw_identity` shown; counted as one observation of unverified raw identity |
| R3 | same `observation_id`, different `methodology_id` | `SAME_OBSERVATION_DIFFERENT_ASSESSMENT` | none | both kept; one observation |
| R3a | same `observation_id`, same `methodology_id` and T, different `ac_id`, `raw_identity` verified or complete | `CONFLICTING_ASSESSMENT` | both `INELIGIBLE` | same input, same method, different output |
| R3b | as R3a but `raw_identity = PARTIAL` | `UNRESOLVED_OBSERVATION_IDENTITY` | both `UNVERIFIED` | cannot tell one book assessed twice from two books |
| R4a | different `observation_id`, **D equal** (same algorithm, same section kind ⇒ same input rows), **M differs** | `SAME_INPUT_DIFFERENT_METHODOLOGY` | none | **Evaluated before R4b/R4c.** Different configuration (e.g. `atr_period`) legitimately yields different derived values. Both retained; the pair forms a `SHARED_INPUT_VERIFIED` edge (one input, not two confirmations); every metric `UNKNOWN: METHODOLOGY_DIFFERS`; **never** a report defect, never `INELIGIBLE` |
| R4b | different `observation_id`, **D equal**, **M equal**, same T, and *material output differs*: some compared metric is `DIFFERENT` (§3.4, which requires equal methodology and equal window) **or** `ac_id` differs | `CONFLICTING_ASSESSMENT` | both `INELIGIBLE` | requires the **same verified input identity, the same methodology, the same T, and different material output**. Report defect |
| R4c | different `observation_id`, **D equal**, **M equal**, same T, exposed content differs only in metrics that are `UNKNOWN` (window not verified, withheld on one side) and `ac_id` equal | `UNRESOLVED_INPUT_SET_DIFFERENCE` | both `UNVERIFIED` | cannot prove a defect; not a conflict |
| R5 | different `observation_id`, **D differs**, **M equal**, `any_different` | `CONFLICTING_OBSERVATION` | all partitions `INELIGIBLE` | proven difference in exposed economic metrics under equal methodology and equal window |
| R6 | different `observation_id`, **D differs**, **M equal**, `all_compared_equal`, ≥1 compared | `EQUIVALENT_ON_COMPARED_METRICS` | none | plus flags `RECEIPT_VARIANT` if delivery differs, `COVERAGE_VARIANT` if coverage relation ≠ `SAME`; `uncompared` listed; `RAW_CANDLES_NOT_EXPOSED` where raw content is not exposed |
| R7 | different `observation_id`, **D differs**, **M equal**, `none_compared` | `UNRESOLVED_INPUT_SET_DIFFERENCE` | all `UNVERIFIED` | **not** a contradiction |
| R8 | different `observation_id`, **D differs**, **M differs** | `UNRESOLVED_INPUT_SET_DIFFERENCE` | all `UNVERIFIED` | all metrics `UNKNOWN: METHODOLOGY_DIFFERS` |
| R9 | different `observation_id`, **no digest on either side** (`basis = EXPOSED_FIELDS`), `exposed_content_id` equal | `EQUIVALENT_AS_EXPOSED` + `RECEIPT_VARIANT` if delivery differs | none | raw identity not claimed |
| R10 | different `observation_id`, no digest, `exposed_content_id` differs, `any_different` | `CONFLICTING_OBSERVATION` | all `INELIGIBLE` | requires `ESTABLISHED_EQUAL` through §25.12.1; the C07 hidden-threshold/different-best-bid case instead follows R10a (§25.12.4; AT-B1-9) |
| R10a | as R10, `none_compared` | `UNRESOLVED_INPUT_SET_DIFFERENCE` | all `UNVERIFIED` | |
| R11 | one side `PRESENT`, other `WITHHELD`/`NOT_AVAILABLE` | metric `UNKNOWN: NOT_PRESENT` | falls to R6/R7/R10a by the other metrics | absence is never equality |

If some metrics are `DIFFERENT` and others `EQUAL`, the proven difference governs (R5/R10). An equal metric does not cancel a proven difference.

**Rule ordering (normative, v3.1).** For each pair, evaluate in this order and stop at the first match:
1. Same `observation_id`: R1, R2, R3, R3a, R3b.
2. Different `observation_id`, **both digests present with equal algorithm and section kind** (D equal): **methodology first** — R4a (M differs), then R4b/R4c (M equal).
3. Different `observation_id`, D differs: R5, R6, R7, R8 (R8 when M differs).
4. No digest on either side: R9, R10, R10a.
5. R11 applies inside metric comparison, not as a separate branch.

Consequence: no pair with different `methodology_id` can reach R4b, R5 or R10, because each of those requires M equal (R5 and R10 through §3.4, where `cmp` returns `UNKNOWN` when methodology differs). A different configuration value alone is never classified as a report defect, and no variant is ever ranked or counted as independent confirmation (`independence` stays `NOT_ESTABLISHED`).

No row selects a winner. Same provider alone creates no relation. The mixed-direction case (a pair of units with an equal digest and a pair with a different digest in one slot) is evaluated pairwise; the group relation is the most severe pairwise relation, and every pairwise relation is retained.

### 5.4 Consistency check [P]

- R1–R3c depend on equal `observation_id`; R4a–R10a depend on different `observation_id`. Their observation-identity domains are disjoint; unresolved labels and activation prerequisites remain those of §25.12–25.13.
- In the different-observation/equal-D domain, §25.12.2 partitions the three methodology states: R4a for ESTABLISHED_DIFFERENT, R4b then its complement R4c for ESTABLISHED_EQUAL, R4d for NOT_ESTABLISHED. This partition is disjoint and exhaustive at the branch level, including equal-XC/different-delivery variants. It does not establish completeness of unrelated deferred routing. R5–R8 apply to differing D; R9–R10a require no digest on either side. Unequal digest availability remains a future routing dependency, not an inferred equality.
- **v3.1 guarantee, reconciled:** the fixture with identical candles and differing ATR under `atr_period=2` versus `3` has equal D and different exposed-content/observation identities. It follows R4a only with ESTABLISHED_DIFFERENT established under one approved mapping; otherwise R4d. Neither case may fall through to a conflict. Different configuration alone is not mapping-validation evidence.
- `observation_id` equal implies `slot_id`, `exposed_content_id` and `input_set_id` all equal. So R6 (digest differs, exposed content equal) always has different `input_set_id` and is therefore always a different `observation_id`. No overlap with R1/R2.
- A receipt-only difference changes `input_set_id` (via L5), not `exposed_content_id`. For the ordinary C09 case where the source digest also changes: `ESTABLISHED_EQUAL` permits R6 when at least one metric compares equal; `NOT_ESTABLISHED` follows R8, with `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED` and `RECEIPT_VARIANT`. With no compared metric, the equal-methodology case is R7. A no-digest pair with equal XC follows R9; an equal-D/different-delivery pair follows the explicit §25.12.2 disposition. Receipt difference alone never proves a financial conflict or methodology equality. This replaces the unconditional R6-or-R9 guarantee.
- A coverage-only difference changes `exposed_content_id`, never proves an economic contradiction, and retains `COVERAGE_VARIANT`. For differing digests, R6/R7 require `ESTABLISHED_EQUAL` (R6 also requires at least one compared equal metric); otherwise R8 applies. For equal D, §25.12.2 governs. No digest or other unresolved routing may borrow an R6 equivalence from coverage equality. The no-conflict-from-coverage guarantee is unconditional; the equivalence routing is conditional.
- A candle price difference inside a verified comparable metric window can establish a compared difference and R5 only with `ESTABLISHED_EQUAL` and differing digests. Under `NOT_ESTABLISHED`, the metric is `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED`, and R8 preserves both variants as `UNVERIFIED`; price inequality is not erased or promoted into a proven C15 conflict. **B1 item 1, conditional routing.**

### 5.5 Source-reported contradictions [P]

Copied verbatim as `(category, kind, code, location)`; C15 infers none. Includes C10 `CONTRADICTORY_MOMENTUM`, C12 `FomcEvidence.consistency=CONTRADICTORY` and `conflicting_receipts`, C13 `FALSE`/`MISLEADING`/`OUTDATED` and fact outcome `CONTRADICTED`, C11 `contradictory_label_count` and `wallets_conflict`, C12 ETF `FundStatus.CONFLICT`. These are not C15 relations and do not affect §5.3.

---

## 6. TYPED_LINEAGE_CONTRACT

### 6.1 Edge types [P]

| Edge | Direction | Verified by | Forms a lineage group? |
|---|---|---|---|
| `COORDINATE_ASSOCIATION` | undirected | equal `series_id` or `slot_id` | no (association cluster only) |
| `PROVENANCE_EQUAL` | undirected | equal full `SourceProvenance` tuple (`source`, `source_type`, `source_id`, `source_timestamp`, `received_timestamp`) on exposed provenance | no |
| `SHARED_INPUT_VERIFIED` | undirected | equal `input_digest` **and** equal `digest_algorithm` **and** equal section kind | yes |
| `DERIVATION_VERIFIED` | C10 → C08/C09 | `SourceRef.input_digest` equals a supplied section's `input_digest`, equal algorithm | yes |
| `DERIVATION_MISMATCH` | C10 → C08/C09 | a supplied section of that kind exists but no digest equals | no (both kept; flag) |
| `DERIVATION_UNRESOLVED` | C10 → source | source section not supplied | no (`lineage_complete=false`) |
| `CITATION_RESOLVED` | C13 → C12 | citation path begins with `series[<id>]` or `fomc` and the supplied C12 report holds that unit | yes (directed) |
| `CITATION_UNRESOLVED` | C13 → ? | path in another form or no supplied unit | no |

**Equal `economic_fingerprint` is not a lineage edge, and v2's EF no longer exists.** Equal coordinates mean `COORDINATE_ASSOCIATION` only. Equal `exposed_content_id` is a relation in family B, not lineage.

### 6.2 Groups [P]

A lineage group is a connected component over edges that form groups (`SHARED_INPUT_VERIFIED`, `DERIVATION_VERIFIED`, `CITATION_RESOLVED`). Association clusters and provenance-equal pairs are reported in separate fields. `independence` is **always** `NOT_ESTABLISHED`. Group size is never a confirmation count.

C12 report-level `MacroEvidenceReport.input_digest` is **never** a lineage token or unit identity. It identifies the whole report input set. It is recorded once as `report_input_ref`. Per-unit provenance and explicit C13 path citations are the only C12 links. The C13 result does not expose which C12 report it used, so each `CITATION_RESOLVED` edge carries `C12_REPORT_IDENTITY_NOT_EXPOSED_BY_C13_RESULT`.

### 6.3 Temporal contract [P]

All report evaluation times must equal T. A report at another T is retained in `excluded` with its own times and is never relabeled.

Timestamp roles: **OBSERVED** (after T ⇒ `FUTURE_OBSERVATION`), **RECEIPT** (after T ⇒ `FUTURE_AVAILABILITY`), **WINDOW_BOUND** (consistency only), **SCHEDULED_FOR** (may be after T; FOMC `calendar_provenance.received_timestamp ≤ T` checked; series carry `SCHEDULE_AVAILABILITY_NOT_EXPOSED_BY_C12_REPORT`).
A unit excluded for a future timestamp is recorded as `{kind, report_ref, reasons, content_withheld=true}`; its content enters no identity, relation, group or count. (Unchanged from v2.)

### 6.4 Documented limits [P]

- **C08/C09/C10 receipt visibility.** Only the newest record's receipt metadata is exposed (`FlowProvenance.newest_trade_provenance`, `InputProvenance.newest_record_provenance`, plus counts). C15 cannot verify that every contributing record was received at or before T. It relies on the source's receipt filter (`flow/analytics.py:240`; `derivatives/analytics.py` `_split_known`). Records carry `RECEIPT_TIME_VISIBILITY_LIMITED_TO_NEWEST_RECORD`.
- **Overlap without proof.** Reports from one venue over overlapping windows may share underlying observations without a provable link. They carry `POSSIBLE_OVERLAPPING_SOURCE_OBSERVATIONS_LINEAGE_NOT_PROVEN`, form no lineage group, and are never counted as independent.

---

## 7. C13_IDENTITY_AND_REVISION_POLICY

- **[F]** `claim_id` is derived from the claim's source, `source_id` and `text_digest` (`news/models.py:343-356`). **[F]** `VerificationResult.input_digest` includes the evaluation time, the policy and a digest of the whole evidence set (`news/engine.py:478-501`), so it is an **assessment-input** digest.
- **[P] `news_claims` is deferred out of Phase 1.** `fuse()` takes only `VerificationReport`. C13 identity therefore never depends on an optional input. Re-introduction requires its own owner decision and a separate contract.
- **[P] Slot and observation.** `series_key = {NEWS.result}`; `slot_time = claim_id`; `basis = EXPOSED_FIELDS`; `raw_identity = EXPOSED_CONTENT_PARTIAL` (source and text are not exposed on the result; only the id). `input_set_ref.digest = null`. The result's `input_digest` is placed in `AC`, never in L1–L5 or any token.
- **[P] No revision inference.** C15 does not link claims by a shared `source_id`. A non-null generic `source_id` is not evidence that two claims are revisions of one another, and `VerificationResult` does not expose the source anyway. A corrected text yields a different `text_digest`, hence a different `claim_id`, slot and observation. It does not inherit the old identity. C15 records `CLAIM_REVISION_LINKAGE_NOT_ESTABLISHED`. It never merges, replaces or supersedes.
- **[P] Same `claim_id` twice at one T.**
  - equal `input_digest` (C13 methodology `MI` is constant, so M is equal), different exposed content ⇒ R4b `CONFLICTING_ASSESSMENT`; **[v3.7 PROPOSED: superseded by §25.12.3. M is no longer "equal" by constancy.]**
  - different `input_digest`, different exposed content ⇒ `UNRESOLVED_INPUT_SET_DIFFERENCE` (evidence or policy differs; not a proven conflict);
  - equal content ⇒ `EQUIVALENT_AS_EXPOSED`.
- **[P] Methodology.** `MI = {engine_version, VERIFICATION_POLICY_NOT_EXPOSED}`. C13 methodology is partial and disclosed. **[v3.7 PROPOSED: restated as an illustrative, unapproved mapping candidate in §25.11 and §25.12.3]**
- **[P]** C13 path citations feed `CITATION_RESOLVED` edges only (§6.1).

---

## 8. COMPLETE_C14_BINDING_CONTRACT

### 8.1 Design [P]

v2's V1–V10 are replaced by **replay**. C15 does not trust the record's `request`, `interpretation`, `evidence`, `source_references`, `annotations` or `private_bindings`. It recomputes them from the supplied source reports using C14's own code and requires equality.

C15 imports `traid.ai.selection.select`, `traid.ai.validation.check_output`, `traid.ai.validation.adapt`, `traid.ai.selection.canonical_json`. It never imports private names (`_sections`, `_context`, `_Builder`).

### 8.2 Inputs [P]

```
AiBindingInput:
  result: AIResult
  record: AIAnalysisRecord
  evidence_inputs: EvidenceInputs      # the exact C14 inputs; supplied by the caller
```

**Two distinct checks (v3.1).** `EvidenceInputs` holds source reports **and** a configuration object. They are verified differently and are never mixed.

1. **Source reports** — `market_state`, `whales`, `macro`, `etf`, `news`. For each non-`None` member, `report_sha256(member)` (imported from `ai.selection`) must equal the `report_sha256` of a report of the same type registered in this call. Otherwise `AI_INPUT_NOT_REGISTERED:<member>`. Only these are registered as evidence, appear in the manifest, and carry a report digest.
2. **ETF mapping** — `etf_mapping` (`AssetEtfMapping`) **is not a source report.** It is neither registered as evidence nor entered in the manifest, and no report digest is assigned to it. It is verified only by **configuration equality**:
   - both `evidence_inputs.etf_mapping` and `FusionInputs.etf_mapping` are `None`: pass;
   - both present: pass iff `canonical_json(a.model_dump(mode="json")) == canonical_json(b.model_dump(mode="json"))` (value equality of the model; no new digest function is assumed to exist);
   - one `None` and one present, or unequal: `AI_MAPPING_NOT_EQUAL`, commentary withheld.

   The same mapping object is what `fuse` supplies to the ETF adapter and what C14 `select` replays with, so BIND-4 cannot pass on a different mapping. The deterministic report records the configuration under `configuration.etf_mapping` as `{present: bool, config_sha256: sha256(canonical_json(model_dump(mode="json"))) or null}`. The field name says "config", never "report".

### 8.3 Checks (fail-closed; any failure ⇒ commentary withheld) [P]

| ID | Check |
|---|---|
| BIND-1 | `result.status is VALID`, `result.persistence is COMMITTED`, `result.interpretation` present; `record.status is VALID`; `record.interpretation` present; `result.run_id == record.run_id`, both non-null; `result.interpretation == record.interpretation` (full model equality). |
| BIND-2 | `record.evaluation_time == record.request.evaluation_time == T`; `record.task_id == record.request.task_id.value == record.interpretation.task_id.value`; `record.request`, `record.request_sha256`, `record.private_bindings` all non-null. |
| BIND-3 | `sha256(canonical_json(record.request.model_dump(mode="json"))) == record.request_sha256`. |
| BIND-4 | **Replay selection.** `sel = select(TaskId(record.task_id), T, evidence_inputs)`. Require `sel.skip is None`, `sel.request == record.request`, `sel.request_sha256 == record.request_sha256`, `sel.bindings == record.private_bindings` (compared inside C15, not output), `sel.excluded == record.excluded_items`, `sel.context is not None`. This binds every request item, claim, fact, handle and `HandleSource` locator to the supplied source reports. A locator that C14 would not produce from these reports makes the equality fail. |
| BIND-5 | **Section-by-section original-output verification.** For every section of `record.interpretation.output` (`summary`, `anchor_assessments`, `context_notes`, `claim_notes`, `uncertainties`) and every `NumberRef`: run `check_output(output, sel.context)` (must not raise). Then C15 additionally walks the public `TaskOutput` fields itself and requires: each ref classified by `ctx` membership as exactly one of `EVIDENCE_ITEM` (in `ctx.items`), `CLAIM` (`ctx.claims`), `CLAIM_FACT` (`ctx.facts`), `CATEGORY` (`CAT:` + known `Category`); each anchor id in `ctx.anchors`; each `claim_notes[].claim_id` in `ctx.claims`; each `NumberRef.value_id` in `ctx.values`; claims not cited as facts in `summary` or `anchor_assessments`; anchor and claim coverage complete. Classification uses `ctx`, **never a regex alone**. |
| BIND-6 | **Re-projection.** `expected = adapt(output, sel.context, record.interpretation.analysis_timestamp)`; require `expected == record.interpretation` (full model equality). This forces consistency between the original output, the canonical `evidence` list, `source_references` (kind, subject, tier, category, engine version), `annotations` (`upstream_state`, `claim_state`), `uncertainty`, `missing_information`, `flags` and `limitations`. |
| BIND-7 | `available_at = record.decided_at`; require `record.invoked_at <= record.decided_at` and non-null. `POST_EVALUATION_COMMENTARY` is set when `available_at > T`. Informational. |
| BIND-8 | `asset_scope == "BTC"` ⇒ the registered market-state report is BTC; the macro task keeps `NONE_MACRO_ONLY` (from `record.request`, verified equal to `sel.request`). |

`tool_input_sha256` is **not** replayed (the model's raw tool input is not reconstructible from `TaskOutput`). It is excluded from public output; the block carries `TOOL_INPUT_DIGEST_NOT_REPLAYED`.

### 8.4 Handle kinds (distinguished) [P]

| Handle form | Kind | Space | Persistence |
|---|---|---|---|
| `E###` | `EVIDENCE_ITEM` | request-local | per request only |
| `N###` | `CLAIM` | request-local | per request only |
| `N###.F##` | `CLAIM_FACT` | request-local | per request only |
| `A##` | `ANCHOR` | request-local | per request only |
| `E###.V#` | `NUMERIC_VALUE` | request-local | per request only |
| `CAT:<category>` | `CATEGORY` | global enum | stable |

All request-local handles are labeled `REQUEST_LOCAL_HANDLES_NOT_EVIDENCE_IDS` and are never C15 evidence ids.

### 8.5 Failure statuses [P]

- Binding failure ⇒ `AI_BINDING_UNVERIFIED` with codes (`BIND-n:<code>` where the code is C14's own `OutputInvalid.code` when a replay check raised it). The interpretation is withheld from the output. `deterministic_digest` is unchanged (§9).
- `AI_INVALID`, `AI_UNAVAILABLE`, `AI_NOT_REQUESTED` are carried with their own reasons. No interpretation.
- A source locator that cannot be verified ⇒ BIND-4 fails ⇒ withhold. **C15 never labels unverified commentary as verified.**

### 8.6 E999 counterexample (mandatory acceptance test, AT-AI-E999) [P]

Construct a valid replayable record, then in separate cases:

1. Put `"E999"` in `output.summary.refs`. Expect BIND-5 fail (`UNKNOWN_REFERENCE` from `check_output`).
2. Put `"E999"` in each of `anchor_assessments[].evidence_ids`, `context_notes[].refs`, `claim_notes[].refs`, `uncertainties[].refs`. Each must fail BIND-5, with the section named in the code detail.
3. Put `"E999.V1"` as a `NumberRef.value_id` in each section. Expect `UNKNOWN_REFERENCE`.
4. Leave `output` valid but add `"E999"` to `interpretation.evidence` only. Expect BIND-6 mismatch.
5. Leave `output` and `evidence` valid but add an `E999` `SourceReference` and/or `Annotation`. Expect BIND-6 mismatch.
6. Change a `SourceReference.kind`, `.subject`, `.tier`, an `Annotation.upstream_state` or `.claim_state` to a plausible but wrong value. Expect BIND-6 mismatch.
7. Re-use a valid claim handle in `summary.refs` (claim cited as fact). Expect `CLAIM_CITED_AS_FACT`.

The original fixture must **not** be adjusted to pass: the checks are never weakened, and if the unmodified record fails BIND-4 because `select` is non-deterministic or inputs differ, the commentary is withheld and the defect is reported.

---

## 9. PRIVATE_DATA_AND_AI_ISOLATION

- **[F]** `PrivateBindings` is owner-only (`ai/models.py:430-431`) and holds `report_digests`, `handle_sources` (with locators), watchlist and whale fields.
- **[P] Never in public output:** any `PrivateBindings` field or value, `handle_sources` and locators, whale digests and contributors, `record.raw_response`, `record.attempts`, `record.model`, `record.tool_input_sha256`, the full `record.request`, run-internal exclusions. Output carries only: status, reasons, run id, task id, evaluation time, `available_at`, the BIND verdict and codes, and (only if bound) the released `interpretation` as untrusted data.
- **[P] AI text is untrusted.** The released interpretation carries `untrusted_model_text=true`. C15 never parses it for facts.
- **[P] AI stances are not roles.** `supporting_factors` and `contradicting_factors` are the model's anchor stances (`adapt`, `ai/validation.py:874-885`). C15 never reads them into any role, count, group, relation, warning or gap. They appear only inside the verbatim payload labeled `AI_STANCE_NOT_A_ROLE`. No deterministic C15 role, enum member, count, group, relation, warning, gap, score, ordering or decision authority is derived from them, and none is named with `support` or `contradict`. **Exempt names:** `SourceReportedContradiction` and `source_reported_contradictions` (§5.5, §11), and the verbatim payload keys `supporting_factors` and `contradicting_factors` inside the payload labeled `AI_STANCE_NOT_A_ROLE`. The exempt names carry source-reported or AI-quoted content only and confer no authority. Source-reported values such as `CONTRADICTORY_MOMENTUM` (§5.5) are data values copied verbatim; they are not newly authorized C15 enum members or field names.
- **[P] No AI influence on the deterministic part.** No code path reading `ai_commentary` is reachable while building the deterministic part.
- **[O] Wallets.** `wallet_ref = "wr1:" + HID("c15.wallet.v1", address)`; no raw address in output. Not approved. C14 already guards requests against addresses (`ai/selection.py` `ADDRESS` check).
- **[P]** C15 reads `evidence_inputs` and `record` only inside the binding function and does not store them in its report.

### 9.1 Deterministic and full digests [P]

- `deterministic_digest = sha256(canonical_json(D))` where `D` = the `FusionReport` **without** `ai_commentary`, `deterministic_digest`, `report_digest`. (`canonical_json` imported from `ai.selection`; `model_dump(mode="json")`.)
- `report_digest = sha256(canonical_json(R))` where `R` = the full report without `report_digest`, with `deterministic_digest` included.
- Changing or removing any AI input changes `report_digest`, never `deterministic_digest`.

---

## 10. CANONICAL_PHASE_1_STATUS

- **Phase 1 is a partial milestone. C15 remains OPEN.** The Card's Exit Gate is not altered, not weakened, and not claimed.
- **[F]** The Spec's C15 scope lists "supporting and contradicting roles" and its Exit Gate requires "support, contradiction, missing/stale evidence, and coverage gaps ... remain visible". Phase 1 defines no support or contradict role.
- **[P]** `ROLE_RULES_ACTIVE = ()`. P1, P2 and P3 are inactive constants with no activation parameter, flag, attestation or environment switch. `EvidenceRole = {DESCRIPTIVE_ONLY, MISSING, STALE, UNVERIFIED, INELIGIBLE}`; it has exactly these five members, and `DESCRIPTIVE_ONLY` is the normal descriptive role (§5.2 step 6). No `ELIGIBLE`, `SUPPORT` or `CONTRADICT` member exists. No score, probability, weight, readiness number or prediction.
- **Out of scope in Phase 1:** active signal fusion, C13 `news_claims`, historical fusion, any Strategy or Risk interface, any additional AI call, any upstream modification.
- **C16 is not authorized.** A Phase 1 merge must not be recorded as C15 COMPLETE. C16 depends on C15; starting it needs a separate owner decision.
- **Required before implementation [O]:** card-start approval and `ROADMAP_ALIGNMENT_GATE: PASS` (Spec §2 process); owner approval of Phase 1 as a scope-limited, partial deliverable, with canonical reconciliation as the Spec requires for scope material changes (the rule cited earlier as `TRAID_CARD_SPECIFICATIONS.md:64` — re-verify the line number and wording); an independent Codex PASS on this contract.
- **Canonical wording issue [O]:** the Spec says C07–C14 "produce independent evidence". In the repository, C10 is built from C07–C09, C13 cites C12, C14 consumes C10–C13. C15 will not claim independence. Amending the wording is an owner decision and a canonical edit, **not done here**.

---

## 11. MINIMAL_PUBLIC_API

```python
# traid/fusion/__init__.py   (Phase 1; pure, in-memory; no I/O, network, AWS, Strategy or Risk imports)
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class AiBindingInput:
    result: AIResult
    record: AIAnalysisRecord
    evidence_inputs: EvidenceInputs

@dataclass(frozen=True)
class FusionInputs:
    liquidity:    tuple[LiquidityReport, ...] = ()
    flow:         tuple[FlowReport, ...] = ()
    derivatives:  tuple[DerivativesReport, ...] = ()
    market_state: tuple[MarketStateReport, ...] = ()
    whales:       tuple[WhaleReport, ...] = ()
    macro:        tuple[MacroEvidenceReport, ...] = ()
    etf:          tuple[EtfEvidenceReport, ...] = ()
    etf_mapping:  AssetEtfMapping | None = None
    news:         tuple[VerificationReport, ...] = ()
    ai:           tuple[AiBindingInput, ...] = ()

def fuse(*, evaluation_time: datetime, inputs: FusionInputs) -> FusionReport: ...
def id_enc(value) -> object: ...                       # §4; raises IdentityEncodingError
def id_digest(tag: str, value) -> str: ...             # HID
```

- No configuration object: Phase 1 has no thresholds, no weights, no activation flags.
- `fuse` never mutates its inputs. Each report passes C14's `check_report`-style revalidation (dump, validate, re-dump equality; engine version accepted; evaluation time equals T) before use. A failing report is retained in `excluded` with its reason.
- `FusionReport` fields (names only, nothing score-like): `schema_version`, `evaluation_time`, `policy` (the inactive-role table), `manifest` (source reports only; the ETF mapping is not listed), `configuration` (`etf_mapping` config reference, §8.2), `evidence`, `excluded`, `relations`, `conflicts`, `lineage_groups`, `association_clusters`, `source_reported_contradictions`, `coverage_gaps`, `etf`, `limitations`, `ai_commentary`, `deterministic_digest`, `report_digest`.
- Class names above are confirmed from §1 grep. Module paths and the `AssetEtfMapping` import path are to be confirmed at implementation.

---

## 12. UPDATED_ACCEPTANCE_TEST_MATRIX

None of these tests exists yet. None has been run. All are required acceptance criteria. **[v3.7 PROPOSED: §25.12.4 makes every B1 expectation that needs equal or different methodology conditional on an ESTABLISHED methodology state.]**

### B1 — identity, economic changes, coverage

| ID | Behavior |
|---|---|
| AT-B1-CX1 | §3.6 CX-1 ⇒ `CONFLICTING_OBSERVATION`; both retained; no winner; coverage `SAME` |
| AT-B1-CX2 | CX-2 ⇒ `EQUIVALENT_ON_COMPARED_METRICS` + `RECEIPT_VARIANT`; not conflict; not exact duplicate |
| AT-B1-CX3 | CX-3 ⇒ `EQUIVALENT_ON_COMPARED_METRICS` + `COVERAGE_VARIANT`; `vwap` uncompared; no conflict |
| AT-B1-CX4 | CX-4 ⇒ conflict at comparable window; coverage difference neither causes nor masks it |
| AT-B1-CX5 | CX-5 ⇒ `UNRESOLVED_INPUT_SET_DIFFERENCE`; never equivalent |
| AT-B1-CX6 | CX-6 ⇒ absent is `UNKNOWN`, never equal |
| AT-B1-1 | Same timestamps and counts with different raw candles is never classified equal; no output text claims raw equality |
| AT-B1-2 | Different `input_digest` alone never yields `CONFLICTING_OBSERVATION` |
| AT-B1-3 | Equal `input_digest`, **equal** `methodology_id`, same T, a compared metric `DIFFERENT` (forged report) ⇒ `CONFLICTING_ASSESSMENT` (R4b); equal digest, equal methodology, only `ac_id` differs ⇒ `CONFLICTING_ASSESSMENT`; equal digest, equal methodology, only `UNKNOWN` metrics differ ⇒ `UNRESOLVED_INPUT_SET_DIFFERENCE` (R4c) |
| AT-B1-4 | Digests **differ** and methodology differs ⇒ every metric `UNKNOWN: METHODOLOGY_DIFFERS`; `UNRESOLVED_INPUT_SET_DIFFERENCE` (R8) |
| AT-B1-ATR-1 | **Identical candle inputs** (≥ 4 closed hourly candles, one `input_digest`), `atr_period=2` vs `atr_period=3`, ATR values differ ⇒ `SAME_INPUT_DIFFERENT_METHODOLOGY` (R4a); both retained; both keep their own eligibility; neither `INELIGIBLE`; `SHARED_INPUT_VERIFIED` edge present; `independence=NOT_ESTABLISHED`; no output text says conflict, defect or confirmation |
| AT-B1-ATR-2 | Same pair in both input orders and both argument positions ⇒ identical relation (`SAME_INPUT_DIFFERENT_METHODOLOGY`) and byte-identical `deterministic_digest` |
| AT-B1-ATR-3 | Rule-ordering probe: for the AT-B1-ATR-1 pair, assert R4b, R5, R10 and R4c are **not** matched (instrument or enumerate candidate relations); a pair with equal `atr_period` and different ATR on the same digest ⇒ R4b, **not** R4a |
| AT-B1-ATR-4 | Other configuration differences on identical input (`volatility_period`, `momentum_lookbacks`, `session_start`, `funding_lookback_hours`) ⇒ `SAME_INPUT_DIFFERENT_METHODOLOGY`, never a conflict; the `methodology_id` differs in each case |
| AT-B1-ATR-5 | `atr_period=2` vs `3` with **different** input digests ⇒ R8 (`UNRESOLVED_INPUT_SET_DIFFERENCE`), not R4a and not a conflict |
| AT-B1-ATR-6 | Three variants of one input (`atr_period` 2, 3, 4) ⇒ all retained; pairwise relations all `SAME_INPUT_DIFFERENT_METHODOLOGY`; one shared-input group; no winner |
| AT-B1-5 | Same observation, different methodology ⇒ `SAME_OBSERVATION_DIFFERENT_ASSESSMENT`, counted once |
| AT-B1-6 | Different slot, same series ⇒ `DIFFERENT_SLOT_SAME_SERIES`; no metric comparison; no conflict |
| AT-B1-7 | Metric windows: a metric with `window_id=None` never compares; VWAP uncompared when `earliest_time > session_start` |
| AT-B1-8 | Pairwise relations retained; the group relation is the most severe; no winner under any input order |
| AT-B1-9 | C07 identical exposed fields follow R2/R9 only when their structural prerequisites hold, yielding `EQUIVALENT_AS_EXPOSED`, never raw identity or methodology completeness. Two revalidated C07 reports with identical snapshot time, provenance and configuration but best bids 100 and 99.5 carry undischargeable `QUALITY_THRESHOLDS_NOT_EXPOSED`: they are `NOT_ESTABLISHED`, every metric is `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED`, and their different observations with no digest follow R10a as `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`, never `CONFLICTING_*`. Preserve both reports and their differing values. No same-provenance merge and no independent-confirmation claim |
| AT-B1-10 | Same provider alone creates no relation |
| AT-B1-11 | Coordinate association and exposed-content relation never produce a lineage group |
| AT-B1-12 | Receipt-only variants ⇒ `RECEIPT_VARIANT` informational; coverage-only variants ⇒ `COVERAGE_VARIANT` informational |
| AT-B1-13 | Eligibility effects exactly as §5.3 (worst-of precedence) |
| AT-B1-14 | Shuffled inputs and repeated runs give byte-identical identities, relations, `deterministic_digest` and `report_digest` |

### B2 — serialization

| ID | Behavior |
|---|---|
| AT-SER-1 | Decimal with more than 8,192 significant digits: two values differing only after digit 8,192 get **different** `ID_ENC`; the same value built two ways gets the same. No exception |
| AT-SER-2 | `1.0`, `1.00`, `1E+0` share one encoding; `100` and `1E+2` share one; `0.00` and `0` share one |
| AT-SER-3 | `1.5` ≠ `1.50` is **equal** under `ID_ENC`, but `REPORT_JSON` of a model holding each differs |
| AT-SER-4 | `Decimal("-0")` and `Decimal("0")`: equal under `ID_ENC`; `REPORT_JSON` keeps the repository spelling `"-0"` |
| AT-SER-5 | Datetimes `2026-01-01T12:00Z` and `2026-01-01T13:00+01:00` encode identically; naive datetime rejected; microseconds always six digits |
| AT-SER-6 | `date(2026,1,1)` ≠ `datetime(2026,1,1,0,0,tz=UTC)`; each tagged distinctly; `datetime` is checked before `date` |
| AT-SER-7 | `timedelta` exact for negative values, days, and microseconds; no truncation |
| AT-SER-8 | Nested enums (enum whose value is an enum, a tuple of enums) recursively encoded |
| AT-SER-8a | Two enum classes both named `State`, with the same member name and value, defined in **different modules** (test creates classes whose `__module__` differ) ⇒ different `ID_ENC` and different `HID` digests |
| AT-SER-8b | `StrEnum` member (`"X"`) ≠ plain `str "X"`; `IntEnum` member (`1`) ≠ `int 1` ≠ `bool True`; enum dispatch precedes `str`/`int`/`bool` (a `StrEnum` is never encoded as a bare string) |
| AT-SER-8c | Nested: an enum whose value is another enum; a tuple of enums; an enum whose value is a `Decimal`; each encodes recursively and equal Decimal spellings give equal encodings |
| AT-SER-8d | Stability: encode the same fixtures repeatedly in-process and in two subprocesses with different `PYTHONHASHSEED`; all byte-identical |
| AT-SER-8e | Ambiguity: a class with `<locals>` in its `__qualname__`, a class in `__main__`, and a second distinct class object registered under an existing `module:qualname` each raise `AmbiguousEnumTypeError`; re-encoding the same class object does not raise |
| AT-SER-8f | `REPORT_JSON` / `report_sha256` outputs for an existing fixture are unchanged by the enum rule (C14 compatibility pin) |
| AT-SER-9 | Structured values: `seq` order matters; `bag`/`set` order does not; a dict with the key `"$"` cannot collide with a tagged value; int `1` ≠ Decimal `1` ≠ str `"1"` ≠ bool `True` |
| AT-SER-10 | Rejections: float, NaN, ±Infinity Decimal, bytes, `time`, non-str dict key, unclassified collection |
| AT-SER-11 | `report_sha256` imported from C14 equals C15's source-report digest for the same report; no separate reimplementation exists |
| AT-SER-12 | No `int()`/`str(int)` conversion on coefficients (a 20,000-digit Decimal encodes without a digit-limit error) |
| AT-SER-13 | **Subclass rejection.** A subclass of each of `Decimal` (overriding `as_tuple`), `datetime` (overriding `year`), `date` (overriding `year`), `timedelta` (overriding `__floordiv__`), `list` and `tuple` (overriding `__iter__`), `dict` (overriding `items`), `set` and `frozenset` (overriding `__iter__`) and `Unordered` raises `ID_TYPE_SUBCLASS_REJECTED`, directly and when nested; exact built-ins are accepted; `namedtuple` and `OrderedDict` are rejected |
| AT-SER-14 | **F1.** An `Enum` whose `value` property returns `0` for every member (both members read `0`) raises `ID_ENUM_NONSTANDARD`, as does an enum with a member named `value`. Ordinary `Enum`, `StrEnum`, `IntEnum`, `IntFlag` (including a composite), an enum with a custom `__new__` setting `_value_`, and an alias keep their declared value and distinct digests |
| AT-SER-15 | **F2.** An `Unordered` subclass whose `items` property hides the stored contents raises `ID_TYPE_SUBCLASS_REJECTED`; exact `Unordered` with different contents has different digests |
| AT-SER-16 | **F3.** A `datetime` with a stateful custom `tzinfo` (offset differs on every call) raises `ID_TZ_UNSUPPORTED` on repeated calls and when nested |
| AT-SER-17 | **Timezone acceptance.** `timezone.utc`, a fixed-offset `timezone`, `pydantic_core.TzInfo` and `ZoneInfo` give the same identity for the same instant; `ZoneInfo` `fold=0` and `fold=1` at an ambiguous time give different, correct UTC instants; a `ZoneInfo` subclass and a naive datetime are rejected |
| AT-SER-18 | `str` and `int` subclasses with overridden `__str__` / `__int__` encode their base value (carried from the previous remediation) |

### B3 — AI binding

| ID | Behavior |
|---|---|
| AT-AI-0 | **Gate:** `select` with identical inputs called twice returns equal `request`, `request_sha256`, `bindings`, `excluded`. If not, implementation stops and reports |
| AT-AI-E999 | All seven §8.6 cases fail closed with the specified code |
| AT-AI-1 | Each BIND-1..BIND-8 failure independently withholds the commentary |
| AT-AI-2 | Replay of an unmodified, valid fixture record passes; deterministic part unchanged by pass or fail |
| AT-AI-3 | `evidence_inputs` not registered in this call ⇒ `AI_INPUT_NOT_REGISTERED` |
| AT-AI-4 | A locator or `HandleSource` altered ⇒ BIND-4 fails; commentary withheld |
| AT-AI-5 | Each handle kind in §8.4 verified by `ctx` membership; a regex-valid but absent handle fails |
| AT-AI-6 | A ref valid in one section but not allowed there (claim in `summary`) fails per section |
| AT-AI-7 | Consistency of `evidence` ⇔ cited refs; `SourceReference` kind, subject, state, tier; `Annotation` states |
| AT-AI-8 | `AI_INVALID`, `AI_UNAVAILABLE`, `AI_NOT_REQUESTED` shown with their reasons; never bound |
| AT-AI-9 | `POST_EVALUATION_COMMENTARY` set when `available_at > T` |
| AT-AI-10 | A forged `AIResult`/record pair (fields valid, replay mismatched) never releases content |

### Privacy, roles, canonical scope, and the rest

| ID | Behavior |
|---|---|
| AT-PRIV-1 | No `PrivateBindings` field, locator, whale digest, `raw_response`, `attempts`, `model`, `tool_input_sha256`, or full `request` anywhere in the output (recursive scan of serialized output) |
| AT-PRIV-2 | AI `supporting_factors` / `contradicting_factors` populate no deterministic C15 field, role, count, group, relation, warning or gap, and are never used to generate a score or decision authority; a name scan finds `support` or `contradict` only in the exempt names listed in §9 |
| AT-PRIV-3 | No raw wallet address in output |
| AT-DIG-1 | Adding, altering or removing AI input changes `report_digest`, never `deterministic_digest` |
| AT-P-1 | `ROLE_RULES_ACTIVE == ()`; no activation field or parameter in any model or signature; `EvidenceRole` has exactly the five members |
| AT-P-2 | For funding, flow and trend fixtures in every state, no `SUPPORT` or `CONTRADICT` role appears; states, reasons, quality and provenance pass through unchanged |
| AT-C13-1 | `fuse` signature has no `news_claims`; C13 identity identical with or without any other input |
| AT-C13-2 | Corrected claim text ⇒ different `claim_id`, slot, observation; never old identity; `CLAIM_REVISION_LINKAGE_NOT_ESTABLISHED` |
| AT-C13-3 | A shared non-null generic `source_id` never links two claims |
| AT-C13-4 | `VerificationResult.input_digest` only in `AC`; changing T or hidden policy changes `assessment_id` not `observation_id` |
| AT-LIN-1 | Only `SHARED_INPUT_VERIFIED`, `DERIVATION_VERIFIED`, `CITATION_RESOLVED` form groups; C10 mismatch ⇒ `DERIVATION_MISMATCH`; unsupplied ⇒ `DERIVATION_UNRESOLVED`; no output claims independence |
| AT-LIN-2 | C12 report-level digest never appears as a token; no unrelated C12 units group because of it |
| AT-TIME-1..3 | Evaluation-time extraction per source; future observation and availability excluded with content withheld; known future schedule retained |
| AT-LIM-1 | `RECEIPT_TIME_VISIBILITY_LIMITED_TO_NEWEST_RECORD` and `POSSIBLE_OVERLAPPING_SOURCE_OBSERVATIONS_LINEAGE_NOT_PROVEN` present |
| AT-ETF-2 | `etf_mapping` is not in the manifest, not registered as evidence, and has no report digest; `configuration.etf_mapping.config_sha256` is present only when a mapping is supplied |
| AT-ETF-3 | AI binding: equal mapping ⇒ passes; mapping absent on one side or unequal ⇒ `AI_MAPPING_NOT_EQUAL`, commentary withheld; an `etf` source report not registered ⇒ `AI_INPUT_NOT_REGISTERED`; mapping check never uses `report_sha256` |
| AT-ETF-4 | Changing only the mapping changes `configuration` and `deterministic_digest` but registers no new evidence unit |
| AT-ETF-1 | Missing, null, partial or conflicting ETF data never directional or zero; availability, applicability, freshness independent; freshness `NOT_DEFINED_BY_C12`; `ETF_COVERAGE_INSUFFICIENT` raised |
| AT-SRC-1 | Source-reported contradictions copied verbatim; none inferred |
| AT-NOPRED-1 | Model-field scan finds no `score`, `alignment`, `strength`, `confidence`, `probability`, `weight`, `readiness`, `priority`; `ALIGNMENT_IS_NOT_PROBABILITY` present; no Strategy, Risk, network or AWS import |

---

## 13. REMAINING_OWNER_APPROVALS

**Granted in this conversation (from earlier user instructions):** O1, O2, O3, O4, O5, O8; P1/P2/P3 inactive with no activation mechanism and no attestation; exact identity and conflict semantics as a direction; the nine corrections MC1–MC9 (as a direction, not a verdict on the text).

**Not granted:**

1. Card-start approval and `ROADMAP_ALIGNMENT_GATE: PASS` for C15.
2. Approval of Phase 1 as a scope-limited partial milestone, plus the canonical reconciliation of the Card Spec and Roadmap (not done here).
3. `wallet_ref` privacy approach (§9).
4. Deferral of `news_claims` out of Phase 1 (§7) — recommended; needs confirmation.
5. ETF freshness policy (C12 defines none).
6. The "independent evidence" wording amendment (§10).
7. An independent Codex PASS on this v3 contract.
8. Whether C16 may start on a Phase 1 partial (default: no).

---

## 14. FINAL_DESIGN_VERDICT

**READY_FOR_INDEPENDENT_AUDIT** (v3.1) — *not* approved, *not* PASS. The verdict applies to the two reproduced defects and the ETF clarification only; everything else is carried from v3.0 and keeps v3.0's open items. I authored this contract and I cannot audit it independently.

Unresolved items that Codex should weigh:

1. **I lack Codex's audit text** and the three candle counterexamples (§3.6 are reconstructions).
2. **Metric window rules** (§3.3) are proposed; only the `_tail` consecutive-run property was verified. VWAP, momentum, volatility and C08 windows must be read before enabling comparison. Fail-safe default is `UNKNOWN`.
3. **`select` determinism and purity** (AT-AI-0) is unverified. If it fails, BIND-4 cannot be used and the AI block must be deferred.
4. **`check_output`** was read for ref/section checks (lines 200-232). The narrative checks (`narrative_check`, lines ~287-860) were not re-read; replay reuses them but I make no claim about their content here.
5. R6's equivalence says nothing about candles outside metric windows (`RAW_CANDLES_NOT_EXPOSED`).
6. No production composition site feeds these reports. Historical fusion is unsupported. Live-provider behavior is unverified. U2 (trade-window completeness) is open.
7. The signed-zero and >8,192-digit rules intentionally diverge from the repository's converters, and are disclosed in §4.3.

No code, test, Git or canonical document was changed by this task.

---

## 15. INDEPENDENT_AUDIT_HANDOFF

**Challenge, in priority order:**

0. **v3.1 targets.** (a) §5.3 R4a–R4c and the ordering block: can any pair with different `methodology_id` still reach a conflict branch (R4b, R5, R10)? Run the `atr_period=2` vs `3` case against the written rules. (b) §4.2a: can two distinct enum types still collide, or can an Enum be encoded through a primitive branch? (c) §8.2: is the mapping/report split complete, and does anything still treat `AssetEtfMapping` as a report?
1. **§5.3 R5/R6/R7.** Is "equal methodology + equal window + exact metric difference ⇒ conflict" sound for each C09 metric class? Is it right that a `PRESENT` ATR implies an identical underlying window, so a differing ATR proves differing candles? Re-read `_candle_section` and `_tail`.
2. **§3.3 window rules.** Verify, per metric, the claimed window against the source formula. Any rule that does not hold must become `window_id=None`.
3. **§4.** Check `ID_ENC` for collisions across types, the signed-zero rule against C10 comparisons, behaviour above 8,192 digits, and whether any source model carries a type the encoder rejects (`datetime.time`, `date`).
4. **§8.** Re-read all of `ai/validation.py` and `ai/selection.py`. Does `select` replay deterministically? Does `check_output` plus `adapt` equality close every E999-style path, including `numbers[].value_id` ownership? Are there fields of `ValidatedInterpretation` that `adapt` does not derive from `(output, ctx, analysis_timestamp)` alone?
5. **§6.1.** Is `SHARED_INPUT_VERIFIED` by equal digest sufficient? Is the C13→C12 prefix convention (`series[...]`, `fomc...`) stable?
6. **§7.** Is deferral of `news_claims` acceptable, and is `claim_id` alone enough as the C13 slot?
7. **§10.** Confirm Phase 1 cannot be read as satisfying the Exit Gate.

**Evidence to check:** `derivatives/analytics.py:138-148,297-355,360,411-424`, `ai/selection.py:71-136,892-985`, `ai/validation.py:93-232,874-938`, `ai/models.py:418-488`, `tests/test_ai_validation.py:109-112,270`, `whales/models.py:29,48-61`, `macro/models.py:39,51-68`, `regime/engine.py:180-190`, `news/engine.py:478-501`, `news/models.py:333-356`.

**No implementation has started and none is authorized.** STOP.

---

## 16. CHANGES_V3_0_TO_V3_1

Exactly these clauses changed. Everything else is byte-identical to `TRAID_C15_PHASE1_CONTRACT_v3_AFTER_AUDIT_FAIL.md`.

| # | Clause | v3.0 | v3.1 |
|---|---|---|---|
| C1 | Header | version `v3.0-DRAFT` | version `v3.1-DRAFT`, supersedes v3.0 and v2, scope note |
| C2 | §5.3 R4 | one row: equal digest, different `exposed_content_id` ⇒ `CONFLICTING_ASSESSMENT`, no methodology test | replaced by R4a (`SAME_INPUT_DIFFERENT_METHODOLOGY`, M differs), R4b (`CONFLICTING_ASSESSMENT`: same verified input, same M, same T, different material output), R4c (`UNRESOLVED_INPUT_SET_DIFFERENCE`) |
| C3 | §5.3 ordering | none stated | "Rule ordering (normative)" block: methodology tested before any conflict branch |
| C4 | §5.2 step 4 | "apply R4–R10" | "R4a–R10a, in the order given under Rule ordering" |
| C5 | §5.4 | R1–R3b / R4–R10a disjointness | R4a–R10a; added R4a/R4b/R4c partition bullet and the `atr_period=2` vs `3` guarantee |
| C6 | §7 same-`claim_id` bullet | "R4" | "R4b" (C13 `MI` is constant) |
| C7 | §4.2 Enum row | `{"$":"enum","c":"<__qualname__>",...}` | `c` = `<__module__>:<__qualname__>`; any Enum subclass; dispatched before primitives |
| C8 | new §4.2a | — | dispatch order, enum type identity, ambiguity registry, stability, statement of what is unchanged |
| C9 | §8.2 | one rule: every `evidence_inputs` member must match a registered report digest | split: source reports (digest verification) vs `etf_mapping` (configuration equality, not a report); `AI_MAPPING_NOT_EQUAL` |
| C10 | §11 `FusionReport` | no configuration block | `manifest` clarified (source reports only); new `configuration.etf_mapping` |
| C11 | §12 tests | AT-B1-3, AT-B1-4, AT-SER-8 (old text) | AT-B1-3/4 corrected; added AT-B1-ATR-1..6, AT-SER-8a..8f, AT-ETF-2..4; AT-SER-8 narrowed |
| C12 | §14 | `READY_FOR_INDEPENDENT_REVIEW` | `READY_FOR_INDEPENDENT_AUDIT` (v3.1), scope note |
| C13 | §15 | — | item 0 added: v3.1 audit targets |
| C14 | new §16 | — | this table |

### 16.1 Unrelated design rules: unchanged
B1 candle comparison (§3.3–3.6, CX-1..6, §5.3 R1–R3b, R5–R11), B2 serialization (all of §4 except the Enum row and §4.2a), B3 replay binding (BIND-1..8 except the §8.2 input split), inactive P1/P2/P3 (`ROLE_RULES_ACTIVE = ()`), Phase 1 partial and C15 OPEN, no C16 authorization, privacy and AI isolation (§9), no Strategy/Risk interface, no score, weight, probability or prediction, `news_claims` deferral, lineage edge types (§6).

### 16.2 Remaining owner approvals
Unchanged from §13: card-start and `ROADMAP_ALIGNMENT_GATE`, partial-milestone scope approval with canonical reconciliation, `wallet_ref`, `news_claims` deferral, ETF freshness policy, the "independent evidence" wording, an independent Codex PASS on v3.1, and whether C16 may start (default no).

### 16.3 Honest limits of this edit
No test was run and no code written. The two defects are taken from the task description, not from Codex's audit text, which I do not hold. `AssetEtfMapping` is defined at `src/traid/macro/etf.py:81` as a `MacroModel` subclass (verified by grep only); that `model_dump(mode="json")` works on it is assumed from the shared model base and is to be confirmed at implementation.

---

## 17. CHANGES_V3_1_TO_V3_2

Exactly these clauses changed. Everything else is carried over from v3.1.

| # | Clause | v3.1 | v3.2 |
|---|---|---|---|
| D1 | Header | version `v3.1-DRAFT`, scope two defects | version `v3.2-DRAFT`, derived from v3.1, scope the bounded type policy (F1, F2, F3), list of unchanged historical sections |
| D2 | §4.2 table | `Decimal`, `datetime`, `date`, `timedelta`, collections and `Unordered` accepted by `isinstance`; `datetime` converted with `astimezone`; enum value read as `member.value` | exact-type rows; `datetime` offset read once with `datetime.utcoffset` and subtracted; enum value is the stored `_value_`; rejection row extended |
| D3 | new §4.2b | — | bounded type policy, Enum policy, timezone policy, failure codes |
| D4 | new §4.2c | — | honest limits of the policy |
| D5 | §12 | AT-SER-1..12 | added AT-SER-13..18 |
| D6 | §17 | — | this table |

**Behavior that changes for callers.** A value previously accepted and now rejected: any subclass of the exact-type rows, a `datetime` with a `tzinfo` outside `timezone`, `ZoneInfo`, `pydantic_core.TzInfo`, and an enum failing the Enum policy. Identity values for every accepted input are unchanged from the v3.1 Slice 1 implementation, apart from the earlier audit fixes (double-encoded envelope, encoded dictionary keys, unbounded integers), which are already part of v3.1 §4.

**Not changed.** Phase 1 is a partial milestone; C15 stays OPEN; C16 is not authorized; P1/P2/P3 are inactive; no SUPPORT or CONTRADICT roles; no score, probability or forecast; no Strategy or Risk interface; `news_claims` excluded; no new ETF freshness policy; wallet references privacy-preserving; U2 separate. The canonical Exit Gate and Closure Rule are untouched.

**Honest limits of this edit.** This contract change was written by the implementer and has not been audited by Codex. The three defect descriptions come from the task statement; I do not hold Codex's audit text.

---

## 18. CHANGES_V3_2_TO_V3_3

Exactly these clauses changed. Everything else is carried over from v3.2 unchanged.

| # | Clause | v3.2 | v3.3 |
|---|---|---|---|
| E1 | Title, version identifier, new v3.3 note | `v3.2`, bounded type policy | `v3.3`, role-precedence and naming-rule errata; derived from v3.2 |
| E2 | §5.2 step 6 (C-1) | precedence `INELIGIBLE > MISSING > STALE > UNVERIFIED > ELIGIBLE > DESCRIPTIVE_ONLY` | `ELIGIBLE` removed; `DESCRIPTIVE_ONLY` defined as the normal inactive descriptive role (not confirmation, support or readiness) |
| E3 | §10 `EvidenceRole` bullet (C-1) | five members listed; no `SUPPORT` or `CONTRADICT` | states exactly five members; also no `ELIGIBLE` |
| E4 | §9 "AI stances are not roles" (C-2) | "No C15 field name uses `support` or `contradict`." | no deterministic derivation from AI stances; names `SourceReportedContradiction`, `source_reported_contradictions` and the isolated payload keys exempt; source values such as `CONTRADICTORY_MOMENTUM` are data, not new names |
| E5 | §12 AT-PRIV-2 (C-2) | no C15 field name contains `support` or `contradict` | name scan finds them only in the exempt names; no score or decision authority |
| E6 | §18 | — | this table |

**Not changed.** Phase 1 is a partial milestone; C15 stays OPEN; C16 is not authorized; P1/P2/P3 are inactive; no `SUPPORT` or `CONTRADICT` role; no score, probability or forecast; no Strategy or Risk interface; `news_claims` excluded; no new ETF freshness policy; wallet references privacy-preserving; U2 separate. AT-NOPRED-1 is unchanged. The canonical Exit Gate and Closure Rule are untouched. Sections §1, §14, §15, §16 and §17 remain v3.1/v3.2 history.

**Honest limits of this edit.** v3.3 was written by the implementer and has not been audited by Codex. The Slice 1 serializer and Slice 2 models (commit `50ce584`) need no change.

---

## 19. SLICE_3_IDENTITY_AMENDMENT [v3.4: OWNER-APPROVED, BOUNDED]

This section was independently audited (PASS) and approved by the owner on 2026-11-12, bounded to the scope listed in the v3.4 note and §19.1. It is binding for those items only. Items it defers (§19.1, §19.11) remain deferred and unapproved, and it authorizes no implementation.

### 19.1 Scope of the amendment

- **Applies to** exactly three identifiers: `series_id`, `slot_id` and `exposed_content_id`, and to the typed inputs they need (`SeriesKey`, `Slot`, and the ordering rule for `MetricObservation` tuples). It uses the existing Slice 2 `Coverage`, `MetricObservation`, `MetricState`, `Basis` and `UtcDatetime` unchanged.
- **Tags and prefixes are unchanged from v3.3 §3.2:** `sr1:` with `c15.series.v1`, `sl1:` with `c15.slot.v1`, `xc1:` with `c15.xc.v1`.
- **Not frozen by this amendment:** `input_set_id`, `observation_id`, `methodology_id`, `assessment_id`, `Delivery`, `InputSetRef`, `Methodology`, `EvidenceUnit`, source adapters and `fuse()`. Their v3.3 text is unchanged and still [P]. Delivery needs an amendment of the L5 row and the `input_set_id` formula before it can be pinned. Methodology needs a type policy for config values (for example `timedelta` in `FlowConfig`, and `OrderRequest` tuples in `LiquidityConfig`). `assessment_id` needs an authoritative `ac_id`.
- **The ETF and FOMC rows of §3.7 are not removed from the C15 contract.** They are excluded from the Slice 3 implementation only. Their series keys remain an open contract item (§19.11).

### 19.2 SeriesKey

`SeriesKey` has exactly six fields, all always present: `kind`, `section`, `symbol`, `interval`, `source`, `qualifier`. `kind` and `section` are required text. The other four are text or `None`. Text is non-empty with no leading or trailing whitespace, and is never stripped or coerced.

**Dotted-token mapping.** v3.3 §3.7 writes a series key as a dotted token plus members, for example `{LIQ.book, symbol, source}`. This amendment reads the token as `kind.section`: `LIQ.book` gives `kind="LIQ"` and `section="book"`. A member that is none of `symbol`, `interval` or `source` goes into `qualifier`. At most one such member exists per row. Fields a row does not list are `None`.

| §3.7 row | kind | section | symbol | interval | source | qualifier | Notes |
|---|---|---|---|---|---|---|---|
| C07 book | `LIQ` | `book` | listed | `None` | listed | `None` | |
| C08 flow | `FLOW` | `window` | listed | `None` | listed | `None` | source is not exposed when provenance is absent |
| C09 candles | `DER` | `candles` | listed | `"1h"` | listed | `None` | same limit |
| C09 funding | `DER` | `funding` | listed | `"1h"` | listed | `None` | same limit |
| C10 dimension | `REGIME` | `dim` | listed | `None` | `None` | the dimension name | |
| C11 wallet | `WHALE` | `wallet` | `None` | `None` | `None` | `wallet_ref` | **No value may be produced.** The `wr1:` reference rule is not approved (§9 of v3.3). |
| C12 series | `MACRO` | `series` | `None` | `None` | `None` | the source series id | |
| C13 result | `NEWS` | `result` | `None` | `None` | `None` | `None` | |
| C12 FOMC, C12 ETF metric | not mapped by this amendment | | | | | | v3.3 §3.7 incorporates the v2 mapping by reference; it needs a self-contained, reviewed definition before adapter implementation (§19.11) |
| C09 open interest, basis | none | | | | | | no observation (v3.3 §3.4) |
| C14 | not registered as an observation | | | | | | v3.3 §3.7 |

This table defines the structural vocabulary only. It does **not** verify that any source field can fill a given member. That verification belongs to the adapter slices.

### 19.3 Slot

A `Slot` has `series_key: SeriesKey` and `slot_time`, which is exactly one of four tagged forms. The tag field is `form`. Fields are named; no positional tuple is used.

| Form | Fields | Intended use (informational) |
|---|---|---|
| `INSTANT` | `at` | C07 `snapshot_timestamp`, C09 `latest_start` |
| `WINDOW_SESSION` | `window_start`, `session_start` | C08 |
| `REFERENCE_PERIOD` | `period` | C12 series `reference_period` |
| `CLAIM_ID` | `claim_id` | C13 |

- Datetime fields use `UtcDatetime` unchanged (Slice 2 behavior): strict ISO text (at most six fractional digits, `Z` or `±HH:MM`, matched with `fullmatch`) and datetime objects are admitted and normalized to UTC.
- `period` is non-empty text with no padding, and is never parsed. `claim_id` is 64 lowercase hexadecimal characters. Neither is coerced into the other form.
- Slot times for C10, C11 and C12 FOMC/ETF are not specified by this amendment.

### 19.4 Metric ordering

The L4 `metrics` value is an **ordered tuple of `MetricObservation`**. The tuple must be in ascending order by `(name, window_id)`, where names compare by Python string order and a `window_id` of `None` sorts before any text. A duplicate `(name, window_id)` pair is rejected. An unsorted tuple is rejected. Nothing is sorted, merged or dropped silently. An empty tuple is allowed.

An ordered tuple and `Unordered` produce different digests, so they are not interchangeable (verified, §19.7). This amendment selects the ordered tuple.

### 19.5 Projection rules

- **R1.** Each projection is plain data built by an explicit function. It is not a `model_dump`.
- **R2.** Every projection has a fixed key set. All keys are present. An absent value is `None`. Omitting a key is not allowed, because `None` and omission give different digests.
- **R3.** Enum members are passed as their string `.value`, never as enum objects, so an identity does not depend on a Python module path. The `Basis` and `MetricState` values are plain strings.
- **R4.** Datetimes are UTC `datetime` objects. Decimals are exact `Decimal` objects, and floats are rejected. Integers are `int`. The Decimal spelling does not matter: `1.5` and `1.50` give the same digest (§4).
- **R5.** Sequences are ordered tuples unless §19.4 or another clause says otherwise. `Unordered` is not used in this amendment.
- **R6.** Duplicates are rejected by the model, never deduplicated.
- **R7.** A nested object is projected as a full nested dict. The slot embeds the six-key series dict, not `series_id`.
- **R8.** `HID(tag, v) = id_digest(tag, v)` as in §4.4. The serializer encodes `v` and then the envelope a second time, so independent reproduction needs the §4 encoder.

### 19.6 Exact projections

| Id | Value passed to `id_digest` |
|---|---|
| `series_id` = `"sr1:"` + `HID("c15.series.v1", K)` | `K = {"kind", "section", "symbol", "interval", "source", "qualifier"}` |
| `slot_id` = `"sl1:"` + `HID("c15.slot.v1", {"series_key": K, "slot_time": S})` | `S` is one of the four forms below |
| `S` for `INSTANT` | `{"form": "INSTANT", "at": datetime}` |
| `S` for `WINDOW_SESSION` | `{"form": "WINDOW_SESSION", "window_start": datetime, "session_start": datetime}` |
| `S` for `REFERENCE_PERIOD` | `{"form": "REFERENCE_PERIOD", "period": text}` |
| `S` for `CLAIM_ID` | `{"form": "CLAIM_ID", "claim_id": text}` |
| `exposed_content_id` = `"xc1:"` + `HID("c15.xc.v1", X)` | `X = {"slot": slot_id, "coverage": C, "metrics": M, "basis": text}` |

- `C = {"earliest_time", "latest_time", "contributing_count", "interval"}`: always four keys, `None` where unknown.
- `M` is an ordered tuple (§19.4) of `{"name", "state", "value", "unit", "window_id", "reason"}`, with `state` as a string, `value` as `Decimal` or `None`, and the rest as text or `None`.
- `basis` is the string value of `Basis`.
- L5 (including `delivery`) is excluded from `exposed_content_id`, as in v3.3 §3.2.

### 19.7 Golden vectors

Computed by the repository serializer on `main` at `3c088a9` in a scratch run. They are **structural encoding fixtures**. They are not valid source mappings: the key `{DER, candles, BTC-PERP, 1h, hyperliquid, None}` is a fixture and does not claim that any C09 field produces it.

Fixture key `K` is `kind="DER"`, `section="candles"`, `symbol="BTC-PERP"`, `interval="1h"`, `source="hyperliquid"`, `qualifier=None`. Its `ID_JSON` is:

`{"$":"map","v":[["interval","1h"],["kind","DER"],["qualifier",null],["section","candles"],["source","hyperliquid"],["symbol","BTC-PERP"]]}`

| Case | Input | Expected id |
|---|---|---|
| `series_id` | `K` | `sr1:a8eb04b981cbb2c036eb5404486b9e7a5d88f2fcf6cafd0d33e59918a80e30ae` |
| `slot_id`, `INSTANT` | `at = 2026-01-01T12:00:00Z` | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` |
| `slot_id`, `WINDOW_SESSION` | `window_start = 2026-01-01T11:00:00Z`, `session_start = 2026-01-01T00:00:00Z` | `sl1:8d6cb6ced1c83e0dcee39e1ac2c22a30969e34efa160e32e43b71f15f7c56d56` |
| `slot_id`, `REFERENCE_PERIOD` | `period = "2025-12"` | `sl1:588aeede2aa7f97416c7641d32c6afe2ba83ff3199b41cc6a425e8f6b9915ffa` |
| `slot_id`, `CLAIM_ID` | `claim_id = "a"` repeated 64 times | `sl1:d4a37999a079b19e2715833cdc6a33d400cd332fcd872fffa9b7420fe0f330bc` |
| `exposed_content_id` | the `INSTANT` slot above; coverage `{earliest_time 2026-01-01T07:00:00Z, latest_time 2026-01-01T12:00:00Z, contributing_count 6, interval "1h"}`; basis `EXPOSED_FIELDS`; metrics below | `xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14` |
| `exposed_content_id`, empty | the same slot; coverage with four `None`; no metrics; basis `NO_OBSERVATION` | `xc1:8f19c767a2eff3fd1a93ffbf19b5662ed8608ad84426d213c35fba39ce296a2b` |

Metrics for the `exposed_content_id` row, in this order: `{name "atr", state "PRESENT", value Decimal("1.50"), unit "USD", window_id "atr:2:2026-01-01T12:00:00Z", reason None}` and `{name "vwap", state "WITHHELD", value None, unit "USD", window_id None, reason "UNTRUSTED"}`.

`ID_JSON` of that `exposed_content_id` input:

`{"$":"map","v":[["basis","EXPOSED_FIELDS"],["coverage",{"$":"map","v":[["contributing_count",{"$":"int","v":"6"}],["earliest_time",{"$":"dt","v":"2026-01-01T07:00:00.000000Z"}],["interval","1h"],["latest_time",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}]]}],["metrics",{"$":"seq","v":[{"$":"map","v":[["name","atr"],["reason",null],["state","PRESENT"],["unit","USD"],["value",{"$":"dec","v":"15e-1"}],["window_id","atr:2:2026-01-01T12:00:00Z"]]},{"$":"map","v":[["name","vwap"],["reason","UNTRUSTED"],["state","WITHHELD"],["unit","USD"],["value",null],["window_id",null]]}]}],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"]]}`

Verified behaviors (scratch probes, serializer at `3c088a9`):
- The same `exposed_content_id` input with `Decimal("1.5")` instead of `Decimal("1.50")` gives the same id.
- Passing the `Basis` enum object instead of its string gives a different digest.
- An ordered tuple and `Unordered` over the same metric dicts give different digests, and reversing the tuple changes its digest.
- `None` and an omitted key give different digests, and a list and a tuple give the same digest.

### 19.8 Deliberate departures from v3.3

| # | v3.3 | v3.4 |
|---|---|---|
| P1 | L1 key is `{kind, symbol, interval, source, section}`, while §3.7 uses dotted tokens and extra members (`dimension`, `wallet_ref`, `series_id`) | Six-field `SeriesKey`, explicit dotted-token split, one `qualifier` field (§19.2) |
| P2 | L2 `slot_time` written as a bare value or a positional pair | Four tagged forms with named fields (§19.3) |
| P3 | L4 "tuple of `MetricObservation`" with no ordering rule | Ascending `(name, window_id)` order, duplicates and unsorted input rejected (§19.4) |
| P4 | Projection types not stated | Enums as strings, datetimes as UTC objects, fixed key sets with nulls (§19.5) |
| P5 | L3 coverage "where exposed" | Always four keys, `None` where not exposed (§19.6) |
| P6 | `slot_id = HID("c15.slot.v1", slot)` with `slot` described as `series_key` plus `slot_time` | Stated exactly: the slot embeds the six-key dict, not `series_id` (§19.6) |

### 19.9 Implementation scope boundaries (for a later implementation authorization)

- **Allowed:** one new module under `src/traid/fusion/` with `SeriesKey`, `Slot` and its four forms, and the three functions; one new test file; additive exports in `src/traid/fusion/__init__.py`. File names are to be fixed in the implementation authorization.
- **Required tests:** the golden vectors above; sensitivity (`series_id` ignores the slot time, `slot_id` ignores coverage and metrics, and a coverage or metric change moves `exposed_content_id`); rejection of unsorted or duplicate metrics, a malformed `claim_id`, a float and a padded text; a string basis versus an enum basis; the Slice 2 name scan and import-purity rules; and the Slice 1 and Slice 2 regressions.
- **Prohibited:** `Delivery`, `InputSetRef`, `Methodology`, `input_set_id`, `observation_id`, `methodology_id`, `assessment_id`, `EvidenceUnit`, source adapters, relations, lineage, `fuse()`, wallet references, ETF and FOMC mappings, roles other than the five of §10, any score, probability or forecast, any AI-derived input, any change to `serialization.py` or to `UtcDatetime`, and C16.

### 19.10 Owner approval checklist

- [x] Approve the six-field `SeriesKey` and the dotted-token split (§19.2).
- [x] Approve the four `Slot` forms with named fields (§19.3).
- [x] Approve the sorted ordered metrics tuple, with rejection of unsorted and duplicate input (§19.4), over `Unordered`.
- [x] Approve string enum projections and the fixed null key sets (§19.5).
- [x] Approve the exact projections and the golden vectors (§19.6 and §19.7).
- [x] Confirm that ETF and FOMC are excluded from Slice 3 implementation only, and not from the contract.
- [x] Confirm that `Delivery`, `InputSetRef`, `Methodology`, their ids and `assessment_id` stay deferred.
- [x] Approve the contract route: this file as v3.4 after independent audit, and an owner-approved update of the Spec §7 pointer (done in the activation change).
- [ ] Authorize the implementation scope of §19.9 in a separate task.

### 19.11 Unresolved contract issues

- **FOMC and ETF series keys:** v3.3 §3.7 incorporates the v2 mapping by reference ("per v2 §4, unchanged"). That inherited mapping needs a self-contained, reviewed definition before adapter implementation. For ETF, the asset may map to `symbol` and the metric may map to `qualifier`, subject to owner approval; two discriminators do not by themselves require two qualifier fields. Fund-ticker granularity is a separate unresolved decision.
- **Missing `source`:** C08 and C09 expose `source` only through provenance, which may be absent. A key built without it would be a different key, so an adapter rule is needed.
- **Slot times** for C10, C11 and C12 FOMC are not defined by this amendment, and the C12 series `reference_period` may be `None`. For C10, the inherited contract (v3.3 §3.7) specifies the newest `SourceRef.source_timestamp`, but the actual C10 model exposes `newest_provenance` (`regime/engine.py:274`), not a direct `source_timestamp`. The exact source path and the missing-value behavior require verification before adapter implementation.
- **Wallet references:** `wr1:` remains unapproved, so no C11 key may be produced.
- **L5 and Delivery:** the open `...` tail of the v3.3 `delivery` object and the four delivery states (complete, newest-record-only, unavailable, known-empty) need an amendment before `input_set_id` can be pinned. C08 `provenance=None` conflates "no retained trade" with "integrity failed", so it cannot be read as known-empty.
- **Methodology:** a type policy for nested or typed config values is needed (see §19.1).
- **`ac_id`:** no formula, tag or prefix exists (v3.3 §3.2 and R3a).
- **`coverage_id` and `metrics_id`:** appear only in the §3.2 "Hashed into" column and are treated here as unresolved notation, not as required identities.

---

## 20. CHANGES_V3_3_TO_V3_4

Exactly these clauses change. Everything else is carried over from v3.3 unchanged.

| # | Clause | v3.3 | v3.4 |
|---|---|---|---|
| F1 | Title, version identifier, v3.4 note | `v3.3` | `v3.4`, derived from v3.3 and approved |
| F2 | §3.2 L1 row | five-key `series_key` | pointer to the six-field `SeriesKey` (§19.2) |
| F3 | §3.2 L2 row | `slot_time` by source | pointer to the four Slot forms (§19.3) |
| F4 | §3.2 L4 row | tuple of `MetricObservation` | ordered, unique, ascending tuple (§19.4) |
| F5 | new §19 | none | Slice 3 identity amendment (approved, bounded) |
| F6 | new §20 | none | this table |

**Not changed.** Phase 1 is a partial milestone. C15 stays OPEN and C16 is not authorized. P1, P2 and P3 are inactive. `EvidenceRole` has exactly five members and there is no `SUPPORT`, `CONTRADICT` or `ELIGIBLE` role. There is no score, probability or forecast, no Strategy or Risk interface, `news_claims` is excluded, there is no new ETF freshness policy, wallet references stay privacy-preserving and unapproved, and U2 is separate. The Exit Gate and Closure Rule are untouched. v3.3 and v3.2 stay historical and unmodified, and the Spec §7 pointer now names v3.4.

**Honest limits of this contract.** It was written by the implementer (Claude Code), passed the independent Codex design audit, and received bounded owner approval on 2026-11-12. The golden vectors were produced by the repository serializer in a scratch run. They are not an independent reimplementation.

---

## 21. L5_INPUT_IDENTITY_AMENDMENT [v3.5: OWNER-APPROVED, BOUNDED; INDEPENDENT DESIGN AUDIT PASSED WITH CONDITIONS, EDITORIAL CORRECTIONS APPLIED]

This section was independently audited (PASS_WITH_CONDITIONS, with the editorial corrections since applied) and approved by the owner on 2026-11-13, bounded to the items listed in §21.1 and §21.12. It is binding for those items only. Items it defers (§21.11) remain deferred, and implementation needs a separate owner authorization (§21.10). The canonical Spec pointer names v3.5. Labels: **[F]** verified repository fact with a file reference, **[C]** requirement inherited from v3.4, **[P]** v3.5 design decision (owner-approved).

### 21.1 Scope

- **Applies to** exactly three items: the `Delivery` model, the `InputSetRef` model and the identifier `input_set_id`.
- **Tag and prefix are unchanged [C]:** `is1:` with `c15.is.v1` (v3.4 §3.2). The identifier is computed with the existing `id_digest` (§4.4). No new tag, prefix or hash is introduced.
- **Not in this amendment:** `observation_id` (it consumes `input_set_id` and is deferred to a later slice), `methodology_id`, `assessment_id`, `Methodology`, `EvidenceUnit`, source adapters, relations, lineage and `fuse()`. Their v3.4 text is unchanged and still [P].

### 21.2 Exact L5 amendment

The v3.4 L5 row reads: `input_set_ref` = `{digest: [algorithm, sha256] or null, delivery: {source_type, source_id, received_timestamp, ...}}`, receipt-sensitive, hashed into `input_set_id`.

**Replacement of the content cell:** `input_set_ref` is an `InputSetRef` (§21.4): exactly the three fields `state`, `digest` and `delivery`, where `digest` is `null` or the ordered pair `(algorithm, digest)` and `delivery` is `null` or a `Delivery` (§21.3). The open `...` tail is closed: a `Delivery` has exactly five fields. The receipt-sensitivity column (**yes**) and the hashed-into column (`input_set_id`) are unchanged. The formula `input_set_id = "is1:" + HID("c15.is.v1", input_set_ref)` is unchanged, with `input_set_ref` read as the projection of §21.5.

### 21.3 Delivery

`Delivery` is a frozen model that rejects unknown fields. It has exactly five fields, which are the five fields of `SourceProvenance` **[F]** (`src/traid/domain/models.py:83-93`).

| Field | Type | Rule |
|---|---|---|
| `source` | `Text` | non-empty, no leading or trailing whitespace; never stripped or coerced |
| `source_type` | `Text` | same |
| `source_id` | `Text` or `None` | same when present; `None` is explicit |
| `source_timestamp` | `UtcDatetime` or `None` | Slice 2 admission policy unchanged: strict ISO text or a datetime object, aware, accepted time-zone types only, normalized to UTC; `None` is explicit |
| `received_timestamp` | `UtcDatetime` | required; same policy |

- **Ordering invariant [F/P]:** when `source_timestamp` is not `None`, `received_timestamp` must not precede it. This copies the upstream rule (`domain/models.py:92-93`) and is a structural check only.
- **No other source field is carried.** For example, `FlowProvenance.source_types` and the contributing counts are not part of `Delivery`.
- **No inference.** `source_id` and `source_timestamp` are never derived or defaulted.

### 21.4 InputSetRef

`InputSetRef` is a closed tagged union. The tag is the string field `state`. It has exactly three fields: `state`, `digest` and `delivery`. The `digest`, when present, is validated like the existing `InputDigestRef` **[F]** (`src/traid/fusion/models.py:143-145`): a non-empty unpadded `algorithm` text and a `digest` of 64 lowercase hexadecimal characters.

| State | `digest` | `delivery` | Contract status | Production-constructible (initial implementation) |
|---|---|---|---|---|
| `COMPLETE_SINGLE` | must be `None` | required | defined | **yes** |
| `DIGEST_WITH_NEWEST` | required | required | defined | **yes** |
| `UNAVAILABLE` | must be `None` | must be `None` | defined | **yes** |
| `KNOWN_EMPTY` | must be `None` | must be `None` | **reserved** | **no** |

- **Strict presence rules.** A combination not in the table is rejected. There is no default state and no state inference from which fields are present.
- **Reserved is not constructible.** `KNOWN_EMPTY` has a pinned projection and a pinned fixture (§21.8) so that its identity is fixed if it is ever enabled. In the initial implementation no public model, constructor, factory or function parameter may accept or produce the state `KNOWN_EMPTY`, and no adapter may emit it. A test must prove the rejection. Enabling it needs a separate owner decision, a source-evidence rule and a contract amendment.
- **`COMPLETE_SINGLE` and completeness.** `COMPLETE_SINGLE` means only: the source model exposes exactly one delivery for this input, and C15 holds no evidence of another delivery. It does **not** claim that the source retained no other record, that the delivery is the only receipt of the underlying observation, or that C15 verified the content. Using it for a source that exposes more than one known receipt would overstate completeness and is prohibited (see C12 in §21.7).
- **`DIGEST_WITH_NEWEST`** means: a source digest over the retained records, plus the delivery of the newest retained record only. The delivery is not a claim about the other records. A digest and a delivery may intentionally appear together; both are preserved in the projection.
- **`UNAVAILABLE`** means: no input identity was observable by C15. It is not a claim of emptiness (§21.6).
- **Observed versus unavailable.** `COMPLETE_SINGLE` and `DIGEST_WITH_NEWEST` carry observed input identity. `UNAVAILABLE` carries none, and `KNOWN_EMPTY` (reserved) would carry a positive statement of emptiness that no currently approved source-evidence rule authorizes.

### 21.5 Canonical `input_set_id` projection

`input_set_id = "is1:" + HID("c15.is.v1", P)`, where `HID(tag, v) = id_digest(tag, v)` (§4.4). `P` is plain data built by an explicit function, not a `model_dump` (§19.5 R1). Rules R2 to R8 of §19.5 apply. `P` has exactly three keys, always present:

```
P = {"state": <string>, "digest": <null | (algorithm, digest)>, "delivery": <null | D>}
D = {"source": <text>, "source_type": <text>, "source_id": <text | null>,
     "source_timestamp": <UTC datetime | null>, "received_timestamp": <UTC datetime>}
```

- **`state`:** the plain string value, for example `"DIGEST_WITH_NEWEST"`. Never an enum object, which would add a module-qualified class key to the encoding (§19.5 R3).
- **`digest`:** `None`, or an **ordered two-element sequence** `(algorithm, digest)`, algorithm first. A tuple and a list encode identically. A named mapping would encode differently and is not allowed.
- **`delivery`:** `None`, or a mapping `D` with exactly the five keys above. Absent values are explicit `None`. A key is never omitted, because `None` and omission hash differently.
- **Timestamps:** UTC `datetime` objects. The serializer encodes the instant, so the same instant in another zone gives the same identifier.
- **No other key** (no reason, count, source type list or timing summary) enters `P`.
- **L5 exclusion:** none of this enters `exposed_content_id` (§3.2, §19.6).

**What changes `input_set_id`:** the state, the algorithm, the digest, and each of the five delivery fields, including `None` versus a value. **What does not:** the slot, the coverage, the metrics, and the spelling of a time zone.

### 21.6 UNAVAILABLE identity and limits

- Every `UNAVAILABLE` reference has the same projection, `{"state": "UNAVAILABLE", "digest": null, "delivery": null}`. **Identical `UNAVAILABLE` references therefore share one `input_set_id`**, across every source, slot and time.
- **Equality of `UNAVAILABLE` identifiers does NOT prove:** identical actual inputs; shared source provenance; the same cause of unavailability (no retained record, a failed integrity check and a source outage look alike); verified emptiness; or equal content of anything.
- **No reason code is hashed.** A reason belongs to the assessment content (v3.4 §3.2, L7), not to input identity.
- **`input_set_id` is never used alone.** Only a later `observation_id` pairs it with a slot. Equality of `input_set_id` alone must never establish shared input lineage, a shared source or equivalence of the underlying data, for any state. Lineage and shared-input relations remain governed by §5.1 families C and D, which read the digest, algorithm and section kind directly. Two references with the same digest can have different `input_set_id` values if their delivery differs, so a relation must read the `digest` field and never infer a shared input from `input_set_id`.
- **`KNOWN_EMPTY` (reserved)** would be a positive claim. No approved source-evidence rule currently authorizes `KNOWN_EMPTY`; `KNOWN_EMPTY` stays contract-reserved and excluded from the initial production API. The only source fact reviewed is that the C08 comment at `src/traid/flow/analytics.py:135` says `provenance` is `None` both when no retained trade existed and when input integrity failed first **[F]**, so `UNAVAILABLE` is the only honest state for those cases.

#### Receipt sensitivity and the digest/delivery redundancy

- **[F] What a source digest covers.** The C08 digest hashes, per retained trade, the source, source type, source id, source timestamp, receipt timestamp, side, price and size (`src/traid/flow/analytics.py:189-195`). The C09 candle and funding digests hash the same provenance fields per record (`src/traid/derivatives/analytics.py:424-426` and `:542-544`). So an equal digest implies equal per-record receipt metadata for those sources, which matches v3.4 §3.1 principle 2.
- **What the delivery adds.** The newest record's delivery makes that record addressable and keeps a receipt-only change visible when only the delivery is compared. When the source is consistent it carries no information beyond the digest.
- **The redundancy is intentional and not harmful [P].** Different digests already give different identifiers. If a source ever paired one digest with two different newest deliveries, including the delivery makes that inconsistency show as different identifiers instead of silently equal. C15 does not verify that a digest matches the content behind it (v3.4 §3.2).
- **The algorithm is always part of the identity,** because an equal digest is meaningful only under an equal algorithm (v3.4 §5.1 family C).

### 21.7 Source compatibility and exclusions

This table defines the structural vocabulary only. It does **not** verify that an adapter can fill it, and it creates no adapter. Status: **V** verified in the repository (reference given), **U** unverified, an adapter must verify it.

| Source | Mapping | Status |
|---|---|---|
| C07 book | `COMPLETE_SINGLE`: delivery from the single non-optional `provenance`; no digest | **V** `src/traid/liquidity/analytics.py:132-136` |
| C08 flow | `DIGEST_WITH_NEWEST`: digest `(digest_algorithm, input_digest)` and delivery from `newest_trade_provenance`. When `provenance` is `None`: `UNAVAILABLE`, never `KNOWN_EMPTY` | **V** `src/traid/flow/analytics.py:114-135` |
| C09 candles and funding | `DIGEST_WITH_NEWEST` per section: digest `(digest_algorithm, input_digest)` and delivery from `newest_record_provenance`. When the section `provenance` is `None`: `UNAVAILABLE` | **V** `src/traid/derivatives/analytics.py:138-147`, `:399`, `:521` |
| C11 wallet | `COMPLETE_SINGLE` from a snapshot `provenance`; no snapshot: `UNAVAILABLE`. No C11 observation may be produced anyway, because `wr1:` is unapproved | **V** `src/traid/whales/models.py:156-166` and `src/traid/whales/analytics.py:359`; **U** whether the report-level mapping is snapshot-level |
| C13 result | `UNAVAILABLE` is a candidate: the contract says the digest is null and the result does not expose the claim source. The result's own `input_digest` stays in the assessment content (v3.4 §7). C13 may expose nested official-evidence provenance through `identity_evidence` (`src/traid/news/models.py:583`, `:705`), but that does not establish claim-source provenance or complete input-set provenance, and no input-set identity is inferred from it. C13 stays excluded from approved Slice 4 source mappings | **U** whether any claim-source delivery is exposed by the C13 result; owner confirmation needed |
| C10 dimension | **deferred (composite input)** | see below |
| C12 series | **deferred (selected capture)** | see below |
| C12 FOMC and ETF, C14 | not mapped | v3.4 §19.2 and §3.7 |

- **C10 is excluded from this amendment.** One C10 dimension carries a tuple of up to four `SourceRef` inputs (`src/traid/regime/engine.py:308`), and `InputSetRef` holds a single digest and a single delivery. A composite design is a later decision. A C10 `SourceRef` has a nullable digest and a separately supplied newest provenance (`src/traid/regime/engine.py:263-274`, `:474-485`). Whether a digest can occur without a newest provenance is **U**.
- **C12 series is excluded.** The series `provenance` is the chosen known capture (`src/traid/macro/evidence.py:142`), while other known receipts exist in `revisions` and `conflicting_receipts`. `COMPLETE_SINGLE` would overstate completeness, and `SELECTED_DELIVERY` is deliberately **not** introduced in this amendment. The report-level `input_digest` (`src/traid/macro/evidence.py:194`) is not per series and is not mapped.
- **Other unverified claims.** (a) Whether C09's `input_count` could support a future `KNOWN_EMPTY` rule (`src/traid/derivatives/analytics.py:160`). (b) Whether a C08 or C09 section with one retained record needs a different state (this amendment keeps `DIGEST_WITH_NEWEST`, which is harmless because the state follows the presence of fields, not a count).

### 21.8 Golden vectors and full ID_JSON fixtures

**Status.** Computed by the repository serializer (`id_digest`, `id_json`) on `main` at `60983aa` in a scratch run. They are **structural encoding fixtures**. They are not source mappings: the algorithm `sha256-canonical-candles-v1` and the delivery values below are fixtures and do not claim that any source produces them. The four state identifiers were additionally recomputed by hashing the §4.4 envelope directly, `sha256(ID_JSON({"tag": "c15.is.v1", "v": ID_ENC(P)}))`, with the same result. That is a recomputation through the same encoder, not an independent reimplementation of §4. Every `ID_JSON` string below is complete and byte-exact (it contains no abbreviation), and it is `ID_JSON(P)` as in §19.7. Independent reproduction needs the §4 encoder.

**Fixture inputs.**
- Delivery fixture `D0`: `source = "hyperliquid"`, `source_type = "REST"`, `source_id = "book-1"`, `source_timestamp = 2026-01-01T12:00:00Z`, `received_timestamp = 2026-01-01T12:00:01Z`.
- Digest fixture `G0`: `algorithm = "sha256-canonical-candles-v1"`, `digest` = the character `b` repeated 64 times (`bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb`).

| Vector | `state` | `digest` | `delivery` | `input_set_id` |
|---|---|---|---|---|
| V1 | `COMPLETE_SINGLE` | `None` | `D0` | `is1:71ae34903b46b3741b7c856c674db3997ac7d433602487a8b5c353e390e59320` |
| V2 | `DIGEST_WITH_NEWEST` | `(G0.algorithm, G0.digest)` | `D0` | `is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b` |
| V3 | `UNAVAILABLE` | `None` | `None` | `is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb` |
| V4 (reserved fixture, not reachable through the production API) | `KNOWN_EMPTY` | `None` | `None` | `is1:cb2e6ddeafe7c39450cfb3cf9d78f6c40893a2527dc8fb2e56d682b2d909b6ab` |

**`ID_JSON(P)` for V1:**

`{"$":"map","v":[["delivery",{"$":"map","v":[["received_timestamp",{"$":"dt","v":"2026-01-01T12:00:01.000000Z"}],["source","hyperliquid"],["source_id","book-1"],["source_timestamp",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}],["source_type","REST"]]}],["digest",null],["state","COMPLETE_SINGLE"]]}`

**`ID_JSON(P)` for V2:**

`{"$":"map","v":[["delivery",{"$":"map","v":[["received_timestamp",{"$":"dt","v":"2026-01-01T12:00:01.000000Z"}],["source","hyperliquid"],["source_id","book-1"],["source_timestamp",{"$":"dt","v":"2026-01-01T12:00:00.000000Z"}],["source_type","REST"]]}],["digest",{"$":"seq","v":["sha256-canonical-candles-v1","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]}],["state","DIGEST_WITH_NEWEST"]]}`

**`ID_JSON(P)` for V3:**

`{"$":"map","v":[["delivery",null],["digest",null],["state","UNAVAILABLE"]]}`

**`ID_JSON(P)` for V4 (reserved fixture):**

`{"$":"map","v":[["delivery",null],["digest",null],["state","KNOWN_EMPTY"]]}`

**Sensitivity vectors.** Each differs from V2 in exactly one respect and gives a different identifier:

| Vector | Change from V2 | `input_set_id` |
|---|---|---|
| S1 | `received_timestamp = 2026-01-01T12:00:02Z` | `is1:033dbc5e0d778620c89ae961ac828edc98e765bec2449916a64c864bc99194dc` |
| S2 | `source_timestamp = None` | `is1:fcb087cf940e56f83823a53f2b3ccb2c01f3ca1442a984ef61b6207ece15b0f9` |
| S3 | `source_id = None` | `is1:91df3539e71cbbccfc9fa4eb9e351b901dd4d3cd655e1c2537ad85a5df24f42b` |
| S4 | `algorithm = "sha256-canonical-funding-v1"` | `is1:481fac8425c0a8db3a421eb846a9a9053bc17639f64627e77623089dab876464` |
| S5 | `digest` = the character `c` repeated 64 times | `is1:3fc84508b950946469f7bcd7bf3008ccad22ffa7b296ba3c566919c206cb964b` |

`ID_JSON(P)` for each sensitivity vector is the V2 string with only the named value changed (a timestamp or the `null`/value at the named key, the algorithm string, or the digest string); it is not repeated here.

**Required behavioral tests (when implemented):**
- V1 to V4 and S1 to S5 reproduce the pinned identifiers; the four state identifiers are pairwise distinct; `UNAVAILABLE` and `KNOWN_EMPTY` differ on `state` alone.
- The same instant in another zone (`2026-01-01T13:00:01+01:00`) gives V2.
- A digest given as a list gives V2; a named-mapping digest gives a different identifier; an omitted key gives a different identifier.
- Rejected: a digest in `COMPLETE_SINGLE`; a missing digest or delivery in `DIGEST_WITH_NEWEST`; a delivery or digest in `UNAVAILABLE`; any attempt to build `KNOWN_EMPTY` through the production API; a malformed digest (length, uppercase, whitespace); a padded or empty text; a naive, malformed or non-UTC-admissible timestamp; a `received_timestamp` before `source_timestamp`; a float; an unknown field; a mutated frozen model; a forged `model_construct` instance.
- Equal `input_set_id` is never accepted by any function as evidence of lineage (no such function exists in this slice).

### 21.9 Deliberate departures from v3.4

| # | v3.4 | v3.5 |
|---|---|---|
| D1 | L5 is `{digest, delivery: {source_type, source_id, received_timestamp, ...}}`, with an open tail | `Delivery` is closed at five fields, adding `source` and `source_timestamp` (§21.3) |
| D2 | L5 has no state | L5 carries a `state` field so that the absent states cannot collide (§21.4, §21.5) |
| D3 | L5 allows `digest` to be absent and `delivery` to be present (C07, C11) and says nothing about the other combinations | four states with strict presence rules; unlisted combinations rejected |
| D4 | none | `KNOWN_EMPTY` is reserved and not production-constructible |
| D5 | v3.4 §19.9 prohibits `Delivery`, `InputSetRef` and `input_set_id` | lifted for those three items only, now that this amendment is approved, and only after a separate implementation authorization is given (§21.10) |
| D6 | §3.7 L5 column for C07, C08, C09, C11, C13 (partly informal) | the mappings of §21.7; C10 and C12 left as in v3.4 and marked deferred |

### 21.10 Implementation scope boundaries (binding once separately authorized)

- **Allowed (after a separate authorization):** the `Delivery` and `InputSetRef` models and the `input_set_id` function, in files fixed by that authorization; one new test file or a focused addition; additive exports; the per-file import-policy extension. `UtcDatetime`, `InputDigestRef` and the serializer are reused unchanged.
- **Prohibited:** `observation_id`, `methodology_id`, `assessment_id`, `Methodology`, `EvidenceUnit`, source adapters, any `KNOWN_EMPTY` construction path, `SELECTED_DELIVERY`, C10 composite and C12 capture mappings, relations, lineage, `fuse()`, wallet references, ETF and FOMC mappings, any role other than the five of §10, any score, probability or forecast, any change to `serialization.py`, `UtcDatetime` or the Slice 3 identifiers, and C16.

### 21.11 Deferred components

`observation_id`; `Methodology` and `methodology_id`; `assessment_id` and its `ac_id`; `coverage_id` and `metrics_id` notation; `EvidenceUnit`; source adapters; the C10 composite input; the C12 selected-capture input and `SELECTED_DELIVERY`; positive-emptiness evidence and the enabling of `KNOWN_EMPTY`; C12 FOMC and ETF keys; wallet references; relations, lineage and `fuse()`.

### 21.12 Owner approval checklist

- [x] Approve the five-field `Delivery` and its receipt-order invariant (§21.3).
- [x] Approve the four states (three constructible, one reserved) and the strict presence rules (§21.4).
- [x] Approve that `KNOWN_EMPTY` is reserved, pinned and not production-constructible (§21.4).
- [x] Approve the exact projection with the keys `state`, `digest`, `delivery` and the ordered digest pair (§21.5).
- [x] Approve the `UNAVAILABLE` limits and the rule that `input_set_id` equality never establishes lineage (§21.6).
- [x] Approve the intentional digest-and-delivery redundancy (§21.6).
- [x] Confirm that C10 composite inputs and C12 selected captures are deferred and `SELECTED_DELIVERY` is not introduced (§21.7).
- [ ] Decide whether the C13 candidate mapping `UNAVAILABLE` is acceptable or C13 stays unmapped (§21.7). **Not approved by the v3.5 approval: C13 stays unmapped and excluded from approved source mappings.**
- [x] Approve the golden vectors and full `ID_JSON` fixtures (§21.8).
- [x] Confirm that `observation_id`, `Methodology`, `EvidenceUnit`, adapters and C16 stay deferred (§21.11).
- [x] Approve the contract route: this file as v3.5 after independent audit, and an owner-approved update of the Spec §7 pointer (done in the activation change).
- [ ] Authorize the implementation scope of §21.10 in a separate task.

### 21.13 Unresolved issues and risks

- **C10 composite inputs.** A dimension has up to four `SourceRef` inputs, and this amendment cannot represent them. Until a composite design exists, no C10 adapter can fill L5.
- **C12 selected captures.** A series chooses one capture among several known receipts. Neither `COMPLETE_SINGLE` nor `DIGEST_WITH_NEWEST` fits honestly, and `SELECTED_DELIVERY` is deferred.
- **Unverified source claims (§21.7):** the C13 claim-source delivery exposure (nested `identity_evidence` is official-evidence provenance only and is not input-set provenance); the C11 snapshot-level mapping; whether a C10 digest can occur without a newest provenance; whether C09 `input_count` can support emptiness.
- **`KNOWN_EMPTY` has no producer.** It is reserved without any evidence rule, so a future enabling needs a source-evidence decision first.
- **`UNAVAILABLE` collapses causes.** Different failures share one identifier by design; the cause stays in the assessment content and must never be read from the identifier.
- **Receipt coverage is limited to the newest record** for C08 and C09 deliveries (v3.4 §6.4). The digest covers all retained records' receipt fields, but C15 cannot inspect them.
- **Digest-to-content consistency is not verified** by C15.
- **Name collision.** The C12 source field `series_id` (`src/traid/macro/evidence.py`) is a different thing from the C15 `series_id`. Adapters must not conflate them.
- **The golden vectors come from the repository serializer,** not from an independent reimplementation of §4.

---

## 22. CHANGES_V3_4_TO_V3_5

Exactly these clauses change. Everything else is carried over from v3.4 unchanged.

| # | Clause | v3.4 | v3.5 |
|---|---|---|---|
| G1 | Title, version identifier, v3.5 note | `v3.4` | `v3.5`, derived from v3.4 |
| G2 | §3.2 L5 row | open `delivery` object | pointer to the closed `InputSetRef` (§21) |
| G3 | new §21 | none | L5 input identity amendment (owner-approved, bounded) |
| G4 | new §22 | none | this table |

**Not changed.** v3.4 §19 (the Slice 3 identity amendment and its golden vectors) is untouched. Phase 1 is a partial milestone; C15 stays OPEN and C16 is not authorized. P1, P2 and P3 are inactive. `EvidenceRole` has exactly five members and there is no `SUPPORT`, `CONTRADICT` or `ELIGIBLE` role. There is no score, probability or forecast, no Strategy or Risk interface, `news_claims` is excluded, there is no new ETF freshness policy, wallet references stay privacy-preserving and unapproved, and U2 is separate. v3.4, v3.3 and v3.2 stay unmodified, and the Spec §7 pointer was updated from v3.4 to v3.5 in the activation change (a change outside this file).

**Honest limits of this contract.** It was written by the implementer (Claude Code), passed the independent Codex design audit with conditions (editorial corrections since applied), and received bounded owner approval on 2026-11-13. The golden vectors were produced by the repository serializer in a scratch run. They are not an independent reimplementation.

## 23. OBSERVATION_IDENTITY_AMENDMENT [v3.6: OWNER-APPROVED, BOUNDED; INDEPENDENT AUDIT FINAL_VERDICT: PASS]

This section was independently audited (Codex FINAL_VERDICT: PASS, after PASS_WITH_CONDITIONS conditions were applied) and its bounded design was approved by the owner on 2026-11-15. It is binding for the items in §23.13 only, and only at the contract level. **It does not authorize implementation**: a separate owner authorization is required (§23.12). It supersedes the `observation_id` restrictions in §19.9, §21.1, §21.10 and §21.11 for `observation_id` only (§23.2). Labels: **[F]** verified repository fact, **[C]** requirement inherited from v3.5, **[P]** v3.6 design decision (owner-approved).

### 23.1 Scope

This amendment covers `observation_id` only: its function signature, validation policy, canonical projection and golden vectors. It adds no model, enum, identity layer, serializer rule or source mapping. It consumes the three approved identifiers `slot_id` (§19), `exposed_content_id` (§19) and `input_set_id` (§21) through their existing typed functions **[F]** (`src/traid/fusion/identity.py:105-128`, `src/traid/fusion/input_identity.py:78-93`).

### 23.2 Exact amendment

- **Formula [C] (§3.2), preserved exactly:** `observation_id = "ob1:" + id_digest("c15.ob.v1", {"slot": slot_id, "xc": exposed_content_id, "is": input_set_id})`, where `id_digest(tag, v)` is the existing `HID` of §4.4 **[F]** (`src/traid/fusion/serialization.py`). The prefix `ob1:` and the tag `c15.ob.v1` are unchanged.
- **[P]** The three values are the string identifiers produced by `slot_id`, `exposed_content_id` and `input_set_id` for one supplied composition. They are never supplied by the caller (§23.3).
- **Restrictions superseded, for `observation_id` only [P]:** the owner approved this amendment on 2026-11-15. At the contract level, §23 supersedes the prohibition on `observation_id` in §19.9 and §21.10 and the deferral in §21.1 and §21.11, for `observation_id` only. Those sections still apply in full to every other item they list. The inherited text of those sections is not edited, and this bullet is the record of the supersession. **No implementation is authorized by this approval**: implementing `observation_id` needs a separate owner authorization (§23.12).

### 23.3 Typed composition API

```
observation_id(*, slot: Slot, coverage: Coverage, metrics: tuple[MetricObservation, ...],
               basis: Basis, input_set: InputSetRef) -> str
```

- **Keyword-only.** Positional arguments are rejected. The parameter names are `slot`, `coverage`, `metrics`, `basis` and `input_set`, and the first four are the arguments of `exposed_content_id` **[F]**.
- **Typed objects, never identifier strings.** There is no parameter that accepts a `sl1:`, `xc1:` or `is1:` string. A string, an identifier or any other wrong type is rejected by the existing function that consumes the argument. Cross-namespace substitution (an `xc1:` value where a slot is expected, and so on) is therefore not representable.
- **A composition of existing public APIs, with no outer validation wrapper.** `observation_id` is a plain function whose body calls `slot_id(slot)`, `exposed_content_id(slot=slot, coverage=coverage, metrics=metrics, basis=basis)` and `input_set_id(input_set)` **[F]** (`identity.py:105-128`, `input_identity.py:78-93`), passes each argument through unchanged, and hashes the three results. It preserves the validation and input-admission boundaries of those functions exactly, because each argument is validated only by the function that consumes it. It has **no** `validate_call` of its own and no generic validation layer.
- **Why no outer wrapper (verified by a read-only scratch probe that is not a repository test).** `exposed_content_id` guards `metrics` with an instance-only check (`_ordered_metrics`, `identity.py:86-96`) that runs before its own validation, so a dictionary entry is rejected. An outer strict `validate_call` annotated `metrics: tuple[MetricObservation, ...]` converts a dictionary entry into a `MetricObservation` before that guard runs, and would therefore **admit** metric dictionaries. This amendment forbids that. Metric dictionaries stay rejected.
- **Admission boundaries inherited from the three functions [F].** `slot`, `coverage` and `input_set` may be model instances or dictionaries that the existing functions admit and validate; `metrics` must be a `tuple` of `MetricObservation` instances (dictionary entries and lists are rejected); `basis` must be a `Basis` member (the text of a member is rejected). This admission design is an owner decision recorded in §23.13.
- **Positional arguments** are rejected by the keyword-only signature (a `TypeError`, not a validation error).
- **Reuse only.** `Slot`, `Coverage`, `MetricObservation`, `Basis` and `InputSetRef` are reused unchanged. `observation_id` does not change `serialization.py`, `UtcDatetime`, the Slice 3 identifiers or the Slice 4 identifiers.
- **Return value:** a `str` of the form `ob1:` followed by 64 lowercase hexadecimal characters.
- **Intended location (the file names are fixed by the later implementation authorization):** a new module `src/traid/fusion/observation_identity.py`, additive exports in `src/traid/fusion/__init__.py`, and one new test file.

### 23.4 Derivation and slot consistency

`exposed_content_id` embeds `slot_id(slot)` **[F]** (`identity.py:122`), so the slot enters `observation_id` twice, once as the `slot` key and once inside `xc`. This is intended and is not removed.

1. **One supplied slot, two derivations.** `slot_id(slot)` for the `slot` key and `exposed_content_id(slot=slot, coverage=coverage, metrics=metrics, basis=basis)` for the `xc` key are both computed from the single `slot` argument, and each call validates that argument itself. No second slot parameter exists, so a caller cannot supply a slot for the `slot` key that differs from the slot behind `xc`.
2. **No cross-slot pairing.** Because `xc` is derived inside the function from the same `slot`, an `xc` computed under another slot cannot be paired with this slot. A three-string signature could not prevent that, because `xc` is a hash and its preimage is not available (§23.7 rationale).
3. **Required tests.** A test must capture the projection passed to `id_digest` and assert that the `slot` key equals `slot_id(slot)`, that the `xc` key equals `exposed_content_id(slot=slot, coverage=coverage, metrics=metrics, basis=basis)` for that same `slot`, and that the `is` key equals `input_set_id(input_set)`. A second test must assert the semantic requirement below.
   **Slot sensitivity (exact requirement):** Changing only the Slot changes slot_id, exposed_content_id and observation_id; input_set_id remains unchanged.
4. **Equality statement.** Equal `observation_id` values establish equality of the canonical supplied projections `{"slot", "xc", "is"}` (§23.6), up to the collision resistance of the hash. The identifier alone cannot recover or validate its component preimages, and no function may try to. Equality does not prove raw-source identity, provenance correctness or shared lineage (§23.8).

### 23.5 Validation policy and fail-closed behavior

- **Any invalid component fails the whole call.** A malformed `Slot`, `Coverage`, `MetricObservation`, `Basis` or `InputSetRef`, unsorted or duplicate metrics (§19.4), a metric dictionary, a float, a padded text or a bad timestamp raises the error of the existing function that consumes it, before any hash of `P` is computed. No partial identifier is produced, no value is repaired, and no exception is caught and replaced by a default.
- **Prohibited coercion versus existing normalization.** The prohibition on repair and coercion does not exclude the normalization the existing approved APIs already perform, and this amendment adds none: accepted strict ISO timestamp text and aware datetimes are normalized to UTC by `UtcDatetime` (Slice 2 admission policy, §21.3), and a list digest is normalized to the ordered `(algorithm, digest)` pair by `InputSetRef` (`input_identity.py:46-50`), where that API supports it. No additional defaulting, coercion or repair is permitted, and no other value is converted, defaulted or trimmed. The existing model defaults stay supported: for example, an omitted optional `Coverage` field becomes `None` (`models.py`, `Coverage`), and `Coverage()` is valid with all four fields `None`. Existing accepted UTC normalization and existing digest-list normalization stay supported as stated above. This amendment introduces no new normalization, default or repair rule.
- **Forged models.** A model built with `model_construct`, edited with `object.__setattr__` or `__dict__`, or copied with `model_copy` and an update argument is revalidated before hashing, exactly as in Slices 3 and 4 **[F]**. A forged instance that violates a model rule is rejected.
- **`KNOWN_EMPTY`.** `InputSetRef` cannot hold the state `KNOWN_EMPTY` **[F]** (`input_identity.py:61`), and there is no string parameter that could carry the reserved identifier `is1:cb2e6ddeafe7c39450cfb3cf9d78f6c40893a2527dc8fb2e56d682b2d909b6ab`. A forged `InputSetRef` whose state is changed to `KNOWN_EMPTY` is rejected when `input_set_id` revalidates it. `observation_id` adds no `KNOWN_EMPTY` construction path, and a test must prove each of these rejections.
- **No new state.** `observation_id` adds no model and no enum, and no state field.
- **Determinism.** Dictionary order and the spelling of a time zone do not change the result, and the result is stable across processes and hash seeds.

### 23.6 Canonical projection

`observation_id = "ob1:" + id_digest("c15.ob.v1", P)`, where `P` is built by an explicit function and is plain data with exactly three keys, always present, each a plain `str`:

```
P = {"slot": <slot_id string>, "xc": <exposed_content_id string>, "is": <input_set_id string>}
```

- The values are the full identifier strings including their `sl1:`, `xc1:` and `is1:` prefixes.
- No enum, tuple, datetime, null or nested object appears in `P`. The `Slot`, coverage, metrics and input-set objects enter only through their identifiers.
- `ID_JSON(P)` sorts the keys as `is`, `slot`, `xc`.
- No other key (no state, count or timestamp) enters `P`.

### 23.7 Why typed objects and not three identifier strings

A signature `observation_id(slot_id, xc_id, is_id)` would be the literal reading of §3.2 but is not adopted, for four reasons: (1) an `xc1:` value from one slot can be paired with a `sl1:` value from another, and both are well-formed; (2) the reserved identifier of `KNOWN_EMPTY` (`is1:cb2e6ddeafe7c39450cfb3cf9d78f6c40893a2527dc8fb2e56d682b2d909b6ab`) passes any prefix-and-hex check, which would let a function parameter carry the reserved state (§21.4); (3) any 64-hexadecimal string would be accepted whether or not a Slice 3 or 4 function produced it; (4) the typed form follows the `exposed_content_id` precedent and needs no pattern machinery. The cost is a longer signature, and each call revalidates its objects.

### 23.8 Structural equality versus verified raw-source equality

- **Equal `observation_id` is a structural fact only.** It establishes equality of the canonical supplied projections, that is, the same `slot_id`, the same `exposed_content_id` and the same `input_set_id`, up to hash collision resistance. The identifier alone cannot recover or validate its component preimages. It never establishes raw-source identity, provenance correctness, shared lineage, a shared source, equivalence or equality of the raw data, or verified emptiness (§21.6).
- **`UNAVAILABLE` and `source=None`.** Two different feeds whose `SeriesKey` carries `source=None`, whose exposed content is identical and whose input set is `UNAVAILABLE`, produce one `observation_id`. This is accepted, because `UNAVAILABLE` carries no input identity (§21.6).
- **No inference from the identifier.** A relation or comparison must read the digest, algorithm and section kind directly (§5.1, §21.6). Different `observation_id` values also do not prove different raw data.
- **Source claims stay unverified.** C15 never verifies that a source digest matches the data behind it, and `observation_id` does not change that.

### 23.9 Layer sensitivity

| Change | `slot_id` | `exposed_content_id` | `input_set_id` | `observation_id` |
|---|---|---|---|---|
| receipt time only (any delivery field) | no | no | **yes** | **yes** |
| digest or algorithm | no | no | **yes** | **yes** |
| coverage, metrics or basis | no | **yes** | no | **yes** |
| slot (any form or time) | **yes** | **yes** | no | **yes** |
| spelling of a time zone | no | no | no | no |

`xc` includes the slot (§19.6), so a slot change moves it as well. L5 stays out of `exposed_content_id` (§3.2).

### 23.10 Golden vectors and complete ID_JSON fixtures

**Provenance of these values.** The six `observation_id` values were computed twice in a scratch run on `main` at `b79f00c`: by the existing serializer (`id_digest`, applied to the existing `slot_id`, `exposed_content_id` and `input_set_id` functions) and by a separate encoder written from §4 that shares no code with the repository serializer. The two agreed on all six values and on all six `ID_JSON` strings. This proves agreement between two encoders for these inputs.

**Reconciliation with the historical Codex cases (verified mapping, supplied by the independent Codex audit and approved by the owner).** Four of the six selected cases match historical Codex cases and two are newly selected and independently verified as above:

| Selected case | Historical Codex case |
|---|---|
| O1 | G5 |
| O2 | G1 |
| O3 | NEW |
| O4 | G6 |
| O5 | G2 |
| O6 | NEW |

The original historical cases G3 and G4 are omitted from the selected six-case set. The six vectors are therefore **not** all unchanged historical fixtures: O3 and O6 are new. No value here was copied from the audit; each was computed as described above.

**Fixtures** (all values are complete and reproducible):

- Series key `K`: `kind="DER"`, `section="candles"`, `symbol="BTC-PERP"`, `interval="1h"`, `source="hyperliquid"`, `qualifier=None`.
- Slot `INSTANT`: `K` with `at = 2026-01-01T12:00:00Z`. Slot `WINDOW_SESSION`: `K` with `window_start = 2026-01-01T11:00:00Z` and `session_start = 2026-01-01T00:00:00Z`.
- Coverage `COV`: `earliest_time 2026-01-01T07:00:00Z`, `latest_time 2026-01-01T12:00:00Z`, `contributing_count 6`, `interval "1h"`. Empty coverage: four `None`.
- Metrics, in order: `{name "atr", state "PRESENT", value Decimal("1.50"), unit "USD", window_id "atr:2:2026-01-01T12:00:00Z", reason None}` and `{name "vwap", state "WITHHELD", value None, unit "USD", window_id None, reason "UNTRUSTED"}`. Basis `EXPOSED_FIELDS`, or `NO_OBSERVATION` with no metrics for O4.
- Delivery `D0`: `source "hyperliquid"`, `source_type "REST"`, `source_id "book-1"`, `source_timestamp 2026-01-01T12:00:00Z`, `received_timestamp 2026-01-01T12:00:01Z`. Digest `G0`: algorithm `sha256-canonical-candles-v1`, digest `"b"` repeated 64 times.
- Input sets: V1 `COMPLETE_SINGLE` with `D0`; V2 `DIGEST_WITH_NEWEST` with `G0` and `D0`; V3 `UNAVAILABLE`; S1 is V2 with `received_timestamp 2026-01-01T12:00:02Z`.

| Case | Meaning | `slot_id` | `exposed_content_id` | `input_set_id` | `observation_id` |
|---|---|---|---|---|---|
| O1 | COMPLETE_SINGLE input set (V1) | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` | `xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14` | `is1:71ae34903b46b3741b7c856c674db3997ac7d433602487a8b5c353e390e59320` | `ob1:cadf4636832769da68e24c91059518e39de066f3d1152dd14dfa122006df32a9` |
| O2 | DIGEST_WITH_NEWEST input set (V2) | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` | `xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14` | `is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b` | `ob1:a32bba897d87696f6f7ab6a1ad693f439fbe3980c8f98421f35477f68583b671` |
| O3 | UNAVAILABLE input set (V3) | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` | `xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14` | `is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb` | `ob1:55a0b4660d2ea0d4bd087e16ab287d06807040a50ed0b69828fae47d47d68d5a` |
| O4 | empty exposed content, UNAVAILABLE | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` | `xc1:8f19c767a2eff3fd1a93ffbf19b5662ed8608ad84426d213c35fba39ce296a2b` | `is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb` | `ob1:a14ffdeb6c05200cead4dc8514d60f139374874fbf38e34a4bf968646d0a6de6` |
| O5 | receipt-only change (S1) | `sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f` | `xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14` | `is1:033dbc5e0d778620c89ae961ac828edc98e765bec2449916a64c864bc99194dc` | `ob1:1fa14091c16390d6198fd8482f49f8df370afddc02e1d0643a2ca94af92b13b8` |
| O6 | other slot form, V2 | `sl1:8d6cb6ced1c83e0dcee39e1ac2c22a30969e34efa160e32e43b71f15f7c56d56` | `xc1:ec33208310e69c532e77249c02151e3ba3c79f43404a7b81384b7b848be81610` | `is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b` | `ob1:1762e506f6bd228a58840539b03ad6d2058ee29378e2689a4ef6276ca52de3c8` |

The `slot_id` values are those pinned in §19.7, the `input_set_id` values are those pinned in §21.8, and the `exposed_content_id` values for the `INSTANT` slot are pinned in §19.7. The `exposed_content_id` of O6 (`WINDOW_SESSION` slot) is new in this amendment.

`O1` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:71ae34903b46b3741b7c856c674db3997ac7d433602487a8b5c353e390e59320"],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"],["xc","xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14"]]}`

`O2` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b"],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"],["xc","xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14"]]}`

`O3` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb"],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"],["xc","xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14"]]}`

`O4` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:fb86ff827fd6f34af231864ea7ff1e14cc328caa66c9a00906ffd2368a8565eb"],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"],["xc","xc1:8f19c767a2eff3fd1a93ffbf19b5662ed8608ad84426d213c35fba39ce296a2b"]]}`

`O5` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:033dbc5e0d778620c89ae961ac828edc98e765bec2449916a64c864bc99194dc"],["slot","sl1:bdc282635b110261a39d68aa65d2dd1de145b312b23521073d2b09aa5899e47f"],["xc","xc1:5eae971135b5441b7c861309227cf6e334077e025d421cf14c1cea0d9360bb14"]]}`

`O6` `ID_JSON(P)`:

`{"$":"map","v":[["is","is1:e2f7913c50d4894b21e19991d46588cc3f5947f3cc3c70a007b9ecaaea44c69b"],["slot","sl1:8d6cb6ced1c83e0dcee39e1ac2c22a30969e34efa160e32e43b71f15f7c56d56"],["xc","xc1:ec33208310e69c532e77249c02151e3ba3c79f43404a7b81384b7b848be81610"]]}`

**What the vectors prove:** O2 versus O5 differ only in receipt time (same `xc`, different `is`), so receipt sensitivity passes through `input_set_id`. O3 versus O4 differ only in exposed content. O2 versus O6 differ only in the slot, and `slot_id`, `exposed_content_id` and `observation_id` change while `input_set_id` remains unchanged (Changing only the Slot changes slot_id, exposed_content_id and observation_id; input_set_id remains unchanged). O1, O2 and O3 share one slot and one `xc`, and differ only in the input set.

### 23.11 Deliberate departures from v3.5

| # | v3.5 | v3.6 |
|---|---|---|
| E1 | `observation_id` is prohibited (§19.9, §21.10) and deferred (§21.1, §21.11) | superseded for `observation_id` only, at the contract level (approved 2026-11-15); implementation still needs a separate implementation authorization |
| E2 | §3.2 states the formula over identifiers and no signature | the typed composition of §23.3 and the policy of §23.4 to §23.5 |
| E3 | none | six golden vectors and complete `ID_JSON` fixtures (§23.10) |

### 23.12 Implementation scope boundaries (binding once separately authorized)

- **Allowed (after a separate authorization):** the `observation_id` function; one new module and one new test file; additive exports; the per-file import-policy entry, which allows only `pydantic`, `typing`, `__future__`, `traid.fusion.identity`, `traid.fusion.input_identity`, `traid.fusion.models` and `traid.fusion.serialization`.
- **Required tests:** the six vectors and `ID_JSON` fixtures; the captured projection and tag (a plain `str` with three keys); sensitivity (§23.9); the slot-consistency test of §23.4; rejection of identifier strings, wrong types, positional arguments, metric dictionaries, metric lists, unsorted or duplicate metrics and forged models, plus a test that fails if an outer validation wrapper makes metric dictionaries admissible; the `KNOWN_EMPTY` rejections of §23.5; hash-seed determinism; the Slice 3 and Slice 4 regressions; the name scan and import purity; and mutation-sensitive coverage (swapped or dropped keys, changed prefix or tag, an `xc` computed from a different slot, and removed revalidation).
- **Prohibited:** `methodology_id`, `Methodology`, `assessment_id`, `ac_id`, `EvidenceUnit`, source adapters, relations, lineage, `fuse()`, the C10 composite mapping, the C12 selected-delivery mapping, `SELECTED_DELIVERY`, wallet references, ETF and FOMC mappings, any `KNOWN_EMPTY` construction path, any role other than the five of §10, any score, probability or forecast, any change to `serialization.py`, `UtcDatetime`, the Slice 3 identifiers or the Slice 4 identifiers, and C16.

### 23.13 Owner approval checklist

- [x] Approve lifting the `observation_id` deferral for `observation_id` only (§23.2).
- [x] Approve the keyword-only composition of the existing public APIs with no outer validation wrapper, and the rejection of identifier strings and metric dictionaries (§23.3, §23.7).
- [x] Approve the input-admission design: validated dictionaries remain accepted for `Slot`, `Coverage` and `InputSetRef` where the existing public APIs support them; `MetricObservation` dictionary entries remain rejected; and a redundant outer `validate_call` wrapper is prohibited because it would change admission behavior (§23.3).
- [x] Approve the single-slot derivation and the required consistency test (§23.4).
- [x] Approve the fail-closed policy and the `KNOWN_EMPTY` rejections (§23.5).
- [x] Approve the exact projection with the keys `slot`, `xc`, `is` and string values (§23.6).
- [x] Approve the structural-equality limits (§23.8).
- [x] Approve the golden vectors and complete `ID_JSON` fixtures, with the historical mapping O1 = G5, O2 = G1, O3 = NEW, O4 = G6, O5 = G2, O6 = NEW and G3 and G4 omitted (§23.10).
- [x] Confirm that `methodology_id`, `assessment_id`, `EvidenceUnit`, adapters, relations, lineage, `fuse()` and C16 stay deferred (§23.12).
- [x] Approve the contract route: this file as v3.6 after independent audit, and an owner-approved update of the Spec §7 pointer (done in the activation change).
- [ ] Authorize the implementation scope of §23.12 in a separate task.

### 23.14 Unresolved issues and risks

- **Cost.** The slot is validated twice (once by `slot_id`, once by `exposed_content_id`), and every object is revalidated on each call. This is acceptable at the intended scale.
- **No relation to a source.** `observation_id` names a structural composition only. Source mappings remain deferred (§21.7), and the C13 mapping is still excluded.
- **The inherited text is not edited.** §19.9, §21.1, §21.10 and §21.11 still say `observation_id` is prohibited or deferred. They are superseded for `observation_id` only by §23.2, which records the supersession. Every other prohibition and deferral in them stays in force.

## 24. CHANGES_V3_5_TO_V3_6

Exactly these clauses change. Everything else is carried over from v3.5 unchanged.

| # | Clause | v3.5 | v3.6 |
|---|---|---|---|
| H1 | Title, version identifier, v3.6 note | `v3.5` | `v3.6`, derived from v3.5 |
| H2 | §3.2 `observation_id` line | formula only | pointer to the typed composition (§23) |
| H3 | new §23 | none | observation identity amendment (owner-approved, bounded) |
| H4 | new §24 | none | this table |

**Not changed.** v3.5 §21 (the L5 input identity amendment and its golden vectors) and v3.4 §19 are untouched. Phase 1 is a partial milestone; C15 stays OPEN and C16 is not authorized. P1, P2 and P3 are inactive. `EvidenceRole` has exactly five members and there is no `SUPPORT`, `CONTRADICT` or `ELIGIBLE` role. There is no score, probability or forecast, no Strategy or Risk interface, `news_claims` is excluded, there is no new ETF freshness policy, wallet references stay privacy-preserving and unapproved, and U2 is separate. v3.5, v3.4, v3.3 and v3.2 stay unmodified, and the Spec §7 pointer was updated from v3.5 to v3.6 in the activation change (a change outside this file). The C13 source mapping stays excluded, `KNOWN_EMPTY` stays contract-reserved and not constructible, and `observation_id` implementation needs a separate owner authorization.

**Honest limits of this contract.** It was written by the implementer (Claude Code), passed the independent Codex audit (FINAL_VERDICT: PASS, after documentation conditions were applied), and received bounded owner approval on 2026-11-15, which does not authorize implementation. The golden vectors were computed by the repository serializer and by a separate encoder written from §4 in a scratch run. That shows two encoders agree. It is not an audit. The historical mapping (O1 = G5, O2 = G1, O3 = NEW, O4 = G6, O5 = G2, O6 = NEW; G3 and G4 omitted) is recorded in §23.10.

---

## 25. METHODOLOGY_IDENTITY_AMENDMENT [OWNER-APPROVED v3.8 DESIGN; IMPLEMENTATION NOT AUTHORIZED]

This section is approved as a **design contract only**, subject to its explicit unresolved decisions and deferred gates.
- The owner approved the design; §25.17 preserves the pre-approval checklist as history.
- Implementing it needs a further, separate explicit owner authorization.
- Official v3.8 is the Phase 1 design baseline. Slice 6 implementation remains NOT AUTHORIZED; no mapping or runtime comparison is activated.

Labels:
- **[F]** verified repository fact on `main` at `ebb9cf9`;
- **[C]** requirement inherited from v3.6;
- **[P]** proposal;
- **[O]** owner decision still needed;
- **[U]** unresolved.

### 25.1 Scope [PROPOSED]

**This amendment covers exactly:**
1. The closed `Methodology` model and its four supporting value models: `ConfigEntry`, `ConfigRecord`, `ConfigField` and `NamedDigest`.
2. The `methodology_id` function.
3. Their deterministic validation, normalization and serialization rules.
4. The methodology-equivalence safeguards that future comparison rules must obey (§25.9 and §25.12). These are contract text only. Nothing here evaluates them at runtime.
5. The requirements that any future source mapping must meet (§25.10). The registry starts **EMPTY**.

**It does not cover:**
- `assessment_id`, `ac_id` and `AssessmentContent`;
- `EvidenceUnit`;
- source adapters and registry entries;
- runtime methodology-equivalence evaluation;
- relations, lineage and `fuse()`;
- Strategy or Risk integration;
- Slice 7 and C16.

These all remain deferred or prohibited exactly as v3.6 states.

### 25.2 Exact amendment and supersession record [PROPOSED]

- **Formula [C] (§3.2), preserved:** `methodology_id = "mt1:" + id_digest("c15.mt.v1", P)`.
  - `id_digest` is the existing `HID` of §4.4 **[F]** (`src/traid/fusion/serialization.py:222`).
  - `P` is the explicit projection of §25.6, which is how this amendment reads the v3.6 symbol `MI`.
  - The prefix `mt1:` and the tag `c15.mt.v1` are unchanged.
  - `serialization.py` is not changed.
- **MI made concrete.** The v3.6 L6 row lists five items: "engine and schema version, source-exposed config, rule/mapping digests, quality-policy version, hidden-input codes".
  - All five are kept.
  - The mapping part of "rule/mapping digests" becomes its own field, `mapping_id`. `rule_digests` carries rule digests only.
  - This gives seven fields (§25.3).
- **Inherited open items resolved on approval:**
  - §19.1: "Methodology needs a type policy for config values (for example `timedelta` in `FlowConfig`, and `OrderRequest` tuples in `LiquidityConfig`)".
  - The §19.11 "Methodology" bullet.
  - Both are resolved by §25.4.
- **Restrictions superseded, for `Methodology` and `methodology_id` only, on owner approval and at the contract level:**
  - the prohibitions in §19.9, §21.10 and §23.12;
  - the deferrals in §19.1 ("Not frozen by this amendment") and §21.11.

  The four supporting value models are part of `Methodology` for this purpose. Those sections still apply in full to every other item they list. Their inherited text is not edited, and this bullet is the record of the supersession.
- **Inherited clauses amended by explicit text in §25.12.** Pointer annotations preserve the original text of §3.4, §5.3 (apart from the corrected R10 example), §7 and the §12 preamble. The in-place corrections are identified separately below:
  - §3.4: the first `cmp` line and the reason codes;
  - §5.3: the M column, rows R3–R8 and R10, and the rule ordering;
  - §3.6: the introduction makes methodology-dependent Expected outcomes conditional;
  - §5.4: the partition, receipt, coverage and candle guarantees are corrected in place;
  - §7: the same-`claim_id` bullet and the methodology bullet;
  - §12: the B1 expectations are qualified by §25.12.4; AT-B1-9 is corrected in place for the C07 hidden-threshold case.
- **Not an authorization.** Neither drafting this file nor approving it:
  - authorizes implementation;
  - activates any deferred component;
  - approves any source mapping;
  - selects any general deferred relation label or new relation type. The equal-XC/different-delivery subcase alone proposes the existing unresolved label in §25.12.2, subject to owner approval; it activates no relation.

### 25.3 Methodology model [PROPOSED]

```
Methodology:                           # closed, frozen, strict; all seven fields required; no defaults
  mapping_id:             MText | None             # pattern ^[A-Za-z0-9][A-Za-z0-9._-]*$
  engine_version:         MText                    # the source's engine or formula version string
  schema_version:         MText | None             # the source configuration schema version; None if the source has none
  config:                 tuple[ConfigEntry, ...]  # names strictly ascending (hence unique); may be empty
  rule_digests:           tuple[NamedDigest, ...]  # names strictly ascending (hence unique); may be empty
  quality_policy_version: MText | None             # §25.8
  hidden_input_codes:     tuple[Code, ...]         # strictly ascending (hence unique); may be empty

ConfigEntry:   name: Name;  value: ConfigValue                 # §25.4
ConfigRecord:  fields: tuple[ConfigField, ...]                 # at least one field; names strictly ascending
ConfigField:   name: Name;  value: ConfigScalar                # never None
NamedDigest:   name: Name;  algorithm: MText;  digest: str matching ^[0-9a-f]{64}$

MText:  exact str (type(v) is str), non-empty, no leading or trailing whitespace, never stripped
Name:   exact str matching ^[a-z][a-z0-9_]*$
Code:   exact str matching ^[A-Z][A-Z0-9_]*$
```

| Field | Meaning | `None` means | Decided by |
|---|---|---|---|
| `mapping_id` | the registry mapping under which an adapter claims to have built this value | no mapping is claimed | the adapter, against the registry (§25.10). The model checks only the pattern. |
| `engine_version` | the source's own version string, for example `formula_version` or `engine_version` | not allowed | the source report |
| `schema_version` | the schema version of the source's configuration model | the source has no configuration schema | the mapping |
| `config` | the source-exposed configuration entries required by the mapping | — (an empty tuple means no entries) | the mapping |
| `rule_digests` | named digests of rule sets that the source exposes and binds | — (an empty tuple means none) | the mapping |
| `quality_policy_version` | the C05 policy version that applies to this comparison unit (§25.8) | not applicable, or unavailable together with a code (§25.8) | the mapping |
| `hidden_input_codes` | disclosed inputs that affect the output but are not exposed | — (an empty tuple means none declared) | the mapping |

**Model rules:**
- **Base class.** All five models derive from a private base `_MethodologyModel(FusionModel)` with `ConfigDict(strict=True, revalidate_instances="always")`. From `FusionModel` they inherit `extra="forbid"`, `frozen=True` and `validate_default=True` **[F]** (`src/traid/fusion/models.py:54-55`). `model_construct` and `model_copy` validate, following the Slice 4 precedent **[F]** (`src/traid/fusion/input_identity.py:17-27`).
- **All fields required.** Every field is required, and an omitted field is rejected. A `None` must be passed explicitly. An unexpected field is rejected.
- **Exact `str` everywhere.** Every text position (`MText`, `Name`, `Code`, text config values) requires `type(v) is str`, checked before pydantic conversion. A `StrEnum` member is therefore rejected.
  - **[F]** Scratch probe with pydantic 2.13.5: the existing Slice 2 `Text` admits a `StrEnum` member and converts it to a plain `str`. That is why `MText` needs its own exact-type check.
  - The existing `Text` used by Slices 3–5 is not changed.
- **Ordering.** Names and codes compare by Python string order. An unsorted or duplicate sequence is rejected. Nothing is sorted, merged or deduplicated silently (the §19.4 precedent).
- **One cross-field invariant.** If `quality_policy_version` is not `None`, `hidden_input_codes` must not contain `QUALITY_POLICY_VERSION_NOT_EXPOSED`. Every other cross-field requirement belongs to the mapping (§25.10).
- **No semantic validation.** The model does not check any of the following:
  - that `mapping_id` names an approved mapping;
  - that codes belong to a vocabulary;
  - that config matches a source;
  - that a digest matches its rules.

  It is structural only (§25.7).

### 25.4 Bounded ConfigValue policy [PROPOSED]

**Verified requirements [F].**

| Source config | Field | Source type | ConfigValue form |
|---|---|---|---|
| C07 `LiquidityConfig` (`src/traid/liquidity/analytics.py:64-87`) | `base_asset`, `quote_currency` | `str` | text |
| | `bands_bps` | `tuple[Decimal, ...]`, unique and strictly increasing (`:85-86`) | sequence of Decimal |
| | `orders` | `tuple[OrderRequest, ...]`, where `OrderRequest = {side: Side (StrEnum), quantity: Decimal}` (`:48-62`). There is no uniqueness or ordering check (`:70`, `:79-87`). | sequence of records `{quantity: Decimal, side: text}`, with source order and duplicates preserved |
| C08 `FlowConfig` (`src/traid/flow/analytics.py:88-110`) | `base_asset` | `str` | text |
| | `window`, `late_tolerance` | `timedelta` | timedelta |
| | `session_start` | aware `datetime`, normalized to UTC | datetime |
| C09 `DerivativesConfig` (`src/traid/derivatives/analytics.py:109-135`) | `base_asset`, `quote_currency` | `str` | text |
| | `atr_period`, `volatility_period`, `funding_lookback_hours` | `int` | int |
| | `momentum_lookbacks` | `tuple[int, ...]`, unique and increasing | sequence of int |
| | `session_start` | `datetime \| None`, UTC and hour-aligned | datetime or `None` |

- All three config models carry `schema_version` (`CanonicalModel`, `src/traid/domain/models.py:36-47`). It maps to `Methodology.schema_version`, not to a config entry.
- `symbol` is bound through `SeriesKey.symbol` (L1). The illustrative candidates exclude it from config (§25.11).

**ConfigScalar.** A non-null value of exactly one of these types:
- exact `str`, under the `MText` rules;
- exact `int` (`bool` is rejected);
- exact `Decimal`, finite;
- exact `timedelta`;
- exact `datetime`, aware, with a `tzinfo` type accepted by §4.2b. It must be supplied as an object (ISO text is rejected) and is normalized to UTC.

**ConfigValue** is one of:
- `None`;
- a `ConfigScalar`;
- `tuple[ConfigScalar, ...]`;
- `tuple[ConfigRecord, ...]`.

- `None` is allowed only as the top-level value of an entry. It is not allowed inside a sequence or a record.
- **Sequences:**
  - The type must be exactly `tuple`; a `list` is rejected (strict tuple validation, **[F]** scratch probe).
  - Source order is preserved and is significant.
  - Duplicates are preserved.
  - An empty tuple is allowed.
  - All elements are scalars, or all elements are records.
  - A sequence may not contain another sequence.
- **Records:**
  - flat, with at least one field;
  - field names strictly ascending;
  - field values are non-null scalars;
  - no sequence inside a record.

  A record is the adapter's explicit conversion of a flat source model (C07 `OrderRequest`), with enum fields passed as their string value (the §19.5 R3 precedent).
- **Maximum depth:** entry → sequence → record → scalar.

**Rejected, never coerced:**
- `float`, `bool`, `bytes`, `complex`, `date`, `time`;
- any `Enum` member, including `StrEnum`, `IntEnum` and `IntFlag`;
- any subclass of `str`, `int`, `Decimal`, `timedelta`, `datetime` or `tuple`;
- a naive `datetime`, an unaccepted `tzinfo`, or parsing text into a datetime (an exact, unpadded ISO-looking string remains permitted as generic text, never as a datetime);
- NaN or infinite `Decimal`;
- conversion of `int` into `Decimal` or `timedelta` (an exact `int` is independently a valid generic scalar and remains an int);
- `list`, `dict` as a value, `set`, `frozenset`, `Unordered`;
- nested sequences, a sequence inside a record, `None` inside a sequence or record, an empty record;
- a Pydantic source model (adapters convert it explicitly).

**Bounded by design.** The admitted forms are exactly those the verified C07–C09 configs need. Admitting another form requires a contract amendment. This policy is not a generic serializer: it does not recurse beyond the depth stated above, and it has no fallback branch.

**Normalization that is not lossy.**
- `Decimal` spelling is normalized only by the existing §4.3 encoding, so equal values share one identity: `1.5` and `1.50` are the same.
- `timedelta` has one internal representation, so `60 minutes` and `1 hour` are the same value.
- Datetimes are converted to UTC, which preserves the instant.

No other conversion exists.

**Admission before coercion.** Exact scalar and sequence type checks run before Pydantic union selection or conversion, at every nesting level. `strict=True` alone is insufficient: strict tuple validation can convert a tuple subclass. Datetime admission checks the exact datetime type and the serializer-approved timezone type before calling `utcoffset`, `dst`, `tzname`, `astimezone`, or any parsing/normalization callback. Unsupported timezone objects are rejected without invoking their callbacks; supported datetimes are then checked and normalized using the unchanged serializer boundary. There is no new timezone allowlist and no change to `UtcDatetime`.

**Structural versus mapping-specific types.** Generic scalars have no implicit source-field semantics. `ConfigEntry(name="window", value=3600)` may structurally hold an exact int; it is never converted into a timedelta. `ConfigEntry(name="session_start", value="2026-01-01T00:00:00Z")` may structurally hold text; it is never parsed into a datetime. A future approved mapping expecting a duration or datetime must reject such source-field mismatches during mapping validation. This is not implemented by Slice 6, and no field-name inference is permitted.

### 25.5 Validation policy and fail-closed behavior [PROPOSED]

- **Any invalid field fails the whole call.** The error is raised before any hash is computed. No partial identifier is produced, no default is supplied, nothing is repaired, and no exception is caught and replaced.
- **Forged instances are revalidated before hashing, and rejected if invalid.** This applies to an instance:
  - built with `model_construct`;
  - edited with `object.__setattr__` or through `__dict__`;
  - copied with `model_copy(update=...)`;
  - at any nesting level.
- **Only existing normalization applies:** datetime to UTC, and the §4.3 Decimal encoding. No new normalization, default or repair rule is introduced.
- **Admission of the argument.** `methodology_id` accepts either a `Methodology` instance or a mapping validated by the same strict model. This is consistent with the §23.13 admission precedent for `Slot`, `Coverage` and `InputSetRef`. Nested values in a mapping are validated just as strictly, and lists are rejected where tuples are required. **[O]** The owner may instead require instances only.
- **Determinism.** The result does not depend on dictionary insertion order, the spelling of a time zone, process or hash seed.

### 25.6 `methodology_id` API and canonical projection [PROPOSED]

```
methodology_id(methodology: Methodology) -> str
```

- **Wrapper.** The function is wrapped with `@validate_call(config=ConfigDict(strict=True))`, like `series_id`, `slot_id` and `input_set_id` **[F]** (`src/traid/fusion/identity.py:99-108`, `src/traid/fusion/input_identity.py:78`).
- **Return value.** One parameter; it returns `mt1:` followed by 64 lowercase hexadecimal characters.
- **Projection.** `P` is plain data built by an explicit function. It is **never** produced by `model_dump` or any automatic dump:

```
P = {
  "mapping_id":             <str | None>,
  "engine_version":         <str>,
  "schema_version":         <str | None>,
  "config":                 {<entry name>: <projected value>, ...},
  "rule_digests":           {<name>: {"algorithm": <str>, "digest": <str>}, ...},
  "quality_policy_version": <str | None>,
  "hidden_input_codes":     (<code>, ...),
}
projected value := None | str | int | Decimal | timedelta | UTC datetime
                 | tuple of scalars, in source order
                 | tuple of {<field name>: <scalar>, ...}, in source order
```

- **Keys.** Exactly seven keys, always present. `None` stays `None`. Empty `config` and `rule_digests` become empty maps. An empty `hidden_input_codes` becomes an empty tuple.
- **Maps.** `config`, records and `rule_digests` are projected as maps keyed by name. The model's ascending-name rule also keeps model instances canonical.
- **Plain values only.** No enum object, model object, `set` or `Unordered` appears in `P`.
- **Hash.** `methodology_id = "mt1:" + id_digest("c15.mt.v1", P)`.
- **Nothing else enters `P`.** No evaluation/report timestamp, source-report digest, observation content, assessment content or validation evidence is included. Configuration timestamps explicitly admitted by §25.4 (for example `session_start`) do enter `P` as UTC datetimes. This clarifies wording only and changes no projection or fixture.

### 25.7 Structural equality only [PROPOSED]

- **What equality proves.** Equal `methodology_id` values prove equal canonical projections `P`, up to hash collision resistance. This is **STRUCTURALLY_EQUAL** (§25.9.1).
- **What equality does not prove:**
  - that a mapping was applied or validated;
  - that the configuration inventory was complete;
  - that hidden inputs were equal;
  - that the same code ran, or that the outputs are reproducible;
  - source equality, provenance or lineage.
- **What a difference does not prove.** Different `methodology_id` values do **not** prove different methodology. For example, they can differ because of a different `mapping_id`, or because one side's quality policy version is unavailable.
- **No comparison in Slice 6.** No function compares two methodologies or evaluates a comparison state. The identifier alone cannot recover its preimage, and no function may try to.

### 25.8 Quality policy design (Design A) [PROPOSED]

- **One field per comparison unit.** There is one `quality_policy_version` per comparison unit:
  - a C07 report;
  - a C08 report;
  - a C09 section (`candles` or `funding`);
  - a C10 dimension;
  - a C13 result.
- **Derived from the mapping only.** The value is derived only through the derivation the approved mapping declares. An adapter never infers it from arbitrary report fields, and never from whether a section's quality happens to be present.

| Case | Representation | Enforced by |
|---|---|---|
| Not applicable | `None`, without `QUALITY_POLICY_VERSION_NOT_EXPOSED` | the mapping (declared not applicable) |
| Unavailable (a policy applies, but its version is not exposed) | `None` together with the code `QUALITY_POLICY_VERSION_NOT_EXPOSED` | the mapping (declared condition) |
| Missing or invalid | rejected; no `Methodology` exists | the model: an omitted field, wrong type, padded text or enum is rejected |
| Explicitly identified version | exact text, without that code | the model forbids text together with the code; the mapping fixes the source |

**Derivation kinds a mapping may declare:**
- `NOT_APPLICABLE`.
- `MAPPING_CONSTANT(v)`: bound to the mapping's accepted engine versions. The adapter checks that every exposed version present in the unit equals `v`, and **rejects the unit** otherwise.
- `SOURCE_FIELD(path)`: required, or optional with a declared unavailable condition.
- `NOT_EXPOSED`.

**C09 constraints [F]:**
- Each section has `quality: QualityAssessment | None` (`src/traid/derivatives/analytics.py:155-157`).
- When a section's quality is present, its version is always the code constant `FRESHNESS_POLICY_VERSION = "c09-hourly-freshness-1"` (`:60`, `:293`).
- `analyze_derivatives` takes no policy parameter (`:563-566`).

So a C09 mapping can only be `MAPPING_CONSTANT("c09-hourly-freshness-1")`, bound to `c09-derivatives-1`. A section without quality takes the constant, not `None`, because `None` would create a spurious difference. A present version that differs from the constant causes rejection.

**C10 constraints [F]:**
- `SourceRef.quality_policy_version` (`src/traid/regime/engine.py:263-275`) describes an **upstream input**.
  - One C10 report can carry up to three distinct upstream versions (from C07, C08 and the C09 constant), and they can differ.
  - C10 excludes an upstream assessment whose version differs from its own policy, with `QUALITY_POLICY_NOT_REPRODUCIBLE` (`:512-513`).
  - These values are assessment content, never C10 methodology.
- C10's own policy:
  - is the parameter `quality_policy`, defaulted when `None` (`:1007-1011`);
  - is not exposed in `MarketStateReport` (`:420-430`);
  - is used only by the liquidity and flow dimensions (`:1044-1045`).

  Those two dimensions are therefore `NOT_EXPOSED`, and every other dimension is `NOT_APPLICABLE`.

**Why a single field suffices.**
- Within one unit, at most one C05 policy of the unit's own applies.
- Wherever a version or its thresholds are hidden, the unit carries a code that cannot be discharged (§25.9.3), so the pair can never become `ESTABLISHED_EQUAL`.
- A single field therefore cannot cause a false methodology equality.
- Named per-source policy references (Design B) were considered and **not adopted**. They would duplicate assessment content (`SourceRef`) and prevent no collapse.

**No policy value is invented.** The only literal versions named in §25 are the verified constants `c05-policy-1` (`src/traid/quality/models.py:16`) and `c09-hourly-freshness-1`.

### 25.9 Methodology-equivalence rule [PROPOSED; contract text only, evaluated by the future relations slice]

#### 25.9.1 STRUCTURALLY_EQUAL

A boolean property of a pair: the two `methodology_id` values are equal.
- It is independent of the comparison state below.
- It is informational only.
- It never satisfies any §5.3 row by itself.

#### 25.9.2 Mapping-validation evidence

One side of a pair is **validated** only if all of the following hold:

1. **(a)** The `Methodology` was built **during the same evaluation** by the approved adapter for its `mapping_id`, from a source report that passed revalidation. A `Methodology` value or an `mt1:` string supplied by a caller is never validated.
2. **(b)** `mapping_id` names an entry in the approved registry (§25.10), and the source's engine or formula version is one of that entry's accepted versions.
3. **(c)** Every inventory check of the entry passed (§25.10, item 4).
4. **(d)** The emitted `hidden_input_codes` are exactly the codes that the entry requires for that unit and condition.

**A `mapping_id` string, an `mt1:` identifier or a `Methodology` instance never proves (a)–(d) by itself.** The evidence is held by the evaluator. It is not a field of `Methodology` and does not enter `methodology_id`. Its exact form is deferred to the relations design (§25.13).

#### 25.9.3 Discharge of hidden codes

For a pair, a hidden code is **discharged** only if:
- the mapping declares it dischargeable and names a binding; and
- the bound values are present on both sides and equal.

In this amendment:
- `QUALITY_THRESHOLDS_NOT_EXPOSED` is never dischargeable.
- `QUALITY_POLICY_VERSION_NOT_EXPOSED` is never dischargeable.
- `VERIFICATION_POLICY_NOT_EXPOSED` is dischargeable only by an equal `VerificationResult.input_digest` under an approved C13 mapping (§25.11).

#### 25.9.4 Three exclusive comparison states

| State | Condition |
|---|---|
| `ESTABLISHED_EQUAL` | Both sides are validated under the **same** `mapping_id`, the pair is STRUCTURALLY_EQUAL, and every hidden code on either side is discharged. |
| `ESTABLISHED_DIFFERENT` | Both sides are validated under the **same** `mapping_id`, and at least one of these components differs while its value is available on both sides: `engine_version`, `schema_version`, a config entry value, a rule digest, or `quality_policy_version`. A `None` that carries `QUALITY_POLICY_VERSION_NOT_EXPOSED` counts as unavailable. |
| `NOT_ESTABLISHED` | Every other pair. |

- **Exclusivity.** `ESTABLISHED_EQUAL` requires equal identifiers. `ESTABLISHED_DIFFERENT` requires a differing projected component, so its identifiers differ. `NOT_ESTABLISHED` is the complement of both.
- **What does not count as a difference.** A difference only in hidden codes, or only in an unavailable component, never yields `ESTABLISHED_DIFFERENT`.
- **Hidden codes and `ESTABLISHED_DIFFERENT`.** Hidden codes do not prevent `ESTABLISHED_DIFFERENT`, because a difference visible in an exposed component proves that the methodologies differ.

#### 25.9.5 Conditions that force NOT_ESTABLISHED

Each condition alone is sufficient:
1. Either side is not validated (§25.9.2). This covers:
   - an empty registry;
   - a `None` or unapproved `mapping_id`;
   - a methodology or identifier supplied by a caller;
   - a failed inventory check.
2. The two sides carry different `mapping_id` values.
3. The identifiers are equal, but some hidden code is not discharged. This covers `QUALITY_THRESHOLDS_NOT_EXPOSED`, `QUALITY_POLICY_VERSION_NOT_EXPOSED`, and `VERIFICATION_POLICY_NOT_EXPOSED` with an unequal or absent binding.
4. The identifiers differ only in hidden codes or in components that are unavailable on one side.

**Unknown source versions are not a comparison state.** An unknown source version never reaches comparison: the adapter rejects the unit and records the reason (§25.10, item 10). The unit is excluded. It is never given a `None` mapping or reported as covered.

**Consequence in this v3.8 proposal.** The registry is EMPTY, so **every pair is `NOT_ESTABLISHED`**.

#### 25.9.6 An empty `hidden_input_codes` tuple

An empty tuple never establishes completeness by itself. An adapter that omits a code produces the same empty tuple as an honest one. The empty tuple means "no hidden inputs" only on a validated side whose approved mapping declares that the unit has no hidden inputs.

#### 25.9.7 Safety invariant (binding on every future comparison rule)

1. **No definitive conflict without equal methodology.** No rule that needs proven methodology equality may yield `CONFLICTING_ASSESSMENT`, `CONFLICTING_OBSERVATION` or `EQUIVALENT_ON_COMPARED_METRICS` unless the state is `ESTABLISHED_EQUAL`.
2. **No claim of methodology difference without proof.** No rule may yield `SAME_INPUT_DIFFERENT_METHODOLOGY` or `SAME_OBSERVATION_DIFFERENT_ASSESSMENT` unless the state is `ESTABLISHED_DIFFERENT`.
3. **No eligibility harm from `NOT_ESTABLISHED`.** A `NOT_ESTABLISHED` pair never makes a unit `INELIGIBLE`.

#### 25.9.8 Reason codes

- **New, proposed:** `METHODOLOGY_NOT_ESTABLISHED`, an `uncompared` reason for a `NOT_ESTABLISHED` pair.
- **Narrowed:** `METHODOLOGY_DIFFERS` is used only for `ESTABLISHED_DIFFERENT`.

### 25.10 Mapping registry contract [PROPOSED]

The registry is a contract table maintained by future amendments. Each entry must state all of the following.

1. **`mapping_id`.** It is unique and never reused. A changed entry gets a new `mapping_id`.
2. **Source identity:** the card, the report class and the comparison-unit kind (for example, a C09 candle section).
3. **Accepted engine or formula versions**, as exact strings.
4. **Configuration inventory:**
   - the source configuration model;
   - the **required** fields, each with its `ConfigValue` form and conversion;
   - the **excluded** fields, each with a reason;
   - the field that supplies `schema_version`.

   Compatibility check: the union of required fields, excluded fields and the schema-version field must equal the source model's declared field set (`model_fields`) **exactly**. Any unexpected or missing field rejects the unit. This catches an upstream model change made without a version bump. The source config models are closed (`extra="forbid"`, **[F]** `src/traid/domain/models.py:39-44`).
5. **`schema_version` derivation.**
6. **`rule_digests`:**
   - the name, source path and algorithm of each digest;
   - who verifies it. C15 never recomputes an upstream digest (§4.1).
7. **`quality_policy_version` derivation** (§25.8).
8. **Required hidden-input disclosures**, per unit and condition, each marked dischargeable or not.
9. **Approved digest bindings** for each dischargeable code:
   - the exact source field;
   - the equality rule;
   - what equality binds, and what it does **not** imply.
10. **Unknown-version handling: reject.** This is fixed by this contract and is not optional for an entry. When a source version is not accepted:
    - the adapter produces no `Methodology` for the unit;
    - the unit is excluded and the reason is recorded;
    - the unit is never downgraded to `mapping_id=None`;
    - the unit is never reported as covered.

    The precedents are C10's `UNSUPPORTED_FORMULA_VERSION` (`src/traid/regime/engine.py:462-472`) and the C13 macro adapter's allow-list (`src/traid/news/macro_adapter.py:22`, `:53`).
11. **Reachable states.** Which states the unit can ever reach. For example, a unit carrying `QUALITY_THRESHOLDS_NOT_EXPOSED` can never reach `ESTABLISHED_EQUAL`.

**Registry state in this v3.8 proposal: EMPTY.**

| `mapping_id` | Source | Status |
|---|---|---|
| — | — | no entries |

- No mapping is approved or activated by this proposal.
- An entry requires its own owner approval and the adapter slice.
- Consequently, no methodology comparison is currently `ESTABLISHED`.

### 25.11 Illustrative mapping candidates [ILLUSTRATIVE ONLY; NOT REGISTRY ENTRIES; NOT APPROVED]

The rows below have no `mapping_id`. They cannot be activated by reference. They exist to show that the §25.10 requirements can be met by the verified sources and to make the per-source limits explicit. Every version string is verified **[F]**.

| Candidate unit | Engine version | Required config | Excluded | `quality_policy_version` | Hidden codes | Highest state reachable |
|---|---|---|---|---|---|---|
| C07 report | `c07-liquidity-1` (`liquidity/analytics.py:34`) | `bands_bps`, `base_asset`, `orders` (records `{quantity, side}`; order and duplicates kept), `quote_currency` | `symbol` (bound by L1); `schema_version` (field of its own) | `SOURCE_FIELD(report.quality.policy_version)`, always present (`:137`) | `QUALITY_THRESHOLDS_NOT_EXPOSED` | `ESTABLISHED_DIFFERENT` only |
| C08 report | `c08-trade-flow-1` (`flow/analytics.py:68`) | `base_asset`, `late_tolerance`, `session_start`, `window` | `symbol`; `schema_version` | `SOURCE_FIELD(report.quality.policy_version)` when `quality` is not `None`; otherwise `None` with `QUALITY_POLICY_VERSION_NOT_EXPOSED` (`quality` may be `None`, `:136`) | `QUALITY_THRESHOLDS_NOT_EXPOSED`, plus `QUALITY_POLICY_VERSION_NOT_EXPOSED` when `quality` is `None` | `ESTABLISHED_DIFFERENT` only |
| C09 section (`candles` or `funding`) | `c09-derivatives-1` (`derivatives/analytics.py:59`) | `atr_period`, `base_asset`, `funding_lookback_hours`, `momentum_lookbacks`, `quote_currency`, `session_start` (an explicit `None` allowed), `volatility_period`. All seven apply to both sections. | `symbol`; `schema_version` | `MAPPING_CONSTANT("c09-hourly-freshness-1")` | none | `ESTABLISHED_EQUAL` |
| C10 dimension: liquidity or flow | `c10-market-state-1` (`regime/engine.py:79`) | none (rules are bound by digest) | — | `NOT_EXPOSED` | `QUALITY_POLICY_VERSION_NOT_EXPOSED`, `QUALITY_THRESHOLDS_NOT_EXPOSED` | `ESTABLISHED_DIFFERENT` only |
| C10 dimension: any other | `c10-market-state-1` | none | — | `NOT_APPLICABLE` | none | `ESTABLISHED_EQUAL` |
| C13 result | `c13-news-verification-1` (`news/models.py:22`) | none | — | `NOT_APPLICABLE` | `VERIFICATION_POLICY_NOT_EXPOSED` (dischargeable, below) | `ESTABLISHED_EQUAL`, only with an equal `input_digest` |

**Over-inclusion.** The C09 candidate deliberately includes every configuration field in both sections. Over-inclusion can only split methodology identifiers. That moves a pair toward `ESTABLISHED_DIFFERENT` or `NOT_ESTABLISHED`, never toward a false equality. Omission is the unsafe direction.

**C10 rules digest.**
- Every C10 candidate carries one named digest: `{"rules": (report.digest_algorithm, report.rules_digest)}` (`regime/engine.py:80`, `:420-430`).
- It is carried as an existing digest reference. C15 does **not** reimplement `rules_digest` (§4.1).
- `MarketStateReport` itself rejects a digest that does not match its rules (`bound_to_rules`, `:453-456`), so the revalidation required by §25.9.2(a) checks the digest.
- The digest covers the whole `MarketStateRules`, including `rules_version`, `calibration_status` and every dimension's rules (`:169-199`). A change to one dimension's rules therefore splits the methodology of every dimension. This over-splitting is safe.
- **[O]** The owner must confirm `rules.schema_version` as the C10 `schema_version` source.

**C13 binding.**
- `VerificationPolicy` exposes no version **[F]** (`news/models.py:601-608`).
- `VerificationResult.input_digest` hashes `[claim_id, text_digest, T, policy.model_dump(mode="python"), form, evidence_digest, macro input_digest or None]` **[F]** (`news/engine.py:496-497`).
- Equal digests therefore bind equal verification policies, up to collision resistance. That holds only together with an equal claim, an equal T and an equal evidence set.
- **Equality is used for exactly one purpose: discharging `VERIFICATION_POLICY_NOT_EXPOSED`.** The methodology rule draws no other inference from it: no source equality, no evidence or citation lineage, no C12 report identity, no revision linkage, and no provenance.
- Unequal digests never establish a different policy (the pair is `NOT_ESTABLISHED`).
- The C13 source mapping stays excluded from approved mappings (§21.12, §23.14).

**Outside the scope of these candidates:**
- C11 (wallet references are unapproved; no `wr1:` value may be produced);
- C12 series, FOMC and ETF units, and the ETF mapping;
- C14 (not an observation);
- every other deferred source mapping.

None of them may appear in an implementation of this amendment.

### 25.12 Amendments to inherited clauses [PROPOSED]

#### 25.12.1 §3.4 metric comparison

The first `cmp` line, `UNKNOWN if methodology_id differs`, is replaced by:

```
  UNKNOWN  if methodology_state(a, b) != ESTABLISHED_EQUAL      # §25.9.4
```

- The other `cmp` lines are unchanged.
- Reason codes:
  - `METHODOLOGY_DIFFERS` is used when the state is `ESTABLISHED_DIFFERENT`;
  - `METHODOLOGY_NOT_ESTABLISHED` is used when the state is `NOT_ESTABLISHED`.
- The other reason codes are unchanged.

#### 25.12.2 §5.3 decision table, rule ordering and §5.4

**Reading of the M column:**
- "M equal" means `ESTABLISHED_EQUAL`.
- "M differs" means `ESTABLISHED_DIFFERENT`.
- `NOT_ESTABLISHED` is the new third value.

**Amended and new rows.** Unlisted rows (R1, R2, R9, R10a, R11) keep their v3.6 text. R1 and R2 depend on `assessment_id`, which stays deferred (§25.13).

| # | Amended condition | Relation | Eligibility effect |
|---|---|---|---|
| R3 | same `observation_id`, methodology `ESTABLISHED_DIFFERENT` | `SAME_OBSERVATION_DIFFERENT_ASSESSMENT` (unchanged) | none |
| R3a | same `observation_id`, `ESTABLISHED_EQUAL`, same T, different `ac_id`, `raw_identity` verified or complete | `CONFLICTING_ASSESSMENT` (unchanged) | both `INELIGIBLE` |
| R3b | as R3a, but `raw_identity = PARTIAL` | `UNRESOLVED_OBSERVATION_IDENTITY` (unchanged) | both `UNVERIFIED` |
| **R3c (new)** | same `observation_id`, different `assessment_id`, `NOT_ESTABLISHED` | **label deferred** (§25.13) | bounded by §25.9.7: never `INELIGIBLE`; exact effect deferred |
| R4a | different `observation_id`, D equal, `ESTABLISHED_DIFFERENT` | `SAME_INPUT_DIFFERENT_METHODOLOGY` (unchanged) | none |
| R4b | different `observation_id`, D equal, `ESTABLISHED_EQUAL`, same T, material output differs | `CONFLICTING_ASSESSMENT` (unchanged) | both `INELIGIBLE` |
| R4c | different `observation_id`, D equal, `ESTABLISHED_EQUAL`, and R4b does not match (the explicit complement within this state) | `UNRESOLVED_INPUT_SET_DIFFERENCE` | both `UNVERIFIED`; retain every difference; no conflict or equivalence inferred |
| **R4d (new)** | different `observation_id`, D equal, `NOT_ESTABLISHED` | For the equal-XC, different-delivery case defined below: `UNRESOLVED_INPUT_SET_DIFFERENCE`. For other R4d cases: label deferred (§25.13). Never `CONFLICTING_*`, `SAME_INPUT_DIFFERENT_METHODOLOGY` or `EQUIVALENT_*`. | For that delivery discrepancy: both `UNVERIFIED`; otherwise exact effect deferred, never `INELIGIBLE` |
| R5 | different `observation_id`, D differs, `ESTABLISHED_EQUAL`, `any_different` | `CONFLICTING_OBSERVATION` (unchanged) | all `INELIGIBLE` |
| R6 | as R5, `all_compared_equal`, at least one compared | `EQUIVALENT_ON_COMPARED_METRICS` (unchanged) | none |
| R7 | as R5, `none_compared` | `UNRESOLVED_INPUT_SET_DIFFERENCE` (unchanged) | all `UNVERIFIED` |
| R8 | different `observation_id`, D differs, `ESTABLISHED_DIFFERENT` **or `NOT_ESTABLISHED`** | `UNRESOLVED_INPUT_SET_DIFFERENCE` (unchanged) | all `UNVERIFIED`; metrics `UNKNOWN: METHODOLOGY_DIFFERS` or `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED` |
| R10 | unchanged text; `any_different` now requires `ESTABLISHED_EQUAL` through §25.12.1 | `CONFLICTING_OBSERVATION` | all `INELIGIBLE` |

**Equal-D/delivery discrepancy (B2, normative proposed disposition).** Within one slot and T, hold exposed content and AC unchanged, hold `(algorithm, digest)` and section kind equal, but change a delivery field (the mandatory probe changes only `InputSetRef.delivery.received_timestamp`). L5 and `observation_id` differ while XC stays equal. Preserve both variants and the actual delivery discrepancy; do not repair a delivery, recompute an upstream digest, merge the observations, or claim complete raw-input equality. §21.6 explicitly preserves this source inconsistency.
- `ESTABLISHED_EQUAL`: R4b does not match, so R4c yields `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`.
- `NOT_ESTABLISHED` (including EMPTY registry, a caller-only methodology or an undischargeable hidden code): R4d yields the same unresolved relation, both `UNVERIFIED`; every metric is `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED`.
- `ESTABLISHED_DIFFERENT`: R4a retains precedence, yielding `SAME_INPUT_DIFFERENT_METHODOLOGY`, no eligibility harm from that relation, and `UNKNOWN: METHODOLOGY_DIFFERS`. The delivery discrepancy remains visible; the two variants are not merged. This state requires independent mapping-validation evidence, never an inference from delivery or equal D.
`RECEIPT_VARIANT` records the receipt-only case; other delivery differences retain applicable existing informational flags. These flags confer no trust. Relation effects combine with pre-existing roles using §5.2; an unresolved relation never upgrades an already worse role.

**Rule ordering, replacing the v3.6 block.** For each in-scope pair, evaluate in this order and stop at the first match:
1. Same `observation_id`: R1, R2, R3, R3a, R3b, R3c.
2. Different `observation_id` with D equal: **methodology first**. R4a (`ESTABLISHED_DIFFERENT`); R4b then its explicit complement R4c (`ESTABLISHED_EQUAL`); R4d (`NOT_ESTABLISHED`). R4c includes unchanged exposed output with different delivery, UNKNOWN-only differences and coverage-only differences not satisfying R4b. No caller assertion may manufacture an ESTABLISHED state.
3. Different `observation_id` with D different: R5, R6 and R7 (`ESTABLISHED_EQUAL`), then R8 (otherwise).
4. No digest on either side: R9, R10, R10a.
5. R11 applies inside metric comparison, as before.

**Consequence.** No pair whose state is not `ESTABLISHED_EQUAL` can reach R3a, R4b, R5, R6 or R10. No pair whose state is not `ESTABLISHED_DIFFERENT` can reach R3 or R4a.

**§5.4 bullets amended:**
- R4a, R4b/R4c and R4d exhaustively partition the admitted **different-observation, equal-D domain** by the three exclusive states. Within `ESTABLISHED_EQUAL`, R4b and its complement R4c are disjoint and exhaustive, including unchanged XC with differing delivery. Every pair selects one branch; labels for non-delivery R4d cases remain explicitly deferred. This is not a claim that every deferred routing case elsewhere (notably C13, R1/R2 prerequisites or unequal digest availability) has been resolved.
- Same `observation_id` rows: R3, R3a/R3b and R3c are disjoint for the same reason.
- The v3.1 `atr_period=2` versus `3` guarantee holds as R4a **only when both sides are validated under one approved C09 mapping**. Otherwise the pair is R4d, which is still never a conflict.
- The inherited §5.4 receipt-, coverage- and candle-price guarantees are corrected in place in this v3.8 draft. All methodology-dependent conflict/equivalence claims, including the Expected column of §3.6 and the tests identified in §25.12.4, are conditional; structural equality is never a substitute for validated completeness. Other §5.4 statements remain subject to the explicit ordering and safety gates, not a separate route around them.

#### 25.12.3 §7 C13

**Same-`claim_id` bullet, first sub-bullet.** "C13 methodology `MI` is constant, so M is equal" is superseded:
- M is `ESTABLISHED_EQUAL` only under an approved C13 mapping and with equal `input_digest` (§25.9.3, §25.11).
- Otherwise M is `NOT_ESTABLISHED`, and the pair is never `CONFLICTING_ASSESSMENT`.
- With this v3.8 proposal's registry EMPTY, this sub-bullet cannot currently produce R4b.
- The second and third sub-bullets are unchanged.

**Methodology bullet.** `MI = {engine_version, VERIFICATION_POLICY_NOT_EXPOSED}` is restated as the C13 candidate of §25.11 (`engine_version`, `hidden_input_codes = ("VERIFICATION_POLICY_NOT_EXPOSED",)`). That candidate stays illustrative and unapproved.

**Inherited inconsistency recorded, not resolved [U].** §7 routes an equal-`input_digest` C13 pair to R4b, which requires "D equal". However, §7 also sets the C13 `input_set_ref.digest = null` and places `input_digest` in `AC`, so a C13 pair has no D and would fall to R9–R10a. Which routing applies is deferred to the relations design (§25.13).

#### 25.12.4 §12 acceptance tests

Some inherited expectations need methodology equal or different:
- **Need `ESTABLISHED_EQUAL`:** methodology-dependent conflict/equivalence branches of AT-B1-CX1…CX4, AT-B1-3 and the equal-period/different-output control in AT-B1-ATR-3. CX5/CX6 retain absence-is-UNKNOWN and no-equivalence outcomes without requiring equality; the reason codes follow the actual methodology state.
- **Need `ESTABLISHED_DIFFERENT`:** methodology-difference labels in AT-B1-5 and the differing-configuration branches of AT-B1-ATR-1…ATR-6. AT-B1-4 and AT-B1-ATR-5 retain R8 when D differs and methodology is NOT_ESTABLISHED, but their reason becomes METHODOLOGY_NOT_ESTABLISHED rather than METHODOLOGY_DIFFERS. AT-B1-ATR-3 explicitly contains both a differing-method branch and the separate equal-method control above.

These expectations are **conditional on both sides being validated under one approved mapping** (C09 for the candle cases), and satisfying the stated ESTABLISHED state, not merely having equal config or equal identifiers. The §3.6 Expected column and every corresponding §5.4 guarantee are subject to the same condition. AT-B1-9 is corrected in place: under the C07 hidden-threshold condition its differing-best-bid branch requires an unresolved result, not a conflict. A future upstream change that exposes thresholds would require its own mapping approval; this draft does not assume it. Until such a mapping exists, the required behavior is the `NOT_ESTABLISHED` behavior of §25.12.2:
- no `CONFLICTING_*`, `EQUIVALENT_ON_COMPARED_METRICS` or `SAME_INPUT_DIFFERENT_METHODOLOGY`;
- every metric `UNKNOWN: METHODOLOGY_NOT_ESTABLISHED`.

**Legacy correction matrix (normative for future acceptance tests):**

| Inherited expectation | ESTABLISHED prerequisite / retained behavior | NOT_ESTABLISHED outcome |
|---|---|---|
| §3.6 CX-1…CX-6; AT-B1-CX1…CX6; §5.4 candle, receipt and coverage guarantees | Conflict or compared-metric equivalence requires `ESTABLISHED_EQUAL` and each original row's digest/window prerequisites; absence remains UNKNOWN | For those differing-D fixtures: R8, `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`; all metrics UNKNOWN with `METHODOLOGY_NOT_ESTABLISHED`; actual values and informational receipt/coverage differences remain visible |
| AT-B1-3 and AT-B1-ATR-3 equal-period/material-difference control | Conflict requires `ESTABLISHED_EQUAL`, same T, the applicable observation/raw-identity prerequisites, and all activation gates of §25.13; R4b only for different observations, R3a/R3b for same-observation AC variants | Different observations with equal D: R4d, no conflict, equivalence or methodology-difference claim; same-observation variants not covered by R1/R2: R3c, likewise unresolved and never INELIGIBLE; exact general labels remain deferred except the B2 case |
| AT-B1-4, AT-B1-5, AT-B1-ATR-1…ATR-6 differing-method branches | `ESTABLISHED_DIFFERENT` is required for a methodology-difference label; R8 remains unresolved when D differs. AT-B1-ATR-3 contains the separate equal-method control above | Equal D/different observations: R4d; different D: R8; same-observation/different-assessment variants not covered by R1/R2: R3c. No false conflict or methodology-difference label; all metrics UNKNOWN with `METHODOLOGY_NOT_ESTABLISHED` |
| AT-B1-9, C07 same snapshot/provenance/config, differing best bids | QT is undischargeable; this scenario cannot reach `ESTABLISHED_EQUAL`, even under a future approved mapping with those disclosures | No digest and differing XC: R10a, `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`; retain both best-bid values, no merge, no conflict, no raw equality or independence claim |
| AT-B1-9 identical exposed content; R1/R2/R9 structural paths | Keep only their own structural/raw-identity prerequisites. `EQUIVALENT_AS_EXPOSED` is not economic or methodology equivalence | Structural R1/R2/R9 conditions do not establish completeness. No new route to compared-metric equivalence, conflict or source identity is added |
| AT-B1-12, AT-B1-13 and AT-B1-14 | Preserve flags, corrected branch eligibility and permutation determinism | No informational receipt/coverage flag overrides UNKNOWN comparisons or raises NOT_ESTABLISHED to INELIGIBLE |

**Added relations acceptance cases (contract text only):**
- **AT-MT-REL-B1-C07:** use the two revalidated C07 reports described in AT-B1-9. Verify both original values are preserved and the exact R10a/UNKNOWN outcome above. Same provenance does not merge them.
- **AT-MT-REL-B1-C09:** identical OHLCV with changed per-record receipt metadata changes the C09 digest. With an EMPTY registry, verify R8, `RECEIPT_VARIANT`, both `UNVERIFIED`, and no conflict or compared-metric equivalence. With separately evidenced `ESTABLISHED_EQUAL`, test R6 only when at least one metric compares equal; otherwise R7. Neither fixture activates a mapping.
- **AT-MT-REL-HIDDEN-DIFF:** under one synthetic validated mapping in a future relations test, expose a config or rule-digest difference available on both sides and retain QT on both. The state is `ESTABLISHED_DIFFERENT`, but QT remains undischargeable; never `ESTABLISHED_EQUAL`, no metric comparison and no definitive conflict. Equal exposed components with QT instead force `NOT_ESTABLISHED`. An unavailable-only or hidden-code-only difference also remains `NOT_ESTABLISHED`.
- **AT-MT-REL-B2-DELIVERY:** start with the approved Slice 5 O2 components, clone the input reference, and increase only `delivery.received_timestamp` by one second while preserving its digest pair, Slot, coverage, metrics, basis, T and AC. Verify equal Slot/XC/D and different L5/observation identifiers. With the EMPTY registry the mandatory outcome is R4d, `UNRESOLVED_INPUT_SET_DIFFERENCE`, both `UNVERIFIED`, `RECEIPT_VARIANT`, and no merge/conflict/compared-metric-equivalence inference. Neither receipt differences nor identifier equality establish lineage; any independent D-based lineage decision remains gated by §25.13. Enumerate the other two methodology states using independently supplied future test evidence: R4c for `ESTABLISHED_EQUAL`; R4a for `ESTABLISHED_DIFFERENT`. Changing D or the receipt must not itself create that evidence.
- **AT-MT-REL-R4-PARTITION:** enumerate the three methodology states and R4b true/false within the different-observation/equal-D domain. R4a, R4b, R4c, R4d are mutually exclusive and cover that domain. Include UNKNOWN-only, coverage-only and delivery-only differences; test both input orders. Do not infer global routing completeness for expressly deferred cases.

The future relations slice must test this behavior (§25.16, AT-MT-REL). These cases do not implement or authorize relations or runtime equivalence in Slice 6. Synthetic validation evidence in a future test never populates the production registry.

### 25.13 Deferred relation decisions [DEFERRED to the relations design; not decided here]

1. **Labels for R3c and non-delivery R4d cases.** Candidates remain deferred. The equal-XC/different-delivery R4d subcase alone now has the existing `UNRESOLVED_INPUT_SET_DIFFERENCE` label specified by §25.12.2. This selects no new relation type and no general unresolved-methodology label. All cases obey §25.9.7.
2. **Exact eligibility effect for R3c and non-delivery R4d cases.** Deferred and bounded: never `INELIGIBLE`. The equal-XC/different-delivery R4d subcase has the explicit `UNVERIFIED` relation effect in §25.12.2; pre-existing worse roles are not upgraded.
3. **`SHARED_INPUT_VERIFIED` for R4d pairs.** Whether an R4d pair still carries the `SHARED_INPUT_VERIFIED` edge. The edge depends on D only (§6.1), so the likely answer is yes, but this is a lineage decision.
4. **R1 and R2.** Whether they need a methodology-state condition. They depend on `assessment_id`, which is deferred.
5. **Evidence form.** The form of the validation evidence of §25.9.2, held by the evaluator.
6. **C13 routing.** The inconsistency of §25.12.3 remains unresolved and gated. No C13 comparison route may activate until a separately reviewed/approved relations design resolves the no-L5-digest and same-observation prerequisites. This amendment approves no C13 mapping and neither routes its assessment-input digest into D nor changes its identity layers.
7. **Blocker, not solved by `methodology_id`.** Caller-asserted continuity, recovery and coverage inputs change trust and metric withholding without entering any identity layer.
   - **[F]** C09 passes the `continuity` and `recovery` arguments into its quality assessment (`derivatives/analytics.py:293`).
   - **[F]** C10 re-assesses upstream quality using the upstream `continuity` and `recovery` (`regime/engine.py:516-517`).
   - The effect: two reports with equal input, an `ESTABLISHED_EQUAL` methodology and different assertions can differ in `ac_id`. That would wrongly match R3a or R4b.

   The `ac_id`-difference branches of R3a and R4b **must not be activated** until those assertions are bound or excluded. This is a blocker for the relations slice.

### 25.14 Golden vectors and complete ID_JSON fixtures [PROPOSED]

**Provenance of these values.** Each vector was computed in a scratch run on `main` at `ebb9cf9` by two encoders:
- the **repository serializer** (`id_digest` and `id_json`);
- a **separate encoder** written from §4. It imports nothing from `traid`, and implements its own Decimal, datetime, timedelta, int, seq and map rules, and envelope.

Results:
- All 15 identifiers and all 15 `ID_JSON(P)` strings agree byte for byte between the two encoders.
- Runs under `PYTHONHASHSEED=0` and `12345` produced byte-identical output.

This shows that two encoders agree. It is not an audit. The second encoder was written by the same author (Claude Code).

**These are structural encoding fixtures, not source mappings.**
- `mapping_id = "fixture-mapping-1"` and the digests of 64 `c` or 64 `d` characters are fixture values. They are not registry entries.
- The engine versions, `schema_version = "1.0"` and the policy versions are verified repository strings. Their use here does not claim that any adapter produces these values.

The inputs are listed as the seven `Methodology` fields. `P` follows from §25.6 and is shown in full as `ID_JSON(P)`.

**Base fixtures:**
- **`C09CFG`:** `atr_period=2`, `base_asset="BTC"`, `funding_lookback_hours=24`, `momentum_lookbacks=(1, 3)`, `quote_currency="USD"`, `session_start=None`, `volatility_period=3`.
- **`ORD`:** `({quantity: Decimal("1.50"), side: "BUY"}, {quantity: Decimal("1.50"), side: "BUY"}, {quantity: Decimal("2"), side: "SELL"})`.
- **`QT`:** `QUALITY_THRESHOLDS_NOT_EXPOSED`.
- **`QV`:** `QUALITY_POLICY_VERSION_NOT_EXPOSED`.

| Vector | `mapping_id` | `engine_version` | `schema_version` | `config` | `rule_digests` | `quality_policy_version` | `hidden_input_codes` | `methodology_id` |
|---|---|---|---|---|---|---|---|---|
| M1 C09-style base | `None` | `c09-derivatives-1` | `"1.0"` | `C09CFG` | `()` | `"c09-hourly-freshness-1"` | `()` | `mt1:44de4c476da4631e0eaca61eebcfbfe783f5fa40b28f855d5159b2b5ea8e3a1f` |
| M2 config change | as M1 | as M1 | as M1 | `C09CFG` with `atr_period=3` | `()` | as M1 | `()` | `mt1:d172ac27a95b245ad395f4bf3eb8f239d748d45ca6783277fca3e7109c818579` |
| M3 `mapping_id` change | `"fixture-mapping-1"` | as M1 | as M1 | `C09CFG` | `()` | as M1 | `()` | `mt1:f9a7218e9af27711c5560b360760ff673ed78cd746cab1b03f08b6758f55bea6` |
| M4 hidden code | `None` | as M1 | as M1 | `C09CFG` | `()` | as M1 | `(QT,)` | `mt1:f9590aa74851f52c7d4a8311a8d828a49c62e600d64cea8e7bfbd4d829a09639` |
| M5 omitted entry | `None` | as M1 | as M1 | `C09CFG` without `session_start` | `()` | as M1 | `()` | `mt1:aac008661859b6ef5b3b884d87450118c38d43c6bd8c19524559c56f8cd31482` |
| M6 C07-style base | `None` | `c07-liquidity-1` | `"1.0"` | `bands_bps=(Decimal("10"), Decimal("25.5"))`, `base_asset="BTC"`, `orders=ORD`, `quote_currency="USD"` | `()` | `"c05-policy-1"` | `(QT,)` | `mt1:f41685b45d062dd460c8e8450f28f82cd29d84c000ef698acc8ac876c2dfcf74` |
| M6a Decimal spelling | as M6 | as M6 | as M6 | as M6, with `bands_bps=(Decimal("10.00"), Decimal("25.50"))` and order quantities `Decimal("1.5")`, `Decimal("1.5")`, `Decimal("2.000")` | `()` | as M6 | as M6 | `mt1:f41685b45d062dd460c8e8450f28f82cd29d84c000ef698acc8ac876c2dfcf74` (= M6) |
| M6b order changed | as M6 | as M6 | as M6 | as M6, with `orders=(ORD[2], ORD[0], ORD[1])` | `()` | as M6 | as M6 | `mt1:3ba20733e4150c21aa2ce57817228754d6e6c6606ea74e507282afec825f803b` |
| M6c duplicate removed | as M6 | as M6 | as M6 | as M6, with `orders=(ORD[0], ORD[2])` | `()` | as M6 | as M6 | `mt1:62982af385acdf57512e6d228c55aab46fbc5b489f2eade286e97c6855d20690` |
| M7 C08-style base | `None` | `c08-trade-flow-1` | `"1.0"` | `base_asset="BTC"`, `late_tolerance=timedelta(seconds=5)`, `session_start=2026-01-01T00:00:00Z`, `window=timedelta(hours=1)` | `()` | `None` | `(QV, QT)` | `mt1:0f66d22ab2195b0c8c7d4a484071e28102cc1ff10072909479fb3b002f7116d1` |
| M7a timedelta and zone equivalence | as M7 | as M7 | as M7 | as M7, with `window=timedelta(minutes=60)` and `session_start=2026-01-01T01:00:00+01:00` | `()` | `None` | `(QV, QT)` | `mt1:0f66d22ab2195b0c8c7d4a484071e28102cc1ff10072909479fb3b002f7116d1` (= M7) |
| M7b null versus value | as M7 | as M7 | as M7 | as M7 | `()` | `"c05-policy-1"` | `(QT,)` | `mt1:1e24ee565ce50a191e9c809e4b3bc012135b8956af7f177b132556b3f25f332d` |
| M8 C10-style named digest (liquidity-like) | `None` | `c10-market-state-1` | `"1.0"` | `()` | `(rules, sha256-canonical-rules-v1, "c"×64)` | `None` | `(QV, QT)` | `mt1:e621823b29f68985eebd60fda7b2e4341b7e14c375551cb8cd2827bb0598fdac` |
| M8a digest change | as M8 | as M8 | as M8 | `()` | `(rules, sha256-canonical-rules-v1, "d"×64)` | `None` | `(QV, QT)` | `mt1:32966b90aa40463df997a6d033f2bcac0faea58af6c114eb3f6b860c8a5f6913` |
| M8b C10-style, no hidden codes (direction-like) | as M8 | as M8 | as M8 | `()` | as M8 | `None` | `()` | `mt1:32fd1b43dfa5c61d5f65f97960bbe97b99475b9968ce647b4aaad0b2a652924c` |

`(QV, QT)` is the strictly ascending order of the two codes.

**Complete `ID_JSON(P)`, one per distinct identifier.** The `ID_JSON(P)` of M6a is byte-identical to that of M6, and that of M7a to that of M7 (verified).

`M1`:

`{"$":"map","v":[["config",{"$":"map","v":[["atr_period",{"$":"int","v":"2"}],["base_asset","BTC"],["funding_lookback_hours",{"$":"int","v":"24"}],["momentum_lookbacks",{"$":"seq","v":[{"$":"int","v":"1"},{"$":"int","v":"3"}]}],["quote_currency","USD"],["session_start",null],["volatility_period",{"$":"int","v":"3"}]]}],["engine_version","c09-derivatives-1"],["hidden_input_codes",{"$":"seq","v":[]}],["mapping_id",null],["quality_policy_version","c09-hourly-freshness-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M2`:

`{"$":"map","v":[["config",{"$":"map","v":[["atr_period",{"$":"int","v":"3"}],["base_asset","BTC"],["funding_lookback_hours",{"$":"int","v":"24"}],["momentum_lookbacks",{"$":"seq","v":[{"$":"int","v":"1"},{"$":"int","v":"3"}]}],["quote_currency","USD"],["session_start",null],["volatility_period",{"$":"int","v":"3"}]]}],["engine_version","c09-derivatives-1"],["hidden_input_codes",{"$":"seq","v":[]}],["mapping_id",null],["quality_policy_version","c09-hourly-freshness-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M3`:

`{"$":"map","v":[["config",{"$":"map","v":[["atr_period",{"$":"int","v":"2"}],["base_asset","BTC"],["funding_lookback_hours",{"$":"int","v":"24"}],["momentum_lookbacks",{"$":"seq","v":[{"$":"int","v":"1"},{"$":"int","v":"3"}]}],["quote_currency","USD"],["session_start",null],["volatility_period",{"$":"int","v":"3"}]]}],["engine_version","c09-derivatives-1"],["hidden_input_codes",{"$":"seq","v":[]}],["mapping_id","fixture-mapping-1"],["quality_policy_version","c09-hourly-freshness-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M4`:

`{"$":"map","v":[["config",{"$":"map","v":[["atr_period",{"$":"int","v":"2"}],["base_asset","BTC"],["funding_lookback_hours",{"$":"int","v":"24"}],["momentum_lookbacks",{"$":"seq","v":[{"$":"int","v":"1"},{"$":"int","v":"3"}]}],["quote_currency","USD"],["session_start",null],["volatility_period",{"$":"int","v":"3"}]]}],["engine_version","c09-derivatives-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version","c09-hourly-freshness-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M5`:

`{"$":"map","v":[["config",{"$":"map","v":[["atr_period",{"$":"int","v":"2"}],["base_asset","BTC"],["funding_lookback_hours",{"$":"int","v":"24"}],["momentum_lookbacks",{"$":"seq","v":[{"$":"int","v":"1"},{"$":"int","v":"3"}]}],["quote_currency","USD"],["volatility_period",{"$":"int","v":"3"}]]}],["engine_version","c09-derivatives-1"],["hidden_input_codes",{"$":"seq","v":[]}],["mapping_id",null],["quality_policy_version","c09-hourly-freshness-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M6` (and `M6a`):

`{"$":"map","v":[["config",{"$":"map","v":[["bands_bps",{"$":"seq","v":[{"$":"dec","v":"1e1"},{"$":"dec","v":"255e-1"}]}],["base_asset","BTC"],["orders",{"$":"seq","v":[{"$":"map","v":[["quantity",{"$":"dec","v":"15e-1"}],["side","BUY"]]},{"$":"map","v":[["quantity",{"$":"dec","v":"15e-1"}],["side","BUY"]]},{"$":"map","v":[["quantity",{"$":"dec","v":"2e0"}],["side","SELL"]]}]}],["quote_currency","USD"]]}],["engine_version","c07-liquidity-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version","c05-policy-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M6b`:

`{"$":"map","v":[["config",{"$":"map","v":[["bands_bps",{"$":"seq","v":[{"$":"dec","v":"1e1"},{"$":"dec","v":"255e-1"}]}],["base_asset","BTC"],["orders",{"$":"seq","v":[{"$":"map","v":[["quantity",{"$":"dec","v":"2e0"}],["side","SELL"]]},{"$":"map","v":[["quantity",{"$":"dec","v":"15e-1"}],["side","BUY"]]},{"$":"map","v":[["quantity",{"$":"dec","v":"15e-1"}],["side","BUY"]]}]}],["quote_currency","USD"]]}],["engine_version","c07-liquidity-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version","c05-policy-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M6c`:

`{"$":"map","v":[["config",{"$":"map","v":[["bands_bps",{"$":"seq","v":[{"$":"dec","v":"1e1"},{"$":"dec","v":"255e-1"}]}],["base_asset","BTC"],["orders",{"$":"seq","v":[{"$":"map","v":[["quantity",{"$":"dec","v":"15e-1"}],["side","BUY"]]},{"$":"map","v":[["quantity",{"$":"dec","v":"2e0"}],["side","SELL"]]}]}],["quote_currency","USD"]]}],["engine_version","c07-liquidity-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version","c05-policy-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M7` (and `M7a`):

`{"$":"map","v":[["config",{"$":"map","v":[["base_asset","BTC"],["late_tolerance",{"$":"td","v":"5000000"}],["session_start",{"$":"dt","v":"2026-01-01T00:00:00.000000Z"}],["window",{"$":"td","v":"3600000000"}]]}],["engine_version","c08-trade-flow-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_POLICY_VERSION_NOT_EXPOSED","QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version",null],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M7b`:

`{"$":"map","v":[["config",{"$":"map","v":[["base_asset","BTC"],["late_tolerance",{"$":"td","v":"5000000"}],["session_start",{"$":"dt","v":"2026-01-01T00:00:00.000000Z"}],["window",{"$":"td","v":"3600000000"}]]}],["engine_version","c08-trade-flow-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version","c05-policy-1"],["rule_digests",{"$":"map","v":[]}],["schema_version","1.0"]]}`

`M8`:

`{"$":"map","v":[["config",{"$":"map","v":[]}],["engine_version","c10-market-state-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_POLICY_VERSION_NOT_EXPOSED","QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version",null],["rule_digests",{"$":"map","v":[["rules",{"$":"map","v":[["algorithm","sha256-canonical-rules-v1"],["digest","cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"]]}]]}],["schema_version","1.0"]]}`

`M8a`:

`{"$":"map","v":[["config",{"$":"map","v":[]}],["engine_version","c10-market-state-1"],["hidden_input_codes",{"$":"seq","v":["QUALITY_POLICY_VERSION_NOT_EXPOSED","QUALITY_THRESHOLDS_NOT_EXPOSED"]}],["mapping_id",null],["quality_policy_version",null],["rule_digests",{"$":"map","v":[["rules",{"$":"map","v":[["algorithm","sha256-canonical-rules-v1"],["digest","dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"]]}]]}],["schema_version","1.0"]]}`

`M8b`:

`{"$":"map","v":[["config",{"$":"map","v":[]}],["engine_version","c10-market-state-1"],["hidden_input_codes",{"$":"seq","v":[]}],["mapping_id",null],["quality_policy_version",null],["rule_digests",{"$":"map","v":[["rules",{"$":"map","v":[["algorithm","sha256-canonical-rules-v1"],["digest","cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"]]}]]}],["schema_version","1.0"]]}`

**Sensitivity:**

| Pair | What changes | Result |
|---|---|---|
| M1 / M2 | one config value | ids differ |
| M1 / M3 | `None` versus a `mapping_id` | ids differ. Methodologies under different mappings never collide (§25.9.5, item 2). |
| M1 / M4 | one hidden code | ids differ. Under one mapping, a difference only in codes never gives `ESTABLISHED_DIFFERENT` (§25.9.4). |
| M1 / M5 | an entry with value `None` versus an omitted entry | ids differ, so an explicit null is not an omission. A mapping inventory rejects the omission (§25.10, item 4). |
| M6 / M6a | Decimal spelling only | **equal** (§4.3) |
| M6 / M6b | sequence order | ids differ; source order is significant |
| M6 / M6c | duplicate removed | ids differ; duplicates are preserved |
| M7 / M7a | timedelta spelled as 60 minutes, `session_start` given in `+01:00` | **equal**; timedelta equivalence and UTC normalization |
| M7 / M7b | unavailable (`None` with `QV`) versus an explicit version | ids differ. Under one mapping, this difference is unavailable on one side, so it can never give `ESTABLISHED_DIFFERENT`. |
| M8 / M8a | the named rules digest | ids differ |
| M8 / M8b | hidden codes of a liquidity-like versus a direction-like C10 dimension | ids differ |

Thirteen distinct identifiers result: the 15 vectors minus the two equalities.

### 25.15 Deliberate departures from v3.6 [PROPOSED]

| # | v3.6 | v3.8 (proposed) |
|---|---|---|
| J1 | L6 `MI` is described in prose, with "rule/mapping digests" | closed seven-field `Methodology`, with `mapping_id` separated from `rule_digests` (§25.3) |
| J2 | no type policy for config values (§19.1, §19.11) | bounded `ConfigValue` policy (§25.4) |
| J3 | `methodology_id` formula only | API, explicit projection, structural-equality limits (§25.6, §25.7) |
| J4 | "M equal" and "M differs" are read from `methodology_id` | three exclusive comparison states, plus STRUCTURALLY_EQUAL (§25.9) |
| J5 | §3.4 `UNKNOWN if methodology_id differs` | `UNKNOWN` unless `ESTABLISHED_EQUAL`; new reason `METHODOLOGY_NOT_ESTABLISHED` (§25.12.1) |
| J6 | §5.3 R3–R8 and R10 keyed on `methodology_id` | keyed on the state; R3c/general R4d labels deferred, except the bounded equal-XC/different-delivery R4d disposition (§25.12.2) |
| J7 | §7 "C13 `MI` is constant, so M is equal" | equal only under an approved mapping with equal `input_digest` (§25.12.3) |
| J8 | no mapping-registry contract | registry requirements, registry EMPTY (§25.10) |
| J9 | `Methodology` and `methodology_id` prohibited or deferred (§19.1, §19.9, §21.10, §21.11, §23.12) | superseded for these two items only, on approval; implementation still needs a separate authorization |

### 25.16 Implementation scope boundaries (binding only once separately authorized) [PROPOSED]

**Allowed, after a separate owner authorization:**
- the five models and the `methodology_id` function, in one new module (intended: `src/traid/fusion/methodology_identity.py`; file names are fixed by the authorization);
- one new test file;
- additive exports in `src/traid/fusion/__init__.py`;
- a per-file import-policy entry allowing only `__future__`, `datetime`, `decimal`, `typing`, `pydantic`, `traid.fusion.models` and `traid.fusion.serialization`;
- only the narrowly enumerated existing-test compatibility edits below, during separately authorized implementation. No executable test is changed by this proposal.

**Existing-test compatibility exceptions (B3):**
1. In `tests/test_fusion_serialization.py`, add only the new module's file-specific import policy and the exact additive export symbols imported by `fusion/__init__.py`. Keep every pre-existing file's policy unchanged except that exact additive import/export entry in `__init__.py`; especially preserve the serializer policy. No wildcard or blanket allowlist, skipped assertion or unauthorized dependency is permitted.
2. In `tests/test_fusion_input_identity.py::test_identity_equality_carries_no_lineage_or_source_mapping_authority`, remove only `Methodology` and `methodology_id` from the package-level prohibited-export set, if those exports are added. Preserve `assessment_id`, `EvidenceUnit`, `fuse`, `LineageEdge`, `Relation` and every other assertion verbatim.
3. In `tests/test_fusion_observation_identity.py::test_public_scope_and_plain_composition`, remove only `Methodology` and `methodology_id` from the package-level prohibited-export set, if those exports are added. Preserve `EvidenceUnit`, `assessment_id`, `ac_id`, `fuse`, and every other assertion verbatim.
4. Do not alter the module-local scope assertion in `tests/test_fusion_identity.py`; the existing identity module must not import these new symbols. No other existing test change is authorized by this compatibility exception. Run and inspect the full suites after the explicit changes; do not skip, delete, broaden failure reasons, or weaken numeric, temporal, privacy or authority coverage.

**Required tests:**
1. **AT-MT-1 vectors.** M1–M8b reproduce the pinned identifiers and the byte-exact `ID_JSON(P)` strings. M6 equals M6a, M7 equals M7a, and there are exactly 13 distinct identifiers.
2. **AT-MT-2 projection capture.** `id_digest` is called once with the tag `c15.mt.v1` and a plain `P` with exactly seven keys. `P` contains no model, enum, list, set or `Unordered`. A test fails if `P` is produced by `model_dump`.
3. **AT-MT-3 strict type admission.** In every text position (`mapping_id`, `engine_version`, `schema_version`, `quality_policy_version`, entry and field names, codes, `algorithm`, text config values), the test rejects:
   - a `StrEnum` member, a `str` subclass, empty text and padded text;
   - bad name, code or `mapping_id` patterns.
4. **AT-MT-4 enum and float rejection.**
   - `float`, `bool` (as an int) and `IntEnum` are rejected in every scalar position.
   - A `Side`-like `StrEnum` is rejected inside a record.
   - Decimal NaN and infinity are rejected.
5. **AT-MT-5 unsupported nested values.** Each is rejected:
   - `list` where a tuple is required;
   - `dict` as a config value;
   - `set`, `frozenset`, `Unordered`;
   - a nested sequence, a sequence inside a record;
   - `None` inside a sequence or record, an empty record;
   - `date`, `time`, `bytes`;
   - a naive datetime or an unaccepted `tzinfo`; text must never be parsed into datetime and int must never be converted into timedelta/Decimal. An exact int or unpadded ISO-looking text is independently admissible as its generic scalar type, not as an implicitly inferred source-field type; mapping-specific mismatch rejection is a future mapping test;
   - subclasses of `Decimal`, `timedelta`, `datetime`, `tuple`, `int` and `str`;
   - a Pydantic source model (for example a real `OrderRequest`).
6. **AT-MT-6 missing and unexpected fields.**
   - Omitting each of the seven fields is rejected, as is each nested field.
   - An unexpected field is rejected at every level.
   - An explicit `None` is accepted only where §25.3 allows it.
7. **AT-MT-7 ordering and uniqueness.** Each of these is rejected, never sorted or deduplicated: unsorted or duplicate config names, rule-digest names, record field names and codes. Sequence values keep their order and duplicates.
8. **AT-MT-8 invariant.** A non-null `quality_policy_version` together with `QUALITY_POLICY_VERSION_NOT_EXPOSED` is rejected.
9. **AT-MT-9 forged-model revalidation.** Each of these, at the top level and nested, is rejected before hashing: `model_construct` with an invalid value, `object.__setattr__`, editing `__dict__`, and `model_copy(update=...)`.
10. **AT-MT-10 deterministic encoding.**
    - Dictionary insertion order and time-zone spelling do not change the result.
    - Two subprocesses with different `PYTHONHASHSEED` values give byte-identical identifiers.
11. **AT-MT-11 mutation sensitivity.** The tests must detect each of these mutations:
    - a dropped or renamed key, a changed prefix or tag;
    - sorting instead of rejecting;
    - removed revalidation, removed exact-`str` check, removed `bool` rejection;
    - a record projected as a sequence;
    - a `model_dump`-based projection.
12. **AT-MT-12 import purity and name scan.**
    - The module imports only the allowed list. There are no imports from `traid.liquidity`, `traid.flow`, `traid.derivatives`, `traid.regime`, `traid.news`, `traid.quality`, `traid.ai` or any network or AWS module.
    - The §9 name scan passes.
    - `ROLE_RULES_ACTIVE == ()`, and `EvidenceRole` keeps five members.
    - No score, probability or forecast name appears.
13. **AT-MT-13 no runtime equivalence and no registry.** The module defines no comparison-state enum or function, no registry, and no mapping constant. `METHODOLOGY_NOT_ESTABLISHED` is not introduced into code by Slice 6.
14. **AT-MT-14 regressions.**
    - The Slice 1–5 suites pass with only the explicit B3 import-policy/export-guard compatibility edits enumerated above. All other existing tests and assertions are unchanged. A diff assertion must prove the two export sets lost only `Methodology` and `methodology_id`; all remaining prohibited symbols stay checked.
    - `serialization.py`, `identity.py`, `input_identity.py`, `observation_identity.py` and `models.py` are unchanged.
15. **AT-MT-REL (relations slice, not Slice 6).** All §25.12.4 legacy-matrix and added cases: B1-C07, B1-C09, HIDDEN-DIFF, B2-DELIVERY and R4-PARTITION, with the three methodology states and no mapping activated.
16. **AT-MT-ADMISSION-BEFORE:** demonstrate that an unguarded strict Pydantic tuple adapter admits a tuple subclass, then require the proposed exact-type admission guard to reject it before coercion at every tuple/scalar nesting position. Ordinary exact tuples, ints, strings, finite Decimals and supported datetime/timedelta objects stay accepted. This is future test specification, not implementation here.
17. **AT-MT-TZ-NO-CALLBACK:** pass an exact datetime with a custom tzinfo whose `utcoffset`, `dst` and `tzname` methods count calls and raise. The proposed admission boundary must reject it with all counters zero, directly and nested; also reject datetime subclasses before their overrides. Verify supported timezone.utc, fixed offsets, ZoneInfo fold instants and Pydantic TzInfo through the unchanged serializer boundary. Do not mock normalization into accepting the invalid timezone.
18. **AT-MT-SCALAR-SEMANTICS:** exact int 3600 and ISO-looking text remain their original generic scalar types; their identities differ from timedelta(seconds=3600) and an equivalent datetime. No field name causes conversion. Separately specified future mapping tests must reject wrong source-field types; Slice 6 implements no mapping validation.

**Prohibited:**
- `assessment_id`, `ac_id`, `AssessmentContent`, `EvidenceUnit`;
- source adapters, and any active or populated mapping-registry entry;
- runtime methodology-equivalence evaluation, and any comparison-state type;
- relations, lineage, `fuse()`;
- the C10 composite and C12 selected-delivery mappings, `SELECTED_DELIVERY`;
- wallet references, ETF and FOMC mappings;
- any `KNOWN_EMPTY` construction path;
- any role other than the five of §10;
- any score, probability or forecast;
- any Strategy or Risk integration;
- any AI-derived input;
- any change to `serialization.py`, `UtcDatetime`, `Text`, or the Slice 3, 4 or 5 identifiers;
- Slice 7 and C16.

### 25.17 Owner approval checklist [HISTORICAL PRE-APPROVAL RECORD; IMPLEMENTATION STILL NOT AUTHORIZED]

- [ ] Approve the closed seven-field `Methodology`, its four value models and the single cross-field invariant (§25.3).
- [ ] Approve the bounded `ConfigValue` policy, including the exact-`str` rule that is stricter than Slice 2 `Text` (§25.4).
- [ ] Approve the fail-closed validation and the admission of validated mappings, or require instances only (§25.5).
- [ ] Approve the `methodology_id` API and the explicit projection with `mapping_id` included (§25.6), and the structural-equality limits (§25.7).
- [ ] Approve Design A, the four quality-policy distinctions and the derivation kinds (§25.8).
- [ ] Approve STRUCTURALLY_EQUAL and the three exclusive states, the validation-evidence rule, discharge, the forced-`NOT_ESTABLISHED` conditions and the safety invariant (§25.9).
- [ ] Approve `METHODOLOGY_NOT_ESTABLISHED` and the narrowing of `METHODOLOGY_DIFFERS` (§25.9.8).
- [ ] Approve the corrected §3.4, §5.3, §5.4, §7 and §12 requirements and acceptance matrix. R3c and general R4d labels stay deferred except the explicit equal-XC/different-delivery R4d disposition (§25.12, §25.13).
- [ ] Approve the mapping-registry requirements, reject-on-unknown-version, and the EMPTY registry (§25.10).
- [ ] Approve the hidden-code vocabulary: `QUALITY_THRESHOLDS_NOT_EXPOSED`, `QUALITY_POLICY_VERSION_NOT_EXPOSED`, `VERIFICATION_POLICY_NOT_EXPOSED` (§25.9.3).
- [ ] Confirm that the §25.11 candidates are illustrative and unapproved. Note the open C10 `schema_version` source and the whole-rules-digest choice.
- [ ] Approve the golden vectors and complete `ID_JSON` fixtures (§25.14).
- [ ] Approve the supersession for `Methodology` and `methodology_id` only (§25.2).
- [ ] Approve the contract route: this file as v3.8 only after a separate independent review and owner approval; any Spec §7 pointer change needs its own authorization. None is made here.
- [ ] Authorize the implementation scope of §25.16 in a separate task.

### 25.18 Unresolved issues and risks

- **[U] C09 version-bump risk.**
  - A C09 pair can reach `ESTABLISHED_EQUAL` only on the assumption that `formula_version` changes whenever C09's code constants or formulas change. Examples are `FRESHNESS_POLICY_VERSION`, the hourly freshness thresholds and the indicator code.
  - Nothing in the repository enforces this.
  - A silent code change under `c09-derivatives-1` would produce a false `ESTABLISHED_EQUAL`.
  - The §25.10 inventory check detects configuration-model field changes, not formula changes.
- **[U] Unbound caller assertions.** Continuity, recovery and coverage assertions are unbound (§25.13, item 7). This is a blocker for the relations slice that `methodology_id` does not solve.
- **[U] Units that can never be `ESTABLISHED_EQUAL`.** C07, C08 and the C10 liquidity and flow dimensions cannot reach `ESTABLISHED_EQUAL`, because C05 thresholds and C10's own policy are not exposed **[F]** (`quality/models.py:65-70`, `:99`; `regime/engine.py:1007-1011`). Changing this is an upstream decision outside C15.
- **[U] Phase 1 comparisons stay unresolved.** With the registry EMPTY, every methodology pair is `NOT_ESTABLISHED`; no methodology-dependent conflict or compared-metric equivalence is established. R1/R2/R9 retain only their own structural/raw-identity prerequisites, not a methodology-completeness claim. The corrected B1 tests require the §25.12.4 NOT_ESTABLISHED outcomes until mappings are separately approved. Unselected general relation labels and other routing dependencies remain gated; this proposal does not implement them.
- **[U] Inherited C13 routing inconsistency** (§25.12.3).
- **[U] C10 rules digest.** C15 does not recompute it. Its consistency rests on C10's own `bound_to_rules` validator during revalidation.
- **[U] Text admission differs across slices.** Slices 3–5 `Text` admits a `StrEnum` by converting it, while `Methodology` rejects it. This is disclosed, not reconciled; Slices 3–5 are unchanged.
- **[U] Snake-case naming assumption.** `Name` assumes snake-case source field names. This is verified for C07–C09 only.
- **[U] Second encoder by the same author.** The golden vectors were checked with a second encoder written by the same author. Independent verification by the auditor is still required.

---

## 26. CHANGES_V3_6_TO_V3_7 [HISTORICAL v3.7 PROPOSAL; §27 RECORDS v3.8 CHANGES]

Exactly these clauses change. Everything else is carried over from v3.6 unchanged.

| # | Clause | v3.6 | v3.7 (proposed) |
|---|---|---|---|
| I1 | Title, version identifier, new v3.7 note | `v3.6` | `v3.7-PROPOSED`, derived from v3.6, unapproved |
| I2 | §3.2 L6 row | prose `MI` | pointer sentence to §25.3 appended |
| I3 | §3.2 `methodology_id` line | formula only | pointer sentence to §25.6 and §25.7 appended |
| I4 | §3.4 reason-code bullet | five reason codes | pointer sentence to §25.12.1 appended (text not edited) |
| I5 | §5.3 columns line | M from `methodology_id` | pointer sentence to §25.9 and §25.12.2 appended (rows not edited) |
| I6 | §7 same-`claim_id` sub-bullet and methodology bullet | "MI is constant, so M is equal"; `MI` prose | pointer sentences to §25.12.3 and §25.11 appended |
| I7 | §12 preamble | — | pointer sentence to §25.12.4 appended |
| I8 | new §25 | none | methodology identity amendment (proposed) |
| I9 | new §26 | none | this table |

**Not changed:**
- v3.6 §23, v3.5 §21 and v3.4 §19, with their golden vectors, are untouched.
- Phase 1 is a partial milestone. C15 stays OPEN and C16 is not authorized.
- P1, P2 and P3 are inactive. `EvidenceRole` has exactly five members, and there is no `SUPPORT`, `CONTRADICT` or `ELIGIBLE` role.
- There is no score, probability or forecast, and no Strategy or Risk interface.
- `news_claims` is excluded.
- There is no new ETF freshness policy.
- Wallet references stay unapproved: no `wr1:` value.
- U2 is separate.
- The C13 source mapping stays excluded, and `KNOWN_EMPTY` stays reserved.
- v3.6 is not modified, and the Spec §7 pointer stays on v3.6.

**Historical v3.7 drafting disclosure (before its independent FAIL review; not v3.8 authorship or review status).**
- It was written by the implementer (Claude Code). It has **not** been independently audited and is **not** approved.
- The golden vectors were computed by the repository serializer and by a second encoder written from §4 by the same author, in a scratch run on `main` at `ebb9cf9`. They agree, which is not an audit.
- The pydantic admission claims in §25.3 and §25.4 come from scratch probes against pydantic 2.13.5, not from repository tests.


---

## 27. CHANGES_V3_7_TO_V3_8 [HISTORICAL PRE-ACTIVATION INVENTORY; PRESERVED]

This is the complete substantive remediation inventory. The v3.7 proposal, official v3.6 and canonical Spec remain unmodified. The historical §26 inventory describes the v3.7 derivation, not the additional v3.8 edits below.

| Change | Exact sections | Reason / bounded effect |
|---|---|---|
| K1 | Title/version/status, §25 heading/status, §25.17 contract-route item | Identify v3.8 as an unapproved remediation written by Codex, not an independent approval. Historical v3.7 drafting claims remain explicitly historical. |
| K2 (B1) | §3.6 introduction; §5.4 guarantees and partition references; AT-B1-9; §25.12.2 consistency text; §25.12.4; §25.18 output limitation | Replace unconditional methodology-dependent expectations with ESTABLISHED prerequisites and explicit NOT_ESTABLISHED routes; preserve differing source values and existing informational flags. |
| K3 (B2) | §25.2 label restriction; §25.12.2 R4c/R4d, delivery-discrepancy disposition, ordering and equal-D partition; §25.13 items 1–2; §25.15 J6; §25.17 related checklist | R4c is the complement of R4b within ESTABLISHED_EQUAL. The equal-XC/different-delivery NOT_ESTABLISHED subcase gets the existing unresolved label and UNVERIFIED effect. No new relation type or assumed equality; all other general R4d labels remain deferred. |
| K4 (B3) | §25.16 allowed existing-test exceptions and AT-MT-14 | Permit only file-specific import/export additions and the two-symbol removals in two package-level guards during later authorized implementation. Preserve every other assertion and all existing production behavior. |
| K5 | §25.4 admission/type semantics; §25.6 timestamp wording; AT-MT-5; AT-MT-ADMISSION-BEFORE, AT-MT-TZ-NO-CALLBACK, AT-MT-SCALAR-SEMANTICS | Require exact admission before coercion and unsafe callbacks; clarify generic scalars versus mapping-specific types and config timestamps versus evaluation/report timestamps. No serializer change or new mapping. |
| K6 | §25.12.4 / AT-MT-REL acceptance cases | Specify C07 hidden thresholds, C09 receipt R8 behavior, hidden-but-proven component differences, B2 delivery discrepancy, and exhaustive/disjoint equal-D branch tests. Relations tests remain deferred, not implemented. |
| K7 | §25.13 C13 gate; §25.17 review route; historical §26 heading/disclosure; this §27 | Keep C13 routing explicitly unavailable pending separate design/approval. Require independent review and owner approval; grant no implementation authorization. |
| K8 (N1–N3) | §5.3 R10 example; §25.2 amendment description; §25.9.5, §25.10, §25.12.3 and §25.15 current-version labels | Correct the C07 example and amendment inventory, and label current proposal statements v3.8. Historical v3.7 references remain historical. Wording only: no routing predicate, acceptance outcome, identity projection or fixture changes. |

### 27.1 Preservation and unresolved boundaries

- The seven-field model schema, seven-key methodology projection, mt1: prefix, c15.mt.v1 tag, serializer and all golden-vector inputs/IDs/complete ID_JSON fixtures are unchanged from v3.7. Slices 1–5 identity semantics are unchanged.
- The registry remains EMPTY; mapping_id text alone proves nothing. No candidate mapping is approved. Hidden-threshold codes remain undischargeable; a proven available component difference does not discharge them.
- C13 routing is not resolved or activated. Assessment-input digest remains in AC, not L5; same-observation prerequisites and unavailable D must be reconciled by the future relations design before any C13 comparison route activates.
- General R3c/non-delivery R4d labels/effects, R1/R2 methodology-state decisions, unequal digest availability and binding of caller continuity/recovery/coverage assertions remain future relations dependencies. The equal-D partition correction is not a claim of full relations readiness. No runtime evaluator, mapping-validation evidence type or production registry is implemented or authorized.
- The C09 version-bump limitation and open C10 schema-version source remain disclosed. No source adapter, assessment identity/content, EvidenceUnit, relation/lineage engine, fuse(), active role, score, forecast, AI-derived authority, Slice 7 or C16 is authorized.
- C15 remains OPEN; Phase 1 remains partial; the canonical Exit Gate and Closure Rule are untouched. v3.8 has no approval or activation status. A separate independent reviewer must assess this remediation.
