# A.6: actual prepared-state linear response

This checkpoint derives the renormalized retarded Wick-square and stress
response on A.5's perturbed radiation family, including the subtraction
length, finite curvature freedom and prepared-state integration constant.
It proves conservative numerical derivative bounds for a specified smooth
cutoff. These are first derivatives at zero amplitude, not finite-amplitude
RSET error estimates. A compact-slab second-order correction gives only a
qualitative `O(epsilon³)` actual Einstein residual.

See [FORMULATION.md](FORMULATION.md), [the proof](notes/proof.md) and
[the primary-source dictionary](notes/sources.md). A.5 and earlier files are
immutable dependencies. P8(a)'s full SEE/QSEI/focusing completion remains open.

From the repository root:

```sh
PYTHONPATH=problems/P8/a/src:problems/P8/a/applicability/src:problems/P8/a/applicability/reference/src:problems/P8/a/applicability/reference/asymptotics/src:problems/P8/a/applicability/reference/asymptotics/backreaction/src:problems/P8/a/applicability/reference/asymptotics/backreaction/response/src .venv/bin/python -m p8a_response.verify --check
.venv/bin/python -m pytest problems/P8/a/applicability/reference/asymptotics/backreaction/response/tests -q
```

Without `--check`, the verifier prints JSON to stdout; it never writes a
report. `certificates/radiation-response.json` pins this subtree's sources,
tests and notes, with independent Fraction-only replay of the switch bounds.
