"""Chapter 11: the rules call Python. `now` is a clock;
`calendar` is a calendar the memory does not hold."""
from leanelpi import Const, ElpiError

from agent.host import calendar, clock
from agent.memory import Memory
from agent.terms import wrap

m = Memory()

# ANCHOR: clock
early = m.with_host(now=clock(1999, 0))
late = m.with_host(now=clock(2000, 12))
print(early.ask("upcoming E"))
print(late.ask("upcoming E"))
# ANCHOR_END: clock

# ANCHOR: calendar
slots = {"anna": [((2001, 14), (2001, 15))]}
m2 = m.with_host(calendar=calendar(slots))
for who, a, b in [("anna", 14, 15), ("anna", 16, 17)]:
    q = f"free {who} (d 2001 {a}) (d 2001 {b})"
    print(q, m2.holds(q))
q = "free anna (d 2000 10) (d 2000 11)"
print(q, m2.holds(q))
q = "free taras (d 2000 10) (d 2000 11)"
print(q, m2.holds(q))
# ANCHOR_END: calendar

# ANCHOR: no_host
try:
    m.ask("upcoming E")
except ElpiError as e:
    print(wrap(str(e), "ElpiError: "))
# ANCHOR_END: no_host

# ANCHOR: wrong_type
broken = m.with_host(now=lambda: [Const("lisbon")])
try:
    broken.ask("upcoming E")
except ElpiError as e:
    print(wrap(str(e), "ElpiError: "))
# ANCHOR_END: wrong_type
