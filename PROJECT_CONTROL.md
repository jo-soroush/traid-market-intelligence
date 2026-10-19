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

Operational ownership: this section owns Active Card/State and next-Card eligibility; §30 owns Card rows; §7 owns Card authorization declarations; the Current active-Card record in §6 owns its approval details. Previous/delivered records and secondary summaries are snapshots, not additional live authorities. Maintenance scope belongs to its current record; its current audit receipt owns review/delivery evidence. Git owns actual branch, SHA, ancestry and worktree. A receipt cannot grant authority beyond explicit human approval.

Maintenance snapshot semantics: source-branch Git/authorization/status and
Safe Resume declarations below are frozen review-time values. On clean main,
only a successful production Harness integration check establishes effective
INTEGRATED / NO_ACTIVE_MAINTENANCE with the old audit historical at runtime.
Then follow the next work's separately authorized startup, archiving this
snapshot in that same task/Card branch. Do not interpret frozen review-time
STOP/delivery-not-granted text as a new terminal review requirement. A failed
runtime check still means STOP. External hosted/delivery evidence is separate.

```text
Project: TraID
Target: V1
Project Phase: C07_INTEGRATED_PENDING_VERIFICATION / LOCAL_LIFECYCLE_CORRECTION
Active Card: V1-C07
Active Card State: READY_FOR_HUMAN_REVIEW
Last COMPLETE Card: derived from the authoritative §30 table
Next Roadmap Card: V1-C08 — Trade Flow & CVD
Next Card Authorized: NO — C08 NOT_GRANTED
Implementation Authorization: V1-C07 START_GRANTED; DELIVERY_GRANTED; DELIVERY_NOT_VERIFIED — correction implementation; correction commit/push/PR GRANTED; correction merge NOT_GRANTED
Systemic State-Drift Remediation: CLOSED / DELIVERED / VERIFIED
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

C01 baseline delivery is historical; current execution authorization is owned by §2, §6 and §7.

---

## 4. Repository / Git Reality

Frozen filesystem/review snapshot (actual Git facts are queried at runtime):

```text
Repository Path: /Users/jo.soroush/john/my_projhects/TraID
Repository Root: VERIFIED
Canonical Harness Installation: VERIFIED
Canonical Harness Files: 10 / 10 PRESENT
Harness Structure: VERIFIED
Research / Reconnaissance Organization: VERIFIED
Implementation: completion is derived from the canonical §30 Card Status Table; verification evidence belongs in the Evidence Map
Source Code: PRESENT — C01 baseline, C02 canonical domain contracts, C03 boundary, C04 provider adapter, C05 quality layer, and C06 historical data/replay foundation
Tests: PRESENT — C01 through C06 focused, regression, and Harness tests
Git Repository: INITIALIZED
Git Branch: fix/card-integration-lifecycle-c07
Git Checkpoint: 82eb0644b1e9912cd1dc972c646b489f26d081c4 — verified PR14 squash integration
Git Upstream: NONE — local lifecycle correction not yet pushed; correction commit/push/PR GRANTED, merge NOT_GRANTED
Git Remote: origin — https://github.com/jo-soroush/traid-market-intelligence.git
Git Safe Checkpoint: VERIFIED — historical PR #13 merge 2e04a174096b60e2c3719d4d4d5ff6a92a442e3e; prior reconciliation history preserved
Working Tree: DIRTY_ALLOWED — explicitly scoped Card integration lifecycle correction
V1-C01: COMPLETE
V1-C01 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C02: COMPLETE
V1-C02 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C03: COMPLETE
V1-C03 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C04: COMPLETE
V1-C04 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C05: COMPLETE
V1-C05 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C06: COMPLETE
V1-C06 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
```

Filesystem verification is not implementation evidence. Runtime, test, and
Git delivery claims require their own executed evidence.

C01-C06 implementation and approved delivery evidence are recorded. PR #11 is
merged at e8ce5af0b548819d8b37711ff0e5185c7d306512 with successful hosted CI.
The reconciliation policy was delivered by PR #12 at
622d7848bb00cdd0d1c3a877844b1c3099230f75. Its delivered audit is HISTORICAL;
C06 maintenance remains closed. PR #13 delivered the secret-scan fix at
2e04a174096b60e2c3719d4d4d5ff6a92a442e3e; its audit is HISTORICAL and maintenance
is closed. PR14 is integrated at 82eb0644b1e9912cd1dc972c646b489f26d081c4; production Harness and hosted CI passed. C07 start is now separately authorized.

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-POST-MERGE-LIFECYCLE
Title: Reviewed maintenance integration without reconciliation commits
Status: CLOSED / DELIVERED / VERIFIED — PR14 integrated at 82eb0644b1e9912cd1dc972c646b489f26d081c4; former review-time declarations below are immutable historical snapshots
Reason: reviewed squash merges retain branch-bound candidate snapshots and CURRENT audit evidence, causing repeated main Harness failures and terminal governance deliveries
Originating Evidence: PR13 post-merge failure and terminal closure history; Claude scratch prototype/forgery experiments in /private/tmp/claude-501/proto.py, forge.py and task2.py inspected as non-canonical starting evidence
Base Commit: a63435bc6f8d4672cc2bcfc5d664ebd647134e6b — verified clean main checkpoint
Branch: maintenance/post-merge-lifecycle
Authorized Scope: human CONSOLIDATED HARNESS ROOT-CAUSE REMEDIATION authorizes bounded F01 and F03-F07 correction and combined self-validation; preserve F02 integration model
Prohibited Scope: C06 or PR13 reopening, changes to closed record bodies/history, product/financial behavior, C07 work, dependencies, real commits, push, PR, merge, direct-main edits
Inherited Candidate: scripts/check_maintenance_integration.py remains unchanged from reviewed PR14 commit ae14957b23a6098cdcea3bd3247e004cf03962eb; its inherited diff is retained in Allowed Paths, not authorized for new edits
Expected Areas: .github/workflows/ci.yml, scripts/harness_consistency_check.py, src/traid/harness/lifecycle.py, scripts/check_tracked_secret_filenames.sh, tests/test_maintenance_integration.py, tests/test_harness_consistency.py, tests/test_lifecycle.py, tests/test_secret_filenames.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md
Required Validation: PASS — combined focused/full regressions, real Linux isolated packaging and repeated CI sequence, Harness/bootstrap/both scanners, squash/two-delivery/Card-start/stale-target simulations, mutation/scope and history checks; exact counts and limitations in current Evidence entry
External Git Permissions: NOT_GRANTED — implementation and disposable scratch validation only; no original commit, push, PR change, merge or direct-main change
Closure Evidence: PR14 original candidate delivered as ae14957b23a6098cdcea3bd3247e004cf03962eb; hosted Harness failed on build outputs; prior review preserved in Evidence; new candidate review PENDING
Safe Resume: STOP for independent Claude review of the newly frozen WORKTREE candidate; no original commit, push, PR update or merge authorized; C01-C06 COMPLETE, Active Card NONE, C07 NOT_GRANTED, D-OI-001 DEFERRED
Allowed Paths: scripts/check_maintenance_integration.py, .github/workflows/ci.yml, scripts/harness_consistency_check.py, src/traid/harness/lifecycle.py, scripts/check_tracked_secret_filenames.sh, tests/test_maintenance_integration.py, tests/test_harness_consistency.py, tests/test_lifecycle.py, tests/test_secret_filenames.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md
```

