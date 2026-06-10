import os, requests

class ElevenLabsTTS:
    """Thin ElevenLabs text-to-speech client. Returns raw audio bytes
    (MP3 by default) ready to hand to the face for playback."""
    BASE = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, api_key=None, voice_id="21m00Tcm4TlvDq8ikWAM",
                 model="eleven_turbo_v2_5", output_format="mp3_44100_128",
                 timeout=30):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.voice_id = voice_id
        self.model = model
        self.output_format = output_format
        self.timeout = timeout

    def synthesize(self, text) -> bytes:
        r = requests.post(
            f"{self.BASE}/{self.voice_id}",
            headers={
                "xi-api-key": self.api_key,
                "content-type": "application/json",
                "accept": "audio/mpeg",
            },
            params={"output_format": self.output_format},
            json={"text": text, "model_id": self.model},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.content
