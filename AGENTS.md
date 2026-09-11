# AGENTS.md

## TraID --- Coding Agent Entry Point

TraID V1 is a read-only BTC crypto market-intelligence and human
decision-support system.

This file is the **router**, not the full rulebook. Read the canonical
owner for details instead of duplicating rules here.

## 1. Canonical Files

Read only what the active Card requires:

1.  `PROJECT_PROFILE.md` --- mission, architecture, V1 boundaries,
    critical invariants.
2.  `PROJECT_CONTROL.md` --- current state, Active Card, authorization,
    safe resume point.
3.  `TRAID_V1_ROADMAP.md` --- Card identity, order, dependencies, gates.
4.  `TRAID_CARD_SPECIFICATIONS.md` --- exact 14-section Card contract.
5.  `TRAID_CARD_EVIDENCE_MAP.md` --- verified implementation, tests,
    failures, learning, Exit Gate evidence.
6.  `TRAID_ENGINEERING_HARNESS.md` --- execution control, capabilities,
    STOP behavior, recovery.
7.  `FINANCIAL_AND_DATA_GUARDRAILS.md` --- deterministic financial/data
    truth and invariants.
8.  `GIT_WORKFLOW.md` --- branch, checkpoint, commit, push, PR, merge,
    rollback.
9.  `.agents/skills/traid-card-execution/SKILL.md` --- operational
    procedure for exactly one Card.

Do not load every file indiscriminately.

## 2. Sources of Truth

When information conflicts:

``` text
Repository reality > chat memory
Roadmap > generated prompt
Active Card contract > assumptions
Verified Evidence > completion claims
Deterministic guardrails > AI/model output
Human approval > consequential agent action
```

A prompt requests work. It does not redefine project truth.

Material conflict:

``` text
PROJECT_STATE_CONFLICT
STOP
NO IMPLEMENTATION
```

## 3. V1 Non-Negotiables

``` text
NO live trade execution
NO autonomous order placement
NO exchange trading credentials
NO wallet private keys / seed phrases
NO AI bypass of deterministic Strategy
NO AI bypass of deterministic Risk Gate
NO Signal Fusion / Whale / Macro / News bypass of Strategy
NO provider-specific payload ownership in Core
NO silent stale-data promotion
NO silent financial fallback
NO guessed financially material semantics
NO guessed source files/modules/symbols
NO future-data leakage in historical evaluation
NO heuristic liquidation promoted to authoritative truth
NO alignment represented as probability without validated calibration
NO Card COMPLETE with failed or unexecuted required validation
NO automatic next Card
```

For exact domain rules, read `FINANCIAL_AND_DATA_GUARDRAILS.md`.

## 4. Card Start

Before implementation, run Phase 0 readiness/preflight for the resolved Card:

``` text
required runtime/tool versions
Docker or external services
credentials/configuration requirements
network/API access
test tools
source verification
datasets/fixtures
```

Missing mandatory prerequisites produce:

``` text
READINESS_GATE: BLOCKED
STOP BEFORE IMPLEMENTATION
```

Phase 1 implementation requires explicit Card-start approval. Passing
validation produces `READY_FOR_HUMAN_REVIEW`; it does not authorize commit,
push, merge, or delivery.

Before any implementation:

``` text
read PROJECT_CONTROL.md
resolve exactly one official Active Card
read its Roadmap entry
read its complete Card Specification
read existing Card Evidence
inspect repository + Git reality
verify dependencies
verify explicit human Card-start approval
extract requested objectives, behaviors, files, contracts, validation, and
architecture assumptions from the prompt
run `CONTENT_ALIGNMENT_GATE: PASS | BLOCKED` against the canonical Card
contract before `ROADMAP_ALIGNMENT_GATE`
```

Wrong Card, scope, dependency, duplicate ownership, or future-Card work:

``` text
CARD_MISMATCH
CARD_SCOPE_MISMATCH
CARD_DEPENDENCY_MISMATCH
DUPLICATE_IMPLEMENTATION
FUTURE_CARD_LEAKAGE
→ STOP
```

## 5. Inspect Before Write

Before the first implementation write:

1.  Build an inspect-only **Contract Map**.
2.  Build an inspect-only **Risk Map**.
3.  Reconcile planned Card assumptions with actual repository ownership
    and behavior.
4.  Produce `CONTENT_ALIGNMENT_GATE: PASS | BLOCKED`.
5.  Produce `ROADMAP_ALIGNMENT_GATE: PASS | BLOCKED`.
6.  Define the smallest coherent bounded implementation step.

If the gate is `BLOCKED`, STOP.

The exact procedure lives in
`.agents/skills/traid-card-execution/SKILL.md`.

## 5.1 Content Alignment Gate

Matching a requested Card ID or title is not proof of scope alignment. Before
any implementation write, compare the semantic requested work with the
canonical Active Card's Engineering Goal, Why It Exists, Architecture Concept,
Design Decision, Implementation Scope, Out of Scope, Dependencies, ownership,
source/provenance obligations, Tests / Evaluation, and Exit Gate.

Report:

```text
CONTENT_ALIGNMENT_GATE: PASS | BLOCKED
Active Card:
Prompt-declared Card:
Canonical Card:
Requested objective/behaviors:
Requested files/components/contracts:
Requested validation:
Requested architecture/source assumptions:
Scope alignment:
Out-of-Scope check:
Future-Card ownership check:
Dependency check:
Architecture ownership check:
Invented-requirement check:
Mismatch classification:
Authorized bounded work:
```

