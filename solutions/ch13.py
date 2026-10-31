"""Chapter 13 solutions. Offline: replay files stand in
for the model, and no key or network is needed."""
import json
from pathlib import Path

from leanelpi import Program

from agent import world
from agent.examples.ch13_eval import CASES, report
from agent.host import SamePerson
from agent.llm import ReplayLLM
from agent.loop import Agent, system_prompt
from agent.memory import Memory
from agent.terms import show

ROOT = Path(__file__).resolve().parent.parent
REPLAY = ROOT / "replay"


# ANCHOR: ex1
# Exercise 13.1: an LLM that wraps another and counts
# who called it. The loop and the rule `by_name` send
# different system prompts.
class Counting:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.loop = system_prompt()
        self.calls: dict[str, int] = {}
        self.names: list[str] = []

    def complete(self, system, messages) -> str:
        who = "the loop" if system == self.loop \
            else "a rule"
        self.calls[who] = self.calls.get(who, 0) + 1
        if who == "a rule":
            self.names.append(messages[-1]["content"])
        return self.inner.complete(system, messages)


session = REPLAY / "ch13-session.json"
llm = Counting(ReplayLLM(session))
agent = Agent(llm)
for text in json.loads(session.read_text())["turns"]:
    agent.turn(text)
for who, n in llm.calls.items():
    print(f"calls from {who}: {n}")
print("names a rule asked about:", ", ".join(llm.names))
# ANCHOR_END: ex1


# ANCHOR: ex2
# Exercise 13.2: the LLM's guesses in an answer, read
# from the proof term, not from the printed tree.
def leaves(proof, source: str) -> list:
    """The goals a proof takes from `source`."""
    if proof.name == "leaf":
        origin, goal = proof.args
        return [goal] if origin == source else []
    if proof.name == "by":
        return leaves(proof.args[2], source)
    if proof.name == "and":
        return (leaves(proof.args[0], source) +
                leaves(proof.args[1], source))
    return []  # empty


def guesses(memory: Memory, goal: str) -> list[str]:
    found = memory.solve(f"prove ({goal}) P", limit=1)
    if not found:
        return []
    return [show(g) for g in
            leaves(found[0].terms["P"], "llm")]


names = ReplayLLM(REPLAY / "ch13-same-person.json")
m = Memory().with_host(same_person=SamePerson(names))
for goal in ['met_by_name "Anya" "Marko"',
             "colleague anna marco"]:
    found = guesses(m, goal)
    print(f"{goal}: {len(found)} guesses")
    for g in found:
        print("  " + g)
# ANCHOR_END: ex2


# ANCHOR: ex3
# Exercise 13.3: the travel rule nobody wrote in
# Chapter 1. `check` is a kind, and `assert_clause`
# cannot add declarations, so we build a new program.
TRAVEL = """
type travel check.
% One person at two physical events in two cities,
% with less than four hours between them.
violation travel D :-
  attends E1 P, attends E2 P, not (E1 = E2),
  event E1 K1 _ C1 _ End, physical K1,
  event E2 K2 _ C2 Start _, physical K2,
  not (C1 = C2),
  minutes End M1, minutes Start M2,
  Gap is M2 - M1, Gap >= 0, Gap < 240,
  str P SP, str C1 SC1, str C2 SC2,
  D is SP ^ ": no time to travel from " ^ SC1
    ^ " to " ^ SC2.
"""


def with_rules(extra: str) -> Memory:
    src = world.source() + extra
    program = Program(src)
    for name in world.HOSTS:
        program = program.declare(
            world.pred_decl(src, name))
    return Memory(program)


strict = with_rules(TRAVEL)
report(strict, sorted(CASES, key=lambda c: c[1]))
print(strict.propose(
    "event 33 talk [anna] porto (d 2000 14) (d 2000 15)."
).violations[0])
# ANCHOR_END: ex3
