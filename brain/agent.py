from dataclasses import dataclass
from brain.router import parse_action, build_messages
from brain import tools

@dataclass
class Reply:
    text: str
    used_escalation: bool = False
    used_tool: bool = False

class Conversation:
    def __init__(self, llm, escalator, history, search=tools.default_search,
                 vision=None, extras=""):
        self.llm = llm
        self.escalator = escalator
        self.history = history
        self.search = search
        self.vision = vision  # callable(jpeg_bytes, query) -> str
        self.extras = extras

    def respond(self, user_text, frame_provider) -> Reply:
        messages = build_messages(self.history.messages(), user_text, self.extras)
        raw = self.llm.complete(messages)
        action = parse_action(raw)

        if action is None:
            reply = Reply(text=raw)
        elif action.name == "escalate":
            reply = Reply(text=self.escalator.ask(action.args.get("query", user_text)),
                          used_escalation=True)
        elif action.name == "capture_image":
            jpeg = frame_provider()
            if jpeg and self.vision:
                reply = Reply(text=self.vision(jpeg, user_text), used_tool=True)
            else:
                reply = Reply(text="I couldn't get a picture.", used_tool=True)
        else:
            reply = Reply(text=tools.run(action, search=self.search), used_tool=True)

        self.history.add("user", user_text)
        self.history.add("assistant", reply.text)
        return reply
