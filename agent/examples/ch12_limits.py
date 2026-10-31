"""Chapter 12: what passes every guard and is still
wrong. The guards check form and the rules we wrote,
not what the user meant."""
from agent.formalize import guard, guard_query
from agent.memory import Memory

m = Memory()

# ANCHOR: invention
# "Sofia and Taras had a call." Nobody said so.
text = ("event 14 call [sofia, taras] lviv "
        "(d 2001 9) (d 2001 10).")
print(guard(m, text).history)
# ANCHOR_END: invention

# ANCHOR: wrong_rule
# "People know each other if they report to each
# other." Half of it: one direction only.
k = guard(m, "knows X Y :- reports_to X Y.")
print(k.ask("knows anna Y"), k.ask("knows marco Y"))
# ANCHOR_END: wrong_rule

# ANCHOR: wrong_query
# "Who reports to Anna?" Two queries pass the guards.
print(guard_query(m, "chain anna M"))
print(guard_query(m, "chain M anna"))
# ANCHOR_END: wrong_query
