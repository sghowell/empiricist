"""Rational covariant candidate reconstruction from the derived equations.

These are candidates until domain, regular-chart and tail certificates land.
No finite-time scan is used to select F: its background and principal jets
are solved exactly, then extended as a polynomial in X on an open domain.
"""

from functools import cache

import sympy as sp

from . import coupled
from . import jets as j
from . import quadratic as q

X = sp.Symbol("X", positive=True)
D = 1+j.t**2


def specification(label):
    zero, half = sp.Integer(0), sp.Rational(1, 2)
    if label == "D":
        H = 2*j.t/D
        return {"a": D, "H": H, "F2": -half, "A1": zero, "A3": 4/D**3,
                "K": zero, "matter": False, "Theta_target": H, "Lambda_target": 1-2/D**3}
    if label == "C":
        T = 1-half/D
        H = j.t/(2*D)
        return {"a": D**sp.Rational(1, 4), "H": H,
                "F2": -T/2+3*T*(1-X)/(4*D**2), "A1": zero, "A3": zero,
                "K": zero, "matter": False,
                "Theta_target": j.t*(4*j.t**6+14*j.t**4+10*j.t**2+15)/(8*D**4),
                "Lambda_target": T*(1-3/(2*D**2))}
    if label in ("AC", "BC"):
        # Slower-tail diagnostic models: retained to exercise A1_X/braiding
        # in the derivation, NOT candidates for the canonical-asymptotic gate.
        a = D**sp.Rational(1, 3)
        H = 2*j.t/(3*D)
        if label == "AC":
            f, A1, A3, K = -half+(1-X)/D, (X-1)/(2*D), zero, zero
        else:
            f, A1, A3, K = -half+(1-X)/D, zero, zero, -2*H*(X-1)/D
        return {"a": a, "H": H, "F2": f, "A1": A1, "A3": A3, "K": K,
                "matter": False, "Theta_target": H, "Lambda_target": 1-2/D}
    if label == "CD_matter":
        H = 4*j.t/D
        chi_dot = 1/(10*D**6)
        return {"a": D**2, "H": H, "F2": -half+(1-X)/(2*D**3),
                "A1": zero, "A3": 1/(D**3*X), "K": zero, "matter": True,
                "chi": sp.integrate(chi_dot, j.t), "chi_dot": chi_dot,
                "Theta_target": j.t*(4*D**3-1)/D**4,
                "Lambda_target": 1-3/(2*D**3)}
    raise ValueError(f"Unknown candidate {label}")


def specialize(expr, mapping, spec):
    expr = q.substitute_functions(expr, mapping)
    functions = {j.H: spec["H"], j.a: spec["a"]}
    if spec["matter"]:
        functions[coupled.chi] = spec["chi"]
    return sp.factor(q.substitute_functions(expr, functions))


@cache
def reconstruct(label):
    spec = specification(label)
    zero = sp.Integer(0)
    mapping = q.covariant_N_jets(zero, spec["K"], spec["F2"], spec["A1"], spec["A3"], X)
    for key in q.F:
        mapping.pop(key)
    pure = q.derive()
    GT, FT, Theta, Lambda = (specialize(pure[key], mapping, spec)
                             for key in ("GT", "FT", "Theta", "Lambda"))
    delta = specialize(pure["delta"], mapping, spec)
    if sp.cancel(Theta-spec["Theta_target"]) != 0 or sp.cancel(Lambda-spec["Lambda_target"]) != 0:
        raise RuntimeError("Candidate dictionary differs from the covariantly derived coefficients")
    FS = sp.factor(sp.diff(spec["a"]*GT*Lambda/Theta, j.t)/spec["a"]-FT)
    bg = coupled.background() if spec["matter"] else q.background()
    F0, FN = (specialize(bg["solution"][key], mapping, spec) for key in q.F[:2])
    sigma = coupled.derive()["Sigma_total"] if spec["matter"] else pure["Sigma"]
    sigma_expr = specialize(sigma, mapping, spec)
    # Set the full coupled K11 equal to G11=FS (M0 is the same target).
    target_sigma = sp.factor(Theta**2*(FS-3*GT)/GT**2)
    FNN = sp.solve(sigma_expr-target_sigma, q.F[2])[0]
    FX = -FN/2
    FXX = (FNN+3*FN)/4
    Fexpr = sp.factor(F0+FX*(X-1)+FXX*(X-1)**2/2)
    full_mapping = q.covariant_N_jets(Fexpr, spec["K"], spec["F2"], spec["A1"], spec["A3"], X)
    residuals = {
        "metric_H_definition": sp.factor(sp.diff(spec["a"], j.t)/spec["a"]-spec["H"]),
        "background_lapse": specialize(bg["EN"], full_mapping, spec),
        "background_scale": specialize(bg["Ea"], full_mapping, spec),
        "principal_target": specialize(sigma, full_mapping, spec)-target_sigma,
    }
    if spec["matter"]:
        residuals["matter_equation"] = sp.factor(sp.diff(spec["a"]**3*spec["chi_dot"], j.t))
        residuals["matter_field_definition"] = sp.factor(sp.diff(spec["chi"], j.t)-spec["chi_dot"])
        out = coupled.derive()
        substitution = dict(zip(out["symbols"], (GT, FT, Theta, target_sigma, Lambda,
                             specialize(pure["delta"], mapping, spec), spec["chi_dot"])))
        substitution.update(dict(zip(out["derivative_symbols"],
                                    (spec["H"], sp.diff(GT, j.t), sp.diff(Lambda, j.t), sp.diff(Theta, j.t)))))
        kinetic = out["kinetic"].subs(substitution).applyfunc(sp.factor)
        gradient = out["gradient"].subs(substitution).applyfunc(sp.factor)
        for i in range(2):
            for m in range(2):
                residuals[f"luminal_{i}{m}"] = sp.cancel(kinetic[i, m]-gradient[i, m])
    else:
        kinetic, gradient = sp.Matrix([[FS]]), sp.Matrix([[FS]])
    residuals = {key: sp.cancel(value) for key, value in residuals.items()}
    if any(value != 0 for value in residuals.values()):
        raise RuntimeError(f"Covariant candidate residual: {residuals}")
    return {**spec, "label": label, "F": Fexpr, "F0": F0, "FX": sp.factor(FX),
            "FXX": sp.factor(FXX), "GT": GT, "FT": FT, "Theta": Theta, "Lambda": Lambda, "delta": delta,
            "Sigma_total": target_sigma, "FS": FS, "kinetic": kinetic, "gradient": gradient,
            "residuals": residuals}
