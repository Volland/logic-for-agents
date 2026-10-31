"""The LLM, behind a small protocol.

`AnthropicLLM` calls Claude. `ReplayLLM` plays back
responses recorded in replay/*.json, so the agent and its
tests run without a key or a network. `RecordingLLM` wraps
a live model and writes such a file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

Message = dict[str, str]  # {"role": ..., "content": ...}

MODEL = "claude-sonnet-5-5"


# ANCHOR: protocol
class LLM(Protocol):
    def complete(self, system: str,
                 messages: list[Message]) -> str:
        """The model's text reply to `messages`."""
        ...
# ANCHOR_END: protocol


class LLMError(RuntimeError):
    pass


# ANCHOR: anthropic
class AnthropicLLM:
    """Claude through the `anthropic` SDK. The key comes
    from ANTHROPIC_API_KEY (or an `ant auth login`
    profile)."""

    def __init__(self, model: str = MODEL,
                 max_tokens: int = 16_000,
                 client=None) -> None:
        if client is None:
            import anthropic  # only needed when live
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str,
                 messages: list[Message]) -> str:
        r = self.client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": "medium"},
            # retry a declined request on another model
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if r.stop_reason == "refusal":
            raise LLMError("the model declined to answer")
        return "".join(b.text for b in r.content
                       if b.type == "text")
# ANCHOR_END: anthropic


class ReplayError(AssertionError):
    """The agent asked something the recording did not."""


# @tg: implements:: [[decisions#Strict replay of recorded LLM calls]]
# ANCHOR: replay
class ReplayLLM:
    """Plays back a recording, step by step. Each step
    holds the last user message the agent sent and the
    reply; a different message fails loudly."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        data = json.loads(self.path.read_text("utf-8"))
        self.steps: list[dict] = data["steps"]
        self.next = 0

    def complete(self, system: str,
                 messages: list[Message]) -> str:
        if self.next >= len(self.steps):
            raise ReplayError(
                f"{self.path.name}: the agent made call "
                f"{self.next + 1}, but only "
                f"{len(self.steps)} were recorded")
        step = self.steps[self.next]
        asked = messages[-1]["content"]
        if asked != step["user"]:
            raise ReplayError(
                f"{self.path.name}, step {self.next + 1} "
                f"({step.get('step', '')}):\n"
                f"the agent asked:\n{asked}\n"
                f"the recording has:\n{step['user']}")
        self.next += 1
        return step["response"]

    def finished(self) -> bool:
        return self.next == len(self.steps)
# ANCHOR_END: replay


# ANCHOR: recording
class RecordingLLM:
    """Wraps a live LLM and keeps every exchange, to be
    saved as a replay file."""

    def __init__(self, inner: LLM, label: str = "") -> None:
        self.inner = inner
        self.label = label
        self.steps: list[dict] = []

    def complete(self, system: str,
                 messages: list[Message]) -> str:
        reply = self.inner.complete(system, messages)
        self.steps.append({
            "step": f"{self.label} {len(self.steps) + 1}"
                    .strip(),
            "user": messages[-1]["content"],
            "response": reply})
        return reply

    def save(self, path: str | Path, **extra) -> None:
        data = {"note": "Recorded from a live session "
                        f"with {MODEL}.",
                **extra, "steps": self.steps}
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
            + "\n", encoding="utf-8")
# ANCHOR_END: recording
