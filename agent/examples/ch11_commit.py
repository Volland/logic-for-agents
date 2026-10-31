"""Chapter 11: propose, check, commit. The old memory
stays as it was."""
from agent.memory import Accepted, Memory
from agent.terms import wrap

# ANCHOR: phantom
m0 = Memory()
phantom = ("event 3 meeting [anna, lena] berlin "
           "(d 2000 10) (d 2000 12).")
v = m0.propose(phantom)
print(type(v).__name__)
for broken in v.violations:
    print(broken.rule)
    print("  " + broken.detail)
# ANCHOR_END: phantom

# ANCHOR: propose
call = ("event 11 call [lena, taras] kyiv "
        "(d 2001 9) (d 2001 10).")
v = m0.propose(call)
print(type(v).__name__)
m1 = v.memory
# ANCHOR_END: propose

# ANCHOR: persistent
print(m1.ask("attends 11 P"))
print(m0.ask("attends 11 P"))
print(len(m0.history), len(m1.history))
# ANCHOR_END: persistent

# ANCHOR: more
for clause in ["reports_to taras anna.",
               "event 12 talk [sofia] porto "
               "(d 900 9) (d 900 10).",
               "event 1 trip [taras] lviv "
               "(d 10 0) (d 11 0).",
               "works_at acme sofia.",
               "works_at olena lumen."]:
    v = m1.propose(clause)
    if isinstance(v, Accepted):
        print("accepted:", clause)
    else:
        broken = v.violations[0]
        print(broken.rule)
        print(wrap(broken.detail, "  ", "  "))
# ANCHOR_END: more

# ANCHOR: history
v = m1.propose("works_at sofia lumen.")
m2 = v.memory
for clause in m2.history:
    print(clause)
print(len(m1.history), len(m2.history))
# ANCHOR_END: history
