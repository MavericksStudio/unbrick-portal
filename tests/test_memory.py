from brain.memory import History

def test_append_and_persist(tmp_path):
    p = tmp_path / "mem.json"
    h = History(str(p), enabled=True, max_turns=2)
    h.add("user", "hi"); h.add("assistant", "hello")
    h.add("user", "bye"); h.add("assistant", "later")
    msgs = h.messages()
    # max_turns=2 keeps last 2 user+assistant pairs == 4 messages
    assert len(msgs) == 4
    assert msgs[0]["content"] == "hi" or msgs[-1]["content"] == "later"
    h2 = History(str(p), enabled=True, max_turns=2)
    assert h2.messages()[-1]["content"] == "later"

def test_disabled_keeps_nothing(tmp_path):
    h = History(str(tmp_path / "m.json"), enabled=False)
    h.add("user", "hi")
    assert h.messages() == []
