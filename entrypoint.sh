#!/bin/bash
set -e

echo "[ENTRYPOINT] Starting virtual display..."
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1920x1080x24 -ac &
export DISPLAY=:99
sleep 2

echo "[ENTRYPOINT] GPU check..."
rocm-smi || echo "WARNING: rocm-smi unavailable"

echo "[ENTRYPOINT] Ollama check at ${OLLAMA_HOST}..."
curl -s --max-time 5 "${OLLAMA_HOST}/api/tags" > /dev/null \
  && echo "[OK] Ollama reachable" \
  || echo "[WARN] Ollama not reachable"

while true; do
    echo "[ENTRYPOINT] Launching auto_run.py..."
    python auto_run.py
    echo "[ENTRYPOINT] Pipeline done. Sleeping 24 hours..."
    sleep 86400
done
