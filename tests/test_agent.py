from brain.agent import Conversation, Reply, FrameRequest
from brain.memory import History

def mk(tmp_path, chat_reply="Hi there!", search=None, vision=None):
    class Chat:
        def reply(self, history, user_text): return chat_reply
    hist = History(str(tmp_path / "m.json"), enabled=True)
    return Conversation(
        chat=Chat(), history=hist,
        search=search or (lambda q: "Tokyo is sunny, 20C."),
        vision=vision or (lambda jpeg, q: "I see a desk."),
    )

def test_chat_answer(tmp_path):
    c = mk(tmp_path, chat_reply="The capital is Paris.")
    r = c.respond("what is the capital of France")
    assert isinstance(r, Reply) and r.text == "The capital is Paris."

def test_time(tmp_path):
    r = mk(tmp_path).respond("what time is it")
    assert ":" in r.text and r.used_tool

def test_search(tmp_path):
    c = mk(tmp_path, search=lambda q: "World Cup 2026 is in North America.")
    r = c.respond("what is the news on the world cup")
    assert "2026" in r.text and r.used_tool

def test_capture_returns_frame_request(tmp_path):
    r = mk(tmp_path).respond("what do you see")
    assert isinstance(r, FrameRequest) and r.query == "what do you see"

def test_describe_uses_vision(tmp_path):
    c = mk(tmp_path, vision=lambda jpeg, q: "A cat.")
    r = c.describe(b"JPEG", "what do you see")
    assert r.text == "A cat." and r.used_tool

def test_describe_without_frame(tmp_path):
    r = mk(tmp_path).describe(None, "q")
    assert "couldn't" in r.text.lower()

def test_history_records_chat_turn(tmp_path):
    c = mk(tmp_path, chat_reply="Hello!")
    c.respond("hi")
    assert [m["content"] for m in c.history.messages()] == ["hi", "Hello!"]

def test_history_records_vision_turn(tmp_path):
    c = mk(tmp_path, vision=lambda jpeg, q: "A cat.")
    r = c.respond("what do you see")          # FrameRequest — not recorded yet
    assert c.history.messages() == []
    c.describe(b"J", r.query)
    assert [m["content"] for m in c.history.messages()] == ["what do you see", "A cat."]
