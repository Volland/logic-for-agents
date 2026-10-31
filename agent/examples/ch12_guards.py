"""Chapter 12: each guard, and an LLM mistake it catches.
One try each: no feedback yet."""
from pathlib import Path

from agent.formalize import Formalizer
from agent.llm import ReplayLLM
from agent.memory import Memory
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
llm = ReplayLLM(ROOT / "replay" / "ch12-guards.json")

# ANCHOR: requests
ADD = [
    "Sofia works at Lumen.",
    "Two people know each other if they met, "
    "unless they are the same person.",
    "Sofia works at Acme.",
    "Olena works at Lumen.",
    "Everyone at Acme knows each other.",
    "Everyone who works at Lumen reports to Lena.",
    "People who met know each other, and knowing "
    "goes both ways.",
    "Anna and Lena met in Berlin on day 2000, "
    "from 10 to 12.",
]
ASK = ["When did the kickoff start, in minutes "
       "since day 0?"]
# ANCHOR_END: requests


def report(request: str, result) -> None:
    attempt = result.attempts[-1]
    print(wrap(request))
    for line in attempt.text.splitlines():
        print("  | " + line)
    e = attempt.error
    if e is None:
        print("  ok")
    else:
        print(f"  rejected by the {e.stage} check:")
        print(wrap(e.message, "  ", "  "))
    print()


# ANCHOR: run
f = Formalizer(llm, tries=1)
m = Memory()
for request in ADD:
    report(request, f.add(m, request))
for question in ASK:
    report(question, f.ask(m, question))
# ANCHOR_END: run
