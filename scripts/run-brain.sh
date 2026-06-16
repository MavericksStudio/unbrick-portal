#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Cloud-only brain (gemma/llama dropped — too slow on this SoC). Requires
# ANTHROPIC_API_KEY and ELEVENLABS_API_KEY in the environment.
exec python -m brain
