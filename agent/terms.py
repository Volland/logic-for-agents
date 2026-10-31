"""Print the terms the binding returns as λProlog text."""
from __future__ import annotations

import json
import textwrap

from leanelpi import App, Const, Opaque, Var


# ANCHOR: show
def show(t, nested: bool = False) -> str:
    """`App("d", (2000, 10))` -> `d 2000 10`, with
    parentheses when it is an argument: `(d 2000 10)`."""
    if isinstance(t, bool):
        return "tt" if t else "ff"
    if isinstance(t, (int, float)):
        return str(t)
    if isinstance(t, str):
        return json.dumps(t, ensure_ascii=False)
    if isinstance(t, list):
        return "[" + ", ".join(show(x) for x in t) + "]"
    if isinstance(t, Const):
        return t.name
    if isinstance(t, Var):
        return t.name
    if isinstance(t, Opaque):
        return t.printed
    if isinstance(t, App):
        text = " ".join([t.name] +
                        [show(a, True) for a in t.args])
        return f"({text})" if nested else text
    raise TypeError(f"not a term: {t!r}")
# ANCHOR_END: show


# ANCHOR: tree
def tree(proof, indent: str = "") -> list[str]:
    """A proof term from `prove`, one line per step:
    the goal, then in brackets the rule or the source."""
    if isinstance(proof, Const):  # empty
        return []
    name, args = proof.name, proof.args
    if name == "and":
        return tree(args[0], indent) + tree(args[1], indent)
    if name == "leaf":
        source, goal = args
        return [f"{indent}{show(goal)}  [{source}]"]
    if name == "by":
        rule, goal, sub = args
        return ([f"{indent}{show(goal)}  [{show(rule)}]"]
                + tree(sub, indent + "  "))
    raise ValueError(f"not a proof: {show(proof)}")
# ANCHOR_END: tree


# ANCHOR: wrap
def wrap(text: str, first: str = "", rest: str = "",
         width: int = 64) -> str:
    """Fit printed text to the book's page: each line
    wrapped on its own, continuation lines indented.
    An indented line (a proof step) is kept whole."""
    out = []
    for n, line in enumerate(text.splitlines() or [""]):
        if line.startswith(" "):
            out.append((first if n == 0 else rest) + line)
            continue
        out.append(textwrap.fill(
            line, width, break_long_words=False,
            break_on_hyphens=False,
            initial_indent=first if n == 0 else rest,
            subsequent_indent=rest + "  "))
    return "\n".join(out)
# ANCHOR_END: wrap
