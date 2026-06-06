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
