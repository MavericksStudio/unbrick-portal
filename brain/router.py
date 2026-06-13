import json, re
from dataclasses import dataclass, field

@dataclass
class Action:
    name: str
    args: dict = field(default_factory=dict)

SYSTEM_PROMPT = (
    "You are the on-device brain of a Portal voice assistant. You are fast but "
    "small, so you ROUTE hard work to a bigger model.\n"
    "For each user message reply with EITHER one short spoken sentence (plain "
    "text) OR exactly one JSON object describing an action. Never both. Never use "
    "markdown or code fences. Never use an \"actions\" array — always a single "
    "\"action\" string.\n\n"
    "Available actions:\n"
    '- {"action":"get_time"}\n'
    '- {"action":"search_web","query":"<text>"}\n'
    '- {"action":"capture_image"}\n'
    '- {"action":"escalate","query":"<restated request>"}\n\n'
    "ALWAYS use search_web for news, weather, sports scores, prices, or anything "
    "current/recent — never answer those from memory. Use escalate for any other "
    "real question (facts, reasoning, math, coding). Only answer directly for "
    "greetings and small talk.\n\n"
    "Examples:\n"
    'User: what time is it\n{"action":"get_time"}\n'
    'User: who won the game last night\n'
    '{"action":"search_web","query":"game result last night"}\n'
    'User: what is the news on the world cup\n'
    '{"action":"search_web","query":"world cup news"}\n'
    'User: what do you see\n{"action":"capture_image"}\n'
    'User: what is the capital of France\n'
    '{"action":"escalate","query":"what is the capital of France"}\n'
    'User: explain quantum tunneling\n'
    '{"action":"escalate","query":"explain quantum tunneling"}\n'
    'User: hello\nHey! How can I help?'
)

# Deterministic safety net: a 1B model often ignores the routing instructions and
# just answers (usually wrong/stale). When it returns plain text for a real
# question, override it so the right backend handles it.
_SEARCH_RE = re.compile(
    r"\b(news|latest|today|tonight|current(?:ly)?|right now|weather|temperature|"
    r"forecast|scores?|who won|world cup|olympics|election|stock|price of|prices|"
    r"recent(?:ly)?|happening|this (?:week|month|year)|update)\b", re.I)
_QUESTION_RE = re.compile(
    r"\b(who|what|whats|when|where|why|how|which|whose|is|are|was|were|can|could|"
    r"do|does|did|should|would|will|explain|define|calculate|tell me)\b", re.I)

def classify_fallback(user_text):
    """When the SLM gave plain text, decide if it should have routed instead.
    Returns an Action (search_web/escalate), or None to trust the SLM's text."""
    if not user_text:
        return None
    t = user_text.strip()
    if _SEARCH_RE.search(t):
        return Action("search_web", {"query": t})
    if "?" in t or _QUESTION_RE.search(t):
        return Action("escalate", {"query": t})
    return None

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

def _to_action(data):
    """Map a parsed dict to an Action, tolerating the plural {"actions":[...]}
    form some small models emit."""
    if not isinstance(data, dict):
        return None
    if "action" in data:
        name = data["action"]
        return Action(name=name, args={k: v for k, v in data.items() if k != "action"})
    acts = data.get("actions")
    if isinstance(acts, list) and acts:
        first = acts[0]
        if isinstance(first, str):
            return Action(name=first,
                          args={k: v for k, v in data.items() if k != "actions"})
        if isinstance(first, dict) and "action" in first:
            name = first["action"]
            return Action(name=name,
                          args={k: v for k, v in first.items() if k != "action"})
    return None

def parse_action(text: str):
    if not text:
        return None
    m = _JSON_RE.search(text)
    if not m:
        return None
    blob = m.group(0)
    # try progressively shorter prefixes ending in '}' to tolerate trailing prose
    for end in range(len(blob), 0, -1):
        if blob[end - 1] != "}":
            continue
        try:
            data = json.loads(blob[:end])
        except json.JSONDecodeError:
            continue
        action = _to_action(data)
        if action is not None:
            return action
    return None

def build_messages(history, user_text, extras=""):
    system = SYSTEM_PROMPT + (("\n\n" + extras) if extras else "")
    msgs = [{"role": "system", "content": system}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": user_text})
    return msgs
