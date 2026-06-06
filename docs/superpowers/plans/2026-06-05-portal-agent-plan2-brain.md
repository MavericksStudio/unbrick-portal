# Portal Agent — Plan 2: Headless Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the headless `brain/` package: a WebSocket server that takes an audio utterance from the face, transcribes it locally, routes it through the on-device SLM (answer | tool | escalate-to-Claude), and returns spoken audio + state — all unit-tested on the Mac, then smoke-tested on the device.

**Architecture:** A `brain/` Python package of small, single-responsibility modules wired by an async WebSocket server. The orchestrator (`Conversation`) is pure given injected IO collaborators (local LLM, Claude, tools, STT, TTS), so the whole turn logic is unit-testable without the device or network. Device/network edges (llama.cpp HTTP, whisper.cpp subprocess, cloud TTS, Anthropic SDK) are thin, separately-tested adapters.

**Tech Stack:** Python 3.10+, `websockets`, `requests`, `anthropic`, `duckduckgo-search`, `pytest`, `pytest-asyncio`. Local SLM served by `llama-server` (`--no-mmap`). STT by `whisper.cpp`. TTS by Google Cloud TTS REST.

**Spec:** `docs/superpowers/specs/2026-06-05-portal-agent-design.md` (Phase 0 = GO).

**v1 scope decisions:**
- Tap-to-talk sends ONE complete audio blob on `ptt:stop` (no live streaming; that lands with v2 wake word).
- Vision uses cloud on a single captured frame; local `moondream` deferred.
- `llama-server` MUST be launched with `--no-mmap` (Phase 0 finding).

**Module map (`brain/`):**

| File | Responsibility |
|------|----------------|
| `brain/states.py` | `State` enum (idle/listening/thinking/speaking/error) |
| `brain/config.py` | Load/validate `brain.json` config |
| `brain/router.py` | `Action` type, `parse_action()`, `build_messages()`, system prompt |
| `brain/tools.py` | `get_time`, `search_web`; dispatch by action |
| `brain/llm.py` | Local SLM client (llama-server OpenAI HTTP) |
| `brain/escalate.py` | Claude (Anthropic) client |
| `brain/stt.py` | whisper.cpp subprocess wrapper |
| `brain/tts.py` | Google Cloud TTS REST client |
| `brain/memory.py` | Chat history load/append/save |
| `brain/agent.py` | `Conversation` orchestrator (pure given deps) |
| `brain/server.py` | WebSocket server (protocol ↔ orchestrator) |
| `brain/__main__.py` | Entry point |
| `scripts/run-brain.sh` | Launch llama-server (`--no-mmap`) + brain |

---

## Task 1: Brain package scaffold + test harness

**Files:**
- Create: `brain/__init__.py`
- Create: `requirements-brain.txt`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Create the package and dependency files**

```bash
cd ~/portal-agent
mkdir -p brain tests scripts
: > brain/__init__.py
: > tests/__init__.py
```

```text
# requirements-brain.txt
websockets==12.0
requests==2.32.3
anthropic==0.55.1
duckduckgo-search==6.3.5
pytest==8.3.3
pytest-asyncio==0.24.0
```

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 2: Write a smoke test**

```python
# tests/test_smoke.py
import brain

def test_package_imports():
    assert brain is not None
```

- [ ] **Step 3: Create venv and install deps**

```bash
cd ~/portal-agent
python3 -m venv .venv-brain
. .venv-brain/bin/activate
pip install -q -r requirements-brain.txt
```

Expected: installs without error.

- [ ] **Step 4: Run the smoke test**

Run: `. .venv-brain/bin/activate && pytest tests/test_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd ~/portal-agent
echo '.venv-brain/' >> .gitignore
git add brain tests pytest.ini requirements-brain.txt .gitignore
git commit -m "feat(brain): scaffold brain package and pytest harness"
```

---

## Task 2: State enum

**Files:**
- Create: `brain/states.py`
- Create: `tests/test_states.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_states.py
from brain.states import State

def test_states_have_wire_values():
    assert State.IDLE.value == "idle"
    assert State.LISTENING.value == "listening"
    assert State.THINKING.value == "thinking"
    assert State.SPEAKING.value == "speaking"
    assert State.ERROR.value == "error"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_states.py -v`
Expected: FAIL (no module `brain.states`).

- [ ] **Step 3: Implement**

```python
# brain/states.py
from enum import Enum

class State(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_states.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add brain/states.py tests/test_states.py
git commit -m "feat(brain): add State enum with wire values"
```

---

## Task 3: Config loader

**Files:**
- Create: `brain/config.py`
- Create: `brain.example.json`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import json, pytest
from brain.config import load_config, Config

