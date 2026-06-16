import re
from dataclasses import dataclass, field

@dataclass
class Action:
    name: str                       # get_time | capture_image | search_web | chat
    args: dict = field(default_factory=dict)

# Deterministic on-device intent routing — instant and reliable (no neural model).
_TIME_RE = re.compile(
    r"\b(what(?:'s| is)? the time|what time|the time|o'?clock)\b", re.I)
_VISION_RE = re.compile(
    r"\b(what do you see|what can you see|can you see|look (?:at|around|here)|"
    r"in front of you|describe (?:what|the|this|that)|what(?:'s| is) (?:this|that|"
    r"in front)|take a (?:look|picture|photo|pic)|use (?:the |your )?camera)\b", re.I)
_SEARCH_RE = re.compile(
    r"\b(news|latest|today|tonight|current(?:ly)?|right now|weather|temperature|"
    r"forecast|scores?|who won|world cup|olympics|election|stock|price of|prices|"
    r"recent(?:ly)?|happening|this (?:week|month|year)|update)\b", re.I)

def classify(user_text) -> Action:
    """Route an utterance to exactly one backend. Order matters: time, then
    vision, then current-info search, else a general Claude chat."""
    t = (user_text or "").strip()
    if not t:
        return Action("chat")
    if _TIME_RE.search(t):
        return Action("get_time")
    if _VISION_RE.search(t):
        return Action("capture_image")
    if _SEARCH_RE.search(t):
        return Action("search_web", {"query": t})
    return Action("chat")
