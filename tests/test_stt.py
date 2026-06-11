from brain.stt import WhisperSTT

def test_transcribe_invokes_binary_and_cleans(monkeypatch, tmp_path):
    calls = {}
    def fake_run(cmd, capture_output, text, timeout):
        calls["cmd"] = cmd
        class R: stdout = "\n[00:00:00.000 --> 00:00:02.000]   Hello there.\n"; returncode = 0
        return R()
    import brain.stt as m
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    wav = tmp_path / "in.wav"; wav.write_bytes(b"RIFF")
    stt = WhisperSTT(binary="whisper-cli", model="ggml-base.en.bin")
    text = stt.transcribe(str(wav))
    assert text == "Hello there."
    assert "whisper-cli" in calls["cmd"][0]
    assert str(wav) in calls["cmd"]
