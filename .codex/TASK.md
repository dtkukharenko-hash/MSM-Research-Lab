# Current Codex Task

- task_id: `AUTOMATION-001-R1-RUNNER-SANDBOX-CORRECTION`
- status: `READY`
- published_at: `2026-07-14`
- target_branch: `main`
- commit_message: `AUTOMATION-001 fix runner git and sandbox responsibilities`

## Objective

Finish and correct the partially created MSM Codex runner in `automation/`.

The current draft correctly creates files in the repository, but its runtime prompt expects Codex running with `workspace-write` to commit and push. With the system bubblewrap sandbox, `.git` is protected, so Codex cannot reliably write `FETCH_HEAD`, the index, objects, or refs.

Implement this responsibility split:

1. The shell runner performs Git synchronization, staging, commit, and push outside Codex.
2. Codex only modifies permitted repository working files and writes `.codex/RESULT.md` describing the implementation; it must not run `git pull`, `git add`, `git commit`, or `git push`.
3. The read-only auditor runs before the shell runner commits.
4. The shell runner commits and pushes only after the audit reports `PASS` or `USER_DECISION_REQUIRED` with `technical_pass=true`.
5. `TECHNICAL_CORRECTION_REQUIRED` and `AUDIT_FAILED` must not be committed automatically.

This is an infrastructure correction only. Do not modify research files.

## Existing local state

The repository may already contain untracked partial files under `automation/`. Inspect and revise them; do not discard working implementation blindly.

The exact existing user modification below must remain untouched, unstaged, and uncommitted:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

## Forbidden changes

Never modify or stage:

- `experiments/**`
- `docs/**`
- `MEMORY.md`
- `docs/DEFINITIONS.md`

`PROJECT_QUEUE.md` may be updated only to record automation infrastructure status.

Do not install systemd units during this task. Do not use `sudo`. Do not write outside `/home/nnv/MSM-Research-Lab`.

## Required files

Complete and validate:

- `automation/README.md`
- `automation/install.sh`
- `automation/msm_runner.sh`
- `automation/msm_audit.sh`
- `automation/runner.service`
- `automation/runner.timer`
- `automation/state.json`
- `.codex/AUTOPILOT_POLICY.md`
- `.codex/RESULT.md`

## Required runner flow

### Phase A — preflight outside Codex

The shell runner must:

1. acquire a non-blocking `flock`;
2. verify it runs as `nnv`;
3. allow only the exact unstaged Pine modification above;
4. run `git pull --ff-only origin main` before starting Codex;
5. require exact `status: READY` and a non-empty `task_id`;
6. calculate and persist the task SHA-256;
7. skip a task already completed for the same task ID and hash unless an explicit external retry flag exists;
8. record start commit and state.

### Phase B — Codex implementation

Run Codex with:

- `/home/nnv/.local/bin/codex exec`
- model `gpt-5.6-terra`
- reasoning `medium`
- sandbox `workspace-write`
- approval `never`
- timeout 4 hours

The prompt must explicitly say:

- modify repository files required by `.codex/TASK.md`;
- do not run any Git mutation or network synchronization command;
- do not run `git pull`, `git add`, `git commit`, or `git push`;
- do not touch the protected Pine file;
- write/update `.codex/RESULT.md` with task ID, tests, changed files, and status `IMPLEMENTED_AWAITING_AUDIT`;
- leave changes uncommitted for the shell runner.

After Codex exits, the runner must verify:

- protected Pine hash unchanged;
- protected Pine not staged;
- no forbidden research or docs path changed;
- `.codex/RESULT.md` exists and matches task ID;
- at least one allowed implementation path changed;
- no unexpected staged changes exist.

### Phase C — audit before commit

Run `automation/msm_audit.sh` read-only against the uncommitted worktree.

The auditor must not require implementation/result commit SHAs because they do not exist yet. Pass instead:

- task ID;
- task hash;
- starting commit;
- worktree diff hash or equivalent deterministic snapshot identifier.

The audit JSON must include:

- `task_id`
- `task_hash`
- `starting_commit`
- `worktree_diff_hash`
- `audit_status`
- `technical_pass`
- `research_decision_required`
- `blocking_findings`
- `warnings`
- `recommended_action`
- `finished_at`

Allowed audit statuses:

- `PASS`
- `USER_DECISION_REQUIRED`
- `TECHNICAL_CORRECTION_REQUIRED`
- `AUDIT_FAILED`

### Phase D — shell-controlled commit and push

Only when:

