"""Chapter 12: the consistency guard."""
import json
from pathlib import Path

from agent.formalize import GuardError, guard, guard_query
from agent.memory import Memory
from agent.parse import strip_fence
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
REC = ROOT / "replay" / "ch12-guards.json"
# What the LLM wrote, by the name of its step.
WROTE = {s["step"]: strip_fence(s["response"]) for s in
         json.loads(REC.read_text("utf-8"))["steps"]}


def run(text: str, query: bool = False) -> None:
    for line in text.splitlines():
        print("| " + line)
    try:
        if query:
            answers = guard_query(m, text)
        else:
            guard(m, text)
            answers = []
    except GuardError as e:
        print(f"  rejected by the {e.stage} check:")
        print(wrap(e.message, "  ", "  "))
        return
    print("  passes")
    for a in answers:
        print("  ", a)


m = Memory()

# ANCHOR: run
run(WROTE["a contradictory fact"])
# ANCHOR_END: run

# ANCHOR: ours
# Not from the recording: a second manager for Marco.
run("reports_to marco lena.")
# ANCHOR_END: ours
