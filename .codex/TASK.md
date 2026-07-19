# Current Codex Task

- task_id: `EXP-028-TRANSFER-FAILURE-LOCALIZATION`
- status: `READY`
- published_at: `2026-07-19`
- target_branch: `main`
- infrastructure_maintenance: `false`
- source_experiment: `EXP-027-MULTI-MARKET-DERIVATIVES-TRANSFER`
- commit_message: `EXP-028 transfer failure localization`

## Objective

Localise why EXP-027 reached `MULTI_MARKET_DERIVATIVES_TRANSFER_PARTIAL` without changing any event threshold, history window, episode rule, control rule, OHLC window, parent representation, market panel or target period.

Test three predeclared explanations separately:

1. mixing distinct derivatives-event families hides otherwise stable structure;
2. mixing event sides hides otherwise stable structure;
3. event-state distinctions depend on a causally known volatility regime.

This is a diagnostic causal decomposition, not a search for a favourable cell. Do not tune thresholds, rank outcomes, select markets, or introduce trading language.

## Frozen inputs

Use exactly the validated EXP-027 panel and period:

- `BTCUSDT`
- `ETHUSDT`
- `SOLUSDT`
- `XRPUSDT`
- `2023-07-01T00:00:00Z` through `2024-12-31T23:00:00Z`

Reuse validated local funding, OI and 15m OHLC archives from EXP-027. Do not redownload unless an archive fails its recorded hash/schema validation. Do not modify EXP-026 or EXP-027 outputs.

Reuse unchanged:

- funding extremes at causal 5th/95th percentiles using preceding 90 calendar days and at least 90 prior settlements;
- OI robust score using preceding 30 calendar days, at least 1,000 prior changes and positive MAD;
- OI thresholds `z_mad >= 4.0` and `z_mad <= -4.0`;
- backward 60-minute joint-event rule;
- both 8H and 24H episode views;
- matched-control rules from EXP-027;
- 15m and deterministic UTC 1H state descriptions;
- windows 4, 8 and 32;
- representations `FIXED_8`, `DIRECTION_RUN`, `ATR_ORIGIN`, `CONFIRMED_DIRECTION_CHANGE`, `HYBRID_ORIGIN`.

No future bars, pivots, outcomes or labels are allowed.

## Frozen diagnostic partitions

Every diagnostic must be reported without selecting a winner.

### A. Event-family partition

Evaluate separately:

- `FUNDING_EXTREME`
- `OI_SHOCK`
- `JOINT_EVENT`

Do not pool these families in the primary family analysis.

### B. Side partition

Preserve exact independent sides:

- funding: `LOW`, `HIGH`;
- OI: `EXPANSION`, `CONTRACTION`;
- joint events: the full ordered pair of funding side and OI side.

Do not map sides into bullish/bearish or otherwise force directional equivalence.

### C. Causal volatility regimes

At each event and control timestamp, classify volatility using only complete 1H bars ending no later than that timestamp.

Compute trailing 1H ATR(14) divided by close. Compare the current value with the empirical distribution of the preceding 90 calendar days, excluding the current bar.

Use frozen regimes:

- `LOW_VOL`: percentile `<= 0.25`;
- `MID_VOL`: percentile `> 0.25` and `< 0.75`;
- `HIGH_VOL`: percentile `>= 0.75`.

Require at least 1,000 prior valid 1H observations; otherwise mark `INSUFFICIENT_VOL_HISTORY`. No alternate volatility measure or threshold is permitted.

Controls must match the event volatility regime exactly in addition to every EXP-027 matching field. Preserve unmatched strata explicitly.

## Diagnostic analysis

For every event-family/side/volatility-regime/representation/state-field cell, and separately for 8H and 24H episodes, report:

- support by symbol, month and chronological third;
- matched-control support and unmatched rate;
- representation validity and history exclusions;
- symbol-level event-control contrast sign and magnitude;
- equal-symbol pooled contrast;
- sign consistency across symbols;
- leave-one-symbol-out stability;
- concentration by symbol and time third;
- whether conditioning on family, side or volatility reduces contradiction relative to the corresponding unconditioned EXP-027 cell;
- whether any apparent improvement is caused by support loss, unmatched controls or invalid representation filtering.

