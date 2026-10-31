"""Solutions to the exercises of Chapter 11.

Run from code/:  python solutions/ch11.py
Everything is offline: no LLM is called.
"""
from leanelpi import Const, ElpiError, Program

from agent import world
from agent.memory import (Accepted, Memory, Violation,
                          engine_error)
from agent.terms import wrap


def memory_with(extra: str) -> Memory:
    """The agent's program plus `extra` (λProlog text),
    with the host predicates declared as world.load
    does. `assert_clause` cannot add declarations, so
    new kinds, types and preds go in at load time."""
    src = world.source() + "\n" + extra
    program = Program(src)
    for name in world.HOSTS:
        program = program.declare(world.pred_decl(src, name))
    return Memory(program)


def verdict(v) -> str:
    if isinstance(v, Accepted):
        return "Accepted"
    return "Rejected " + "; ".join(str(b) for b in
                                   v.violations)


print("Exercise 11.1")
# ANCHOR: ex1
# Exercise 11.1: two proposals, three memories.
m0 = Memory()
v1 = m0.propose("reports_to sofia marco.")
print(wrap(verdict(v1)))
m1 = v1.memory
v2 = m1.propose("reports_to sofia lena.")
print(wrap(verdict(v2)))
for name, m in [("m0", m0), ("m1", m1)]:
    print(name, m.ask("chain sofia M"))
# ANCHOR_END: ex1

print("Exercise 11.2")
# ANCHOR: ex2
# Exercise 11.2: a rule for events that end before
# they start. A new rule name is a new constant of
# kind `check`, so it is loaded, not asserted.
BACKWARDS = """
type backwards check.
violation backwards D :-
  event E _ _ _ S T, before T S,
  str E SE,
  D is "event " ^ SE ^ " ends before it starts".
"""
strict = memory_with(BACKWARDS)
talk = "event 13 talk [lena] porto (d 2002 9) (d 2002 8)."
print("old rules:", verdict(Memory().propose(talk)))
print(wrap("new rules: " + verdict(strict.propose(talk))))
# ANCHOR_END: ex2

print("Exercise 11.3")
# ANCHOR: ex3
# Exercise 11.3: a host predicate of our own. Python
# knows each person's office; a rule asks it.
OFFICE = """
pred office i:person, o:city.
pred away o:person, o:int.
away P E :-
  attends E P, event E K _ C _ _, physical K,
  office P O, not (C = O).
"""
src = world.source() + "\n" + OFFICE
program = Program(src).declare(
    "pred office i:person, o:city.")
OFFICES = {"anna": "lisbon", "marco": "porto",
           "lena": "berlin", "taras": "kyiv"}


def office(person: Const):
    city = OFFICES.get(person.name)
    return [Const(city)] if city else []


m = Memory(program).with_host(office=office)
print(m.ask("away P E"))
bad = m.with_host(office=lambda p: [Const("anna")])
try:
    bad.ask("away P E")
except ElpiError as e:
    print(wrap(str(e), "ElpiError: ", "  "))
# ANCHOR_END: ex3

print("Exercise 11.4")
# ANCHOR: ex4
# Exercise 11.4: all or nothing. The batch is checked
# as one; on any failure the old memory comes back.


def propose_all(m: Memory, clauses: list[str]):
    program = m.program
    try:
        for c in clauses:
            program = program.assert_clause(c)
    except ElpiError as e:
        return m, (Violation(engine_error(e), str(e)),)
    broken = m.violations_if(clauses)
    if broken:
        return m, broken
    history = m.history + tuple(clauses)
    return Memory(program, m.host, history), ()


porto = ("event 15 meeting [lena] porto "
         "(d 2003 9) (d 2003 11).")
kyiv = ("event 16 meeting [lena] kyiv "
        "(d 2003 10) (d 2003 12).")
m0 = Memory()
for c in (porto, kyiv):
    print(verdict(m0.propose(c)))
after, broken = propose_all(m0, [porto, kyiv])
print(after is m0)
for b in broken:
    print(wrap(str(b)))
# ANCHOR_END: ex4
