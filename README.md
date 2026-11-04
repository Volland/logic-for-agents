# Logic for Agents — companion code

Code for *Logic for Agents: Building Neurosymbolic AI with Elpi* by Volodymyr Pavlyshyn
([leanpub.com/logicforagents](https://leanpub.com/logicforagents)).

Every example in the book is cut from this repository, and every output printed in the
book is a golden file here that CI checks.

| Path | What |
|---|---|
| `lib/world.elpi`, `lib/time.elpi` | the running example: an agent's memory of people, places, organizations and events |
| `ch01/` … `ch10/` | λProlog examples per chapter; `FILE.out` is the expected output of `FILE.elpi` |
| `ch10/lean/` | a small Lean project that turns LF proofs into kernel-checked certificates |
| `solutions/` | solutions to the exercises |
| `agent/` | the Python logic layer and agent of Chapters 11–13 |
| `replay/` | recorded LLM responses, so the agent runs without an API key |
| `lfa.py` | runs Chapters 1–9 on the `leanelpi` wheel, with the `lean-elpi` program's arguments and output |
| `Dockerfile` | the `lean-elpi` program and Python in one image |
| `tests/` | the golden-file runner and the agent's tests |

## Run

Three ways in. Pick the first unless you want Chapter 10's Lean certificates.

**Python only.** Python 3.10+ and the `leanelpi` wheel from PyPI, which carries the engine:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cd ch01 && ../.venv/bin/lfa phantom.elpi -I ../lib -test   # one example
cd .. && .venv/bin/python tests/run_elpi.py                # every example
```

`lfa` takes the same arguments as the `lean-elpi` program (`-test`, `-I`, `--fuel`, the REPL)
and prints the same output; `tests/run_elpi.py --lfa` checks that against every golden file.
It cannot run Chapter 10's LF files, which `tests/run_elpi.py` then skips. From Python,
`from lfa import load` gives any chapter's file as a `leanelpi.Program`.

**Docker.** The `lean-elpi` program and Python, without installing Lean:

```bash
docker build -t logic-for-agents .
docker run --rm -it -v "$PWD":/book logic-for-agents
python3 tests/run_elpi.py && ch10/run_lf.sh               # inside
```

`docker build --target full` adds Lean, for `cd ch10/lean && lake build`.

**From source.** [lean-elpi](https://github.com/Volland/lean-elpi) v0.4.1, built with elan and
`lake build` (`lean-elpi` on your PATH, or `LEAN_ELPI=/path/to/lean-elpi`):

```bash
lean-elpi ch01/phantom.elpi -I lib -test      # one example
python3 tests/run_elpi.py                     # every example and solution
ch10/run_lf.sh                                # Chapter 10's LF proof terms
```

## Part III: the agent (Chapters 11–13)

The agent is a Python package, `agent/`, on top of the `leanelpi` binding. Its rules are
`.elpi` files in `agent/rules/`; its runnable examples are `agent/examples/chNN_*.py`, each
with a golden `.out` beside it.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q                       # unit tests and every example's output
.venv/bin/python -m agent                 # replay the Chapter 13 session
.venv/bin/python agent/examples/ch12_guards.py
.venv/bin/python agent/examples/ch12_cost.py --live   # calls, tokens, seconds per try
```

Nothing calls the network by default: the LLM's answers come from `replay/*.json`. To talk to
the real model (`claude-sonnet-5-5`), set `ANTHROPIC_API_KEY` and run

```bash
.venv/bin/python -m agent --live                       # the scripted turns, live
.venv/bin/python -m agent --live --chat                # type your own turns
.venv/bin/python -m agent --live --record replay/mine.json
```

`UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_examples.py` rewrites the examples' `.out`
files; read the diff before committing.

License: Apache-2.0.
