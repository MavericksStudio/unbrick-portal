import os

SYSTEM = ("You are the deep-reasoning brain behind a small voice assistant. "
          "Answer correctly and concisely for speech: 1-4 short sentences, no "
          "markdown, no lists unless asked.")

class Escalator:
    def __init__(self, client=None, model="claude-opus-4-8", max_tokens=400):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def ask(self, query) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": query}],
        )
        return "".join(getattr(b, "text", "") for b in resp.content).strip()
