"""A little agent (Chapter 13).

Each user message goes to the LLM, which proposes one
action as JSON. The logic layer decides: it remembers a
fact only if no rule breaks, answers queries with proofs,
answers what-ifs under `=>` without changing memory, and
calls the LLM back (`same_person`) from inside a rule.
The LLM sees one message at a time: the memory, not the
chat history, is the agent's state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import world
from .clauses import read_query, variables
from .formalize import GuardError, guard_query
from .host import SamePerson
from .llm import LLM
from .memory import Accepted, Memory
from .terms import wrap
from .parse import SCHEMA, ParseError, strip_fence, \
    to_clause

SYSTEM = """You are the language side of an assistant \
agent. Its memory is a λProlog program; you never change \
it yourself. Turn the user's message into exactly one \
JSON action:

{{"do": "remember", "facts": [FACT, ...]}}
{{"do": "ask", "query": "<λProlog query>"}}
{{"do": "why", "goal": "<λProlog goal, no variables>"}}
{{"do": "what_if", "assume": [FACT, ...], \
"query": "<λProlog query>"}}
{{"do": "say", "text": "<a short reply>"}}

A FACT is a JSON object with "pred" and these keys:
{facts}
A time is {{"day": D, "hour": H}}.

Queries and goals use this signature:

{contract}

Names in the user's words may not be the constants \
above (a nickname, another spelling). For those, use \
met_by_name "Name" "Name", which asks for a match.
Answer with the JSON only."""


def system_prompt() -> str:
    facts = "\n".join(
        f'  "{p}": ' + ", ".join(keys)
        for p, keys in SCHEMA.items())
    return SYSTEM.format(facts=facts,
                         contract=world.contract())


@dataclass
class Agent:
    llm: LLM
    memory: Memory = field(default_factory=Memory)
    system: str = field(default_factory=system_prompt)

    def __post_init__(self) -> None:
        # What the LLM proposed, for the transcript.
        self.trace: list[str] = []
        # Logic calls the LLM back: same_person.
        names = SamePerson(self.llm)

        def same_person(name: str):
            new = name not in names.answers
            rows = names(name)
            if new:  # the LLM was asked just now
                who = rows[0].name if rows else "nobody"
                self.trace.append(
                    f'same_person "{name}" -> {who}')
            return rows

        self.memory = self.memory.with_host(
            same_person=same_person)

    # ANCHOR: turn
    def turn(self, text: str) -> str:
        """One user message in, one reply out."""
        msg = {"role": "user", "content": text}
        reply = self.llm.complete(self.system, [msg])
        try:
            action = json.loads(strip_fence(reply))
            do = action["do"]
        except (ValueError, KeyError, TypeError):
            return "I did not understand the model's reply."
        self.trace.append(summary(action))
        handler = getattr(self, f"do_{do}", None)
        if handler is None:
            return f"I cannot {do}."
        try:
            return handler(action)
        except (KeyError, TypeError):
            return "The model's action is missing a part."
    # ANCHOR_END: turn

    # ANCHOR: remember
    def do_remember(self, action: dict) -> str:
        out = []
        for fact in action.get("facts", []):
            try:
                clause = to_clause(fact)
            except ParseError as e:
                out.append(f"I can't read that: {e}.")
                continue
            verdict = self.memory.propose(clause)
            if isinstance(verdict, Accepted):
                self.memory = verdict.memory
                out.append(f"Remembered:\n  {clause}")
            else:
                v = verdict.violations[0]
                out.append(
                    f"I won't remember:\n  {clause}\n"
                    f"It breaks the rule {v.rule}:\n"
                    f"  {v.detail}.")
        return "\n".join(out) or "Nothing to remember."
    # ANCHOR_END: remember

    # ANCHOR: ask
    def do_ask(self, action: dict) -> str:
        query = action["query"]
        try:
            answers = guard_query(self.memory, query)
        except GuardError as e:
            return (f"I can't run {query}: the "
                    f"{e.stage} check says {e.message}")
        if not answers:
            return f"No: {query} does not follow from " \
                   "what I know."
        if not variables_of(query):
            proof = self.memory.why(query)
            return f"Yes. Because:\n{proof}"
        return "\n".join(show(a) for a in answers)
    # ANCHOR_END: ask

    def do_why(self, action: dict) -> str:
        proof = self.memory.why(action["goal"])
        if proof.startswith("no proof"):
            return f"I don't think so: {proof}."
        return f"Because:\n{proof}"

    # ANCHOR: what_if
    def do_what_if(self, action: dict) -> str:
        """Answer under `=>`; commit nothing."""
        try:
            assume = [to_clause(f)
                      for f in action.get("assume", [])]
        except ParseError as e:
            return f"I can't read that: {e}."
        query = action["query"]
        out = [f"That would break {v.rule}: {v.detail}."
               for v in self.memory.violations_if(assume)]
        out.append("If that were true:")
        out += answers(self.memory.what_if(assume, query))
        out.append("Memory, unchanged, says:")
        out += answers(self.memory.ask(query))
        return "\n".join(out)
    # ANCHOR_END: what_if

    def do_say(self, action: dict) -> str:
        return str(action.get("text", ""))


def summary(action: dict) -> str:
    """The LLM's proposal, in one short line."""
    do = action.get("do")
    if do == "remember":
        preds = [f.get("pred", "?") for f in
                 action.get("facts", [])
                 if isinstance(f, dict)]
        return f"remember {', '.join(preds)}"
    if do == "ask":
        return f"ask {action.get('query')}"
    if do == "why":
        return f"why {action.get('goal')}"
    if do == "what_if":
        preds = [f.get("pred", "?") for f in
                 action.get("assume", [])
                 if isinstance(f, dict)]
        return (f"what if {', '.join(preds)}: "
                f"{action.get('query')}")
    return str(do)


def variables_of(query: str) -> list[str]:
    return variables(read_query(query))


def answers(found: list[dict[str, str]]) -> list[str]:
    return ["  " + show(a) for a in found] or ["  nothing"]


def show(answer: dict[str, str]) -> str:
    return ", ".join(f"{k} = {v}"
                     for k, v in sorted(answer.items()))


# ANCHOR: session
def session(agent: Agent, turns: list[str]) -> None:
    """Run a scripted conversation and print it: the
    user's turns after `>`, what the LLM proposed on
    the `llm:` lines, then the agent's reply."""
    for text in turns:
        print(wrap(text, "> ", "  "))
        agent.trace.clear()
        reply = agent.turn(text)
        for t in agent.trace:
            print(wrap(t, "  llm: ", "       "))
        print(wrap(reply))
        print()
    n = len(agent.memory.history)
    print(f"memory: {n} new fact{'s' * (n != 1)}")
    for clause in agent.memory.history:
        print("  " + clause)
# ANCHOR_END: session