---

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-SECRET-SCAN-FAIL-CLOSED
Title: Fail-closed portable tracked-file secret scanning
Status: CLOSED / DELIVERED / VERIFIED — PR #13 squash-merged; hosted tests and actual secret scan verified
Reason: hosted secret scan reported PASS despite rg being unavailable because scanner errors inside an if condition were treated as no match
Originating Evidence: terminal commit f109aec3cf27bc96d22336dfcde34693a307892b; Actions run 38464788684 logged scripts/check_secrets.sh: line 11: rg: command not found while reporting success
Base Commit: f109aec3cf27bc96d22336dfcde34693a307892b — verified clean synchronized main maintenance base
Branch: maintenance/secret-scan-fail-closed
Authorized Scope: replace rg with fail-closed git grep for documented tracked-file content scanning; preserve patterns and exclusions; add temporary-repository regression tests and minimum separate maintenance/evidence documentation
Prohibited Scope: closed C06 records, Git workflow, Harness rules/checker, CI workflow, product code, dependencies, unrelated cleanup, C07 work, commit, push, PR, merge
Expected Areas: scripts/check_secrets.sh, tests/test_secret_filenames.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
Required Validation: PASS — 25 focused scanner tests; 370 full tests with 2 existing deprecation warnings; production Harness PASS; bootstrap 20 PASS / 1 expected dirty-tree warning / 0 FAIL; actual git grep scan PASS (status 1, no match); diff and preservation self-review PASS
External Git Permissions: COMPLETED for PR #13 only — human-authorized commit, branch push, PR and squash merge completed; no further external action authorized by this closed record
Closure Evidence: independent PASS preserved for WORKTREE Diff SHA-256 9fa71dcbde434813f77e9c78297917e9e6bd9144d28f218d7541b18bc256061c; commit 16ab7ec5f956884b045117fd48d2c42906a699ae delivered through PR #13, squash-merged at 2e04a174096b60e2c3719d4d4d5ff6a92a442e3e. Push, PR and merge hosted runs passed with 370 tests and actual fail-closed secret-scan execution verified. Post-merge local pytest 370 passed and traced git grep scan passed. Original branch-bound main Harness/bootstrap failure is preserved in the Evidence Map; terminal review, validation and delivery evidence is retained externally under GIT_WORKFLOW.md §21.1.
Safe Resume: no active maintenance; PR #13 maintenance is closed. STOP. Active Card NONE, C01-C06 COMPLETE, C07 NOT_STARTED / NOT_GRANTED, D-OI-001 DEFERRED. Terminal reconciliation follows only the separately authorized GIT_WORKFLOW.md §21.1 procedure.
Allowed Paths: scripts/check_secrets.sh, tests/test_secret_filenames.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
```

---

The closed C06 record below retains every recorded field unchanged; only its
section heading is archived using the existing Previous Maintenance format.

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-C06-POST-MERGE-RECONCILIATION-PR11
Title: PR #11 C06 post-merge governance reconciliation
Status: CLOSED / DELIVERED / VERIFIED — reconciliation policy delivered by PR #12
Reason: PR #11 has merged, and its delivered CURRENT audit record must be retired while final post-merge verification and operational state are reconciled truthfully
Originating Evidence: PR #11 merged at e8ce5af0b548819d8b37711ff0e5185c7d306512; merge and hosted CI observed through GitHub
Base Commit: e8ce5af0b548819d8b37711ff0e5185c7d306512 — verified PR #11 merge on origin/main
Branch: maintenance/c06-post-merge-reconciliation
Authorized Scope: prepare a permanent exceptional terminal post-merge governance reconciliation policy in GIT_WORKFLOW.md and preserve/reconcile the existing PR #11 state evidence in PROJECT_CONTROL.md and TRAID_CARD_EVIDENCE_MAP.md; no execution of the terminal main procedure is authorized by this maintenance
Prohibited Scope: product code, Harness/checker, tests, CI, dependencies, C01-C06 implementation, C07 implementation or authorization, financial guardrails, OI semantics, commit, push, PR creation/update, merge, direct main edits, force push, history rewrite
Expected Areas: GIT_WORKFLOW.md, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
Required Validation: PASS — `.venv/bin/pytest -q` 349 passed with 2 existing deprecation warnings; `python scripts/harness_consistency_check.py` PASS; `bash scripts/session_bootstrap.sh` PASS_WITH_1_WARNINGS (20 PASS, 1 expected dirty-tree warning, 0 FAIL); `bash scripts/check_secrets.sh` PASS; `git diff --check` PASS
External Git Permissions: NOT_GRANTED — this instruction authorizes local branch creation, governance edits, and validation only
Closure Evidence: PR #11 merge SHA and hosted checks remain recorded in TRAID_CARD_EVIDENCE_MAP.md. The policy candidate passed the recorded local validation and independent delta review with exact WORKTREE Diff SHA-256 e586669b9e5a5df9ab839e0e1bb9a52099f474bb77420fc38e918d985e47434b. PR #12 delivered the policy at 622d7848bb00cdd0d1c3a877844b1c3099230f75. The delivered audit is HISTORICAL with its exact PASS evidence preserved. Earlier disposable-clone results remain policy simulation evidence only; terminal review, delivery, and validation evidence is retained outside canonical documents under GIT_WORKFLOW.md §21.1.
Safe Resume: no active maintenance; this policy task is closed. Keep Active Card NONE, C01-C06 COMPLETE, C07 NOT_STARTED / NOT_GRANTED, and D-OI-001 DEFERRED. Terminal reconciliation follows only the separately authorized GIT_WORKFLOW.md §21.1 procedure.
Allowed Paths: GIT_WORKFLOW.md, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
```

