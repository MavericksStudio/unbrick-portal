# Portal Agent — Phase 0: Feasibility Spikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the four load-bearing assumptions of the Portal Agent design on the actual device before building the brain or face.

**Architecture:** Each spike is a self-contained verification with a hard pass/fail gate. Spikes 1–2 are go/no-go (failure forces a pivot to a native Android app); spikes 3–4 produce tuning numbers. Work happens over the existing `adb` USB link; once Termux + sshd are up, switch to `ssh` over an `adb`-forwarded port for automated on-device control.

**Tech Stack:** adb, Termux (+Termux:API, +Termux:Boot), Fully Kiosk Browser, llama.cpp, gemma3:1b GGUF, Python `websockets`.

**Spec:** `docs/superpowers/specs/2026-06-05-portal-agent-design.md` §10.

**Device facts (measured):** Portal Mini, Android 10 / API 29, arm64-v8a, QCS605, ~1.2 GB free RAM, 3.4 GB free on `/data`, no Google Play services, SELinux enforcing, no root. `adb` authorized as serial `819LCM01Z101H523`.

**Working dir for downloaded APKs/models:** `~/portal-agent/.spike/` (gitignored).

---

## Task 0: Spike scratch space

**Files:**
- Create: `~/portal-agent/.spike/` (gitignored)
- Modify: `~/portal-agent/.gitignore`

- [ ] **Step 1: Create scratch dir and ignore it**

```bash
cd ~/portal-agent
mkdir -p .spike
grep -qxF '.spike/' .gitignore || echo '.spike/' >> .gitignore
```

- [ ] **Step 2: Verify device is still connected**

Run: `adb devices`
Expected: a line `819LCM01Z101H523\tdevice` (status `device`, not `unauthorized`/`offline`).

- [ ] **Step 3: Commit the gitignore change**

```bash
cd ~/portal-agent
git add .gitignore
git commit -m "chore: ignore .spike scratch dir for Phase 0"
```

---

## Task 1: Spike — Termux runs on the Portal (GO/NO-GO)

**Goal:** Termux installs and runs a working package manager on this locked, no-root Android 10 device, and we can reach it from the Mac via ssh over an adb-forwarded port.

**Files:**
- Create: `~/portal-agent/.spike/termux-app.apk`
- Create: `~/portal-agent/.spike/termux-api.apk`

- [ ] **Step 1: Download the latest arm64-v8a Termux + Termux:API APKs**

```bash
cd ~/portal-agent/.spike
# Termux app (arm64-v8a split from the official GitHub release)
curl -sL https://api.github.com/repos/termux/termux-app/releases/latest \
  | grep -o 'https://[^"]*arm64-v8a\.apk' | head -1 \
  | xargs curl -L -o termux-app.apk
# Termux:API addon
curl -sL https://api.github.com/repos/termux/termux-api/releases/latest \
  | grep -o 'https://[^"]*arm64-v8a\.apk' | head -1 \
  | xargs curl -L -o termux-api.apk
ls -la termux-app.apk termux-api.apk
```

Expected: both files exist and are > 1 MB.

- [ ] **Step 2: Install both APKs to the Portal**

```bash
adb install -r ~/portal-agent/.spike/termux-app.apk
adb install -r ~/portal-agent/.spike/termux-api.apk
```

Expected: `Success` for each.
If `INSTALL_FAILED_*` appears, record the exact code — a signature/ABI failure here is a partial NO-GO signal (try the F-Droid build before declaring failure).

- [ ] **Step 3: Launch Termux**

```bash
adb shell monkey -p com.termux -c android.intent.category.LAUNCHER 1
```

Expected: Termux opens on the Portal screen showing a terminal prompt. (Confirm visually on the device.)

- [ ] **Step 4: Bootstrap packages + sshd on-device**

On the Portal's Termux terminal (type on the touchscreen keyboard, or drive with `adb shell input text`/`input keyevent 66`), run:

```bash
pkg update -y && pkg install -y openssh
whoami; uname -m; passwd   # set a password for ssh
sshd                       # starts sshd on port 8022
```

