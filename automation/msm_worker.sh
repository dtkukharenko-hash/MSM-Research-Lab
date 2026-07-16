#!/usr/bin/env bash
# Narrow worker boundary: the model emits a schema-checked decision, never a transition.
set -Eeuo pipefail
ROLE= TASK= ALLOWLIST= OUTPUT= MOCK=
while (($#)); do case $1 in --role) ROLE=$2;shift 2;;--task)TASK=$2;shift 2;;--allowlist)ALLOWLIST=$2;shift 2;;--output)OUTPUT=$2;shift 2;;--mock-response)MOCK=$2;shift 2;;*) echo "usage error" >&2;exit 2;;esac;done
[[ $ROLE =~ ^(planner|implementer|auditor|corrector)$ && -f $TASK && -f $ALLOWLIST && -n $OUTPUT ]] || exit 2
mkdir -p "$(dirname "$OUTPUT")"; umask 077
if [[ -n $MOCK ]]; then printf '%s\n' "$MOCK" >"$OUTPUT"; exit 0; fi
CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}; REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; TIMEOUT=${MSM_ROLE_TIMEOUT:-3600}; JSONL="${OUTPUT%.json}.jsonl"
STATE_ROOT=${MSM_STATE_DIR:-/home/nnv/.local/state/msm-orchestrator}
task_key=$(printf '%s' "$TASK" | sha256sum | awk '{print $1}')
RUNTIME="$STATE_ROOT/runtime/$task_key/$ROLE"
RUNTIME_HOME="$RUNTIME/home"; RUNTIME_CACHE="$RUNTIME/cache"; RUNTIME_CONFIG="$RUNTIME/config"
RUNTIME_DATA="$RUNTIME/data"; RUNTIME_STATE="$RUNTIME/state"; RUNTIME_TMP="$RUNTIME/tmp"
RUNTIME_OUTPUT="$RUNTIME/output/result.json"
mkdir -p "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$(dirname "$RUNTIME_OUTPUT")"
chmod 700 "$RUNTIME" "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$(dirname "$RUNTIME_OUTPUT")"
rm -f "$RUNTIME_OUTPUT"
prompt="You are the MSM $ROLE role. Read only task package $TASK and allowlist $ALLOWLIST. Return ONLY JSON: {\"role\":\"$ROLE\",\"verdict\":\"PASS|TECHNICAL_CORRECTION_REQUIRED|USER_DECISION_REQUIRED|FAILED\",\"findings\":[strings],\"summary\":string}. You do not control state transitions. Do not run git mutation/synchronization commands. Implementer/corrector may modify only allowlisted files and leave changes unstaged."
timeout "$TIMEOUT" bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" \
  --bind "$RUNTIME_HOME" "$RUNTIME_HOME" --bind "$RUNTIME_CACHE" "$RUNTIME_CACHE" \
  --bind "$RUNTIME_CONFIG" "$RUNTIME_CONFIG" --bind "$RUNTIME_DATA" "$RUNTIME_DATA" \
  --bind "$RUNTIME_STATE" "$RUNTIME_STATE" --bind "$RUNTIME_TMP" "$RUNTIME_TMP" \
  --bind "$(dirname "$RUNTIME_OUTPUT")" "$(dirname "$RUNTIME_OUTPUT")" \
  --setenv HOME "$RUNTIME_HOME" --setenv XDG_CACHE_HOME "$RUNTIME_CACHE" \
  --setenv XDG_CONFIG_HOME "$RUNTIME_CONFIG" --setenv XDG_DATA_HOME "$RUNTIME_DATA" \
  --setenv XDG_STATE_HOME "$RUNTIME_STATE" --setenv TMPDIR "$RUNTIME_TMP" \
  --proc /proc --dev /dev "$CODEX" exec --json -o "$RUNTIME_OUTPUT" -s workspace-write -C "$REPO" "$prompt" >"$JSONL"
[[ -s $RUNTIME_OUTPUT ]] || { echo 'Codex did not produce a runtime result' >&2; exit 1; }
mv -f "$RUNTIME_OUTPUT" "$OUTPUT"
