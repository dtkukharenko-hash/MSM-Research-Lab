# MSM Codex runner

This is a one-task runner with a strict boundary: the shell service owns Git; Codex owns only permitted working-tree edits. The runner takes a non-blocking lock, permits only the known pre-existing EXP009A Pine edit, synchronizes `main`, invokes Codex in `workspace-write`, validates its uncommitted output, invokes a read-only auditor, and only then stages, commits, and pushes from the shell process.

Codex must never run `git pull`, `git add`, `git commit`, or `git push`. The auditor runs against the uncommitted snapshot and receives the task ID/hash, starting commit, and deterministic worktree-diff hash—never a nonexistent implementation commit.

Runtime state, logs, locks, and `audit.json` live only in `/home/nnv/.local/state/msm-runner`. `automation/state.json` is a committed schema/template and is never copied or mutated as runtime state. Alongside JSONL, stderr, and final Codex output, each run writes a short `*.summary.log` timeline.

## Commit gate and allowlists

Automatic commit is allowed only for audit `PASS`, or `USER_DECISION_REQUIRED` with `technical_pass: true`. `TECHNICAL_CORRECTION_REQUIRED` and `AUDIT_FAILED` leave the worktree untouched and stop. The protected Pine file is re-hashed and checked for staging before and after audit.

The bootstrap task `AUTOMATION-001-R1-RUNNER-SANDBOX-CORRECTION` has its task-defined allowlist: `automation/**`, `.codex/AUTOPILOT_POLICY.md`, `.codex/RESULT.md`, and `PROJECT_QUEUE.md`. Future tasks must provide a tracked `.codex/ALLOWLIST.txt`, one repository-relative shell glob/path per non-comment line; `.codex/RESULT.md` is always added. If that file is absent, the runner blocks automatic commit rather than guessing. It never uses `git add .` or `git add -A`.

The shell uses two commits: implementation files plus RESULT with `PENDING_SHELL_COMMIT`, then a metadata-only RESULT commit containing the actual first SHA and push status. Duplicate detection keys on both task ID and SHA-256 of `.codex/TASK.md`. An external `retry_requested: true` in the runtime state is atomically consumed/reset when the retry begins, so it cannot persist indefinitely.

## Prerequisites and installation

Requires Ubuntu/systemd, user `nnv`, Git/SSH access, `/home/nnv/.local/bin/codex`, `flock`, `timeout`, `sha256sum`, Python 3, and `bubblewrap`. The installed units are `msm-codex-runner.service` and `msm-codex-runner.timer`. The timer runs every five minutes; its documented randomized delay is at most 20 seconds and it is persistent across missed runs.

Review first, then install as an administrator:

```bash
./automation/install.sh --dry-run
sudo ./automation/install.sh --enable-now
systemctl status msm-codex-runner.timer
journalctl -u msm-codex-runner.service -f
cat /home/nnv/.local/state/msm-runner/state.json
cat /home/nnv/.local/state/msm-runner/audit.json
```

`--dry-run` only validates source files and prerequisites; it intentionally does not require executable mode bits, because installation sets those modes. It neither installs units nor writes runtime state. For a no-op runner check, use `./automation/msm_runner.sh --dry-run`; it does not pull, invoke Codex/audit, or change task/result files.

No queues or automatic correction loops are implemented in this revision.
