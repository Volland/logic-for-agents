"""The agent's memory: a persistent logic program.

A commit never changes a memory. It returns a new one,
built with `assert_clause`, and the old one still answers
as before. Every proposal is checked first: the type
checker, then the consistency rules under `=>`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Union

from leanelpi import ElpiError, Program, Solution

from . import world
from .terms import show, tree

FUEL = 100_000  # resolution steps per query


# ANCHOR: verdicts
@dataclass(frozen=True)
class Violation:
    rule: str     # the broken rule: bilocation, ...
    detail: str   # what breaks it, in words

    def __str__(self) -> str:
        return f"{self.rule}: {self.detail}"


@dataclass(frozen=True)
class Accepted:
    clause: str
    memory: "Memory"


@dataclass(frozen=True)
class Rejected:
    clause: str
    violations: tuple[Violation, ...]


Verdict = Union[Accepted, Rejected]
# ANCHOR_END: verdicts


def engine_error(e: ElpiError) -> str:
    """Which guard of the engine spoke: the parser or
    the type checker (an unknown name or a wrong type)."""
    text = str(e)
    if "undeclared constant" in text:
        return "unknown"
    if "has type" in text:
        return "ill_typed"
    return "syntax"


def unclause(text: str) -> str:
    """`works_at lena lumen.` -> `works_at lena lumen`."""
    return text.strip().removesuffix(".").strip()


Host = dict[str, Callable]


@dataclass(frozen=True)
class Memory:
    program: Program = field(default_factory=world.load)
    host: Host = field(default_factory=dict)
    history: tuple[str, ...] = ()

    # ANCHOR: propose
    def propose(self, clause: str) -> Verdict:
        """Check a clause; commit it only if nothing
        breaks. This memory is never changed."""
        try:  # parse and type check
            after = self.program.assert_clause(clause)
        except ElpiError as e:
            v = Violation(engine_error(e), str(e))
            return Rejected(clause, (v,))
        broken = self.violations_if([clause])
        if broken:
            return Rejected(clause, broken)
        history = self.history + (clause.strip(),)
        new = Memory(after, self.host, history)
        return Accepted(clause, new)
    # ANCHOR_END: propose

    # ANCHOR: violations_if
    def violations_if(self, clauses: list[str]
                      ) -> tuple[Violation, ...]:
        """The rules broken if `clauses` were in memory,
        asked under `=>`: nothing is committed."""
        new = ", ".join(unclause(c) for c in clauses)
        found = self.solve(f"check [{new}] N D")
        return tuple(Violation(show(s.terms["N"]),
                               s.terms["D"])
                     for s in found)
    # ANCHOR_END: violations_if

    def extend(self, text: str) -> "Memory":
        """Commit without checking: for clauses that
        have already passed every guard."""
        after = self.program.assert_clause(text)
        history = self.history + (text.strip(),)
        return Memory(after, self.host, history)

    def with_host(self, **fns: Callable) -> "Memory":
        return Memory(self.program, {**self.host, **fns},
                      self.history)

    # ANCHOR: ask
    def solve(self, query: str, *, limit: int | None = None,
              fuel: int = FUEL) -> list[Solution]:
        return self.program.solve_host(
            query, self.host, limit=limit, fuel=fuel)

    def ask(self, query: str) -> list[dict[str, str]]:
        """Every answer, as ELPI prints the values."""
        return [s.bindings for s in self.solve(query)]

    def holds(self, query: str) -> bool:
        return bool(self.solve(query, limit=1))
    # ANCHOR_END: ask

    # ANCHOR: why
    def why(self, goal: str) -> str:
        """The proof of a goal, printed as a tree."""
        found = self.solve(f"prove ({unclause(goal)}) P",
                           limit=1)
        if not found:
            return f"no proof of {unclause(goal)}"
        return "\n".join(tree(found[0].terms["P"]))
    # ANCHOR_END: why

    # ANCHOR: what_if
    def what_if(self, assume: list[str], query: str
                ) -> list[dict[str, str]]:
        """Answers to `query` if `assume` were true.
        The memory is not changed."""
        facts = ", ".join(unclause(a) for a in assume)
        return self.ask(f"[{facts}] => ({query})")
    # ANCHOR_END: what_if
