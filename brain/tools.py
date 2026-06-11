import datetime
from html.parser import HTMLParser

class _DDGSnippetParser(HTMLParser):
    """Pull result snippets out of DuckDuckGo result pages. Handles both the
    html endpoint (`<a class="result__snippet">`) and the lite endpoint
    (`<td class="result-snippet">`)."""
    SNIPPET_CLASSES = ("result__snippet", "result-snippet")

    def __init__(self):
        super().__init__()
        self._tag = None   # name of the element we're currently capturing
        self._buf = []
        self.snippets = []

    def handle_starttag(self, tag, attrs):
        if self._tag is None:
            cls = dict(attrs).get("class", "")
            if any(c in cls for c in self.SNIPPET_CLASSES):
                self._tag = tag
                self._buf = []

    def handle_endtag(self, tag):
        if self._tag is not None and tag == self._tag:
            text = " ".join("".join(self._buf).split())
            if text:
                self.snippets.append(text)
            self._tag = None

    def handle_data(self, data):
        if self._tag is not None:
            self._buf.append(data)

def _parse_snippets(html_text, n=3):
    p = _DDGSnippetParser()
    p.feed(html_text)
    return [{"body": s} for s in p.snippets[:n]]

_DDG_ENDPOINTS = (
    "https://html.duckduckgo.com/html/",
    "https://lite.duckduckgo.com/lite/",
)
_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"

def default_search(query, n=3):
    """Pure-requests DuckDuckGo search (no Rust deps — works on Termux). Tries
    the html endpoint, falls back to lite if it returns nothing (rate-limit
    resilience). Returns [] only if every source fails or is empty."""
    import requests
    for url in _DDG_ENDPOINTS:
        try:
            r = requests.post(url, data={"q": query},
                              headers={"User-Agent": _UA}, timeout=10)
            r.raise_for_status()
            hits = _parse_snippets(r.text, n)
            if hits:
                return hits
        except Exception:
            continue
    return []

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
