# Current Codex Task

- task_id: `EXP-031R6A3P3-PUBLISHED-PACKAGE-RECOVERY`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A3P3 publish recovered bounded-worker package`

## Objective

Publish the already computed and independently audited EXP-031R6A3R bounded-worker evidence into a fresh canonical directory that cannot conflict with pre-existing failed-attempt or recovery paths.

Do not rerun, import, or execute any experiment or fixture generator. This task is static recovery, validation, and publication only.

The authoritative terminal report for EXP-031R6A3R records planner PASS, implementer PASS, corrector PASS, final auditor PASS, and `BOUNDED_WORKER_REPRESENTATION_READY`. Its only terminal failure was `git push origin main` returning a nonzero exit status.

## No user decision

This is a DATA publication task. `USER_DECISION_REQUIRED` is forbidden.

Missing candidates, ambiguous candidates, unavailable blobs, failed validation, source conflicts, or publication uncertainty are technical defects and must be reported as `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`.

Do not interpret prose such as “does not claim TEMPORAL_VALIDATION_DATASET_READY” as an experiment status. The only accepted package status is an explicit declaration of `BOUNDED_WORKER_REPRESENTATION_READY`.

## Immutable baselines

Preserve every pre-existing dirty, tracked, and untracked path byte-for-byte and unstaged, including all EXP-031R4, EXP-031R5, EXP-031R6A, EXP-031R6A2, EXP-031R6A3, EXP-031R6A3R, EXP-031R6A3P, and EXP-031R6A3P2 runtime evidence.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not remove or rewrite pre-existing tracked cache or bytecode paths.

## Source package discovery

Find one unique valid EXP-031R6A3R source package using read-only inspection.

Preferred source:

1. a local Git commit whose subject is exactly `EXP-031R6A3R-BOUNDED-WORKER-ACCEPTANCE-CORRECTION` and whose first-parent diff contains exactly the original fifteen R6A3R paths;
2. if the commit is not reachable by ordinary refs, inspect local reflogs and dashboard backup branches read-only;
3. an existing pre-existing R6A3R worktree package may be used only when every one of its fourteen substantive files is byte-identical to the corresponding blob in the unique candidate commit.

Do not use an R4, R5, R6A, R6A2, R6A3, R6A3P, or R6A3P2 package as substantive evidence.

The candidate must satisfy all of the following:

- normal readable commit and tree;
- exactly the original fifteen R6A3R paths in its first-parent diff;
- every path is a regular blob, not a symlink or submodule;
- original `REPORT.md` explicitly declares `BOUNDED_WORKER_REPRESENTATION_READY`;
- all matching candidates resolve to one unique substantive content set;
- the package is not already fully published under the new R6A3P3 directory.

If no unique valid candidate exists, fail technically without reconstructing data.

## Fresh canonical publication directory

Create exactly these fifteen new paths:

- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/REPORT.md`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/experiment_031r6a3r.py`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_oct_observations.csv.gz`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_oct_volatility_state.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_jan_observations.csv.gz`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_jan_volatility_state.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_episode_control_summary.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_counterexamples.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_reconciliation.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_identity_checks.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/fixture_run_hashes.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/helper_provenance.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/memory_summary.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/implementation_audit.csv`;
- `experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER/test_results.csv`.

No other repository path may be created or changed.

## Copy contract

Copy the fourteen non-REPORT files byte-for-byte from the selected candidate commit into the new directory. Do not execute or import the recovered Python file.

Create a new `REPORT.md` that records:

- status exactly `BOUNDED_WORKER_REPRESENTATION_READY`;
- publication task ID and source candidate commit SHA;
- SHA-256 of every copied source and destination file;
- confirmation that all fourteen source/destination pairs are byte-identical;
- the prior R6A3R role verdicts and push-only failure provenance;
- confirmation that no scientific computation was rerun;
- confirmation that no full four-symbol calendar-2025 dataset was produced;
- no scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim.

Do not copy the old REPORT verbatim because the publication path and provenance must be explicit.

## Mandatory static validation

Without executing or importing the experiment script:

1. confirm exactly fifteen task-created paths and exact allowlist equality;
2. verify all fourteen copied files match candidate blob bytes and SHA-256;
3. stream-reopen every CSV and gzip file;
4. verify deterministic gzip `mtime=0`;
5. confirm every file is below 95 MiB;
6. confirm observations and volatility identity checks report PASS;
7. confirm volatility schema and compound identity include `representation`;
8. confirm five-representation invariance reports PASS;
9. confirm October committed observation reconciliation reports PASS at tolerance `1e-09`;
10. confirm October duplicate-preserving volatility multiset reconciliation reports PASS at tolerance `1e-09`;
11. confirm both deterministic fixture runs have equal substantive hashes and row counts;
12. confirm memory evidence is below `1,048,576 KiB`;
13. confirm helper provenance references committed EXP-027, EXP-029R, and EXP-031 sources with positive use;
14. confirm `implementation_audit.csv` and `test_results.csv` contain no unresolved acceptance FAIL;
15. run `git diff --check` on all fifteen new paths;
16. confirm protected Pine and every baseline path remain unchanged and unstaged;
17. confirm no new cache, bytecode, SQLite, journal, temporary, partial, or shard path exists.

## Acceptance

Planner returns PASS when a unique source package is technically discoverable.

Implementer returns PASS only after creating all fifteen new allowlisted files and completing static validation.

Auditor must inspect the candidate commit, all destination files, hashes, CSV/gzip streams, evidence tables, allowlist boundary, and immutable baselines directly.

Final PASS requires:

- one unique valid source package;
- fourteen substantive files copied byte-identically;
- new publication REPORT with exact status `BOUNDED_WORKER_REPRESENTATION_READY`;
- every mandatory static check passing;
- no experiment execution or recomputation;
- no baseline or out-of-allowlist change;
- all task changes unstaged for the orchestrator.

On final PASS, the orchestrator must commit and push exactly the fifteen R6A3P3 paths to `origin/main`.

EXP-031R6B remains blocked until this task reaches orchestrator `COMPLETED` and the R6A3P3 package is visible on `origin/main`.
