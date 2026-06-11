import datetime
from html.parser import HTMLParser

class _DDGSnippetParser(HTMLParser):
    """Pull result snippet text out of DuckDuckGo's HTML results page."""
    def __init__(self):
        super().__init__()
        self._in_snippet = False
        self._buf = []
        self.snippets = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and "result__snippet" in dict(attrs).get("class", ""):
            self._in_snippet = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_snippet:
            self._in_snippet = False
            text = " ".join("".join(self._buf).split())
            if text:
                self.snippets.append(text)

    def handle_data(self, data):
        if self._in_snippet:
            self._buf.append(data)

def _parse_snippets(html_text, n=3):
    p = _DDGSnippetParser()
    p.feed(html_text)
    return [{"body": s} for s in p.snippets[:n]]

def default_search(query, n=3):
    """Pure-requests DuckDuckGo search (no Rust deps — works on Termux)."""
    import requests
    r = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Portal/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    return _parse_snippets(r.text, n)

def _spoken_time(now=None) -> str:
    now = now or datetime.datetime.now()
    hour = now.hour % 12 or 12  # portable: avoid glibc-only %-I
    ampm = "AM" if now.hour < 12 else "PM"
    return f"It is {hour}:{now.minute:02d} {ampm}"

def run(action, search=default_search) -> str:
    """Execute a non-escalate, non-capture tool action; return spoken text."""
    if action.name == "get_time":
        return _spoken_time()
    if action.name == "search_web":
        try:
            results = search(action.args.get("query", ""), n=3)
        except Exception:  # network/parse error — stay conversational
            return "I can't search the web right now."
        if not results:
            return "I couldn't find anything on that."
        bodies = [r.get("body", "") for r in results if r.get("body")]
        return " ".join(bodies[:2]) or "I found something but couldn't read it."
    return f"I don't know how to do '{action.name}'."
