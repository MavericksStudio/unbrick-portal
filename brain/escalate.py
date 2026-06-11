import os, requests

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM = ("You are the deep-reasoning brain behind a small voice assistant. "
          "Answer correctly and concisely for speech: 1-4 short sentences, no "
          "markdown, no lists unless asked.")

def _headers(api_key):
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

def _extract_text(data) -> str:
    return "".join(
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    ).strip()

class Escalator:
    def __init__(self, api_key=None, model="claude-opus-4-8", max_tokens=400, timeout=60):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout

    def ask(self, query) -> str:
        r = requests.post(
            API_URL,
            headers=_headers(self.api_key),
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": query}],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return _extract_text(r.json())
