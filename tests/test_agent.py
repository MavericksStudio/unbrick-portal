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
