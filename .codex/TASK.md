# Current Codex Task

- task_id: `INFRA-EXP034A-ARCHIVE-HOLD`
- status: `HOLD`
- target_branch: `main`
- infrastructure_maintenance: `true`
- task_kind: `INFRASTRUCTURE`
- allow_user_decision: `false`
- manual_start_required: `true`
- data_ready: `false`
- commit_message: `Archive failed EXP-034A conformance attempt`

## Status

EXP-034A ended `FAILED_TECHNICAL` at attempt zero. It produced an honest `ENGINE_READY=NO` scaffold but did not implement the complete required API and test suite. Its paths are retained as failed technical evidence and must remain byte-for-byte unchanged.

The next work is split into two smaller conformance packages: first the causal state core, then the evaluation/null engine.