---

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-C06-POST-MERGE-SUMMARY-FIXTURE
Title: C06 post-merge summary-fixture, Harness state, and candidate identity maintenance
Status: CLOSED / DELIVERED / VERIFIED — PR #11 delivery and its hosted checks are verified; reconciliation policy delivered by PR #12
Reason: post-merge pytest reported 325 passed and 3 failures in completed-Card summary scenarios; subsequent audit findings concerned governance test fixtures and truthful state reconciliation
Originating Evidence: PR #10 squash merge `1c40b3a5b0c801d303d71053c411427767d671c1`; post-merge pytest result and independent Claude Code root-cause analysis
Base Commit: 1c40b3a5b0c801d303d71053c411427767d671c1 — verified C06 merge on synchronized main
Branch: maintenance/c06-post-merge-summary-fixture
Authorized Scope: completed-Card summary fixtures and authorized governance/Harness corrections as recorded in the historical maintenance authorization and audit evidence
Historical Scope Supplements: later explicit human authorizations extended the original test-fixture scope to include the production Harness working-tree policy (`DIRTY_ALLOWED` accepts clean or authorized in-scope dirty state) and the candidate-identity index comparison against `HEAD`; separate final audit-remediation authorization covered the synthetic Git-history regression and specified F1/F2 governance wording corrections. These changes and their exact candidate/audit history are recorded in TRAID_CARD_EVIDENCE_MAP.md.
Prohibited Scope: C01-C06 product changes, C07 work, financial guardrails, OI semantics, dependencies, and any unapproved delivery action
Expected Areas: tests/test_harness_consistency.py, scripts/harness_consistency_check.py, src/traid/harness/lifecycle.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, tests/test_lifecycle.py, tests/test_maintenance_harness.py
Required Validation: historical maintenance test, identity, Harness, and repository validation requirements are preserved in TRAID_CARD_EVIDENCE_MAP.md
External Git Permissions: COMPLETED for PR #11 only — authorized branch push and PR delivery completed; no further external action is authorized by this historical record
Closure Evidence: maintenance commit a3598cdb212c867e8676d758465bb106148a16ce was delivered through PR #11; PR #11 merged at e8ce5af0b548819d8b37711ff0e5185c7d306512. Both hosted c01-baseline test checks passed for PR head de2179c5c19575d05695dd11f2b19c342bbdee47. Its independent audit PASS remains bound to WORKTREE Diff SHA-256 726e1c94b5e4fda696e887449a42d4c34bf4befe2bd2862c96d5f042e8bda5dd. The subsequent reconciliation policy candidate passed 349 pytest tests, Harness, secret scan, diff check, and bootstrap with 20 PASS / 1 expected dirty-tree warning / 0 FAIL; independent delta review PASS and PR #12 policy delivery are preserved in the Evidence Map.
Safe Resume: no further work under this closed maintenance record; terminal reconciliation follows GIT_WORKFLOW.md §21.1 only under separate authorization. C01-C06 COMPLETE, Active Card NONE, C07 NOT_STARTED / NOT_GRANTED, and D-OI-001 DEFERRED.
Allowed Paths: tests/test_harness_consistency.py, tests/test_maintenance_harness.py, tests/test_lifecycle.py, scripts/harness_consistency_check.py, src/traid/harness/lifecycle.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md
```

This historical maintenance record does not reopen C06 or authorize C07.

---

### Previous Maintenance Record

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
Bootstrap validate its branch category, authorization, base ancestry, and
allowed changed paths. Hosted CI is separate external evidence. At the time of
this historical record, actual GitHub branch-protection settings were
NOT_VERIFIED; repository workflow requirements do not imply that platform
settings are enabled, and no platform settings were changed.

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-PROVENANCE-TEMPORAL-INTEGRITY
Title: Bounded provenance source-time maintenance
Status: CLOSED / DELIVERED / VERIFIED — PR #3 squash-merged and post-merge validation passed
Reason: C04 readiness identified that provider asset-context observations may lack a verified source/event timestamp while C02 required one
Originating Evidence: C04 Phase 0 semantic blocker and approved provenance design review
Base Commit: 6c5425c — verified clean main checkpoint
Branch: maintenance/provenance-temporal-integrity
Authorized Scope: nullable C02 source_timestamp with mandatory received_timestamp, focused provenance tests, regression validation, and maintenance/evidence records
Prohibited Scope: C04 provider implementation, Hyperliquid integration, C05 freshness, C06 replay, product architecture, financial semantic changes, dependency installation, and Git delivery
Expected Areas: src/traid/domain/models.py, tests/test_domain_models.py, tests/test_maintenance_harness.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
Allowed Paths: src/traid/domain/models.py, tests/test_domain_models.py, tests/test_maintenance_harness.py, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
Required Validation: focused provenance tests, C02/C03 regressions, Harness/lifecycle/maintenance checks, full pytest, bootstrap, secret scan, compilation, diff check, and scope/leakage review
External Git Permissions: COMPLETED — approved commit, push, PR, merge, and verification completed; no force push
Closure Evidence: PR #3 squash-merged at `44b9237`; hosted `c01-baseline` checks passed; post-merge focused regression 111 passed; full pytest 131 passed with 2 dependency warnings; Harness consistency, secret scan, compilation, diff check, and final reconciliation passed
Safe Resume: maintenance delivery is complete; keep Active Card NONE, C01/C02/C03 COMPLETE, C04 NOT_STARTED/NOT_GRANTED, and do not start C04
```

