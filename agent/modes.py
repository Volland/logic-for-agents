"""The mode check: is every input bound when it is used?

ELPI uses `i:` and `o:` when it runs a predicate (an input
is matched, not unified), but it does not check modes
before running. A call whose input is still a hole simply
fails, and a rule whose output is never bound answers with
a hole. This guard reads a clause left to right, the way
the engine will run it, and catches both before anything
runs.
"""
from __future__ import annotations

from .clauses import (Call, Clause, Op, Var, text,
                      variables)
from .world import Signature


class ModeError(ValueError):
    pass


# Modes of the built-ins the fragment allows.
BUILTIN = {"std.mem": "io", "std.length": "io",
           "true": "", "fail": ""}


def _vars(t) -> set[str]:
    return set(variables(t))


def _need(bound: set[str], t, where: str) -> None:
    for v in variables(t):
        if v not in bound:
            raise ModeError(f"{where}, but {v} is not "
                            "bound yet")


# ANCHOR: goal
def goal(g, bound: set[str], sig: Signature) -> set[str]:
    """The variables bound after running g, given those
    bound before. Raises ModeError for an unbound input."""
    if isinstance(g, Op) and g.op == ",":
        return goal(g.right, goal(g.left, bound, sig), sig)
    if isinstance(g, Op) and g.op == ";":
        return (goal(g.left, bound, sig)
                & goal(g.right, bound, sig))
    if isinstance(g, Op) and g.op == "=":
        return bound | _vars(g)
    if isinstance(g, Op) and g.op == "is":
        _need(bound, g.right, f"in `{text(g)}` the "
              "right side is an input")
        return bound | _vars(g.left)
    if isinstance(g, Op):  # <, >, =<, >=
        _need(bound, g, f"`{text(g)}` compares inputs")
        return bound
    if isinstance(g, Var):
        _need(bound, g, "a goal that is a variable")
        return bound
    if isinstance(g, Call) and g.name == "not":
        goal(g.args[0], bound, sig)
        return bound  # `not` binds nothing
    if isinstance(g, Call):
        return call(g, bound, sig)
    raise ModeError(f"`{text(g)}` is not a goal")
# ANCHOR_END: goal


def call(c: Call, bound: set[str], sig: Signature
         ) -> set[str]:
    modes = sig.modes.get(c.name) or BUILTIN.get(c.name)
    if modes is None:
        return bound | _vars(c)  # not ours to judge
    out = set(bound)
    for k, (m, arg) in enumerate(zip(modes, c.args), 1):
        if m == "i":
            ty = sig.types.get(c.name, ("",) * k)[k - 1]
            _need(bound, arg, f"`{text(c)}`: input {k} "
                  f"(i:{ty}) must be known")
            if isinstance(arg, Var) and arg.name == "_":
                raise ModeError(f"`{text(c)}`: input {k} "
                                "cannot be _")
        else:
            out |= _vars(arg)
    return out


# @tg: implements:: [[decisions#Mode check and whitelist are Python guards]]
# ANCHOR: clause
def check_clause(c: Clause, sig: Signature) -> None:
    """Inputs of the head are bound on entry; the body
    runs left to right; every output of the head must be
    bound at the end."""
    modes = sig.modes.get(c.head.name, ())
    pairs = list(zip(modes, c.head.args))
    bound = set()
    for m, arg in pairs:
        if m == "i":
            bound |= _vars(arg)
    if c.body is not None:
        bound = goal(c.body, bound, sig)
    for k, (m, arg) in enumerate(pairs, 1):
        if m != "o":
            continue
        if isinstance(arg, Var) and arg.name == "_":
            raise ModeError(
                f"`{text(c.head)}`: output {k} is _, a "
                "hole in every answer")
        for v in variables(arg):
            if v not in bound:
                by = ("a fact" if c.body is None
                      else "the body")
                raise ModeError(
                    f"`{text(c.head)}`: output {k} is "
                    f"{v}, which {by} never binds: a "
                    "hole in every answer")
# ANCHOR_END: clause


def check_query(q, sig: Signature) -> None:
    goal(q, set(), sig)
