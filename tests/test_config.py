import json, pytest
from brain.config import load_config, Config

def test_load_defaults(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({}))
    c = load_config(str(p))
    assert isinstance(c, Config)
    assert c.llm_base_url == "http://127.0.0.1:8080"
    assert c.ws_host == "127.0.0.1"
    assert c.ws_port == 8765
    assert c.claude_model == "claude-opus-4-8"
    assert c.no_mmap is True

def test_overrides(tmp_path):
    p = tmp_path / "brain.json"
    p.write_text(json.dumps({"ws_port": 9000, "claude_model": "claude-sonnet-4-6"}))
    c = load_config(str(p))
    assert c.ws_port == 9000
    assert c.claude_model == "claude-sonnet-4-6"

def test_missing_file_uses_defaults():
    c = load_config("/nonexistent/brain.json")
    assert c.ws_port == 8765
