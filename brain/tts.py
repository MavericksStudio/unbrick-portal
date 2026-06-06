import base64, os, requests

class GoogleTTS:
    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def __init__(self, api_key=None, voice="en-GB-Standard-B", lang="en-GB",
                 encoding="LINEAR16", timeout=30):
        self.api_key = api_key or os.environ.get("GOOGLE_TTS_API_KEY")
        self.voice, self.lang, self.encoding, self.timeout = voice, lang, encoding, timeout

    def synthesize(self, text) -> bytes:
        r = requests.post(
            self.URL,
            params={"key": self.api_key},
            json={
                "input": {"text": text},
                "voice": {"languageCode": self.lang, "name": self.voice},
                "audioConfig": {"audioEncoding": self.encoding},
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"])
