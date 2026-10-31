"""Load the world and the agent's rules into one program.

`Program(src)` compiles one string and cannot follow
`accumulate`, so we follow it here: each `accumulate name.`
line is replaced by the file it names, once, the first
time it appears.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from leanelpi import Program

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
RULES = Path(__file__).resolve().parent / "rules"
PATH = (RULES, LIB)

# The agent's program: every rule file, in one piece.
FILES = ("consistency", "open")
# The predicates Python answers (agent/host.py).
HOSTS = ("now", "calendar", "same_person")

_ACC = re.compile(r"^accumulate\s+([\w/]+)\s*\.\s*$", re.M)


def find(name: str) -> Path:
    for folder in PATH:
        path = folder / f"{name}.elpi"
        if path.exists():
            return path
    raise FileNotFoundError(f"no {name}.elpi in {PATH}")


# ANCHOR: accumulate
def source(names=FILES) -> str:
    """The text of `names`, with accumulates inlined."""
    seen: set[str] = set()

    def expand(name: str) -> str:
        if name in seen:
            return ""
        seen.add(name)
        text = find(name).read_text(encoding="utf-8")
        return _ACC.sub(lambda m: expand(m[1]), text)

    return "\n".join(expand(n) for n in names)
# ANCHOR_END: accumulate


# ANCHOR: load
def load(names=FILES) -> Program:
    """Compile the program and hand the host predicates
    to Python (about one second: the world is compiled
    once, then every commit is cheap)."""
    src = source(names)
    program = Program(src)
    for name in HOSTS:
        program = program.declare(pred_decl(src, name))
    return program
# ANCHOR_END: load


# --- Reading the signature -------------------------------

_COMMENT = re.compile(r"%[^\n]*")
_END = re.compile(r"\.(?=\s|$)")  # not the dot of std.mem


def statements(src: str) -> list[str]:
    """The `kind`, `type` and `pred` statements of src,
    each on one line, without the final period."""
    text = _COMMENT.sub("", src)
    out = []
    for part in _END.split(text):
        s = " ".join(part.split())
        if s.split(" ", 1)[0] in ("kind", "type", "pred"):
            out.append(s)
    return out


def pred_decl(src: str, name: str) -> str:
    for s in statements(src):
        if s.split()[:2] == ["pred", name]:
            return s + "."
    raise KeyError(f"no 'pred {name}' in the program")


@dataclass(frozen=True)
class Signature:
    """What the program declares: the modes of each
    predicate ('i' or 'o' per argument) and the
    constants of each kind."""
    modes: dict[str, tuple[str, ...]]
    types: dict[str, tuple[str, ...]]
    constants: dict[str, frozenset[str]]

    def kind_of(self, const: str) -> str | None:
        for kind, names in self.constants.items():
            if const in names:
                return kind
        return None


def _split_args(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        depth += ch in "(["
        depth -= ch in ")]"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def read_signature(src: str) -> Signature:
    modes, types = {}, {}
    consts: dict[str, set[str]] = {}
    for s in statements(src):
        word, rest = s.split(None, 1)
        if word == "pred":
            name, _, args = rest.partition(" ")
            pairs = [_mode(a) for a in _split_args(args)]
            modes[name] = tuple(m for m, _ in pairs)
            types[name] = tuple(t for _, t in pairs)
        elif word == "type":
            m = re.match(r"([\w, ]+?)\s+(\w+)$", rest)
            if m:  # constants: `type anna, marco person`
                names = [n.strip() for n in m[1].split(",")]
                consts.setdefault(m[2], set()).update(names)
    kinds = {k: frozenset(v) for k, v in consts.items()}
    return Signature(modes, types, kinds)


def _mode(arg: str) -> tuple[str, str]:
    """`i:time` -> ("i", "time"). An argument without
    a mode is an output, as in the engine."""
    if arg[1:2] == ":" and arg[0] in "io":
        return arg[0], arg[2:]
    return "o", arg


@lru_cache(maxsize=None)
def signature(names=FILES) -> Signature:
    return read_signature(source(names))


# What the LLM is shown: the world and the derived and
# open predicates, but not the agent's own machinery.
PUBLIC = ("world", "time", "derived", "open")
PRIVATE = ("rname", "proof", "prop", "question")


# ANCHOR: contract
def contract() -> str:
    """The signature as the LLM sees it: the contract."""
    lines, seen = [], set()
    for name in PUBLIC:
        text = find(name).read_text(encoding="utf-8")
        for s in statements(_ACC.sub("", text)):
            if any(w in s for w in PRIVATE) or s in seen:
                continue
            seen.add(s)
            lines.append(s + ".")
    return "\n".join(lines)
# ANCHOR_END: contract
