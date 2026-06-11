# Portal Agent — Design Spec

**Date:** 2026-06-05
**Status:** Approved (design); **Phase 0 feasibility = GO** (all 4 spikes pass)
**Forked from:** [`brenpoly/be-more-agent`](https://github.com/brenpoly/be-more-agent)

## Phase 0 outcome (2026-06-05)

All four feasibility spikes passed on the physical device — **Approach A is GO**.

- **Spike 1 — Termux:** GO. Locked Android runs Termux (no root); pkg repos,
  `sshd`, and key auth over an `adb`-forwarded port all work. We have automated
  shell access as `u0_a45`.
- **Spike 3 — gemma3:1b:** PASS, **but only with `--no-mmap`**. With mmap the
  806 MB model thrashes flash (~0.08 tok/s) against ~38 MB free RAM. With
  `--no-mmap -t 4`: **pp16 = 13.88 t/s, tg16 = 8.25 t/s** (usable).
  → **The brain MUST launch llama with `--no-mmap` on this device.**
- **Spike 4 — localhost WS:** PASS. Termux WS server + on-device loopback, and a
  Fully Kiosk WebView page reached `ws://127.0.0.1:8765` and round-tripped.
- **Spike 2 — getUserMedia:** PASS (camera + mic) in Fully Kiosk free tier.
  Gotchas: grant `CAMERA`+`RECORD_AUDIO` then **restart Fully** to ungrey the mic
  toggle; enable Camera+Microphone access in Web Content Settings; **resume the
  `AudioContext` on a user tap** (starts suspended on mobile).

Full log: `docs/superpowers/plans/2026-06-05-portal-agent-phase0-feasibility.md`
results / `.spike/RESULTS.md`.

## 1. Goal

Turn a Meta-bricked **Portal Mini** into a self-orchestrating voice + vision AI
appliance. An **on-device small language model (SLM)** is the cheap first
responder and **router**: it answers trivial requests locally and **escalates
hard tasks to cloud APIs**. Everything runs on the Portal's own hardware — no
dependency on an external host at runtime.

This adapts `be-more-agent` (a 100%-local Raspberry Pi agent) to **locked
Android 10, no root**, by splitting it into a headless **Termux brain** and a
**WebView face**.

## 2. Target hardware (measured)

| Spec | Value |
|------|-------|
| Device | Meta Portal Mini (codename `omni`), serial `819LCM01Z101H523` |
| OS | Android 10 (API 29), **no Google Play services**, SELinux enforcing, no root |
| SoC | Qualcomm **QCS605** — 8-core Kryo 300, Adreno 615 GPU, Hexagon 685 DSP |
| RAM | 2.85 GB total, **~1.2 GB free** |
| Storage | 3.4 GB free on `/data` |
| ABI | arm64-v8a (+ dotprod) |
| I/O | far-field mic array, wide camera, speakers, 800×1280 touchscreen |
| Access | `adb` over USB (USB debugging / "ADB Enabled" turned on by user) |

## 3. Architecture

Two on-device processes communicating over `localhost`:

```
┌─────────────────── Meta Portal (Android 10) ───────────────────┐
│  ② Face — WebView / Fully Kiosk      ① Brain — Termux (Python)  │
│  ┌─────────────────────────┐         ┌───────────────────────┐  │
│  │ Avatar face (PNG states)│◄──ws──► │ Agent brain           │  │
│  │ getUserMedia: mic + cam │         │  • state machine      │  │
│  │ WebAudio: speaker       │         │  • llama.cpp SLM      │──┼─► Cloud APIs
│  │ tap-to-talk button      │         │    (gemma3:1b router) │  │   (Claude, TTS)
│  └─────────────────────────┘         │  • whisper.cpp STT    │  │
│                                      │  • tools + memory     │  │
│                                      └───────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### ① Brain — Termux, Python (headless)

Forked `agent.py` with the Tkinter GUI and `sounddevice`/`rpicam` I/O removed.
Becomes a headless WebSocket server. Responsibilities:

- **Local SLM:** `llama.cpp` `llama-server` hosting **gemma3:1b** (Q4 GGUF,
  ~0.8 GB) via its OpenAI-compatible HTTP API (replaces the `ollama` lib).
- **STT:** `whisper.cpp` (`ggml-base.en`) via subprocess — local, per user choice.
- **Router + tool dispatch:** parse the SLM's JSON action and execute it
  (see §4).
- **Chat memory:** `chat_memory.json` (carried over from upstream).
- **WS server:** binds `127.0.0.1:<port>`; one connected face client.

### ② Face — WebView / Fully Kiosk UI (HTML/JS)

Replaces the Tkinter GUI. Handles **all realtime audio/camera** (the reason for
the split — Android's WebView supports `getUserMedia`, Termux audio does not).

- **Mic:** `getUserMedia` audio; tap-to-talk button starts/stops capture;
  streams audio frames to the brain.
- **Speaker:** WebAudio plays TTS audio returned by the brain.
- **Camera:** `getUserMedia` video; sends a single JPEG frame when the brain
  requests one.
- **Avatar:** reuses upstream's **per-state PNG face-sequences**
  (idle / listening / thinking / speaking / error), re-rendered in HTML/JS and
  driven by `state` messages from the brain.
- Hosted in **Fully Kiosk Browser** (auto-grants mic/cam, kiosk autostart,
  wake-lock, screensaver control).

## 4. SLM router contract

Extends upstream's JSON-action scheme. The SLM replies with exactly one JSON
action, or plain text to be spoken:

```json
{"action":"get_time"}
{"action":"search_web","query":"..."}
{"action":"capture_image"}
{"action":"escalate","model":"claude","query":"..."}
```

- `gemma3:1b` handles trivial requests and **routing decisions** locally.
- **`escalate`** (new) hands hard reasoning to **Claude** via the Anthropic API.
- `capture_image` → brain sends `request_frame` to the face → vision (cloud in
  v1; local `moondream` deferred to save RAM).
- Plain text → spoken directly via cloud TTS.

## 5. WebSocket protocol (brain ↔ face)

| Direction | Message | Payload |
|-----------|---------|---------|
| face → brain | `ptt` | `{state: "start" \| "stop"}` |
| face → brain | `audio` | streamed mic audio chunk |
| face → brain | `frame` | `{jpeg: <base64>}` (in response to `request_frame`) |
| brain → face | `state` | `{value: "idle"\|"listening"\|"thinking"\|"speaking"\|"error"}` |
| brain → face | `request_frame` | — |
| brain → face | `tts_audio` | audio buffer to play |
| brain → face | `caption` | `{text: "..."}` |

## 6. Turn flow

1. User taps the screen → face sends `ptt:start`, begins streaming mic audio.
2. Brain sets `state:listening`; on `ptt:stop` (or endpoint), finalizes audio.
3. **whisper.cpp** transcribes locally → `state:thinking`.
4. **gemma3:1b** decides: plain answer | tool action | `escalate`.
5. If `escalate` → call **Claude**; if a tool → run it (web/time/vision).
6. Final text → **cloud TTS** → `tts_audio` + `caption` + `state:speaking`.
7. Face plays audio and animates the avatar; returns to `state:idle`.

## 7. Technology choices (locked)

| Concern | Choice | Notes |
|---------|--------|-------|
| Local SLM | `llama.cpp` + **gemma3:1b** Q4 GGUF | replaces Ollama (Termux-friendly) |
| STT | **whisper.cpp** `ggml-base.en`, local | user choice |
| TTS | **cloud** (ElevenLabs, `eleven_turbo_v2_5`) | user choice — low latency + natural voice for a voice device |
| Escalation brain | **Claude** (Anthropic API) | reuse openclaw's Anthropic SDK |
| Vision (v1) | **cloud** vision on captured frame | local `moondream` deferred (RAM) |
| Runtime | **Termux** + **Termux:API** | no root, no Google services |
| UI host | **Fully Kiosk Browser** | auto-grants mic/cam, autostart, wake-lock |
| Wake word (v2) | **OpenWakeWord** (already in fork) | no Picovoice key needed |

## 8. Autostart / keep-alive (locked Android)

- **Termux:Boot** starts the brain on boot; brain acquires `termux-wake-lock`.
- **Fully Kiosk** auto-launches the face on boot, set as home/launcher,
  configured to keep screen on and auto-grant permissions.
- Brain runs under a small supervisor that restarts it on crash.

## 9. v2 wake-word hook

OpenWakeWord (`wakeword.onnx`) is already in the fork. The face already streams
mic audio to the brain, so v2 runs the wake-word model on that stream (in the
brain, or in the face via `onnxruntime-web`) and flips the trigger from
tap → wake. **No architecture change required.**

## 10. De-risk spikes (run before full build)

1. **Termux runs on the Portal** — sideload the Termux APK via `adb install`,
   confirm an interactive shell and `pkg` work (no root).
2. **WebView `getUserMedia`** — confirm Fully Kiosk (or system WebView) grants
   mic + camera on the Portal's Android 10 WebView.
3. **gemma3:1b performance** — confirm `llama.cpp` runs gemma3:1b at usable
   tokens/sec on QCS605 CPU within ~1.2 GB free RAM.
4. **localhost WS** — confirm a Fully Kiosk page can open a WebSocket to the
   Termux server on `127.0.0.1`.

A blocking failure in spike 1 or 2 forces a pivot toward the native-app
approach (Approach B); spikes 3–4 inform tuning, not feasibility.

## 11. Error handling

- **No network:** local SLM + whisper still work; `escalate` and cloud TTS fail
  gracefully → spoken local fallback + `state:error`.
- **SLM emits malformed JSON:** treat as plain text (upstream already tolerates
  this via `extract_json_from_text`).
- **Brain crash:** supervisor restarts; face shows `state:error` on WS drop and
  auto-reconnects.
- **Mic/cam permission denied:** face surfaces a visible prompt; Fully Kiosk
  config should pre-grant.

## 12. Testing

- **Unit (brain):** router parsing, escalation decision, and tool dispatch
  against recorded transcripts — the brain is headless and deterministic given
  text input.
- **Integration:** drive the WS protocol with a mock face client (scripted
  `ptt`/`audio`/`frame`, assert `state`/`tts_audio`/`caption`).
- **Manual on-device:** end-to-end audio/camera latency and quality.

## 13. Out of scope (YAGNI for v1)

- Always-on wake word (v2).
- On-device vision model (use cloud).
- Far-field beamforming / DSP / AEC tuning.
- Barge-in / speech interruption.
- 3D-printed case (upstream's hardware files).
