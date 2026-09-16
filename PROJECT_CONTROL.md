# PROJECT_CONTROL.md — TraID

## 0. Purpose

`PROJECT_CONTROL.md` is TraID's compact operational state ledger.

It records the verified current state of the project: active Card, authorization, blockers, checkpoints, gates, evidence status, and safe resume point.

It does not redefine project architecture, Roadmap order, Card contracts, financial/data guardrails, Git policy, or evidence standards.

---

## 1. State Authority

This file must agree with:

```text
repository reality
Git reality
TRAID_V1_ROADMAP.md
TRAID_CARD_SPECIFICATIONS.md
TRAID_CARD_EVIDENCE_MAP.md
explicit human authorization
```

Conflict:

```text
PROJECT_STATE_CONFLICT
STOP
RECONCILE
```

Never invent a convenient state.

---

## 2. Current Project State

```text
Project: TraID
Target: V1
Project Phase: POST_IMPLEMENTATION / C03_COMPLETE
Active Card: NONE
Active Card State: NONE
Last COMPLETE Card: V1-C03 — Exchange Adapter Contract
Next Roadmap Card: V1-C04 — Hyperliquid Provider Verification & Adapter
Next Card Authorized: NO — C04 start NOT_GRANTED
Implementation Authorization: NONE — no Active Card; C04 start NOT_GRANTED
V1 COMPLETE: NO
Live Trade Execution: PROHIBITED
Human Final Authority: YES
```

The state above is a control checkpoint, not a repository implementation claim.

---

## 3. Harness Redesign State

Final V1 governance surface:

```text
1. AGENTS.md
2. PROJECT_PROFILE.md
3. PROJECT_CONTROL.md
4. TRAID_V1_ROADMAP.md
5. TRAID_CARD_SPECIFICATIONS.md
6. TRAID_CARD_EVIDENCE_MAP.md
7. GIT_WORKFLOW.md
8. TRAID_ENGINEERING_HARNESS.md
9. FINANCIAL_AND_DATA_GUARDRAILS.md
10. .agents/skills/traid-card-execution/SKILL.md
```

Current redesign checkpoint:

```text
AGENTS.md: CANONICAL / CROSS-CHECK PASS
PROJECT_PROFILE.md: CANONICAL / CROSS-CHECK PASS
PROJECT_CONTROL.md: CANONICAL / CURRENT FILE
TRAID_V1_ROADMAP.md: CANONICAL / CROSS-CHECK PASS
TRAID_CARD_SPECIFICATIONS.md: CANONICAL / CROSS-CHECK PASS
TRAID_CARD_EVIDENCE_MAP.md: CANONICAL / CROSS-CHECK PASS
GIT_WORKFLOW.md: CANONICAL / CROSS-CHECK PASS
TRAID_ENGINEERING_HARNESS.md: CANONICAL / CROSS-CHECK PASS
FINANCIAL_AND_DATA_GUARDRAILS.md: CANONICAL / CROSS-CHECK PASS
.agents/skills/traid-card-execution/SKILL.md: CANONICAL / CROSS-CHECK PASS
```

C01 implementation, validation, approved delivery, and post-merge verification
are complete. Later-Card implementation remains unauthorized.

---

## 4. Repository / Git Reality

Current verified filesystem state:

```text
Repository Path: /Users/jo.soroush/john/my_projhects/TraID
Repository Root: VERIFIED
Canonical Harness Installation: VERIFIED
Canonical Harness Files: 10 / 10 PRESENT
Harness Structure: VERIFIED
Research / Reconnaissance Organization: VERIFIED
Implementation: COMPLETE — C01 and C02 implementation, validation, and approved delivery verified
Source Code: PRESENT — C01 baseline and C02 canonical domain contracts
Tests: PRESENT — C01 baseline and C02 domain/Harness tests
Git Repository: INITIALIZED
Git Branch: main
Git HEAD: 48f2958 — final post-merge C03 reconciliation checkpoint; validation passed
Git Upstream: origin/main
Git Remote: origin — https://github.com/jo-soroush/traid-market-intelligence.git
Git Safe Checkpoint: VERIFIED — 48f2958; C03 delivery reconciled on main and final validation passed
Working Tree: CLEAN — post-merge C03 verification checkpoint
V1-C01: COMPLETE
V1-C01 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C02: COMPLETE
V1-C02 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
```

Filesystem verification is not implementation evidence. Runtime, test, and
Git delivery claims require their own executed evidence.

