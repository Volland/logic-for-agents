"""Chapter 12: the system prompt. The signature is the
contract the LLM writes against."""
from agent.formalize import system_prompt
from agent.terms import wrap

# ANCHOR: prompt
print(wrap(system_prompt()))
# ANCHOR_END: prompt
