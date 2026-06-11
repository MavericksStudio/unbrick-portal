from brain.router import Action
from brain import tools

def test_get_time_format(monkeypatch):
    out = tools.run(Action("get_time"), search=lambda q, n=3: [])
    # Should be a spoken time string, not JSON
    assert "{" not in out
    assert ":" in out or "o'clock" in out.lower()

def test_search_web_summarizes(monkeypatch):
    fake = [{"title": "Mars", "body": "Water found on Mars."},
            {"title": "More", "body": "Rover update."}]
    out = tools.run(Action("search_web", {"query": "mars"}), search=lambda q, n=3: fake)
    assert "Water found on Mars" in out

def test_unknown_action():
    out = tools.run(Action("nope"), search=lambda q, n=3: [])
    assert "don't know" in out.lower() or "unknown" in out.lower()

def test_parse_snippets_extracts_result_bodies():
    html = (
        '<div class="result">'
        '<a class="result__a" href="x">Mars</a>'
        '<a class="result__snippet" href="x">Water was found on <b>Mars</b>.</a>'
        '</div>'
        '<div class="result">'
        '<a class="result__snippet">Second snippet here.</a>'
        '</div>'
    )
    out = tools._parse_snippets(html, n=3)
    assert out[0]["body"] == "Water was found on Mars."
    assert out[1]["body"] == "Second snippet here."

def test_parse_snippets_respects_limit():
    html = '<a class="result__snippet">a</a><a class="result__snippet">b</a>'
    assert len(tools._parse_snippets(html, n=1)) == 1

def test_search_web_unavailable_message_on_failure():
    def boom(q, n=3): raise RuntimeError("network down")
    out = tools.run(Action("search_web", {"query": "x"}), search=boom)
    assert "can't search" in out.lower()
