# P8(b): completed scoped stable-bounce classification

All 16 covariant function-group rows are decided in each of the two frozen
matter sectors. Minimal optional supports are:

- **M0, no extra matter: C or D.** C allows X-dependent curvature coupling
  F2_X; D allows A3 with its dependent Ia completion.
- **M1, rolling free canonical matter: both C and D.** Backreaction is included.

There are 12 existence/4 exclusion rows in M0 and 4 existence/12 exclusion
rows in M1. Three explicit covariant actions certify the existence boundary;
the no-go proof excludes the remaining rows without a parameter scan.
All witnesses are all-time, causally geodesically complete and have healthy
luminal linear principal modes, a regular gamma-crossing chart, and
quantitatively checked conventional GR/scalar tails in a covariant tube.

This completes **the frozen linear P8(b) task**, not all of P8. It does not
establish P8(a), nonlinear/BKL stability, infrared stability at every
wavelength, a strong-coupling hierarchy, UV positivity/completion, or
observational viability. It is certificate-backed, not Lean-formalized.

## Read the result

- [Scope and conventions](FORMULATION.md).
- [Classification theorem and full row table](notes/s3-classification.md).
- [Covariant derivation and regular crossing charts](notes/s1-derived-action.md).
- [Three exact witnesses and all-time coverage](notes/s2-rational-witnesses.md).
- [Known-answer regressions and two source inconsistencies](notes/s2-benchmarks.md).
- [Final adversarial self-review](notes/s4-review.md).

The first S0 certificate remains unchanged and does not retroactively claim
a covariant theorem. Later results are recorded separately in `CLAIMS.md`.

## Offline verification

From the repository root, using the existing locked environment:

```sh
.venv/bin/python -m pytest problems/P8/tests -q
PYTHONPATH=problems/P8/src .venv/bin/python -m p8.verify_all --check
.venv/bin/ruff check problems/P8
```

The complete replay checks the original S0 anchor plus six later artifacts:
the covariant derivation, corrected A25 benchmark, three witnesses, and
classification. It recomputes exact algebra, FLINT Sturm counts, rational
Bernstein bounds and Arb enclosures, and compares source/document hashes.
The analytic continuation, tail and global no-go lemmas are explicit written
proofs linked from the certificates; machine replay does not formalize them.

No downloads, paid compute or external services are needed. The repository's
default pytest configuration targets P9, so select P8 explicitly. To print
fresh reports for inspection, omit `--check`; this never overwrites evidence.
Use `--report witness-C.json` to select one artifact. Do not replace a stored
certificate merely to hide a failed check.
