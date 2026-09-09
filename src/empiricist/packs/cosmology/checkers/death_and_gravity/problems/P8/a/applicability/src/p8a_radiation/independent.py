"""Independent exact Laurent integration in proper and conformal time (FLINT)."""

from fractions import Fraction

from flint import fmpq


def clean(poly):
    return {Fraction(power): fmpq(coefficient) for power, coefficient in poly.items() if coefficient}


def add(*polys):
    out = {}
    for poly in polys:
        for power, coefficient in poly.items():
            out[power] = out.get(power, fmpq(0))+coefficient
    return clean(out)


def scaled(poly, factor):
    return clean({power: coefficient*fmpq(factor) for power, coefficient in poly.items()})


def shifted(poly, power):
    return clean({old+Fraction(power): coefficient for old, coefficient in poly.items()})


def mul(left, right):
    out = {}
    for lp, lc in left.items():
        for rp, rc in right.items():
            out[lp+rp] = out.get(lp+rp, fmpq(0))+lc*rc
    return clean(out)


def derivative(poly):
    return clean({power-1: coefficient*fmpq(power.numerator, power.denominator)
                  for power, coefficient in poly.items() if power})


def evaluate_one(poly):
    return sum(poly.values(), fmpq(0))


def evaluate_two(poly):
    if any(power.denominator != 1 for power in poly):
        raise ValueError("Integer Laurent powers required")
    return sum((coefficient*fmpq(2)**int(power) for power, coefficient in poly.items()), fmpq(0))


def integral(poly, *, conformal=False):
    """Return rational and log(2) coefficients on [1,2] or [1,sqrt(2)]."""
    rational, logarithm = fmpq(0), fmpq(0)
    for power, coefficient in poly.items():
        if power == -1:
            logarithm += coefficient/(2 if conformal else 1)
            continue
        exponent = (power+1)/(2 if conformal else 1)
        if exponent.denominator != 1:
            raise ValueError("Frozen intervals require integer powers of two at endpoints")
        divisor = fmpq((power+1).numerator, (power+1).denominator)
        rational += coefficient*(fmpq(2)**int(exponent)-1)/divisor
    return [rational, logarithm]


def replay(coefficients=(4, -12, 13, -6, 1)):
    h = clean(dict(enumerate(coefficients)))
    hp, hpp = derivative(h), derivative(derivative(h))
    if any((evaluate_one(h), evaluate_two(h), evaluate_one(hp), evaluate_two(hp))):
        raise ValueError("Benchmark must obey H2_0 endpoint conditions")
    h2, hp2, hpp2 = mul(h, h), mul(hp, hp), mul(hpp, hpp)
    norm = add(hpp2, scaled(shifted(hp2, -2), fmpq(-3, 8)),
               scaled(shifted(h2, -4), fmpq(105, 256)))
    hardy = add(shifted(hp, -1), scaled(shifted(h, -2), fmpq(-3, 2)))
    improved = add(hpp2, scaled(mul(hardy, hardy), fmpq(-3, 8)),
                   scaled(shifted(h2, -4), fmpq(-111, 256)))

    # Independently pull the polynomial back with A=2, t=eta**2.
    # f=2**(-3/2)*f0; retain its squared normalization as the rational 1/8.
    f0 = clean({2*power-Fraction(3, 2): coefficient for power, coefficient in h.items()})
    fp, fpp = derivative(f0), derivative(derivative(f0))
    bf_p = derivative(shifted(f0, -1))
    eta_reduced = scaled(add(mul(fpp, fpp), scaled(shifted(mul(fp, fp), -2), 6),
                             scaled(shifted(mul(f0, f0), -4), -12)), fmpq(1, 8))
    eta_sos = scaled(add(mul(add(fpp, scaled(bf_p, fmpq(4, 3))),
                            add(fpp, scaled(bf_p, fmpq(4, 3)))),
                        scaled(mul(bf_p, bf_p), fmpq(2, 9))), fmpq(1, 8))
    answers = {"flat_norm": integral(hpp2), "proper_curved_norm": integral(norm),
               "proper_Hardy_decomposition": integral(improved),
               "conformal_reduced_norm": integral(eta_reduced, conformal=True),
               "conformal_positive_norm": integral(eta_sos, conformal=True)}
    anchor = answers["proper_curved_norm"]
    for key in ("proper_Hardy_decomposition", "conformal_reduced_norm", "conformal_positive_norm"):
        if answers[key] != anchor:
            raise ValueError(f"Independent proper/conformal/positive integration mismatch: {key}")
    return {"polynomial_coefficients_ascending": [str(value) for value in coefficients],
            "proper_interval": ["1", "2"], "conformal_interval_for_A_2": ["1", "sqrt(2)"],
            "integral_basis": ["1", "log(2)"],
            "exact_integrals": {key: [str(value) for value in row] for key, row in answers.items()}}
