import json, base64
from brain.server import handle_message, Session
from brain.agent import Reply
from brain.states import State

class FakeWS:
    def __init__(self): self.sent = []
    async def send(self, msg): self.sent.append(json.loads(msg))

class FakeConv:
    def __init__(self): self.history = type("H", (), {"messages": lambda s: []})()
    def respond(self, text, frame_provider): return Reply(text="ok")

async def test_tts_failure_reports_error_and_recovers(monkeypatch, tmp_path):
    # route the error log to a temp file
    import brain.server as srv
    monkeypatch.setattr(srv, "ERROR_LOG", str(tmp_path / "err.log"))

    def boom(text): raise RuntimeError("tts 401 unauthorized")
    ws = FakeWS()
    sess = Session(ws, conv=FakeConv(), transcribe=lambda w: "hi",
                   synthesize=boom, to_wav=lambda b: "/tmp/x.wav")
    await handle_message(sess, json.dumps(
        {"type": "audio", "data": base64.b64encode(b"RIFF....").decode()}))
    states = [m["value"] for m in ws.sent if m["type"] == "state"]
    assert State.ERROR.value in states
    assert State.IDLE.value in states  # finally always returns to idle
    assert any(m["type"] == "caption" and "wrong" in m["text"].lower() for m in ws.sent)
    # the real exception is logged
    assert "tts 401 unauthorized" in open(str(tmp_path / "err.log")).read()
