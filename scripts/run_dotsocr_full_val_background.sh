#!/usr/bin/env bash
# Keep the fixed full-validation inference observable without modifying the dataset.
set -u
set -o pipefail

cd "$(dirname "$0")/.." || exit 1
RUN_ID="${1:?usage: bash scripts/run_dotsocr_full_val_background.sh RUN_ID [--resume-from OLD_PREDICTIONS ...] [--preflight]}"
if [[ ! "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-dots-full-val$ ]]; then
  printf 'Invalid run ID: %s\n' "$RUN_ID" >&2
  exit 2
fi

MANIFEST=artifacts/input-manifests/20260921T071841Z-smoke-input-manifests/dots-full-documents-val-full.jsonl
EXPECTED_SHA=2782f9ed14bda9858907ae3e6fe43b399c95d6907c64c0b4004b997a9c6e54cd
OUT="outputs/baselines/dots-ocr/$RUN_ID"
LOG="logs/baselines/dots-ocr/$RUN_ID"
PRED="$OUT/predictions.jsonl"
RESUME_FILES=()
PREFLIGHT=0
shift
while test "$#" -gt 0; do
  case "$1" in
    --resume-from)
      shift
      while test "$#" -gt 0 && [[ "$1" != --* ]]; do
        RESUME_FILES+=("$1")
        shift
      done
      test "${#RESUME_FILES[@]}" -ge 1 || exit 2
      ;;
    --preflight)
      test "$PREFLIGHT" -eq 0 || exit 2
      PREFLIGHT=1
      shift
      ;;
    *) printf 'Unexpected argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
