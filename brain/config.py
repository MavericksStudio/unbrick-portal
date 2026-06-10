import json, os
from dataclasses import dataclass, asdict

@dataclass
class Config:
    # local SLM (llama-server, OpenAI-compatible)
    llm_base_url: str = "http://127.0.0.1:8080"
    llm_model: str = "gemma-3-1b-it"        # label only; server hosts one model
    no_mmap: bool = True                     # Phase 0: REQUIRED on device
    # websocket
    ws_host: str = "127.0.0.1"
    ws_port: int = 8765
    # escalation
    claude_model: str = "claude-opus-4-8"
    # stt
    whisper_bin: str = "whisper-cli"
    whisper_model: str = "ggml-base.en.bin"
    # tts (ElevenLabs)
    tts_voice_id: str = "21m00Tcm4TlvDq8ikWAM"   # "Rachel" — change to your voice
    tts_model: str = "eleven_turbo_v2_5"          # low-latency, multilingual
    tts_output_format: str = "mp3_44100_128"
    # memory
    memory_path: str = "chat_memory.json"
    memory_enabled: bool = True
    # persona appended to the router system prompt
    system_prompt_extras: str = ""

def load_config(path: str = "brain.json") -> "Config":
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)

def write_example(path: str) -> None:
    with open(path, "w") as f:
        json.dump(asdict(Config()), f, indent=2)