This record is operational maintenance state, not a Roadmap Card and not a
new source of truth for Card order or authorization.

### Previous Maintenance Record — MAINT-AEVS-ADOPTION-V1

```text
Maintenance Task ID: MAINT-AEVS-ADOPTION-V1
Title: AEVS v1.0 incremental governance adoption
Status: CLOSED / DELIVERED / VERIFIED — PR #8 delivery and final operational reconciliation completed through PR #9
Reason: adopt risk-proportional verification and explicit independent audit records for future work while correcting a stale completed-Card summary
Originating Evidence: read-only governance assessment identified the project-risk-context ambiguity and stale C05 completion summary; independent audit of the first candidate returned BLOCKED with three major and two minor findings
Base Commit: 81d010d2e699119b65e3f16894d38f5d3b1b2b69 — verified clean main baseline
Branch: maintenance/aevs-adoption-v1
Authorized Scope: minimum AEVS v1.0 governance adoption from future work beginning with C06; generic completed-Card summary checking and focused tests; delivery-state audit clarification in GIT_WORKFLOW.md; truthful maintenance and evidence records; non-canonical Claude Code routing entry point
Prohibited Scope: delivery; C06 start or classification; reopening C01-C05; product architecture or product code; dependencies or external verification tools; C05 threshold recalibration; D-OI-001 resolution; financial guardrail changes; trading/account execution
Expected Areas: AGENTS.md, CLAUDE.md, PROJECT_PROFILE.md, PROJECT_CONTROL.md, GIT_WORKFLOW.md, TRAID_ENGINEERING_HARNESS.md, TRAID_CARD_EVIDENCE_MAP.md, scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py
Required Validation: focused governance tests; Harness/lifecycle/maintenance tests; 27-Card and completed-summary consistency; authorization and evidence/learning checks; full pytest; Harness consistency; bootstrap; secret scan; compilation/import/health; pip check; git diff --check
External Git Permissions: COMPLETED — explicit final delivery authorization; PR #8 squash merge and hosted CI completed
Closure Evidence: PR #8 merged at 41d5a0331609fca60d09be224364ef5f7e3d335e; its AEVS audit and delivery evidence remain in TRAID_CARD_EVIDENCE_MAP.md. PR #9 merged by squash at 0772397185b9d34640241addb6a2a9dba2ae7cf9, adding the generic post-merge lifecycle rule; the delivered audit record is now HISTORICAL and final reconciliation validation passed
Safe Resume: AEVS governance maintenance is delivered and verified; keep Active Card NONE; C01-C05 COMPLETE; C06 NOT_STARTED / NOT_GRANTED and do not start it without separate explicit human approval; D-OI-001 DEFERRED; Hyperliquid OI UNVERIFIED FOR CANONICAL USE
Allowed Paths: AGENTS.md, CLAUDE.md, PROJECT_PROFILE.md, PROJECT_CONTROL.md, GIT_WORKFLOW.md, TRAID_ENGINEERING_HARNESS.md, TRAID_CARD_EVIDENCE_MAP.md, scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py
```

This record is historical maintenance state, not a Roadmap Card or a second
Card-state owner. AEVS operational reconciliation is complete; current Card
state is owned by the state table and active-Card record below.

### Previous Maintenance Record — MAINT-POST-MERGE-RECONCILIATION-CONTRACT-V1

```text
Maintenance Task ID: MAINT-POST-MERGE-RECONCILIATION-CONTRACT-V1
Title: Generic post-merge maintenance audit lifecycle and deterministic governance fixtures
Status: CLOSED / DELIVERED / VERIFIED — PR #9 squash-merged and post-merge reconciliation validation passed
Reason: PR #8 merged, but main Harness/bootstrap remained blocked because its delivered Current Maintenance Re-Audit Record still named the old maintenance branch; two policy tests also inherited mutable live text/scope
Originating Evidence: read-only root-cause analysis proved two test fixture defects, correct production checker behavior, and a missing CURRENT-to-HISTORICAL post-merge lifecycle rule
Base Commit: 41d5a0331609fca60d09be224364ef5f7e3d335e — verified PR #8 merge on main
Branch: maintenance/post-merge-reconciliation-contract-v1
Authorized Scope: deterministic governance tests, explicit CURRENT/HISTORICAL audit-record lifecycle checks, concise Harness/Git Workflow rules, and truthful maintenance evidence/state
Prohibited Scope: delivery; C06 start or authorization; C01-C05 lifecycle changes; product code/architecture; dependencies/tools; automatic reconciliation; OI semantics; financial guardrails
Expected Areas: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md, scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py
Required Validation: focused Safe Resume/scope/lifecycle tests; Harness/maintenance/lifecycle tests; all-27-Card consistency; full pytest; Harness; bootstrap; secret scan; compilation/import/health; pip check; git diff --check
External Git Permissions: COMPLETED — approved commit, push, PR #9, hosted CI, and squash merge completed
Closure Evidence: Independent bounded audit PASS for the exact WORKTREE identity recorded in TRAID_CARD_EVIDENCE_MAP.md; PR #9 merged by squash at 0772397185b9d34640241addb6a2a9dba2ae7cf9; both required hosted c01-baseline/test checks passed; post-merge validation and final clean synchronized-main reconciliation passed as recorded in TRAID_CARD_EVIDENCE_MAP.md
Safe Resume: this bounded maintenance is closed; keep Active Card NONE; C01-C05 COMPLETE; C06 NOT_STARTED / NOT_GRANTED and do not start it without separate explicit human approval; D-OI-001 DEFERRED; Hyperliquid OI UNVERIFIED FOR CANONICAL USE
Allowed Paths: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_ENGINEERING_HARNESS.md, GIT_WORKFLOW.md, scripts/harness_consistency_check.py, tests/test_harness_consistency.py, tests/test_maintenance_harness.py
```

