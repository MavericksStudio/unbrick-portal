import datetime

def _spoken_time(now=None) -> str:
    now = now or datetime.datetime.now()
    hour = now.hour % 12 or 12  # portable: avoid glibc-only %-I
    ampm = "AM" if now.hour < 12 else "PM"
    return f"It is {hour}:{now.minute:02d} {ampm}"

def run(action, search=None) -> str:
    """Execute a non-escalate, non-capture tool action; return spoken text.

    `search` is a callable (query) -> str (a finished, spoken-ready answer), or
    None if web search is not configured."""
    if action.name == "get_time":
        return _spoken_time()
    if action.name == "search_web":
        if search is None:
            return "I can't search the web right now."
        try:
            answer = search(action.args.get("query", ""))
        except Exception:  # network / API error — stay conversational
            return "I can't search the web right now."
        return answer or "I couldn't find anything on that."
    return f"I don't know how to do '{action.name}'."
