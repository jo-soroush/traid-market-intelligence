# TraID V1-C15 Phase 1 — Corrected Implementation Contract

**Version identifier:** `C15-P1-CONTRACT-v3.1-DRAFT` (2026-11-04)
**Supersedes:** `TRAID_C15_PHASE1_CONTRACT_v3_AFTER_AUDIT_FAIL.md` (v3.0) and `TRAID_C15_PHASE1_CONTRACT_FOR_CODEX.md` (v2). Both are left untouched and are NOT the contract. Where they differ from v3.1, v3.1 governs.
**v3.1 scope:** a bounded remediation of exactly two blocking defects reproduced by Codex's v3 audit (R4 methodology mismatch; Enum type collisions) plus one clarification (ETF mapping versus source reports). Every changed clause is listed in §16. All other clauses are carried unchanged from v3.0. The two reproduced defects are described here from the task statement; I do not hold Codex's audit text.
**Baseline:** `main` at `c08bd61` (verified: `HEAD` = `c08bd61`; the only untracked file before this task was the v2 contract).
**Status:** proposed, unapproved design. Not independently reviewed. Not an implementation. Not an audit.
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
| L1 | `series_key` | what is observed, without time slot: `{kind, symbol, interval, source, section}` | no | `series_id` |
| L2 | `slot` | one observation slot of the series: `series_key` plus `slot_time` (C09: `latest_start`; C07: `snapshot_timestamp`; C08: `(window_start, session_start)`) | no | `slot_id` |
| L3 | `coverage` | history actually behind the slot: `{earliest_time, latest_time, contributing_count, interval}` where exposed | no | `coverage_id` |
| L4 | `metrics` | tuple of `MetricObservation` (below). Source-exposed material economic metrics | no | `metrics_id` |
| L5 | `input_set_ref` | `{digest: [algorithm, sha256] or null, delivery: {source_type, source_id, received_timestamp, ...}}` | **yes** | `input_set_id` |
| L6 | `methodology` | `MI`: engine and schema version, source-exposed config, rule/mapping digests, quality-policy version, hidden-input codes | no | `methodology_id` |
| L7 | `assessment_content` (`AC`) | every other exposed field (states, reasons, quality verdicts, limitations) | no | `ac_id` |

Derived identifiers [P]:

- `series_id = "sr1:" + HID("c15.series.v1", series_key)` — **association only**.
- `slot_id = "sl1:" + HID("c15.slot.v1", slot)`.
- `exposed_content_id = "xc1:" + HID("c15.xc.v1", {"slot": slot_id, "coverage": coverage, "metrics": metrics, "basis": basis})` — everything economic that is exposed, **excluding L5**. Equal value means equal exposed projection only.
- `input_set_id = "is1:" + HID("c15.is.v1", input_set_ref)`.
- `observation_id = "ob1:" + HID("c15.ob.v1", {"slot": slot_id, "xc": exposed_content_id, "is": input_set_id})` — one delivered observation (one delivered input set projected to one slot).
- `methodology_id = "mt1:" + HID("c15.mt.v1", MI)`.
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
- `uncompared`: metric names whose verdict is `UNKNOWN`, each with a reason code: `METHODOLOGY_DIFFERS`, `NOT_PRESENT`, `WINDOW_NOT_VERIFIED`, `WINDOW_DIFFERS`, `UNIT_DIFFERS`.
- `any_different`, `all_compared_equal`, `none_compared`.

A report exposing **no metrics at all** (for example C09 open interest and basis, always unavailable at `derivatives/analytics.py`) has `basis = NO_OBSERVATION`. It cannot be compared and never forms a relation.

### 3.5 Coverage relation [P]

Computed from `coverage` only. It is **informational** and never changes eligibility by itself.

`SAME` (all four fields equal), `NESTED` (one `[earliest, latest]` interval contains the other, same `latest_time`), `OVERLAPPING`, `DISJOINT`, `UNKNOWN` (a field missing).
Contributing counts are shown, never used to infer equality of records.

### 3.6 Regression fixtures for the three C09 candle counterexamples [P]

