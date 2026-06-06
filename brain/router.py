import json, re
from dataclasses import dataclass, field

@dataclass
class Action:
    name: str
    args: dict = field(default_factory=dict)

SYSTEM_PROMPT = (
    "You are the on-device brain of a Portal voice assistant. You are fast but "
    "small, so you ROUTE hard work to a bigger model.\n"
    "Reply with EXACTLY ONE JSON object when an action is needed, otherwise reply "
    "with a short spoken answer in plain text.\n\n"
    "Actions:\n"
    '1. Time: {"action":"get_time"}\n'
    '2. Web search (current events / facts you are unsure of): '
    '{"action":"search_web","query":"..."}\n'
    '3. See (camera): {"action":"capture_image"}\n'
    '4. Escalate to the big model (deep reasoning, math, coding, multi-step '
    'logic, anything you are not confident about): '
    '{"action":"escalate","query":"<restate the user request>"}\n\n'
    "If a simple greeting or trivial fact, answer directly in one or two "
    "sentences. When unsure, prefer escalate. Output ONLY the JSON for actions, "
    "with no extra words."
)

# greedy-but-safe: find the first balanced {...} that parses as JSON with "action"
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

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
        if isinstance(data, dict) and "action" in data:
            name = data.pop("action")
            return Action(name=name, args={k: v for k, v in data.items()})
    return None

def build_messages(history, user_text, extras=""):
    system = SYSTEM_PROMPT + (("\n\n" + extras) if extras else "")
    msgs = [{"role": "system", "content": system}]
    msgs.extend(history)
    msgs.append({"role": "user", "content": user_text})
    return msgs
