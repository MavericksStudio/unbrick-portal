from brain.router import parse_action, build_messages, Action, SYSTEM_PROMPT

def test_parse_plain_text_is_none():
    assert parse_action("It is sunny today.") is None

def test_parse_clean_json():
    a = parse_action('{"action":"get_time"}')
    assert a == Action(name="get_time", args={})

def test_parse_json_embedded_in_prose():
    a = parse_action('Sure! {"action":"search_web","query":"mars news"} ok')
    assert a == Action(name="search_web", args={"query": "mars news"})

def test_parse_escalate():
    a = parse_action('{"action":"escalate","query":"prove sqrt(2) irrational"}')
    assert a.name == "escalate"
    assert a.args["query"].startswith("prove")

def test_parse_malformed_json_is_none():
    assert parse_action('{"action": ') is None

def test_build_messages_includes_system_and_history():
    msgs = build_messages([{"role": "user", "content": "hi"},
                           {"role": "assistant", "content": "hello"}],
                          "what time is it", extras="Be terse.")
    assert msgs[0]["role"] == "system"
    assert "escalate" in msgs[0]["content"]
    assert "Be terse." in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "what time is it"}
    assert {"role": "assistant", "content": "hello"} in msgs
