#!/usr/bin/env python3
"""Run the book's λProlog files with only `pip install leanelpi`.

`lfa` takes the same arguments as the `lean-elpi` program for
everything Chapters 1 to 9 do, and prints the same output:

    lfa phantom.elpi -I ../lib -test     # run main
    lfa phantom.elpi -I ../lib           # the REPL
    lfa q_fuel.elpi -I ../lib -test --fuel 2000

It drives the engine inside the `leanelpi` wheel, so it needs
neither Lean nor a build. What it does not do: `-exec`,
`--lean-env` and the LF options of Chapter 10, which need the
`lean-elpi` program itself.

From Python, `load` gives a chapter's file as a `Program`:

    from lfa import load
    p = load("ch01/phantom.elpi")
    [s["P"] for s in p.solve("works_at P acme")]  # anna, marco

`Program(src)` compiles one string and cannot follow
`accumulate`, so we inline each accumulated file once, as
agent/world.py does, and map error positions back to the file
and line they came from.
"""
from __future__ import annotations

import ctypes
import re
import sys
from pathlib import Path

from leanelpi import ElpiError, Program

_ACC = re.compile(r"^accumulate\s+([\w/]+)\s*\.\s*$")
_POS = re.compile(r"<string>:(\d+):(\d+):")
_LIBC = ctypes.CDLL(None)


def flush() -> None:
    """Flush Python's stdout and the engine's, in that order, so
    the REPL's text and the program's prints come out in turn."""
    sys.stdout.flush()
    _LIBC.fflush(None)


class Source:
    """One program text with accumulates inlined, and a map from
    each of its lines back to (file name, line)."""

    def __init__(self, path: Path, includes: list[Path]) -> None:
        self.includes = includes
        self.lines: list[str] = []
        self.origin: list[tuple[str, int]] = []
        self.seen: set[Path] = set()
        self.add(path)

    def find(self, name: str, here: Path) -> Path:
        for folder in (here, *self.includes):
            path = folder / f"{name}.elpi"
            if path.exists():
                return path.resolve()
        raise ElpiError(f"cannot find accumulated file '{name}'")

    def add(self, path: Path) -> None:
        path = path.resolve()
        if path in self.seen:
            return
        self.seen.add(path)
        text = path.read_text(encoding="utf-8")
        if text.startswith("#lf"):
            raise ElpiError(f"{path.name} is an LF signature (#lf);"
                            " Chapter 10 needs the lean-elpi program")
        for n, line in enumerate(text.split("\n"), 1):
            m = _ACC.match(line)
            if m:
                self.add(self.find(m[1], path.parent))
            else:
                self.lines.append(line)
                self.origin.append((path.name, n))

    def text(self) -> str:
        return "\n".join(self.lines)

    def locate(self, message: str) -> str:
        """Replace `<string>:L:C:` by the file and line it was."""
        def back(m: re.Match) -> str:
            name, line = self.origin[int(m[1]) - 1]
            return f"{name}:{line}:{m[2]}:"
        return _POS.sub(back, message)


LIB = Path(__file__).resolve().parent / "lib"


def load(path: str | Path, includes=(LIB,)) -> Program:
    """The file at `path`, with its accumulates, as a Program.
    The repository's lib/ is on the include path."""
    return Program(Source(Path(path), list(includes)).text())


def error(src: Source | None, e: ElpiError) -> str:
    """An engine error, worded as the lean-elpi program words it."""
    if e.out_of_fuel:
        return "resource error: out of fuel"
    msg = src.locate(str(e)) if src else str(e)
    if "undeclared constant" in msg:
        msg += ("\nhint: if this is a builtin registered by a"
                " Lean module, run with --lean-env MODULE")
    return msg


def report(constraints: list[str]) -> None:
    """Residual goals after `-test`, on stderr, as lean-elpi does."""
    if constraints:
        print("Constraints:", file=sys.stderr)
        for c in constraints:
            print(c, file=sys.stderr)
        print("State:", file=sys.stderr)


def run_main(p: Program, fuel: int | None) -> int:
    try:
        sols = p.solve("main", limit=1, fuel=fuel)
    except ElpiError as e:
        flush()
        print(error(None, e), file=sys.stderr)
        return 1
    flush()
    if not sols:
        print("Failure", file=sys.stderr)
        return 1
    report(sols[0].constraints)
    return 0


def read_query() -> str | None:
    acc = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            return acc if acc.strip() else None
        acc += line
        if acc.strip().endswith("."):
            return acc


_VAR = re.compile(r'"(?:[^"\\]|\\.)*"|%[^\n]*|\b([A-Z]\w*)')


def order(query: str) -> dict[str, int]:
    """Each variable's first position in the query: lean-elpi
    prints the bindings in that order, the binding sorts them."""
    seen: dict[str, int] = {}
    for m in _VAR.finditer(query):
        if m[1] and m[1] not in seen:
            seen[m[1]] = len(seen)
    return seen


def show(sol, query: str) -> None:
    print("Success:")
    first = order(query)
    for v in sorted(sol.bindings, key=lambda v: first.get(v, len(first))):
        print(f"  {v} = {sol.bindings[v]}")
    for c in sol.constraints:
        print(c)


def repl(p: Program, fuel: int | None) -> int:
    """The lean-elpi REPL. Each further answer reruns the query
    with a larger limit, so a query that prints, prints again."""
    while True:
        print("?- ", end="")
        flush()
        q = read_query()
        if q is None:
            return 0
        q = q.strip()[:-1]
        n = 0
        try:
            while True:
                sols, done = p.solve_all(q, limit=n + 1, fuel=fuel)
                flush()
                if len(sols) <= n:
                    print("Failure" if n == 0 else "No more solutions")
                    break
                show(sols[n], q)
                n += 1
                print("More? (y/N) ", end="")
                flush()
                if sys.stdin.readline().strip() not in ("y", ";"):
                    break
        except ElpiError as e:
            flush()
            print(f"error: {error(None, e)}", file=sys.stderr)


def usage(msg: str) -> int:
    print(f"lfa: {msg}", file=sys.stderr)
    return 2


# @tg: implements:: [[decisions#Wheel first, with lfa]]
def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    files: list[str] = []
    includes: list[Path] = []
    test = False
    fuel: int | None = None
    while args:
        a = args.pop(0)
        if a == "-test":
            test = True
        elif a == "-I":
            if not args:
                return usage("-I expects a directory")
            includes.append(Path(args.pop(0)))
        elif a == "--fuel":
            if not args or not args[0].isdigit():
                return usage("--fuel expects a number")
            fuel = int(args.pop(0))
        elif a.startswith("-"):
            return usage(f"unknown option '{a}' (lfa runs -test, -I"
                         " and --fuel; use lean-elpi for the rest)")
        else:
            files.append(a)
    if len(files) != 1:
        return usage("give one .elpi file")
    src = None
    try:
        src = Source(Path(files[0]), includes)
        p = Program(src.text())
    except ElpiError as e:
        print(error(src, e), file=sys.stderr)
        return 1
    return run_main(p, fuel) if test else repl(p, fuel)


if __name__ == "__main__":
    sys.exit(main())
