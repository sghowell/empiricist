# A.2: exact radiation-background QSEI applicability test

For a massless minimally coupled scalar on the specified radiation FLRW patch,
the evaluated difference-QSEI functional has exact proper-time corrections:

`Q[h] = hbar/(16*pi^2) * integral [hddot^2 - 3*hdot^2/(8*t^2) + 105*h^2/(256*t^4)] dt`.

Independent positive-form and Hardy identities prove
`0 <= Q[h] <= hbar*||hddot||^2/(16*pi^2)` on every compact sampling interval
strictly above `t=0`. This removes an assumed small-duration requirement for
the **difference bound in this fixed testbed**.

The absolute reference-state EED is retained. Its value, the semiclassical
Einstein equations and a new cosmological singularity theorem remain open.
The result is not full P8(a) completion.

- [Frozen physical and sampling scope](FORMULATION.md)
- [Spectral derivation and reference-state bridge](notes/derivation.md)
- [Primary-source dictionary](notes/sources.md)
- [Pinned read-only certificate](certificates/radiation-qsei.json)

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src .venv/bin/python -m p8a_radiation.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/tests -q
.venv/bin/ruff check problems/P8/a/applicability
```

Without `--check`, the verifier prints a candidate report, never writing it.
The replay pins and validates the unchanged A.1 checkpoint and all new inputs,
then repeats symbolic identities, independent FLINT proper/conformal integrals
and Arb enclosures.

Next: calculate the renormalized reference EED in a fully specified prescription,
then establish which, if any, semiclassical solutions and normal geodesic families
can use the resulting absolute bound. Neither step can be inferred from flat
rescaled mode functions alone.
