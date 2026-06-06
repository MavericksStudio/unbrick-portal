from brain.escalate import Escalator

class FakeMessages:
    def create(self, **kw):
        self.kw = kw
        class R: content = [type("B", (), {"text": "Because 2 has no integer root."})()]
        return R()

class FakeClient:
    def __init__(self): self.messages = FakeMessages()

def test_escalate_returns_text():
    esc = Escalator(client=FakeClient(), model="claude-opus-4-8")
    out = esc.ask("why is sqrt(2) irrational")
    assert "integer root" in out

def test_escalate_passes_model():
    fc = FakeClient()
    esc = Escalator(client=fc, model="claude-sonnet-4-6")
    esc.ask("hi")
    assert fc.messages.kw["model"] == "claude-sonnet-4-6"
