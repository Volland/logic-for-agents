"""The LLM protocol: replay, recording, and the
Anthropic adapter (with a fake client: no network)."""
import json
from types import SimpleNamespace

import pytest

from agent.llm import (AnthropicLLM, LLMError,
                       RecordingLLM, ReplayError,
                       ReplayLLM)
from conftest import REPLAY, ScriptLLM, write_replay


def ask(text):
    return [{"role": "user", "content": text}]


def test_replay_plays_steps_in_order(tmp_path):
    path = write_replay(tmp_path / "r.json", [
        {"user": "a", "response": "1"},
        {"user": "b", "response": "2"}])
    llm = ReplayLLM(path)
    assert llm.complete("sys", ask("a")) == "1"
    assert not llm.finished()
    assert llm.complete("sys", ask("b")) == "2"
    assert llm.finished()


def test_replay_fails_loudly_on_a_different_question(
        tmp_path):
    path = write_replay(tmp_path / "r.json", [
        {"step": "one", "user": "a", "response": "1"}])
    with pytest.raises(ReplayError, match="step 1"):
        ReplayLLM(path).complete("sys", ask("z"))


def test_replay_fails_loudly_when_exhausted(tmp_path):
    path = write_replay(tmp_path / "r.json", [])
    with pytest.raises(ReplayError, match="only 0"):
        ReplayLLM(path).complete("sys", ask("a"))


def test_recording_writes_a_replay_file(tmp_path):
    rec = RecordingLLM(ScriptLLM("x", "y"), "turn")
    rec.complete("sys", ask("a"))
    rec.complete("sys", ask("b"))
    path = tmp_path / "rec.json"
    rec.save(path, turns=["a", "b"])
    data = json.loads(path.read_text())
    assert data["turns"] == ["a", "b"]
    assert data["note"].startswith("Recorded")
    replay = ReplayLLM(path)
    assert replay.complete("s", ask("a")) == "x"
    assert replay.complete("s", ask("b")) == "y"


def test_every_replay_file_says_what_it_is():
    for path in REPLAY.glob("*.json"):
        data = json.loads(path.read_text())
        assert data["note"], path.name
        assert "Authored fixture" in data["note"]
        for step in data["steps"]:
            assert {"user", "response"} <= set(step)


class FakeMessages:
    def __init__(self, reply):
        self.reply = reply
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.reply


def fake_client(stop="end_turn", text="hi"):
    blocks = [SimpleNamespace(type="text", text=text)]
    reply = SimpleNamespace(stop_reason=stop,
                            content=blocks)
    msgs = FakeMessages(reply)
    return SimpleNamespace(
        beta=SimpleNamespace(messages=msgs)), msgs


def test_anthropic_adapter_sends_the_request():
    client, msgs = fake_client(text="ok")
    llm = AnthropicLLM(client=client)
    assert llm.complete("sys", ask("a")) == "ok"
    assert msgs.kwargs["model"] == "claude-sonnet-5-5"
    assert msgs.kwargs["system"] == "sys"
    assert msgs.kwargs["fallbacks"] == "default"


def test_anthropic_adapter_reports_a_refusal():
    client, _ = fake_client(stop="refusal")
    with pytest.raises(LLMError):
        AnthropicLLM(client=client).complete(
            "sys", ask("a"))
