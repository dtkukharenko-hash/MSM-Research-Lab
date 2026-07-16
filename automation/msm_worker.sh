#!/usr/bin/env bash
# Narrow worker boundary: the model emits a schema-checked decision, never a transition.
set -Eeuo pipefail
ROLE= TASK= ALLOWLIST= OUTPUT= MOCK=
while (($#)); do case $1 in --role) ROLE=$2;shift 2;;--task)TASK=$2;shift 2;;--allowlist)ALLOWLIST=$2;shift 2;;--output)OUTPUT=$2;shift 2;;--mock-response)MOCK=$2;shift 2;;*) echo "usage error" >&2;exit 2;;esac;done
[[ $ROLE =~ ^(planner|implementer|auditor|corrector)$ && -f $TASK && -f $ALLOWLIST && -n $OUTPUT ]] || exit 2
mkdir -p "$(dirname "$OUTPUT")"; umask 077
if [[ -n $MOCK ]]; then printf '%s\n' "$MOCK" >"$OUTPUT"; exit 0; fi
CODEX=${MSM_CODEX:-/home/nnv/.local/bin/codex}; REPO=${MSM_REPO:-/home/nnv/MSM-Research-Lab}; TIMEOUT=${MSM_ROLE_TIMEOUT:-3600}; JSONL="${OUTPUT%.json}.jsonl"
prompt="You are the MSM $ROLE role. Read only task package $TASK and allowlist $ALLOWLIST. Return ONLY JSON: {\"role\":\"$ROLE\",\"verdict\":\"PASS|TECHNICAL_CORRECTION_REQUIRED|USER_DECISION_REQUIRED|FAILED\",\"findings\":[strings],\"summary\":string}. You do not control state transitions. Do not run git mutation/synchronization commands. Implementer/corrector may modify only allowlisted files and leave changes unstaged."
timeout "$TIMEOUT" bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" --proc /proc --dev /dev "$CODEX" exec --json -o "$OUTPUT" -s workspace-write -C "$REPO" "$prompt" >"$JSONL"
