#!/usr/bin/env bash
# Install an isolated, pinned PaddleOCR-VL-1.5 native runtime (CPU/network only).
set -euo pipefail
cd /data01/public/zhengguojie/paper
RUN_ID="${1:?run ID required}"
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]
ENV_DIR="$PWD/.venvs/paddle-v15-$RUN_ID"
LOG_DIR="$PWD/logs/paddle-setup/$RUN_ID"
test ! -e "$ENV_DIR"
test ! -e "$LOG_DIR"
mkdir -p "$LOG_DIR/tmp" "$LOG_DIR/pip-cache"
export TMPDIR="$LOG_DIR/tmp"
export PIP_CACHE_DIR="$LOG_DIR/pip-cache"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_INPUT=1
export CUDA_VISIBLE_DEVICES=""
.venvs/eval312/bin/python -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --index-url https://pypi.org/simple \
  --timeout 60 --retries 2 --report "$LOG_DIR/paddle-install.json" \
  'https://paddle-whl.cdn.bcebos.com/stable/cu118/paddlepaddle-gpu/paddlepaddle_gpu-3.2.1-cp312-cp312-linux_x86_64.whl'
"$ENV_DIR/bin/python" -m pip install --index-url https://pypi.org/simple \
  --timeout 60 --retries 2 --report "$LOG_DIR/ocr-install.json" \
  'paddleocr[doc-parser]==3.4.0' 'paddlex==3.4.1' 'numpy==1.26.4'
"$ENV_DIR/bin/python" -m pip check
"$ENV_DIR/bin/python" -m pip freeze > "$LOG_DIR/requirements.lock.txt"
"$ENV_DIR/bin/python" -c 'import importlib.metadata as m, json, sys; print(json.dumps({"python":sys.version,"paddleocr":m.version("paddleocr"),"paddlex":m.version("paddlex"),"paddlepaddle-gpu":m.version("paddlepaddle-gpu"),"status":"installed_not_smoke_tested"}))' > "$LOG_DIR/setup-complete.json"
