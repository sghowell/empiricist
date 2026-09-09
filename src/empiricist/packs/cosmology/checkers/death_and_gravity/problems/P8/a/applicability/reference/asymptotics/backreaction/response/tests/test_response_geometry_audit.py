"""Independent point-split, geometric and physical-clock audits for A.6.

These derive the quantities directly, without calling the response assembly
or its identity checker. The constant-potential integral below tests a local
kernel limit, not the existence of a smoothly prepared constant-potential state.
"""

import sympy as sp
from p8a_response import response


def test_response_spatial_split_finite_constant():
    radius, duration, scale, length = sp.symbols("r D a lambda", positive=True)
    # Exact integral from 0 to D of log |(2s+r)/(2s-r)|, for 0<r<2D.
    primitive = duration*sp.log((2*duration+radius)/(2*duration-radius))
    primitive += radius*sp.log((4*duration**2-radius**2)/radius**2)/2
    assert sp.simplify(sp.diff(primitive, duration)
                       - sp.log((2*duration+radius)/(2*duration-radius))) == 0
    # Strip hbar*V/(8*pi^2). The Hadamard constant is a''/(48*pi^2*a),
    # so subtracting it contributes +1/6 in these units, since a''/a=-V.
    regularized = -primitive/radius - sp.log(radius*scale/(sp.sqrt(2)*length))
    regularized += sp.Rational(1, 6)
    finite = sp.limit(regularized, radius, 0, dir="+")
    expected = -sp.log(sp.sqrt(2)*scale*duration/length)-sp.Rational(5, 6)
    assert sp.simplify(sp.expand_log(finite-expected, force=True)) == 0
    assert sp.simplify(sp.expand_log(finite-(expected-sp.Rational(1, 6)),
                                   force=True)) == sp.Rational(1, 6)


def test_response_density_from_direct_proper_time_curvature():
    eta, amplitude = sp.symbols("eta A", positive=True)
    q = sp.Function("Q")(eta)
    kernel = sp.Function("K")(eta)
    dt = lambda value: sp.diff(value, eta)/(amplitude*eta)
    h0 = 1/(amplitude*eta**2)
    dh0 = -2/(amplitude**2*eta**4)
    h1, dh1 = dt(q), dt(dt(q))
    box0 = lambda value: dt(dt(value))+3*h0*dt(value)
    r1 = 6*(dh1+4*h0*h1)
    potential = -sp.diff(q, eta, 2)-3*sp.diff(q, eta)/eta
    assert sp.simplify(r1+6*potential/(amplitude**2*eta**2)) == 0

    # Riemann^2-Ricci^2=-12 H^2*(Hdot+H^2); differentiate before
    # setting Hdot=-2H^2. Keep GS's positive-time Box convention.
    h, dh = sp.symbols("H Hdot")
    curvature_difference = -12*h**2*(dh+h**2)
    delta_difference = sp.diff(curvature_difference, h).subs({h: h0, dh: dh0})*h1
    delta_difference += sp.diff(curvature_difference, dh).subs({h: h0, dh: dh0})*dh1
    delta_v1 = delta_difference/720-box0(r1)/120
    wick1 = -kernel/(8*amplitude**2*eta**2)
    theta1 = -box0(wick1)/2-delta_v1/4  # units hbar/pi^2
    rho1 = (sp.diff(kernel, eta)/eta**5-kernel/eta**6)/(16*amplitude**4)
    rho1 += (-3*sp.diff(potential, eta)/eta**5+3*potential/eta**6
             + sp.diff(q, eta)/eta**7)/(240*amplitude**4)
    rho0 = 1/(960*amplitude**4*eta**8)
    # Linearization of rho_dot+4H*rho-H*Theta=0, with Theta0=-4rho0.
    assert sp.simplify(dt(rho1)+4*h0*rho1-h0*theta1+8*h1*rho0) == 0
    exported = response.proper_time(kernel, q, eta=eta, a=amplitude, hbar=sp.pi**2, gamma=0)
    assert sp.simplify(exported["density"]-rho1) == 0
    assert sp.simplify(exported["density"]-3*exported["pressure"]-theta1) == 0
    assert sp.simplify(exported["EED"]-rho1+theta1/2) == 0
    # A dropped anomaly term does not pass the same conservation check.
    assert sp.simplify(dt(rho1)+4*h0*rho1+h0*box0(wick1)/2
                       + 8*h1*rho0) != 0


