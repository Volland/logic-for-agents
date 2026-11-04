"""Chapter 12: what the guard loop costs. The retry session
again, metered: model calls, characters sent and received,
and the guard that stopped each failed try.

  python agent/examples/ch12_cost.py          # the replay
  python agent/examples/ch12_cost.py --live   # Claude, with
                                              # seconds and tokens
"""
import sys
from collections import Counter
from pathlib import Path

from agent.formalize import Formalizer, system_prompt
from agent.llm import AnthropicLLM, Metered, ReplayLLM
from agent.memory import Memory

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE = "--live" in sys.argv
inner = AnthropicLLM() if LIVE else \
    ReplayLLM(ROOT / "replay" / "ch12-retry.json")

# ANCHOR: run
llm = Metered(inner)
f = Formalizer(llm, tries=3)
m = Memory()
results = []
for request in ["Sofia works at Acme.",
                "People know each other if they met or "
                "are colleagues, and knowing goes both "
                "ways."]:
    results.append(f.add(m, request))
    m = results[-1].memory
results.append(f.ask(m, "Whom does Sofia know?"))
# ANCHOR_END: run

# ANCHOR: report
print(f"system prompt: {len(system_prompt())} characters")
n = 0
for r in results:
    for a in r.attempts:
        c = llm.calls[n]
        n += 1
        stage = a.error.stage if a.error else "passed"
        line = (f"call {n}: sent {c.sent:5}, "
                f"got {c.received:4}  {stage}")
        if LIVE:
            line += (f"  {c.seconds:.1f}s"
                     f"  tokens {c.tokens}")
        print(line)
first = sum(len(r.attempts) == 1 and r.ok
            for r in results)
stops = Counter(a.error.stage for r in results
                for a in r.attempts if a.error)
print(f"requests: {len(results)}, calls: {n}, "
      f"passed on the first try: {first}")
print("failed tries by guard:", dict(stops))
# ANCHOR_END: report