C01, C02, and C03 repository, runtime, validation, approved delivery, and
post-merge verification evidence are recorded. Active Card is NONE; C04 remains
unauthorized.

### Current Maintenance Record

```text
Maintenance Task ID: MAINT-CI-PYTHON-PORTABILITY
Title: Hosted-CI Python subprocess interpreter portability correction
Status: CLOSED / DELIVERED / VERIFIED — generic enforcement delivered and post-merge validation passed
Reason: hosted CI evidence showed Harness subprocess tests assumed ROOT/.venv/bin/python
Originating Evidence: post-delivery CI portability incident; see TRAID_CARD_EVIDENCE_MAP.md
Base Commit: ef35af1 — verified main checkpoint
Branch: maintenance/ci-python-portability
Authorized Scope: CI interpreter portability correction plus generic maintenance/hotfix Harness enforcement and its governance/evidence reconciliation
Prohibited Scope: C03, product/domain behavior, financial rules, Harness semantics, architecture, and Card-state changes
Expected Areas: scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md, AGENTS.md, and the Card-execution Skill
Allowed Paths: scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md, AGENTS.md, .agents/skills/traid-card-execution/SKILL.md
Required Validation: focused portability tests, Harness/lifecycle tests, affected C02 tests, full pytest, secret scan, compilation, diff check
External Git Permissions: COMPLETED — approved push, PR, merge, and verification completed; no force push
Closure Evidence: PR #1 merged at c957bd4; push/PR hosted c01-baseline passed for c396c0e; post-merge main hosted c01-baseline run 34841403500 passed; local post-merge validation passed
Safe Resume: maintenance incident closed; do not start C03; obtain separate explicit C03 start authorization before any Card implementation
```

This record is operational maintenance state, not a Roadmap Card and not a
new source of truth for Card order or authorization. The Harness checker and
Bootstrap now validate its branch category, authorization, base ancestry, and
allowed changed paths. Hosted CI and GitHub branch-protection settings remain
external evidence and are not inferred from local validation.

---

## 5. Canonical Card States

