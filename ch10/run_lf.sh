#!/usr/bin/env bash
# Golden tests for the LF command-line modes of Chapter 10.
#
# tests/run_elpi.py runs `lean-elpi FILE -I lib -test` only. The LF
# examples are run with `--lf-proof QUERY` and `--lf-erase`, so this
# script runs them and compares stdout followed by stderr with the
# golden files NAME.lf.out (the same capture as run_elpi.py).
#
#   ch10/run_lf.sh            compare
#   ch10/run_lf.sh --update   rewrite the golden files; read the diff
#
# The binary is $LEAN_ELPI or `lean-elpi` on PATH.
set -u
cd "$(dirname "$0")"
EXE="${LEAN_ELPI:-$(command -v lean-elpi)}"
[ -x "$EXE" ] || { echo "lean-elpi not found: set LEAN_ELPI"; exit 2; }
UPDATE=0; [ "${1:-}" = "--update" ] && UPDATE=1

# golden file | lean-elpi arguments (one case per line)
CASES=$(cat <<'END'
chain.marco.lf.out|--lf-proof|chain marco anna|chain.elpi
chain.sofia.lf.out|--lf-proof|chain sofia anna|chain.elpi
chain.who.lf.out|--lf-proof|chain sofia B|chain.elpi
chain.lena.lf.out|--lf-proof|chain lena anna|chain.elpi
chain.erase.lf.out|--lf-erase|chain.elpi
loop.lf.out|--fuel|20000|--lf-proof|chain sofia anna|loop.elpi
loop_iddfs.lf.out|--fuel|20000|--lf-proof|chain sofia anna|loop_iddfs.elpi
END
)

pass=0; bad=0
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
while IFS= read -r line; do
  [ -z "$line" ] && continue
  IFS='|' read -r -a parts <<< "$line"
  golden=${parts[0]}; args=("${parts[@]:1}")
  "$EXE" "${args[@]}" > "$TMP/out" 2> "$TMP/err"
  cat "$TMP/out" "$TMP/err" > "$TMP/got"
  if [ $UPDATE = 1 ]; then
    cp "$TMP/got" "$golden"; pass=$((pass + 1)); continue
  fi
  if cmp -s "$TMP/got" "$golden"; then
    pass=$((pass + 1))
  else
    echo "FAIL ch10/$golden"
    diff "$golden" "$TMP/got"
    bad=$((bad + 1))
  fi
done <<< "$CASES"
echo "$pass/$((pass + bad)) LF examples pass"
[ $bad = 0 ]
