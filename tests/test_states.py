from brain.states import State

def test_states_have_wire_values():
    assert State.IDLE.value == "idle"
    assert State.LISTENING.value == "listening"
    assert State.THINKING.value == "thinking"
    assert State.SPEAKING.value == "speaking"
    assert State.ERROR.value == "error"
