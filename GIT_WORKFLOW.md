# GIT_WORKFLOW.md — TraID

## 0. Purpose

This is TraID's canonical Git and GitHub delivery procedure.

It owns branch, checkpoint, commit, push, pull-request, merge, rollback, and integration procedure. It does not redefine Card scope, architecture, financial controls, or implementation evidence.

```text
AGENTS.md → approval/execution/safety rules
TRAID_V1_ROADMAP.md → Card order
TRAID_CARD_SPECIFICATIONS.md → exact Card contract
TRAID_CARD_EVIDENCE_MAP.md → actual technical/learning evidence
PROJECT_CONTROL.md → current operational checkpoint
GIT_WORKFLOW.md → Git/GitHub delivery procedure
Git → live branch/SHA/upstream/worktree/integration truth
```

If documentation disagrees with live Git facts, inspect Git and reconcile. Never invent Git state.

## 1. Core Principles

```text
one Card → one primary branch
small coherent changes
validate before commit
evidence before delivery claims
human approval before consequential Git actions
no secrets/generated junk
no force push/history rewrite by default
no direct Card implementation on main
no automatic merge
no automatic next Card
known checkpoint before risky change
```

Git provides versioned checkpoints. GitHub provides review and traceability. Neither may redefine TraID engineering truth.

## 2. Approval Boundary

Read-only Git inspection is allowed:

```bash
git status
git branch --show-current
git log
git diff
git diff --cached
git show
git remote -v
git rev-parse
git ls-files
```

Explicit human approval is required before:

```text
commit
push
PR creation
material PR update
merge
force push
shared-history rewrite/rebase
consequential branch deletion
tag/release
deployment/release
```

Card-start approval is not commit/push/PR/merge approval. Approval for one action does not silently authorize later consequential actions.

Two-phase Card workflow:

```text
PHASE 0 — PRE-CARD READINESS / PREFLIGHT
→ verify mandatory runtime, tools, Docker, services, credentials/configuration,
  network, source verification, datasets/fixtures, and Exit-Gate dependencies
→ missing mandatory prerequisite = READINESS_GATE: BLOCKED
→ STOP BEFORE IMPLEMENTATION

PHASE 1 — IMPLEMENT + VALIDATE
→ requires explicit Card-start approval
→ bounded implementation, validation, Evidence, and CARD_QUALITY_GATE
→ successful result = READY_FOR_HUMAN_REVIEW
→ no commit/push/merge authority

PHASE 2 — HUMAN REVIEW + DELIVERY
→ requires explicit human delivery approval
→ approved commit/push/merge, delivery verification, and reconciliation
→ only then Card = COMPLETE and Active Card = NONE
```

`CARD_QUALITY_GATE: PASS` alone never authorizes delivery or implies
`COMPLETE`. `READY_FOR_HUMAN_REVIEW` remains the active Card state until
approved delivery is verified.

## 3. Repository Reality Check

Before Card work and consequential Git actions inspect at minimum:

```bash
git status --short
git branch --show-current
git log -5 --oneline --decorate
git remote -v
git rev-parse HEAD
```

When relevant inspect upstream:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

Fetch before remote equality comparison when appropriate and approved:

```bash
git fetch <remote>
```

Record actual results only.

Uncertain repository state:

```text
PROJECT_STATE_CONFLICT
STOP
```

## 4. Main Branch Protection

Never implement a TraID Card directly on `main`.

`main` represents integrated reviewed state. Do not use it as a scratch branch.

Before Card branch creation, verify the intended base and worktree.

## 5. Branch Model

Preferred:

```text
main
└── card/v1-cNN-short-slug
```

Examples:

```text
card/v1-c01-repository-baseline
card/v1-c04-hyperliquid-adapter
card/v1-c17-deterministic-risk-gate
card/v1-c26-golden-case
```

Rules:

* one primary branch per Card;
* include Card ID;
* branch from verified approved base;
* do not mix future Cards;
* do not reuse unrelated branches;
* record start commit;
* use an extra recovery/review branch only for a concrete reason.

If the repository already has a durable verified naming policy, preserve it.

## 6. Card Branch Start

After explicit Card-start approval and repository reconciliation:

```bash
git switch <verified-base>
git status --short
git switch -c card/v1-cNN-short-slug
```

Do not run blindly on a dirty/uncertain worktree.

Before first implementation write:

```text
Card identity verified
dependencies verified
branch verified
start commit recorded
Contract Map / Risk Map complete
ROADMAP_ALIGNMENT_GATE: PASS
```

Branch creation never overrides a blocked gate.