def test_load_defaults(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({}))
    c = load_config(str(p))
    assert isinstance(c, Config)
    assert c.llm_base_url == "http://127.0.0.1:8080"
    assert c.ws_host == "127.0.0.1"
    assert c.ws_port == 8765
    assert c.claude_model == "claude-opus-4-8"
    assert c.no_mmap is True

def test_overrides(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({"ws_port": 9000, "claude_model": "claude-sonnet-4-6"}))
    c = load_config(str(p))
    assert c.ws_port == 9000
    assert c.claude_model == "claude-sonnet-4-6"

def test_missing_file_uses_defaults():
    c = load_config("/nonexistent/brain.json")
    assert c.ws_port == 8765
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (no module `brain.config`).

- [ ] **Step 3: Implement**

```python
# brain/config.py
import json, os
from dataclasses import dataclass, asdict

@dataclass
class Config:
    # local SLM (llama-server, OpenAI-compatible)
    llm_base_url: str = "http://127.0.0.1:8080"
    llm_model: str = "gemma-3-1b-it"        # label only; server hosts one model
    no_mmap: bool = True                     # Phase 0: REQUIRED on device
    # websocket
    ws_host: str = "127.0.0.1"
    ws_port: int = 8765
    # escalation
    claude_model: str = "claude-opus-4-8"
    # stt
    whisper_bin: str = "whisper-cli"
    whisper_model: str = "ggml-base.en.bin"
    # tts (Google Cloud TTS REST)
    tts_voice: str = "en-GB-Standard-B"
    tts_lang: str = "en-GB"
    # memory
    memory_path: str = "chat_memory.json"
    memory_enabled: bool = True
    # persona appended to the router system prompt
    system_prompt_extras: str = ""

def load_config(path: str = "brain.json") -> "Config":
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)

def write_example(path: str) -> None:
    with open(path, "w") as f:
        json.dump(asdict(Config()), f, indent=2)
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Generate the example config and commit**

```bash
cd ~/portal-agent
. .venv-brain/bin/activate
python -c "from brain.config import write_example; write_example('brain.example.json')"
git add brain/config.py brain.example.json tests/test_config.py
git commit -m "feat(brain): add Config loader with device-safe defaults"
```

---

## Task 4: Router — action parsing, messages, system prompt

**Files:**
- Create: `brain/router.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_router.py
from brain.router import parse_action, build_messages, Action, SYSTEM_PROMPT

def test_parse_plain_text_is_none():
    assert parse_action("It is sunny today.") is None

def test_parse_clean_json():
    a = parse_action('{"action":"get_time"}')
    assert a == Action(name="get_time", args={})

def test_parse_json_embedded_in_prose():
    a = parse_action('Sure! {"action":"search_web","query":"mars news"} ok')
    assert a == Action(name="search_web", args={"query": "mars news"})

def test_parse_escalate():
    a = parse_action('{"action":"escalate","query":"prove sqrt(2) irrational"}')
    assert a.name == "escalate"
    assert a.args["query"].startswith("prove")

def test_parse_malformed_json_is_none():
    assert parse_action('{"action": ') is None

def test_build_messages_includes_system_and_history():
    msgs = build_messages([{"role": "user", "content": "hi"},
                           {"role": "assistant", "content": "hello"}],
                          "what time is it", extras="Be terse.")
    assert msgs[0]["role"] == "system"
    assert "escalate" in msgs[0]["content"]
    assert "Be terse." in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "what time is it"}
    assert {"role": "assistant", "content": "hello"} in msgs
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_router.py -v`
Expected: FAIL (no module `brain.router`).

- [ ] **Step 3: Implement**

```python
# brain/router.py
import json, re
from dataclasses import dataclass, field

@dataclass
class Action:
    name: str
    args: dict = field(default_factory=dict)

SYSTEM_PROMPT = (
    "You are the on-device brain of a Portal voice assistant. You are fast but "
    "small, so you ROUTE hard work to a bigger model.\n"
    "Reply with EXACTLY ONE JSON object when an action is needed, otherwise reply "
    "with a short spoken answer in plain text.\n\n"
    "Actions:\n"
    '1. Time: {"action":"get_time"}\n'
    '2. Web search (current events / facts you are unsure of): '
    '{"action":"search_web","query":"..."}\n'
    '3. See (camera): {"action":"capture_image"}\n'
    '4. Escalate to the big model (deep reasoning, math, coding, multi-step '
    'logic, anything you are not confident about): '
    '{"action":"escalate","query":"<restate the user request>"}\n\n'
    "If a simple greeting or trivial fact, answer directly in one or two "
    "sentences. When unsure, prefer escalate. Output ONLY the JSON for actions, "
    "with no extra words."
)

