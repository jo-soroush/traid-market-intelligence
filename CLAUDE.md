# Claude Code entry point

Read `AGENTS.md` completely, then `PROJECT_CONTROL.md`, the applicable
canonical Card specification, relevant evidence, and the engineering Harness.
Follow all Harness STOP conditions.

Canonical project state, specifications, architecture, evidence, authorization,
and delivery rules remain owned by their designated repository artifacts.
`CLAUDE.md` is a NON-CANONICAL Claude Code entry point only and must not
duplicate mutable project state.

Before acting, verify repository reality against canonical artifacts. If Git
state, Card state, authorization, specification, or evidence materially
conflict, STOP and report the contradiction rather than guessing.

## Implementation role

When authorized to implement a Card:

- work only within authorized scope;
- derive work from canonical specification, Exit Gate/Acceptance equivalent,
  affected Critical Invariants, and risk/verification record;
- do not weaken tests or controls to obtain PASS;
- treat executed evidence, not implementation-agent claims, as verification;
- stop on material failure and perform root-cause analysis before remediation;
- do not start another Card automatically.

Implementation authorization does not authorize delivery. Commit, push, PR,
merge, or other delivery actions require separate explicit human delivery
authorization and must follow `GIT_WORKFLOW.md`.

## Independent verifier role

When assigned the INDEPENDENT VERIFIER role:

- review the frozen candidate from the specification first;
- read its Exit Gate/Acceptance equivalent and affected Critical Invariants
  before trusting implementation;
- inspect the actual diff and executed evidence;
- actively search for missing requirements, false-green tests, invariant
  violations, scope leakage, weak failure handling, stale evidence, and
  contradictory state;
- report findings with reproducible references;
- do not certify from implementation-agent claims;
- do not edit the candidate during audit.

Remediation requires separate authorization. A materially remediated candidate
requires bounded independent re-audit.

While acting as INDEPENDENT VERIFIER, do not modify files, commit, push, create
or merge a PR, authorize delivery, or start another Card.
