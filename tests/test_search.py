from brain.search import web_search_via_claude

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_web_search_sends_tool_and_extracts_answer(monkeypatch):
    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["key"] = headers["x-api-key"]
        return FakeResp({"content": [
            {"type": "web_search_tool_result", "content": []},
            {"type": "text", "text": "Mars has seasonal water flows."},
        ]})
    import brain.search as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    out = web_search_via_claude("water on mars", api_key="k", model="claude-opus-4-8")
    assert out == "Mars has seasonal water flows."
    assert captured["key"] == "k"
    assert captured["json"]["model"] == "claude-opus-4-8"
    tool = captured["json"]["tools"][0]
    assert tool["type"] == "web_search_20250305" and tool["name"] == "web_search"
    assert captured["json"]["messages"][0]["content"] == "water on mars"