def test_response_finite_tensor_from_covariant_variation():
    eta, amplitude = sp.symbols("eta A", positive=True)
    potential = sp.Function("V")(eta)
    h0 = 1/(amplitude*eta**2)
    r1 = -6*potential/(amplitude**2*eta**2)
    dt = lambda value: sp.diff(value, eta)/(amplitude*eta)
    # FK R_tt=3*(Hdot+H^2)=-3H^2 at radiation. Vary the full tensor
    # I_ab=2RR_ab-g_ab R^2/2-2(g_ab Box-nabla_a nabla_b)R.
    density = 2*r1*(-3*h0**2)-6*h0*dt(r1)
    trace = -6*(dt(dt(r1))+3*h0*dt(r1))
    expected = 36*(sp.diff(potential, eta)/eta**5-potential/eta**6)/amplitude**4
    assert sp.simplify(density-expected) == 0
    pressure = (density-trace)/3
    assert sp.simplify(dt(density)+3*h0*(density+pressure)) == 0
    exported = response.curvature_response(potential, eta=eta, a=amplitude)
    assert sp.simplify(exported["density"]-density) == 0
    assert sp.simplify(exported["pressure"]-pressure) == 0


def test_response_preparation_clock_integral_cancels_only_after_pullback():
    eta, amplitude = sp.symbols("eta A", positive=True)
    q = sp.Function("Q")(eta)
    integral = sp.Function("J")(eta)
    b = q+integral/eta
    # dJ/deta=Q, b=Q+J/eta; the comparison time shift is A*eta*J.
    density_clock_part = (sp.diff(b, eta)/eta**7-b/eta**8)/(240*amplitude**4)
    density_clock_part = density_clock_part.subs(sp.diff(integral, eta), q)
    rho0 = 1/(960*amplitude**4*eta**8)
    pulled_back = density_clock_part-integral*sp.diff(rho0, eta)
    assert sp.simplify(pulled_back-sp.diff(q, eta)/(240*amplitude**4*eta**7)) == 0
    assert sp.simplify(density_clock_part-pulled_back) != 0
    # On A.5's target slab, identifying Q with b gives the wrong potential.
    d = sp.symbols("d", positive=True)
    target = -4*d/(amplitude**2*eta**4)
    correct = -sp.diff(target, eta, 2)-3*sp.diff(target, eta)/eta
    copied_clock = -sp.diff(target, eta, 2)-2*sp.diff(target, eta)/eta
    assert sp.simplify(correct-32*d/(amplitude**2*eta**6)) == 0
    assert sp.simplify(copied_clock-correct-16*d/(amplitude**2*eta**6)) == 0


def test_response_second_order_geometric_correction_and_bianchi_identity():
    t, d, epsilon = sp.symbols("t d epsilon", positive=True)
    correction = sp.Function("r")(t)
    quantum_density1 = sp.Function("kappa_rho1")(t)
    # A.5 reference stress: kappa*rho0=3d/t^4. First-order stress
    # conservation fixes kappa*p1 once kappa*rho1 is known.
    quantum_pressure1 = -quantum_density1-2*t*sp.diff(quantum_density1, t)/3-32*d**2/t**6
    frozen_density2 = 24*d**2/t**6
    frozen_pressure2 = 40*d**2/t**6
    density_defect = frozen_density2-quantum_density1
    pressure_defect = frozen_pressure2-quantum_pressure1
    assert sp.simplify(sp.diff(density_defect, t)
                       + 3*(density_defect+pressure_defect)/(2*t)) == 0
    # Directly vary the radiation background at order epsilon^2. These
    # are changes relative to a_OR, not the full second-order metric jets.
    a_relative = sp.exp(epsilon**2*correction)
    h = 1/(2*t)+sp.diff(sp.log(a_relative), t)
    density = 3*h**2-3*a_relative**(-4)/(4*t**2)
    pressure = -2*sp.diff(h, t)-3*h**2-a_relative**(-4)/(4*t**2)
    density_change = sp.diff(density, epsilon, 2).subs(epsilon, 0)/2
    pressure_change = sp.diff(pressure, epsilon, 2).subs(epsilon, 0)/2
    first = -correction/t-t*density_defect/3
    second = sp.diff(first, t).subs(sp.diff(correction, t), first)
    rules = {sp.diff(correction, t): first, sp.diff(correction, t, 2): second}
    assert sp.simplify((density_defect+density_change).subs(rules, simultaneous=True)) == 0
    assert sp.simplify((pressure_defect+pressure_change).subs(rules, simultaneous=True)) == 0
