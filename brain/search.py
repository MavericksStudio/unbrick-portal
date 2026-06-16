import datetime
import requests
from brain.chat import API_URL, _headers, _extract_text

def web_search_via_claude(query, api_key, model="claude-opus-4-8",
                          max_uses=3, timeout=40) -> str:
    """Answer a query using Claude's server-side web_search tool. Returns the
    spoken-ready answer text. The current date + an explicit instruction push
    the model to actually search instead of answering from stale memory."""
    today = datetime.date.today().isoformat()
    system = (
        f"Today's date is {today}. You have a web_search tool. You MUST use it "
        "to find current information before answering — your training data is out "
        "of date, so do not answer from prior knowledge. After searching, answer "
        "concisely for speech: 1-3 short sentences, plain text, no markdown, no "
        "URLs or citation markers."
    )
    r = requests.post(
        API_URL,
        headers=_headers(api_key),
        json={
            "model": model,
            "max_tokens": 600,
            "system": system,
            "messages": [{"role": "user",
                          "content": f"Search the web and tell me: {query}"}],
            "tools": [{"type": "web_search_20250305", "name": "web_search",
                       "max_uses": max_uses}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return _extract_text(r.json())
