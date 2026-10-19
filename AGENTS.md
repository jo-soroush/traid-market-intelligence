# TraID — AI Agent Working Rules

## Purpose
Improve software-development accuracy and quality using separate implementation and independent review. This is a personal software project, not an organizational approval or compliance system. Keep the process lightweight.

## Roles and independence
- **Claude Code — implementer:** Understand the task and existing code, implement the scoped change, write and run relevant tests, and report what actually ran.
- **Codex — independent reviewer:** Review the requirement and relevant repository documentation first, then inspect the implementation diff and tests. Look for bugs, missing requirements, weak tests, regressions, and violations of existing product constraints. Report findings with file/line references and severity. Do not modify code while acting as reviewer.
- The implementation agent's self-tests are useful, but they are not independent approval. A reviewer must not independently approve code it authored.
- The owner makes final scope and merge decisions. Never push directly to `main` or merge without explicit owner authorization.

## Simple task flow
1. **Define:** State the goal, in-scope behavior, and observable completion criteria. Use the repository's current code and product documentation as the source of truth; ask rather than guess when a blocking detail is missing.
2. **Implement (Claude):** Make the smallest relevant change and add/update appropriate tests. Do not weaken checks just to make them pass.
3. **Verify:** Run focused tests, then the relevant existing project checks. Distinguish tests actually run from tests not run; report failures plainly.
4. **Review (Codex):** Inspect the requirement, diff, tests and actual results independently. Give actionable findings, or say explicitly when no findings were identified; never claim this proves correctness.
5. **Fix and deliver:** Claude addresses valid findings; Codex reviews material fixes when needed. Use normal Git commits, a PR and GitHub CI. The owner decides whether to merge.

This flow is sequential where review depends on completed code. Do not introduce orchestration or claim the two roles are working simultaneously on the same unfinished change.

## Existing project safeguards
- Respect `FINANCIAL_AND_DATA_GUARDRAILS.md` and the project's actual product requirements. TraID is not a live trading system: do not add live order execution, wallet keys or trading credentials.
- Treat missing/stale input as untrusted, never silently replace missing values with zero, preserve units and timestamps, and prevent lookahead/data leakage.
- Keep AI-generated interpretations separate from verified market data. Do not bypass applicable product checks.
- Avoid unrelated refactors, dependencies, new governance files, special hashes, evidence databases or custom harness scripts unless a concrete product need is demonstrated and the owner approves.

## Validation and evidence
- Existing baseline commands (run from the project environment): `python -m pytest` and `bash scripts/check_secrets.sh`.
- Keep evidence in the ordinary PR: task goal, main code changes, test commands and observed results, Codex findings and resolutions, and CI result/link. No separate evidence-map file is required by default.
- Existing CI and real test output are evidence; agent claims alone are not. For important behavior, check that tests actually measure the requirement rather than mirroring implementation assumptions.

## Environment and Git
- Verify the active repository, branch and working-tree status before editing.
- Use separate Git branches/worktrees if separate agent checkouts are needed; never share an editable Python environment between worktrees without verifying imports resolve to the intended source tree.
- Avoid conflicting edits and never overwrite another worktree's work. Do not force-push or perform destructive cleanup without explicit authorization.
- Historical references to former TraID Harness/Card approval procedures are not instructions to reintroduce those processes. Prefer current code, product constraints, and the owner's active task.