EXPECTED_RESUME_FILES=(
  outputs/baselines/dots-ocr/20261006T172527Z-dots-full-val/predictions.jsonl
  outputs/baselines/dots-ocr/20261010T024700Z-dots-full-val/predictions.jsonl
  outputs/baselines/dots-ocr/20261017T081912Z-dots-full-val/predictions.jsonl
)
EXPECTED_RESUME_HASHES=(
  76d318a1b51406c3d6fae65f15b875ca7ca70092bb8bbdbf3eb4e9e793e1d57e
  1765dc4c23dec7bafe3b5a673458ad004a8f5185b89427281e865510dccd0e79
  90209757ffa3bf1b6ac6e3682b89a4acce46a67243227d5b67660732af43bbfa
)
EXPECTED_RESUME_PAGES=(6151 636 6844)
test "${#RESUME_FILES[@]}" -le "${#EXPECTED_RESUME_FILES[@]}" || exit 2
HISTORICAL_PAGES=0
RESUME_HASHES=()
for ((i=0; i<${#RESUME_FILES[@]}; i++)); do
  file="${RESUME_FILES[i]}"
  test "$file" = "${EXPECTED_RESUME_FILES[i]}" && test -f "$file" || {
    printf 'Unexpected or missing recovery file: %s\n' "$file" >&2; exit 2;
  }
  hash="$(sha256sum "$file" | cut -d' ' -f1)" || exit 2
  count="$(wc -l < "$file")"
  test "$hash" = "${EXPECTED_RESUME_HASHES[i]}" && test "$count" -eq "${EXPECTED_RESUME_PAGES[i]}" || {
    printf 'Recovery file hash or count mismatch: %s\n' "$file" >&2; exit 2;
  }
  RESUME_HASHES+=("$hash")
  HISTORICAL_PAGES=$((HISTORICAL_PAGES + count))
done

test -d checkpoints/dots-ocr || { printf 'Model unavailable\n' >&2; exit 2; }
test -d 'data/pubtables-v2/extracted/Full Documents/val/images' || { printf 'Images unavailable\n' >&2; exit 2; }
ACTUAL_SHA="$(sha256sum "$MANIFEST" | cut -d' ' -f1)" || exit 2
test "$ACTUAL_SHA" = "$EXPECTED_SHA" || { printf 'Manifest hash mismatch\n' >&2; exit 2; }
PAGES="$(wc -l < "$MANIFEST")"
test "$PAGES" -eq 13871 || { printf 'Manifest page count mismatch\n' >&2; exit 2; }
if test "${#RESUME_FILES[@]}" -gt 0; then
  .venvs/eval312/bin/python - "$MANIFEST" "${RESUME_FILES[@]}" <<'PY' || exit 2
import json
import sys

manifest, *shards = sys.argv[1:]
with open(manifest, encoding="utf-8") as stream:
    expected = [json.loads(line)["image_id"] for line in stream]
actual = []
for shard in shards:
    with open(shard, encoding="utf-8") as stream:
        actual.extend(json.loads(line)["image_id"] for line in stream)
if actual != expected[:len(actual)]:
    raise SystemExit("Recovery shards do not match manifest prefix")
print(f"validated recovery prefix: {len(actual)}/{len(expected)} pages")
PY
fi

GPU_ROW="$(nvidia-smi --id=0 --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits)" || exit 2
GPU_FREE="$(printf '%s' "$GPU_ROW" | cut -d, -f2 | tr -dc '0-9')"
test -n "$GPU_FREE" && test "$GPU_FREE" -ge 30000 || {
  printf 'GPU 0 insufficient free memory: %s MiB\n' "$GPU_FREE" >&2
  exit 3
}
printf 'utc=%s run_id=%s manifest_pages=%s historical_pages=%s gpu0=%s\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$RUN_ID" "$PAGES" "$HISTORICAL_PAGES" "$GPU_ROW"
if test "$PREFLIGHT" -eq 1; then exit 0; fi

# The launcher creates only LOG for its own redirected stdout; refuse all other files.
test -d "$LOG" && test -f "$LOG/launcher.log" || exit 2
test ! -e "$OUT" && test ! -e "$LOG/events.log" || {
  printf 'Refusing to reuse existing run output\n' >&2
  exit 2
}
for path in "$PWD/artifacts/cache/hf-$RUN_ID" "$PWD/artifacts/cache/xdg-$RUN_ID" \
  "$PWD/artifacts/cache/torch-$RUN_ID" "$PWD/artifacts/tmp-$RUN_ID"; do
  test ! -e "$path" || { printf 'Refusing existing cache: %s\n' "$path" >&2; exit 2; }
done

set -C
mkdir -p "$OUT" "$PWD/artifacts/cache/hf-$RUN_ID" "$PWD/artifacts/cache/xdg-$RUN_ID" \
  "$PWD/artifacts/cache/torch-$RUN_ID" "$PWD/artifacts/tmp-$RUN_ID"
printf 'utc,event,details\n' > "$LOG/events.log"
printf 'utc,used_mib,free_mib,util_pct\n' > "$LOG/gpu-memory.csv"
printf 'utc,pages_written,total_pages\n' > "$LOG/progress.csv"
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_gpu_memory --format=csv,noheader,nounits > "$LOG/gpu-processes-start.csv"
printf '%s,started,"wrapper_pid=%s;gpu0_initial_free_mib=%s;manifest_sha256=%s;resume_sha256=%s;historical_pages=%s"\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$$" "$GPU_FREE" "$EXPECTED_SHA" "${RESUME_HASHES[*]:-none}" "$HISTORICAL_PAGES" >> "$LOG/events.log"

# Keep all model caches within the project and do not pass implicit credentials.
unset HF_TOKEN HUGGING_FACE_HUB_TOKEN
RESUME_ARGS=()
if test "${#RESUME_FILES[@]}" -gt 0; then RESUME_ARGS=(--resume-from "${RESUME_FILES[@]}"); fi
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
  HF_HOME="$PWD/artifacts/cache/hf-$RUN_ID" \
  XDG_CACHE_HOME="$PWD/artifacts/cache/xdg-$RUN_ID" \
  TORCH_HOME="$PWD/artifacts/cache/torch-$RUN_ID" \
  TMPDIR="$PWD/artifacts/tmp-$RUN_ID" PYTHONPATH=src \
  .venvs/eval312/bin/python scripts/evaluate_dotsocr_pubtables_v2.py \
    --model checkpoints/dots-ocr \
    --images 'data/pubtables-v2/extracted/Full Documents/val/images' \
    --manifest "$MANIFEST" --output "$PRED" --max-new-tokens 24000 "${RESUME_ARGS[@]}" \
    > "$LOG/inference.log" 2>&1 &
RUNNER=$!
printf '%s,runner_started,"pid=%s;predictions=%s"\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$RUNNER" "$PRED" >> "$LOG/events.log"

on_signal() {
  printf '%s,signal,"stopping own runner pid=%s"\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$RUNNER" >> "$LOG/events.log"
  kill -TERM "$RUNNER" 2>/dev/null || true
}
trap on_signal TERM INT

(
  samples=0
  misses=0
  last_pages=-1
  last_progress="$(date +%s)"
  while kill -0 "$RUNNER" 2>/dev/null; do
    row="$(nvidia-smi --id=0 --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>/dev/null)"
    if test -z "$row"; then
      misses=$((misses + 1))
      if test "$misses" -ge 3; then
        printf '%s,guard,"nvidia-smi failed three consecutive samples"\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG/events.log"
        kill -TERM "$RUNNER" 2>/dev/null || true
        break
      fi
    else
      misses=0
      printf '%s,%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$(printf '%s' "$row" | tr -d ' ')" >> "$LOG/gpu-memory.csv"
      free="$(printf '%s' "$row" | cut -d, -f2 | tr -dc '0-9')"
      if test -n "$free" && test "$free" -lt 8192; then
        printf '%s,guard,"gpu0 free=%s MiB, stopping own runner"\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$free" >> "$LOG/events.log"
        kill -TERM "$RUNNER" 2>/dev/null || true
        break
      fi
    fi
    samples=$((samples + 1))
    if test "$((samples % 6))" -eq 0; then
      pages=0
      if test -f "$PRED"; then pages="$(wc -l < "$PRED")"; fi
      printf '%s,%s,%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$((HISTORICAL_PAGES + pages))" "$PAGES" >> "$LOG/progress.csv"
      if test "$pages" -ne "$last_pages"; then
        last_pages="$pages"
        last_progress="$(date +%s)"
      elif test "$(($(date +%s) - last_progress))" -ge 5400; then
        printf '%s,guard,"no new page for 90 minutes, stopping own runner"\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG/events.log"
        kill -TERM "$RUNNER" 2>/dev/null || true
        break
      fi
      if test -f "$LOG/inference.log" && tail -n 5 "$LOG/inference.log" | grep -Eq 'OutOfMemoryError|CUDA out of memory'; then
        printf '%s,guard,"model reported CUDA OOM, stopping own runner"\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG/events.log"
        kill -TERM "$RUNNER" 2>/dev/null || true
        break
      fi
      recent="$(tail -n 40 "$LOG/inference.log" | grep -E '"status": "(ok|error)"' | tail -n 3)"
      if test "$(printf '%s\n' "$recent" | grep -c '"status": "error"' || true)" = 3; then
        printf '%s,guard,"three consecutive inference errors, stopping own runner"\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG/events.log"
        kill -TERM "$RUNNER" 2>/dev/null || true
        break
      fi
    fi
    sleep 10
  done
) &
MONITOR=$!
wait "$RUNNER"
RESULT=$?
kill "$MONITOR" 2>/dev/null || true
wait "$MONITOR" 2>/dev/null || true
FINAL_PAGES=0
if test -f "$PRED"; then FINAL_PAGES="$(wc -l < "$PRED")"; fi
printf '%s,finished,"exit_code=%s;new_pages=%s;historical_pages=%s;combined_pages=%s;expected=%s"\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$RESULT" "$FINAL_PAGES" "$HISTORICAL_PAGES" "$((HISTORICAL_PAGES + FINAL_PAGES))" "$PAGES" >> "$LOG/events.log"
printf '%s,%s,%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$((HISTORICAL_PAGES + FINAL_PAGES))" "$PAGES" >> "$LOG/progress.csv"
if test -f "$PRED"; then sha256sum "$PRED" > "$LOG/predictions.sha256"; fi
exit "$RESULT"
