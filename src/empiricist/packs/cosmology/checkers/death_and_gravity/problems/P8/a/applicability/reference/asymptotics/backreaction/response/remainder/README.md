# A.7: a finite-amplitude quantum-stress error certificate

The actual prepared scalar state's renormalized stress is approximated by an
explicit retarded functional on the exact metric. This checkpoint bounds its
nonlinear error, not just a first derivative at zero amplitude. An IR/UV split
controls all frequencies and two derivatives; rational smooth-cutoff bounds
make the finite-amplitude domain explicit.

At `delta=10^-12` the certified error is below one percent of each positive
radiation-reference component on the observation envelope. This is not a
relative error against actual stress or a claim that the metric solves SEE.

Read [FORMULATION.md](FORMULATION.md), [the proof](notes/proof.md), and
[the source dictionary](notes/sources.md). Earlier checkpoints are unchanged.

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src:problems/P8/a/applicability/reference/src:problems/P8/a/applicability/reference/asymptotics/src:problems/P8/a/applicability/reference/asymptotics/backreaction/src:problems/P8/a/applicability/reference/asymptotics/backreaction/response/src:problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/src .venv/bin/python -m p8a_remainder.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/reference/asymptotics/backreaction/response/remainder/tests -q
```

The verifier prints a report when run without `--check` and never writes it.
The pinned report is `certificates/radiation-remainder.json`. No finite-
amplitude SEE shadowing, stability, QSEI or focusing conclusion is claimed.