This record is historical maintenance state, not a Roadmap Card or a second
Card-state owner. Its audit evidence is historical and does not authorize new
work.

---

### Previous Maintenance Record

```text
Maintenance Task ID: MAINT-OI-CONTRACT-RECONCILIATION
Title: Bounded Hyperliquid Open Interest contract reconciliation
Status: CLOSED / DELIVERED / VERIFIED — PR #4 squash-merged and post-merge validation passed
Reason: C04 required an explicit verified-unavailable outcome for unresolved Hyperliquid OI semantics
Originating Evidence: final OI contract audit; D-OI-001 and D-008
Base Commit: d226adc — verified synchronized main checkpoint
Branch: maintenance/oi-contract-reconciliation
Authorized Scope: C04/C09 contract wording, Roadmap wording, Project Control decision/deferred records, and Evidence Map reconciliation
Prohibited Scope: C04 implementation, Hyperliquid provider code, raw OI mapping, C05/C06/C09 implementation, C02/C03 production changes, and force push/history rewrite
Expected Areas: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_CARD_SPECIFICATIONS.md, TRAID_V1_ROADMAP.md, tests/test_maintenance_harness.py
Allowed Paths: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, TRAID_CARD_SPECIFICATIONS.md, TRAID_V1_ROADMAP.md, tests/test_maintenance_harness.py
Required Validation: governance/Harness tests, full pytest, Harness consistency, bootstrap, secret scan, and diff check
External Git Permissions: COMPLETED — approved commit, push, PR, merge, and verification completed; no force push
Closure Evidence: PR #4 squash-merged at `6e84cb8`; both hosted `c01-baseline` checks passed; post-merge validation and final reconciliation completed at the verified checkpoint recorded by Git
Safe Resume: full baseline validation and C04 Phase 0 only after separate explicit C04 start approval; keep D-OI-001 deferred, Active Card NONE, C01/C02/C03 COMPLETE, C04 NOT_STARTED/NOT_GRANTED, and do not implement C04
```

This record is operational maintenance state, not a Roadmap Card and not a
new source of truth for Card order or authorization.

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

Current delivered-Card record:

```text
Card ID: V1-C05
Title: Data Quality, Freshness & Provenance
State: COMPLETE
Branch: card/v1-c05-data-quality-freshness-provenance
Start Commit: 6a58b91
Safe Checkpoint: efc8ef612f956a29d9219bec5e9aae1dc594d035 — verified squash merge and post-merge validation
Engineering Goal: Prevent stale, malformed, missing, gapped, or unavailable data from silently becoming trusted evidence
Learning Goal: Make data quality, freshness, provenance, coverage, gaps, and recovery first-class deterministic contracts
Authorized Scope: provider-neutral quality policy/evaluator, explicit freshness/provenance/coverage/gap/recovery results, deterministic tests, and C05 evidence/learning updates
Out of Scope: historical replay/backfill, analytics, Strategy, Risk Gate, AI, trading, wallet/account operations, and OI semantic resolution
Dependencies: V1-C04 COMPLETE and delivery verified
Source/Provenance Obligations: preserve truthful source/received timestamps; do not fabricate source freshness or continuity
Financial/Data Guardrails: LIVE/DELAYED/STALE/UNAVAILABLE explicit; missing != zero; unavailable OI remains unavailable/unverified
Security Requirements: no network requirement, credentials, account mutation, trading, or secret material
Focused Validation: PASS — 46 focused C05 tests; 211 full tests with 2 dependency warnings; Harness, bootstrap, security, compilation, import/health, pip check, and diff checks passed
Exit Gate: PASS — trust-model invariants, timezone semantics, deterministic quality behavior, and scope boundaries proven
ROADMAP_ALIGNMENT_GATE: PASS
CARD_QUALITY_GATE: PASS
Blockers: None
Known Limitations: thresholds are TraID policy defaults, not provider cadence claims; C06 retains replay/backfill ownership
Human Start Approval: GRANTED — explicit V1-C05 Phase 1 authorization
Human Delivery Approval: GRANTED — explicit V1-C05 Phase-2 delivery authorization
Delivery Verified: YES — PR #7, squash merge `efc8ef6`, remote verification, and post-merge validation complete
```


---

Last completed-Card record:

```text
Card ID: V1-C04
Title: Hyperliquid Provider Verification & Adapter
State: COMPLETE
Branch: card/v1-c04-hyperliquid-provider
Start Commit: 4e5da73
Safe Checkpoint: 4e5da73 — verified clean main baseline
Engineering Goal: Verify Hyperliquid semantics and connect real BTC REST/WebSocket data through C03
Learning Goal: Provider semantic verification, bounded transport, canonical normalization, and fail-closed data handling
Authorized Scope: public read-only Hyperliquid adapter, verified BTC mappings, bounded WebSocket transport, provenance, coverage, tests, and evidence
Out of Scope: trading, wallet/account operations, credentials, AI, Strategy, Risk Gate, C05+, and delivery
Dependencies: V1-C03 COMPLETE and delivery verified
Source/Provenance Obligations: official Hyperliquid evidence, truthful source/received timestamps, explicit limitations
Financial/Data Guardrails: unresolved OI remains unavailable/unverified; no synthetic zero or mark-price conversion
Security Requirements: public market data only; no account mutation or trading capability
Focused Validation: PASS — 15 focused provider tests; latest post-merge full-suite checkpoint: 165 passed with 2 dependency warnings
Exit Gate: PASS — REST/WebSocket mappings, bounded reconnect, resubscription, failure matrix, OI fail-closed, and live BTC WebSocket data proof
ROADMAP_ALIGNMENT_GATE: PASS
CARD_QUALITY_GATE: PASS
Blockers: None for C04 Exit Gate; OI remains explicitly unavailable/unverified
Known Limitations: OI unit/aggregation semantics remain unverified; missed WebSocket continuity is not claimed
Human Start Approval: GRANTED — explicit V1-C04 Phase 1 authorization
Human Delivery Approval: GRANTED — explicit V1-C04 final delivery authorization
Delivery Verified: YES — PR #6, squash merge `50165e3`, remote verification, and post-merge validation complete
```

