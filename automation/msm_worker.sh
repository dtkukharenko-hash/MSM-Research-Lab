#!/usr/bin/env bash
# Narrow worker boundary: the model emits a schema-checked decision, never a transition.
set -Eeuo pipefail
ROLE= TASK= ALLOWLIST= OUTPUT= BASELINE= MOCK=
while (($#)); do case $1 in --role) ROLE=$2;shift 2;;--task)TASK=$2;shift 2;;--allowlist)ALLOWLIST=$2;shift 2;;--output)OUTPUT=$2;shift 2;;--baseline-json)BASELINE=$2;shift 2;;--mock-response)MOCK=$2;shift 2;;*) echo "usage error" >&2;exit 2;;esac;done
[[ $ROLE =~ ^(planner|implementer|auditor|corrector)$ && -f $TASK && -f $ALLOWLIST && -n $OUTPUT && ( -z $BASELINE || -f $BASELINE ) ]] || exit 2
mkdir -p "$(dirname "$OUTPUT")"; umask 077
if [[ -n $MOCK ]]; then printf '%s\n' "$MOCK" >"$OUTPUT"; exit 0; fi
CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}; REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; TIMEOUT=${MSM_ROLE_TIMEOUT:-3600}; JSONL="${OUTPUT%.json}.jsonl"
STATE_ROOT=${MSM_STATE_DIR:-/home/nnv/.local/state/msm-orchestrator}
SOURCE_CODEX_HOME=${MSM_CODEX_HOME:-${CODEX_HOME:-$HOME/.codex}}
task_key=$(printf '%s' "$TASK" | sha256sum | awk '{print $1}')
RUNTIME="$STATE_ROOT/runtime/$task_key/$ROLE"
RUNTIME_HOME="$RUNTIME/home"; RUNTIME_CACHE="$RUNTIME/cache"; RUNTIME_CONFIG="$RUNTIME/config"
RUNTIME_DATA="$RUNTIME/data"; RUNTIME_STATE="$RUNTIME/state"; RUNTIME_TMP="$RUNTIME/tmp"
RUNTIME_CODEX_HOME="$RUNTIME/codex"
RUNTIME_OUTPUT="$RUNTIME/output/result.json"
AUTH_SOURCE="$SOURCE_CODEX_HOME/auth.json"
[[ -f $AUTH_SOURCE && -r $AUTH_SOURCE ]] || { echo 'Codex credentials are unavailable' >&2; exit 1; }
mkdir -p "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$RUNTIME_CODEX_HOME" "$(dirname "$RUNTIME_OUTPUT")"
chmod 700 "$RUNTIME" "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$RUNTIME_CODEX_HOME" "$(dirname "$RUNTIME_OUTPUT")"
cp -- "$AUTH_SOURCE" "$RUNTIME_CODEX_HOME/auth.json"
chmod 600 "$RUNTIME_CODEX_HOME/auth.json"
if [[ -f $SOURCE_CODEX_HOME/config.toml && -r $SOURCE_CODEX_HOME/config.toml ]]; then
  cp -- "$SOURCE_CODEX_HOME/config.toml" "$RUNTIME_CODEX_HOME/config.toml"
  chmod 600 "$RUNTIME_CODEX_HOME/config.toml"
fi
rm -f "$RUNTIME_OUTPUT"
baseline_context='No captured baseline was supplied.'
if [[ -n $BASELINE ]]; then baseline_context=$(<"$BASELINE"); fi
role_instruction="Evaluate only the task delta relative to that baseline."
if [[ $ROLE == auditor ]]; then
  role_instruction="Evaluate only the task delta relative to that baseline. If no task-created allowlisted paths exist for a task with required outputs, return TECHNICAL_CORRECTION_REQUIRED, not PASS."
elif [[ $ROLE == corrector ]]; then
  role_instruction="Correct the task delta relative to that baseline. If no task-created allowlisted paths exist, create every required allowlisted output from the task package. Outputs must be substantive task implementations, not placeholders or scaffolds. If prior correction created incomplete files, replace them with complete allowlisted outputs that satisfy the task validation. Leave the files unstaged."
fi
prompt="You are the MSM $ROLE role. Captured non-secret worktree baseline: $baseline_context. $role_instruction Listed pre-existing paths, including the protected Pine when its SHA256 matches the baseline, are preserved user state and are not task violations. Report any change to a baseline path, protected-Pine staging, or task-created path outside the allowlist. Read task package $TASK and allowlist $ALLOWLIST first; then read task-required evidence, local data, and allowlisted outputs needed to complete or audit the task. Return ONLY JSON: {\"role\":\"$ROLE\",\"verdict\":\"PASS|TECHNICAL_CORRECTION_REQUIRED|USER_DECISION_REQUIRED|FAILED\",\"findings\":[strings],\"summary\":string}. You do not control state transitions. Do not run git mutation/synchronization commands. Implementer/corrector may modify only allowlisted files and leave changes unstaged."
timeout "$TIMEOUT" bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" \
  --bind "$RUNTIME_HOME" "$RUNTIME_HOME" --bind "$RUNTIME_CACHE" "$RUNTIME_CACHE" \
  --bind "$RUNTIME_CONFIG" "$RUNTIME_CONFIG" --bind "$RUNTIME_DATA" "$RUNTIME_DATA" \
  --bind "$RUNTIME_STATE" "$RUNTIME_STATE" --bind "$RUNTIME_TMP" "$RUNTIME_TMP" \
  --bind "$RUNTIME_CODEX_HOME" "$RUNTIME_CODEX_HOME" \
  --bind "$(dirname "$RUNTIME_OUTPUT")" "$(dirname "$RUNTIME_OUTPUT")" \
  --setenv HOME "$RUNTIME_HOME" --setenv XDG_CACHE_HOME "$RUNTIME_CACHE" \
  --setenv XDG_CONFIG_HOME "$RUNTIME_CONFIG" --setenv XDG_DATA_HOME "$RUNTIME_DATA" \
  --setenv XDG_STATE_HOME "$RUNTIME_STATE" --setenv TMPDIR "$RUNTIME_TMP" --setenv CODEX_HOME "$RUNTIME_CODEX_HOME" \
  --setenv PYTHONDONTWRITEBYTECODE 1 \
  --proc /proc --dev /dev "$CODEX" exec --json -o "$RUNTIME_OUTPUT" --dangerously-bypass-approvals-and-sandbox -C "$REPO" "$prompt" >"$JSONL"
[[ -s $RUNTIME_OUTPUT ]] || { echo 'Codex did not produce a runtime result' >&2; exit 1; }
mv -f "$RUNTIME_OUTPUT" "$OUTPUT"
