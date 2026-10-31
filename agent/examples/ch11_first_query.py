"""Chapter 11: the leanelpi API, one call at a time."""
from leanelpi import ElpiError, Program

from agent import world

# ANCHOR: load
src = world.source(["world", "time"])
memory = Program(src)
# ANCHOR_END: load

# ANCHOR: first
print(memory.first("works_at marco Org"))
print(memory.ask("reports_to marco anna"))
print(memory.ask("reports_to anna marco"))
# ANCHOR_END: first

# ANCHOR: solve
for s in memory.solve("works_at P acme"):
    print(s["P"])
# ANCHOR_END: solve

# ANCHOR: solve_all
sols, exhausted = memory.solve_all(
    "works_at P O", limit=2)
print(len(sols), "answers, exhausted:", exhausted)
# ANCHOR_END: solve_all

# ANCHOR: terms
s = memory.first("event 1 K Who C From To")
for name, value in s.items():
    print(name, "=", value)
t = memory.solve("event 1 K Who C From To")[0].terms
print(t["Who"], t["From"])
# ANCHOR_END: terms

# ANCHOR: assert
newer = memory.assert_clause("works_at sofia lumen.")
print(newer.ask("works_at sofia lumen"))
print(memory.ask("works_at sofia lumen"))
# ANCHOR_END: assert

# ANCHOR: errors
try:
    memory.assert_clause("works_at acme sofia.")
except ElpiError as e:
    print("ElpiError:")
    print(e)
# ANCHOR_END: errors

# ANCHOR: fuel
loop = memory.assert_clause(
    "reports_to X Y :- reports_to Y X.")
try:
    loop.solve("reports_to sofia M", fuel=10_000)
except ElpiError as e:
    print(e.out_of_fuel)
    print(e)
# ANCHOR_END: fuel
