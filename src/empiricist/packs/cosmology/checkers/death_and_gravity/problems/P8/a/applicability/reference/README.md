# Radiation reference stress: P8(a) A.3

The standard locally covariant massless prescription gives the specified
radiation-reference state a **positive** effective energy density,
`E_ref=hbar/(5120*pi^2*t^4)`. Combining it with A.2 closes the reference-input gap
for this exact testbed and gives an absolute QSEI with multiplier `1` for every
compact positive-time sample. A sharper positive functional is also certified.

This is fixed-background quantum-field analysis, not an SEE solution or a new
cosmological singularity theorem. Read [FORMULATION.md](FORMULATION.md) for the
field, prescription, state, endpoint conditions and limitations; the full proof
and convention audit are in [notes/derivation.md](notes/derivation.md) and
[notes/sources.md](notes/sources.md).

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src:problems/P8/a/applicability/reference/src .venv/bin/python -m p8a_reference.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/reference/tests -q
.venv/bin/ruff check problems/P8/a/applicability/reference
```

Replay is read-only. It first checks the pinned A.2 report and replays A.2/A.1,
then compares the full new report, including source/document/test hashes. Run
the verifier without `--check` to print a proposed report; it never writes one.

The evidence includes two source routes to the reference stress, symbolic
sign/conservation/mode and boundary-term checks, independent exact rational
Laurent calculations, outward Arb bounds, and negative controls for altered
signs, nonvacuum state terms, curvature counterterms away from radiation,
missing endpoint jets, added gravitational terms and tampered reports.

The next physical obligation is an SEE-compatible background/state and relevant
geodesic coverage. Neither may be inferred merely from this absolute QSEI.
