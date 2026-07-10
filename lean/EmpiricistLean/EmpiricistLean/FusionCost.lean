/-
Copyright (c) 2026 Sean Howell. All rights reserved.
Released under the MIT license as described in the file LICENSE.
Authors: Sean Howell
-/
import Mathlib.Combinatorics.SimpleGraph.Acyclic
import EmpiricistLean.Basic

/-!
# The universal minimum-fusion lower bound `F(G) ≥ N − 3` (Empiricist Problem 5)

This module formalizes the folklore lower bound for the minimum-fusion synthesis
problem (Problem 5 of the FT-FBQC open-problems document):

> If `g` GHZ₃ states are consumed and `f` fusions are performed, photon counting
> gives `N = 3g − 2f`, and connectivity of the output forces `f ≥ g − 1`;
> eliminating `g` yields `F(G) ≥ N − 3` for every connected `G` on `N ≥ 3`
> vertices.

`F(G)` is the minimum number of fusions producing a graph state LC-equivalent to
`|G⟩` from an unbounded supply of GHZ₃ resource states; this file proves the
lower bound `F(G) ≥ N − 3` that every synthesis schedule must obey, so it is a
lower bound on the *minimum* `F(G)` as well.

## The physical quantities

* `g` — the number of GHZ₃ resource states consumed. Each GHZ₃ is a 3-qubit
  connected graph state, so `g` GHZ₃'s contribute `3g` qubits and start as `g`
  disjoint connected components.
* `f` — the number of fusions performed. A fusion is a destructive Bell
  measurement on **one qubit from each of two disjoint components**; it consumes
  those 2 qubits.
* `N` — the number of vertices (qubits) of the connected output graph state.

## Two invariants, and why each is faithful

**(A) Photon counting — `hcount : N + 2 * f = 3 * g`.**  Exact qubit bookkeeping:
the `g` GHZ₃'s supply `3g` qubits; every one of the `f` fusions destroys exactly
`2` of them; the `N` output vertices are what remain. This is `N = 3g − 2f`
written additively (`N + 2f = 3g`) to avoid ℕ truncated subtraction. It is an
*equality*, holding with no side conditions.

**(B) Connectivity / spanning-tree bound — `hconn : g ≤ f + 1`, i.e. `f ≥ g − 1`.**
This is the non-trivial content, and it is **derived** below (Layer 2), not
assumed: to merge `g` initially-disjoint components into a single connected
output, at least `g − 1` of the fusions must each join two distinct components.
Any single fusion decreases the number of connected components by **at most 1**
(a fusion between two distinct components merges them, `−1`; a fusion internal to
one component leaves the count unchanged, `−0`; no fusion can drop it by more).
So dropping from `g` components to `1` takes at least `g − 1` fusions.

## The three theorems

* `fusion_cost_lower_bound` — **Layer 1**, the arithmetic core: from (A) and (B),
  `N ≤ f + 3` (which is exactly `f ≥ N − 3`, and hence `F(G) ≥ N − 3`). Stated
  additively over ℕ so `omega` is exact — no truncated subtraction.
* `components_merge_bound` / `merge_graph_connectivity_bound` — **Layer 2**, two
  faithful models of the component-merge process, each *proving* invariant (B)
  rather than assuming it:
  * `components_merge_bound` — the abstract dynamics: a component-count function
    `c : ℕ → ℕ` with `c 0 = g` (start), `c f = 1` (connected output), and the
    per-fusion bound `c i ≤ c (i+1) + 1` (each fusion drops the count by ≤ 1)
    forces `g ≤ f + 1`.
  * `merge_graph_connectivity_bound` — the static spanning-tree view: the merges
    form a connected `SimpleGraph` on the `g` initial components; a connected
    graph on `g` vertices has `≥ g − 1` edges (`Empiricist.connected_edge_bound`,
    the pinned scaffold lemma), and there are `≤ f` merge-edges, so `g ≤ f + 1`.
* `fusion_cost_lower_bound_derived` / `fusion_cost_lower_bound_of_merge_graph` —
  the combined statements: photon counting **plus a merge-process object**
  (never the bare `hconn` hypothesis) yield `N ≤ f + 3`. Here invariant (B) is
  discharged by Layer 2, so the conclusion rests only on the two genuinely
  physical inputs (A) and the local merge rule.

Nothing here smuggles the conclusion into a definition: the hypotheses are the
exact qubit-count equality and *local* facts about the merge process (start `g`,
end connected, each step `−1` at most / a connected merge graph with `≤ f`
edges). The `N ≥ 3` regime of the problem statement is carried as `hN` on the
`N ≤ f + 3` theorems for faithful correspondence with the folklore statement,
even though the arithmetic holds for all `N`.
-/

namespace Empiricist

open SimpleGraph

