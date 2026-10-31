"""Chapter 13: a rule asks the LLM whether two names
mean one person, and still decides for itself."""
from pathlib import Path

from leanelpi import ElpiError

from agent.host import SamePerson
from agent.llm import ReplayLLM
from agent.memory import Memory
from agent.terms import wrap

ROOT = Path(__file__).resolve().parent.parent.parent
llm = ReplayLLM(ROOT / "replay" / "ch13-same-person.json")

# ANCHOR: host
names = SamePerson(llm)
m = Memory().with_host(same_person=names)
# ANCHOR_END: host

# ANCHOR: ask
for a, b in [("Anya", "Marko"), ("Lenka", "Marko"),
             ("Bob", "Marko"), ("Lisa", "Marko"),
             ("Olena", "Marko")]:
    q = f'met_by_name "{a}" "{b}"'
    try:
        print(q, "->", m.holds(q))
    except ElpiError as e:
        print(q, "->")
        print(wrap(str(e), "  ElpiError: ", "  "))
# ANCHOR_END: ask

# ANCHOR: guesses
for name, rows in names.answers.items():
    print(f"  the LLM said {name} is",
          rows[0].name if rows else "nobody")
# ANCHOR_END: guesses

# ANCHOR: why
print(m.why('met_by_name "Anya" "Marko"'))
# ANCHOR_END: why
