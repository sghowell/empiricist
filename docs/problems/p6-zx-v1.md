# Problem 6, formulation `p6-zx-v1`: ZX rewriting in the zx pack's model

**Status:** frozen 2026-09-09. Claims with `problem: P6` and `formulation_version: p6-zx-v1`
are statements about the objects defined here, checked by the `zx` pack's verifiers
(`empiricist.packs.zx`, manifest version 0.1). A change to any definition below is a new
formulation version, never an edit of this one.

Source problem: `docs/open_problems_ftfbqc.md`, Problem 6 (proof complexity and confluence of
ZX rewriting), parts (i) and (ii). References: Backens 2014 [20] (the ZX-calculus is complete
for stabilizer quantum mechanics); Jeandel–Perdrix–Vilmart 2018 [21] (complete axiomatisation
for Clifford+T, arXiv:1705.11151, whose Figure 1 the pack's rule library decodes).

## 1. Diagrams

A **diagram** is a finite open multigraph: vertices of kind `Z` (green spider), `X` (red
spider) or `B` (boundary); a **phase** on every spider, an element of `(1/4)·Z / 2Z`, written
in units of π (so `1/2` is π/2; `k/4` for k in 0..7 is the Clifford+T phase set, `k/2` for k
in 0..3 the **stabilizer** set); edges as a multiset of unordered pairs, each plain or
**Hadamard**; self-loops and parallel edges allowed; boundary vertices have degree 1 and are
listed as ordered **inputs** and **outputs**. The pack's canonical JSON is
`{"vertices": [[id, kind, phase]], "edges": [[u, v, hadamard]], "inputs": [...], "outputs":
[...]}` with phases as reduced fractions. Two diagrams are **equal** when they are isomorphic
as multigraphs with kinds, phases and edge types preserved and the boundary orders respected
(the pack's `relabel_canonical` decides this).

**Semantics.** A diagram with `i` inputs and `o` outputs denotes a `2^o × 2^i` matrix by the
standard ZX interpretation: a Z spider of degree d and phase α is the tensor with entry 1 at
0…0 and e^{iπα} at 1…1 (zero elsewhere), an X spider is the Z spider conjugated by Hadamard on
every leg, a Hadamard edge is the Hadamard matrix, a plain edge is the identity, a boundary
vertex is the identity wire, a self-loop is a trace. Two diagrams are **semantically equal**
when their matrices are equal up to a non-zero complex scalar (the zero matrix is equal only to
the zero matrix). The pack's oracle evaluates diagrams with at most 6 boundary wires, 64
vertices, degree 16 and 20 simultaneously open indices, with tolerance 1e-9 after
normalisation; anything larger is "not judged", never "not equal".

## 2. Rules and the rewriting relation

A **rule** is a pair of patterns `lhs`, `rhs` — diagrams over a shared **interface** (their
`B` vertices, each of degree 1 on both sides) whose spider phases may be linear expressions
over shared variables — together with a **residual** map: an LHS interior vertex listed there is
a **star** vertex, allowed to carry host legs beyond the pattern's own, which are re-attached
to the listed RHS target(s), with the Hadamard flag toggled where the target's flip is set. A
rule is used **forward** (lhs → rhs) unless stated; `reversed()` swaps the sides and inverts
the residual map.

A **matching** of a rule in a host diagram is a map from LHS vertices to host vertices such
that: it is injective on spiders and maps kinds to kinds; interface vertices map to any host
vertex (two interface vertices may share an image; an image may be a boundary vertex or a
spider) but never to the image of a deleted spider (the **identification condition**); every
LHS edge maps to a distinct host edge of the same type between the images; a non-star spider's
host image has exactly the pattern degree (**degree-exact**); a star's host image may have
extra incident edges (its **residual legs**); LHS phases are solved for variables with unit
coefficient and otherwise must match syntactically. **Applying** a matched rule deletes the
spider images and the matched edges, inserts the RHS with fresh ids, and re-attaches every
residual leg to its target with the target's flip. `G → G'` (one **step**) when some rule of
the system, in the forward direction, applies to `G` at some matching and yields `G'`. This
relation — not the standard DPO presentation on open graphs with !-boxes — is what every P6
claim under this formulation is about; the mapping between the two is not established here.

The **library** is the pack's decoding of JPV18 Figure 1 up to non-zero scalars plus the rules
the graph model itself needs (identity with 0/1/2 Hadamard legs, self-loop removal), with
colour-swapped twins suffixed `_x`; the 24 **Clifford rules** are `fusion`, `fusion_x`,
`identity_z`, `identity_x`, `identity_z_h`, `identity_x_h`, `identity_z_hh`, `identity_x_hh`,
`colour_change`, `copy`, `copy_x`, `bialgebra`, `pi_commute`, `pi_commute_x`, `pi_copy`,
`pi_copy_x`, `hopf`, `hopf_h`, `euler`, `euler_x`, `loop_z`, `loop_x`, `loop_z_h`, `loop_x_h`.
A claim may also name an inline rule by its JSON.

## 3. Properties a claim may assert

- **Sound (on a class of instances).** A rule is sound on an instance (a grounding of its
  variables over a phase set and a choice of residual legs per star) when the LHS instance and
  its rewrite are semantically equal. "Sound on stabilizer instances with up to k residual legs
  per star" means: for every grounding over the stabilizer phases and every configuration of at
  most k extra legs of each type on each star vertex, within the oracle's budget. This is a
  statement about finitely many instances; it is checked exhaustively (`zx_rule_sound`).
- **Terminating under a measure M.** M is a lexicographic tuple of local counts (`vertices`,
  `z_vertices`, `x_vertices`, `edges`, `hadamard_edges`, `plain_edges`, `self_loops`) of the
  interior; a system is terminating under M when every rule strictly decreases M on every
  instance, checked symbolically per rule over every residual-leg category (`zx_termination`).
  This implies termination of `→` for that system.
- **Locally confluent within depth d at residual arity ≤ k.** For every unordered pair of rules
  of the system, every critical overlap — a minimal host both LHSs match while sharing a deleted
  spider or matched edge, with star vertices carrying up to k extra context legs of each type —
  has its two results joinable by at most d forward steps on each side (`zx_critical_pairs`).
  **This is exactly what is asserted, no more:** the critical-pair lemma for star (variable-arity)
  rules is not established in this formulation, so local confluence at arity ≤ k does not by
  itself yield local confluence of `→` on all hosts. A claim that omits the arity bound is out of
  scope for `p6-zx-v1`.
- **Complete for the class C(w, v, e).** C(w, v, e) is the set of well-formed diagrams with at
  most w boundary wires in total, at most v interior spiders with stabilizer phases, and at most e
  edges counted with multiplicity, up to isomorphism. A system is complete for C(w, v, e) when
  every diagram in the class reduces (first applicable rule, deterministic order) to a normal form
  within the step budget and semantically equal diagrams share one normal form
  (`zx_completeness`). A FAIL is a certified counterexample pair.

## 4. Levels under this formulation

A property checked exhaustively over a bounded, stated class is VERIFIED_N with `n` the number
of instances or pairs judged and `coverage: exhaustive`. A universal statement contradicted by a
certified FAIL is REFUTED (terminal) and stays in the ledger with its witness. CERTIFIED and
FORMALIZED are reserved for statements about all hosts of the relation, which need the missing
critical-pair lemma or a Lean proof.
