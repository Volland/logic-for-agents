"""Shared fixtures. The engine is loaded once per run."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.memory import Memory

ROOT = Path(__file__).resolve().parent.parent
REPLAY = ROOT / "replay"


@pytest.fixture(scope="session")
def memory() -> Memory:
    """The world and the rules, nothing committed.
    Memories are persistent, so tests can share it."""
    return Memory()


class ScriptLLM:
    """An LLM that answers from a list, and keeps what
    it was asked."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.asked: list[list[dict]] = []

    def complete(self, system, messages):
        self.asked.append([dict(m) for m in messages])
        return self.replies.pop(0)


@pytest.fixture
def script():
    return ScriptLLM


def write_replay(path: Path, steps: list[dict]) -> Path:
    path.write_text(json.dumps({"note": "test",
                                "steps": steps}))
    return path