Current C05 delivery record:

```text
Human Delivery Approval: GRANTED — explicit V1-C05 Phase-2 delivery authorization
Delivery Verified: YES — PR #7, squash merge `efc8ef6`, remote verification, and post-merge validation complete
```

Last completed-Card record:

```text
Card ID: V1-C06
Title: Historical Data & Replay Foundation
State: COMPLETE
Branch: card/v1-c06-historical-data-replay-foundation
Start Commit: 9d96cd5537e1c978003ca3235aa331c5750b347c
Safe Checkpoint: 9d96cd5537e1c978003ca3235aa331c5750b347c — verified clean main base
Engineering Goal: versioned canonical BTC historical datasets and deterministic replay with explicit coverage and gaps
Learning Goal: temporal integrity, dataset identity, and reproducible replay
Authorized Scope: C06 historical provider, canonical dataset/store/replay, bounded real-data acceptance, deterministic tests, and evidence
Out of Scope: C07+ analytics, backtesting/fills/P&L, OI semantic resolution, new dependencies, C01-C05 contract changes, and delivery
Dependencies: V1-C02 and V1-C05 COMPLETE with delivered evidence and passing baseline tests
Source/Provenance Obligations: Hyperliquid public info BTC perpetual candles and funding; local collection only; publication latency and redistribution rights unverified
Financial/Data Guardrails: preserve source and receipt times; model availability with explicit policy offsets; no inferred funding cadence, OI, interpolation, or lookahead
Security Requirements: bounded read-only API, no credentials, root outside Git, integrity checks and symlink/path-escape rejection
Focused Validation: PASS — 52 focused C06 tests and 328 full-suite tests passed after audit remediation; exact commands and warnings are in Card Evidence
Exit Gate: PASS — bounded real BTC dataset, coverage, gaps, integrity, and deterministic replay recorded in Card Evidence
ROADMAP_ALIGNMENT_GATE: PASS — C06 scope/dependencies/ownership verified at Phase 0
CARD_QUALITY_GATE: PASS — developer validation and exact Exit Gate complete; independent audit PASS_WITH_GAPS with R1 accepted as non-blocking for delivery
Blockers: final post-merge governance verification is being completed under MAINT-C06-POST-MERGE-RECONCILIATION-PR11; no C06 product defect identified; C07 remains NOT_GRANTED
Known Limitations: R1 boundary regression-test gap remains; provider publication time, historical revisions/backfills, funding cadence/continuity, and redistribution rights are unverified
Human Start Approval: GRANTED — explicit V1-C06 implementation authorization in this request
Human Delivery Approval: GRANTED — explicit C06 controlled-delivery authorization
Delivery Verified: YES — PR #10 merged with hosted PR CI PASS at `1c40b3a5b0c801d303d71053c411427767d671c1`; PR #11 governance maintenance merged with hosted CI PASS at `e8ce5af0b548819d8b37711ff0e5185c7d306512`. PR #12 delivered the reconciliation policy at `622d7848bb00cdd0d1c3a877844b1c3099230f75`; its audit is HISTORICAL and maintenance is closed. C07 remains NOT_GRANTED.
```

The Card record retains the reviewed source identity. Runtime integration and the separately authorized correction scope are proved by the single Card Integration Record below, not by rewriting historical audit identity. Successful recognition is pending verification, never COMPLETE.

Current active-Card record:

```text
Card ID: V1-C07
Title: Order Book & Liquidity Analytics
State: READY_FOR_HUMAN_REVIEW
Branch: card/v1-c07-order-book-liquidity
Start Commit: 82eb0644b1e9912cd1dc972c646b489f26d081c4
Human Start Approval: GRANTED — explicit user V1-C07 implementation request
Human Delivery Approval: GRANTED — explicit C07 FINAL MERGE & POST-MERGE VERIFICATION; PR15 squash merge authorized and performed; closure not yet verified
Delivery Verified: NO
```

Card Integration Record:

```text
Card ID: V1-C07
Source Branch: card/v1-c07-order-book-liquidity
Base SHA: 82eb0644b1e9912cd1dc972c646b489f26d081c4
Source Commit: d26b45a3be831850ea8a8ac12b6d346d2ecad159
Merge Anchor: b86a265e644bbac0674aad091769c38389ca7385
PR: 15
Protected Paths: src/traid/liquidity/__init__.py, src/traid/liquidity/analytics.py, tests/test_liquidity.py
Integrated Paths: PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md, src/traid/liquidity/__init__.py, src/traid/liquidity/analytics.py, tests/test_harness_consistency.py, tests/test_liquidity.py, tests/test_maintenance_harness.py
Human Merge Approval: GRANTED — explicit C07 FINAL MERGE & POST-MERGE VERIFICATION instruction; PR15 merge independently verified through GitHub
Post-Merge Verification: NOT_VERIFIED
Closure Approval: NOT_GRANTED
Correction Branch: fix/card-integration-lifecycle-c07
Correction Base SHA: b86a265e644bbac0674aad091769c38389ca7385
Correction Paths: .github/workflows/ci.yml, scripts/harness_consistency_check.py, scripts/check_maintenance_integration.py, tests/test_card_integration.py, tests/test_maintenance_harness.py, GIT_WORKFLOW.md, TRAID_ENGINEERING_HARNESS.md, PROJECT_CONTROL.md, TRAID_CARD_EVIDENCE_MAP.md
Correction Authorization: GRANTED — ONE BOUNDED CARD INTEGRATION LIFECYCLE FIX and CONSOLIDATED HARNESS LIFECYCLE STABILIZATION; local implementation/testing; commit/push/PR GRANTED — explicit user authorization for controlled delivery of this correction only; merge NOT_GRANTED, C07 closure NOT_GRANTED, C08 NOT_GRANTED
Correction Diff SHA-256: d1bd7c3a0f64d48aa5e4ea5e3fd1957594d834d647a886f6cf899762657ad2a5
```

