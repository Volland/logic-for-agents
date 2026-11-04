"""How to Read: Chapter 1's λProlog file, asked from Python.
Run from the repository's root."""
# ANCHOR: load
from lfa import load

p = load("ch01/phantom.elpi")
for s in p.solve("works_at P acme"):
    print(s["P"])
print(p.ask("in_country lisbon portugal"))
print(p.solve("bilocated P C1 C2")[0].bindings)
# ANCHOR_END: load
