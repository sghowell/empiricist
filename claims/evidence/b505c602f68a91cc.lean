import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Acyclic
import EmpiricistLean.Basic
import EmpiricistLean.LocalComp
import EmpiricistLean.FusionRule
import EmpiricistLean.CenterMerge

namespace Empiricist

open SimpleGraph

/-- Extended production model: starting from the GHZ₃ resource graph, we may
apply the engine-verified leaf-merge (pendant) fusion, the engine-verified
center-merge (false-twin) fusion, free local complementation (local Clifford),
and relabelling by graph isomorphism.  The `Nat` index counts fusions used. -/
inductive ProducibleByExt : Nat → {V : Type} → SimpleGraph V → Prop
  | base : ProducibleByExt 0 GHZ3graph
  | leafMerge {m : Nat} {V : Type} (G : SimpleGraph V) (a : V) :
      ProducibleByExt m G → ProducibleByExt (m + 1) (ghz3LeafMerge G a)
  | centerMerge {m : Nat} {V : Type} (G : SimpleGraph V) (a : V) :
      ProducibleByExt m G → ProducibleByExt (m + 1) (ghz3CenterMerge G a)
  | lc {m : Nat} {V : Type} (G : SimpleGraph V) (v : V) :
      ProducibleByExt m G → ProducibleByExt m (localComplement G v)
  | iso {m : Nat} {V W : Type} {G : SimpleGraph V} {H : SimpleGraph W} :
      ProducibleByExt m G → G ≃g H → ProducibleByExt m H

/-- The extended model reaches C₄ (the false twin of GHZ₃'s centre, the
smallest non-tree distance-hereditary graph) in a single fusion, directly via
the center-merge primitive. -/
theorem producibleByExt_c4 :
    ProducibleByExt 1 (addFalseTwin GHZ3graph (1 : Fin 3)) :=
  ProducibleByExt.iso
    (ProducibleByExt.centerMerge GHZ3graph 1 ProducibleByExt.base)
    (ghz3CenterMerge_iso_addFalseTwin GHZ3graph 1)

end Empiricist