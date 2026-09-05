"""P3 deterministic tier: numerical optimisation of Bell-measurement schemes.

The P5 lesson, applied to P3: do not ask the model to do what a deterministic
search does better. This module maps the (k, m) landscape of ancilla-boosted
linear-optical Bell measurements for BOTH metrics -- the problem's `p_min` and
the literature's `p_avg` -- with no model spend, and hands exact-looking optima
to the exact verifier (`domain/p3/exact.py`) so they can enter the ledger as
CERTIFIED witnesses. Nothing here is trusted: every reported number is
re-derived by `verify_scheme_agreed` (both float engines) before it is shown,
and float results ingest at HEURISTIC exactly like model-found schemes.

Parametrisation. A universal Clements-style rectangular mesh
(`MeshTopology.universal(m)`: m layers of nearest-neighbour 50:50-capable
beamsplitters, (theta, phi) per element -- output phases are irrelevant to
photon-number detection and are omitted) plus a k-photon ancilla amplitude
vector over `patterns(k, m-4)` (real/imag pairs, normalised on evaluation).

Objective. With `P[s, B] = Pr[s | B]` over the n-photon output patterns s,
`w(s) = argmax_B P[s, B]` and the relative leak `r(s) = (sum_B P[s,B] - max_B
P[s,B]) / max_B P[s,B]`, the gate `g(s) = exp(-r(s) / tau)` down-weights
ambiguous patterns, and `S_B = sum_{s : w(s) = B} P[s, B] g(s)` is a smooth
stand-in for the assignment-derived success of B. `p_avg` maximises `mean_B
S_B`; `p_min` maximises the soft minimum `-tau log sum_B exp(-S_B / tau)`. As
tau -> 0 the surrogate converges to the exact assignment metric (a leakage-free
scheme scores EXACTLY its metric at every tau). The optimiser anneals tau over
a schedule, warm-starting each stage.

Exact lift. The structure of an optimum lives in the overall unitary, not in
individual mesh angles (a universal mesh has gauge freedom). So after
optimisation the photon-carrying columns are gauge-fixed (row phases, one phase
per dual-rail qubit, the ancilla column) onto the pi/12 phase lattice, each
entry is snapped to sqrt(rational) * exp(i k pi/12), and the result must be an
EXACT isometry whose exact success vector reproduces the engines' float vector.
That `ExactWitness` is what `P3ExactVerifier` certifies (`to_exact_witness`).
"""
from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass
from math import pi

import numpy as np
from blake3 import blake3
from scipy.optimize import minimize
from scipy.special import logsumexp

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Run

from .exact import (
    ONE,
    ExactReport,
    ExactUnsupported,
    ExactWitness,
    exact_distributions,
    exact_report,
    snap_isometry,
    witness_to_json,
)
from .fock import factorial_prod, patterns
from .interferometer import Mesh, mesh_unitary
from .scheme import BELL_LABELS, BellScheme, SchemeReport
from .verify import verify_scheme_agreed

# ---------------------------------------------------------------------------
# Parametrisation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeshTopology:
    """An ordered list of beamsplitter (i, j) pairs; each carries (theta, phi)."""

    n_modes: int
    pairs: tuple[tuple[int, int], ...]

    @staticmethod
    def universal(m: int) -> MeshTopology:
        """Clements-style rectangular mesh: m layers of nearest-neighbour pairs,
        alternating offsets -- universal for U(m) up to output phases."""
        if m < 2:
            raise ValueError("a mesh needs at least two modes")
        pairs: list[tuple[int, int]] = []
        for layer in range(m):
            for i in range(layer % 2, m - 1, 2):
                pairs.append((i, i + 1))
        return MeshTopology(n_modes=m, pairs=tuple(pairs))

    @property
    def n_mesh_params(self) -> int:
        return 2 * len(self.pairs)


def ancilla_basis(k: int, m: int) -> tuple[tuple[int, ...], ...]:
    """The k-photon Fock patterns on the m-4 ancilla modes (empty tuple for m=4)."""
    if m < 4:
        raise ValueError("a Bell scheme needs at least the 4 dual-rail modes")
    return patterns(k, m - 4)


