# Plan 3 — Portal Agent WebView Face (reactive orb)

## Context

The headless brain (Plan 2) is merged and verified on-device (`SMOKE OK`): it
listens on `ws://127.0.0.1:8765`, takes a spoken utterance, routes it through the
on-device SLM (escalating to Claude), and returns spoken audio. But it has **no
face** — today you talk to it only via a scripted smoke client.

Plan 3 builds the **WebView face**: the thing you actually look at and talk to on
the Portal's 800×1280 touchscreen. It captures your voice, plays the brain's
reply through the speakers, and shows a **minimal reactive orb** that changes per
state and pulses to audio. This is the final leg to a usable appliance — walk up,
tap, talk, hear it answer — all on the Portal's own hardware.

The face is **decoupled from the brain by the WebSocket contract** (authored in
`brain/server.py`) and ships as a self-contained static web app served locally on
the device. The only brain-side work is one small change — restoring the
`request_frame` round-trip so the camera can be **on-demand** (see "Brain change").

## Protocol (from `brain/server.py`)

`ws://127.0.0.1:8765`, JSON text frames, binary payloads are base64 in JSON.

| Direction | Message | Notes |
|-----------|---------|-------|
| face → brain | `{"type":"ptt","state":"start"}` | user began talking |
| face → brain | `{"type":"audio","data":"<b64 WAV>"}` | **16k mono 16-bit WAV** (brain passes RIFF straight to whisper) |
| brain → face | `{"type":"request_frame"}` | brain needs a camera frame **now** (SLM picked `capture_image`) |
| face → brain | `{"type":"frame","data":"<b64 JPEG>"}` | **only in response** to `request_frame` |
| brain → face | `{"type":"state","value":"idle\|listening\|thinking\|speaking\|error"}` | drive the orb |
| brain → face | `{"type":"caption","text":"..."}` | show on screen |
| brain → face | `{"type":"tts_audio","data":"<b64 MP3>"}` | **MP3** (`eleven_turbo_v2_5`, mp3_44100_128) — play + analyse |

**Camera is on-demand only** (privacy + power): the face keeps the camera OFF until
it receives `request_frame`, then briefly activates it, grabs ONE frame, sends it,
and releases it. This requires restoring the `request_frame` round-trip in the brain
(Plan 2 used a passive `last_frame`; see "Brain change" below).

## Design

**Visual (single orb, Canvas 2D), per state:**
- `idle` — slow breathing pulse, cool dim cyan; faint "tap to talk" hint.
- `listening` — brighter teal/green; **radius + ripple driven by live mic level**
  (WebAudio analyser on the capture stream).
- `thinking` — amber/violet rotating gradient ring, indeterminate motion.
- `speaking` — warm violet; **pulses to the TTS audio amplitude** (analyser on the
  decoded MP3 playback).
- `error` — red flash + brief shake, then back to idle.

**Interaction (tap-to-toggle, v1):**
- First tap (idle): resume `AudioContext` (Phase 0 gotcha), start mic capture,
  show `listening` locally (immediate), send `ptt:start`.
- Second tap: stop capture, encode WAV, send `audio`. Brain then drives
  `thinking → speaking → idle`. Taps ignored while thinking/speaking (barge-in is v2).

**Audio capture → WAV:** `getUserMedia({audio})` → `AudioContext` → capture Float32
PCM (AudioWorklet, ScriptProcessorNode fallback) → **downsample to 16 kHz mono** →
encode **16-bit PCM WAV** (RIFF) → base64. (This is the one bug-prone, silently-
failing piece → unit-tested.)

**TTS playback → orb:** base64 → bytes → `decodeAudioData(mp3)` →
`AudioBufferSourceNode` → analyser → destination. Analyser amplitude drives the
`speaking` orb; `onended` returns to idle locally (brain also sends idle).

**On-demand camera:** the camera stays OFF. On `request_frame`, the face calls
`getUserMedia({video})`, waits one frame, draws to a canvas →
`toBlob('image/jpeg', ~0.6)` downscaled (~320×240) → base64 → sends `frame`, then
**stops all video tracks** (camera + indicator off). Graceful if denied/timeout
(brain proceeds with "I couldn't get a picture"). A brief on-screen "👁 looking…"
hint shows while the camera is momentarily active.

**Connection:** open WS on load; on close, show a reconnecting indicator and retry
with backoff (the brain may restart). Set `idle` on open.

**Hosting:** served on-device by `python -m http.server --bind 127.0.0.1 8088
--directory face` — `127.0.0.1` is a secure context (getUserMedia allowed) and can
reach `ws://127.0.0.1:8765`. Fully Kiosk loads `http://127.0.0.1:8088/`.

## Brain change (on-demand vision round-trip)

Plan 2's `capture_image` used a passive `sess.last_frame`. To make the camera
on-demand, restore the spec's `request_frame` round-trip — a small, contained change
to `brain/` (keeps the orchestrator pure, IO at the edges):

- `brain/agent.py`: `Conversation.respond()` returns a `FrameRequest(query)` sentinel
  for `capture_image` instead of calling vision inline; add `describe(jpeg, query)`
  that wraps `self.vision`. `respond` stays sync and unit-testable.
