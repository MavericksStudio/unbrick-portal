import asyncio, base64, json, os, subprocess, tempfile, traceback
import websockets
from brain.states import State
from brain.agent import FrameRequest

ERROR_LOG = os.path.expanduser("~/brain-errors.log")

def log_error(err: str):
    print(err, flush=True)
    try:
        with open(ERROR_LOG, "a") as f:
            f.write(err + "\n")
    except OSError:
        pass

def webm_to_wav(blob: bytes) -> str:
    """Transcode a non-WAV browser audio blob to 16k mono WAV via ffmpeg."""
    src = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    src.write(blob); src.close()
    dst = src.name + ".wav"
    subprocess.run(["ffmpeg", "-y", "-i", src.name, "-ar", "16000", "-ac", "1", dst],
                   capture_output=True, timeout=60)
    os.unlink(src.name)
    return dst

def to_wav(blob: bytes) -> str:
    """Return a path to a WAV file for whisper. If the face already sent a WAV
    (RIFF/WAVE container), write it through untouched (no ffmpeg). Otherwise
    transcode via ffmpeg as a fallback."""
    if blob[:4] == b"RIFF":
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        f.write(blob); f.close()
        return f.name
    return webm_to_wav(blob)

class Session:
    def __init__(self, ws, conv, transcribe, synthesize, to_wav=to_wav):
        self.ws = ws
        self.conv = conv
        self.transcribe = transcribe
        self.synthesize = synthesize
        self.to_wav = to_wav
        self._frame_waiter = None

    async def send(self, **obj):
        try:
            await self.ws.send(json.dumps(obj))
        except websockets.exceptions.ConnectionClosed:
            pass  # face dropped/reloaded mid-turn — nothing to do

    async def set_state(self, state: State):
        await self.send(type="state", value=state.value)

    async def request_frame(self, timeout=5):
        """Ask the face for one camera frame and await it (None on timeout)."""
        self._frame_waiter = asyncio.get_event_loop().create_future()
        await self.send(type="request_frame")
        try:
            return await asyncio.wait_for(self._frame_waiter, timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._frame_waiter = None

    def resolve_frame(self, jpeg: bytes):
        if self._frame_waiter and not self._frame_waiter.done():
            self._frame_waiter.set_result(jpeg)

    async def run_turn(self, blob: bytes):
        await self.set_state(State.THINKING)
        try:
            wav = self.to_wav(blob)
            text = self.transcribe(wav)
            result = self.conv.respond(text)
            if isinstance(result, FrameRequest):
                jpeg = await self.request_frame()
                reply = self.conv.describe(jpeg, result.query)
            else:
                reply = result
            await self.send(type="caption", text=reply.text)
            await self.set_state(State.SPEAKING)
            audio = self.synthesize(reply.text)
            await self.send(type="tts_audio", data=base64.b64encode(audio).decode())
        except Exception:  # never wedge the face
            log_error(traceback.format_exc())
            await self.send(type="caption", text="Sorry, something went wrong.")
            await self.set_state(State.ERROR)
        finally:
            await self.set_state(State.IDLE)

async def handle_message(sess: Session, raw: str):
    msg = json.loads(raw)
    t = msg.get("type")
    if t == "ptt":
        if msg.get("state") == "start":
            await sess.set_state(State.LISTENING)
    elif t == "frame":
        sess.resolve_frame(base64.b64decode(msg["data"]))
    elif t == "audio":
        # Run the turn as a task so this read-loop stays live to receive the
        # frame the turn may request mid-flight.
        task = asyncio.create_task(sess.run_turn(base64.b64decode(msg["data"])))
        task.add_done_callback(_reap_task)

def _reap_task(task):
    # Retrieve any exception so it isn't an "never retrieved" warning, and log it.
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc:
        log_error("".join(traceback.format_exception(exc)))

async def serve(host, port, make_session):
    async def conn(ws):
        sess = make_session(ws)
        await sess.set_state(State.IDLE)
        async for raw in ws:
            await handle_message(sess, raw)
    async with websockets.serve(conn, host, port):
        await asyncio.Future()
