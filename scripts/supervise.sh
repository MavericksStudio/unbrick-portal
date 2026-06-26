#!/data/data/com.termux/files/usr/bin/bash
# Keep the Portal Agent alive: hold a wake-lock and (re)start the brain + face
# server whenever they're not listening. Launched at boot by Termux:Boot, or run
# by hand. Secrets come from ~/.portal-agent.env (chmod 600).
set -uo pipefail
cd "$(dirname "$0")/.."

if [ -f "$HOME/.portal-agent.env" ]; then
  set -a; . "$HOME/.portal-agent.env"; set +a
fi

termux-wake-lock 2>/dev/null || true

listening() { (echo >"/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1; }

echo "[supervise] $(date) starting watch loop"
while true; do
  if ! listening 8022; then
    echo "[supervise] $(date) sshd down -> starting"
    sshd 2>/dev/null || true
  fi
  if ! listening 8765; then
    echo "[supervise] $(date) brain down -> starting"
    nohup python -m brain >>"$HOME/brain.log" 2>&1 &
  fi
  if ! listening 8088; then
    echo "[supervise] $(date) face down -> starting"
    nohup python -m http.server 8088 --bind 127.0.0.1 --directory "$PWD/face" \
      >>"$HOME/face.log" 2>&1 &
  fi
  sleep 15
done
