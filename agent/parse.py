"""From the LLM's JSON to a typed clause.

Parsing is checking: every key must be one we expect and
every name must be a constant of the right kind in the
world. The engine's type checker runs again on the
clause; this is the first line, with errors in the
LLM's own terms.
"""
from __future__ import annotations

import json
from typing import Any

from . import world


class ParseError(ValueError):
    """The LLM's JSON does not describe a fact we know."""


# ANCHOR: schema
# For each predicate: its JSON keys, in argument order,
# and the type each key must have.
SCHEMA = {
    "works_at":   {"person": "person", "org": "org"},
    "reports_to": {"person": "person",
                   "manager": "person"},
    "event":      {"id": "int", "kind": "evkind",
                   "who": "list person", "city": "city",
                   "from": "time", "to": "time"},
    "attends":    {"event": "int", "person": "person"},
}
# ANCHOR_END: schema


# ANCHOR: value
def value(key: str, ty: str, v: Any) -> str:
    """One JSON value as λProlog text of type `ty`."""
    if ty == "int":
        if type(v) is not int or v < 0:
            raise ParseError(f"{key}: expected a number, "
                             f"got {v!r}")
        return str(v)
    if ty == "time":
        if (not isinstance(v, dict) or
                set(v) != {"day", "hour"}):
            raise ParseError(f"{key}: expected "
                             '{"day": D, "hour": H}, '
                             f"got {v!r}")
        day = value(key + ".day", "int", v["day"])
        hour = value(key + ".hour", "int", v["hour"])
        if int(hour) > 23:
            raise ParseError(f"{key}: hour {hour} is not "
                             "an hour of the day")
        return f"(d {day} {hour})"
    if ty.startswith("list "):
        if not isinstance(v, list) or not v:
            raise ParseError(f"{key}: expected a list")
        item = ty.removeprefix("list ")
        parts = [value(key, item, x) for x in v]
        return "[" + ", ".join(parts) + "]"
    return constant(key, ty, v)
# ANCHOR_END: value


# ANCHOR: constant
def constant(key: str, ty: str, v: Any) -> str:
    """A name the world declares with kind `ty`."""
    sig = world.signature()
    known = sig.constants.get(ty, frozenset())
    if v in known:
        return v
    if isinstance(v, str) and sig.kind_of(v):
        raise ParseError(f"{key}: {v} is {a(sig.kind_of(v))}"
                         f", not {a(ty)}")
    names = ", ".join(sorted(known))
    raise ParseError(f"{key}: unknown {ty} {v!r} "
                     f"(known: {names})")
# ANCHOR_END: constant


def a(word: str) -> str:
    return ("an " if word[0] in "aeiou" else "a ") + word


# ANCHOR: to_clause
def to_clause(fact: dict | str) -> str:
    """{"pred": "works_at", "person": "lena", ...}
    -> 'works_at lena lumen.'"""
    if isinstance(fact, str):
        fact = json.loads(fact)
    if not isinstance(fact, dict):
        raise ParseError("a fact is a JSON object")
    pred = fact.get("pred")
    if pred not in SCHEMA:
        preds = ", ".join(SCHEMA)
        raise ParseError(f"unknown pred {pred!r} "
                         f"(expected one of: {preds})")
    keys = SCHEMA[pred]
    extra = set(fact) - set(keys) - {"pred"}
    if extra:
        raise ParseError(f"{pred}: unknown key "
                         f"{sorted(extra)[0]!r} (expected:"
                         f" {', '.join(keys)})")
    missing = [k for k in keys if k not in fact]
    if missing:
        raise ParseError(f"{pred}: missing key "
                         f"{missing[0]!r}")
    args = [value(k, ty, fact[k])
            for k, ty in keys.items()]
    return f"{pred} {' '.join(args)}."
# ANCHOR_END: to_clause


def facts(reply: str) -> list[dict]:
    """The LLM's reply: {"facts": [...]}, nothing else."""
    try:
        data = json.loads(strip_fence(reply))
    except json.JSONDecodeError as e:
        raise ParseError(f"not JSON: {e}") from e
    if not isinstance(data, dict) or "facts" not in data:
        raise ParseError('expected {"facts": [...]}')
    if not isinstance(data["facts"], list):
        raise ParseError('"facts" must be a list')
    return data["facts"]


def strip_fence(reply: str) -> str:
    """Drop a ``` fence, if the model wrote one."""
    text = reply.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text \
            else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()
