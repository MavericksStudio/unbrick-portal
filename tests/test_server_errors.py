import json, base64
from brain.server import Session
from brain.agent import Reply
from brain.states import State

class FakeWS:
    def __init__(self): self.sent = []
    async def send(self, msg): self.sent.append(json.loads(msg))

class OkConv:
    def respond(self, text): return Reply(text="ok")

async def test_tts_failure_reports_error_and_recovers(monkeypatch, tmp_path):
    import brain.server as srv
    monkeypatch.setattr(srv, "ERROR_LOG", str(tmp_path / "err.log"))

    def boom(text): raise RuntimeError("tts 401 unauthorized")
    ws = FakeWS()
    sess = Session(ws, conv=OkConv(), transcribe=lambda w: "hi",
                   synthesize=boom, to_wav=lambda b: "/tmp/x.wav")
    await sess.run_turn(b"RIFF....")
    states = [m["value"] for m in ws.sent if m["type"] == "state"]
    assert State.ERROR.value in states
    assert State.IDLE.value in states  # finally always returns to idle
    assert any(m["type"] == "caption" and "wrong" in m["text"].lower() for m in ws.sent)
    assert "tts 401 unauthorized" in open(str(tmp_path / "err.log")).read()
