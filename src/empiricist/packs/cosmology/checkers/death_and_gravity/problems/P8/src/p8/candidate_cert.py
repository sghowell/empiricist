"""All-time algebra/sign/domain/tail certificates for the selected candidates."""

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import sympy as sp

from . import gamma, rational_candidates, signs
from . import jets as j
from .matter import ia_completion


def build(label):
    if label not in ("C", "D", "CD_matter"):
        raise ValueError("This is not a frozen promotion candidate")
    r = rational_candidates.reconstruct(label)
    T, theta, lam = r["GT"], r["Theta"], r["Lambda"]
    X, D = rational_candidates.X, rational_candidates.D
    support = "".join(flag for flag, value in (
        ("A", r["A1"]), ("B", sp.diff(r["K"], X)),
        ("C", sp.diff(r["F2"], X)), ("D", r["A3"])) if sp.cancel(value) != 0)
    expected_support = "CD" if label == "CD_matter" else label
    if support != expected_support or r["A1"] != 0 or sp.cancel(T-r["FT"]) != 0:
        raise ValueError("Frozen support/tensor-domain hypothesis failed")
    velocity = r["chi_dot"] if r["matter"] else sp.Integer(0)
    w = velocity*(3*r["delta"]-1)
    J0 = sp.factor(r["Sigma_total"]+3*theta**2/T)
    J = sp.factor(J0-w**2/2)
    chart = gamma.principal_chart()
    substitution = dict(zip(chart["symbols"], (T, r["FT"], theta, lam, w, velocity, J)))
    substitution.update(dict(zip(chart["derivative_symbols"],
                                (r["H"], sp.diff(T, j.t), sp.diff(lam, j.t), sp.diff(theta, j.t)))))
    K = chart["kinetic"].subs(substitution).applyfunc(sp.factor)
    G = chart["gradient"].subs(substitution).applyfunc(sp.factor)
    if not r["matter"]:
        K, G = K[:1, :1], G[:1, :1]
    if any(sp.cancel(value) != 0 for value in K-G):
        raise RuntimeError("Regular chart is not exactly luminal")
    sign_certificates = {
        "tensor_margin_GT_gt_1_over_4": signs.even_rational_positive(T-sp.Rational(1, 4), j.t),
        "unique_simple_gamma_Theta_over_t": signs.even_rational_positive(theta/j.t, j.t),
        "unitary_K11": signs.even_rational_positive(r["kinetic"][0, 0], j.t, punctured=True),
        "unitary_detK": signs.even_rational_positive(r["kinetic"].det(), j.t, punctured=True),
        "Hamiltonian_J": signs.even_rational_positive(J, j.t),
        "gamma_Lambda_negative": signs.even_rational_positive(-lam, j.t, upper=Fraction(1, 16)),
        "gamma_K11": signs.even_rational_positive(K[0, 0], j.t, upper=Fraction(1, 16)),
        "gamma_detK": signs.even_rational_positive(K.det(), j.t, upper=Fraction(1, 16)),
    }
    if r["matter"]:
        sign_certificates["matter_rolls_at_all_finite_times"] = signs.even_rational_positive(velocity, j.t)
    # All explicit time coefficients are pole-free; the X-domain is checked
    # below by the uniform Bernstein tail/domain proof for the Ia completion.
    domain_certificates = {key: signs.denominator_regular(r[key], j.t)
                           for key in ("F0", "FX", "FXX", "delta", "H", "Theta", "Lambda")}
    _, A4, A5 = ia_completion(r["F2"], sp.diff(r["F2"], X), r["A1"], r["A3"], X)
    p = sp.limit(j.t*r["H"], j.t, sp.oo)
    if p < sp.Rational(1, 2) or sp.simplify(r["a"]-D**(p/2)) != 0:
        raise ValueError("The positive-power scale-factor/normalization lemma does not apply")
    if r["H"].subs(j.t, 0) != 0 or sp.diff(r["H"], j.t).subs(j.t, 0) <= 0:
        raise ValueError("The designated point is not a bounce")
    # varphi=sqrt(2p)*asinh(phi). Every factor dphi/dvarphi and its second
    # derivative is bounded by sqrt(D) for these p>=1/2. These weighted Ai
    # bounds thus control every operator induced by this field redefinition.
    tails = {
        "curvature_coupling_to_GR": r["F2"]+sp.Rational(1, 2),
        "normalized_X_R_coefficient": D*sp.diff(r["F2"], X)/(2*p),
        "canonical_kinetic_error": D*(r["FX"]-r["FXX"])/(2*p)-sp.Rational(1, 2),
        "noncanonical_X_squared": D**2*r["FXX"]/(8*p**2),
        "potential_term": r["F0"]-r["FX"]+r["FXX"]/2,
        "weighted_A3": D**2*r["A3"], "weighted_A4": D**2*A4, "weighted_A5": D**3*A5,
        "H_squared": r["H"]**2, "H_dot": sp.diff(r["H"], j.t),
    }
    tail_certificates = {key: signs.rational_tail_bound(expr, j.t, X) for key, expr in tails.items()}
    derivative_certificates = {}
    for key, expr in tails.items():
        # d/dvarphi=sqrt(D/(2p))*d/dphi at fixed clock X. Squaring the
        # first derivative keeps the verifier in its even-rational domain.
        variations = {
            "canonical_phi_first_squared": D*sp.diff(expr, j.t)**2/(2*p),
            "canonical_phi_second": (D*sp.diff(expr, j.t, 2)+j.t*sp.diff(expr, j.t))/(2*p),
            "canonical_phi_X_mixed_squared": D*sp.diff(expr, j.t, X)**2/(2*p),
            "X_first": sp.diff(expr, X), "X_second": sp.diff(expr, X, 2),
        }
        derivative_certificates[key] = {name: signs.rational_tail_bound(value, j.t, X)
                                       for name, value in variations.items()}
    # Tensor-domain inequalities on the whole covariant tube, not just X=1.
    u, z = sp.symbols("u z", real=True)
    t2 = sp.Symbol("t2")
    f2_domain = r["F2"].subs(j.t**2, t2).subs(t2, (1-u)/u).subs(X, sp.Rational(9, 10)+z/5)
    num, den = sp.fraction(sp.cancel(-f2_domain))
    numerator_bound, denominator_bound = (signs.bernstein_bounds(e, (u, z)) for e in (num, den))
    if Fraction(numerator_bound["lower"]) <= 0 or Fraction(denominator_bound["lower"]) <= 0:
        raise RuntimeError("Covariant F2 domain bound needs refinement")
    source_names = ("adm.py", "covariant.py", "jets.py", "quadratic.py", "coupled.py", "tensor.py",
                    "gamma.py", "tilted_hessian.py", "matter.py", "rational_candidates.py", "signs.py", "candidate_cert.py")
    folder = Path(__file__).resolve().parent
    return {
        "schema": 1, "candidate": label, "minimal_covariant_support": support,
        "scope": "All-time background, linear principal stability/subluminality, regular gamma chart, covariant tube and canonical tails; not UV/strong-coupling/nonlinear stability",
        "covariant_domain": {"phi": "R", "X": ["9/10", "11/10"],
                             "minus_F2_numerator": numerator_bound, "minus_F2_denominator": denominator_bound},
        "covariant_functions": {key: str(r[key]) for key in ("F", "F2", "A1", "A3", "K")},
        "background": {"a": str(r["a"]), "H": str(r["H"]), "phi": "t", "tail_power": str(p),
                       "a_lower_bound": "1", "Hdot_at_bounce": str(sp.diff(r["H"], j.t).subs(j.t, 0)),
                       "chi_dot": str(velocity)},
        "exact_background_and_principal_residuals": {key: str(value) for key, value in r["residuals"].items()},
        "coverage": {"core": ["-2", "2"], "tails": ["(-infinity,-2]", "[2,+infinity)"],
                     "unitary_chart": "|t| >= 1/8", "regular_gamma_chart": "|t| <= 1/4",
                     "global_signs": "exact even-rational Sturm proofs cover both tails and the core simultaneously"},
        "principal": {"GT": str(T), "FT": str(r["FT"]), "Theta": str(theta), "Lambda": str(lam),
                      "K": str(r["kinetic"]), "G": str(r["gradient"]),
                      "K_gamma": str(K), "G_gamma": str(G), "J": str(J)},
        "sign_certificates": sign_certificates, "time_domain_certificates": domain_certificates,
        "tail_certificates": tail_certificates,
        "canonical_kinetic_ge_1_over_4_when_d_ge": str(max(Fraction(1), 4*Fraction(tail_certificates["canonical_kinetic_error"]["bound"]))),
        "tail_derivative_certificates": derivative_certificates,
        "analytic_lemmas_required": ["Sturm root count and positive sample imply strict positivity",
                                     "Bernstein convex-hull enclosure bounds the entire compactified tube",
                                     "smooth Hamiltonian with nondegenerate symplectic form gives regular finite-k continuation",
                                     "a>=1 on R implies physical causal geodesic completeness",
                                     "a>=1 and FT>1/4 imply both tensor integrals diverge",
                                     "canonical field-redefinition expansion in notes/s2-rational-witnesses.md"],
        "source_sha256": {name: hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in source_names},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", choices=("C", "D", "CD_matter"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build(args.candidate)
    if args.check:
        path = Path(__file__).resolve().parents[2]/"certificates"/f"witness-{args.candidate}.json"
        if json.loads(path.read_text()) != report:
            raise ValueError("Witness certificate differs from exact replay")
        print(f"{args.candidate}: all-time certificate replay passed")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
