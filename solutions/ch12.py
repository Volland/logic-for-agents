"""Solutions to the exercises of Chapter 12.

Run from code/:  python solutions/ch12.py
Everything is offline: the "LLM" is a script.
"""
from leanelpi import ElpiError, Program

from agent import modes, world
from agent.formalize import (Formalizer, GuardError,
                             consistency, guard,
                             parse_and_type, read,
                             sandbox)
from agent.memory import Memory
from agent.terms import wrap


class ScriptLLM:
    """An LLM that answers from a list."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.asked: list[list[dict]] = []

    def complete(self, system, messages):
        self.asked.append(list(messages))
        return self.replies.pop(0)


def memory_with(extra: str) -> Memory:
    """As in the Chapter 11 solutions: the agent's
    program plus `extra`, loaded (not asserted)."""
    src = world.source() + "\n" + extra
    program = Program(src)
    for name in world.HOSTS:
        program = program.declare(world.pred_decl(src, name))
    return Memory(program)


def stage(m: Memory, text: str) -> str:
    try:
        guard(m, text)
    except GuardError as e:
        return e.stage
    return "passes"


m = Memory()

print("Exercise 12.1")
# ANCHOR: ex1
# Exercise 12.1: be the LLM, then be the guards.
for text in ["works_at sofia kyiv.",
             "knows anna X.",
             "chain sofia anna.",
             "knows X Y :- colleague X Y.",
             "reports_to sofia sofia."]:
    print(f"{stage(m, text):12}{text}")
# ANCHOR_END: ex1

print("Exercise 12.2")
# ANCHOR: ex2
# Exercise 12.2: a retry of our own.
llm = ScriptLLM(
    "knows X Y :- works_at X acme.",
    "knows X Y :- works_at X acme,"
    " works_at Y acme, differ X Y.")
r = Formalizer(llm).add(m, "Everyone at Acme knows "
                        "everyone else at Acme.")
for a in r.attempts:
    print("| " + a.text)
print(wrap(llm.asked[1][-1]["content"], "> ", "> "))
print(r.ok, r.memory.ask("knows marco Y"))
# ANCHOR_END: ex2

print("Exercise 12.3")
# ANCHOR: ex3
# Exercise 12.3: a self-report passes every guard,
# then breaks a query that used to stop.
selfish = guard(m, "reports_to sofia sofia.")
try:
    selfish.solve("chain sofia M", fuel=10_000)
except ElpiError as e:
    print(e)
SELF = """
type self_report check.
violation self_report D :-
  reports_to P P, str P SP,
  D is SP ^ " reports to " ^ SP.
"""
try:
    guard(memory_with(SELF), "reports_to sofia sofia.")
except GuardError as e:
    print(e)
# ANCHOR_END: ex3

print("Exercise 12.4")
# ANCHOR: ex4
# Exercise 12.4: a second open predicate, and our own
# pipeline built from the same guards.
TRUSTS = "pred trusts o:person, o:person."
wider = memory_with(TRUSTS)
sig = world.read_signature(world.source() + TRUSTS)
OPEN = {"knows", "trusts"}


def guard_wider(m: Memory, text: str) -> Memory:
    program = parse_and_type(m, text)
    clauses = read(text)
    for c in clauses:
        try:
            modes.check_clause(c, sig)
        except modes.ModeError as e:
            raise GuardError("mode", str(e)) from e
        if c.head.name not in OPEN:
            raise GuardError("allowed", (
                f"{c.head.name} is not open; open: "
                + ", ".join(sorted(OPEN))))
    sandbox(m, program, clauses, 20_000)
    consistency(m, clauses)
    return Memory(program, m.host,
                  m.history + (text.strip(),))


for text in ["trusts X Y :- reports_to X Y.",
             "trusts X Y :- works_at X acme.",
             "trusts X Y :- trusts Y X.",
             "reports_to sofia marco."]:
    try:
        new = guard_wider(wider, text)
        print("passes:", new.ask("trusts X anna"))
    except GuardError as e:
        print(wrap(str(e), "", "  "))
# ANCHOR_END: ex4
