from brain.agent import Conversation, Reply, FrameRequest
from brain.memory import History

def mk(tmp_path, llm_reply, escalate_reply="ESCALATED", search=None, vision=None):
    class LLM:
        def complete(self, messages): return llm_reply
    class Esc:
        def ask(self, q): return escalate_reply
    hist = History(str(tmp_path / "m.json"), enabled=True)
    return Conversation(
        llm=LLM(), escalator=Esc(), history=hist,
        search=search or (lambda q: "Mars has water."),
        vision=vision or (lambda jpeg, q: "I see a desk."),
        extras="",
    )

def test_plain_answer_passthrough(tmp_path):
    c = mk(tmp_path, "Hello there!")
    r = c.respond("hi")
    assert isinstance(r, Reply)
    assert r.text == "Hello there!"
    assert not r.used_escalation

def test_get_time_tool(tmp_path):
    c = mk(tmp_path, '{"action":"get_time"}')
    r = c.respond("what time")
    assert ":" in r.text and r.used_tool

def test_search_tool(tmp_path):
    c = mk(tmp_path, '{"action":"search_web","query":"mars"}')
    r = c.respond("mars news")
    assert r.text == "Mars has water." and r.used_tool

def test_escalate(tmp_path):
    c = mk(tmp_path, '{"action":"escalate","query":"hard q"}', escalate_reply="42")
    r = c.respond("hard q")
    assert r.text == "42" and r.used_escalation

def test_capture_image_returns_frame_request(tmp_path):
    c = mk(tmp_path, '{"action":"capture_image"}')
    r = c.respond("what do you see")
    assert isinstance(r, FrameRequest)
    assert r.query == "what do you see"

def test_describe_uses_vision(tmp_path):
    c = mk(tmp_path, "irrelevant", vision=lambda jpeg, q: "A cat.")
    r = c.describe(b"JPEGBYTES", "what do you see")
    assert r.text == "A cat." and r.used_tool

def test_describe_without_frame(tmp_path):
    c = mk(tmp_path, "irrelevant")
    r = c.describe(None, "what do you see")
    assert "couldn't" in r.text.lower()

def test_history_records_normal_turn(tmp_path):
    c = mk(tmp_path, "Hi!")
    c.respond("hello")
    roles = [m["role"] for m in c.history.messages()]
    assert roles == ["user", "assistant"]

def test_history_records_vision_turn(tmp_path):
    c = mk(tmp_path, '{"action":"capture_image"}', vision=lambda jpeg, q: "A cat.")
    r = c.respond("what do you see")          # FrameRequest — not recorded yet
    assert c.history.messages() == []
    c.describe(b"JPEG", r.query)               # records the pair
    assert [m["content"] for m in c.history.messages()] == ["what do you see", "A cat."]
