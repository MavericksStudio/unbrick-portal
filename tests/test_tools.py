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
