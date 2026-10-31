"""Chapter 13: the whole agent on the recorded
session, turn by turn."""
import json

from agent.llm import ReplayLLM
from agent.loop import Agent
from conftest import REPLAY

SESSION = REPLAY / "ch13-session.json"


def run():
    turns = json.loads(SESSION.read_text())["turns"]
    llm = ReplayLLM(SESSION)
    agent = Agent(llm)
    replies = [agent.turn(t) for t in turns]
    return agent, llm, replies


def test_the_recorded_session():
    agent, llm, r = run()
    assert llm.finished()
    # remembers
    assert r[0] == "Remembered:\n  works_at sofia acme."
    # answers
    assert r[1] == "M = anna"
    # refuses the phantom and names the broken rule
    assert "won't remember:\n  event 3" in r[2]
    assert "bilocation" in r[2]
    # explains, using what it just learned
    assert "works_at sofia acme  [memory]" in r[3]
    # a what-if, and memory unchanged
    assert "M = anna" in r[4].split("Memory")[0]
    assert "M = anna" not in r[4].split("Memory")[1]
    # same_person from inside a rule, checked by rules
    assert r[5].startswith("Yes.")
    assert 'same_person "Anya" anna  [llm]' in r[5]
    # the sofia trap
    assert "born_before" in r[6]
    # parsing is checking
    assert "unknown person 'olena'" in r[7]
    assert agent.memory.history == (
        "works_at sofia acme.",)


def test_a_bad_query_is_refused(memory, script):
    agent = Agent(script('{"do": "ask", "query": '
                         '"minutes T 600"}'), memory)
    reply = agent.turn("When is minute 600?")
    assert "mode check" in reply


def test_a_reply_that_is_not_json(memory, script):
    agent = Agent(script("Sure!"), memory)
    assert "did not understand" in agent.turn("hi")
