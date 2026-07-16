# AUTOMATION-008 Result

- task_id: `AUTOMATION-008-PREEXISTING-DIRTY-BASELINE`
- status: `IMPLEMENTED_AWAITING_MANUAL_COMMIT`
- implementation_commit_sha: `UNCOMMITTED_BY_TASK_REQUIREMENT`
- push_status: `NOT_ATTEMPTED_BY_TASK_REQUIREMENT`

## Summary

The orchestrator now captures a non-secret baseline before role execution: the
protected Pine SHA256 plus signatures for all pre-existing modified or
untracked paths. It validates every task delta against that baseline before
and after each role, supplies the baseline to every worker role, and stages
only newly created allowlisted task paths at completion. A pre-existing dirty
Pine is therefore preserved rather than treated as a task violation.

Technical correction verdicts now use correction R1 and R2 while attempts
remain; only user-decision verdicts enter `BLOCKED_USER_DECISION` directly.

## Validation

- `bash -n automation/msm_worker.sh automation/verify_orchestrator.sh`: PASS
- Python compile validation for `automation/msm_orchestrator.py`: PASS
- `bash automation/verify_orchestrator.sh --worker-fixture`: PASS
- `bash automation/verify_orchestrator.sh --mock-cycle --wait 0`: PASS
  - SMOKE-005 preserved a pre-existing dirty protected Pine while accepting
    one allowlisted task-created file.
  - Post-baseline protected-Pine byte changes and staging were rejected.
  - A post-baseline non-allowlisted path was rejected.
  - Technical corrections reached R1 then R2; user-decision verdicts blocked
    immediately.
- Live read-only baseline capture and verification: PASS
  - protected Pine SHA256: `0889efa1f8fa8420962160cbc602b5f6f0836763aab6d34534245ea3dad0223f`
  - protected Pine staged: `no`
- `git diff --check`: PASS

## Changed files

- `automation/msm_orchestrator.py`
- `automation/msm_worker.sh`
- `automation/verify_orchestrator.sh`
- `automation/AUTOMATION-008-RESULT.md`

## Warnings

- Changes are intentionally unstaged and uncommitted.
- The pre-existing protected Pine modification remains byte-identical and
  unstaged.
