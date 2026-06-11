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
    "Use escalate for anything needing reasoning, math, coding, or knowledge you "
    "are unsure of.\n\n"
    "Examples:\n"
    'User: what time is it\n{"action":"get_time"}\n'
    'User: who won the game last night\n'
    '{"action":"search_web","query":"game result last night"}\n'
    'User: what do you see\n{"action":"capture_image"}\n'
    'User: explain quantum tunneling\n'
    '{"action":"escalate","query":"explain quantum tunneling"}\n'
    'User: hello\nHey! How can I help?'
)

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