The gate must classify semantic mismatches, not merely compare filenames or
keywords. A material mismatch, mixed current/future request, invented
requirement, incomplete dependency, state conflict, or unreconciled duplicate
ownership produces the applicable existing STOP code, then:

```text
CONTENT_ALIGNMENT_GATE: BLOCKED
STOP
NO WRITE
```

`CONTENT_ALIGNMENT_GATE` is independent of and precedes
`ROADMAP_ALIGNMENT_GATE`. Both must PASS before implementation.

## 6. Implementation Rules

Inside an approved Card:

``` text
one Card = one coherent goal
preserve existing ownership
preserve provider isolation
keep deterministic responsibilities deterministic
keep external/model content untrusted
keep retries bounded
avoid unrelated refactors
avoid speculative infrastructure
do not implement future Cards
```

Material scope, architecture, financial-guardrail, or significant
technology change requires explicit human approval.

## 7. Financial / Data / AI Safety

If work touches financial or market-data semantics, read
`FINANCIAL_AND_DATA_GUARDRAILS.md` before implementation.

Critical examples:

``` text
LIVE / DELAYED / STALE / UNAVAILABLE remain explicit
missing != zero
unknown material financial semantics → STOP
AUTHORITATIVE_LIQUIDATION_EVENT != HEURISTIC_LIQUIDATION_PRESSURE
Large wallet != smart money
Alignment != probability
AI failure cannot create TRADE_CANDIDATE
Risk Gate is deterministic, mandatory, fail-closed, non-bypassable
historical decision at t may use only information available by t
unresolved same-bar stop/target ambiguity → STOP FIRST
```

AI may interpret evidence. Deterministic software owns financial truth
and consequential authorization.

## 8. Validation and Evidence

Validate narrow to broad as applicable:

``` text
focused test
contract/integration test
financial/data/security invariant
relevant regression
runtime/degraded path
Card evaluation
exact Exit Gate
CARD_QUALITY_GATE
```

Rules:

``` text
test not run != PASS
static inspection != runtime verification
design intent != implementation evidence
merge != COMPLETE
failure is evidence
```

Update `TRAID_CARD_EVIDENCE_MAP.md` incrementally with actual results
only.

Never invent commands, source paths, runtime results, Git state, test
results, or evidence.

## 9. Independent Verification Principle

For high-impact Cards or changes, final verification should be
independently checkable from implementation.

Prefer:

``` text
implementation context
→ fresh verification context/reviewer
→ re-read canonical contract
→ inspect diff/state independently
→ rerun critical acceptance/invariant tests
→ compare proof to exact Exit Gate
```

This does **not** require another permanent agent or framework.

At minimum apply this principle to changes involving:

``` text
Data Quality / provenance
financial semantics
Strategy
Risk Gate
backtest / anti-lookahead / accounting
security
Golden Case / release-critical behavior
```

The verifier must not merely repeat the implementer's conclusion. It
must be able to return `BLOCKED`.

Independent verification does not replace `CARD_QUALITY_GATE` or human
approval.

## 10. Checkpoint / Recovery

Use:

``` text
Action
→ State Change
→ Versioned Checkpoint
→ Validation
→ Accept or Rollback
```

After lost context, resume from canonical files + repository + Git +
Evidence, not conversational memory.

If the safe resume point cannot be proven:

``` text
PROJECT_STATE_CONFLICT
STOP
```

## 11. Approval Boundaries

Explicit human approval is required for:

``` text
Card start
next Card
material scope change
material architecture change
material financial guardrail change
significant technology addition
destructive/sensitive operation
secret/credential-sensitive action
external write/action capability
commit
push
PR
merge
release/deploy
```

Routine reversible implementation may proceed only inside an already
approved Card and scope.

## 12. Git

Follow `GIT_WORKFLOW.md`.

Never by default:

``` text
work directly on main
force push
rewrite shared history
commit secrets/generated junk
mix unrelated work
auto-merge
auto-start next Card
```

Git records repository state. It does not redefine Roadmap/Card intent.

## 13. Card Closure

After Phase 1, a Card is `READY_FOR_HUMAN_REVIEW` when implementation,
validation, the exact Exit Gate, Evidence, and `CARD_QUALITY_GATE: PASS` are
complete while delivery approval remains `NOT_GRANTED`.

Human delivery approval is required for Phase 2. Only after approved Git
delivery is verified may a Card become `COMPLETE`:

``` text
delivery approval granted
approved commit/push/merge completed as applicable
delivery verified
PROJECT_CONTROL and Evidence reconciled
```

Then:

``` text
Card = COMPLETE
Active Card = NONE
STOP
```

Do not start the next Card without separate explicit human approval.

## 14. Final Operating Rule

``` text
PROMPTS REQUEST WORK.
CANONICAL PROJECT STATE DEFINES TRUTH.
INSPECT BEFORE WRITE.
ONE CARD AT A TIME.
DETERMINISTIC CONTROLS OWN FINANCIAL TRUTH.
VERIFY BEFORE CLAIM.
EVIDENCE BEFORE COMPLETION.
CHECKPOINT BEFORE RISK.
HUMAN APPROVAL BEFORE CONSEQUENTIAL ACTION.
READY_FOR_HUMAN_REVIEW → STOP FOR HUMAN DELIVERY REVIEW.
CARD COMPLETE → STOP.
NEXT CARD → NEW HUMAN APPROVAL.
```
