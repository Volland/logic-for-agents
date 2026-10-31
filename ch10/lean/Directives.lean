/-
Chapter 10: what the LF directives `#mode` and `#total` report.
The Lean commands check them; the command line does not.
-/
import Elpi
open Elpi.LFCmd

-- ANCHOR: mode
/-- error: clause skip violates the mode: in premise
  `chain Y Z`, input argument 1 contains `Y`, which is
  not ground -/
#guard_msgs (whitespace := lax) in
lf_signature modes "../modes.elpi"
-- ANCHOR_END: mode

lf_signature home "../home.elpi"

-- ANCHOR: missing
/-- error: totality of lives: input coverage fails:
  missing case `lives sofia C` -/
#guard_msgs (whitespace := lax) in
lf_export home
-- ANCHOR_END: missing

lf_signature homes "../home_all.elpi"

-- ANCHOR: total
/-- info: lives is total in its first argument (P),
  with inputs P and output C -/
#guard_msgs (whitespace := lax) in
lf_export homes
-- ANCHOR_END: total

-- ANCHOR: theorem
/-- info: Homes.lives_total :
  ∀ (P : Homes.Person), ∃ C, Homes.Lives P C -/
#guard_msgs (whitespace := lax) in
#check @Homes.lives_total
-- ANCHOR_END: theorem

/-- info: 'Homes.lives_total' does not depend on any axioms -/
#guard_msgs in
#print axioms Homes.lives_total

-- A quirk of lean-elpi 0.4 (not shown in the book): the mode
-- checker reads `step`'s premises in proof-term order
-- (`chain Y Z` first), while the search runs them in the order
-- written (`reports_to X Y` first). So the chain rules of
-- `chain.elpi`, which search well, fail the mode check.
/-- error: clause step violates the mode: in premise
  `chain Y Z`, input argument 1 contains `Y`, which is
  not ground -/
#guard_msgs (whitespace := lax) in
lf_signature moded lp%{
#lf
person : type.
anna : person.
marco : person.
reports_to : person -> person -> type.
#mode reports_to +X -Y.
rt_marco : reports_to marco anna.
chain : person -> person -> type.
#mode chain +X -Y.
one  : chain X Y <- reports_to X Y.
step : chain X Z <- reports_to X Y <- chain Y Z.
}%

-- A limit of the 0.4 exporter (stated, not shown, in the book):
-- a `pi` premise over people searches, but does not export.
lf_signature hyp lp%{
#lf
person : type.
anna : person.
marco : person.
reports_to : person -> person -> type.
rt_marco : reports_to marco anna.
chain : person -> person -> type.
one  : chain X Y <- reports_to X Y.
all_under : person -> type.
au : all_under M <- (pi x:person\ reports_to x M -> chain x M).
}%

/-- info: proof: au anna (x0\ x1\ one x0 anna x1) -/
#guard_msgs in
#lf_query hyp lp%{ all_under anna }%

/-- error: lp%:11:0: in declaration 'au': outside the exportable
  fragment: a hypothetical premise over a family without
  binders -/
#guard_msgs (whitespace := lax) in
lf_export hyp
