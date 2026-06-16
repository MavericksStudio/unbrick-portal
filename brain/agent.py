from dataclasses import dataclass
from brain.router import classify
from brain import tools

@dataclass
class Reply:
    text: str
    used_tool: bool = False

@dataclass
class FrameRequest:
    """Returned by respond() when the user asked the device to see something. The
    server fetches a camera frame, then calls describe(jpeg, query)."""
    query: str

class Conversation:
    def __init__(self, chat, history, search=None, vision=None):
        self.chat = chat        # ClaudeChat
        self.history = history
        self.search = search    # callable(query) -> answer str
        self.vision = vision    # callable(jpeg, query) -> str

    def respond(self, user_text):
        """Returns a Reply, or a FrameRequest if the camera is needed first."""
        action = classify(user_text)
        if action.name == "capture_image":
            return FrameRequest(query=user_text)  # defer; server runs describe()
        if action.name == "get_time":
            reply = Reply(text=tools.run(action), used_tool=True)
        elif action.name == "search_web":
            reply = Reply(text=tools.run(action, search=self.search), used_tool=True)
        else:  # chat
            reply = Reply(text=self.chat.reply(self.history.messages(), user_text))
        self._record(user_text, reply.text)
        return reply

    def describe(self, jpeg, query) -> Reply:
        if jpeg and self.vision:
            text = self.vision(jpeg, query)
        else:
            text = "I couldn't get a picture."
        self._record(query, text)
        return Reply(text=text, used_tool=True)

    def _record(self, user_text, assistant_text):
        self.history.add("user", user_text)
        self.history.add("assistant", assistant_text)