Use:

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
READY_FOR_HUMAN_REVIEW
COMPLETE
DEFERRED
```

Optional review annotation:

```text
READY_FOR_HUMAN_REVIEW
CLOSED / PASS
```

`COMPLETE` requires evidence and the exact Card Quality Gate.

---

## 6. Active Card Record

Maintain when a Card is active:

```text
Card ID:
Title:
State:
Branch:
Start Commit:
Safe Checkpoint:
Engineering Goal:
Learning Goal:
Authorized Scope:
Out of Scope:
Dependencies:
Source/Provenance Obligations:
Financial/Data Guardrails:
Security Requirements:
Focused Validation:
Exit Gate:
ROADMAP_ALIGNMENT_GATE:
CARD_QUALITY_GATE:
Blockers:
Known Limitations:
Human Start Approval:
Human Delivery Approval:
```

Current delivered-Card record:

```text
Card ID: V1-C03
Title: Exchange Adapter Contract
State: COMPLETE
Branch: card/v1-c03-exchange-adapter-contract
Start Commit: 471a482
Safe Checkpoint: 133d064 — verified squash merge and post-merge validation
Engineering Goal: Define a capability-aware exchange-neutral adapter contract without changing Core
Learning Goal: Learn interface segregation, capability discovery, normalized errors, and provider isolation
Authorized Scope: provider-neutral exchange boundary, capability discovery, lifecycle/health where needed, normalized errors, fake/test adapter, and C02 canonical outputs
Out of Scope: C04 provider transport, Hyperliquid, live APIs, credentials, freshness, replay, analytics, Strategy, Risk Gate, and all later Cards
Dependencies: V1-C02 COMPLETE and delivery verified
Source/Provenance Obligations: no external source-derived implementation required; source/category coverage remains explicit at the contract boundary
Financial/Data Guardrails: preserve C02 canonical types and explicit availability; no provider-specific or freshness semantics
Security Requirements: no credentials, network transport, raw provider payloads, or live execution
Focused Validation: PASS — 20 C03 tests; 83 relevant regression tests; 123 full tests with 2 dependency warnings; hosted CI PASS
Exit Gate: PASS — fake adapter, capabilities, normalized errors, canonical outputs, and provider-neutrality proof
ROADMAP_ALIGNMENT_GATE: PASS
CARD_QUALITY_GATE: PASS
Learning Record Status: COMPLETE
Blockers: None
Known Limitations: C04 provider verification/transport and C05 freshness remain out of scope
Human Start Approval: GRANTED — V1-C03 Phase 1 authorization
Human Delivery Approval: GRANTED — explicit V1-C03 final delivery authorization
Delivery Verified: YES — PR #2, squash merge `133d064`, remote verification, and post-merge validation complete
```

---

## 7. Authorization Ledger

```text
Card Start: GRANTED — V1-C03; V1-C02 delivery completed
Delivery Approval: GRANTED — V1-C03 delivery completed and verified
Next Card: NOT_GRANTED — C04 remains unauthorized
V1-C03 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
Architecture Change: NOT_GRANTED
Material Scope Change: NOT_GRANTED
Significant Technology Addition: NOT_GRANTED
Sensitive Credential Use: NOT_GRANTED
External Write/Action Capability: NOT_GRANTED
Live Execution Capability: PROHIBITED IN V1
Commit: GRANTED — `6c3f7d4` C03 implementation commit
Push: GRANTED — C03 branch pushed and verified
PR: GRANTED — PR #2
Merge: GRANTED — squash merge `133d064` on main
Force Push/History Rewrite: NOT_GRANTED
Deployment/Release: NOT_GRANTED
```

Read-only inspection is allowed.

Routine reversible implementation is allowed only inside an explicitly approved active Card after its alignment gate passes.

---

## 8. Roadmap Position

```text
Approved V1 Cards: 27
Completed Cards: V1-C01, V1-C02, V1-C03
Active Card: NONE
Next Roadmap Card: V1-C04 — available only after separate C04 start approval
Later Cards: NOT AUTHORIZED
```

Being next in sequence is not authorization.

---

## 9. Card Transition Rule

```text
PRE-CARD READINESS_GATE PASS
→ explicit Card-start approval
→ ROADMAP_ALIGNMENT_GATE PASS
→ IN_PROGRESS
→ bounded implementation + validation + evidence
→ exact Exit Gate proof
→ CARD_QUALITY_GATE PASS
→ READY_FOR_HUMAN_REVIEW
→ STOP for human delivery review
→ explicit delivery approval
→ approved Git delivery and verification
→ COMPLETE
→ Active Card NONE
→ STOP
→ separate explicit approval for next Card
```

Never pre-authorize the next Card.

---

## 10. Current Blockers

```text
B-001: None — C01 delivery approval, merge, and post-merge verification are complete.
```

These are control blockers, not claims that the repository is broken.

---

## 11. Blocker Record

For each material blocker:

```text
Blocker ID:
Card:
Detected:
Category:
Description:
Observed Evidence:
Impact:
Root Cause:
Known:
Unknown:
Required Resolution:
Owner:
Status:
Resolution Evidence:
```

No blocker becomes resolved without evidence.

---

## 12. STOP State

Record:

```text
STOP Code:
Card:
Step:
Reason:
Observed Evidence:
Affected State:
Last Safe Checkpoint:
Rollback Needed:
Approval Needed:
Required Resolution:
```

Canonical codes include:

```text
CARD_MISMATCH
CARD_SCOPE_MISMATCH
CARD_DEPENDENCY_MISMATCH
PROJECT_STATE_CONFLICT
DUPLICATE_IMPLEMENTATION
FUTURE_CARD_LEAKAGE
ARCHITECTURE_CHANGE_REQUEST
SOURCE FILE NOT YET VERIFIED
SOURCE_LICENSE_BLOCK
FINANCIAL_SEMANTICS_UNVERIFIED
CRITICAL_GUARDRAIL_FAILURE
LOOKAHEAD_VIOLATION
ROADMAP_ALIGNMENT_GATE_BLOCKED
CARD_QUALITY_GATE_BLOCKED
DESTRUCTIVE_OPERATION_APPROVAL_REQUIRED
```

---

## 13. Roadmap Alignment State

Maintain for the active Card:

```text
ROADMAP_ALIGNMENT_GATE:
Timestamp:
Card:
Dependency Check:
Repository-State Check:
Duplicate Check:
Ownership Check:
Source/Provenance Check:
Financial/Data Guardrail Check:
Security Check:
Future-Scope Check:
Approval Check:
Authorized Bounded Step:
Focused Validation:
Exit-Gate Requirement Advanced:
```

Current:

```text
ROADMAP_ALIGNMENT_GATE: NOT_RUN
Reason: no active authorized Card
```

---

## 14. Current Bounded Step

```text
Step ID:
Card:
Goal:
Files Expected:
Contracts Affected:
Dependencies:
Must Remain Unchanged:
Validation:
Exit-Gate Advancement:
Status:
```

Current:

```text
Step ID: NONE
Status: NOT_STARTED
```

Only one bounded implementation step should be active at a time.

---

## 15. Contract Map / Risk Map

First implementation step of every new Card:

```text
Contract Map: REQUIRED
Risk Map: REQUIRED
Initial Mapping: READ-ONLY
```

Track:

```text
Contract Map Status:
Risk Map Status:
Important Owners:
Critical Contracts:
Critical Risks:
Unresolved Semantics:
```

Current:

```text
Contract Map Status: NOT_RUN
Risk Map Status: NOT_RUN
Reason: no active Card
```

---

## 16. Source / Provenance State

For source-dependent work:

```text
Decision ID:
Classification:
Source Project:
Repository:
Commit/Tag/Branch:
Exact File:
Exact Symbol:
License:
Behavior/Semantics:
Runtime Status:
TraID Modification:
Required Tests:
Remaining Unknowns:
```

Unknown exact source remains:

```text
SOURCE FILE NOT YET VERIFIED
```

Current:

```text
No active source-adaptation Card.
```

---

## 17. Financial / Data Guardrail State

Track when applicable:

```text
Units:
Timestamp Semantics:
Freshness:
Provenance:
Gap/Recovery:
Funding:
Fees:
Slippage:
Trade Side:
Open Interest:
Liquidation Truth:
Risk Gate:
Anti-Lookahead:
Same-Bar Policy:
Replay Determinism:
P&L Reconciliation:
MFE/MAE:
Other:
```

Current:

```text
No active financially material Card.
Global V1 guardrails remain in force.
```

Unknown material semantics:

```text
FINANCIAL_SEMANTICS_UNVERIFIED
STOP
```

---

## 18. AI / External Intelligence State

Track when applicable:

```text
AI Provider:
Model:
Structured Schema:
Prompt/Schema Version:
Evidence References:
Timeout:
Retry Policy:
Malformed Output:
Failure State:
Prompt Injection:
News Verification:
Whale Provenance:
Macro Provenance:
```

Current:

```text
No active AI/external-intelligence Card.
Bedrock is planned for V1-C14, not active now.
```

---

## 19. Risk / Backtest State

Current implementation evidence:

```text
Risk Gate Implementation: NOT_STARTED
Risk Gate Non-Bypass Evidence: NOT_AVAILABLE
Historical Replay Foundation: NOT_STARTED
Anti-Lookahead Evidence: NOT_AVAILABLE
Backtest Engine Integration: NOT_STARTED
STOP-FIRST Test Evidence: NOT_AVAILABLE
P&L Reconciliation Evidence: NOT_AVAILABLE
Replay Determinism Evidence: NOT_AVAILABLE
```

Architectural requirements already exist, but implementation must not be claimed before evidence.

---

## 20. Test / Evaluation State

Track only tests actually run:

```text
Test/Command:
Card:
Purpose:
Environment:
Timestamp:
Actual Result:
Pass/Fail:
Evidence Reference:
```

Current:

```text
TraID repository test state: VERIFIED — C03/full regression: 123 passed, 2 warnings
Harness consistency: PASS — C03 COMPLETE, delivery verification, and Active Card NONE validated
Readiness gate: PASS — V1-C03 dependency/runtime/configuration preflight
Secret scan: PASS
Python compilation: PASS
git diff --check: PASS
```

An intended or inspected test is not a passed test.

---

## 21. Card Quality Gate State

```text
CARD_QUALITY_GATE:
Focused Tests:
Relevant Regression:
Card Acceptance/Evaluation:
Financial Invariants:
Data Quality/Provenance:
AI/Risk:
Security:
Exit Gate Proof:
Evidence Updated:
Project Control Updated:
git diff Reviewed:
git status Reviewed:
Unrelated Changes:
Secrets/Generated Artifacts:
Known Limitations:
Recommended State:
```

Current:

```text
CARD_QUALITY_GATE: PASS — C03 evidence and exact Exit Gate proven after approved delivery and post-merge verification
Focused tests: 20 C03 tests passed; 83 relevant regression tests passed; 123 full tests passed
Evidence updated: YES — C03 implementation, failures, learning, and Exit Gate recorded
Learning Record: COMPLETE
Remaining issue: None for C03; C04 still requires separate start authorization
```

---

## 22. Evidence / Learning State

Detailed evidence belongs in `TRAID_CARD_EVIDENCE_MAP.md`.

This file keeps only:

```text
Latest Evidence Update:
Evidence Card:
Evidence Status:
Critical Missing Proof:
Learning Record Status:
Key Demonstrated Lesson:
```

Current:

```text
Latest Evidence Update: C02 DELIVERY — committed, merged, and verified
Evidence Card: V1-C02
Evidence Status: COMPLETE — approved C02 Git delivery and post-merge verification recorded
Critical Missing Proof: none for C02; later Cards remain unauthorized
Learning Record Status: COMPLETE — explicit 30-field record recorded in Evidence Map
Key Demonstrated Lesson: executable Harness checks must agree with safe repository conventions
```

Never duplicate or fabricate the Evidence Map here.

---

## 23. Checkpoint / Rollback State

```text
Checkpoint Type:
Branch:
Commit/State:
Validation:
Created:
Rollback Path:
```

Current:

```text
Checkpoint Type: NONE VERIFIED
Branch: NOT VERIFIED
Commit/State: NOT VERIFIED
Validation: NOT VERIFIED
Rollback Path: NOT VERIFIED
```

Destructive rollback requires explicit approval.

---

## 24. Git Delivery State

```text
Branch:
Commits:
Push:
PR:
PR State:
Human Review:
Merge Approval:
Merge:
Post-Merge Verification:
```

Current:

```text
Branch: main; Card branch: card/v1-c02-canonical-domain-models
Commits: 400358e (C02); f89af6d (C02 merge); prior C01/Harness commits recorded above
Push: C02 Card branch and origin/main VERIFIED
PR: NONE
PR State: N/A
Human Review: APPROVED — C02 delivery approval granted
Merge Approval: GRANTED
Merge: VERIFIED — f89af6d on main
Post-Merge Verification: PASS — main contains 400358e; remote and working tree verified
```

The live repository is currently on the authorized maintenance branch recorded
in Section 4. The block above is retained as C02 delivery history and is not a
claim that the current worktree is `main` or clean.

Files designed outside the repository are not Git delivery evidence.

---

## 25. Security State

```text
Real Secrets in Repository: MUST BE NO
.env Committed: MUST BE NO
Exchange Trading Credentials: PROHIBITED
Wallet Private Keys: PROHIBITED
Live Execution Endpoint: PROHIBITED
Secret Scan: NOT VERIFIED IN ACTUAL REPOSITORY
Least Privilege: REQUIRED
External Content: UNTRUSTED
Model Output: UNTRUSTED
```

Actual repository security status must be evidenced in the owning Cards.

---

## 26. Observability / Recovery State

```text
Structured Runtime Observability: NOT YET VERIFIED
Audit Trail: NOT YET VERIFIED
Provider Recovery: NOT YET VERIFIED
AI Failure Recovery: NOT YET VERIFIED
Data-Gap Recovery: NOT YET VERIFIED
```

Architecture intent is not runtime evidence.

---

## 27. Deferred Work Ledger

Format:

```text
Deferred ID:
Originating Card:
Idea:
Reason Deferred:
Target Card / Future Version:
Dependency:
Risk if Forgotten:
```

Current:

```text
No deferred implementation items recorded here.
```

Deferred work is not authorized work.

---

## 28. Decision Ledger

```text
D-001
Decision: V1 is read-only decision support with no live trade execution.
Status: ACTIVE

