"""Memory: propose, check under =>, commit; persistent."""
import pytest

from agent.memory import Accepted, Memory, Rejected

PHANTOM = ("event 3 meeting [anna, lena] berlin "
           "(d 2000 10) (d 2000 12).")
CALL = ("event 11 call [lena, taras] kyiv "
        "(d 2001 9) (d 2001 10).")


def rules(v):
    assert isinstance(v, Rejected)
    return [x.rule for x in v.violations]


def test_a_consistent_fact_is_committed(memory):
    v = memory.propose(CALL)
    assert isinstance(v, Accepted)
    assert v.memory.holds("attends 11 taras")
    assert v.memory.history == (CALL,)


def test_commit_leaves_the_old_memory_untouched(memory):
    new = memory.propose(CALL).memory
    assert not memory.holds("attends 11 taras")
    assert memory.history == ()
    assert new is not memory


def test_the_phantom_is_refused_by_name(memory):
    v = memory.propose(PHANTOM)
    assert rules(v) == ["bilocation"]
    assert "lisbon" in v.violations[0].detail
    assert "berlin" in v.violations[0].detail


@pytest.mark.parametrize("clause, rule", [
    ("event 12 talk [sofia] porto (d 900 9) (d 900 10).",
     "born_before"),
    ("event 1 trip [taras] lviv (d 10 0) (d 11 0).",
     "duplicate_id"),
    ("reports_to marco lena.", "second_manager"),
    ("works_at acme anna.", "ill_typed"),
    ("works_at olena acme.", "unknown"),
    ("works_at anna acme", "syntax"),
])
def test_each_rule_has_a_name(memory, clause, rule):
    assert rules(memory.propose(clause)) == [rule]


def test_a_call_needs_no_presence(memory):
    # the review is a call in kyiv at the kickoff's hour
    assert memory.violations_if(
        ["event 17 call [marco] porto "
         "(d 2000 10) (d 2000 11)."]) == ()


def test_violations_if_commits_nothing(memory):
    assert memory.violations_if([PHANTOM])
    assert not memory.holds("event 3 _ _ _ _ _")


def test_two_facts_can_break_a_rule_together(memory):
    a = "reports_to sofia anna."
    b = "reports_to sofia lena."
    assert memory.violations_if([a]) == ()
    found = memory.violations_if([a, b])
    assert [v.rule for v in found] == ["second_manager"]


def test_why_prints_the_proof(memory):
    text = memory.why("chain marco anna")
    assert text.splitlines() == [
        "chain marco anna  [boss]",
        "  reports_to marco anna  [memory]"]
    assert memory.why("met anna lena") == \
        "no proof of met anna lena"


def test_why_binds_variables(memory):
    first = memory.why("colleague anna X").splitlines()[0]
    assert first == "colleague anna marco  [same_org]"


def test_what_if_answers_without_committing(memory):
    got = memory.what_if(["reports_to lena anna."],
                         "chain taras M")
    assert got == [{"M": "lena"}, {"M": "anna"}]
    assert memory.ask("chain taras M") == [{"M": "lena"}]


def test_fresh_memories_are_independent():
    a, b = Memory(), Memory()
    a2 = a.propose("works_at sofia lumen.").memory
    assert a2.holds("works_at sofia lumen")
    assert not b.holds("works_at sofia lumen")