Expected: `pkg` downloads succeed (proves networking + repo access), `uname -m` prints `aarch64`, `sshd` starts with no error.
A `pkg update` failure (DNS/repo) is recoverable (switch mirror with `termux-change-repo`); a hard crash of Termux on launch is a NO-GO.

- [ ] **Step 5: Reach Termux from the Mac via adb-forwarded ssh**

```bash
adb forward tcp:8022 tcp:8022
ssh -p 8022 -o StrictHostKeyChecking=no "$(adb shell whoami | tr -d '\r')"@127.0.0.1 'echo SSH_OK; uname -a; nproc; free -m'
```

Wait — Termux username is not the adb shell user. Get it from Step 4's `whoami` (typically `u0_aXXX`). Use that:

```bash
adb forward tcp:8022 tcp:8022
ssh -p 8022 -o StrictHostKeyChecking=no u0_aXXX@127.0.0.1 'echo SSH_OK; nproc; free -m'
```

Expected: prints `SSH_OK`, core count (8), and memory. **This is the GO gate for Task 1** — we now have automated shell access to the on-device Linux userland.

- [ ] **Step 6: Record the result**

```bash
cd ~/portal-agent/.spike
printf 'SPIKE 1 (Termux): %s\n' "$(date)" >> RESULTS.md
printf '  ssh user: u0_aXXX  port: 8022 (adb-forwarded)\n' >> RESULTS.md
printf '  pkg works: YES/NO   sshd works: YES/NO\n' >> RESULTS.md
```

(Fill YES/NO by hand from observed output.)

---

## Task 2: Spike — WebView getUserMedia mic + camera (GO/NO-GO)

**Goal:** A web page running in an on-device browser can access the Portal's mic and camera via `getUserMedia` and grant the permission persistently.

**Files:**
- Create: `~/portal-agent/.spike/getusermedia-test.html`
- Create: `~/portal-agent/.spike/fully-kiosk.apk`

- [ ] **Step 1: Write a minimal getUserMedia test page**

```html
<!-- ~/portal-agent/.spike/getusermedia-test.html -->
<!doctype html><meta charset="utf-8">
<title>gUM test</title>
<style>body{font:5vw sans-serif;background:#111;color:#0f0;margin:0}
video{width:100%}#lvl{height:8vw;background:#030}</style>
<video id="v" autoplay playsinline muted></video>
<div id="lvl"></div><pre id="log"></pre>
<script>
const log=(m)=>document.getElementById('log').textContent+=m+'\n';
(async()=>{try{
  const s=await navigator.mediaDevices.getUserMedia({audio:true,video:true});
  document.getElementById('v').srcObject=s; log('CAMERA OK');
  const ac=new AudioContext(),src=ac.createMediaStreamSource(s),
        an=ac.createAnalyser();src.connect(an);
  const buf=new Uint8Array(an.fftSize);
  setInterval(()=>{an.getByteTimeDomainData(buf);
    let p=0;for(const x of buf)p=Math.max(p,Math.abs(x-128));
    document.getElementById('lvl').style.width=(p/128*100)+'%';},100);
  log('MIC OK — speak to move the bar');
}catch(e){log('FAIL: '+e.name+' '+e.message);}})();
</script>
```

- [ ] **Step 2: Serve the page from the Mac**

```bash
cd ~/portal-agent/.spike
python3 -m http.server 8099 >/tmp/spike-http.log 2>&1 &
echo "served on http://<mac-LAN-ip>:8099/getusermedia-test.html"
ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1
```

Expected: prints the Mac's LAN IP. The Portal (same Wi-Fi) will load `http://<that-ip>:8099/getusermedia-test.html`.

- [ ] **Step 3: Install Fully Kiosk Browser**

```bash
cd ~/portal-agent/.spike
curl -L -o fully-kiosk.apk "https://www.fully-kiosk.com/fully-kiosk.apk"
adb install -r fully-kiosk.apk
```