## 7. Working Tree Discipline

During a Card:

* keep edits inside authorized scope;
* inspect diff frequently;
* do not mix unrelated cleanup;
* do not edit future Card scope;
* do not commit local caches/build output/debug artifacts;
* do not commit credentials;
* do not delete unrelated user work.

Useful inspection:

```bash
git status --short
git diff
git diff --stat
git diff -- <path>
```

If unrelated changes exist, identify ownership first. Never discard/stash/reset/clean user changes just to make the worktree look clean.

## 8. Forbidden Commit Content

Unless a verified requirement explicitly says otherwise, never commit:

```text
.env
real credentials
AWS access keys
exchange API/trading keys
wallet private keys / seed phrases
tokens
local model weights
venv/ or .venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
coverage/build artifacts
temporary logs
user-local IDE/OS state
generated secrets
```

`.env.example` may contain safe placeholders only.

A secret finding means:

```text
STOP
remove/redact safely
rotate if exposure may have occurred
record evidence
revalidate
```

Deleting a leaked secret does not erase exposure history.

## 9. Staging Discipline

Prefer explicit staging:

```bash
git add <explicit-paths>
git diff --cached --stat
git diff --cached
```

Avoid:

```bash
git add .
git add -A
```

unless the complete worktree was reviewed and every change belongs to the Card.

Before commit verify:

```text
only Card-scoped files staged
tests/evidence match actual work
no secrets
no generated junk
no future-Card leakage
no unrelated refactor
```

## 10. Validation Before Commit

A commit is a validated checkpoint, not a save button.

Before commit approval:

1. run focused tests for the bounded step;
2. run relevant regression/invariant checks;
3. update Evidence with actual results;
4. review `git diff`;
5. review staged diff;
6. review `git status`;
7. check secrets/generated artifacts;
8. state limitations;
9. reconfirm Card scope.

For consequential financial code, applicable financial/data/Risk/anti-lookahead tests must pass before calling a checkpoint validated.

Mandatory test failure:

```text
NO COMMIT AS A VALIDATED CHECKPOINT
```

A WIP/diagnostic commit requires explicit exceptional approval and honest labeling.

## 11. Commit Approval Report

Before requesting commit approval report:

```text
Card:
Bounded step:
Branch:
Files changed:
Focused validation:
Relevant regression/invariants:
Actual result:
Evidence updated:
git diff reviewed:
git status reviewed:
Secrets/generated artifacts:
Known limitations:
Proposed commit message:
Approval required: COMMIT
```

## 12. Commit Design

One commit should represent one coherent validated change.

Examples:

```text
feat(c04): add verified Hyperliquid market adapter
feat(c05): enforce data freshness and provenance
feat(c17): add deterministic risk gate
test(c18): enforce anti-lookahead and stop-first rules
docs(c01): install TraID engineering harness
```

Avoid vague messages such as `update`, `fix stuff`, `changes`, `final`, `misc`.

Do not combine unrelated refactors, dependency upgrades, documentation rewrites, and features.

## 13. Checkpoint and Rollback

Use the Playbook Shepherd pattern:

```text
Agent Action
→ State Change
→ Versioned Checkpoint
→ Validation
→ Accept or Rollback
```

A checkpoint identifies branch, commit/pre-change state, validation, scope, and rollback path.

Prefer forward fixes for reviewed/shared history.

```text
uncommitted mistake → restore only explicitly approved affected paths
local unshared commit → choose revert/reset only after consequence review and approval
shared/pushed commit → prefer corrective commit or git revert
merged change → prefer git revert or corrective PR
```

Never choose destructive rollback merely because it is faster.

## 14. Destructive Git Operations

Treat as consequential:

```bash
git reset --hard
git clean -fd
git checkout -- <path>
git restore --source=... <path>
git rebase
git commit --amend
git push --force
git push --force-with-lease
git filter-repo
git filter-branch
```

Require explicit human approval and recovery plan.

Before approval state why, affected files/commits, shared-history status, data-loss risk, safer alternatives, checkpoint, and recovery path.

Default:

```text
NO FORCE PUSH
NO HISTORY REWRITE
```

## 15. Push Policy

Push only an explicitly approved stable checkpoint.

Before push verify commit, Card scope, validation, Evidence, worktree, remote/upstream, and secret status.

First push normally:

```bash
git push -u <remote> <card-branch>
```

Later:

```bash
git push
```

Never push Card implementation directly to `main`. If push is rejected, diagnose; do not force push reflexively.

## 16. Draft Pull Request

Use a Draft PR while a Card remains active or not fully closed.

