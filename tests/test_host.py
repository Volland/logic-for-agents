"""Host predicates: Python answers calls from rules."""
import pytest
from leanelpi import Const, ElpiError

from agent.host import SamePerson, calendar, clock


def test_clock(memory):
    assert memory.with_host(now=clock(1999, 0)) \
        .ask("upcoming E") == [{"E": "1"}, {"E": "2"}]
    assert memory.with_host(now=clock(2000, 10)) \
        .ask("upcoming E") == []


def test_calendar_and_memory_both_count(memory):
    m = memory.with_host(calendar=calendar(
        {"anna": [((2001, 14), (2001, 15))]}))
    assert not m.holds("free anna (d 2001 14) (d 2001 15)")
    assert m.holds("free anna (d 2001 15) (d 2001 16)")
    assert not m.holds("free anna (d 2000 10) (d 2000 11)")
    assert m.holds("free taras (d 2000 10) (d 2000 11)")


def test_a_rule_needs_its_host(memory):
    with pytest.raises(ElpiError, match="no host"):
        memory.ask("upcoming E")


def test_the_binding_rejects_a_wrong_kind(memory):
    m = memory.with_host(now=lambda: [Const("lisbon")])
    with pytest.raises(ElpiError, match="type time"):
        m.ask("upcoming E")


def test_same_person_asks_once_per_name(memory, script):
    llm = script('{"person": "anna"}',
                 '{"person": "marco"}')
    names = SamePerson(llm)
    m = memory.with_host(same_person=names)
    assert m.holds('met_by_name "Anya" "Marko"')
    assert m.holds('met_by_name "Anya" "Marko"')
    assert len(llm.asked) == 2
    assert llm.asked[0][-1]["content"] == "Anya"


def test_rules_still_decide(memory, script):
    llm = script('{"person": "lena"}',
                 '{"person": "marco"}')
    m = memory.with_host(same_person=SamePerson(llm))
    # a fine match, but Lena never met Marco
    assert not m.holds('met_by_name "Lenka" "Marko"')


@pytest.mark.parametrize("reply, message", [
    ('{"person": "lisbon"}', "type person"),
    ('{"person": "olena"}', "unknown constant 'olena'"),
])
def test_wrong_guesses_are_errors(memory, script,
                                  reply, message):
    m = memory.with_host(
        same_person=SamePerson(script(reply)))
    with pytest.raises(ElpiError, match=message):
        m.holds('met_by_name "X" "Marko"')


def test_null_means_nobody(memory, script):
    m = memory.with_host(same_person=SamePerson(
        script('{"person": null}')))
    assert not m.holds('met_by_name "Bob" "Marko"')