Expected: `Success`. (If the direct URL 404s, fetch the current APK link from https://www.fully-kiosk.com/#download and retry.)

- [ ] **Step 4: Configure Fully Kiosk to auto-grant mic/cam and load the page**

Launch Fully Kiosk:

```bash
adb shell monkey -p de.ozerov.fully -c android.intent.category.LAUNCHER 1
```

On the Portal, in Fully Kiosk settings:
- Set **Start URL** = `http://<mac-LAN-ip>:8099/getusermedia-test.html`
- **Web Content Settings** → enable **Enable Camera/Microphone Access** and **Auto Grant Permissions** (free-tier supports the WebView permission grant; some camera *capture* features are Plus, but `getUserMedia` for web content works).
- Tap **Load Start URL**.

- [ ] **Step 5: Verify mic + camera**

Expected on the Portal screen: live **camera preview** is visible, the page logs `CAMERA OK` and `MIC OK`, and the green level bar **moves when you speak**.
**This is the GO gate for Task 2.** If the page logs `FAIL: NotAllowedError` even after enabling auto-grant, try the system Android WebView update or a second browser before declaring NO-GO.

- [ ] **Step 6: Record the result + stop the server**

```bash
cd ~/portal-agent/.spike
printf 'SPIKE 2 (getUserMedia): camera=YES/NO mic=YES/NO  %s\n' "$(date)" >> RESULTS.md
kill %1 2>/dev/null   # stop python http.server
```

---

## Task 3: Spike — gemma3:1b runs at usable speed on QCS605

**Goal:** `llama.cpp` loads gemma3:1b within free RAM and generates at a usable rate for short routing prompts. Runs over the ssh-from-Task-1 link.

**Files:**
- Create (on device): `~/llama/` with `llama.cpp` and `gemma-3-1b-it-Q4_K_M.gguf`

- [ ] **Step 1: Open an ssh session to Termux**

```bash
adb forward tcp:8022 tcp:8022
ssh -p 8022 u0_aXXX@127.0.0.1
```

(All steps below run inside that Termux ssh session. Replace `u0_aXXX` with the Task-1 username.)

- [ ] **Step 2: Install llama.cpp**

```bash
pkg install -y llama-cpp wget
llama-cli --version
```

Expected: prints a llama.cpp build/version line.
If the `llama-cpp` package is unavailable, fall back to building: `pkg install -y git cmake clang && git clone --depth 1 https://github.com/ggerganov/llama.cpp && cd llama.cpp && cmake -B build -DGGML_NATIVE=ON && cmake --build build -j$(nproc)`.

- [ ] **Step 3: Download gemma3:1b Q4 GGUF**

```bash
mkdir -p ~/llama && cd ~/llama
wget -O gemma-3-1b-it-Q4_K_M.gguf \
  https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf
ls -la gemma-3-1b-it-Q4_K_M.gguf
```

Expected: file ~0.7–0.8 GB. (If that repo/quant path moved, pick any `gemma-3-1b-it` `Q4_K_M` GGUF on Hugging Face.)

- [ ] **Step 4: Benchmark a short routing-style generation**

```bash
cd ~/llama
llama-cli -m gemma-3-1b-it-Q4_K_M.gguf -t 4 -n 64 -no-cnv \
  -p 'Reply ONLY with JSON. User: what time is it? Action:' 2>&1 | tail -20
```

Expected: coherent output **and** a final timing line reporting `eval time ... tokens per second`.
**Pass criteria:** model loads without OOM (watch `free -m` in another ssh session stays > 0 available) and **eval ≥ 5 tok/s**. Below ~3 tok/s, note it — Task in Plan 2 may switch to a 0.5B model.

- [ ] **Step 5: Record numbers**

```bash
# back on the Mac
cd ~/portal-agent/.spike
printf 'SPIKE 3 (gemma3:1b): load=OK/OOM  eval=__ tok/s  threads=4  %s\n' "$(date)" >> RESULTS.md
```

---

## Task 4: Spike — localhost WebSocket between Fully Kiosk page and Termux

**Goal:** A page in Fully Kiosk can open a WebSocket to a server running in Termux over `127.0.0.1` — the core IPC channel of the design.

**Files:**
- Create (on device): `~/ws_echo.py`
- Create: `~/portal-agent/.spike/ws-test.html`

- [ ] **Step 1: Write an echo WS server (in Termux via ssh)**

```bash
pkg install -y python
pip install websockets
cat > ~/ws_echo.py <<'PY'
import asyncio, websockets
async def h(ws):
    async for m in ws:
        await ws.send("echo:" + m)
async def main():
    async with websockets.serve(h, "127.0.0.1", 8765):
        print("WS up on 127.0.0.1:8765"); await asyncio.Future()
asyncio.run(main())
PY
python ~/ws_echo.py
```

Expected: prints `WS up on 127.0.0.1:8765` and blocks (leave it running).

- [ ] **Step 2: Write a WS client test page**

```html
<!-- ~/portal-agent/.spike/ws-test.html -->
<!doctype html><meta charset="utf-8"><title>ws</title>
<pre id="o" style="font:5vw monospace;color:#0f0;background:#111"></pre>
<script>
const o=document.getElementById('o'),log=m=>o.textContent+=m+'\n';
const ws=new WebSocket('ws://127.0.0.1:8765');
ws.onopen =()=>{log('OPEN');ws.send('ping');};
ws.onmessage=e=>log('RECV '+e.data);   // expect "echo:ping"
ws.onerror =e=>log('ERROR');
ws.onclose =()=>log('CLOSE');
</script>
```

- [ ] **Step 3: Push the page on-device and load it in Fully Kiosk**

The page must be served from the device so its origin can reach `127.0.0.1`. Serve it from Termux:

```bash
# in a second Termux ssh session
mkdir -p ~/wwwspike && cd ~/wwwspike
# copy ws-test.html here (scp from Mac):
#   scp -P 8022 ~/portal-agent/.spike/ws-test.html u0_aXXX@127.0.0.1:~/wwwspike/
python -m http.server 8088
```

Then in Fully Kiosk set Start URL = `http://127.0.0.1:8088/ws-test.html` and load it.

- [ ] **Step 4: Verify the round-trip**

Expected on the Portal screen: the page prints `OPEN` then `RECV echo:ping`.
**This is the GO gate for Task 4** — confirms the page↔Termux localhost WS channel works inside the device.

- [ ] **Step 5: Record result**

```bash
cd ~/portal-agent/.spike
printf 'SPIKE 4 (localhost WS): roundtrip=YES/NO  %s\n' "$(date)" >> RESULTS.md
```

---

## Task 5: Phase 0 verdict

- [ ] **Step 1: Summarize and commit the results file**

```bash
cd ~/portal-agent/.spike && cat RESULTS.md
```

- [ ] **Step 2: Decide GO / PIVOT**

- All four spikes pass → **GO**: proceed to Plan 2 (headless brain) and Plan 3 (WebView face) as designed.
- Spike 1 (Termux) or Spike 2 (getUserMedia) fails → **PIVOT** to Approach B (native Android app); revisit the spec before more planning.
- Spike 3 weak (< 3 tok/s) → keep Approach A but down-spec the local SLM to 0.5B in Plan 2.
- Spike 4 fails → keep Approach A but reconsider IPC (e.g., HTTP long-poll on localhost) in Plan 2.

- [ ] **Step 3: Record the verdict in the spec**

Append a short "Phase 0 outcome" note to `docs/superpowers/specs/2026-06-05-portal-agent-design.md` and commit:

```bash
cd ~/portal-agent
git add docs/superpowers/specs/2026-06-05-portal-agent-design.md
git commit -m "docs: record Phase 0 feasibility outcome"
```

---

## Subsequent plans (outline — written after Phase 0 GO)

- **Plan 2 — Headless Brain** (`portal-agent` Python): fork `agent.py` → strip Tkinter + `sounddevice`/`rpicam`; swap `ollama` → `llama.cpp` HTTP client; add WS server; implement the `escalate` action (Claude) and cloud-TTS path; keep whisper.cpp STT, tool dispatch, and `chat_memory.json`. Unit-test router parsing + escalation + tool dispatch; integration-test WS with a mock face.
- **Plan 3 — WebView Face** (HTML/JS): avatar PNG state machine, `getUserMedia` mic (tap-to-talk) + camera, WebAudio playback, WS client; Fully Kiosk config.
- **Plan 4 — Integration & Autostart:** Termux:Boot + `termux-wake-lock`, brain supervisor/restart, Fully Kiosk auto-launch, end-to-end on-device test; then the v2 wake-word hook.