PR title includes Card ID and goal, for example:

```text
V1-C17: Deterministic Risk Gate
```

PR body uses actual evidence:

```text
Card ID/title
Engineering Goal
What changed
Architecture/ownership impact
Source/provenance decisions
Financial/data/AI/security implications
Validation actually run
Actual results
Exit Gate status
CARD_QUALITY_GATE status
Known limitations
Deferred work
Evidence location
No-future-Card statement
```

A Draft PR does not prove Card completion.

## 17. PR Review

Review both code and contract alignment:

```text
scope / Out of Scope
dependencies
architecture ownership
provider isolation
source/license provenance
financial/data semantics
AI boundary
Risk Gate authority
anti-lookahead where applicable
security/secrets
tests/evaluation
Evidence consistency
diff cleanliness
future-Card leakage
```

Material scope/architecture discovery:

```text
ARCHITECTURE_CHANGE_REQUEST or CARD_SCOPE_MISMATCH
STOP
```

Do not expand scope just to satisfy review comments.

## 18. PR Updates

Review fixes may be developed inside approved Card scope, but pushing/updating the external PR follows the approval boundary.

Before update: understand comment, confirm scope, rerun focused tests and affected regression, update Evidence, review diff.

Never mark a review concern resolved without implementing/validating the required resolution.

## 19. Pre-Merge Gate

Merge is prohibited unless:

```text
Card contract satisfied
exact Exit Gate proven
CARD_QUALITY_GATE: PASS
focused tests PASS
relevant regression PASS
applicable financial/data/AI/Risk/security invariants PASS
Evidence current
Project Control consistent
PR diff reviewed
no unrelated changes
secret/generated-artifact check PASS
limitations explicit
human merge approval granted
```

Unknown mandatory item:

```text
NO MERGE
```

GitHub green status alone is not enough.

## 20. Merge Strategy

Preferred default:

```text
squash merge
```

This supports one Card → one coherent integrated change.

Use another strategy only for a verified repository policy or concrete traceability need.

Never auto-merge. Automation approval cannot replace human merge approval.

## 21. Post-Merge Verification

After approved merge verify:

```text
merged commit exists on intended target
Card changes are contained
required files exist
working tree is understood
local/remote relation is understood
required post-merge validation still passes
Evidence delivery history is accurate
Project Control is reconciled
```

Typical checks, when appropriate:

```bash
git switch main
git pull --ff-only
git log -5 --oneline --decorate
git status --short
```

Do not start the next Card during verification.

## 22. Card Closure After Delivery

After verified approved integration:

```text
record branch/commit/PR/merge historical evidence
confirm Quality Gate remains PASS
confirm Exit Gate remains proven
update Project Control
mark COMPLETE only when delivery approval, delivery verification, and the
closure contract are satisfied
Active Card = NONE
STOP
```

Merge does not authorize the next Card.

## 23. Branch Cleanup

Branch deletion is optional unless verified policy requires it.

Delete only after integration is verified, no unique work remains, and applicable approval exists.

Never delete a branch to hide unresolved work.

## 24. Conflict Handling

For merge conflicts:

1. inspect conflict;
2. determine whether target changes alter Card assumptions;
3. STOP if scope/architecture/financial semantics changed;
4. choose least-destructive integration;
5. rerun affected validation;
6. update Evidence.

Never resolve semantic conflicts mechanically with "ours" or "theirs".

A clean textual merge does not prove a correct semantic merge.

## 25. Dependency Changes

Dependency changes have supply-chain impact.

Before significant dependency commit verify:

```text
Card permits it
required human approval exists
concrete need exists
license acceptable
version reproducible
security/lock-in considered
tests prove behavior
removal/rollback path understood
```

Do not add technology merely because a reference repository or Playbook mentions it. Review lockfile changes intentionally.

## 26. Generated and Large Artifacts

Do not commit raw exchange archives, model weights, large datasets, local databases, build products, or generated reports merely for convenience.

If Git truly must version an artifact, justify it, record provenance/version/hash, verify license/data rights, and keep it manageable/reproducible.

## 27. Tags and Releases

Release/tag only after applicable release Cards and explicit approval.

Before V1 release:

```text
C25 release gate PASS
C26 Golden Case PASS
C27 documentation/demo closure as applicable
critical invariants green
version identified
limitations documented
security PASS
human release approval
```

No ordinary Card should create a release tag.

## 28. Hotfix Policy

For a critical post-merge defect:

```text
identify affected integrated commit
record failure evidence
create approved bounded fix branch
add/regress failing test
implement smallest safe fix
run relevant regression
deliver through review
```

