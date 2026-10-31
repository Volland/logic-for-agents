"""LLM JSON -> typed clauses. Parsing is checking."""
import pytest

from agent.parse import ParseError, facts, to_clause

EVENT = {"pred": "event", "id": 3, "kind": "meeting",
         "who": ["anna", "lena"], "city": "berlin",
         "from": {"day": 2000, "hour": 10},
         "to": {"day": 2000, "hour": 12}}


def test_an_event_becomes_a_clause():
    assert to_clause(EVENT) == (
        "event 3 meeting [anna, lena] berlin "
        "(d 2000 10) (d 2000 12).")


def test_json_text_is_accepted():
    assert to_clause('{"pred": "works_at", "person": '
                     '"lena", "org": "lumen"}') == \
        "works_at lena lumen."


@pytest.mark.parametrize("fact, message", [
    ({"pred": "likes", "person": "anna"},
     "unknown pred 'likes'"),
    ({"pred": "works_at", "person": "anna",
      "org": "acme", "office": "porto"},
     "unknown key 'office'"),
    ({"pred": "works_at", "person": "anna"},
     "missing key 'org'"),
    ({"pred": "works_at", "person": "olena",
      "org": "acme"}, "unknown person 'olena'"),
    ({"pred": "works_at", "person": "acme",
      "org": "anna"}, "acme is an org, not a person"),
    ({**EVENT, "from": "2000-10"}, '{"day": D'),
    ({**EVENT, "to": {"day": 2000, "hour": 25}},
     "hour 25"),
    ({**EVENT, "id": "3"}, "expected a number"),
    ({**EVENT, "who": []}, "expected a list"),
    ({**EVENT, "who": ["anna", "kyiv"]},
     "kyiv is a city, not a person"),
])
def test_bad_facts_are_rejected_clearly(fact, message):
    with pytest.raises(ParseError, match=message[:12]):
        to_clause(fact)
    try:
        to_clause(fact)
    except ParseError as e:
        assert message in str(e)


def test_facts_reads_the_reply_and_drops_a_fence():
    reply = '```json\n{"facts": [{"pred": "x"}]}\n```'
    assert facts(reply) == [{"pred": "x"}]
    with pytest.raises(ParseError, match="not JSON"):
        facts("Sure! Here are the facts.")
    with pytest.raises(ParseError, match="facts"):
        facts('{"fact": []}')
