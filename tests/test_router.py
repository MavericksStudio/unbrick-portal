from brain.router import (parse_action, build_messages, classify_fallback,
                          Action, SYSTEM_PROMPT)

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

def test_parse_markdown_fenced():
    a = parse_action('```json\n{"action":"get_time"}\n```')
    assert a == Action(name="get_time", args={})

def test_parse_actions_array_fallback():
    a = parse_action('{"actions":["get_time"]}')
    assert a == Action(name="get_time", args={})

def test_parse_actions_array_with_query():
    a = parse_action('{"actions":["search_web"],"query":"mars"}')
    assert a == Action(name="search_web", args={"query": "mars"})

def test_fallback_news_routes_to_search():
    a = classify_fallback("what is the news on the world cup")
    assert a.name == "search_web" and "world cup" in a.args["query"]

def test_fallback_weather_routes_to_search():
    assert classify_fallback("how's the weather in tokyo").name == "search_web"

def test_fallback_general_question_escalates():
    assert classify_fallback("what is the capital of France").name == "escalate"

def test_fallback_question_mark_escalates():
    assert classify_fallback("tell me about black holes?").name == "escalate"

def test_fallback_greeting_is_none():
    assert classify_fallback("hello there") is None
    assert classify_fallback("thanks") is None

def test_build_messages_includes_system_and_history():
    msgs = build_messages([{"role": "user", "content": "hi"},
                           {"role": "assistant", "content": "hello"}],
                          "what time is it", extras="Be terse.")
    assert msgs[0]["role"] == "system"
    assert "escalate" in msgs[0]["content"]
    assert "Be terse." in msgs[0]["content"]
    assert msgs[-1] == {"role": "user", "content": "what time is it"}
    assert {"role": "assistant", "content": "hello"} in msgs
