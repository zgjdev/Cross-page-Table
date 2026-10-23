#!/usr/bin/env bash
# A finite train smoke waits for its isolated environment, not a recurring monitor.
set -euo pipefail
cd /data01/public/zhengguojie/paper
SETUP_ID=20261023T081029Z-paddle-v15
SETUP_UNIT=paper-paddle-setup-20261023T081029Z.service
RUN_ID="${1:?timestamped smoke ID required}"
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z-paddle-train-smoke$ ]]
ENV_DIR=".venvs/paddle-v15-$SETUP_ID"
COMPLETE="logs/paddle-setup/$SETUP_ID/setup-complete.json"
printf 'WAIT_SETUP %s\n' "$(date -u +%FT%TZ)"
while test ! -f "$COMPLETE"; do
  STATE="$(systemctl --user show "$SETUP_UNIT" -p ActiveState --value)"
  case "$STATE" in
    active|activating) sleep 15 ;;
    *) printf 'SETUP_NOT_COMPLETE state=%s\n' "$STATE" >&2; exit 2 ;;
  esac
done
printf 'START_SMOKE %s\n' "$(date -u +%FT%TZ)"
exec "$ENV_DIR/bin/python" -u scripts/run_paddle_v15_smoke.py \
  --inputs artifacts/paddle-smoke/20261023T081900Z-train-inputs \
  --vl-model models/20261023T064109Z-public-models/paddleocr-vl-1.5 \
  --layout-model models/20261023T081029Z-paddle-layout/pp-doclayoutv3 \
  --gpu 0 --run-id "$RUN_ID"
