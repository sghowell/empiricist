# P8(a): conditional local-QEI focusing track

First checkpoint **A.1** certifies an exact local-to-long-time focusing bound
and a finite-family optimization. For the stated dimensionless test case, the
optimized sufficient initial-contraction threshold falls from
`4.8747718608/tau` to `4.4445507651/tau`, an improvement of **8.825--8.826%**
over the cubic trial in the same partition functional.

This is independent of P8(b). It is **not full P8(a) completion**: QEI validity
scales, field/state calibration and cosmological applicability remain open.
The initial pointwise Ricci condition is an explicit extra assumption.

## Evidence and replay

- [Frozen hypotheses and scope](FORMULATION.md)
- [Derivation, support coverage and focusing proof](notes/focusing.md)
- [Primary-source equation dictionary](notes/sources.md)
- [Pinned exact/validated certificate](certificates/focusing.json)

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src .venv/bin/python -m p8a.verify --check
.venv/bin/python -m pytest problems/P8/a/tests -q
.venv/bin/ruff check problems/P8/a
```

`--check` is read-only. Without it, the verifier prints a candidate report to
standard output; it never writes or silently refreshes a certificate. Replay
compares all source/doc/test hashes and recalculates the exact symbolic matrix,
independent FLINT integrals, infinite-tail reconstruction, and Arb enclosures.

## Next research checkpoint

Turn the assumed local averaging-duration bound into a quantitatively justified
field/geometry statement, or first extend the trial and partition optimization
with separately stated domains. Actual field-scale input is needed before
claiming cosmological strength. Worldvolume, null and nonminimal extensions
remain separate from this four-dimensional timelike calculation.
