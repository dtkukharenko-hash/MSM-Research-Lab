#!/usr/bin/env bash
set -Eeuo pipefail

REPO=/home/nnv/MSM-Research-Lab
STATE=/home/nnv/.local/state/msm-orchestrator
LOCK=/run/lock/msm-dashboard-publish-r6a3r.lock
PINE=experiments/EXP-009_CAUSAL_MOVE_AGE/EXP-009A_START_VISUAL_REVIEW/artifacts/EXP009A_START_REVIEW.pine
TASK_FILE="$REPO/.codex/TASK.md"
EXPECTED_SUBJECT=EXP-031R6A3R-BOUNDED-WORKER-ACCEPTANCE-CORRECTION
SOURCE_DIR=experiments/EXP-031R6A3R_BOUNDED_WORKER_ACCEPTANCE
TARGET_DIR=experiments/EXP-031R6A3P3_PUBLISHED_BOUNDED_WORKER
REPORT_OUT="$STATE/reports/EXP-031R6A3R-DIRECT-PUBLICATION.md"
FILES=(
  REPORT.md
  experiment_031r6a3r.py
  fixture_oct_observations.csv.gz
  fixture_oct_volatility_state.csv
  fixture_jan_observations.csv.gz
  fixture_jan_volatility_state.csv
  fixture_episode_control_summary.csv
  fixture_counterexamples.csv
  fixture_reconciliation.csv
  fixture_identity_checks.csv
  fixture_run_hashes.csv
  helper_provenance.csv
  memory_summary.csv
  implementation_audit.csv
  test_results.csv
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

source_paths=()
for name in "${FILES[@]}"; do source_paths+=("$SOURCE_DIR/$name"); done
expected_list=$(printf '%s\n' "${source_paths[@]}" | LC_ALL=C sort)
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
  for path in "${source_paths[@]}"; do
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

  report_text=$("${GIT[@]}" show "$sha:$SOURCE_DIR/REPORT.md" 2>/dev/null || true)
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

mkdir -p "$STATE/reports"
chown nnv:nnv "$STATE/reports"
chmod 700 "$STATE/reports"

tmp=$(runuser -u nnv -- mktemp -d "$STATE/publish-r6a3r.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
index="$tmp/index"
report_file="$tmp/REPORT.md"
GITI=(runuser -u nnv -- env GIT_INDEX_FILE="$index" git -C "$REPO")

{
  echo '# EXP-031R6A3P3 published bounded-worker package'
  echo
  echo '- Status: `BOUNDED_WORKER_REPRESENTATION_READY`'
  echo '- Publication task: `INFRA-R6A3R-DIRECT-PUBLICATION-HOLD`'
  echo "- Source candidate commit: \`$selected\`"
  echo "- Source package fingerprint: \`$package_fingerprint\`"
  echo "- Identical valid candidate commits: \`${#valid_candidates[@]}\`"
  echo '- Prior role verdicts: planner PASS; implementer PASS; corrector PASS; final auditor PASS.'
  echo '- Prior terminal failure: Git push only.'
  echo '- Scientific computation rerun: `NO`'
  echo '- Full four-symbol calendar-2025 dataset produced: `NO`'
  echo '- Scientific confirmation, rejection, transfer, ranking, filtering, or predictive claim: `NONE`'
  echo
  echo '## Byte-identical copied evidence'
  echo
  echo '| File | Source SHA-256 | Destination |'
  echo '| --- | --- | --- |'
  for name in "${FILES[@]:1}"; do
    src="$SOURCE_DIR/$name"
    dst="$TARGET_DIR/$name"
    sha256=$("${GIT[@]}" show "$selected:$src" | sha256sum | awk '{print $1}')
    printf '| `%s` | `%s` | `%s` |\n' "$src" "$sha256" "$dst"
  done
} >"$report_file"
chown nnv:nnv "$report_file"
chmod 600 "$report_file"
report_blob=$("${GIT[@]}" hash-object -w "$report_file")

already=1
existing_report=$("${GIT[@]}" show "origin/main:$TARGET_DIR/REPORT.md" 2>/dev/null || true)
grep -q 'BOUNDED_WORKER_REPRESENTATION_READY' <<<"$existing_report" || already=0
for name in "${FILES[@]:1}"; do
  source_blob=$("${GIT[@]}" rev-parse "$selected:$SOURCE_DIR/$name")
  target_blob=$("${GIT[@]}" rev-parse "origin/main:$TARGET_DIR/$name" 2>/dev/null || true)
  [[ "$source_blob" == "$target_blob" ]] || already=0
done

if (( already == 1 )); then
  publication_commit=$origin_before
  result=ALREADY_PUBLISHED
else
  "${GITI[@]}" read-tree "$origin_before"
  "${GITI[@]}" update-index --add --cacheinfo "100644,$report_blob,$TARGET_DIR/REPORT.md"
  for name in "${FILES[@]:1}"; do
    entry=$("${GIT[@]}" ls-tree "$selected" -- "$SOURCE_DIR/$name")
    mode=$(awk '{print $1}' <<<"$entry")
    blob=$(awk '{print $3}' <<<"$entry")
    "${GITI[@]}" update-index --add --cacheinfo "$mode,$blob,$TARGET_DIR/$name"
  done

  tree=$("${GITI[@]}" write-tree)
  parent_tree=$("${GIT[@]}" rev-parse "$origin_before^{tree}")
  [[ "$tree" != "$parent_tree" ]] || { echo 'PUBLICATION_FAILED_EMPTY_TREE_CHANGE'; exit 1; }

  publication_commit=$(printf '%s\n' 'EXP-031R6A3P3 publish accepted bounded-worker package' | "${GIT[@]}" commit-tree "$tree" -p "$origin_before")
  "${GIT[@]}" push origin "$publication_commit:refs/heads/main"
  "${GIT[@]}" fetch origin main
  [[ "$("${GIT[@]}" rev-parse origin/main)" == "$publication_commit" ]] || {
    echo 'PUBLICATION_FAILED_REMOTE_VERIFICATION'
    exit 1
  }
  result=PUBLISHED
fi

for name in "${FILES[@]:1}"; do
  source_blob=$("${GIT[@]}" rev-parse "$selected:$SOURCE_DIR/$name")
  remote_blob=$("${GIT[@]}" rev-parse "origin/main:$TARGET_DIR/$name")
  [[ "$source_blob" == "$remote_blob" ]] || {
    echo "PUBLICATION_FAILED_BLOB_MISMATCH file=$name"
    exit 1
  }
done
remote_report=$("${GIT[@]}" show "origin/main:$TARGET_DIR/REPORT.md")
grep -q 'Status: `BOUNDED_WORKER_REPRESENTATION_READY`' <<<"$remote_report" || {
  echo 'PUBLICATION_FAILED_REPORT_STATUS'
  exit 1
}

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
- Published directory: $TARGET_DIR
- Published paths: ${#FILES[@]}
- Protected Pine SHA-256: $pine_hash_after
- Worktree status preserved: YES
- Scientific computation rerun: NO
- Accepted implementation status: BOUNDED_WORKER_REPRESENTATION_READY
EOF
chown nnv:nnv "$REPORT_OUT"
chmod 600 "$REPORT_OUT"

echo "PUBLICATION_$result source=$selected commit=$publication_commit directory=$TARGET_DIR paths=${#FILES[@]}"
