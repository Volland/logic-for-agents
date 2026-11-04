# The book's toolchain without installing Lean. The companion
# repository is mounted, not copied:
#
#   docker build -t logic-for-agents .
#   docker run --rm -it -v "$PWD":/book logic-for-agents
#
# The default image holds the lean-elpi program (Chapters 1-10,
# including the LF options of Chapter 10) and Python with the
# leanelpi wheel (Chapters 11-13). Inside, `python3 tests/run_elpi.py`
# checks every example. Chapter 10's kernel-checked certificates
# (`cd ch10/lean && lake build`) also need Lean itself:
#
#   docker build --target full -t logic-for-agents:full .
#
# The first build compiles lean-elpi once, which takes a while.
# Readers who skip Chapter 10's Lean part need no image at all:
# `pip install -e .` gives the `lfa` runner and the agent.

FROM python:3.12-slim-bookworm AS python
RUN pip install --no-cache-dir "leanelpi>=0.4.1" "anthropic>=2.3" pytest \
 && printf '#!/bin/sh\nexec python3 /book/lfa.py "$@"\n' > /usr/local/bin/lfa \
 && chmod +x /usr/local/bin/lfa
ENV PYTHONPATH=/book
WORKDIR /book
CMD ["bash"]

# Lean and lean-elpi at the release the book pins.
FROM python AS full
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*
ENV ELAN_HOME=/opt/elan PATH=/opt/elan/bin:$PATH
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --no-modify-path --default-toolchain none
RUN git clone --depth 1 --branch v0.4.1 https://github.com/Volland/lean-elpi /opt/lean-elpi \
 && cd /opt/lean-elpi && lake build lean-elpi \
 && ln -s /opt/lean-elpi/.lake/build/bin/lean-elpi /usr/local/bin/lean-elpi

# The default: the program alone, without the toolchain that built it.
FROM python AS cli
COPY --from=full /opt/lean-elpi/.lake/build/bin/lean-elpi /usr/local/bin/lean-elpi