- `brain/server.py`: when `respond()` yields a `FrameRequest`, send `request_frame`,
  `await` the face's `frame` (an `asyncio.Future` resolved by the `frame` handler,
  ~5 s timeout → `None`), then call `conv.describe(jpeg, query)` for the final reply.
  Dispatch each **audio turn as a task** so the connection read-loop stays live to
  receive the requested `frame` while the turn awaits it (tap-to-talk serializes
  turns, so no overlap in practice). `ptt`/`frame` stay handled inline.
- Update `tests/test_agent.py` (capture_image now returns `FrameRequest`; add a
  `describe` test) and `tests/test_server.py` (new request_frame→frame→vision flow
  with a mock face). Drop the old passive-`last_frame` assertion.

This re-aligns the implementation with the design spec (§4–5), which already
specified `request_frame`.

## Files to create

```
face/
  index.html      # fullscreen dark layout: <canvas> orb + caption + tap layer
  style.css       # portrait 800x1280, no-scroll, dark
  app.js          # wiring: tap handling, state machine, orchestration (ES module)
  ws.js           # WebSocket client + protocol encode/decode + reconnect
  orb.js          # Canvas renderer; setState(state); feed(level) for reactivity
  audio.js        # mic capture, playback; uses wav.js
  wav.js          # PURE: downsample(float32,srcRate,dstRate), encodeWav16(float32,rate)
  wav.test.mjs    # node:test units for wav.js (no deps)
scripts/
  run-face.sh     # serve face/ on 127.0.0.1:8088 (Termux)
```

Reuse: protocol/states from `brain/server.py` + `brain/states.py`; `run-brain.sh`
pattern for `run-face.sh`; Phase 0 findings in
`docs/superpowers/specs/2026-06-05-portal-agent-design.md` (Fully Kiosk grants
CAMERA+RECORD_AUDIO then restart to ungrey mic; resume AudioContext on tap;
getUserMedia works on the device WebView; localhost WS works).

## Implementation outline (TDD where it pays)

0. **Brain: on-demand vision** (Python, TDD) — `FrameRequest` sentinel +
   `Conversation.describe()` in `brain/agent.py`; `request_frame`→`frame` round-trip
   + per-turn task dispatch in `brain/server.py`; update `tests/test_agent.py` and
   `tests/test_server.py`. Full `pytest` green before touching the face.
1. `face/wav.js` + `wav.test.mjs` — `downsample` (48k→16k) and `encodeWav16`
   (correct RIFF/WAVE header, 16-bit LE PCM). Verify with `node --test`: known
   sample-count math, header magic bytes (`RIFF`/`WAVE`/`fmt `/`data`), 16k rate
   field, byte length.
2. `face/orb.js` — Canvas render loop; `setState(state)`; `feed(level)` for
   mic/tts reactivity. Pure rendering, no network.
3. `face/ws.js` — connect, `onMessage(handler)`, `sendPtt()`, `sendAudio(wavBytes)`,
   `sendFrame(jpegBytes)`, reconnect-with-backoff.
4. `face/audio.js` — `startCapture()` (returns a live mic-level callback + a
   `stop()` that yields a 16k WAV Uint8Array via `wav.js`); `play(mp3Bytes, onLevel,
   onEnded)`; `captureFrame()` (on-demand: open camera → grab one JPEG → **release
   all video tracks** → return bytes).
5. `face/app.js` + `index.html` + `style.css` — tap-to-toggle state machine; route
   brain `state`/`caption`/`tts_audio` to orb + caption + playback; on
   `request_frame`, call `captureFrame()` and reply with `frame`.
6. `scripts/run-face.sh` — `python -m http.server --bind 127.0.0.1 8088 --directory
   "$(dirname "$0")/../face"`.

## Verification

**Unit (host, no deps):** `node --test face/wav.test.mjs` — downsample length +
WAV header/format correctness (the silent-failure risk for whisper).

**On-device end-to-end (mirrors the Plan 2 smoke, but human-in-the-loop):**
1. Start the brain: `bash scripts/run-brain.sh` (keys exported).
2. Serve the face: `bash scripts/run-face.sh` (Termux, background).
3. Point Fully Kiosk at it: `adb shell am start -a android.intent.action.VIEW -d
   "http://127.0.0.1:8088/" -p de.ozerov.fully` (Fully closed elsewhere to save RAM
   only if needed; the face itself is light).
4. On the Portal: orb shows `idle`. Tap → orb reacts to your voice (`listening`).
   Tap again → `thinking` → **hear the reply through the speakers** while the orb
   pulses (`speaking`) → `idle`. Caption shows the text.
5. Confirm the **camera is OFF at rest** (no indicator). Say "what do you see" →
   the camera activates *briefly* (indicator blips, "👁 looking…" hint), one frame
   is captured, vision answers, camera goes OFF again.
6. Watch `~/brain-errors.log` for any turn errors.

**Memory note:** the face is light, but keep an eye on RAM — gemma (`--no-mmap`) +
whisper + WebView. If pressure appears, the Phase-0 levers apply (tiny.en,
`-c 1024`).

## Out of scope (v2)

- Always-on wake word (OpenWakeWord on the captured stream) — replaces tap-trigger.
- Barge-in / interrupt while speaking.
- On-device vision model (currently cloud via Claude).
- Autostart/keep-alive (Termux:Boot, Fully Kiosk auto-launch) — that's Plan 4.

## After approval

Land on a `plan3-face` branch; also copy this plan to
`docs/superpowers/plans/2026-06-11-portal-agent-plan3-face.md` for repo history,
then implement the outline (TDD for `wav.js`, on-device E2E for the rest).
