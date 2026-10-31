"""Chapter 13: a wrong guess the rules cannot catch.

The LLM matches "Bob" to anna. The answer is well typed,
anna is a person, and the rule that called it goes on to
prove the rest. The proof shows which step was a guess."""
from agent.host import SamePerson
from agent.memory import Memory


# ANCHOR: canned
class Canned:
    """An LLM that answers from a table: a stand-in
    for any provider, offline."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = replies

    def complete(self, system, messages) -> str:
        return self.replies[messages[-1]["content"]]
# ANCHOR_END: canned


# ANCHOR: wrong
llm = Canned({"Bob": '{"person": "anna"}',
              "Marko": '{"person": "marco"}'})
m = Memory().with_host(same_person=SamePerson(llm))
print(m.holds('met_by_name "Bob" "Marko"'))
print(m.why('met_by_name "Bob" "Marko"'))
# ANCHOR_END: wrong
