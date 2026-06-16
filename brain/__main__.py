import functools, os, asyncio
from brain.config import load_config
from brain.chat import ClaudeChat
from brain.search import web_search_via_claude
from brain.vision import describe_with_claude
from brain.stt import WhisperSTT
from brain.tts import ElevenLabsTTS
from brain.memory import History
from brain.agent import Conversation
from brain.server import Session, serve

def main():
    cfg = load_config()
    key = os.environ.get("ANTHROPIC_API_KEY")
    chat = ClaudeChat(api_key=key, model=cfg.claude_model, persona=cfg.persona)
    stt = WhisperSTT(cfg.whisper_bin, cfg.whisper_model)
    tts = ElevenLabsTTS(voice_id=cfg.tts_voice_id, model=cfg.tts_model,
                        output_format=cfg.tts_output_format)
    vision = functools.partial(describe_with_claude, key, cfg.claude_model)
    search = functools.partial(web_search_via_claude, api_key=key,
                               model=cfg.claude_model)

    def make_session(ws):
        conv = Conversation(
            chat=chat,
            history=History(cfg.memory_path, cfg.memory_enabled),
            search=search, vision=vision,
        )
        return Session(ws, conv=conv, transcribe=stt.transcribe,
                       synthesize=tts.synthesize)

    print(f"brain: ws://{cfg.ws_host}:{cfg.ws_port}")
    asyncio.run(serve(cfg.ws_host, cfg.ws_port, make_session))

if __name__ == "__main__":
    main()
