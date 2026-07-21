# P3: the certificate layer's first results — an exact ½ certificate, two proof sketches, and a randomization gap

**Date:** 2026-07-20 · **Problem:** P3 · **Method:** Fable strategist (Track A) + the M20c
exact-certificate pipeline (Track B), `runs/p3-campaign`.

## 1. The first exact certificate (machine-verified, on main)

`tests/goldens/p3_k0_standard_assignment.json`: for **every** U ∈ U(4), the standard-BSM
assignment's average success probability satisfies `p_avg ≤ 1/2` — **exactly**, the
Calsamiglia–Lütkenhaus k=0 ceiling, bound attained by the standard BSM. The certificate is a
degree-4 SOS identity over a 128-monomial Gram basis with rational coefficients throughout,
verified by the stdlib-only exact checker (polynomial identity over ℚ + rational LDL^T PSD).
Constructed analytically from the probability-conservation identity; the exact checker — not
the construction — is the warrant. Scope honestly stated: assignment-fixed, not a general
optimized `p*(0)` statement.

## 2. Track A: two Fable proof sketches (ledger artifacts)

**k=0 (`aed4942e`, HEURISTIC):** *at most 3 of the 4 Bell states can have identifying
patterns; hence min_B p_B = 0 unconditionally.* Lemma chain L1–L4: Pauli-component structure
of coincidence amplitudes (Q = XᵀσₓY; identification ⟺ Q ∝ σ_μ; bunched patterns are rank-1
and never identify — **engine-verified** on the standard BSM), a ≤2-labels-per-detector
eigenvector bound, a 2-regular-multigraph counting argument, and a unitarity contradiction
killing the 4-cycle case. Explains the wave-1 data exactly (three-way splits allowed,
four-way never). Companion conjecture at CONJECTURED (`0fa89362`), grounded on the 14
wave-1 schemes.

**k=2 (`fd8567f8`, HEURISTIC):** *Grice's floor p_min ≤ 1/2 is optimal for fixed meshes*
(sketch L1′–L4′: the Pauli reduction survives with ancilla-weighted sums; the row-decoupling
dies — precisely why k=2 helps; replacements via Bloch completeness + the symmetric UᵀU Gram;
conjectured Z-pair trade-off `p(Φ⁺)+p(Φ⁻) ≤ 1 or p(Ψ⁺)+p(Ψ⁻) ≤ 1`).

## 3. The randomization gap (engine-verified)

The k=2 sketch's caveat, confirmed by both engines: conjugating Grice's mesh by a dual-rail
Pauli X (a rail swap — itself passive) yields exactly the vector (1, 1, ½, ½) with zero
leakage. A 50/50 classical coin over {Grice, X·Grice} therefore achieves **p_min = 3/4 for
every Bell state** — the wave-2 target that fixed meshes could not reach. So the min-balanced
question splits: *randomized* schemes achieve min ¾ at k=2 (verified); *fixed-mesh* schemes
are conjectured stuck at ½ (`49ae1507`, CONJECTURED with the twirl check as evidence). The
wave-2 search's "disconnected basins" (p_min = 3/16, ≈0.073) are the Pauli-conjugated optima
of a fixed-mesh landscape — the searches were finding the right structure all along.

## Accounting

Search (waves 1–2) found the patterns; Fable's strategist produced the proofs' skeletons; the
harness verified every checkable claim (L1's bunched-pattern claim, the twirl vector, the ½
certificate) and recorded the rest at HEURISTIC/CONJECTURED. Next: formalizing the k=0
L1–L4 chain in Lean via the M18 loop (finite-dimensional 2×2 complex linear algebra —
mathlib-friendly) would make "at most 3 of 4" the first fully-verified new P3 theorem.
