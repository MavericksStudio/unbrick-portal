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
