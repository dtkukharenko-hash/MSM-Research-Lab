# Current Codex Task

- task_id: `EXP-034A1-TEMPORAL-STATE-CORE-CONFORMANCE-HOLD`
- status: `HOLD`
- target_branch: `main`
- infrastructure_maintenance: `false`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `Archive failed EXP-034A1 temporal state core conformance`

## Terminal result

EXP-034A1 ended `FAILED_TECHNICAL` and was not accepted. It produced no reusable or accepted engine component.

The principal defects were:

1. the synthetic expected states did not cover EMERGING, DEVELOPING, CORRECTION, or TERMINATING;
2. confirmed opposite direction bypassed TERMINATING;
3. expected outputs were derived by the implementation under test;
4. test-result evidence contained blanket PASS assertions;
5. EMA27 was not exposed or independently verified;
6. prefix-invariance evidence did not test appended-row independence;
7. invalid fixture variants were missing;
8. protocol/API documentation and paired-run evidence were incomplete.

All EXP-034A1 files are failed technical evidence only. Preserve them byte-for-byte and do not reuse their code, fixtures, expectations, or verdicts.
