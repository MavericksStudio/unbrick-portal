from brain.chat import ClaudeChat

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_reply_sends_history_persona_and_extracts(monkeypatch):
    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["key"] = headers["x-api-key"]
        return FakeResp({"content": [{"type": "text", "text": "Hi, I'm Portal."}]})
    import brain.chat as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    chat = ClaudeChat(api_key="k", model="claude-haiku-4-5-20251001", persona="Be Portal.")
    out = chat.reply([{"role": "user", "content": "hey"},
                      {"role": "assistant", "content": "hello"}], "who are you")
    assert out == "Hi, I'm Portal."
    assert captured["key"] == "k"
    assert "api.anthropic.com" in captured["url"]
    assert captured["json"]["model"] == "claude-haiku-4-5-20251001"
    assert captured["json"]["system"] == "Be Portal."
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "who are you"}
    assert {"role": "assistant", "content": "hello"} in captured["json"]["messages"]

def test_default_persona_used_when_unset(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        assert "Portal" in json["system"]
        return FakeResp({"content": [{"type": "text", "text": "ok"}]})
    import brain.chat as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    ClaudeChat(api_key="k").reply([], "hi")
