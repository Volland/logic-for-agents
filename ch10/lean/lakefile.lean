import Lake
open Lake DSL

package ch10 where
  leanOptions := #[⟨`autoImplicit, false⟩]

-- lean-elpi at the release the book pins. The first
-- `lake build` fetches and builds it into .lake/packages.
require «lean-elpi» from git
  "https://github.com/Volland/lean-elpi" @ "v0.4.0"

@[default_target] lean_lib Ch10 where
  roots := #[`Certify, `Directives]
