from brain.router import Action
from brain import tools

def test_get_time_format():
    out = tools.run(Action("get_time"))
    assert "{" not in out
    assert ":" in out or "o'clock" in out.lower()

def test_search_web_returns_answer():
    out = tools.run(Action("search_web", {"query": "mars"}),
                    search=lambda q: "Water was found on Mars.")
    assert out == "Water was found on Mars."

def test_search_web_empty_answer():
    out = tools.run(Action("search_web", {"query": "x"}), search=lambda q: "")
    assert "couldn't find" in out.lower()

def test_search_web_no_backend():
    out = tools.run(Action("search_web", {"query": "x"}), search=None)
    assert "can't search" in out.lower()

def test_search_web_error_is_graceful():
    def boom(q): raise RuntimeError("api down")
    out = tools.run(Action("search_web", {"query": "x"}), search=boom)
    assert "can't search" in out.lower()

def test_unknown_action():
    out = tools.run(Action("nope"))
    assert "don't know" in out.lower() or "unknown" in out.lower()
