import datetime

def default_search(query, n=3):
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=n))

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
        results = search(action.args.get("query", ""), n=3)
        if not results:
            return "I couldn't find anything on that."
        bodies = [r.get("body", "") for r in results if r.get("body")]
        return " ".join(bodies[:2]) or "I found something but couldn't read it."
    return f"I don't know how to do '{action.name}'."
