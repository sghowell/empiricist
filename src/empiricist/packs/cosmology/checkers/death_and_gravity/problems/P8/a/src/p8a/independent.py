"""Independent FLINT polynomial integration for the localization certificate."""

from flint import fmpq, fmpq_poly

P = fmpq_poly([0, 0, 3, -2])
ANGLE_D = P.derivative()/2
ANGLE_DD = ANGLE_D.derivative()
R = fmpq(3, 4)
A = 1-R
BASIS = (P, fmpq_poly([0, 0, 1, -2, 1]), fmpq_poly([0, 0, -1, 4, -5, 2]))


def integral(poly):
    return sum((value/fmpq(j+1) for j, value in enumerate(poly)), fmpq(0))


def local_pair(left, right):
    """Coefficients in ascending powers of pi squared; only FLINT rationals."""
    lp, rp = left.derivative(), right.derivative()
    lpp, rpp = lp.derivative(), rp.derivative()
    return [integral(lpp*rpp),
            integral(-ANGLE_D**2*(left*rpp+lpp*right)
                     +(2*ANGLE_D*lp+ANGLE_DD*left)*(2*ANGLE_D*rp+ANGLE_DD*right)),
            integral(ANGLE_D**4*left*right)]


def compose(poly, argument):
    value = fmpq_poly([])
    for coefficient in reversed(list(poly)):
        value = value*argument+coefficient
    return value


def tail_pair(left, right, first_cell=1):
    result = [fmpq(0)]*3
    w = fmpq_poly([1, -A])
    for k, ak in enumerate(left):
        for ell, al in enumerate(right):
            if not ak or not al:
                continue
            exponent = k+ell-3
            if min(k, ell) < 2:
                raise ValueError("Non-H2 endpoint monomial")
            factor = ak*al*R**(exponent*(first_cell-1))/((A*R)**3*(1-R**exponent))
            local = local_pair(w**k, w**ell)
            result = [value+factor*term for value, term in zip(result, local, strict=True)]
    return result


def finite_cells(left, right, cells):
    """Direct substitution and integration on j=1,...,cells; no geometric sum."""
    result = [fmpq(0)]*3
    for j in range(1, cells+1):
        w = fmpq_poly([R**(j-1), -A*R**(j-1)])
        local = local_pair(compose(left, w), compose(right, w))
        h = A*R**j
        result = [value+term/h**3 for value, term in zip(result, local, strict=True)]
    return result


def replay():
    result = {"initial_localized_norm": [str(value/A**3) for value in local_pair(P, P)],
              "tail_basis_gram": [], "finite_sum_plus_remainder_residuals": []}
    for left in BASIS:
        row = []
        for right in BASIS:
            infinite = tail_pair(left, right)
            finite = finite_cells(left, right, 4)
            remainder = tail_pair(left, right, 5)
            residual = [total-part-rest for total, part, rest
                        in zip(infinite, finite, remainder, strict=True)]
            if any(residual):
                raise ValueError("Independent finite-cell and infinite-tail reconstruction failed")
            row.append([str(value) for value in infinite])
            result["finite_sum_plus_remainder_residuals"].append([str(value) for value in residual])
        result["tail_basis_gram"].append(row)
    return result
