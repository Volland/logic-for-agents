"""Chapter 13: the whole agent, replaying a recorded
session (the same as `python -m agent`)."""
import json
from pathlib import Path

from agent.llm import ReplayLLM
from agent.loop import Agent, session

ROOT = Path(__file__).resolve().parent.parent.parent
REPLAY = ROOT / "replay" / "ch13-session.json"

# ANCHOR: run
turns = json.loads(REPLAY.read_text())["turns"]
agent = Agent(ReplayLLM(REPLAY))
session(agent, turns)
# ANCHOR_END: run