Current active-Card Contract/Risk Map:

```text
Card Verification Level: LEVEL_3
Risk rationale: deterministic financial analytics with precision, quality and provenance boundaries
Invariants affected: G03 G04 G05 G06 G07 G10 G17; no trading or decision path
Verification-technique applicability:
  deterministic invariant testing: REQUIRED — known-value formulas, units, quality and invalid-input fixtures
  property-based testing: REQUIRED — deterministic generated books exercise invariants without a new dependency
  failure injection: REQUIRED — degraded quality, empty sides and insufficient liquidity
  fuzzing: REQUIRED — bounded generated malformed and extreme numeric inputs
  mutation testing: REQUIRED — isolated formula and trust-gate mutants must fail regression
  differential testing: REQUIRED — independent Fraction reference for slippage and depth
  adversarial testing: REQUIRED — validation bypass, duplicate/crossed levels and hostile Decimal context
  chaos testing: NOT_APPLICABLE — pure snapshot computation has no service or concurrency failure boundary
  formal methods: NOT_APPLICABLE — bounded deterministic arithmetic verified by independent fixtures and invariants; no new proof tooling justified
```

## 7. Authorization Ledger

```text
V1-C01 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C02 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
Card Start: GRANTED — V1-C07 Phase 1 implementation
Delivery Approval: GRANTED — C07 PR15 commit/push/PR/merge authorized and performed; verification pending; correction commit/push/PR GRANTED (explicit user authorization), correction merge NOT_GRANTED
Next Card: NOT_GRANTED — C08 and later remain unauthorized
V1-C03 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C04 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C05 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C06 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_COMPLETED
V1-C07 Authorization: START_GRANTED; DELIVERY_GRANTED; DELIVERY_NOT_VERIFIED
Architecture Change: NOT_GRANTED
Material Scope Change: NOT_GRANTED
Significant Technology Addition: NOT_GRANTED
Sensitive Credential Use: NOT_GRANTED
External Write/Action Capability: NOT_GRANTED
Live Execution Capability: PROHIBITED IN V1
Historical Commit: GRANTED — `6c3f7d4` C03 implementation commit
Historical Push: GRANTED — C03 branch pushed and verified
Historical PR: GRANTED — PR #2
Historical Merge: GRANTED — squash merge `133d064` on main
Force Push/History Rewrite: NOT_GRANTED
Deployment/Release: NOT_GRANTED
```

Read-only inspection is allowed.

Routine reversible implementation is allowed only inside an explicitly approved active Card after its alignment gate passes.

---

## 8. Roadmap Position

```text
Approved V1 Cards: 27
Completed Cards: derived from the authoritative §30 table by Harness
Active Card: NONE
Next Roadmap Card: V1-C07 — available only after separate C07 start approval
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
B-001: fresh independent review PENDING and delivery NOT_GRANTED for the changed candidate. Prior hosted failure and completed local remediation proof are in the maintenance Evidence entry.
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
ROADMAP_ALIGNMENT_GATE: PASS — V1-C06 exact contract, C02/C05 dependencies, source and future-Card boundaries verified
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
Contract Map Status: PASS — C02 canonical models, C05 trust boundary, new provider/history/store/replay ownership inspected
Risk Map Status: PASS — timestamp, provenance, integrity, duplicate, publication, storage and lookahead risks recorded
Reason: V1-C06 explicitly authorized and bounded to historical data/replay
```

For future active Cards beginning with V1-C06, record this work-item-specific
Contract/Risk Map before implementation:

```text
Current active-Card Contract/Risk Map:
Card Verification Level: LEVEL_1 | LEVEL_2 | LEVEL_3 | LEVEL_4
Risk rationale:
Invariants affected:
Verification-technique applicability:
  deterministic invariant testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  property-based testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  failure injection: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  fuzzing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  mutation testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  differential testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  adversarial testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  chaos testing: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
  formal methods: REQUIRED | CONDITIONAL | NOT_APPLICABLE — substantive rationale
```

For `CONDITIONAL`, add an indented `Trigger: <explicit condition>` below that
technique. `Invariants affected` names canonical IDs/sections or
`NONE — <substantive reason>`; bare `NONE` is invalid. Phase 0 records
decisions. The Evidence Map records actual closure before the quality gate.

Current active-Card Contract/Risk Map:

