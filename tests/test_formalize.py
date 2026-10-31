"""Chapter 12's guards, one at a time, and the retry
loop."""
import pytest

from agent.clauses import FragmentError, quantify, \
    read_clauses, read_query, text
from agent.formalize import (STAGES, Formalizer,
                             GuardError, guard,
                             guard_query)

PHANTOM = ("event 3 meeting [anna, lena] berlin "
           "(d 2000 10) (d 2000 12).")


def stage(memory, clauses: str) -> str:
    with pytest.raises(GuardError) as e:
        guard(memory, clauses)
    return e.value.stage


# ANCHOR: one_per_guard
@pytest.mark.parametrize("clauses, expected", [
    ("knows X Y :- met X Y, X \\= Y.", "parse"),
    ("pred likes o:person, o:person.", "parse"),
    ("Knows anna marco.", "parse"),
    ("works_at acme sofia.", "type"),
    ("works_at olena lumen.", "type"),
    ("works_at(sofia, lumen).", "type"),
    ("knows X Y :- works_at X acme.", "mode"),
    ("works_at X acme.", "mode"),
    ("knows X Y :- before S T, met X Y.", "mode"),
    ("reports_to X lena :- works_at X lumen.",
     "allowed"),
    ("in_country porto germany.", "allowed"),
    ("knows X Y :- print X, met X Y.", "allowed"),
    ("knows X Y :- met X Y, prove (met X Y) P.",
     "allowed"),
    ("knows X Y :- met X Y.\nknows X Y :- knows Y X.",
     "sandbox"),
    (PHANTOM, "consistency"),
    ("reports_to marco lena.", "consistency"),
])
def test_each_guard_catches_its_mistake(
        memory, clauses, expected):
    assert stage(memory, clauses) == expected
# ANCHOR_END: one_per_guard


def test_stages_run_in_order():
    assert STAGES == ("parse", "type", "mode", "allowed",
                      "sandbox", "consistency")


def test_engine_messages_are_passed_on(memory):
    with pytest.raises(GuardError) as e:
        guard(memory, "works_at acme sofia.")
    assert e.value.message.startswith(
        "<assert>:1:9: acme has type org")


def test_good_clauses_pass_and_commit(memory):
    rules = "knows X Y :- met X Y.\n" \
            "knows X Y :- colleague X Y."
    new = guard(memory, rules)
    # marco twice: they met, and they are colleagues
    assert new.ask("knows anna Y") == [{"Y": "marco"}] * 2
    assert new.history == (rules,)
    assert memory.ask("knows anna Y") == []


def test_consistency_uses_quantified_rules(memory):
    # A rule assumed with => must not share its
    # variables between uses.
    c = read_clauses("knows X _ :- met X Y.")[0]
    assert quantify(c) == \
        "(pi X\\ (pi Anon1\\ (pi Y\\ " \
        "(knows X Anon1 :- met X Y))))"


def test_query_guards(memory):
    assert guard_query(memory, "chain marco M") == \
        [{"M": "anna"}]
    for q, expected in [
            ("works_at acme X", "type"),
            ("works_at anna (X", "parse"),
            ("minutes T M, event 1 _ _ _ T _", "mode"),
            ("rule N H B", "allowed")]:
        with pytest.raises(GuardError) as e:
            guard_query(memory, q)
        assert e.value.stage == expected, q


def test_query_errors_point_into_the_query(memory):
    with pytest.raises(GuardError) as e:
        guard_query(memory, "works_at acme X")
    assert e.value.message.startswith("<query>:1:9:")


def test_fragment_reader():
    q = read_query("event 1 _ _ _ T _, minutes T M")
    assert text(q) == "event 1 _ _ _ T _, minutes T M"
    with pytest.raises(FragmentError):
        read_clauses("knows X Y :- !, met X Y.")


# ANCHOR: retry
def test_feedback_reaches_the_llm_and_retry_commits(
        memory, script):
    llm = script("works_at acme sofia.",
                 "works_at sofia acme.")
    r = Formalizer(llm).add(memory, "Sofia works at Acme.")
    assert r.ok and len(r.attempts) == 2
    assert r.attempts[0].error.stage == "type"
    feedback = llm.asked[1][-1]["content"]
    assert "acme has type org" in feedback
    assert r.memory.holds("works_at sofia acme")
# ANCHOR_END: retry


def test_retry_gives_up_after_tries(memory, script):
    llm = script(*["works_at olena acme."] * 3)
    r = Formalizer(llm, tries=3).add(memory, "Olena.")
    assert not r.ok and len(r.attempts) == 3
    assert r.memory is memory
    assert len(llm.asked) == 3


def test_the_llm_sees_the_conversation(memory, script):
    llm = script("works_at acme sofia.",
                 "works_at sofia acme.")
    Formalizer(llm).add(memory, "Sofia works at Acme.")
    roles = [m["role"] for m in llm.asked[1]]
    assert roles == ["user", "assistant", "user"]


def test_ask_runs_the_query(memory, script):
    llm = script("minutes T M, event 1 _ _ _ T _",
                 "event 1 _ _ _ T _, minutes T M")
    r = Formalizer(llm).ask(memory, "kickoff minutes?")
    assert r.ok and r.answers[0]["M"] == "2880600"
    assert r.attempts[0].error.stage == "mode"


def test_system_prompt_is_the_contract():
    from agent.formalize import system_prompt
    s = system_prompt()
    assert "pred knows o:person, o:person." in s
    assert "Rules may only define: knows." in s
