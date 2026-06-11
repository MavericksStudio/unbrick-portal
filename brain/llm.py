import requests

class LocalLLM:
    def __init__(self, base_url, temperature=0.3, max_tokens=256, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def complete(self, messages) -> str:
        r = requests.post(
            self.base_url + "/v1/chat/completions",
            json={
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