def n_params(k: int, m: int, topo: MeshTopology) -> int:
    n_anc = len(ancilla_basis(k, m)) if k > 0 else 0
    return topo.n_mesh_params + 2 * n_anc


def unitary_from_params(topo: MeshTopology, x: np.ndarray) -> np.ndarray:
    """The mode unitary, composed IN ORDER with interferometer.py's convention
    bs(i, j, theta, phi): a_i -> cos a_i + e^{i phi} sin a_j and
    a_j -> -e^{-i phi} sin a_i + cos a_j."""
    m = topo.n_modes
    u = np.eye(m, dtype=np.complex128)
    for e, (i, j) in enumerate(topo.pairs):
        theta, phi = float(x[2 * e]), float(x[2 * e + 1])
        c, s = math.cos(theta), math.sin(theta)
        g = np.eye(m, dtype=np.complex128)
        g[i, i] = c
        g[j, i] = np.exp(1j * phi) * s
        g[i, j] = -np.exp(-1j * phi) * s
        g[j, j] = c
        u = g @ u
    return u


def ancilla_from_params(k: int, m: int, topo: MeshTopology, x: np.ndarray) -> np.ndarray:
    """Normalised complex ancilla amplitude vector over `ancilla_basis(k, m)`."""
    basis = ancilla_basis(k, m)
    if k == 0:
        return np.ones(len(basis), dtype=np.complex128)  # the vacuum pattern, amplitude 1
    raw = np.asarray(x[topo.n_mesh_params:], dtype=float)
    vec = raw[0::2] + 1j * raw[1::2]
    norm = np.linalg.norm(vec)
    if norm < 1e-12:
        vec = np.zeros(len(basis), dtype=np.complex128)
        vec[0] = 1.0
        return vec
    return vec / norm


def params_to_scheme(k: int, m: int, x: np.ndarray, topo: MeshTopology) -> BellScheme:
    x = np.asarray(x, dtype=float)
    if x.shape != (n_params(k, m, topo),):
        raise ValueError(f"expected {n_params(k, m, topo)} parameters, got {x.shape}")
    elements = tuple(
        ("bs", i, j, float(x[2 * e]), float(x[2 * e + 1]))
        for e, (i, j) in enumerate(topo.pairs)
    )
    basis = ancilla_basis(k, m)
    anc = ancilla_from_params(k, m, topo, x)
    ancilla = {basis[t]: complex(anc[t]) for t in range(len(basis)) if abs(anc[t]) > 0.0}
    if m == 4:
        ancilla = {}
    return BellScheme(n_modes=m, n_ancilla_photons=k, ancilla=ancilla,
                      mesh=Mesh(n_modes=m, elements=elements))


def scheme_to_json(scheme: BellScheme) -> dict:
    """The `BellSchemeOut`-shaped dict the campaign ingests (screen -> verify)."""
    return {
        "n_modes": scheme.n_modes,
        "n_ancilla_photons": scheme.n_ancilla_photons,
        "ancilla": [
            {"pattern": list(p), "re": float(complex(a).real), "im": float(complex(a).imag)}
            for p, a in sorted(scheme.ancilla.items())
        ],
        "mesh": [
            {"kind": el[0], "i": int(el[1]), "j": int(el[2]) if el[0] == "bs" else 0,
             "theta": float(el[3]) if el[0] == "bs" else float(el[2]),
             "phi": float(el[4]) if el[0] == "bs" else 0.0}
            for el in scheme.mesh.elements
        ],
    }


# ---------------------------------------------------------------------------
# Fast evaluation (numpy, batched Ryser)
# ---------------------------------------------------------------------------


def batched_permanents(mats: np.ndarray) -> np.ndarray:
    """Ryser's formula over a batch: (N, n, n) -> (N,)."""
    mats = np.asarray(mats)
    n_batch, n, _ = mats.shape
    if n == 0:
        return np.ones(n_batch, dtype=np.complex128)
    total = np.zeros(n_batch, dtype=np.complex128)
    for mask in range(1, 1 << n):
        cols = [j for j in range(n) if (mask >> j) & 1]
        col_sum = mats[:, :, cols].sum(axis=2)
        total += ((-1) ** len(cols)) * np.prod(col_sum, axis=1)
    return ((-1) ** n) * total


