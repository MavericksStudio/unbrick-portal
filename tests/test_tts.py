import base64
from brain.tts import GoogleTTS

class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p

def test_synthesize_returns_audio_bytes(monkeypatch):
    audio = b"FAKEWAVDATA"
    def fake_post(url, params=None, json=None, timeout=None):
        assert "text-to-speech" in url
        assert json["input"]["text"] == "hello"
        return FakeResp({"audioContent": base64.b64encode(audio).decode()})
    import brain.tts as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    tts = GoogleTTS(api_key="k", voice="en-GB-Standard-B", lang="en-GB")
    out = tts.synthesize("hello")
    assert out == audio
