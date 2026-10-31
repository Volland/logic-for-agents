"""The LLM writes λProlog; the guards decide (Chapter 12).

A generated answer passes six guards, in order, before it
can touch memory:

  parse -> type -> mode -> allowed -> sandbox
        -> consistency -> commit

The parser and the type checker are the engine's own (we
pass on its messages word for word). The mode check and
the whitelist are ours (agent/modes.py, below). The
sandbox runs the new clauses with a fuel budget. The
consistency check asks the rules under `=>`. A failure
becomes a message for the LLM, which may try again.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from leanelpi import ElpiError, Program

from . import modes, world
from .clauses import (Clause, FragmentError, calls,
                      quantify, read_clauses, read_query)
from .llm import LLM, Message
from .memory import Memory
from .parse import strip_fence

FUEL = 20_000  # resolution steps for a sandbox run

STAGES = ("parse", "type", "mode", "allowed", "sandbox",
          "consistency")

# ANCHOR: policy
# Facts may only be about the memory's own predicates;
# rules may only define the open ones (open.elpi).
FACTS = frozenset({"works_at", "reports_to", "event"})
RULES = frozenset({"knows"})
# Bodies and queries may call the public predicates
# and these built-ins, nothing else.
BUILTINS = frozenset({"std.mem", "std.length", "not",
                      "true", "fail"})
PRIVATE = frozenset({"rule", "direct", "prove", "check",
                     "violation", "str", "question"})
# ANCHOR_END: policy


# ANCHOR: guard_error
@dataclass
class GuardError(Exception):
    stage: str     # which guard: one of STAGES
    message: str   # what it said

    def __str__(self) -> str:
        return f"{self.stage}: {self.message}"

    def feedback(self) -> str:
        """The message the LLM gets back."""
        return (f"Rejected by the {self.stage} check:\n"
                f"{self.message}\n"
                "Answer again with corrected λProlog "
                "only.")
# ANCHOR_END: guard_error


def engine_stage(e: ElpiError) -> str:
    text = str(e)
    if "has type" in text or "undeclared" in text:
        return "type"
    return "parse"


# --- The guards, one function each ----------------------

def parse_and_type(memory: Memory, text: str) -> Program:
    """The engine's parser and type checker: assert the
    text into a copy of memory (the sandbox)."""
    try:
        return memory.program.assert_clause(text)
    except ElpiError as e:
        if str(e) == "assert expects clauses":
            raise GuardError("parse", "only clauses are "
                             "allowed: the signature is "
                             "fixed") from e
        raise GuardError(engine_stage(e), str(e)) from e


def read(text: str) -> list[Clause]:
    try:
        return read_clauses(text)
    except FragmentError as e:
        raise GuardError("parse", str(e)) from e


def check_modes(clauses: list[Clause]) -> None:
    sig = world.signature()
    for c in clauses:
        try:
            modes.check_clause(c, sig)
        except modes.ModeError as e:
            raise GuardError("mode", str(e)) from e


# ANCHOR: allowed
def check_allowed(clauses: list[Clause]) -> None:
    for c in clauses:
        name, rule = c.head.name, c.body is not None
        if rule and name not in RULES:
            raise GuardError("allowed", (
                f"a rule may not define {name}; rules may"
                f" only define: {', '.join(sorted(RULES))}"
            ))
        if not rule and name not in FACTS | RULES:
            raise GuardError("allowed", (
                f"a fact may not be about {name}; facts "
                f"may be about: {', '.join(sorted(FACTS))}"
            ))
        check_calls(c.body)
# ANCHOR_END: allowed


def check_calls(body) -> None:
    public = set(world.signature().modes) - PRIVATE
    for call in calls(body):
        if call.name not in public | BUILTINS:
            raise GuardError("allowed", (
                f"{call.name} may not be called here"))


# ANCHOR: sandbox
def sandbox(memory: Memory, program: Program,
            clauses: list[Clause], fuel: int) -> None:
    """Run every predicate the clauses define, with all
    arguments open, on a budget of `fuel` steps."""
    for c in {c.head.name: c for c in clauses}.values():
        holes = " ".join(f"X{k}" for k in
                         range(1, len(c.head.args) + 1))
        query = f"{c.head.name} {holes}".strip()
        try:
            program.solve_host(query, memory.host,
                               fuel=fuel)
        except ElpiError as e:
            raise GuardError(
                "sandbox", f"{e}\nwhile running `{query}`"
            ) from e
# ANCHOR_END: sandbox


# ANCHOR: consistency
def consistency(memory: Memory,
                clauses: list[Clause]) -> None:
    """Assume the clauses with `=>` and ask the rules."""
    new = [quantify(c) for c in clauses]
    broken = memory.violations_if(new)
    if broken:
        lines = "\n".join(str(v) for v in broken)
        raise GuardError("consistency", lines)
# ANCHOR_END: consistency


# @tg: implements:: [[decisions#Python logic layer for Part III]]
# ANCHOR: guard
def guard(memory: Memory, text: str,
          fuel: int = FUEL) -> Memory:
    """Every guard, in order; the new memory if all
    pass. Raises GuardError at the first that fails."""
    program = parse_and_type(memory, text)
    clauses = read(text)
    check_modes(clauses)
    check_allowed(clauses)
    sandbox(memory, program, clauses, fuel)
    consistency(memory, clauses)
    history = memory.history + (text.strip(),)
    return Memory(program, memory.host, history)
# ANCHOR_END: guard


_ASSERT_POS = re.compile(r"<assert>:(\d+):")


# ANCHOR: guard_query
def guard_query(memory: Memory, query: str,
                fuel: int = FUEL) -> list[dict[str, str]]:
    """The query guards; then its answers."""
    q = query.strip().removesuffix(".")
    try:  # type-check it as the body of a clause
        memory.program.assert_clause(
            f"question :-\n{q}.")
    except ElpiError as e:
        msg = _ASSERT_POS.sub(
            lambda m: f"<query>:{int(m[1]) - 1}:", str(e))
        raise GuardError(engine_stage(e), msg) from e
    try:
        goal = read_query(q)
    except FragmentError as e:
        raise GuardError("parse", str(e)) from e
    try:
        modes.check_query(goal, world.signature())
    except modes.ModeError as e:
        raise GuardError("mode", str(e)) from e
    check_calls(goal)
    try:
        return [s.bindings for s in
                memory.solve(q, fuel=fuel)]
    except ElpiError as e:
        raise GuardError("sandbox", str(e)) from e
# ANCHOR_END: guard_query


# --- Talking to the LLM ---------------------------------

SYSTEM = """You write λProlog (the ELPI dialect) for the \
memory of an assistant agent. This signature is the \
contract: use only these kinds, constants and predicates.