_BELL4: dict[str, tuple[tuple[tuple[int, int, int, int], float], ...]] = {
    "phi+": (((1, 0, 1, 0), 1.0), ((0, 1, 0, 1), 1.0)),
    "phi-": (((1, 0, 1, 0), 1.0), ((0, 1, 0, 1), -1.0)),
    "psi+": (((1, 0, 0, 1), 1.0), ((0, 1, 1, 0), 1.0)),
    "psi-": (((1, 0, 0, 1), 1.0), ((0, 1, 1, 0), -1.0)),
}


class FastEvaluator:
    """Output-pattern probabilities for the four Bell inputs, vectorised.

    `probabilities(U, anc)` returns P of shape (n_patterns, 4) in the order
    `patterns(k+2, m)` x BELL_LABELS -- the same numbers `PermanentEngine`
    computes one permanent at a time (pinned to 1e-10 by tests)."""

    def __init__(self, k: int, m: int) -> None:
        self.k, self.m = k, m
        self.n_photons = k + 2
        self.out_patterns = patterns(self.n_photons, m)
        self.rows = np.array(
            [[i for i, si in enumerate(s) for _ in range(si)] for s in self.out_patterns],
            dtype=int,
        )  # (N, n)
        self.out_norm = np.array(
            [1.0 / math.sqrt(factorial_prod(s)) for s in self.out_patterns], dtype=float
        )
        self.anc_basis = ancilla_basis(k, m)
        # Per ancilla basis pattern: its column indices and 1/sqrt(prod t!).
        self.anc_cols = [
            [4 + j for j, tj in enumerate(p) for _ in range(tj)] for p in self.anc_basis
        ]
        self.anc_norm = np.array(
            [1.0 / math.sqrt(factorial_prod(p)) for p in self.anc_basis], dtype=float
        )

    def probabilities(self, unitary: np.ndarray, ancilla: np.ndarray) -> np.ndarray:
        r = 1.0 / math.sqrt(2.0)
        rows = self.rows
        out = np.zeros((len(self.out_patterns), 4), dtype=float)
        for b, label in enumerate(BELL_LABELS):
            amp = np.zeros(len(self.out_patterns), dtype=np.complex128)
            for bell_pat, sign in _BELL4[label]:
                bell_cols = [j for j, tj in enumerate(bell_pat) for _ in range(tj)]
                for t, anc_cols in enumerate(self.anc_cols):
                    coeff = sign * r * ancilla[t] * self.anc_norm[t]
                    if coeff == 0:
                        continue
                    cols = np.array(bell_cols + anc_cols, dtype=int)
                    sub = unitary[rows[:, :, None], cols[None, None, :]]
                    amp += coeff * batched_permanents(sub)
            amp *= self.out_norm
            out[:, b] = np.abs(amp) ** 2
        return out


# ---------------------------------------------------------------------------
# Surrogate objective
# ---------------------------------------------------------------------------


def gated_success(P: np.ndarray, *, tau: float) -> np.ndarray:
    """S_B = sum_{s: w(s)=B} P[s,B] * exp(-r(s)/tau): the smooth stand-in for the
    assignment-derived success of each Bell state (see the module docstring)."""
    P = np.asarray(P, dtype=float)
    max_b = P.max(axis=1)
    winner = P.argmax(axis=1)
    live = max_b > 1e-300
    leak = P.sum(axis=1) - max_b
    r = np.zeros_like(max_b)
    r[live] = leak[live] / max_b[live]
    gate = np.exp(-r / tau)
    return np.bincount(winner[live], weights=(max_b * gate)[live], minlength=4)[:4]


_LOG_EPS = 1e-3
TARGETS = ("p_min", "p_avg", "p_low2", "p_sum_all4")


def metric_of(report: SchemeReport, target: str) -> float:
    """The assignment-derived value of `target` for a (float) scheme report."""
    v = sorted(report.success_by_state.values())
    if target == "p_min":
        return report.p_min
    if target == "p_avg":
        return report.p_avg
    if target == "p_low2":
        return v[0] + v[1]
    if target == "p_sum_all4":
        return sum(v) if v[0] > 0 else 0.0
    raise ValueError(f"target must be one of {TARGETS}")


