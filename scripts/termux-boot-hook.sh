#!/data/data/com.termux/files/usr/bin/bash
# Reference copy of the Termux:Boot hook. You normally DON'T install this by hand —
# scripts/setup-termux.sh generates the real hook at ~/.termux/boot/start-portal.sh
# with the absolute path to wherever you cloned the repo. Termux:Boot runs the hook
# at device boot; it hands off to the supervisor, which keeps everything alive.
exec "$(cd "$(dirname "$0")/.." && pwd)/scripts/supervise.sh" >>"$HOME/supervise.log" 2>&1