# greedy-but-safe: find the first balanced {...} that parses as JSON with "action"
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

def parse_action(text: str):
    if not text:
        return None
    m = _JSON_RE.search(text)
    if not m:
        return None
    blob = m.group(0)
    # try progressively shorter prefixes ending in '}' to tolerate trailing prose
    for end in range(len(blob), 0, -1):
        if blob[end - 1] != "}":
            continue
        try:
            data = json.loads(blob[:end])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "action" in data:
            name = data.pop("action")
            return Action(name=name, args={k: v for k, v in data.items()})
    return None

def build_messages(history, user_text, extras=""):
    system = SYSTEM_PROMPT + (("\n\n" + extras) if extras else "")
    msgs = [{"role": "system", "content": system}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": user_text})
    return msgs
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_router.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/router.py tests/test_router.py
git commit -m "feat(brain): add router (action parsing, system prompt, messages)"
```

---

## Task 5: Tools — time and web search

**Files:**
- Create: `brain/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py
from brain.router import Action
from brain import tools

def test_get_time_format(monkeypatch):
    out = tools.run(Action("get_time"), search=lambda q, n=3: [])
    # Should be a spoken time string, not JSON
    assert "{" not in out
    assert ":" in out or "o'clock" in out.lower()

def test_search_web_summarizes(monkeypatch):
    fake = [{"title": "Mars", "body": "Water found on Mars."},
            {"title": "More", "body": "Rover update."}]
    out = tools.run(Action("search_web", {"query": "mars"}), search=lambda q, n=3: fake)
    assert "Water found on Mars" in out

def test_unknown_action():
    out = tools.run(Action("nope"), search=lambda q, n=3: [])
    assert "don't know" in out.lower() or "unknown" in out.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL (no module `brain.tools`).

- [ ] **Step 3: Implement**

```python
# brain/tools.py
import datetime

def default_search(query, n=3):
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=n))

def run(action, search=default_search) -> str:
    """Execute a non-escalate, non-capture tool action; return spoken text."""
    if action.name == "get_time":
        now = datetime.datetime.now()
        return "It is " + now.strftime("%-I:%M %p")
    if action.name == "search_web":
        results = search(action.args.get("query", ""), n=3)
        if not results:
            return "I couldn't find anything on that."
        bodies = [r.get("body", "") for r in results if r.get("body")]
        return " ".join(bodies[:2]) or "I found something but couldn't read it."
    return f"I don't know how to do '{action.name}'."
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/tools.py tests/test_tools.py
git commit -m "feat(brain): add tool dispatch (get_time, search_web)"
```

---

## Task 6: Local SLM client (llama-server HTTP)

**Files:**
- Create: `brain/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
from brain.llm import LocalLLM

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_complete_posts_and_extracts(monkeypatch):
    captured = {}
    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp({"choices": [{"message": {"content": '{"action":"get_time"}'}}]})
    import brain.llm as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    llm = LocalLLM("http://127.0.0.1:8080")
    out = llm.complete([{"role": "user", "content": "time?"}])
    assert out == '{"action":"get_time"}'
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["json"]["messages"][0]["content"] == "time?"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL (no module `brain.llm`).

- [ ] **Step 3: Implement**

```python
# brain/llm.py
import requests

class LocalLLM:
    def __init__(self, base_url, temperature=0.3, max_tokens=256, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def complete(self, messages) -> str:
        r = requests.post(
            self.base_url + "/v1/chat/completions",
            json={
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_llm.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/llm.py tests/test_llm.py
git commit -m "feat(brain): add local SLM client (llama-server HTTP)"
```

---

## Task 7: Escalation client (Claude)

**Files:**
- Create: `brain/escalate.py`
- Create: `tests/test_escalate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_escalate.py
from brain.escalate import Escalator

class FakeMessages:
    def create(self, **kw):
        self.kw = kw
        class R: content = [type("B", (), {"text": "Because 2 has no integer root."})()]
        return R()

class FakeClient:
    def __init__(self): self.messages = FakeMessages()

def test_escalate_returns_text():
    esc = Escalator(client=FakeClient(), model="claude-opus-4-8")
    out = esc.ask("why is sqrt(2) irrational")
    assert "integer root" in out

def test_escalate_passes_model():
    fc = FakeClient()
    esc = Escalator(client=fc, model="claude-sonnet-4-6")
    esc.ask("hi")
    assert fc.messages.kw["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_escalate.py -v`
Expected: FAIL (no module `brain.escalate`).

- [ ] **Step 3: Implement**

```python
# brain/escalate.py
import os

SYSTEM = ("You are the deep-reasoning brain behind a small voice assistant. "
          "Answer correctly and concisely for speech: 1-4 short sentences, no "
          "markdown, no lists unless asked.")

class Escalator:
    def __init__(self, client=None, model="claude-opus-4-8", max_tokens=400):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def ask(self, query) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": query}],
        )
        return "".join(getattr(b, "text", "") for b in resp.content).strip()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_escalate.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/escalate.py tests/test_escalate.py
git commit -m "feat(brain): add Claude escalation client"
```

---

## Task 8: STT (whisper.cpp subprocess)

**Files:**
- Create: `brain/stt.py`
- Create: `tests/test_stt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stt.py
from brain.stt import WhisperSTT

def test_transcribe_invokes_binary_and_cleans(monkeypatch, tmp_path):
    calls = {}
    def fake_run(cmd, capture_output, text, timeout):
        calls["cmd"] = cmd
        class R: stdout = "\n[00:00:00.000 --> 00:00:02.000]   Hello there.\n"; returncode = 0
        return R()
    import brain.stt as m
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    wav = tmp_path / "in.wav"; wav.write_bytes(b"RIFF")
    stt = WhisperSTT(binary="whisper-cli", model="ggml-base.en.bin")
    text = stt.transcribe(str(wav))
    assert text == "Hello there."
    assert "whisper-cli" in calls["cmd"][0]
    assert str(wav) in calls["cmd"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_stt.py -v`
Expected: FAIL (no module `brain.stt`).

- [ ] **Step 3: Implement**

```python
# brain/stt.py
import subprocess, re

_TS = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]")

class WhisperSTT:
    def __init__(self, binary="whisper-cli", model="ggml-base.en.bin",
                 lang="en", threads=4, timeout=120):
        self.binary, self.model = binary, model
        self.lang, self.threads, self.timeout = lang, threads, timeout

    def transcribe(self, wav_path) -> str:
        cmd = [self.binary, "-m", self.model, "-l", self.lang,
               "-t", str(self.threads), "-nt", "-f", wav_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        lines = []
        for line in r.stdout.splitlines():
            line = _TS.sub("", line).strip()
            if line:
                lines.append(line)
        return " ".join(lines).strip()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_stt.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/stt.py tests/test_stt.py
git commit -m "feat(brain): add whisper.cpp STT wrapper"
```

---

## Task 9: TTS (Google Cloud TTS REST)

**Files:**
- Create: `brain/tts.py`
- Create: `tests/test_tts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tts.py
import base64
from brain.tts import GoogleTTS

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_synthesize_returns_audio_bytes(monkeypatch):
    audio = b"FAKEWAVDATA"
    def fake_post(url, params=None, json=None, timeout=None):
        assert "text-to-speech" in url
        assert json["input"]["text"] == "hello"
        return FakeResp({"audioContent": base64.b64encode(audio).decode()})
    import brain.tts as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    tts = GoogleTTS(api_key="k", voice="en-GB-Standard-B", lang="en-GB")
    out = tts.synthesize("hello")
    assert out == audio
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_tts.py -v`
Expected: FAIL (no module `brain.tts`).

- [ ] **Step 3: Implement**

```python
# brain/tts.py
import base64, os, requests

class GoogleTTS:
    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def __init__(self, api_key=None, voice="en-GB-Standard-B", lang="en-GB",
                 encoding="LINEAR16", timeout=30):
        self.api_key = api_key or os.environ.get("GOOGLE_TTS_API_KEY")
        self.voice, self.lang, self.encoding, self.timeout = voice, lang, encoding, timeout

    def synthesize(self, text) -> bytes:
        r = requests.post(
            self.URL,
            params={"key": self.api_key},
            json={
                "input": {"text": text},
                "voice": {"languageCode": self.lang, "name": self.voice},
                "audioConfig": {"audioEncoding": self.encoding},
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"])
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_tts.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/tts.py tests/test_tts.py
git commit -m "feat(brain): add Google Cloud TTS REST client"
```

---

## Task 10: Chat memory

**Files:**
- Create: `brain/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory.py
from brain.memory import History

def test_append_and_persist(tmp_path):
    p = tmp_path / "mem.json"
    h = History(str(p), enabled=True, max_turns=2)
    h.add("user", "hi"); h.add("assistant", "hello")
    h.add("user", "bye"); h.add("assistant", "later")
    msgs = h.messages()
    # max_turns=2 keeps last 2 user+assistant pairs == 4 messages
    assert len(msgs) == 4
    assert msgs[0]["content"] == "hi" or msgs[-1]["content"] == "later"
    h2 = History(str(p), enabled=True, max_turns=2)
    assert h2.messages()[-1]["content"] == "later"

def test_disabled_keeps_nothing(tmp_path):
    h = History(str(tmp_path / "m.json"), enabled=False)
    h.add("user", "hi")
    assert h.messages() == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL (no module `brain.memory`).

- [ ] **Step 3: Implement**

```python
# brain/memory.py
import json, os

class History:
    def __init__(self, path, enabled=True, max_turns=8):
        self.path, self.enabled, self.max_turns = path, enabled, max_turns
        self._msgs = []
        if enabled and os.path.exists(path):
            try:
                with open(path) as f:
                    self._msgs = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._msgs = []

    def add(self, role, content):
        if not self.enabled:
            return
        self._msgs.append({"role": role, "content": content})
        self._msgs = self._msgs[-self.max_turns * 2:]
        self._save()

    def messages(self):
        return list(self._msgs) if self.enabled else []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._msgs, f)
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_memory.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/memory.py tests/test_memory.py
git commit -m "feat(brain): add chat history memory"
```

---

## Task 11: Conversation orchestrator

**Files:**
- Create: `brain/agent.py`
- Create: `tests/test_agent.py`

The orchestrator is pure given injected collaborators. `respond()` returns a
`Reply(text, used_escalation, used_tool)`. `capture_image` is handled via an
injected `frame_provider()` returning JPEG bytes (or `None`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
from brain.agent import Conversation, Reply
from brain.memory import History

def mk(tmp_path, llm_reply, escalate_reply="ESCALATED", search=None, vision=None):
    class LLM:
        def complete(self, messages): return llm_reply
    class Esc:
        def ask(self, q): return escalate_reply
    hist = History(str(tmp_path / "m.json"), enabled=True)
    return Conversation(
        llm=LLM(), escalator=Esc(), history=hist,
        search=search or (lambda q, n=3: [{"body": "Mars has water."}]),
        vision=vision or (lambda jpeg, q: "I see a desk."),
        extras="",
    )

def test_plain_answer_passthrough(tmp_path):
    c = mk(tmp_path, "Hello there!")
    r = c.respond("hi", frame_provider=lambda: None)
    assert isinstance(r, Reply)
    assert r.text == "Hello there!"
    assert not r.used_escalation

def test_get_time_tool(tmp_path):
    c = mk(tmp_path, '{"action":"get_time"}')
    r = c.respond("what time", frame_provider=lambda: None)
    assert ":" in r.text and r.used_tool

def test_search_tool(tmp_path):
    c = mk(tmp_path, '{"action":"search_web","query":"mars"}')
    r = c.respond("mars news", frame_provider=lambda: None)
    assert "Mars has water" in r.text

def test_escalate(tmp_path):
    c = mk(tmp_path, '{"action":"escalate","query":"hard q"}', escalate_reply="42")
    r = c.respond("hard q", frame_provider=lambda: None)
    assert r.text == "42" and r.used_escalation

def test_capture_image_uses_vision_and_frame(tmp_path):
    c = mk(tmp_path, '{"action":"capture_image"}', vision=lambda jpeg, q: "A cat.")
    r = c.respond("what do you see", frame_provider=lambda: b"JPEGBYTES")
    assert r.text == "A cat."

def test_history_records_turn(tmp_path):
    c = mk(tmp_path, "Hi!")
    c.respond("hello", frame_provider=lambda: None)
    roles = [m["role"] for m in c.history.messages()]
    assert roles == ["user", "assistant"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL (no module `brain.agent`).

- [ ] **Step 3: Implement**

```python
# brain/agent.py
from dataclasses import dataclass
from brain.router import parse_action, build_messages
from brain import tools

@dataclass
class Reply:
    text: str
    used_escalation: bool = False
    used_tool: bool = False

class Conversation:
    def __init__(self, llm, escalator, history, search=tools.default_search,
                 vision=None, extras=""):
        self.llm = llm
        self.escalator = escalator
        self.history = history
        self.search = search
        self.vision = vision  # callable(jpeg_bytes, query) -> str
        self.extras = extras

    def respond(self, user_text, frame_provider) -> Reply:
        messages = build_messages(self.history.messages(), user_text, self.extras)
        raw = self.llm.complete(messages)
        action = parse_action(raw)

        if action is None:
            reply = Reply(text=raw)
        elif action.name == "escalate":
            reply = Reply(text=self.escalator.ask(action.args.get("query", user_text)),
                          used_escalation=True)
        elif action.name == "capture_image":
            jpeg = frame_provider()
            if jpeg and self.vision:
                reply = Reply(text=self.vision(jpeg, user_text), used_tool=True)
            else:
                reply = Reply(text="I couldn't get a picture.", used_tool=True)
        else:
            reply = Reply(text=tools.run(action, search=self.search), used_tool=True)

        self.history.add("user", user_text)
        self.history.add("assistant", reply.text)
        return reply
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add brain/agent.py tests/test_agent.py
git commit -m "feat(brain): add Conversation orchestrator (route/tool/escalate)"
```

---

## Task 12: WebSocket server

Protocol (JSON text frames; audio/frame payloads are base64 in JSON for v1
simplicity). face→brain: `ptt`, `audio`, `frame`. brain→face: `state`,
`request_frame`, `tts_audio`, `caption`.

**Files:**
- Create: `brain/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing test (drives the handler with a fake socket)**

```python
# tests/test_server.py
import json, base64, asyncio, pytest
from brain.server import handle_message, Session
from brain.agent import Reply
from brain.states import State

class FakeWS:
    def __init__(self): self.sent = []
    async def send(self, msg): self.sent.append(json.loads(msg))

class FakeConv:
    def __init__(self): self.history = type("H", (), {"messages": lambda s: []})()
    def respond(self, text, frame_provider):
        frame_provider()  # exercise the path
        return Reply(text="hi back")

async def test_audio_runs_turn_and_emits_states(monkeypatch):
    ws = FakeWS()
    sess = Session(ws, conv=FakeConv(),
                   transcribe=lambda wav: "hello",
                   synthesize=lambda text: b"AUDIO",
                   to_wav=lambda blob: "/tmp/x.wav")
    await handle_message(sess, json.dumps({"type": "ptt", "state": "start"}))
    await handle_message(sess, json.dumps(
        {"type": "audio", "data": base64.b64encode(b"webm").decode()}))
    types = [m["type"] for m in ws.sent]
    assert "state" in types
    states = [m["value"] for m in ws.sent if m["type"] == "state"]
    assert State.THINKING.value in states
    assert State.SPEAKING.value in states
    assert State.IDLE.value in states
    assert any(m["type"] == "caption" and m["text"] == "hi back" for m in ws.sent)
    assert any(m["type"] == "tts_audio" for m in ws.sent)

async def test_frame_message_resolves_provider():
    ws = FakeWS()
    sess = Session(ws, conv=FakeConv(),
                   transcribe=lambda wav: "x", synthesize=lambda t: b"A",
                   to_wav=lambda b: "/tmp/x.wav")
    # deliver a frame, then ensure it is stored for the provider
    await handle_message(sess, json.dumps(
        {"type": "frame", "data": base64.b64encode(b"JPEG").decode()}))
    assert sess.last_frame == b"JPEG"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_server.py -v`
Expected: FAIL (no module `brain.server`).

- [ ] **Step 3: Implement**

```python
# brain/server.py
import asyncio, base64, json, os, subprocess, tempfile
import websockets
from brain.states import State

def webm_to_wav(blob: bytes) -> str:
    """Convert a browser audio blob to 16k mono WAV for whisper via ffmpeg."""
    src = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    src.write(blob); src.close()
    dst = src.name + ".wav"
    subprocess.run(["ffmpeg", "-y", "-i", src.name, "-ar", "16000", "-ac", "1", dst],
                   capture_output=True, timeout=60)
    os.unlink(src.name)
    return dst

class Session:
    def __init__(self, ws, conv, transcribe, synthesize, to_wav=webm_to_wav):
        self.ws = ws
        self.conv = conv
        self.transcribe = transcribe
        self.synthesize = synthesize
        self.to_wav = to_wav
        self.last_frame = None

    async def send(self, **obj):
        await self.ws.send(json.dumps(obj))

    async def set_state(self, state: State):
        await self.send(type="state", value=state.value)

    def _frame_provider(self):
        # v1: use the most recent frame the face already pushed (face sends a
        # frame on connect / periodically). Returns bytes or None.
        return self.last_frame

async def handle_message(sess: Session, raw: str):
    msg = json.loads(raw)
    t = msg.get("type")
    if t == "ptt":
        if msg.get("state") == "start":
            await sess.set_state(State.LISTENING)
        return
    if t == "frame":
        sess.last_frame = base64.b64decode(msg["data"])
        return
    if t == "audio":
        blob = base64.b64decode(msg["data"])
        await sess.set_state(State.THINKING)
        try:
            wav = sess.to_wav(blob)
            text = sess.transcribe(wav)
            reply = sess.conv.respond(text, frame_provider=sess._frame_provider)
            await sess.send(type="caption", text=reply.text)
            await sess.set_state(State.SPEAKING)
            audio = sess.synthesize(reply.text)
            await sess.send(type="tts_audio",
                            data=base64.b64encode(audio).decode())
        except Exception as e:  # never wedge the face
            await sess.send(type="caption", text="Sorry, something went wrong.")
            await sess.set_state(State.ERROR)
        finally:
            await sess.set_state(State.IDLE)
        return

async def serve(host, port, make_session):
    async def conn(ws):
        sess = make_session(ws)
        await sess.set_state(State.IDLE)
        async for raw in ws:
            await handle_message(sess, raw)
    async with websockets.serve(conn, host, port):
        await asyncio.Future()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_server.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all tests pass (Tasks 1–12).

- [ ] **Step 6: Commit**

```bash
git add brain/server.py tests/test_server.py
git commit -m "feat(brain): add WebSocket server (protocol + turn pipeline)"
```

---

## Task 13: Entry point + run script

**Files:**
- Create: `brain/__main__.py`
- Create: `scripts/run-brain.sh`
- Create: `brain/vision.py`

- [ ] **Step 1: Add a cloud vision helper (used by capture_image)**

```python
# brain/vision.py
import base64

def describe_with_claude(escalator_client, model, jpeg_bytes, query):
    b64 = base64.b64encode(jpeg_bytes).decode()
    resp = escalator_client.messages.create(
        model=model, max_tokens=200,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
             "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": query or "Briefly describe what you see."},
        ]}],
    )
    return "".join(getattr(b, "text", "") for b in resp.content).strip()