Use deterministic distribution-distance and rank metrics already used in EXP-027. Do not add new metrics because they produce larger separation.

## Predeclared localisation criteria

A factor may be called an explanatory source of partial transfer only when all are true:

1. the conditioned cell has sufficient matched support on at least three symbols;
2. at least three symbols share the same contrast sign;
3. the sign survives every feasible leave-one-symbol-out calculation;
4. the sign agrees in both 8H and 24H views;
5. no symbol contributes more than 50% of equal-symbol pooled absolute contrast;
6. history, validity and unmatched-control exclusions together remove no more than 50% of independent episodes in supporting symbols;
7. the corresponding unconditioned EXP-027 cell fails at least one of criteria 2–5;
8. the improvement is present in at least two chronological thirds, not only one concentrated interval.

Do not relax these criteria and do not combine weak factors post hoc.

## Decision

Select exactly one verdict:

- `TRANSFER_FAILURE_LOCALIZED_FAMILY` — event-family separation explains the partial transfer under all frozen localisation criteria;
- `TRANSFER_FAILURE_LOCALIZED_SIDE` — side separation explains it;
- `TRANSFER_FAILURE_LOCALIZED_VOLATILITY` — causal volatility conditioning explains it;
- `TRANSFER_FAILURE_LOCALIZED_MULTIPLE` — at least two factors independently satisfy all criteria, without requiring a post-hoc combined filter;
- `TRANSFER_FAILURE_NOT_LOCALIZED` — none of the three factors satisfies the frozen criteria;
- `TRANSFER_FAILURE_DATA_FAILED` — validated inputs cannot support an honest diagnostic.

Do not force localisation.

## Required outputs

Create exactly these nine files:

- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/REPORT.md`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/input_validation.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/diagnostic_membership.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/volatility_regimes.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/matched_controls.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/diagnostic_summary.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/localization_tests.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/counterexamples.csv`
- `experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/experiment_028.py`

Do not commit raw archives or create cache files.

## Validation

Before PASS:

1. Reproduce and verify EXP-027 archive hashes, schemas, coverage and exact symbol panel.
2. Verify event ids and 8H/24H episode memberships correspond exactly to frozen EXP-027 definitions.
3. Assert volatility regimes use only prior complete 1H observations and exclude the current bar.
4. Assert no event threshold, history window, representation or state field differs from EXP-027.
5. Verify every diagnostic partition is exhaustive and mutually exclusive where applicable.
6. Verify controls preserve all EXP-027 matches plus exact volatility regime, remain source-excluded and deterministic.
7. Verify localisation criteria directly from `localization_tests.csv`.
8. Preserve insufficient history, invalid representation and unmatched-control cases explicitly.
9. Run twice and require identical SHA-256 hashes for all nine outputs.
10. Parse every CSV and reproduce REPORT values and verdict.
11. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile experiments/EXP-028_TRANSFER_FAILURE_LOCALIZATION/experiment_028.py`, remove cache artifacts and run `git diff --check`.
12. Perform baseline-relative allowlist validation and verify protected/pre-existing dirty files remain byte-identical and unstaged.

## Hard protections

Never modify, stage, delete, rename, chmod or rewrite `.codex/TASK.md`, `.codex/ALLOWLIST.txt`, `.codex/RESULT.md`, `docs/DEFINITIONS.md`, `start.sh`, `.git` internals, any EXP-009 file, or any EXP-013 through EXP-027 file.

The protected dirty file `experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine` must remain byte-identical and unstaged.

Only the nine EXP-028 outputs may change inside the repository. Non-repository writes are limited to temporary deterministic files under `${HOME}/.local/share/msm-market-data/`.

## Result contract

Planner, implementer, auditor and corrector use the required JSON role contract. The implementer leaves only the nine allowlisted EXP-028 outputs unstaged. The orchestrator performs the final baseline-relative allowlist check, commits once with the declared commit message and pushes to `main`.