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
DATA_ROOT=${MSM_MARKET_DATA_ROOT:-/home/nnv/.local/share/msm-market-data}
SOURCE_CODEX_HOME=${MSM_CODEX_HOME:-${CODEX_HOME:-$HOME/.codex}}
read_header_field() {
  local key=$1
  awk -v key="$key" '
    /^## / { exit }
    $0 ~ "^- " key ":" {
      sub("^- " key ":[[:space:]]*", "")
      gsub(/^[`\"]|[`\"]$/, "")
      print
      exit
    }
  ' "$TASK"
}
TASK_KIND=$(read_header_field task_kind | tr '[:lower:]' '[:upper:]')
TASK_KIND=${TASK_KIND:-RESEARCH}
ALLOW_USER_DECISION=$(read_header_field allow_user_decision | tr '[:upper:]' '[:lower:]')
ALLOW_USER_DECISION=${ALLOW_USER_DECISION:-false}
task_key=$(printf '%s' "$TASK" | sha256sum | awk '{print $1}')
RUNTIME="$STATE_ROOT/runtime/$task_key/$ROLE"
RUNTIME_HOME="$RUNTIME/home"; RUNTIME_CACHE="$RUNTIME/cache"; RUNTIME_CONFIG="$RUNTIME/config"
RUNTIME_DATA="$RUNTIME/data"; RUNTIME_STATE="$RUNTIME/state"; RUNTIME_TMP="$RUNTIME/tmp"
RUNTIME_CODEX_HOME="$RUNTIME/codex"
RUNTIME_OUTPUT="$RUNTIME/output/result.json"
AUTH_SOURCE="$SOURCE_CODEX_HOME/auth.json"
[[ -f $AUTH_SOURCE && -r $AUTH_SOURCE ]] || { echo 'Codex credentials are unavailable' >&2; exit 1; }
mkdir -p "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$RUNTIME_CODEX_HOME" "$(dirname "$RUNTIME_OUTPUT")" "$DATA_ROOT"
chmod 700 "$RUNTIME" "$RUNTIME_HOME" "$RUNTIME_CACHE" "$RUNTIME_CONFIG" "$RUNTIME_DATA" "$RUNTIME_STATE" "$RUNTIME_TMP" "$RUNTIME_CODEX_HOME" "$(dirname "$RUNTIME_OUTPUT")" "$DATA_ROOT"
cp -- "$AUTH_SOURCE" "$RUNTIME_CODEX_HOME/auth.json"
chmod 600 "$RUNTIME_CODEX_HOME/auth.json"
if [[ -f $SOURCE_CODEX_HOME/config.toml && -r $SOURCE_CODEX_HOME/config.toml ]]; then
  cp -- "$SOURCE_CODEX_HOME/config.toml" "$RUNTIME_CODEX_HOME/config.toml"
  chmod 600 "$RUNTIME_CODEX_HOME/config.toml"
fi
rm -f "$RUNTIME_OUTPUT"
baseline_context='No captured baseline was supplied.'
if [[ -n $BASELINE ]]; then baseline_context=$(<"$BASELINE"); fi
case "$ROLE" in
  planner)
    role_instruction="Plan the work and inspect feasibility only. The absence of task outputs is expected at this stage and must not trigger correction. Do not modify files. Return PASS when the task is technically actionable; report data or implementation blockers as TECHNICAL_CORRECTION_REQUIRED or FAILED."
    ;;
  implementer)
    role_instruction="Implement the task now. Create every required allowlisted output as substantive work, not placeholders. Use the persistent market-data root when the task requires external datasets. Leave repository changes unstaged and remove cache files."
    ;;
  auditor)
    role_instruction="Audit only the completed task delta relative to the baseline. Verify every required output, deterministic evidence, persistent-data claims, allowlist boundary, and protected paths. If required outputs are absent or invalid, return TECHNICAL_CORRECTION_REQUIRED."
    ;;
  corrector)
    role_instruction="Correct the completed task delta relative to the baseline. Create missing required outputs or replace incomplete files with complete allowlisted outputs. Compare git status with the supplied baseline and remove every task-created path outside the allowlist without touching baseline paths. Use the persistent market-data root when required. Remove cache files and leave repository changes unstaged."
    ;;
esac
if [[ $TASK_KIND == RESEARCH && $ALLOW_USER_DECISION == true ]]; then
  verdict_contract='PASS|TECHNICAL_CORRECTION_REQUIRED|USER_DECISION_REQUIRED|FAILED'
  decision_instruction='USER_DECISION_REQUIRED is allowed only for the explicit decision class named by the task.'
else
  verdict_contract='PASS|TECHNICAL_CORRECTION_REQUIRED|FAILED'
  decision_instruction='USER_DECISION_REQUIRED is forbidden for this task. Missing, ambiguous, conflicting, unavailable, or invalid evidence is a technical outcome and must be TECHNICAL_CORRECTION_REQUIRED or FAILED.'