```

- [ ] **Step 2: Write the entry point**

```python
# brain/__main__.py
import functools, anthropic
from brain.config import load_config
from brain.llm import LocalLLM
from brain.escalate import Escalator
from brain.stt import WhisperSTT
from brain.tts import GoogleTTS
from brain.memory import History
from brain.agent import Conversation
from brain.tools import default_search
from brain.vision import describe_with_claude
from brain.server import Session, serve
import asyncio

def main():
    cfg = load_config()
    anthropic_client = anthropic.Anthropic()
    llm = LocalLLM(cfg.llm_base_url)
    escalator = Escalator(client=anthropic_client, model=cfg.claude_model)
    stt = WhisperSTT(cfg.whisper_bin, cfg.whisper_model)
    tts = GoogleTTS(voice=cfg.tts_voice, lang=cfg.tts_lang)
    vision = functools.partial(describe_with_claude, anthropic_client, cfg.claude_model)

    def make_session(ws):
        conv = Conversation(
            llm=llm, escalator=escalator,
            history=History(cfg.memory_path, cfg.memory_enabled),
            search=default_search, vision=vision, extras=cfg.system_prompt_extras,
        )
        return Session(ws, conv=conv, transcribe=stt.transcribe,
                       synthesize=tts.synthesize)

    print(f"brain: ws://{cfg.ws_host}:{cfg.ws_port}")
    asyncio.run(serve(cfg.ws_host, cfg.ws_port, make_session))

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the launch script (llama-server with --no-mmap)**

