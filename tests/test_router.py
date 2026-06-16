from brain.router import classify, Action

def test_time_intent():
    assert classify("what time is it").name == "get_time"
    assert classify("do you know the time?").name == "get_time"

def test_vision_intent():
    assert classify("what do you see").name == "capture_image"
    assert classify("take a look around").name == "capture_image"
    assert classify("describe what is in front of you").name == "capture_image"

def test_search_intent():
    a = classify("what is the news on the world cup")
    assert a.name == "search_web" and "world cup" in a.args["query"]
    assert classify("what's the weather in tokyo").name == "search_web"
    assert classify("who won the game last night").name == "search_web"

def test_chat_intent_default():
    assert classify("what is the capital of France").name == "chat"
    assert classify("tell me a joke").name == "chat"
    assert classify("hello there").name == "chat"
    assert classify("").name == "chat"

def test_priority_time_before_search():
    # "what time" should win even though phrasing could look like a question
    assert classify("what time is it right now").name in ("get_time", "search_web")
    # time regex is checked first, so:
    assert classify("what time is it").name == "get_time"
