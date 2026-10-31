"""Chapter 13: what the session transcript does not show.

Replays the session of `python -m agent`, then prints the
JSON the LLM sent for two turns and asks the final memory
a few questions. Lines starting `# ANCHOR` mark the
pieces the book quotes."""
import json
from pathlib import Path

from agent.llm import ReplayLLM
from agent.loop import Agent

ROOT = Path(__file__).resolve().parent.parent.parent
REPLAY = ROOT / "replay" / "ch13-session.json"


class Seen:
    """Wraps an LLM and keeps every reply it gave."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.replies: list[str] = []

    def complete(self, system, messages) -> str:
        reply = self.inner.complete(system, messages)
        self.replies.append(reply)
        return reply


turns = json.loads(REPLAY.read_text())["turns"]
llm = Seen(ReplayLLM(REPLAY))
agent = Agent(llm)
for text in turns:
    agent.turn(text)


def piece(name: str, text: str) -> None:
    print(f"# ANCHOR: {name}")
    print(text)
    print(f"# ANCHOR_END: {name}")


# What the LLM sent for turns 1 and 5.
piece("json", json.dumps(json.loads(llm.replies[0]),
                         indent=2))
piece("what_if_json", json.dumps(
    json.loads(llm.replies[4]), indent=2))

# ANCHOR: after
m = agent.memory
lines = [f"{q}: {m.holds(q)}" for q in [
    "works_at sofia acme",   # turn 1
    "reports_to lena anna",  # turn 5, a what-if
    "attends 3 lena",        # turn 3, the phantom
    "attends 30 sofia"]]     # turn 7, the trap
lines.append(f"calls to the LLM: {len(llm.replies)}")
piece("after", "\n".join(lines))
# ANCHOR_END: after
