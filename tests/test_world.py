"""Loading: accumulate by concatenation, the signature,
the contract the LLM sees."""
import re

import pytest
from leanelpi import ElpiError, Program

from agent import world


def test_program_cannot_follow_accumulate():
    with pytest.raises(ElpiError, match="accumulated"):
        Program("accumulate world.\n")


def test_source_inlines_each_file_once():
    src = world.source()
    assert not re.search(r"^accumulate", src, re.M)
    assert src.count("kind person") == 1
    # rules that accumulate world, time and derived
    # still get one copy of each
    assert src.count("pred overlaps") == 1
    assert src.count("pred attends") == 1


def test_the_concatenated_program_loads(memory):
    assert memory.holds("works_at anna acme")
    assert memory.holds("chain marco anna")


def test_load_declares_the_host_predicates(memory):
    with pytest.raises(ElpiError, match="now"):
        memory.program.solve("now T")


def test_signature_reads_modes_and_constants():
    sig = world.signature()
    assert sig.modes["minutes"] == ("i", "o")
    assert sig.types["event"][2] == "list person"
    assert "sofia" in sig.constants["person"]
    assert sig.kind_of("berlin") == "city"
    assert sig.kind_of("olena") is None


def test_contract_shows_the_world_not_the_machinery():
    text = world.contract()
    assert "pred knows o:person, o:person." in text
    assert "pred event o:int, o:evkind" in text
    for private in ("prove", "rule", "question",
                    "violation", "same_person"):
        assert f"pred {private} " not in text
