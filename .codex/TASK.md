# Current Codex Task

- task_id: `EXP-031R6A3P2-PUBLICATION-RECOVERY`
- status: `READY`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `DATA`
- data_ready: `true`
- data_manifest: `data/readiness/DATA-001_BYBIT_2025/REPORT.md`
- data_manifest_sha256: `fd894efc57bbd91c792db92afa31f15e091a7f7128055ff2c57cf471e580f4ba`
- commit_message: `EXP-031R6A3P2 publish recovered bounded-worker outputs`

## Objective

Recover and publish the already computed and independently audited EXP-031R6A3R package after its sole terminal failure: the orchestrator created the result commit but `git push origin main` failed.

Do not rerun the bounded worker, fixture generation, experiment script, canonical-data processing, or scientific computation. This is publication recovery only.

The authoritative terminal report states:

- planner: PASS;
- implementer: PASS;
- final auditor: PASS;
- corrector: PASS;
- package claim: `BOUNDED_WORKER_REPRESENTATION_READY`;
- terminal failure reason: only `git push origin main` returned exit status 1.

This task makes no new scientific claim. It only restores the accepted fifteen-file package into the worktree, independently rechecks the package, and lets the orchestrator create and push a fresh publication commit.

## Resolved decisions

These decisions are fixed and require no user judgment:

1. Do not repeat EXP-031R6A3R computation.
2. Recover only from a pre-existing local Git commit created by the failed EXP-031R6A3R `commit_once()` path.
3. The candidate may be found in local backup branches, local refs, or reflogs created before or during dashboard synchronization.
4. Never use a working-tree failed-attempt directory as the recovery source.
5. The orchestrator is authorized to stage, commit, and push exactly the fifteen allowlisted recovered paths after final auditor PASS.
6. Any missing, ambiguous, or invalid recovery commit is `TECHNICAL_CORRECTION_REQUIRED` or `FAILED`, not `USER_DECISION_REQUIRED`.
7. `.codex/RESULT.md` must not be created or modified.
8. The predecessor task `EXP-031R6A3P-PUBLICATION-RECOVERY` has a terminal envelope and must not be rerun. This task uses a new unique ID solely to permit one fresh recovery attempt.

## Immutable baselines

Preserve every pre-existing dirty or untracked path byte-for-byte and unstaged, including all EXP-031R4, EXP-031R5, EXP-031R6A, EXP-031R6A2, EXP-031R6A3, and failed runtime evidence.

The protected Pine must remain byte-identical, dirty, and unstaged:

`experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine`

Required SHA-256:

`0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`

Do not remove or rewrite any pre-existing tracked cache or bytecode path.

## Candidate commit discovery

Search read-only across local Git refs and reflogs for the commit created by the failed task.

A candidate is eligible only when all of the following hold:

1. its commit subject is exactly `EXP-031R6A3R-BOUNDED-WORKER-ACCEPTANCE-CORRECTION`, or the commit is otherwise uniquely tied to that failed task by the local reflog and timestamp;
2. it has a normal commit object and readable tree;
3. its first-parent diff contains exactly the fifteen paths in `.codex/ALLOWLIST.txt` and no other path;
4. every allowlisted path exists as a regular blob in the candidate tree;
5. none of the fifteen paths is a symlink, submodule, deletion, rename target from outside the allowlist, or executable-mode surprise;
6. the candidate package contains `REPORT.md` declaring `BOUNDED_WORKER_REPRESENTATION_READY`;
7. the candidate is not already reachable from `origin/main`;
8. all matching candidate commits resolve to one unique fifteen-file content set.

Record the selected commit SHA and the complete candidate validation in the implementer findings and `REPORT.md`. If no candidate exists, or multiple non-identical candidates remain, fail without generating or reconstructing data.

## Recovery method

Restore the fifteen blobs directly from the selected commit into the existing allowlisted paths.

Allowed approach:

- create parent directories as required;
- for each allowlisted path, stream `git show <candidate>:<path>` into that same worktree path;
- preserve the blob bytes exactly;
- do not execute the recovered Python file;
- do not use `git checkout`, `git restore`, cherry-pick, merge, reset, rebase, or branch switching inside the worker;
- do not alter `.git` refs;
- do not stage files.

After restoration, verify every worktree file SHA-256 equals the corresponding candidate blob SHA-256.

## Mandatory package revalidation

Inspect the recovered files directly. Do not rerun computation.

At minimum verify:

1. exactly fifteen task-created paths exist and they equal the allowlist;
2. every recovered byte hash equals the selected commit blob;
3. every CSV and gzip file reopens successfully;
4. deterministic gzip header `mtime=0` remains true;
5. every file is below 95 MiB;
6. `REPORT.md` declares `BOUNDED_WORKER_REPRESENTATION_READY` and explicitly makes no full-2025 or scientific claim;
7. observation and volatility identity evidence reports PASS;
8. volatility schema and compound identity include `representation`;
9. five-representation volatility invariance evidence reports PASS;
10. October committed-observation reconciliation reports PASS at tolerance `1e-09`;
11. October duplicate-preserving volatility multiset reconciliation reports PASS at tolerance `1e-09`;
12. both deterministic fixture runs have equal substantive hashes and row counts;
13. memory evidence is below `1,048,576 KiB`;
14. helper provenance names committed EXP-027, EXP-029R, and EXP-031 sources with positive production-use evidence;
15. `implementation_audit.csv` and `test_results.csv` contain no unresolved FAIL for an acceptance requirement;
16. `git diff --check` passes for all recovered paths;
17. no path outside the allowlist changed;
18. all immutable baselines and protected Pine remain unchanged and unstaged;
19. no repository cache, bytecode, SQLite, journal, temporary, partial, or shard path is newly created.

Static inspection, CSV streaming, gzip streaming, hashing, and read-only SQL/CSV consistency checks are permitted. The recovered `experiment_031r6a3r.py` must not be executed or imported.

## Required outputs

Recover exactly the fifteen paths already listed in `.codex/ALLOWLIST.txt`:

- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/REPORT.md`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/experiment_031r6a3r.py`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_oct_observations.csv.gz`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_oct_volatility_state.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_jan_observations.csv.gz`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_jan_volatility_state.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_episode_control_summary.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_counterexamples.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_reconciliation.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_identity_checks.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_run_hashes.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/helper_provenance.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/memory_summary.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/implementation_audit.csv`;
- `experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/test_results.csv`.

No other repository path may be created or changed.

## Acceptance

The final auditor must inspect the selected commit, the restored worktree blobs, and the substantive package evidence directly.

PASS only when:

- one unique valid source commit was found;
- exactly fifteen allowlisted blobs were recovered byte-identically;
- all mandatory package checks pass;
- no scientific computation was rerun;
- no failed working-tree implementation was used as the source;
- no baseline or out-of-allowlist path changed;
- the worktree changes remain unstaged for the orchestrator;
- the package still supports `BOUNDED_WORKER_REPRESENTATION_READY` as an implementation status only.

On PASS, the orchestrator must create a fresh commit from exactly these fifteen paths and push it to `origin/main`.

EXP-031R6B remains blocked until this publication-recovery task reaches orchestrator `COMPLETED` and the recovered package is visible on `origin/main`.