- audit status is `PASS`; or
- audit status is `USER_DECISION_REQUIRED` and `technical_pass=true`;

then the shell runner must:

1. recheck the protected Pine hash and staged state;
2. stage only an explicit allowlist of files changed for the task, never `git add .` or `git add -A`;
3. reject any changed path under forbidden directories;
4. update `.codex/RESULT.md` to record the implementation commit as `PENDING_SHELL_COMMIT` before commit, or use a two-commit workflow documented below;
5. create the implementation commit using the task commit message;
6. push implementation commit with `git push origin main`;
7. update `.codex/RESULT.md` with actual implementation SHA and push status;
8. create a separate result commit;
9. push the result commit;
10. record both SHAs and final state.

A safe two-commit workflow is required:

- Commit 1: implementation files plus `.codex/RESULT.md` showing `implementation_commit_sha: PENDING_SHELL_COMMIT`.
- Determine Commit 1 SHA and push.
- Update `.codex/RESULT.md` with real Commit 1 SHA and push status.
- Commit 2: result metadata only.
- Push Commit 2.

The protected Pine must never be staged in either commit.

On audit `TECHNICAL_CORRECTION_REQUIRED` or `AUDIT_FAILED`:

- do not stage, commit, or push;
- persist audit JSON and state;
- stop for manual correction.

## Explicit staging allowlist

The runner must derive changed paths and permit only task-owned paths. For this infrastructure task, accepted paths are:

- `automation/**`
- `.codex/AUTOPILOT_POLICY.md`
- `.codex/RESULT.md`
- `PROJECT_QUEUE.md`

For future tasks, use a safe task-declared allowlist mechanism. Do not assume every changed repository file is safe merely because Codex changed it.

Document the chosen future-task allowlist mechanism in `automation/README.md`. A simple supported approach is an optional `.codex/ALLOWLIST.txt`, one repository-relative glob/path per line, plus always-allowed `.codex/RESULT.md`; absence of the file must block automatic commit rather than stage arbitrary changes.

## Fixes required in current draft

1. Remove commit/push requirements from the Codex prompt.
2. Audit the uncommitted worktree before committing.
3. Move all commit and push operations to `msm_runner.sh`.
4. Do not pass a nonexistent audited implementation commit to the auditor.
5. Make `result_pushed` and duplicate detection use task ID plus task hash.
6. Ensure `retry_requested` cannot remain permanently true after one retry; consume/reset it atomically.
7. Ensure the original `automation/state.json` template is not used as mutable runtime state after installation; runtime state remains under `/home/nnv/.local/state/msm-runner/state.json`.
8. Fix `install.sh --dry-run` so it validates files without requiring them to already have executable bits, or ensure executable modes are set and committed. Document the behavior.
9. Add a normal text run summary log alongside JSONL/stderr/final output.
10. Ensure `runner.service` has a suitable `PATH`, `HOME=/home/nnv`, working directory, user/group `nnv`, and hardening that does not prevent required Git/SSH/Codex access.
11. Ensure the timer runs every 5 minutes and uses `Persistent=true` with a small randomized delay only if documented.
12. Do not implement task queues or automatic correction loops in this revision.

## Validation

Run and report:

- `bash -n automation/install.sh`
- `bash -n automation/msm_runner.sh`
- `bash -n automation/msm_audit.sh`
- `systemd-analyze verify automation/runner.service automation/runner.timer` where available; if paths inside units prevent direct verification, verify temporary renamed copies or report the exact limitation honestly;
- `./automation/msm_runner.sh --dry-run`
- source scan proving Codex prompt forbids Git mutation;
- source scan proving shell runner contains explicit commit/push logic after audit;
- source scan proving no `git add .` or `git add -A`;
- source scan proving protected Pine exclusion;
- source scan proving automatic commit is blocked without an allowlist;
- verify no research file changed other than the pre-existing unstaged protected Pine;
- verify no secret, token, or auth file is committed.

## Result requirements

Update `.codex/RESULT.md` with:

- task ID `AUTOMATION-001-R1-RUNNER-SANDBOX-CORRECTION`;
- status `IMPLEMENTED_AWAITING_MANUAL_COMMIT` for this one bootstrap run, because the current manual Codex invocation cannot write `.git`;
- files created/modified;
- all validations and outcomes;
- explicit confirmation that no research file was modified;
- installation commands, but do not install;
- note that after this bootstrap task is manually committed and installed, future tasks use shell-controlled Git.

Do not attempt commit or push from this current Codex run. Leave all intended files uncommitted for manual review and bootstrap commit.
