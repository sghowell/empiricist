# The k = 1 all-four witness, FORMALIZED (2026-09-05)

`P3K1Witness.lean` is the module accepted by the harness's sandboxed kernel gate
(`LeanVerifier` 3.3, `leanchecker` + axiom audit; axioms ⊆ {propext, Classical.choice,
Quot.sound}), ingested into `runs/p3-campaign` as FORMALIZED artifact
`57d67ad5b8d1a742441dfa49b2f2524894778d9b3cc62582fb5fc167bff061fe` (Fable, 3 rounds through
the M18 formalize loop; the first two rounds were compile errors in the sqrt-arithmetic
pipeline, fixed by the model from the compiler's diagnostics).

Recorded statement (`Empiricist.p3_k1_witness_all_four`):

    ∀ (mu : Empiricist.BellLabel), ∃ i j k, Empiricist.Identifies3 Empiricist.Vk1 i j k mu

where `Vk1` is the balanced exact witness from the deterministic tier (entries in
ℚ(i, √2, √3), the certified artifact `ffbda750…`), `perm3` is the 3 × 3 permanent over
three output rows and the two Bell columns plus the ancilla column 4, `rawAmp3` mirrors the
trusted k = 0 `rawAmp` (phiP ↦ perm 0 2 4 + perm 1 3 4, …), and `Identifies3` is the k = 0
`Identifies` predicate (nonzero for the label, zero for the other three). This is the exact
k = 1 counterpart of the FORMALIZED k = 0 theorem `p3_at_most_three`, which says no 4 × 4
unitary identifies all four Bell states.

Faithfulness review (2026-09-05): the four definitions match the specification verbatim and
the theorem is the intended statement. That module does not itself assert that `Vk1` is
unitary; `P3K1Exists.lean` (FORMALIZED artifact
`c6e57d9d6135ef3c3493a4712a32971f79717bde7ce49d15b682062c2fe47ce5`, 2 rounds, scaffolded
verbatim on the first module — the diff is imports plus an appended section) closes that gap
with `Vk1_unitary : Vk1 ∈ Matrix.unitaryGroup (Fin 5) ℂ` (all 25 entries of `star Vk1 * Vk1 = 1`
by the same sqrt-arithmetic pipeline) and records the clean existential statement

    ∃ V ∈ Matrix.unitaryGroup (Fin 5) ℂ, ∀ (mu : Empiricist.BellLabel), ∃ i j k, Empiricist.Identifies3 V i j k mu

(`Empiricist.p3_k1_all_four_exists`, axioms ⊆ {propext, Classical.choice, Quot.sound}): there
exists a unitary 5-mode interferometer with one ancilla photon that identifies all four Bell
states. Together with `p3_at_most_three` (no 4 × 4 unitary does), this is the machine-verified
boundary of the identification question between k = 0 and k = 1. Total spend for the two
loops ≈ $13.

Leaf-theorem policy: like the P5 family theorems, this is a ledger leaf (not promoted into the
trusted foundation set); the source is kept here for the record.
