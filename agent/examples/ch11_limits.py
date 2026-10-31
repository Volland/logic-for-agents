"""Chapter 11: what the logic layer lets through. Each
of these is well-typed and breaks no rule we wrote."""
from agent.memory import Memory

m = Memory()

# ANCHOR: limits
for clause in [
        # Lena works at Lumen; now also at Acme.
        "works_at lena acme.",
        # Ends an hour before it starts.
        "event 13 talk [lena] porto (d 2002 9) (d 2002 8).",
        # Taras and Sofia never spoke. Or did they?
        "event 14 call [sofia, taras] lviv "
        "(d 2001 9) (d 2001 10)."]:
    verdict = m.propose(clause)
    print(clause)
    print("  " + type(verdict).__name__)
# ANCHOR_END: limits
