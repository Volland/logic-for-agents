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
| `tests/` | the golden-file runner and the agent's tests |

## Run

You need [lean-elpi](https://github.com/Volland/lean-elpi) v0.4 (`lean-elpi` on your PATH,
or `LEAN_ELPI=/path/to/lean-elpi`) and, for Part III, Python 3.10+.

```bash
lean-elpi ch01/phantom.elpi -I lib -test      # one example
python3 tests/run_elpi.py                     # every example and solution
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
```

Until `leanelpi` 0.4 is on PyPI, install it from a lean-elpi checkout first and point it at
the engine library you built with `scripts/build-ffi.sh`:

```bash
.venv/bin/pip install -e ../lean-elpi/bindings/python
export LEANELPI_LIB=$PWD/../lean-elpi/dist/libleanelpi.dylib   # .so on Linux
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