D-002
Decision: Hyperliquid is the only required V1 live exchange implementation; Core remains provider-neutral.
Status: ACTIVE

D-003
Decision: AI is provider-isolated and cannot override deterministic Strategy/Risk authority.
Status: ACTIVE

D-004
Decision: Risk Gate is mandatory, deterministic, reason-coded, fail-closed, and non-bypassable.
Status: ACTIVE

D-005
Decision: historical evaluation is anti-lookahead; unresolved same-bar stop/target ordering uses STOP FIRST.
Status: ACTIVE

D-006
Decision: Harness remains coding-tool-neutral; tool-specific adapters are optional thin layers.
Status: ACTIVE

D-007
Decision: final V1 governance surface is ten canonical Harness files including one TraID Card-execution Skill.
Status: ACTIVE
```

New material architecture decisions require explicit approval.

---

## 29. External Source Summary

High-level audited roles only:

```text
Hyperliquid Analytics Dashboard → market-data / deterministic analytics reference and ADAPT candidates
HyperStats → Whale / Smart Money methodology reference
Hyperliquid Data Layer API → conditional EVALUATE/ADAPT after exact verification
NEXUS → macro/provider/operational reference
Quant Flow → structured fail-closed AI reference
CryptoRadar → Signal Fusion / detector / Outcome reference
Keel → typed Strategy / validation / agent-safety reference
Hyperliquid Backtester → deterministic replay / anti-lookahead / accounting reference
Hyper Display → UX reference
```

This summary is not source verification.

Exact source decisions belong in Card evidence/source mapping.

---

## 30. V1 Card Status Table

| Card | Title | State | Start Approved | Quality Gate | Evidence |
|---|---|---|---|---|---|
| V1-C01 | Repository Baseline & Engineering Harness | COMPLETE | YES | PASS | COMPLETE |
| V1-C02 | Canonical Domain Models | COMPLETE | YES | PASS | COMPLETE |
| V1-C03 | Exchange Adapter Contract | COMPLETE | YES | PASS | COMPLETE |
| V1-C04 | Hyperliquid Provider Verification & Adapter | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C05 | Data Quality, Freshness & Provenance | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C06 | Historical Data & Replay Foundation | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C07 | Order Book & Liquidity Analytics | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C08 | Trade Flow & CVD | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C09 | Derivatives & Volatility | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C10 | Market Regime, Crowding & Liquidation Context | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C11 | Whale Intelligence Foundation | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C12 | Macro Intelligence | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C13 | Primary-Source News Verification | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C14 | Bedrock Provider & Structured Intelligence | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C15 | Evidence Registry & Signal Fusion | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C16 | Typed Strategy Engine | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C17 | Deterministic Risk Gate | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C18 | Backtest Engine Integration | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C19 | Outcome Tracking | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C20 | Evaluation Registry | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C21 | Decision-Support API | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C22 | Dashboard | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C23 | Observability, Audit & Failure Recovery | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C24 | Security & Secrets Hardening | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C25 | Docker, CI & Release Gate | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C26 | Golden Case End-to-End Validation | NOT_STARTED | NO | NOT_RUN | PENDING |
| V1-C27 | V1 Documentation & Demo | NOT_STARTED | NO | NOT_RUN | PENDING |

Update only from actual evidence.

---

## 31. Resume Protocol

After interruption:

```text
1. Read AGENTS.md.
2. Read PROJECT_PROFILE.md.
3. Read PROJECT_CONTROL.md.
4. Read TRAID_V1_ROADMAP.md.
5. Read the active Card Specification.
6. Read active Card Evidence.
7. Read TRAID_ENGINEERING_HARNESS.md.
8. Read FINANCIAL_AND_DATA_GUARDRAILS.md when relevant.
9. Inspect Git/repository reality.
10. Reconcile mismatch.
11. Re-run ROADMAP_ALIGNMENT_GATE before writing.
```

Never resume implementation from chat summary alone.

---

## 32. Update Rules

Update Project Control on meaningful transitions:

```text
Card start
Card block/unblock
bounded-step checkpoint
material approved decision
source/provenance blocker
Quality Gate result
ready-for-human-review
commit/push/PR/merge approval state
post-merge verification
Card completion
next-Card authorization
material deferral
```

Do not update it for every trivial edit.

---

## 33. State Integrity

Never write:

```text
COMPLETE
PASS
VERIFIED
MERGED
PUSHED
TESTED
AUTHORIZED
```

without corresponding evidence.

Do not infer state from:

- chat memory;
- intended commands;
- unexecuted tests;
- generated drafts;
- local files outside the repository;
- external repository claims;
- Card titles;
- prior agent summaries.

Prefer:

```text
NOT VERIFIED
PENDING
BLOCKED
```

when proof is absent.

---

## 34. Current Safe Resume Point

```text
Safe Resume:
C01, C02, and C03 are delivered and verified. C03 merged into `main` at
`133d064` through PR #2; post-merge validation passed. Active Card is NONE.
Do not start C04 without separate explicit human approval.

Implementation Card: NONE
Repository Write Authorization: no Active Card; C04 start NOT_GRANTED
Next Roadmap Card: V1-C04
V1-C01 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C02 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C03 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
```

Current resume point:

```text
C03 delivery is complete and verified.
→ Active Card NONE
→ stop
→ obtain separate explicit approval before starting C04
```

---

## 35. Final Control Principle

```text
PROJECT_CONTROL RECORDS REAL STATE.
IT DOES NOT CREATE REALITY.

NO EVIDENCE → NO CLAIM.
NO APPROVAL → NO CONSEQUENTIAL ACTION.
NO ACTIVE CARD → NO IMPLEMENTATION.
CARD COMPLETE → STOP.
NEXT CARD → SEPARATE HUMAN APPROVAL.
```
