"""Chapter 11: derived facts come with their proofs."""
from agent.memory import Memory

m = Memory()

# ANCHOR: why
print(m.why("chain marco anna"))
print("--")
print(m.why("colleague anna marco"))
print("--")
print(m.why("met anna marco"))
print("--")
print(m.why("met anna taras"))
# ANCHOR_END: why

# ANCHOR: raw
s = m.solve("prove (chain marco anna) P")[0]
print(s["P"])
# ANCHOR_END: raw
