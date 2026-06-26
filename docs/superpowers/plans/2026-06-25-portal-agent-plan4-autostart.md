# Portal Agent — Plan 4: Autostart & Keep-Alive

**Goal:** Make the Portal a true appliance — brain + face start on boot, stay up if
they crash, and survive the Termux session closing. Today both die when the
session ends; we relaunch by hand every time.

**Approach:** A supervisor loop (holds a wake-lock, restarts brain + face server if
they drop) launched at boot by **Termux:Boot**, with secrets in a `chmod 600` env
file. **Fully Kiosk** auto-launches the face on boot. Verified by a real reboot.

**Context (measured 2026-06-25):** Termux:Boot/API *apps* not installed; no
`~/.termux/boot/`; no secrets file; gemma dropped (Plan 3) so RAM is comfortable
(~1.5 GB free) — OOM-kill risk is low now.

## Pieces

1. **Secrets at rest** — `~/.portal-agent.env` (user-created, `chmod 600`):
   `ANTHROPIC_API_KEY=...` and `ELEVENLABS_API_KEY=...`. Sourced by the supervisor.
2. **`scripts/supervise.sh`** (new) — sources the env, `termux-wake-lock`, then a
   loop: if `127.0.0.1:8765` (brain) not listening → start `python -m brain`; if
   `127.0.0.1:8088` (face) not listening → start the static server; `sleep 15`.
3. **`~/.termux/boot/start-portal.sh`** (on device) — runs `supervise.sh` at boot.
4. **Termux:Boot + Termux:API apps** — install matching-signature APKs (GitHub
   releases, same key as the GitHub Termux app), launch once to register.
5. **Battery/doze whitelist** (adb) — keep Termux alive in the background.
6. **Fully Kiosk** — Start on Boot + Start URL `http://127.0.0.1:8088/` + keep
   screen on (+ its own crash-relaunch).

## Steps

- [ ] **Branch** `plan4-autostart`.
- [ ] **Install addon apps** (arm64, GitHub releases for signature match):
  `termux-boot` (`com.termux.boot`) and `termux-api` (`com.termux.api`) via
  `adb install`; launch each once (`monkey -p ... LAUNCHER`).
- [ ] **Doze/background whitelist** via adb:
  `dumpsys deviceidle whitelist +com.termux`, `+com.termux.boot`;
  `cmd appops set com.termux RUN_IN_BACKGROUND allow`.
- [ ] **`scripts/supervise.sh`** — write, commit, deploy. Content:
  ```bash
  #!/data/data/com.termux/files/usr/bin/bash
  set -uo pipefail
  cd "$(dirname "$0")/.."
  [ -f "$HOME/.portal-agent.env" ] && set -a && . "$HOME/.portal-agent.env" && set +a
  termux-wake-lock 2>/dev/null || true
  listening() { (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1; }
  while true; do
    listening 8765 || { echo "[sup] starting brain"; nohup python -m brain >>"$HOME/brain.log" 2>&1 & }
    listening 8088 || { echo "[sup] starting face"; nohup python -m http.server 8088 --bind 127.0.0.1 --directory "$PWD/face" >>"$HOME/face.log" 2>&1 & }
    sleep 15
  done
  ```
- [ ] **Boot hook** — create on device:
  `~/.termux/boot/start-portal.sh` = `#!/data/data/com.termux/files/usr/bin/bash`
  + `exec ~/portal-agent/scripts/supervise.sh >>~/supervise.log 2>&1`; `chmod +x`.
- [ ] **Secrets** — user creates `~/.portal-agent.env` with both keys; `chmod 600`.
- [ ] **Fully Kiosk** — in settings: enable *Start on Boot* / *Launch on Boot*,
  set *Start URL* = `http://127.0.0.1:8088/`, *Keep Screen On*, *Auto-reload on
  idle/disconnect* if available. (User taps; some settable via Fully provisioning.)

## Verification

1. **Supervisor (no reboot):** kill brain; run `bash scripts/supervise.sh &`;
   confirm within ~15 s the brain is back on 8765 (`brain.log` shows start) and a
   turn works from the Portal.
2. **Crash recovery:** `pkill -f "python -m brain"`; confirm the supervisor
   restarts it within 15 s.
3. **Full reboot:** `adb reboot`; wait; **without any manual start**, confirm:
   Termux:Boot ran the hook (`~/supervise.log`), brain (8765) + face (8088) are up,
   Fully Kiosk is showing the orb, and a tap-to-talk turn works end to end.
4. Re-arm `adb forward` after reboot; check `~/brain-errors.log` clean.

## Out of scope
- OOM auto-recovery mid-session (Termux:Boot only fires at boot; mitigated by the
  freed RAM). If it recurs, add a watchdog or reduce footprint further.
- Over-the-air updates / remote management.

## Done = the appliance test
Unplug the Portal, move it, plug it in → it boots straight to the talking orb with
no laptop, no ssh, no manual commands.
