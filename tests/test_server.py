import json, base64, asyncio, pytest
from brain.server import Session, handle_message
from brain.agent import Reply, FrameRequest
from brain.states import State

class FakeWS:
    def __init__(self): self.sent = []
    async def send(self, msg): self.sent.append(json.loads(msg))

class NormalConv:
    def respond(self, text): return Reply(text="hi back")

def mk(ws, conv):
    return Session(ws, conv=conv, transcribe=lambda wav: "hello",
                   synthesize=lambda text: b"AUDIO", to_wav=lambda blob: "/tmp/x.wav")

async def test_run_turn_emits_states_caption_audio():
    ws = FakeWS()
    await mk(ws, NormalConv()).run_turn(b"RIFFblob")
    states = [m["value"] for m in ws.sent if m["type"] == "state"]
    assert State.THINKING.value in states
    assert State.SPEAKING.value in states
    assert State.IDLE.value in states
    assert any(m["type"] == "caption" and m["text"] == "hi back" for m in ws.sent)
    assert any(m["type"] == "tts_audio" for m in ws.sent)

class VisionConv:
    def respond(self, text): return FrameRequest(query="what do you see")
    def describe(self, jpeg, query):
        return Reply(text="A cat." if jpeg == b"JPEG" else "no pic", used_tool=True)

async def test_capture_image_request_frame_roundtrip():
    ws = FakeWS()
    sess = mk(ws, VisionConv())
    turn = asyncio.create_task(sess.run_turn(b"RIFFblob"))
    for _ in range(100):                         # let the turn reach request_frame
        await asyncio.sleep(0)
        if any(m["type"] == "request_frame" for m in ws.sent):
            break
    assert any(m["type"] == "request_frame" for m in ws.sent)
    sess.resolve_frame(b"JPEG")                  # face replies with a frame
    await turn
    assert any(m["type"] == "caption" and m["text"] == "A cat." for m in ws.sent)
    assert any(m["type"] == "tts_audio" for m in ws.sent)

async def test_request_frame_times_out():
    ws = FakeWS()
    res = await mk(ws, NormalConv()).request_frame(timeout=0.05)
    assert res is None

async def test_handle_message_ptt_sets_listening():
    ws = FakeWS()
    await handle_message(mk(ws, NormalConv()), json.dumps({"type": "ptt", "state": "start"}))
    assert any(m["type"] == "state" and m["value"] == "listening" for m in ws.sent)

async def test_handle_message_frame_resolves_waiter():
    ws = FakeWS()
    sess = mk(ws, NormalConv())
    sess._frame_waiter = asyncio.get_event_loop().create_future()
    await handle_message(sess, json.dumps(
        {"type": "frame", "data": base64.b64encode(b"JPEG").decode()}))
    assert sess._frame_waiter is not None and sess._frame_waiter.result() == b"JPEG"