These three are my reconstruction from the B1 requirement list (see disclosure). Each fixture is two `DerivativesReport` candle sections at one T, one slot (`latest_start` equal), one methodology (`config` equal), `symbol` and `source` equal.

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
| `Decimal` | see 4.3 |
| `datetime` (checked **before** `date`) | requires aware (`utcoffset() is not None`), converted with `astimezone(timezone.utc)`, `{"$":"dt","v":"YYYY-MM-DDTHH:MM:SS.ffffffZ"}` always with six fractional digits |
| `date` (not `datetime`) | `{"$":"date","v":"YYYY-MM-DD"}` |
| `timedelta` | `{"$":"td","v":"<total microseconds as base-10 string>"}`, computed as `days*86400*10**6 + seconds*10**6 + microseconds`, sign preserved |
| `Enum` (any subclass, including `StrEnum`, `IntEnum`, `IntFlag`) | `{"$":"enum","c":"<type.__module__>:<type.__qualname__>","v":ID_ENC(member.value)}`, **recursive** (the value may itself be an enum, tuple or Decimal). **Dispatched before** `bool`, `str`, `int` and every other primitive, because an Enum may subclass them. See 4.2a |
| ordered sequence (`tuple`, `list`) | `{"$":"seq","v":[ID_ENC(x), ...]}` in the original order |
| `set`, `frozenset` | `{"$":"set","v":[...]}` sorted by `json.dumps` of the encoded element; duplicate encoded elements raise |
| adapter-declared unordered multiset (`Unordered(items)` wrapper) | `{"$":"bag","v":[...]}` sorted likewise, duplicates kept |
| `dict` | `{"$":"map","v":[[ID_ENC(k), ID_ENC(v)], ...]}` sorted by encoded key; keys must be `str` |
| `float`, `bytes`, `datetime.time`, NaN or infinite Decimal, naive datetime, any other type | **rejected** |

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
6. Eligibility is the worst-of across the unit's relations with precedence `INELIGIBLE > MISSING > STALE > UNVERIFIED > ELIGIBLE > DESCRIPTIVE_ONLY` where the roles are the inactive-only set (§10).

### 5.3 Decision table

Columns: **D** = `input_digest` comparison, **M** = `methodology_id`, **Cmp** = metric comparison summary (§3.4). "Same observation" means equal `observation_id`.

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
| R10 | different `observation_id`, no digest, `exposed_content_id` differs, `any_different` | `CONFLICTING_OBSERVATION` | all `INELIGIBLE` | e.g. two C07 reports for one snapshot timestamp with different best bid |
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

- R1–R3b depend on equal `observation_id`; R4a–R10a depend on different `observation_id`. Disjoint.
- R4a, R4b, R4c partition "different `observation_id`, D equal" by M (differs / equal) and, for equal M, by material output (differs / not provable). They are disjoint and exhaustive. R5–R8 require D differs. R9–R10a require no digest. So the four digest cases (D equal, D differs, no digest) are disjoint.
- **v3.1 guarantee:** identical candle inputs under `atr_period=2` and `atr_period=3` have equal D, different M, hence different `exposed_content_id` (the ATR differs) and different `observation_id`; they match R4a first and cannot reach R4b, R5 or R10.
- `observation_id` equal implies `slot_id`, `exposed_content_id` and `input_set_id` all equal. So R6 (digest differs, exposed content equal) always has different `input_set_id` and is therefore always a different `observation_id`. No overlap with R1/R2.
- A receipt-only difference changes `input_set_id` (via L5) and not `exposed_content_id` (L5 excluded). It therefore lands in R6 or R9, never R5 or R10. **This is the B1 item 2 guarantee.**
- A coverage-only difference changes `coverage` in `exposed_content_id`. It lands in R6 (with `COVERAGE_VARIANT`) only if every compared metric is `EQUAL`; with no compared metric it is R7. It is never R5 on its own. **B1 item 3.**
- A candle price difference inside a metric window changes a compared metric ⇒ R5. **B1 item 1.**

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
  - equal `input_digest` (C13 methodology `MI` is constant, so M is equal), different exposed content ⇒ R4b `CONFLICTING_ASSESSMENT`;
  - different `input_digest`, different exposed content ⇒ `UNRESOLVED_INPUT_SET_DIFFERENCE` (evidence or policy differs; not a proven conflict);
  - equal content ⇒ `EQUIVALENT_AS_EXPOSED`.
- **[P] Methodology.** `MI = {engine_version, VERIFICATION_POLICY_NOT_EXPOSED}`. C13 methodology is partial and disclosed.
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
- **[P] AI stances are not roles.** `supporting_factors` and `contradicting_factors` are the model's anchor stances (`adapt`, `ai/validation.py:874-885`). C15 never reads them into any role, count, group, relation, warning or gap. They appear only inside the verbatim payload labeled `AI_STANCE_NOT_A_ROLE`. No C15 field name uses `support` or `contradict`.
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
- **[P]** `ROLE_RULES_ACTIVE = ()`. P1, P2 and P3 are inactive constants with no activation parameter, flag, attestation or environment switch. `EvidenceRole = {DESCRIPTIVE_ONLY, MISSING, STALE, UNVERIFIED, INELIGIBLE}`. No `SUPPORT` or `CONTRADICT` member exists. No score, probability, weight, readiness number or prediction.
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

None of these tests exists yet. None has been run. All are required acceptance criteria.

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
| AT-B1-9 | C07 identical exposed fields ⇒ `EQUIVALENT_AS_EXPOSED`, `raw_identity=PARTIAL`; text never says duplicate, identical or distinct book; different best bid at one snapshot ⇒ `CONFLICTING_OBSERVATION`; same provenance tuple with different values never merges |
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
| AT-PRIV-2 | AI `supporting_factors` / `contradicting_factors` populate no C15 field, role, count, group, relation, warning or gap; no C15 field name contains `support` or `contradict` |
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
