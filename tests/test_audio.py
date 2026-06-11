import brain.server as srv

def test_wav_passthrough_no_ffmpeg(monkeypatch):
    called = {"ffmpeg": False}
    monkeypatch.setattr(srv, "webm_to_wav", lambda b: called.__setitem__("ffmpeg", True))
    blob = b"RIFF" + b"\x00" * 40  # minimal WAV-ish header
    path = srv.to_wav(blob)
    assert path.endswith(".wav")
    assert open(path, "rb").read() == blob
    assert called["ffmpeg"] is False

def test_non_wav_falls_back_to_ffmpeg(monkeypatch):
    monkeypatch.setattr(srv, "webm_to_wav", lambda b: "/tmp/converted.wav")
    out = srv.to_wav(b"\x1aEd\xdf" + b"webmdata")  # EBML/webm magic
    assert out == "/tmp/converted.wav"
