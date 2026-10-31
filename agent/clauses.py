"""Read LLM-written clauses into a small syntax tree.

The engine has already parsed and type-checked the text
when we get here. This reader exists for the guards the
engine does not have: modes and the predicate whitelist.
It accepts a fragment of λProlog (facts, rules, queries
with `,` `;` `not` `=` `is` and comparisons) and says so
when the text goes beyond it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class FragmentError(ValueError):
    """Text the engine accepts but the agent does not."""


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Lit:
    value: object  # int or str


@dataclass(frozen=True)
class Seq:  # a list: [a, b | T]
    items: tuple
    tail: object = None


@dataclass(frozen=True)
class Call:  # a name applied to arguments
    name: str
    args: tuple = ()


@dataclass(frozen=True)
class Op:  # X = Y, X is E, X < Y, A + B, A , B, A ; B
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Clause:
    head: Call
    body: object = None  # None for a fact


_TOKEN = re.compile(r"""
  (?P<ws>\s+|%[^\n]*)
| (?P<str>"(?:[^"\\]|\\.)*")
| (?P<int>\d+)
| (?P<var>[A-Z_][\w']*)
| (?P<name>[a-z][\w']*(?:\.[a-z][\w']*)*)
| (?P<sym>:-|=<|>=|=>|\\=|!=|[()\[\],|;.=<>+*\-\\!])
""", re.X)

_BINARY = {"=": 1, "is": 1, "<": 1, ">": 1, "=<": 1,
           ">=": 1}
_ARITH = ("+", "-", "*")


def tokens(text: str) -> list[tuple[str, str]]:
    out, i = [], 0
    while i < len(text):
        m = _TOKEN.match(text, i)
        if m is None:
            raise FragmentError(f"unexpected {text[i]!r}")
        i = m.end()
        if m.lastgroup != "ws":
            out.append((m.lastgroup, m[0]))
    return out


class _Reader:
    def __init__(self, text: str) -> None:
        self.toks = tokens(text)
        self.i = 0

    def peek(self) -> str | None:
        if self.i < len(self.toks):
            return self.toks[self.i][1]
        return None

    def take(self, want: str | None = None) -> tuple:
        if self.i >= len(self.toks):
            raise FragmentError("unexpected end of text")
        tok = self.toks[self.i]
        if want is not None and tok[1] != want:
            raise FragmentError(
                f"expected {want!r}, found {tok[1]!r}")
        self.i += 1
        return tok

    # body := conj (";" conj)*
    def body(self):
        left = self.conj()
        while self.peek() == ";":
            self.take()
            left = Op(";", left, self.conj())
        return left

    def conj(self):
        left = self.goal()
        while self.peek() == ",":
            self.take()
            left = Op(",", left, self.goal())
        return left

    def goal(self):
        left = self.expr()
        if self.peek() in _BINARY:
            op = self.take()[1]
            return Op(op, left, self.expr())
        return left

    def expr(self):
        left = self.app()
        while self.peek() in _ARITH:
            op = self.take()[1]
            left = Op(op, left, self.app())
        return left

    def app(self):
        kind, text = self.toks[self.i] if (
            self.i < len(self.toks)) else ("", "")
        first = self.primary()
        if kind != "name" or text == "is":
            return first
        args = []
        while self.starts_primary():
            args.append(self.primary())
        return Call(text, tuple(args))

    def starts_primary(self) -> bool:
        if self.i >= len(self.toks):
            return False
        kind, text = self.toks[self.i]
        if kind == "name":
            return text != "is"
        return kind in ("var", "int", "str") or (
            text in ("(", "["))

    def primary(self):
        kind, text = self.take()
        if kind == "var":
            return Var(text)
        if kind == "int":
            return Lit(int(text))
        if kind == "str":
            return Lit(text[1:-1])
        if kind == "name":
            return Call(text)
        if text == "(":
            inner = self.body()
            self.take(")")
            return inner
        if text == "[":
            return self.seq()
        raise FragmentError(
            f"{text!r} is outside the fragment the agent "
            "accepts")

    def seq(self):
        items, tail = [], None
        if self.peek() == "]":
            self.take()
            return Seq(())
        items.append(self.expr())
        while self.peek() == ",":
            self.take()
            items.append(self.expr())
        if self.peek() == "|":
            self.take()
            tail = self.expr()
        self.take("]")
        return Seq(tuple(items), tail)

    def clause(self) -> Clause:
        head = self.app()
        if isinstance(head, Var):
            raise FragmentError(
                f"the head of a clause must be a predicate,"
                f" not the variable {head.name}")
        if not isinstance(head, Call):
            raise FragmentError("a clause must start with "
                                "a predicate")
        body = None
        if self.peek() == ":-":
            self.take()
            body = self.body()
        self.take(".")
        return Clause(head, body)


def read_clauses(text: str) -> list[Clause]:
    r = _Reader(text)
    out = []
    while r.peek() is not None:
        out.append(r.clause())
    if not out:
        raise FragmentError("no clauses")
    return out


def read_query(text: str):
    r = _Reader(text.strip().removesuffix("."))
    goal = r.body()
    if r.peek() is not None:
        raise FragmentError(f"unexpected {r.peek()!r}")
    return goal


# --- Walking the tree ------------------------------------

def variables(t) -> list[str]:
    """Named variables in order of first appearance."""
    out: list[str] = []

    def walk(t) -> None:
        if isinstance(t, Var):
            if t.name != "_" and t.name not in out:
                out.append(t.name)
        elif isinstance(t, Call):
            for a in t.args:
                walk(a)
        elif isinstance(t, Op):
            walk(t.left)
            walk(t.right)
        elif isinstance(t, Seq):
            for a in t.items:
                walk(a)
            walk(t.tail)
        elif isinstance(t, Clause):
            walk(t.head)
            walk(t.body)

    walk(t)
    return out


def calls(t) -> list[Call]:
    """Every predicate call in a body, in order."""
    if isinstance(t, Op) and t.op in (",", ";"):
        return calls(t.left) + calls(t.right)
    if isinstance(t, Call) and t.name == "not" and t.args:
        return [t] + calls(t.args[0])
    if isinstance(t, Call):
        return [t]
    return []


def text(t, nested: bool = False) -> str:
    """Print a tree back as λProlog."""
    if isinstance(t, Var):
        return t.name
    if isinstance(t, Lit):
        if isinstance(t.value, str):
            return f'"{t.value}"'
        return str(t.value)
    if isinstance(t, Seq):
        s = ", ".join(text(x) for x in t.items)
        if t.tail is not None:
            s += " | " + text(t.tail)
        return f"[{s}]"
    if isinstance(t, Call):
        if not t.args:
            return t.name
        s = " ".join([t.name] +
                     [text(a, True) for a in t.args])
        return f"({s})" if nested else s
    if isinstance(t, Op):
        sep = ", " if t.op == "," else f" {t.op} "
        s = _side(t.left, t.op) + sep + _side(t.right, t.op)
        return f"({s})" if nested else s
    if isinstance(t, Clause):
        if t.body is None:
            return text(t.head)
        return f"{text(t.head)} :- {text(t.body)}"
    raise TypeError(f"not a tree: {t!r}")


_LOOSE = {",": 1, ";": 2}


def _side(t, op: str) -> str:
    """An operand: in parentheses only when needed."""
    if not isinstance(t, Op):
        return text(t)  # application binds tightest
    if op in _LOOSE and (t.op not in _LOOSE or
                         _LOOSE[t.op] <= _LOOSE[op]):
        return text(t)
    return f"({text(t)})"


def rename_anonymous(c: Clause) -> Clause:
    """Give every `_` its own name, so the clause can be
    quantified with `pi`."""
    count = [0]

    def walk(t):
        if isinstance(t, Var) and t.name == "_":
            count[0] += 1
            return Var(f"Anon{count[0]}")
        if isinstance(t, Call):
            return Call(t.name, tuple(walk(a) for a in t.args))
        if isinstance(t, Op):
            return Op(t.op, walk(t.left), walk(t.right))
        if isinstance(t, Seq):
            return Seq(tuple(walk(a) for a in t.items),
                       walk(t.tail))
        return t

    return Clause(walk(c.head), walk(c.body))


# ANCHOR: quantify
def quantify(c: Clause) -> str:
    """A clause to assume with `=>`: its variables bound
    by `pi`, so each use of it gets fresh ones."""
    c = rename_anonymous(c)
    out = f"({text(c)})"
    for v in reversed(variables(c)):
        out = f"(pi {v}\\ {out})"
    return out
# ANCHOR_END: quantify
