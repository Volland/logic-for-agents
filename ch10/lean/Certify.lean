/-
Chapter 10: Lean as the checker we call.

The searcher (lean-elpi) finds a derivation in the LF signature
`../chain.elpi`; Lean's kernel checks it. Every output the book
shows is pinned here with `#guard_msgs`, so `lake build`
fails if any of them changes. Long messages are wrapped by hand;
`whitespace := lax` compares them up to spacing.
-/
-- ANCHOR: header
import Elpi
open Elpi.LFCmd
-- ANCHOR_END: header

-- ANCHOR: signature
lf_signature org "../chain.elpi"
-- ANCHOR_END: signature

-- ANCHOR: export
lf_export org
-- ANCHOR_END: export

-- ANCHOR: check_step
/-- info: @Org.Chain.step : ∀ {X Z Y : Org.Person},
  Org.Chain Y Z → Org.Reports_to X Y → Org.Chain X Z -/
#guard_msgs (whitespace := lax) in
#check @Org.Chain.step
-- ANCHOR_END: check_step

-- ANCHOR: certify
lf_certify org sofia_anna lp%{ chain sofia anna }%
-- ANCHOR_END: certify

-- ANCHOR: print
/-- info: theorem sofia_anna :
    Org.Chain Org.Person.sofia Org.Person.anna :=
  Org.Chain.step (Org.Chain.one Org.Reports_to.rt_marco)
    Org.Reports_to.rt_sofia -/
#guard_msgs (whitespace := lax) in
#print sofia_anna
-- ANCHOR_END: print

-- ANCHOR: axioms
/-- info: 'sofia_anna' does not depend on any axioms -/
#guard_msgs in
#print axioms sofia_anna
-- ANCHOR_END: axioms

-- ANCHOR: nothing
/-- error: query has no solution -/
#guard_msgs in
lf_certify org lena_anna lp%{ chain lena anna }%
-- ANCHOR_END: nothing

-- A searcher with a bug skips a step: it claims that Sofia
-- reports straight to Anna. Lean refuses the term.
-- ANCHOR: forged
/--
error: Application type mismatch: The argument
  Org.Reports_to.rt_sofia
has type
  Org.Reports_to Org.Person.sofia Org.Person.marco
but is expected to have type
  Org.Reports_to Org.Person.sofia Org.Person.anna
in the application
  Org.Chain.one Org.Reports_to.rt_sofia
-/
#guard_msgs in
theorem forged : Org.Chain .sofia .anna :=
  .one .rt_sofia
-- ANCHOR_END: forged

-- The same forgery, handed to the kernel directly with
-- `addDecl`, the call `lf_certify` makes. No front end helps.
-- Lean keeps a rejected name (as an axiom) so it can go on
-- checking the file; `#print axioms` below gives it away.
open Lean in
def forgery : Declaration :=
  let p (n : Name) := mkConst (`Org.Person ++ n)
  .thmDecl {
    name := `forged_k
    levelParams := []
    type := mkApp2 (mkConst ``Org.Chain) (p `sofia) (p `anna)
    value := mkApp3 (mkConst ``Org.Chain.one)
      (p `sofia) (p `anna) (mkConst ``Org.Reports_to.rt_sofia) }

-- ANCHOR: kernel
/-- error: (kernel) application type mismatch
  Org.Chain.one Org.Reports_to.rt_sofia
argument has type
  Org.Reports_to Org.Person.sofia Org.Person.marco
but function has type
  Org.Reports_to Org.Person.sofia Org.Person.anna →
    Org.Chain Org.Person.sofia Org.Person.anna -/
#guard_msgs (whitespace := lax) in
run_cmd Lean.Elab.Command.liftCoreM (Lean.addDecl forgery)
-- ANCHOR_END: kernel

-- ANCHOR: forged_axioms
/-- info: 'forged' depends on axioms: [sorryAx] -/
#guard_msgs in
#print axioms forged
-- ANCHOR_END: forged_axioms

-- ANCHOR: kernel_axioms
/-- info: 'forged_k' depends on axioms: [forged_k] -/
#guard_msgs in
#print axioms forged_k
-- ANCHOR_END: kernel_axioms
