from dataclasses import dataclass
from brain.router import parse_action, build_messages
from brain import tools

@dataclass
class Reply:
    text: str
    used_escalation: bool = False
    used_tool: bool = False

@dataclass
class FrameRequest:
    """Returned by respond() when the SLM picked capture_image. The server
    fetches a camera frame, then calls describe(jpeg, query) for the final reply."""
    query: str

class Conversation:
    def __init__(self, llm, escalator, history, search=tools.default_search,
                 vision=None, extras=""):
        self.llm = llm
        self.escalator = escalator
        self.history = history
        self.search = search
        self.vision = vision  # callable(jpeg_bytes, query) -> str
        self.extras = extras

    def respond(self, user_text):
        """Returns a Reply, or a FrameRequest if a camera frame is needed first."""
        messages = build_messages(self.history.messages(), user_text, self.extras)
        raw = self.llm.complete(messages)
        action = parse_action(raw)

        if action is not None and action.name == "capture_image":
            return FrameRequest(query=user_text)  # defer; server runs describe()

        if action is None:
            reply = Reply(text=raw)
        elif action.name == "escalate":
            reply = Reply(text=self.escalator.ask(action.args.get("query", user_text)),
                          used_escalation=True)
        else:
            reply = Reply(text=tools.run(action, search=self.search), used_tool=True)

        self._record(user_text, reply.text)
        return reply

    def describe(self, jpeg, query) -> Reply:
        """Complete a capture_image turn once a frame is available."""
        if jpeg and self.vision:
            text = self.vision(jpeg, query)
        else:
            text = "I couldn't get a picture."
        self._record(query, text)
        return Reply(text=text, used_tool=True)

    def _record(self, user_text, assistant_text):
        self.history.add("user", user_text)
        self.history.add("assistant", assistant_text)
