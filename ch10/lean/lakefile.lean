import Lake
open Lake DSL

package ch10 where
  leanOptions := #[⟨`autoImplicit, false⟩]

-- lean-elpi from a local checkout that is already built
-- (`lake build` there), so this project does not rebuild it.
-- TODO(release): switch to the tagged release:
-- require «lean-elpi» from git
--   "https://github.com/Volland/lean-elpi" @ "v0.4.0"
require «lean-elpi» from "../../../../../work/lean-elpi"

@[default_target] lean_lib Ch10 where
  roots := #[`Certify, `Directives]
