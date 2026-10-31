"""Chapter 11: the phantom arrives as JSON. Parsing turns
it into a clause; the memory decides."""
from pathlib import Path

from agent import parse
from agent.llm import ReplayLLM
from agent.memory import Memory
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
llm = ReplayLLM(ROOT / "replay" / "ch11-extract.json")

# The prompt of ch11_json.py (a replay does not read it).
SYSTEM = """Extract facts from the user's sentence.
Answer with JSON only: {"facts": [FACT, ...]}.
A FACT has "pred" and these keys:
""" + "\n".join(f"  {p}: {', '.join(keys)}"
                for p, keys in parse.SCHEMA.items()) + """
A time is {"day": D, "hour": H}. Give a new event
a new id; events 1 and 2 exist."""

# ANCHOR: call
sentence = ("Anna and Lena met in Berlin on day 2000, "
            "from 10 to 12.")
msg = {"role": "user", "content": sentence}
reply = llm.complete(SYSTEM, [msg])
print(wrap(reply))
# ANCHOR_END: call

# ANCHOR: clause
fact = parse.facts(reply)[0]
clause = parse.to_clause(fact)
print(type(fact).__name__, "->", type(clause).__name__)
print(clause)
# ANCHOR_END: clause

# ANCHOR: verdict
verdict = Memory().propose(clause)
print(type(verdict).__name__)
print(verdict.violations[0])
# ANCHOR_END: verdict
