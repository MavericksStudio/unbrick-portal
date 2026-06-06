from brain.escalate import Escalator

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_escalate_returns_text(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        assert "api.anthropic.com" in url
        assert headers["x-api-key"] == "k"
        return FakeResp({"content": [{"type": "text",
                                      "text": "Because 2 has no integer root."}]})
    import brain.escalate as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    esc = Escalator(api_key="k", model="claude-opus-4-8")
    out = esc.ask("why is sqrt(2) irrational")
    assert "integer root" in out

def test_escalate_passes_model(monkeypatch):
    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["model"] = json["model"]
        return FakeResp({"content": [{"type": "text", "text": "x"}]})
    import brain.escalate as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    esc = Escalator(api_key="k", model="claude-sonnet-4-6")
    esc.ask("hi")
    assert captured["model"] == "claude-sonnet-4-6"
