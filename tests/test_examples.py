"""Every example script and Python solution prints its
golden output.

  UPDATE_GOLDEN=1 pytest tests/test_examples.py

rewrites the .out files; read the diff before
committing.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "agent" / "examples")
                  .glob("*.py")) + \
    sorted((ROOT / "solutions").glob("ch*.py"))


def run(script: Path) -> str:
    p = subprocess.run([sys.executable, str(script)],
                       cwd=ROOT, capture_output=True,
                       text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.mark.parametrize("script", EXAMPLES,
                         ids=lambda p: p.stem)
def test_example_output(script: Path) -> None:
    out = run(script)
    golden = script.with_suffix(".out")
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(out, encoding="utf-8")
        return
    assert golden.exists(), f"no {golden.name}"
    assert out == golden.read_text(encoding="utf-8")


def test_python_m_agent_replays_the_session() -> None:
    p = subprocess.run([sys.executable, "-m", "agent"],
                       cwd=ROOT, capture_output=True,
                       text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    golden = ROOT / "agent" / "examples" / \
        "ch13_session.out"
    assert p.stdout == golden.read_text(encoding="utf-8")
