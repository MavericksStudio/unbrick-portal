import asyncio, base64, json, os, subprocess, tempfile
import websockets
from brain.states import State

def webm_to_wav(blob: bytes) -> str:
    """Convert a browser audio blob to 16k mono WAV for whisper via ffmpeg."""
    src = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    src.write(blob); src.close()
    dst = src.name + ".wav"
    subprocess.run(["ffmpeg", "-y", "-i", src.name, "-ar", "16000", "-ac", "1", dst],
                   capture_output=True, timeout=60)
    os.unlink(src.name)
    return dst

class Session:
    def __init__(self, ws, conv, transcribe, synthesize, to_wav=webm_to_wav):
        self.ws = ws
        self.conv = conv
        self.transcribe = transcribe
        self.synthesize = synthesize
        self.to_wav = to_wav
        self.last_frame = None

    async def send(self, **obj):
        await self.ws.send(json.dumps(obj))

    async def set_state(self, state: State):
        await self.send(type="state", value=state.value)

    def _frame_provider(self):
        # v1: use the most recent frame the face already pushed (face sends a
        # frame on connect / periodically). Returns bytes or None.
        return self.last_frame

async def handle_message(sess: Session, raw: str):
    msg = json.loads(raw)
    t = msg.get("type")
    if t == "ptt":
        if msg.get("state") == "start":
            await sess.set_state(State.LISTENING)
        return
    if t == "frame":
        sess.last_frame = base64.b64decode(msg["data"])
        return
    if t == "audio":
        blob = base64.b64decode(msg["data"])
        await sess.set_state(State.THINKING)
        try:
            wav = sess.to_wav(blob)
            text = sess.transcribe(wav)
            reply = sess.conv.respond(text, frame_provider=sess._frame_provider)
            await sess.send(type="caption", text=reply.text)
            await sess.set_state(State.SPEAKING)
            audio = sess.synthesize(reply.text)
            await sess.send(type="tts_audio",
                            data=base64.b64encode(audio).decode())
        except Exception as e:  # never wedge the face
            await sess.send(type="caption", text="Sorry, something went wrong.")
            await sess.set_state(State.ERROR)
        finally:
            await sess.set_state(State.IDLE)
        return

async def serve(host, port, make_session):
    async def conn(ws):
        sess = make_session(ws)
        await sess.set_state(State.IDLE)
        async for raw in ws:
            await handle_message(sess, raw)
    async with websockets.serve(conn, host, port):
        await asyncio.Future()
