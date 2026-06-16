import os
import requests

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

DEFAULT_PERSONA = (
    "You are Portal, a warm, concise voice assistant running on a repurposed Meta "
    "Portal device. Answer in 1-3 short sentences meant to be spoken aloud: plain "
    "text, no markdown, no lists or URLs unless explicitly asked."
)

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

class ClaudeChat:
    """General conversational answers from Claude, with history + persona."""
    def __init__(self, api_key=None, model="claude-haiku-4-5-20251001",
                 persona="", max_tokens=400, timeout=40):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.persona = persona or DEFAULT_PERSONA
        self.max_tokens = max_tokens
        self.timeout = timeout

    def reply(self, history, user_text) -> str:
        messages = list(history) + [{"role": "user", "content": user_text}]
        r = requests.post(
            API_URL,
            headers=_headers(self.api_key),
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": self.persona,
                "messages": messages,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return _extract_text(r.json())
