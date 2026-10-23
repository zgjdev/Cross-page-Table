#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
run_id="${1:?usage: run_dotsocr_full_val_offline_background.sh RUN_ID}"
log_dir="logs/cross-page-scores/$run_id"
adapter="artifacts/cross-page-adapters/$run_id-no-merge"
no_merge="artifacts/cross-page-scores/$run_id-no-merge"
merge="artifacts/cross-page-merges/$run_id-simple-merge"
simple_score="artifacts/cross-page-scores/$run_id-simple-merge"
manifest="artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl"
gold="artifacts/cross-page-manifests/20260929T093449Z-cross-page-val-audit/gold-cross-page.jsonl"
truth="data/pubtables-v2/extracted/Full Documents/val/tables"
images="data/pubtables-v2/extracted/Full Documents/val/images"
python=".venvs/eval312/bin/python"
export PYTHONPATH=src:third_party/grits-main

[[ -d "$log_dir" && -f "$adapter/summary.json" ]] || { echo 'missing audited adapter/log directory' >&2; exit 2; }
for output in "$no_merge" "$merge" "$simple_score"; do
  [[ ! -e "$output" ]] || { echo "output already exists: $output" >&2; exit 2; }
done

echo "START $(date -u +%Y-%m-%dT%H:%M:%SZ) run_id=$run_id pid=$$"
on_exit() {
  status=$?
  echo "END $(date -u +%Y-%m-%dT%H:%M:%SZ) status=$status run_id=$run_id"
}
trap on_exit EXIT

echo 'STEP no_merge score'
"$python" scripts/score_cross_page_predictions.py \
  --manifest "$manifest" --page-results "$adapter/page-results.jsonl" \
  --document-tables "$adapter/document-tables.jsonl" --truth-dir "$truth" \
  --cross-page-gold "$gold" --output-dir "$no_merge" \
  > "$log_dir/background-no-merge-score.log" 2>&1

echo 'STEP repeated_header merge'
"$python" scripts/merge_dotsocr_repeated_header.py \
  --manifest "$manifest" --adapter-dir "$adapter" --images "$images" \
  --output-dir "$merge" > "$log_dir/background-simple-merge.log" 2>&1

echo 'STEP simple_merge score'
"$python" scripts/score_cross_page_predictions.py \
  --manifest "$manifest" --page-results "$adapter/page-results.jsonl" \
  --document-tables "$merge/document-tables.jsonl" --truth-dir "$truth" \
  --cross-page-gold "$gold" --output-dir "$simple_score" \
  > "$log_dir/background-simple-merge-score.log" 2>&1

sha256sum "$no_merge/metrics.json" "$no_merge/matches.jsonl" "$no_merge/failures.jsonl" \
  "$merge/summary.json" "$simple_score/metrics.json" "$simple_score/matches.jsonl" \
  "$simple_score/failures.jsonl" > "$log_dir/background-checksums.sha256"
echo 'STEP all finished'
