"""`python -m agent`: replay the Chapter 13 session.

  python -m agent                  # replay, no key needed
  python -m agent --live           # call Claude
  python -m agent --live --record replay/mine.json
  python -m agent --live --chat    # type your own turns
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .llm import AnthropicLLM, RecordingLLM, ReplayLLM
from .loop import Agent, session

ROOT = Path(__file__).resolve().parent.parent
SESSION = ROOT / "replay" / "ch13-session.json"


def chat(agent: Agent) -> list[str]:
    turns = []
    for line in sys.stdin:
        if line.strip():
            turns.append(line.strip())
            session(agent, [line.strip()])
    return turns


# ANCHOR: main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent")
    ap.add_argument("--replay", default=str(SESSION))
    ap.add_argument("--live", action="store_true",
                    help="call Claude (ANTHROPIC_API_KEY)")
    ap.add_argument("--record", metavar="PATH",
                    help="save the live calls as a replay")
    ap.add_argument("--chat", action="store_true",
                    help="read turns from stdin")
    args = ap.parse_args(argv)

    script = json.loads(Path(args.replay).read_text())
    if args.live:
        llm = AnthropicLLM()
        if args.record:
            llm = RecordingLLM(llm, "turn")
    else:
        llm = ReplayLLM(args.replay)
    agent = Agent(llm)
    if args.chat:
        turns = chat(agent)
    else:
        turns = script["turns"]
        session(agent, turns)
    if isinstance(llm, RecordingLLM):
        llm.save(args.record, turns=turns)
    if isinstance(llm, ReplayLLM) and not llm.finished():
        print("replay: unused steps in the replay file",
              file=sys.stderr)
        return 1
    return 0
# ANCHOR_END: main


if __name__ == "__main__":
    sys.exit(main())
