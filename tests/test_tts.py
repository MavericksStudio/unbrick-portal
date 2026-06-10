from brain.tts import ElevenLabsTTS

class FakeResp:
    def __init__(self, content): self.content = content
    def raise_for_status(self): pass

def test_synthesize_returns_audio_bytes(monkeypatch):
    audio = b"MP3AUDIODATA"
    def fake_post(url, headers=None, params=None, json=None, timeout=None):
        assert "api.elevenlabs.io" in url
        assert url.endswith("/VOICE123")
        assert headers["xi-api-key"] == "k"
        assert json["text"] == "hello"
        assert json["model_id"] == "eleven_turbo_v2_5"
        assert params["output_format"] == "mp3_44100_128"
        return FakeResp(audio)
    import brain.tts as m
    monkeypatch.setattr(m.requests, "post", fake_post)
    tts = ElevenLabsTTS(api_key="k", voice_id="VOICE123",
                        model="eleven_turbo_v2_5", output_format="mp3_44100_128")
    out = tts.synthesize("hello")
    assert out == audio
