#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${LLAMA_MODEL:-$HOME/llama/gemma-3-1b-it-Q4_K_M.gguf}"

# 1) start llama-server with --no-mmap (Phase 0: REQUIRED on this device)
if ! curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "starting llama-server (--no-mmap)..."
  nohup llama-server -m "$MODEL" --no-mmap -t 4 -c 2048 \
    --host 127.0.0.1 --port 8080 >"$HOME/llama-server.log" 2>&1 &
  for i in $(seq 1 60); do
    curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1 && break; sleep 1
  done
fi

# 2) start the brain
exec python -m brain
