"""Host predicates: calls from the rules into Python.

The rules declare `now`, `calendar` and `same_person`
(agent/rules/host.elpi) and call them like any predicate.
During `solve_host` the engine hands each call to the
function registered under its name. A function gets the
`i:` arguments and returns rows of `o:` values.
"""
from __future__ import annotations

import json

from leanelpi import App, Const

from . import world
from .llm import LLM
from .parse import strip_fence

Slot = tuple[tuple[int, int], tuple[int, int]]


def moment(day: int, hour: int) -> App:
    """`(d day hour)` as a value the binding can return."""
    return App("d", (day, hour))


# ANCHOR: clock
def clock(day: int, hour: int):
    """`now`: a clock stopped at one moment, so every
    run prints the same thing. A real one would read
    the system time."""
    def now():
        return [moment(day, hour)]
    return now
# ANCHOR_END: clock


# ANCHOR: calendar
def calendar(slots: dict[str, list[Slot]]):
    """`calendar P From To`: busy slots kept outside the
    memory, e.g. in a calendar service."""
    def busy(person: Const):
        return [(moment(*a), moment(*b))
                for a, b in slots.get(person.name, [])]
    return busy
# ANCHOR_END: calendar


SYSTEM = """You match names to people in a small world.
The people are: {people}.
Given a name as the user wrote it, answer with JSON only:
{{"person": "<one of the people>"}} if the name means one
of them (a nickname, a spelling, a transliteration), or
{{"person": null}} if it means none of them."""


# ANCHOR: same_person
class SamePerson:
    """`same_person Name P`, answered by the LLM. The
    answer is a guess: the binding checks its type, and
    the rules that called it still decide."""

    def __init__(self, llm: LLM) -> None:
        people = world.signature().constants["person"]
        self.system = SYSTEM.format(
            people=", ".join(sorted(people)))
        self.llm = llm
        self.answers: dict[str, list[Const]] = {}

    def __call__(self, name: str) -> list[Const]:
        if name not in self.answers:  # ask once per name
            msg = {"role": "user", "content": name}
            reply = self.llm.complete(self.system, [msg])
            guess = json.loads(strip_fence(reply))
            match = guess.get("person")
            self.answers[name] = (
                [Const(match)] if match else [])
        return self.answers[name]
# ANCHOR_END: same_person
