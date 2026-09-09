# Whole-patch radiation obstruction: P8(a) A.4

Changing the Hadamard state cannot make the exact whole radiation patch an
SEE solution for this free massless scalar plus ordinary classical radiation.
Every such state has the same positive leading EED,
`t^4*E_omega -> hbar/(5120*pi^2)`, while the attempted Einstein equation
requires a zero limit. The result is restricted to this ansatz and source
class; it does not exclude a finite slab or a backreacted radiation-like
cosmology.

The key new ingredient is a two-variable smooth Cauchy-extension argument for
the conformally rescaled state difference. It works with arbitrary smooth
noncompact data and does not assume a state or physical metric extension
through the big bang. See [FORMULATION.md](FORMULATION.md),
[notes/proof.md](notes/proof.md), and [notes/sources.md](notes/sources.md).

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src:problems/P8/a/applicability/reference/src:problems/P8/a/applicability/reference/asymptotics/src .venv/bin/python -m p8a_asymptotics.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/reference/asymptotics/tests -q
.venv/bin/ruff check problems/P8/a/applicability/reference/asymptotics
```

The verifier is read-only and pins/replays A.3 and its A.2/A.1 dependencies.
It checks exact conformal/proper-time exponents and constants, a polynomial
two-variable Cauchy benchmark by two independent implementations, coherent
state examples, an outward-rounded state-dependent residual bound, domain
and extra-source exclusion controls, and all source/document/test hashes.
Without `--check`, it prints a candidate report but never writes one.

Arithmetic replay does not prove the general smooth PDE or Hadamard theorems:
those are primary-source inputs plus the written extension argument. The
finite polynomial benchmark is a check, not an analyticity assumption on
arbitrary states. No git or earlier checkpoint files are changed by replay.
