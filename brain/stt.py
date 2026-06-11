import subprocess, re

_TS = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]")

class WhisperSTT:
    def __init__(self, binary="whisper-cli", model="ggml-base.en.bin",
                 lang="en", threads=4, timeout=120):
        self.binary, self.model = binary, model
        self.lang, self.threads, self.timeout = lang, threads, timeout

    def transcribe(self, wav_path) -> str:
        cmd = [self.binary, "-m", self.model, "-l", self.lang,
               "-t", str(self.threads), "-nt", "-f", wav_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        lines = []
        for line in r.stdout.splitlines():
            line = _TS.sub("", line).strip()
            if line:
                lines.append(line)
        return " ".join(lines).strip()
