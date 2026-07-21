# Current Codex Task

- task_id: `INFRA-REPORT-001-TERMINAL-MARKDOWN`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `true`
- task_kind: `INFRASTRUCTURE`
- data_ready: `false`
- commit_message: `infra: install terminal Markdown reporter`

## Objective

Install the already committed terminal-reporting infrastructure. This is a manual bootstrap task because the running orchestrator cannot safely replace its own installed runtime.

The reporter must automatically generate one human-readable Markdown report for every terminal task state:

- `COMPLETED`;
- `FAILED_TECHNICAL`;
- `BLOCKED_USER_DECISION`.

Reports are runtime evidence and must be written outside the repository under:

`~/.local/state/msm-orchestrator/reports/`

The task-specific report is:

`~/.local/state/msm-orchestrator/reports/<task_id>.md`

The most recent report is copied to:

`~/.local/state/msm-orchestrator/reports/latest.md`

## Required report content

Each report must include:

1. final orchestrator status and acceptance state;
2. experiment `REPORT.md` claim, when present;
3. an explicit mismatch warning when an experiment claims READY/ACCEPT but the orchestrator did not accept it;
4. role summaries and every available finding from planner, implementer, auditor and corrector results;
5. state transitions from the JSONL log;
6. task artifacts with presence, byte size and SHA-256;
7. rendered contents of small `validation_summary.csv` and `protocol_reconciliation.csv` files;
8. paths to the envelope, transition log and role-result JSON files.

The reporter must not modify task verdicts, repository files, experiment artifacts or Git state.

## Bootstrap

Run from the repository root:

```bash
./start.sh
```

`start.sh` must install and start `msm-reporter.service`, run the reporter self-test during installation, and exit after confirming the infrastructure bootstrap.

The reporter must immediately generate a retrospective report for existing terminal envelopes, including `EXP-031R4-TEMPORAL-VALIDATION-2025` while its uncommitted artifacts are still present.

## Acceptance

- `automation/msm_reporter.py --self-test` prints `REPORTER_SELF_TEST_OK`;
- `msm-reporter.service` is active;
- `reports/EXP-031R4-TEMPORAL-VALIDATION-2025.md` exists;
- that report states `FINAL STATUS: FAILED_TECHNICAL`;
- that report states `ORCHESTRATOR ACCEPTANCE: NOT ACCEPTED`;
- that report records the conflicting experiment claim `TEMPORAL_VALIDATION_DATASET_READY`;
- all four auditor findings are present in the Markdown report;
- the protected Pine remains byte-identical, dirty and unstaged.

## Hard protections

Do not modify, stage, delete, rename or rewrite any experiment file during bootstrap. In particular, preserve:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

with SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`