Urgency never bypasses Risk, financial, anti-lookahead, security, or Evidence requirements.

## 29. Tool Neutrality

Valid for Claude Code, Codex, Cursor, future agents, and human Git workflows.

Tool-specific automation must not weaken approval, scope, validation, Evidence, secret protection, no-force-push, human merge authority, or no-auto-next-Card rules.

## 30. Standard Delivery Flow

```text
VERIFY REPOSITORY
→ VERIFY ACTIVE CARD + APPROVAL
→ CREATE/VERIFY CARD BRANCH
→ CONTRACT/RISK MAP
→ ROADMAP_ALIGNMENT_GATE
→ BOUNDED IMPLEMENTATION
→ FOCUSED TESTS
→ RELEVANT REGRESSION / INVARIANTS
→ UPDATE EVIDENCE
→ REVIEW DIFF / STATUS / SECRETS
→ REQUEST COMMIT APPROVAL
→ COMMIT
→ REQUEST PUSH APPROVAL
→ PUSH STABLE CHECKPOINT
→ DRAFT PR WHEN APPROVED
→ REVIEW / FIX / REVALIDATE
→ EXACT EXIT GATE
→ CARD_QUALITY_GATE
→ REQUEST MERGE APPROVAL
→ MERGE
→ POST-MERGE VERIFICATION
→ RECORD DELIVERY
→ CARD COMPLETE
→ ACTIVE CARD NONE
→ STOP
→ SEPARATE NEXT-CARD APPROVAL
```

## 31. Delivery Report Templates

### Before Commit

```text
GIT_CHECKPOINT_READY
Card:
Branch:
Bounded step:
Files changed:
Validation run:
Actual result:
Evidence updated:
git diff reviewed:
git status reviewed:
Secrets/generated artifacts:
Known limitations:
Proposed commit:
Approval required: COMMIT
```

### Before Push

```text
PUSH_READY
Card:
Branch:
Commit:
Remote/upstream:
Validation state:
Evidence state:
Working tree:
Secrets check:
Approval required: PUSH
```

### Before PR

```text
PR_READY
Card:
Branch:
Commit(s):
Engineering Goal:
Summary:
Architecture impact:
Validation:
Exit Gate status:
CARD_QUALITY_GATE:
Known limitations:
Evidence location:
Approval required: PR CREATE/UPDATE
```

### Before Merge

```text
MERGE_READY
Card:
PR:
Target branch:
Exact Exit Gate: PASS
CARD_QUALITY_GATE: PASS
Relevant regression: PASS
Financial/data/AI/Risk/security checks:
Evidence current: YES
Project Control consistent: YES
Diff reviewed: YES
Secrets/generated artifacts: PASS
Known limitations:
Approval required: MERGE
```

### After Merge

```text
INTEGRATION_VERIFIED
Card:
Target branch:
Merged commit:
Post-merge checks:
Post-merge validation:
Evidence delivery record:
Project Control:
Remaining issues:
Card recommended status:
Next Card authorization: NOT_GRANTED
```

## 32. Final Rule

```text
GIT RECORDS VERSIONED CHANGE.
EVIDENCE PROVES ENGINEERING CLAIMS.
ROADMAP + CARD CONTRACT DEFINE AUTHORIZED WORK.
HUMAN APPROVAL AUTHORIZES CONSEQUENTIAL DELIVERY.

NO VALIDATION → NO VALIDATED CHECKPOINT.
NO EVIDENCE → NO COMPLETION CLAIM.
NO APPROVAL → NO COMMIT/PUSH/PR/MERGE.
NO FORCE PUSH BY DEFAULT.
NO DIRECT CARD WORK ON MAIN.
MERGE → VERIFY → RECORD → STOP.
NEXT CARD → SEPARATE HUMAN APPROVAL.
```

## 33. Hosted CI and Local Parity Contract

The repository workflow is `.github/workflows/ci.yml`, named `c01-baseline`.
It runs on `push` and `pull_request` on `ubuntu-latest`, installs Python
`3.13`, installs the project with `python -m pip install '.[dev]'`, runs
`pytest`, and runs `bash scripts/check_secrets.sh`. The workflow does not
currently run the local Harness checker, session bootstrap, readiness script,
or a separate compilation command.

Local success and hosted success are different facts:

```text
LOCAL PASS != HOSTED CI PASS
```

Python tests and subprocess helpers must not assume
`ROOT/.venv/bin/python` unless the workflow explicitly creates that path.
When the test is intended to exercise the current test interpreter,
`sys.executable` is the preferred portable choice. A test may intentionally
select another interpreter only when that distinction is part of the test
contract. Repository-relative paths, shell commands, permissions, working
directory, environment variables, case sensitivity, and generated/local-only
files must be reviewed against the hosted runner.

