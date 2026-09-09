# Finite-slab backreaction: P8(a) A.5

The first-order radiation correction is
`a/a0=1-epsilon*kappa*hbar/(46080*pi^2*t^2)+O(epsilon^2)` after fixing the
normalization/time-origin modes. A conserved order-reduced surrogate has an
exact solution and certified rational Taylor/error bounds. A smooth
transported-state construction also gives a qualitative second-order actual
Einstein residual on compact positive-time slabs.

This is not an exact SEE solution or a numerical bound on the actual quantum
response. Read [FORMULATION.md](FORMULATION.md) and
[notes/proof.md](notes/proof.md) for the distinction; primary sources and
their assumptions are listed in [notes/sources.md](notes/sources.md).

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src:problems/P8/a/applicability/reference/src:problems/P8/a/applicability/reference/asymptotics/src:problems/P8/a/applicability/reference/asymptotics/backreaction/src .venv/bin/python -m p8a_backreaction.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/reference/asymptotics/backreaction/tests -q
.venv/bin/ruff check problems/P8/a/applicability/reference/asymptotics/backreaction
```

Replay is read-only. It pins and replays A.4 and all its dependencies before
checking this checkpoint's symbolic identities, independent rational
polynomials, source/test/document hashes, and domain/overclaim controls.
Without `--check` it prints, but never writes, a candidate report. All test
basenames are distinct from earlier checkpoints.
