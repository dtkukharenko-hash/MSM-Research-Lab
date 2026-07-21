#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
LOCK=/run/lock/msm-dashboard-publish-r6a3r.lock
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
TASK_FILE="$REPO/.codex/TASK.md"
EXPECTED_SUBJECT=EXP-031R6A3R-BOUNDED-WORKER-ACCEPTANCE-CORRECTION
REPORT_OUT="$STATE/reports/EXP-031R6A3R-DIRECT-PUBLICATION.md"

EXPECTED_PATHS=(
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/REPORT.md
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/experiment_031r6a3r.py
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_oct_observations.csv.gz
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_oct_volatility_state.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_jan_observations.csv.gz
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_jan_volatility_state.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_episode_control_summary.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_counterexamples.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_reconciliation.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_identity_checks.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/fixture_run_hashes.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/helper_provenance.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/memory_summary.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/implementation_audit.csv
  experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE/test_results.csv
)

exec 9>"$LOCK"
flock -n 9 || { echo 'PUBLICATION_ALREADY_IN_PROGRESS'; exit 1; }

field() {
  local name=$1
  awk -v key="$name" '
    /^## / { exit }
    $0 ~ "^- " key ":" {
      sub("^- " key ":[[:space:]]*", "")
      gsub(/^[`\"]|[`\"]$/, "")
      print
      exit
    }
  ' "$TASK_FILE"
}

[[ -f "$TASK_FILE" ]] || { echo 'TASK_FILE_MISSING'; exit 1; }
[[ "$(field task_id)" == INFRA-R6A3R-DIRECT-PUBLICATION-HOLD ]] || {
  echo 'PUBLICATION_REFUSED_TASK_NOT_HELD'
  exit 1
}
[[ "$(field status)" == HOLD ]] || {
  echo 'PUBLICATION_REFUSED_STATUS_NOT_HOLD'
  exit 1
}

for dir in queue running; do
  if find "$STATE/$dir" -maxdepth 1 -type f -name '*.json' -print -quit 2>/dev/null | grep -q .; then
    echo "PUBLICATION_REFUSED_ACTIVE_TASK directory=$dir"
    exit 1
  fi
done

systemctl stop msm-task-feeder.service msm-orchestrator.service >/dev/null 2>&1 || true

GIT=(runuser -u nnv -- git -C "$REPO")
branch=$("${GIT[@]}" branch --show-current)
[[ "$branch" == main ]] || { echo "PUBLICATION_REFUSED_BRANCH branch=$branch"; exit 1; }

if ! "${GIT[@]}" diff --cached --quiet; then
  echo 'PUBLICATION_REFUSED_STAGED_CHANGES'
  exit 1
fi

pine_path="$REPO/$PINE"
[[ -f "$pine_path" ]] || { echo 'PUBLICATION_REFUSED_PROTECTED_PINE_MISSING'; exit 1; }
pine_hash_before=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_before=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")
status_before=$("${GIT[@]}" status --porcelain=v1 -z --untracked-files=all | sha256sum | awk '{print $1}')

"${GIT[@]}" fetch origin main
origin_before=$("${GIT[@]}" rev-parse origin/main)

expected_list=$(printf '%s\n' "${EXPECTED_PATHS[@]}" | LC_ALL=C sort)
mapfile -t candidate_rows < <("${GIT[@]}" log --all --reflog --format='%H%x09%s' 2>/dev/null | awk -F '\t' -v s="$EXPECTED_SUBJECT" '$2 == s {print $1}' | awk '!seen[$0]++')

valid_candidates=()
package_fingerprint=''
selected=''
for sha in "${candidate_rows[@]}"; do
  [[ -n "$sha" ]] || continue
  "${GIT[@]}" cat-file -e "$sha^{commit}" 2>/dev/null || continue
  parent=$("${GIT[@]}" rev-parse "$sha^" 2>/dev/null || true)
  [[ -n "$parent" ]] || continue
  actual_list=$("${GIT[@]}" diff-tree --no-commit-id --name-only -r "$parent" "$sha" | LC_ALL=C sort)
  [[ "$actual_list" == "$expected_list" ]] || continue

  rows=''
  valid=1
  for path in "${EXPECTED_PATHS[@]}"; do
    entry=$("${GIT[@]}" ls-tree "$sha" -- "$path")
    mode=$(awk '{print $1}' <<<"$entry")
    type=$(awk '{print $2}' <<<"$entry")
    blob=$(awk '{print $3}' <<<"$entry")
    if [[ "$type" != blob || "$mode" != 100644 || -z "$blob" ]]; then
      valid=0
      break
    fi
    rows+="$path $mode $blob"$'\n'
  done
  (( valid == 1 )) || continue

  report_text=$("${GIT[@]}" show "$sha:${EXPECTED_PATHS[0]}" 2>/dev/null || true)
  grep -Eq '(^|[^A-Z_])BOUNDED_WORKER_REPRESENTATION_READY([^A-Z_]|$)' <<<"$report_text" || continue

  fingerprint=$(printf '%s' "$rows" | sha256sum | awk '{print $1}')
  if [[ -z "$package_fingerprint" ]]; then
    package_fingerprint=$fingerprint
    selected=$sha
  elif [[ "$fingerprint" != "$package_fingerprint" ]]; then
    echo "PUBLICATION_REFUSED_AMBIGUOUS_CANDIDATES first=$selected other=$sha"
    exit 1
  fi
  valid_candidates+=("$sha")
done

[[ -n "$selected" ]] || {
  echo 'PUBLICATION_FAILED_NO_VALID_R6A3R_COMMIT'
  exit 1
}

already=1
for path in "${EXPECTED_PATHS[@]}"; do
  source_blob=$("${GIT[@]}" rev-parse "$selected:$path")
  target_blob=$("${GIT[@]}" rev-parse "origin/main:$path" 2>/dev/null || true)
  if [[ "$source_blob" != "$target_blob" ]]; then
    already=0
    break
  fi
done

mkdir -p "$STATE/reports"
chown nnv:nnv "$STATE/reports"
chmod 700 "$STATE/reports"

if (( already == 1 )); then
  publication_commit=$origin_before
  result=ALREADY_PUBLISHED
else
  tmp=$(runuser -u nnv -- mktemp -d "$STATE/publish-r6a3r.XXXXXX")
  trap 'rm -rf "$tmp"' EXIT
  index="$tmp/index"
  GITI=(runuser -u nnv -- env GIT_INDEX_FILE="$index" git -C "$REPO")
  "${GITI[@]}" read-tree "$origin_before"

  for path in "${EXPECTED_PATHS[@]}"; do
    entry=$("${GIT[@]}" ls-tree "$selected" -- "$path")
    mode=$(awk '{print $1}' <<<"$entry")
    blob=$(awk '{print $3}' <<<"$entry")
    "${GITI[@]}" update-index --add --cacheinfo "$mode,$blob,$path"
  done

  tree=$("${GITI[@]}" write-tree)
  parent_tree=$("${GIT[@]}" rev-parse "$origin_before^{tree}")
  [[ "$tree" != "$parent_tree" ]] || {
    echo 'PUBLICATION_FAILED_EMPTY_TREE_CHANGE'
    exit 1
  }

  publication_commit=$(printf '%s\n' 'EXP-031R6A3R publish accepted bounded-worker package' | "${GIT[@]}" commit-tree "$tree" -p "$origin_before")
  "${GIT[@]}" push origin "$publication_commit:refs/heads/main"
  "${GIT[@]}" fetch origin main
  [[ "$("${GIT[@]}" rev-parse origin/main)" == "$publication_commit" ]] || {
    echo 'PUBLICATION_FAILED_REMOTE_VERIFICATION'
    exit 1
  }
  result=PUBLISHED
fi

pine_hash_after=$(sha256sum "$pine_path" | awk '{print $1}')
pine_status_after=$("${GIT[@]}" status --porcelain=v1 -- "$PINE")
status_after=$("${GIT[@]}" status --porcelain=v1 -z --untracked-files=all | sha256sum | awk '{print $1}')
[[ "$pine_hash_after" == "$pine_hash_before" ]] || { echo 'PUBLICATION_ABORT_PROTECTED_PINE_HASH_CHANGED'; exit 1; }
[[ "$pine_status_after" == "$pine_status_before" ]] || { echo 'PUBLICATION_ABORT_PROTECTED_PINE_STATUS_CHANGED'; exit 1; }
[[ "$status_after" == "$status_before" ]] || { echo 'PUBLICATION_ABORT_WORKTREE_STATUS_CHANGED'; exit 1; }
"${GIT[@]}" diff --cached --quiet || { echo 'PUBLICATION_ABORT_STAGED_CHANGES_CREATED'; exit 1; }

cat >"$REPORT_OUT" <<EOF
# EXP-031R6A3R direct publication

- Status: $result
- Source candidate: $selected
- Candidate count with identical package: ${#valid_candidates[@]}
- Package fingerprint: $package_fingerprint
- Origin before: $origin_before
- Publication commit: $publication_commit
- Origin after: $("${GIT[@]}" rev-parse origin/main)
- Published paths: ${#EXPECTED_PATHS[@]}
- Protected Pine SHA-256: $pine_hash_after
- Worktree status preserved: YES
- Scientific computation rerun: NO
- Accepted implementation status: BOUNDED_WORKER_REPRESENTATION_READY
EOF
chown nnv:nnv "$REPORT_OUT"
chmod 600 "$REPORT_OUT"

echo "PUBLICATION_$result source=$selected commit=$publication_commit paths=${#EXPECTED_PATHS[@]}"
