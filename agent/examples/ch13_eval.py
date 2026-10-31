"""Chapter 13: measuring what the logic layer catches.

Ten proposals, written as the LLM's JSON, each labeled
with what really happened in the story. The labels are
ours, authored like the replay files: the counts measure
the rules on this set, not a model."""
from agent.memory import Accepted, Memory
from agent.parse import ParseError, to_clause


def ev(eid, kind, who, city, day, start, end):
    """An event the LLM proposes, as JSON."""
    return {"pred": "event", "id": eid, "kind": kind,
            "who": who, "city": city,
            "from": {"day": day, "hour": start},
            "to": {"day": day, "hour": end}}


# ANCHOR: cases
# name, was it true?, what the LLM proposed
CASES = [
    ("the phantom", False,
     ev(3, "meeting", ["anna", "lena"], "berlin",
        2000, 10, 12)),
    ("Taras now reports to Anna", True,
     {"pred": "reports_to", "person": "taras",
      "manager": "anna"}),
]
# ANCHOR_END: cases
CASES += [
    ("Berlin, after the kickoff", False,
     ev(4, "meeting", ["anna", "lena"], "berlin",
        2000, 11, 12)),
    ("a call nobody had", False,
     ev(14, "call", ["sofia", "taras"], "lviv",
        2001, 9, 10)),
    ("the sofia trap", False,
     ev(30, "meeting", ["sofia", "taras"], "lviv",
        900, 9, 10)),
    ("a second boss for Marco", False,
     {"pred": "reports_to", "person": "marco",
      "manager": "lena"}),
    ("arguments swapped", False,
     {"pred": "works_at", "person": "acme",
      "org": "sofia"}),
    ("Sofia joins Acme", True,
     {"pred": "works_at", "person": "sofia",
      "org": "acme"}),
    ("Anna's talk in Porto", True,
     ev(33, "talk", ["anna"], "porto", 2000, 14, 15)),
    ("Olena reports to Lena", True,
     {"pred": "reports_to", "person": "olena",
      "manager": "lena"}),
]


# ANCHOR: judge
def judge(memory, fact):
    """The logic layer's verdict on one proposal:
    (remembered?, the rule that refused it)."""
    try:
        clause = to_clause(fact)
    except ParseError:
        return False, "parse"
    verdict = memory.propose(clause)
    if isinstance(verdict, Accepted):
        return True, "-"
    return False, verdict.violations[0].rule
# ANCHOR_END: judge


# ANCHOR: report
def report(memory, cases):
    """Judge every case against the same memory and
    count the four outcomes."""
    count = {}
    for name, true, fact in cases:
        kept, rule = judge(memory, fact)
        label = "true " if true else "false"
        said = "remembered" if kept else "refused   "
        print(f"{label}  {said}  {rule:14} {name}")
        key = (true, kept)
        count[key] = count.get(key, 0) + 1
    for true in (False, True):
        kept = count.get((true, True), 0)
        refused = count.get((true, False), 0)
        print(f"{'true' if true else 'false'} proposals:"
              f" {kept + refused}, remembered {kept},"
              f" refused {refused}")
# ANCHOR_END: report


if __name__ == "__main__":
    # sort for the printout: false ones first
    report(Memory(), sorted(CASES, key=lambda c: c[1]))
