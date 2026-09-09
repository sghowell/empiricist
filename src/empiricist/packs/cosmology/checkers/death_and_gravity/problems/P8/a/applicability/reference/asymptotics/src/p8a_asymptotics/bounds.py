"""Conditional quantitative residual margins from explicit state-jet bounds."""

from dataclasses import dataclass
from fractions import Fraction

import sympy as sp
from p8a_radiation import validated


def rational(value):
    if isinstance(value, float):
        raise TypeError("Use exact rational inputs, not binary floating point")
    try:
        return Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("A finite exact rational input is required") from exc


@dataclass(frozen=True)
class JetBounds:
    """Supplied witness bounds on 0<=eta<=eta_max at a fixed compact set."""

    m0: Fraction
    m1: Fraction
    m2: Fraction
    eta_max: Fraction

    def __post_init__(self):
        for name in ("m0", "m1", "m2", "eta_max"):
            object.__setattr__(self, name, rational(getattr(self, name)))
        if min(self.m0, self.m1, self.m2) < 0 or self.eta_max <= 0:
            raise ValueError("Nonnegative jet bounds and a positive finite domain are required")


@dataclass(frozen=True)
class Couplings:
    a: Fraction
    kappa: Fraction
    b: Fraction
    ell: Fraction
    radiation_c: Fraction
    hbar: Fraction

    def __post_init__(self):
        for name in ("a", "kappa", "b", "ell", "radiation_c", "hbar"):
            object.__setattr__(self, name, rational(getattr(self, name)))
        if min(self.a, self.kappa, self.b, self.hbar) <= 0 or self.radiation_c < 0:
            raise ValueError("Positive a,kappa,b,hbar and nonnegative radiation C are required")


def error_polynomial(jets, couplings, eta):
    return sp.expand(sp.Rational(jets.m0)*eta**2+sp.Rational(jets.m1)*eta**3
                     +sp.Rational(jets.m2+abs(couplings.radiation_c
                         -3*couplings.b*couplings.a**2/couplings.kappa))*eta**4
                     +sp.Rational(abs(couplings.ell)*couplings.a**4/couplings.kappa)*eta**8)


def certify_interval(jets, couplings, cutoff):
    cutoff = rational(cutoff)
    if cutoff <= 0 or cutoff > jets.eta_max:
        raise ValueError("Cutoff must be positive and inside the supplied jet-bound interval")
    error = error_polynomial(jets, couplings, sp.Rational(cutoff))
    leading = sp.Rational(couplings.hbar)/(320*sp.pi**2)
    validated.positive(leading/2-error)
    return {
        "cutoff": str(cutoff),
        "supplied_jet_bounds": {name: str(getattr(jets, name)) for name in ("m0", "m1", "m2", "eta_max")},
        "couplings": {name: str(getattr(couplings, name))
                      for name in ("a", "kappa", "b", "ell", "radiation_c", "hbar")},
        "maximum_error": str(error),
        "residual_lower_bound": str(leading-error),
        "residual_strictly_greater_than_half_leading_coefficient": True,
        "certified_interval": "0 < eta <= cutoff",
        "conditional_on_the_supplied_state_jet_bounds": True,
    }
