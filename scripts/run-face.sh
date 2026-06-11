#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
FACE_DIR="$(cd "$(dirname "$0")/.." && pwd)/face"
echo "serving face at http://127.0.0.1:8088/  (dir: $FACE_DIR)"
exec python -m http.server 8088 --bind 127.0.0.1 --directory "$FACE_DIR"