```bash
# scripts/run-brain.sh
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
```

- [ ] **Step 4: Verify the entry point imports cleanly (no network)**

Run: `. .venv-brain/bin/activate && python -c "import brain.__main__; print('ok')"`
Expected: prints `ok` (import side-effect free; `main()` not called).

- [ ] **Step 5: Commit**

```bash
chmod +x scripts/run-brain.sh
git add brain/__main__.py brain/vision.py scripts/run-brain.sh
git commit -m "feat(brain): add entry point, cloud vision, and run-brain.sh"
```

---

## Task 14: On-device integration smoke test

Runs the real brain on the Portal against the real llama-server, with a scripted
WS client standing in for the face. Requires `whisper.cpp` + `ffmpeg` on device
and `ANTHROPIC_API_KEY` / `GOOGLE_TTS_API_KEY` exported in Termux.

**Files:**
- Create: `scripts/smoke_client.py`

- [ ] **Step 1: Install device prerequisites (over ssh)**

```bash
adb forward tcp:8022 tcp:8022
ssh -p 8022 -i ~/.ssh/portal_agent_ed25519 u0_a45@127.0.0.1 \
  'pkg install -y whisper.cpp ffmpeg git && \
   ls $PREFIX/bin/whisper-cli && \
   mkdir -p ~/whisper-models && cd ~/whisper-models && \
   wget -nc https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin && \
   ls -la ggml-base.en.bin'
```

