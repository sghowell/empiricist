# P3 strategist answers (2026-09-05)

Two free-form Fable calls through the harness client (role `p3_strategist`, MEDIUM effort,
no tools, no shell), recorded in `runs/p3-campaign` as runs `p3strat-k1min-f6d58c1a`
($2.74, 30.5k output tokens, 398 s) and `p3strat-k1avg-dc23e562` ($3.16, 39.5k output
tokens, 523 s). The prompts carried the machine-verified facts (the k=0 theorem, the exact
k=1 witnesses, the optimizer landscape) and asked for decisive, refutable claims. The
answers are model output — HEURISTIC — and are kept verbatim here for provenance; nothing
in them enters the ledger without machine evidence.

- `k1-min-mechanism-and-optimality.md`: decodes the (1, 1/6, 1/2, 2/9) witness as an
  X-basis Bell analyser whose two HOM ports feed a balanced tritter with the ancilla photon
  (checked exactly below), conjectures max-min = 1/4 at k=1 for every m, proposes the
  frontier p₍₁₎ + p₍₂₎ ≤ 1/2, and lists optimizer tests P1–P6.
- `k1-avg-bound-sketch.md`: a lemma ladder S0–L6* for p_avg ≤ 1/2 at k=1; S0–L5* are
  mechanical on the existing Lean development, L6* (the one-photon distillation bound) is the
  content; a certified p_avg ≤ 3/4 at m=5 via rational SOS is named as the realistic first
  machine milestone.
