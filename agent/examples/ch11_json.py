"""Chapter 11: the LLM reads a sentence and proposes
facts as JSON. Parsing checks them, then the memory."""
from pathlib import Path

from agent import parse
from agent.llm import ReplayLLM
from agent.memory import Accepted, Memory
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
llm = ReplayLLM(ROOT / "replay" / "ch11-extract.json")

# ANCHOR: system
SYSTEM = """Extract facts from the user's sentence.
Answer with JSON only: {"facts": [FACT, ...]}.
A FACT has "pred" and these keys:
""" + "\n".join(f"  {p}: {', '.join(keys)}"
                for p, keys in parse.SCHEMA.items()) + """
A time is {"day": D, "hour": H}. Give a new event
a new id; events 1 and 2 exist."""
# ANCHOR_END: system


# ANCHOR: extract
def remember(m: Memory, sentence: str) -> Memory:
    msg = {"role": "user", "content": sentence}
    reply = llm.complete(SYSTEM, [msg])
    for fact in parse.facts(reply):
        try:
            clause = parse.to_clause(fact)
        except parse.ParseError as e:
            print(wrap(str(e), "  parse: ", "  "))
            continue
        v = m.propose(clause)
        if isinstance(v, Accepted):
            print("  commit:\n    " + clause)
            m = v.memory
        else:
            for broken in v.violations:
                print(f"  reject: {broken.rule}\n"
                      f"    {broken.detail}")
    return m
# ANCHOR_END: extract


# ANCHOR: run
m = Memory()
for sentence in [
        "Anna and Lena met in Berlin on day 2000, "
        "from 10 to 12.",
        "Lena and Taras had a call from Kyiv on "
        "day 2001, 9 to 10.",
        "Taras now also reports to Anna.",
        "Sofia works at the Porto office of Acme.",
        "Olena works at Lumen.",
        "Acme hired Sofia."]:
    print(wrap(sentence))
    m = remember(m, sentence)
print(len(m.history), "fact(s) committed")
# ANCHOR_END: run