-- `hN` (the problem's `N ≥ 3` regime) is retained for faithful correspondence
-- with the folklore statement, though `omega` does not need it for the
-- arithmetic (the bound holds for every `N`); the unused-binder linter is
-- disabled only to keep that faithful binder.
set_option linter.unusedVariables false in
/-- **Layer 1 — the arithmetic core.**  Photon counting (`hcount`) together with
the spanning-tree connectivity bound (`hconn`) force the universal minimum-fusion
lower bound.

`g` = GHZ₃ resources consumed, `f` = fusions performed, `N` = connected-output
vertices. The conclusion `N ≤ f + 3` is exactly `f ≥ N − 3` (ℕ truncated
subtraction: `f ≥ N - 3 ↔ N ≤ f + 3` for all `N`), i.e. `F(G) ≥ N − 3`.

Everything is phrased additively over ℕ so `omega` is a faithful decision
procedure with no truncated-subtraction pitfalls: `hcount` is `N = 3g − 2f`
written `N + 2f = 3g`, and `hconn` is `f ≥ g − 1` written `g ≤ f + 1`. `hN`
(the problem's `N ≥ 3` regime) is retained for faithful correspondence though
the bound is arithmetically valid for every `N`. -/
theorem fusion_cost_lower_bound {N g f : ℕ} (hN : 3 ≤ N)
    -- photon counting: `N = 3g − 2f`, each GHZ₃ = 3 qubits, each fusion consumes 2
    (hcount : N + 2 * f = 3 * g)
    -- connectivity: `f ≥ g − 1`, at least `g − 1` merging fusions to join `g` components
    (hconn : g ≤ f + 1) :
    N ≤ f + 3 := by
  omega

/-- **Layer 2 (abstract merge dynamics).**  Model a fusion schedule by its effect
on the number of connected components: `c i` is the component count after the
first `i` fusions. The schedule starts with the `g` disjoint GHZ₃ components
(`c 0 = g`), ends with a single connected output (`c f = 1`), and — the local
physical fact about a fusion — each fusion decreases the component count by **at
most one** (`c i ≤ c (i+1) + 1`, i.e. `c (i+1) ≥ c i − 1`: a merge is `−1`, an
internal fusion is `−0`, and no fusion can join more than two components).

These local hypotheses *derive* the connectivity bound `g ≤ f + 1` (`f ≥ g − 1`):
the number of components can fall by at most `1` per step, so falling from `g` to
`1` needs at least `g − 1` steps. This is invariant (B), proved rather than
assumed. -/
theorem components_merge_bound {g f : ℕ} (c : ℕ → ℕ)
    (hstart : c 0 = g) (hend : c f = 1)
    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    g ≤ f + 1 := by
  -- Invariant: after `i` fusions, the count has dropped by at most `i` from `g`,
  -- i.e. `g ≤ c i + i`. Proved by induction on `i` using the per-step `−1` bound.
  have key : ∀ i, i ≤ f → g ≤ c i + i := by
    intro i
    induction i with
    | zero => intro _; omega
    | succ n ih =>
      intro hle
      have hstep_n := hstep n (by omega)
      have hprev := ih (by omega)
      omega
  have hfinal := key f (le_refl f)
  rw [hend] at hfinal
  omega

/-- **Layer 2 (static spanning-tree view, most faithful).**  Model the schedule's
merges as a `SimpleGraph M` on the `g` initial GHZ₃ components (`Fin g`): put an
edge between two components when a fusion merges them. Since the output is a
single connected graph state, the merge graph is connected (`hconn`), and since
each of its edges is witnessed by a distinct merging fusion among the `f` total
fusions, it has at most `f` edges (`hfuse : M.edgeFinset.card ≤ f`).

A connected simple graph on `g` vertices has at least `g − 1` edges
(`Empiricist.connected_edge_bound`, the pinned scaffold lemma — the spanning-tree
bound), so `g − 1 ≤ M.edgeFinset.card ≤ f`, giving `g ≤ f + 1`. This is
invariant (B) again, now as the literal spanning-tree argument. -/
theorem merge_graph_connectivity_bound {g f : ℕ} (M : SimpleGraph (Fin g))
    [DecidableRel M.Adj] (hconn : M.Connected) (hfuse : M.edgeFinset.card ≤ f) :
    g ≤ f + 1 := by
  have hedge := connected_edge_bound M hconn
  rw [Fintype.card_fin] at hedge
  omega

/-- **Layer 2 combined (abstract).**  The universal lower bound `N ≤ f + 3` from
photon counting (`hcount`) **plus the abstract component-merge process** — the
connectivity bound `hconn` is *discharged* by `components_merge_bound`, not
assumed. This is the non-vacuous form of `fusion_cost_lower_bound`: its inputs
are the exact qubit-count equality and the local per-fusion merge rule. -/
theorem fusion_cost_lower_bound_derived {N g f : ℕ} (hN : 3 ≤ N)
    (hcount : N + 2 * f = 3 * g) (c : ℕ → ℕ)
    (hstart : c 0 = g) (hend : c f = 1)
    (hstep : ∀ i, i < f → c i ≤ c (i + 1) + 1) :
    N ≤ f + 3 :=
  fusion_cost_lower_bound hN hcount (components_merge_bound c hstart hend hstep)

/-- **Layer 2 combined (spanning-tree, most faithful end-to-end).**  The universal
lower bound `N ≤ f + 3` from photon counting (`hcount`) **plus the connected
merge graph** on the `g` initial components — the connectivity bound is
discharged by `merge_graph_connectivity_bound` (via the pinned scaffold lemma
`Empiricist.connected_edge_bound`), not assumed. -/
theorem fusion_cost_lower_bound_of_merge_graph {N g f : ℕ} (hN : 3 ≤ N)
    (hcount : N + 2 * f = 3 * g) (M : SimpleGraph (Fin g)) [DecidableRel M.Adj]
    (hconn : M.Connected) (hfuse : M.edgeFinset.card ≤ f) :
    N ≤ f + 3 :=
  fusion_cost_lower_bound hN hcount (merge_graph_connectivity_bound M hconn hfuse)

end Empiricist
