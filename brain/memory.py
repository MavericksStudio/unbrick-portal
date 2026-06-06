import json, os

class History:
    def __init__(self, path, enabled=True, max_turns=8):
        self.path, self.enabled, self.max_turns = path, enabled, max_turns
        self._msgs = []
        if enabled and os.path.exists(path):
            try:
                with open(path) as f:
                    self._msgs = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._msgs = []

    def add(self, role, content):
        if not self.enabled:
            return
        self._msgs.append({"role": role, "content": content})
        self._msgs = self._msgs[-self.max_turns * 2:]
        self._save()

    def messages(self):
        return list(self._msgs) if self.enabled else []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._msgs, f)
