"""Outward-rounded all-time regression for the corrected A25 M0 benchmark.

Arb encloses the core. Explicit exponential error lemmas in
notes/s2-benchmarks.md close both infinite tails. Reconstruction uses the
independently derived Sigma, not the inconsistent printed equation (47).
"""

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from functools import cache

from flint import arb, ctx


def ball(q):
    q = Fraction(q)
    return arb(q.numerator)/q.denominator


def enclosure(value):
    """Exact outward dyadic endpoints; pretty Arb strings can hide sign gaps."""
    scale = 2**64
    lower = Fraction(str(value.lower().fmpq()))
    upper = Fraction(str(value.upper().fmpq()))
    # Outward rounding to a fixed dyadic grid keeps evidence small; the
    # underlying transcendental operations still use 160-bit Arb balls.
    lo = lower*scale//1
    hi = -((-upper*scale)//1)
    return [str(Fraction(lo, scale)), str(Fraction(hi, scale))]


@dataclass
class Jet:
    value: arb
    first: arb
    second: arb

    @classmethod
    def constant(cls, q):
        return cls(ball(q), arb(0), arb(0))

    def __add__(self, other):
        o = other if isinstance(other, Jet) else Jet.constant(other)
        return Jet(self.value+o.value, self.first+o.first, self.second+o.second)

    __radd__ = __add__

    def __neg__(self):
        return Jet(-self.value, -self.first, -self.second)

    def __sub__(self, other):
        return self+-other

    def __rsub__(self, other):
        return -self+other

    def __mul__(self, other):
        o = other if isinstance(other, Jet) else Jet.constant(other)
        return Jet(self.value*o.value, self.first*o.value+self.value*o.first,
                   self.second*o.value+2*self.first*o.first+self.value*o.second)

    __rmul__ = __mul__

    def __pow__(self, exponent):
        p = ball(exponent)
        a = self.value**p
        d = p*self.value**(p-1)
        dd = p*(p-1)*self.value**(p-2)
        return Jet(a, d*self.first, dd*self.first**2+d*self.second)

    def __truediv__(self, other):
        o = other if isinstance(other, Jet) else Jet.constant(other)
        return self*o**-1

    def __rtruediv__(self, other):
        return self**-1*other

    def exp(self):
        e = self.value.exp()
        return Jet(e, e*self.first, e*(self.second+self.first**2))

    def tanh(self):
        f = self.value.tanh()
        d = 1-f**2
        return Jet(f, d*self.first, d*self.second-2*f*d*self.first**2)


def evaluate(lo, hi):
    t = Jet(arb(ball((lo+hi)/2), ball((hi-lo)/2)), arb(1), arb(0))
    s = t/10
    D = 1+s**2
    positive, negative = 1/(1+(-s).exp()), 1/(1+s.exp())
    a = positive*D**Fraction(1, 6)+negative*D**Fraction(1, 10)
    H = a.first/a.value
    Hd = a.second/a.value-H**2
    th0, th1 = s.tanh(), (s+Fraction(1, 10)).tanh()
    g = Fraction(2, 3)*(1-th1**2)
    correction = g*(th0-th1)/(5*D)
    theta, theta_dot = H+correction.value, Hd+correction.first
    lam, lam_dot = 1-3*g.value, -3*g.first
    sigma = 1/D.value**2+(1-th0.value)/(2500*D.value)
    P = H*lam*theta+lam_dot*theta-lam*theta_dot-theta**2
    J = sigma+3*theta**2
    return {"a": a.value, "H": H, "Theta": theta, "Theta_dot": theta_dot,
            "Lambda": lam, "Sigma": sigma, "J": J, "P": P, "J_minus_P": J-P}


def tail_checks():
    """Endpoint tests for monotone error ratios from the analytic tail lemma."""
    x = arb(50)
    checks = {
        "positive_P_error_ratio": 8000*x**3*(-x).exp(),
        "subluminal_gap_error_ratio": 16*x**5*(-x).exp(),
        "Theta_sign_error_ratio": 100*x**2*(-x).exp(),
        "a_relative_error_twice": 2*x*(-x).exp(),
        "g_constant_e_point_2_lt_3_over_2": ball(Fraction(2, 3))*ball(Fraction(1, 5)).exp(),
    }
    if not all(0 < value < 1 for value in checks.values()):
        raise ValueError("Analytic tail endpoint bound failed")
    return {key: enclosure(value) for key, value in checks.items()}


@cache
def build():
    with ctx.workprec(160):
        pending = [(Fraction(-500), Fraction(500), 0)]
        tiles = []
        while pending:
            lo, hi, depth = pending.pop()
            r = evaluate(lo, hi)
            principal = all(r[key] > 0 for key in ("a", "J", "P", "J_minus_P"))
            unitary = r["Theta"] > 0 or r["Theta"] < 0
            gamma = r["Lambda"] < 0 and r["Theta_dot"] > 0
            if principal and (unitary or gamma):
                tiles.append({"interval": [str(lo), str(hi)],
                              "chart": "unitary" if unitary else "gamma",
                              "bounds": {key: enclosure(value) for key, value in r.items()}})
            else:
                if depth >= 26:
                    raise ValueError(f"No certified enclosure at {[lo, hi]}: {r}")
                mid = (lo+hi)/2
                pending.extend(((mid, hi, depth+1), (lo, mid, depth+1)))
        # A gamma zero exists and all possible zeros have positive derivative,
        # hence the continuous all-time function has exactly one crossing.
        assert evaluate(Fraction(-500), Fraction(-500))["Theta"] < 0
        assert evaluate(Fraction(500), Fraction(500))["Theta"] > 0
        return {"schema": 1, "precision_bits": 160, "saved_endpoint_grid": "2^-64 (outward)",
                "scope": "Corrected/reconstructed A25 section 3 M0 external regression; not an M1 witness",
                "parameters": {"tau": "10", "epsilon": "5", "w": "2", "u": "1/10"},
                "core": ["-500", "500"], "tiles": tiles,
                "tails": {"absolute_t_lower": "500", "dimensionless_x_lower": "50",
                          "endpoint_checks": tail_checks(),
                          "analytic_lemma": "notes/s2-benchmarks.md, exponential tail estimates"},
                "gamma_count": 1,
                "reconstruction": "F0 and FX from derived background equations; FXX from independently derived Sigma=Sigma_target (50)",
                "source_corrections": ["D: MRV20 (8a)", "Sigma: regressions.py and independent_sigma.py"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
