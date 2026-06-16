import json, pytest
from brain.config import load_config, Config

def test_load_defaults(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({}))
    c = load_config(str(p))
    assert isinstance(c, Config)
    assert c.ws_host == "127.0.0.1"
    assert c.ws_port == 8765
    assert c.claude_model == "claude-haiku-4-5-20251001"
    assert c.whisper_model == "ggml-tiny.en.bin"

def test_overrides(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({"ws_port": 9000, "claude_model": "claude-opus-4-8"}))
    c = load_config(str(p))
    assert c.ws_port == 9000
    assert c.claude_model == "claude-opus-4-8"

def test_missing_file_uses_defaults():
    c = load_config("/nonexistent/brain.json")
    assert c.ws_port == 8765