def exact_metric_of(exact: ExactReport, target: str) -> float:
    vals = sorted(x.to_float() for x in exact.success.values())
    if target == "p_min":
        return exact.p_min.to_float()
    if target == "p_avg":
        return exact.p_avg.to_float()
    if target == "p_low2":
        return vals[0] + vals[1]
    if target == "p_sum_all4":
        return sum(vals) if exact.all_identified else 0.0
    raise ValueError(f"target must be one of {TARGETS}")


def surrogate(P: np.ndarray, *, target: str, tau: float, shaping: str = "final") -> float:
    """Higher is better.

    `p_avg`: mean_B S_B. `p_min`: with `shaping="log"` the balanced product
    objective mean_B log(S_B + eps) -- a Bell state that is never identified
    costs log(eps), so the gradient always pushes the WORST state up (the plain
    soft-minimum is flat at 0 whenever some state is unidentified, which is
    exactly where a random start sits); with `shaping="final"` the soft minimum
    -tau log sum_B exp(-S_B/tau), which converges to min_B S_B as tau -> 0.
    A leakage-free scheme scores exactly its metric under the final shaping.
    """
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    s = gated_success(P, tau=tau)
    if target == "p_avg":
        return float(s.mean())
    if target == "p_sum_all4":
        # total success, but only schemes identifying ALL FOUR states count:
        # the log-product term is -inf-like when any S_B is ~0 (log shaping) and
        # a small tie-breaker under the final shaping.
        if shaping == "log":
            return float(np.mean(np.log(s + _LOG_EPS)) + s.sum())
        return float(s.sum() + 1e-3 * np.mean(np.log(s + _LOG_EPS)))
    if target == "p_low2":
        # the sum of the two smallest successes (the strategist's frontier
        # conjecture p(1) + p(2) <= 1/2): soft-minimum over the six pairs.
        pairs = np.array([s[a] + s[b] for a in range(4) for b in range(a + 1, 4)])
        if shaping == "log":
            return float(np.mean(np.log(s + _LOG_EPS)))
        return float(-tau * logsumexp(-pairs / tau))
    if shaping == "log":
        return float(np.mean(np.log(s + _LOG_EPS)))
    return float(-tau * logsumexp(-s / tau))


# ---------------------------------------------------------------------------
# Lifting an optimum to an exact witness: gauge fix, then snap the isometry
# ---------------------------------------------------------------------------


def absorb_single_photon_ancilla(
    unitary: np.ndarray, ancilla: np.ndarray, k: int
) -> tuple[np.ndarray, np.ndarray]:
    """For k = 1 the ancilla superposition sum_a c_a |1_a> is ONE effective input
    column w = sum_a c_a U[:, 4+a]; the scheme is then the 5-column isometry
    [U[:, :4], w] with ancilla |1> in its fifth input mode. Other k: unchanged."""
    if k != 1:
        return unitary, ancilla
    # `ancilla[t]` is the amplitude of `ancilla_basis(1, m)[t]`, a LEXICOGRAPHIC
    # single-photon pattern over the m-4 ancilla modes -- index 0 is the photon in
    # the LAST ancilla mode, so map each pattern to its mode explicitly.
    m = unitary.shape[0]
    basis = ancilla_basis(1, m)
    w = np.zeros(m, dtype=np.complex128)
    for t, pat in enumerate(basis):
        w += ancilla[t] * unitary[:, 4 + pat.index(1)]
    return np.concatenate([unitary[:, :4], w[:, None]], axis=1), np.array([1.0 + 0j])


