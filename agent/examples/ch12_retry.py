"""Chapter 12: the guard's message goes back to the LLM,
and the next try passes."""
from pathlib import Path

from agent.formalize import Formalizer
from agent.llm import ReplayLLM
from agent.memory import Memory
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
llm = ReplayLLM(ROOT / "replay" / "ch12-retry.json")


def report(result) -> None:
    for n, a in enumerate(result.attempts, 1):
        print(f"try {n}:")
        for line in a.text.splitlines():
            print("  | " + line)
        if a.error:
            print(wrap(a.error.feedback(), "  > ",
                       "  > "))
    print("committed" if result.ok else "gave up")
    print()


# ANCHOR: retry
f = Formalizer(llm, tries=3)
m = Memory()
r = f.add(m, "Sofia works at Acme.")
report(r)
r = f.add(r.memory, "People know each other if they "
          "met or are colleagues, and knowing goes "
          "both ways.")
report(r)
m = r.memory
# ANCHOR_END: retry

# ANCHOR: use
for clause in m.history:
    print(clause)
q = f.ask(m, "Whom does Sofia know?")
print(q.attempts[-1].text)
for answer in q.answers:
    print("  ", answer)
print(m.why("knows sofia anna"))
# ANCHOR_END: use