`CI_VERIFIED` requires the applicable GitHub Actions run for the pushed
commit/PR to show the required `test` job PASS, including its pytest and
secret-scan steps. GitHub branch-protection settings are NOT_VERIFIED from the
repository checkout; repository policy still requires the applicable hosted
CI result before delivery is called fully verified or a Card is called
COMPLETE. A failed run is a delivery blocker until diagnosed, corrected,
affected regression is rerun, and the new hosted result is recorded. A failure
after merge requires the same bounded maintenance path below and does not
silently reopen the completed Card. The human who approved the maintenance
change authorizes any subsequent push, PR update, or merge.

## 34. Post-Delivery Maintenance and Hotfixes

Completed Cards are not reopened for a bounded post-delivery defect. The
generic path is:

```text
verified main
→ verified defect
→ maintenance/hotfix authorization
→ maintenance or hotfix branch from verified main
→ smallest fix
→ focused regression
→ full affected validation
→ evidence and maintenance record
→ human delivery approval
→ push
→ hosted CI
→ merge
→ post-merge validation
→ clean main
```

While maintenance is active, `Active Card = NONE` and completed Card states
remain `COMPLETE`. A maintenance record belongs in `PROJECT_CONTROL.md`; it is
not a Roadmap Card and cannot authorize the next Card. It must identify a
task ID/title, reason, originating failure, base commit, branch, authorized
and prohibited scope, expected files, validation, external Git permissions,
status, safe resume point, and closure evidence.

Branch categories are:

| Category | Base and state | Active Card | Delivery rule |
|---|---|---|---|
| `main` | verified integration branch; clean after delivery | NONE after Card closure | protected; merge and post-merge verification |
| `card/v1-cNN-*` | verified `main`; one approved Card | required | Card Phase 1 then approved Phase 2 |
| `maintenance/*` | verified `main`; bounded post-delivery defect | NONE | maintenance authorization, focused/affected validation, hosted CI, approved merge |
| `hotfix/*` | verified `main`; urgent bounded defect when needed | NONE | same maintenance controls, with urgency recorded |
| recovery/review branch | only when explicitly authorized for recovery or review | depends on recorded purpose | no delivery until reconciled with the owning branch and approval |

The Harness/Bootstrap now accept an explicit, schema-checked maintenance
record only when the branch is `maintenance/*` or `hotfix/*`, require a
verified base and allowed dirty state, reject missing/mismatched records and
out-of-scope changes, and preserve `Active Card = NONE` and no next-Card
authorization. This generic enforcement is covered by maintenance regression
tests. Hosted CI remains a separate external gate.

## 35. External Actions and Egress

Read-only inspection is allowed. Push, PR creation/update, merge, deployment,
external API writes, and other consequential egress require explicit human
approval at the phase where the exact destination, commit, and scope are
known. Record the trusted destination identity before acting. The configured
Git remote is `origin` at
`https://github.com/jo-soroush/traid-market-intelligence.git`; current GitHub
branch-protection/settings status is `NOT_VERIFIED` from this checkout.
Least privilege, no-force-push, and no secret transmission remain mandatory.

## 36. Delivery State Definitions

These states are distinct and require their own evidence:

```text
IMPLEMENTED              approved files changed; no validation claim
LOCALLY_VALIDATED        required local checks passed
READY_FOR_HUMAN_REVIEW   Phase 1 evidence and CARD_QUALITY_GATE are complete; STOP
READY_TO_DELIVER         human review accepted; delivery approval still required
PUSHED                   approved commit exists on the intended remote branch
CI_VERIFIED              applicable hosted workflow/job passed for that commit
MERGED                   target branch contains the approved integration commit
POST_MERGE_VERIFIED      target branch and affected checks were reverified
COMPLETE                 all contract, evidence, approval, delivery, and reconciliation conditions pass
```

No generic `PASS` label substitutes for these states.

## 37. Consolidated Remediation and Prompt Churn

Prefer one comprehensive Phase 1 prompt, one independent audit, at most one
consolidated remediation cycle for related findings, and one delivery cycle.
Collect related symptoms, diagnose once, classify severity, repair the root
cause, rerun affected validation, and retain each failure record. Additional
prompts are justified only by new external failure evidence, genuine scope or
architecture conflict, missing approval, unexpected repository state, or an
unavailable external result. This is an operational rule, not an arbitrary
machine-count limit.