def gauge_fix_to_lattice(
    v: np.ndarray,
    column_groups: list[list[int]],
    *,
    lattice: int = 24,
    restarts: int = 40,
    seed: int = 0,
) -> np.ndarray:
    """Multiply each ROW by a phase (output phases are free) and each column
    GROUP by a common phase (a global phase per dual-rail qubit and per ancilla
    column is free) to put every entry's phase on the 2 pi / lattice grid, if a
    gauge exists. Minimises sum |v_ij|^2 (1 - cos(lattice * arg)) by L-BFGS-B
    from random starts; returns the best gauge-fixed matrix (not necessarily
    on-lattice -- the exact snap decides)."""
    m, n = v.shape
    w = np.abs(v) ** 2
    ang = np.angle(v)
    g_of_col = np.zeros(n, dtype=int)
    for gi, cols in enumerate(column_groups):
        for c in cols:
            g_of_col[c] = gi
    n_groups = len(column_groups)
    rng = np.random.default_rng(seed)

    def phased_angles(x: np.ndarray) -> np.ndarray:
        rho, gam = x[:m], x[m:]
        return ang + rho[:, None] + gam[g_of_col][None, :]

    def cost(x: np.ndarray) -> float:
        return float(np.sum(w * (1.0 - np.cos(lattice * phased_angles(x)))))

    best_x, best_c = np.zeros(m + n_groups), cost(np.zeros(m + n_groups))
    for _ in range(restarts):
        x0 = rng.uniform(0, 2 * pi, size=m + n_groups)
        res = minimize(cost, x0, method="L-BFGS-B")
        if res.fun < best_c:
            best_x, best_c = res.x, float(res.fun)
    rho, gam = best_x[:m], best_x[m:]
    return v * np.exp(1j * rho)[:, None] * np.exp(1j * gam[g_of_col])[None, :]


def to_exact_witness(
    scheme: BellScheme, *, max_denom: int = 64, tol: float = 1e-6, seed: int = 0
) -> ExactWitness | None:
    """Try to lift a float scheme to an exact witness.

    Route A: the mesh itself is on the pi/12 lattice with in-field ancilla
    amplitudes (`ExactWitness.from_mesh`). Route B (k <= 1): absorb a single
    ancilla photon into one column, gauge-fix rows / qubit pairs / the ancilla
    column onto the lattice, snap every entry to sqrt(rational) * exp(i k pi/12)
    and require an EXACT isometry. None when neither route lands.
    """
    try:
        return ExactWitness.from_mesh(scheme, max_denom=max_denom)
    except (ExactUnsupported, ValueError):
        pass
    k, m = scheme.n_ancilla_photons, scheme.n_modes
    if k > 1:
        return None
    u = mesh_unitary(scheme.mesh)
    basis = ancilla_basis(k, m)
    anc = np.array([scheme.ancilla.get(p, 0.0) for p in basis], dtype=np.complex128)
    if k == 0:
        v, groups = u[:, :4], [[0, 1], [2, 3]]
    else:
        v, _ = absorb_single_photon_ancilla(u, anc, k)
        groups = [[0, 1], [2, 3], [4]]
    v = gauge_fix_to_lattice(v, groups, seed=seed)
    try:
        iso = snap_isometry([list(row) for row in v], max_denom=max_denom, tol=tol)
        witness = ExactWitness(
            n_modes=m, n_ancilla_photons=k,
            isometry=tuple(tuple(row) for row in iso),
            ancilla={(1,): ONE} if k == 1 else {},
        )
        witness.validate()
    except (ExactUnsupported, ValueError):
        return None
    return witness


# ---------------------------------------------------------------------------
# The optimiser
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OptResult:
    restart: int
    objective: float                   # final surrogate value (search-side number)
    scheme_json: dict
    report: SchemeReport               # two-engine consensus report (float)
    witness_json: dict | None          # exact witness lifted from the optimum, if any
    exact: ExactReport | None          # its exact report (reproduces `report` to 1e-6)
    run_id: str | None = None          # the OPTIMIZE `runs` row this result came from

    def metric(self, target: str) -> float:
        if self.exact is not None:
            return exact_metric_of(self.exact, target)
        return metric_of(self.report, target)


def _agreed_report(scheme: BellScheme) -> SchemeReport | None:
    """Two-engine consensus report, or None for a screened/invalid scheme.
    An engine DISAGREEMENT is the F3 alarm and raises."""
    res = verify_scheme_agreed(scheme)
    if res.verdict == "ERROR":
        raise RuntimeError(f"F3 alarm during optimisation: {res.detail}")
    if res.report is None:
        return None
    return res.report


