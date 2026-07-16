# AUTOMATION-005-R1 Result

- task_id: `AUTOMATION-005-R1-RESTORE-ALLOWLISTED-RESEARCH-PATHS`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`

## Defect corrected

`automation/msm_task_feeder.py::is_protected()` incorrectly rejected every path containing an `artifacts` component and every experiment `.md`, `.txt`, `.csv`, `.pine`, or `.json` path. Those two blanket restrictions were removed. Explicit, exact entries in `.codex/ALLOWLIST.txt` remain mandatory because `read_allowlist()` validates each normalized entry and feeder ingestion always calls it before queueing.

The unchanged hard protections still reject `docs/DEFINITIONS.md`, the exact protected EXP009A Pine path, `.codex/RESULT.md`, `.git` and `.git/*`, absolute installed-system paths, traversal and malformed paths, duplicate entries, and secret-, credential-, private-key-, PEM-, key-, and environment-like paths. Task-text gates and the `infrastructure_maintenance: true` automatic-ingestion block are unchanged.

## Changed files

- `automation/msm_task_feeder.py`
- `automation/verify_feeder.sh`
- `automation/AUTOMATION-005-R1-RESULT.md`

## Validation commands and exact outputs

```text
$ PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --fixtures
OFFLINE_OK
FIXTURES_OK
FIXTURES_OK

$ PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --service --test-mode --wait 1
OFFLINE_OK
SERVICE_STATIC_OK

$ PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --service --production --wait 1
OFFLINE_OK
SERVICE_STATIC_OK

$ PYTHONDONTWRITEBYTECODE=1 bash automation/verify_feeder.sh --health
OFFLINE_OK
HEALTH_OK

$ git diff --check
(no output; passed)

$ git diff --cached --quiet -- experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
(no output; passed)

$ ! find . -type f -name '*.pyc' -o -type d -name '__pycache__' | grep -q .
(no output; passed)
```

The isolated fixtures passed existing feeder coverage for identical-task deduplication, changed-hash blocking, concurrent enqueue, restart preservation, kill switch behavior, non-READY handling, infrastructure-task blocking, task-text gates, no Git mutation calls, and no Python cache artifacts.

## Allowlist and protection proof

The isolated fixtures explicitly enqueue each of these exact ordinary research allowlist entries with task text containing no research-decision gate:

- `experiments/EXP-TEST/source.py`
- `experiments/EXP-TEST/artifacts/report.md`
- `experiments/EXP-TEST/artifacts/metrics.csv`

Each returns `ENQUEUED`; the fixture also asserts that `read_allowlist()` returns precisely the listed path. The same fixture rejects blank, absolute (`/tmp`, `/usr`, `/etc`, `/home`), traversing, non-normalized, duplicate, `docs/DEFINITIONS.md`, `.codex/RESULT.md`, `.git`, `.git/config`, secret-like, and the exact protected EXP009A Pine allowlist entries.

## Protected Pine and worktree proof

The protected Pine was neither accessed for content nor modified by this task or its validation. Its post-validation SHA-256 is:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

The cached-diff check above passed, proving it is unstaged. Final status contains only the two implementation files and this report, plus the pre-existing unrelated modified protected Pine. No research file was modified by validation. All edits are intentionally unstaged and uncommitted.