Expected: `whisper-cli` exists and `ggml-base.en.bin` (~140 MB) downloads.
(If `pkg` lacks `whisper.cpp`, build it: `git clone https://github.com/ggerganov/whisper.cpp && cd whisper.cpp && cmake -B build && cmake --build build -j && cp build/bin/whisper-cli $PREFIX/bin/`.)

- [ ] **Step 2: Deploy the brain to the device**

```bash
cd ~/portal-agent
rsync -az -e "ssh -p 8022 -i ~/.ssh/portal_agent_ed25519" \
  brain scripts requirements-brain.txt brain.example.json \
  u0_a45@127.0.0.1:~/portal-agent/
ssh -p 8022 -i ~/.ssh/portal_agent_ed25519 u0_a45@127.0.0.1 \
  'cd ~/portal-agent && cp -n brain.example.json brain.json && \
   pip install -r requirements-brain.txt && \
   sed -i "s|ggml-base.en.bin|$HOME/whisper-models/ggml-base.en.bin|" brain.json'
```

Expected: deps install; `brain.json` created with the absolute whisper model path.

- [ ] **Step 3: Write a scripted WS smoke client**

```python
# scripts/smoke_client.py
import asyncio, base64, json, sys, websockets

async def main(wav_path):
    blob = open(wav_path, "rb").read()
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        await ws.send(json.dumps({"type": "ptt", "state": "start"}))
        await ws.send(json.dumps({"type": "audio",
                                  "data": base64.b64encode(blob).decode()}))
        got_caption = got_audio = False
        for _ in range(20):
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            print("<<", m.get("type"), m.get("value", m.get("text", "")[:60]))
            if m["type"] == "caption": got_caption = True
            if m["type"] == "tts_audio": got_audio = True
            if m["type"] == "state" and m["value"] == "idle" and got_caption:
                break
        assert got_caption and got_audio, "missing caption or audio"
        print("SMOKE OK")

asyncio.run(main(sys.argv[1]))
```