def lift_reproduces(witness: ExactWitness, report: SchemeReport, tol: float = 1e-6) -> bool:
    """The exact witness must reproduce the engines' FULL per-pattern
    distributions (not just the four success values): a lift that lands on a
    different scheme with a coincidentally equal vector is rejected."""
    exact = exact_distributions(witness)
    for b in BELL_LABELS:
        float_dist = report.distributions[b]
        for key in set(float_dist) | set(exact[b]):
            ex = exact[b].get(key)
            ev = 0.0 if ex is None else ex.to_float()
            if abs(ev - float_dist.get(key, 0.0)) > tol:
                return False
    return True


def _config_hash(cfg: dict) -> str:
    return blake3(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def optimize_scheme(
    k: int,
    m: int,
    *,
    target: str,
    restarts: int = 20,
    seed: int = 0,
    max_iter: int = 300,
    ledger: Ledger | None = None,
    tau_schedule: tuple[float, ...] = (0.3, 0.1, 0.03, 0.01),
    topology: MeshTopology | None = None,
) -> list[OptResult]:
    """Random-restart L-BFGS-B over the surrogate, annealed in tau; results are
    sorted best-first by the ENGINE-VERIFIED metric (snapped when kept). With a
    ledger, one `runs` row (move OPTIMIZE) records seed/config/wall time."""
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    if restarts < 1:
        raise ValueError("restarts must be >= 1")
    topo = topology if topology is not None else MeshTopology.universal(m)
    ev = FastEvaluator(k, m)
    rng = np.random.default_rng(seed)
    dim = n_params(k, m, topo)
    n_mesh = topo.n_mesh_params
    cfg = {"k": k, "m": m, "target": target, "restarts": restarts, "seed": seed,
           "max_iter": max_iter, "tau_schedule": list(tau_schedule),
           "topology": [list(p) for p in topo.pairs]}
    run_id = f"p3opt-k{k}-m{m}-{target}-s{seed}-{uuid.uuid4().hex[:8]}"
    started = time.monotonic()
    if ledger is not None:
        ledger.start_run(Run(run_id=run_id, move="OPTIMIZE", seed=seed,
                             config_hash=_config_hash(cfg)))
    results: list[OptResult] = []
    exit_code = 1  # anything but a normal completion below is recorded as a failure
    try:
        for restart in range(restarts):
            x = np.concatenate([
                rng.uniform(0.0, 2.0 * pi, size=n_mesh),
                rng.normal(size=dim - n_mesh),
            ])

            def neg_obj(v: np.ndarray, tau: float, shaping: str) -> float:
                u = unitary_from_params(topo, v)
                anc = ancilla_from_params(k, m, topo, v)
                return -surrogate(ev.probabilities(u, anc), target=target, tau=tau,
                                  shaping=shaping)

            # Annealed stages under the balanced ("log") shaping, then one
            # polishing stage under the final shaping at the smallest tau.
            stages = [(tau, "log") for tau in tau_schedule] + [(tau_schedule[-1], "final")]
            for tau, shaping in stages:
                res = minimize(neg_obj, x, args=(tau, shaping), method="L-BFGS-B",
                               options={"maxiter": max_iter})
                x = res.x
            objective = -neg_obj(x, tau_schedule[-1], "final")
            scheme = params_to_scheme(k, m, x, topo)
            report = _agreed_report(scheme)
            if report is None:
                continue
            witness_json = exact = None
            witness = to_exact_witness(scheme, seed=seed + restart)
            if witness is not None and lift_reproduces(witness, report):
                witness_json, exact = witness_to_json(witness), exact_report(witness)
            results.append(OptResult(
                restart=restart, objective=float(objective),
                scheme_json=scheme_to_json(scheme), report=report,
                witness_json=witness_json, exact=exact,
                run_id=run_id if ledger is not None else None,
            ))
        exit_code = 0
    finally:
        if ledger is not None:
            ledger.finish_run(run_id, exit_code=exit_code, wall_s=time.monotonic() - started)
    # Best metric first; among equals, prefer a result that lifted to an exact
    # witness (the certifiable object) and then the lower restart index.
    results.sort(key=lambda r: (-r.metric(target), r.exact is None, r.restart))
    return results
