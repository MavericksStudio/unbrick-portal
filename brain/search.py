import requests
from brain.escalate import API_URL, _headers, _extract_text

SYSTEM = ("Search the web and answer concisely for speech: 1-3 short sentences, "
          "plain text, no markdown, no URLs or citation markers read aloud.")

def web_search_via_claude(query, api_key, model="claude-opus-4-8",
                          max_uses=3, timeout=40) -> str:
    """Answer a query using Claude's server-side web_search tool. Returns the
    spoken-ready answer text."""
    r = requests.post(
        API_URL,
        headers=_headers(api_key),
        json={
            "model": model,
            "max_tokens": 500,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": query}],
            "tools": [{"type": "web_search_20250305", "name": "web_search",
                       "max_uses": max_uses}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return _extract_text(r.json())