```text
Card Verification Level: LEVEL_3
Risk rationale: C06 creates financial decision-support inputs that future evaluation may trust; corrupted history, false availability, or lookahead could mislead downstream decisions, while no trading or account action is enabled.
Invariants affected: FINANCIAL_AND_DATA_GUARDRAILS §§34-35 (point-in-time and anti-lookahead), §47 (determinism); PROJECT_PROFILE §12 (historical provenance/coverage); TRAID_ENGINEERING_HARNESS §36 (validation ladder)
Verification-technique applicability:
  deterministic invariant testing: REQUIRED — dataset integrity, provenance, gap, duplicate and replay-time properties are exact contracts
  property-based testing: REQUIRED — deterministic permutation matrices exercise record-order and duplicate invariance without a new dependency
  failure injection: REQUIRED — corrupt storage, partial publication and provider failures must fail closed
  fuzzing: CONDITIONAL — use bounded malformed-input generation if deterministic adversarial cases expose an unmodeled parser state
    Trigger: deterministic adversarial parser cases reveal an unmodeled input class or insufficient boundary coverage
  mutation testing: CONDITIONAL — use targeted mutation only if review finds a false-green invariant test
    Trigger: developer review or audit finds a test that passes despite a violated C06 invariant
    Trigger observed: YES — independent audit found surviving incomplete-candle and retry-limit mutations; bounded checks and closure are recorded in C06 Evidence
  differential testing: REQUIRED — equivalent source payloads must normalize like the existing C04 adapter where semantics overlap
  adversarial testing: REQUIRED — future data, OI, conflicting duplicates, malformed timestamps and symlink escape are explicit hazards
  chaos testing: NOT_APPLICABLE — C06 has no distributed runtime or service-failover system
  formal methods: NOT_APPLICABLE — deterministic examples and permutation/failure tests can exercise this bounded serialization and replay contract
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
V1-C06 historical source, provenance, storage and replay are active.
No financial policy or execution authority changes; global V1 guardrails remain in force.
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
Historical Replay Foundation: COMPLETE — C06 dataset/replay foundation delivered
Anti-Lookahead Evidence: PASS — C06 modeled replay-availability boundaries proven; backtesting remains future work
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

Current verification reference:

```text
TraID repository test state: VERIFIED — actual C07 results are owned by the C07 Evidence entry
Harness consistency: PASS — C07 production checker; final freeze rechecked separately
Readiness gate: PASS — C07 runtime, C05 dependency and canonical alignment
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
CARD_QUALITY_GATE: PASS — C07 local proof and independent Claude PASS preserved; original FAIL retained; integration verification pending; correction quality evidence owned by Evidence §26
Evidence updated: YES — see C07 Evidence
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
Latest Evidence Update: C06 POST-MERGE GOVERNANCE CLOSURE — PR #10, PR #11, and PR #12 delivery recorded; original 325 passed / 3 summary-fixture failures preserved as history
Evidence Card: V1-C06
Evidence Status: COMPLETE — C06 delivery remains complete; delivered maintenance audits are HISTORICAL; no active maintenance
Critical Missing Proof: NONE for delivered C06 and maintenance policy; terminal procedure evidence is retained externally under GIT_WORKFLOW.md §21.1
Learning Record Status: COMPLETE — C06 learning fields recorded in Evidence Map
Key Demonstrated Lesson: historical event time, receipt time, and inferred replay availability require distinct contracts
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
Checkpoint Type: POST_MERGE_RECONCILIATION
Branch: main
Commit/State: 622d7848bb00cdd0d1c3a877844b1c3099230f75 — historical PR #12 policy merge and terminal base
Validation: historical maintenance validation PASS — 349 tests; original 325 passed / 3 failed and intermediate 333 passed remain historical evidence; terminal validation is recorded externally under GIT_WORKFLOW.md §21.1
Rollback Path: forward corrective governance commit or revert; no history rewrite
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
Branch: main; Card branch: card/v1-c06-historical-data-replay-foundation
Commits: 4090151f937006b227f9644ad284d504c04884ef (C06 source); 1c40b3a5b0c801d303d71053c411427767d671c1 (C06 squash merge); prior Card commits recorded above
Push: C06 Card branch and origin/main VERIFIED
PR: #10 — https://github.com/jo-soroush/traid-market-intelligence/pull/10
PR State: MERGED — both hosted c01-baseline/test checks PASS
Human Review: APPROVED — explicit C06 controlled-delivery authorization
Merge Approval: GRANTED — explicit C06 controlled-delivery authorization
Merge: VERIFIED — `1c40b3a5b0c801d303d71053c411427767d671c1` squash merge on main
Post-Merge Verification: original 325 passed / 3 summary-fixture failures preserved as history; PR #11 correction and PR #12 reconciliation policy delivered; recorded policy candidate validation 349 passed; terminal validation and synchronization evidence is retained externally under GIT_WORKFLOW.md §21.1
```

The block above records the verified C06 delivery and current integrated
repository state. Runtime branch, HEAD, remote, and worktree facts are derived
from Git when validated.

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
Deferred ID: D-OI-001
Originating Card: V1-C04 readiness / semantic verification
Idea: Resolve Hyperliquid raw open-interest unit and aggregation semantics for canonical mapping
Reason Deferred: Official evidence establishes the field exists and is likely size-related, but does not fully establish exact API unit and one-sided versus combined aggregation meaning
Target Card / Future Version: No active Card; future version after authoritative Hyperliquid semantics are verified; C09 may consume only verified canonical OI under its separately authorized contract
Dependency: authoritative Hyperliquid documentation/source/runtime evidence establishing unit and aggregation semantics
Risk if Forgotten: downstream derivatives/crowding analysis may lack trustworthy open-interest context
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

D-008
Decision: C04's required OI outcome is explicit unavailable/unverified when provider semantics cannot be verified. Raw Hyperliquid OI semantics remain deferred until authoritative evidence is available; unverified semantics cannot enter Core as trusted values. C09 OI metrics are conditional on verified canonical OI.
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
| V1-C04 | Hyperliquid Provider Verification & Adapter | COMPLETE | YES | PASS | COMPLETE |
| V1-C05 | Data Quality, Freshness & Provenance | COMPLETE | YES | PASS | COMPLETE |
| V1-C06 | Historical Data & Replay Foundation | COMPLETE | YES | PASS | COMPLETE |
| V1-C07 | Order Book & Liquidity Analytics | READY_FOR_HUMAN_REVIEW | YES | PASS | READY_FOR_HUMAN_REVIEW |
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
Active Card is V1-C07
Next Roadmap Card: V1-C08
Repository Write Authorization: one Card integration lifecycle correction only; no financial changes; correction commit/push/PR GRANTED; correction merge NOT_GRANTED
Safe Resume: Continue only the authorized Card integration lifecycle correction on fix/card-integration-lifecycle-c07; C07 integrated but not verified/COMPLETE. Original Claude audit and FAIL history remain immutable. Correction commit/push/PR GRANTED by explicit user authorization (exact scope: the nine recorded correction paths); correction merge, C07 closure and C08 NOT_GRANTED.
C01-C06 COMPLETE. PR14 integrated and predecessor archived in this normal C07 task.
D-OI-001 remains DEFERRED; C08 and later NOT_GRANTED.
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