- [ ] **Step 4: Run llama-server + brain on device, fire the smoke client**

```bash
# terminal A (device): start brain stack
ssh -p 8022 -i ~/.ssh/portal_agent_ed25519 u0_a45@127.0.0.1 \
  'cd ~/portal-agent && export ANTHROPIC_API_KEY=... GOOGLE_TTS_API_KEY=... && \
   nohup bash scripts/run-brain.sh >~/brain.log 2>&1 & sleep 25 && tail -5 ~/brain.log'
```

```bash
# terminal B (device): generate a test wav (TTS or `say`-style) and run client
ssh -p 8022 -i ~/.ssh/portal_agent_ed25519 u0_a45@127.0.0.1 \
  'cd ~/portal-agent && \
   ffmpeg -f lavfi -i "sine=frequency=200:duration=1" -ar 16000 -ac 1 /tmp/silence.wav -y 2>/dev/null; \
   python scripts/smoke_client.py /tmp/silence.wav'
```

Expected: the client prints incoming `state`/`caption`/`tts_audio` frames and ends with `SMOKE OK`. (With a real spoken wav, the caption should reflect the words; silence just exercises the pipeline end-to-end.)

- [ ] **Step 5: Record result and commit**

```bash
cd ~/portal-agent
printf 'BRAIN on-device smoke: caption=__ tts_audio=__ %s\n' "$(date)" >> .spike/RESULTS.md
git add scripts/smoke_client.py
git commit -m "test(brain): add on-device integration smoke client"
```

