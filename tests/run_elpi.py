#!/usr/bin/env python3
"""Check every λProlog example in the book against its golden output.

For each `FILE.elpi` that has a `FILE.out` beside it, run

    lean-elpi FILE.elpi -I lib -test

from the file's own folder and compare stdout+stderr with `FILE.out`.
A file whose first line is `% expect: fail` must exit non-zero (a type
error the book shows on purpose); every other file must exit 0. A line
`% fuel: N` runs the file with `--fuel N`, so a looping example stops
with "out of fuel" instead of hanging (combine with `% expect: fail`).

For each `FILE.repl`, pipe it into `lean-elpi BASE.elpi -I lib` (the REPL)
and compare with `FILE.repl.out`. BASE is the part of FILE before the
first dot, so `family.more.repl` drives `family.elpi`.

  python3 tests/run_elpi.py [--update] [--lfa] [PATH...]

`--update` rewrites the golden files from the current output; review the
diff before committing. The binary is $LEAN_ELPI or `lean-elpi` on PATH;
without either, or with `--lfa`, the files run on `lfa.py`, which needs
only the `leanelpi` wheel (pip install "leanelpi>=0.4.1").
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
FOLDERS = sorted(p for p in ROOT.iterdir()
                 if p.is_dir() and (p.name.startswith("ch")
                                    or p.name == "solutions"))


USE_LFA = False


def binary() -> list[str]:
    exe = os.environ.get("LEAN_ELPI") or shutil.which("lean-elpi")
    if exe and not USE_LFA:
        return [exe]
    return [sys.executable, str(ROOT / "lfa.py")]


def run(args: list[str], cwd: Path, stdin: str | None = None) \
        -> tuple[int, str]:
    p = subprocess.run([*binary(), *args, "-I", str(LIB)], cwd=cwd,
                       input=stdin, capture_output=True, text=True,
                       timeout=120)
    return p.returncode, p.stdout + p.stderr


def check(cases: list[tuple[str, Path, int, str]], update: bool) -> int:
    bad = 0
    for name, golden, rc_ok, out in cases:
        if rc_ok == 0:
            print(f"FAIL {name}: wrong exit status")
            print(out)
            bad += 1
            continue
        if update:
            golden.write_text(out, encoding="utf-8")
            continue
        want = golden.read_text(encoding="utf-8")
        if out != want:
            print(f"FAIL {name}: output differs from {golden.name}")
            print("--- expected\n" + want + "--- got\n" + out)
            bad += 1
    return bad


# @tg: implements:: [[decisions#Checked companion repository]]
def collect(paths: list[Path]) -> list[tuple[str, Path, int, str]]:
    cases = []
    for folder in paths:
        if USE_LFA and folder.name == "ch10":
            print("skip ch10: LF needs the lean-elpi program")
            continue
        files = [folder] if folder.is_file() else sorted(folder.iterdir())
        for f in files:
            if f.suffix == ".elpi" and f.with_suffix(".out").exists():
                src = f.read_text(encoding="utf-8")
                expect_fail = src.startswith("% expect: fail")
                fuel = re.search(r"^% fuel: (\d+)\s*$", src, re.M)
                extra = ["--fuel", fuel.group(1)] if fuel else []
                rc, out = run([f.name, "-test", *extra], f.parent)
                ok = (rc != 0) if expect_fail else (rc == 0)
                cases.append((str(f.relative_to(ROOT)), f.with_suffix(".out"),
                              int(ok), out))
            elif f.suffix == ".repl":
                base = f.parent / (f.name.split(".")[0] + ".elpi")
                rc, out = run([base.name], f.parent,
                              f.read_text(encoding="utf-8"))
                cases.append((str(f.relative_to(ROOT)),
                              f.with_name(f.name + ".out"), int(rc == 0), out))
    return cases


def main(argv: list[str]) -> int:
    global USE_LFA
    USE_LFA = "--lfa" in argv or not (os.environ.get("LEAN_ELPI")
                                      or shutil.which("lean-elpi"))
    print("engine: " + " ".join(binary()))
    update = "--update" in argv
    paths = [Path(a).resolve() for a in argv if not a.startswith("--")] \
        or FOLDERS
    cases = collect(paths)
    bad = check(cases, update)
    print(f"{len(cases) - bad}/{len(cases)} examples pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