fi
prompt="You are the MSM $ROLE role. Task kind: $TASK_KIND. Captured non-secret worktree baseline: $baseline_context. $role_instruction $decision_instruction Listed pre-existing paths, including the protected Pine when its SHA256 matches the baseline, are preserved user state and are not task violations. Report any change to a baseline path, protected-Pine staging, or task-created path outside the allowlist. Read task package $TASK and allowlist $ALLOWLIST first; then read task-required evidence, local data, and allowlisted outputs needed to complete or audit the task. Return ONLY JSON: {\"role\":\"$ROLE\",\"verdict\":\"$verdict_contract\",\"findings\":[strings],\"summary\":string}. You do not control state transitions. Do not run git mutation/synchronization commands. Implementer/corrector may modify only allowlisted files and leave changes unstaged."
timeout "$TIMEOUT" bwrap --die-with-parent --ro-bind / / --bind "$REPO" "$REPO" --ro-bind "$REPO/.git" "$REPO/.git" \
  --bind "$DATA_ROOT" "$DATA_ROOT" \
  --bind "$RUNTIME_HOME" "$RUNTIME_HOME" --bind "$RUNTIME_CACHE" "$RUNTIME_CACHE" \
  --bind "$RUNTIME_CONFIG" "$RUNTIME_CONFIG" --bind "$RUNTIME_DATA" "$RUNTIME_DATA" \
  --bind "$RUNTIME_STATE" "$RUNTIME_STATE" --bind "$RUNTIME_TMP" "$RUNTIME_TMP" \
  --bind "$RUNTIME_CODEX_HOME" "$RUNTIME_CODEX_HOME" \
  --bind "$(dirname "$RUNTIME_OUTPUT")" "$(dirname "$RUNTIME_OUTPUT")" \
  --setenv HOME "$RUNTIME_HOME" --setenv XDG_CACHE_HOME "$RUNTIME_CACHE" \
  --setenv XDG_CONFIG_HOME "$RUNTIME_CONFIG" --setenv XDG_DATA_HOME "$RUNTIME_DATA" \
  --setenv XDG_STATE_HOME "$RUNTIME_STATE" --setenv TMPDIR "$RUNTIME_TMP" --setenv CODEX_HOME "$RUNTIME_CODEX_HOME" \
  --setenv MSM_MARKET_DATA_ROOT "$DATA_ROOT" --setenv PYTHONDONTWRITEBYTECODE 1 --setenv PYTHONPYCACHEPREFIX "$RUNTIME_CACHE/pycache" \
  --proc /proc --dev /dev "$CODEX" exec --json -o "$RUNTIME_OUTPUT" --dangerously-bypass-approvals-and-sandbox -C "$REPO" "$prompt" >"$JSONL"
[[ -s $RUNTIME_OUTPUT ]] || { echo 'Codex did not produce a runtime result' >&2; exit 1; }
python3 - "$RUNTIME_OUTPUT" "$ROLE" "$TASK_KIND" "$ALLOW_USER_DECISION" "$REPO" "$BASELINE" "$ALLOWLIST" <<'PY'
import json
import os
import pathlib
import shutil
import subprocess
import sys

path, expected_role, task_kind, allow_user_decision, repo_text, baseline_path, allowlist_path = sys.argv[1:]
repo = pathlib.Path(repo_text).resolve()
with open(path, encoding="utf-8") as source:
    value = json.load(source)
if not isinstance(value, dict) or value.get("role") != expected_role:
    raise SystemExit("invalid worker result")
findings = value.get("findings")
if not isinstance(findings, list):
    findings = []

# Remove every new untracked path outside the allowlist. The baseline proves these
# paths were created by the current task, so deleting them cannot touch user state.
if baseline_path:
    with open(baseline_path, encoding="utf-8") as source:
        baseline = json.load(source)
    baseline_paths = set(baseline.get("preexisting_paths", {}))
    with open(allowlist_path, encoding="utf-8") as source:
        allowed = {
            line.strip()
            for line in source
            if line.strip() and not line.lstrip().startswith("#")
        }
    raw = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        capture_output=True,
    ).stdout
    entries = {}
    records = raw.split(b"\0")
    index = 0
    while index < len(records) - 1:
        row = records[index]
        index += 1
        if len(row) < 4:
            continue
        code = row[:2].decode("ascii", "replace")
        relative = row[3:].decode("utf-8", "surrogateescape")
        if relative:
            entries[relative] = code
    unexpected = sorted(set(entries) - baseline_paths - allowed)
    blocked = []
    for relative in unexpected:
        code = entries[relative]
        candidate = (repo / relative).resolve()
        if repo not in candidate.parents or code != "??":
            blocked.append(f"{code} {relative}")
            continue
        if candidate.is_symlink() or candidate.is_file():
            candidate.unlink(missing_ok=True)
        elif candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink(missing_ok=True)
        parent = candidate.parent
        while parent != repo:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        findings.append("runtime removed task-created path outside allowlist: " + relative)
    if blocked:
        findings.append("non-untracked path outside allowlist remains: " + ", ".join(blocked))
        value["verdict"] = "TECHNICAL_CORRECTION_REQUIRED"
        value["summary"] = (
            str(value.get("summary", ""))
            + " A tracked or staged path outside the allowlist remains and requires technical correction."
        ).strip()

if value.get("verdict") == "USER_DECISION_REQUIRED" and not (
    task_kind == "RESEARCH" and allow_user_decision == "true"
):
    findings.append(
        "runtime normalized USER_DECISION_REQUIRED to TECHNICAL_CORRECTION_REQUIRED because this task forbids user-decision blocking"
    )
    value["verdict"] = "TECHNICAL_CORRECTION_REQUIRED"
    value["summary"] = (
        str(value.get("summary", ""))
        + " This task cannot enter BLOCKED_USER_DECISION."
    ).strip()
value["findings"] = findings
temporary = path + ".normalized"
with open(temporary, "w", encoding="utf-8") as target:
    json.dump(value, target, ensure_ascii=False, sort_keys=True)
    target.write("\n")
os.replace(temporary, path)
PY
mv -f "$RUNTIME_OUTPUT" "$OUTPUT"