{contract}

- Facts may only be about: {facts}.
- Rules may only define: {rules}.
- Never write kind, type or pred declarations.
- End every clause with a period.
- A query is one goal, with no period.
- Answer with λProlog only, no prose."""


def system_prompt() -> str:
    return SYSTEM.format(contract=world.contract(),
                         facts=", ".join(sorted(FACTS)),
                         rules=", ".join(sorted(RULES)))


@dataclass(frozen=True)
class Attempt:
    text: str
    error: GuardError | None = None


@dataclass(frozen=True)
class Result:
    memory: Memory
    attempts: tuple[Attempt, ...]
    answers: list[dict[str, str]] | None = None

    @property
    def ok(self) -> bool:
        return self.attempts[-1].error is None


@dataclass
class Formalizer:
    llm: LLM
    tries: int = 3
    fuel: int = FUEL
    system: str = field(default_factory=system_prompt)

    # ANCHOR: retry
    def add(self, memory: Memory, request: str) -> Result:
        """Ask for clauses; guard them; on a failure,
        send the guard's message back and try again."""
        ask = f"Write λProlog clauses for: {request}"
        messages: list[Message] = [user(ask)]
        attempts: list[Attempt] = []
        for _ in range(self.tries):
            reply = self.llm.complete(self.system,
                                      messages)
            text = strip_fence(reply)
            try:
                new = guard(memory, text, self.fuel)
            except GuardError as e:
                attempts.append(Attempt(text, e))
                messages += [assistant(reply),
                             user(e.feedback())]
                continue
            attempts.append(Attempt(text))
            return Result(new, tuple(attempts))
        return Result(memory, tuple(attempts))
    # ANCHOR_END: retry

    def ask(self, memory: Memory, question: str) -> Result:
        """The same loop for a query: its answers come
        back in `Result.answers`."""
        ask = f"Write one λProlog query for: {question}"
        messages: list[Message] = [user(ask)]
        attempts: list[Attempt] = []
        for _ in range(self.tries):
            reply = self.llm.complete(self.system,
                                      messages)
            text = strip_fence(reply)
            try:
                answers = guard_query(memory, text,
                                      self.fuel)
            except GuardError as e:
                attempts.append(Attempt(text, e))
                messages += [assistant(reply),
                             user(e.feedback())]
                continue
            attempts.append(Attempt(text))
            return Result(memory, tuple(attempts), answers)
        return Result(memory, tuple(attempts))


def user(text: str) -> Message:
    return {"role": "user", "content": text}


def assistant(text: str) -> Message:
    return {"role": "assistant", "content": text}
