import functools, os
from brain.config import load_config
from brain.llm import LocalLLM
from brain.escalate import Escalator
from brain.stt import WhisperSTT
from brain.tts import GoogleTTS
from brain.memory import History
from brain.agent import Conversation
from brain.tools import default_search
from brain.vision import describe_with_claude
from brain.server import Session, serve
import asyncio

def main():
    cfg = load_config()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    llm = LocalLLM(cfg.llm_base_url)
    escalator = Escalator(api_key=anthropic_key, model=cfg.claude_model)
    stt = WhisperSTT(cfg.whisper_bin, cfg.whisper_model)
    tts = GoogleTTS(voice=cfg.tts_voice, lang=cfg.tts_lang)
    vision = functools.partial(describe_with_claude, anthropic_key, cfg.claude_model)

    def make_session(ws):
        conv = Conversation(
            llm=llm, escalator=escalator,
            history=History(cfg.memory_path, cfg.memory_enabled),
            search=default_search, vision=vision, extras=cfg.system_prompt_extras,
        )
        return Session(ws, conv=conv, transcribe=stt.transcribe,
                       synthesize=tts.synthesize)

    print(f"brain: ws://{cfg.ws_host}:{cfg.ws_port}")
    asyncio.run(serve(cfg.ws_host, cfg.ws_port, make_session))

if __name__ == "__main__":
    main()