---

## Self-Review

- **Spec coverage:** brain (Termux Python) ✓ Tasks 1–13; llama.cpp `--no-mmap` ✓ Task 13 run script; whisper STT ✓ Task 8/14; cloud TTS ✓ Task 9; `escalate`→Claude ✓ Task 7/11; tools ✓ Task 5; capture_image→cloud vision ✓ Tasks 11/13; memory ✓ Task 10; WS protocol (`state/request_frame/tts_audio/caption` + `ptt/audio/frame`) ✓ Task 12; error handling (never wedge the face, ERROR state) ✓ Task 12; testing strategy (unit + mock-WS + on-device) ✓ throughout.
- **Deferred to Plan 3/4 (face/integration), intentionally:** live `request_frame` round-trip (v1 uses the last pushed frame), autostart/keep-alive, avatar. Noted, not gaps.
- **Type/name consistency:** `Action(name,args)`, `Reply(text,used_escalation,used_tool)`, `Session`, `handle_message`, `State.*` values used identically across tasks.
- **Placeholders:** none — every code step is complete and runnable; `...` appears only where the operator supplies live API keys.

---

## Subsequent plans

- **Plan 3 — WebView Face:** avatar PNG state machine driven by `state`; `getUserMedia` mic (MediaRecorder → blob on `ptt:stop`) + camera frame push; WebAudio playback of `tts_audio`; AudioContext resume-on-tap; Fully Kiosk config.
- **Plan 4 — Integration & Autostart:** Termux:Boot + `termux-wake-lock`, brain supervisor/restart, Fully Kiosk auto-launch + start URL, end-to-end on-device; then the v2 wake-word hook (OpenWakeWord on the audio the face streams).
