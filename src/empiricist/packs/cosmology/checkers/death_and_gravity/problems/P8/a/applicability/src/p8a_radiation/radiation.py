"""Mode, field-map and comoving geometric checks on the radiation patch."""

import sympy as sp


def identities():
    eta, t, scale, k = sp.symbols("eta t A k", positive=True)
    a = sp.Function("a")(eta)
    chi = sp.Function("chi")(eta)
    phi = chi/a
    rescaled = sp.expand(a*(sp.diff(phi, eta, 2)+2*sp.diff(a, eta)/a*sp.diff(phi, eta)+k**2*phi))
    generic = sp.diff(chi, eta, 2)+(k**2-sp.diff(a, eta, 2)/a)*chi
    ar = scale*eta
    mode = sp.exp(-sp.I*k*eta)/(ar*sp.sqrt(2*k))
    conjugate = sp.conjugate(mode)
    mode_residual = sp.simplify(sp.diff(mode, eta, 2)+2/eta*sp.diff(mode, eta)+k**2*mode)
    wronskian = sp.simplify(ar**2*(mode*sp.diff(conjugate, eta)-sp.diff(mode, eta)*conjugate))
    velocity = 1/ar
    acceleration = sp.simplify(velocity*sp.diff(velocity, eta)+sp.diff(ar, eta)/ar*velocity**2)
    hubble = 1/(2*t)
    expansion = 3*hubble
    rho = sp.diff(expansion, t)+expansion**2/3
    ricci_scalar = 6*(sp.diff(hubble, t)+2*hubble**2)
    kretschmann = 12*((sp.diff(hubble, t)+hubble**2)**2+hubble**4)
    wrong_a = scale*eta**2
    wrong_mode = sp.exp(-sp.I*k*eta)/(wrong_a*sp.sqrt(2*k))
    wrong_residual = sp.simplify(wrong_a*(sp.diff(wrong_mode, eta, 2)
                                +2*sp.diff(wrong_a, eta)/wrong_a*sp.diff(wrong_mode, eta)
                                +k**2*wrong_mode))
    return {
        "residuals": {
            "rescaled_Klein_Gordon": sp.simplify(rescaled-generic),
            "radiation_plane_wave_solves_KG": mode_residual,
            "canonical_mode_Wronskian": sp.simplify(wronskian-sp.I),
            "cosmic_clock": sp.diff(scale*eta**2/2, eta)-ar,
            "comoving_geodesic_acceleration": acceleration,
            "radiation_Ricci_scalar_zero": ricci_scalar,
        },
        "metric": "ds^2=(A*eta)^2*(deta^2-dx^2), A>0, eta>0",
        "proper_time": "t=A*eta^2/2 > 0",
        "reference_two_point": "W0_rad(x,x')=W0_Mink(x,x')/[a(eta)*a(eta')]",
        "field_map": "chi=a*phi; Dchi=(partial_eta-1/eta)chi; partial_t phi=a^-2 Dchi",
        "Ricci_UU_FK_convention": str(rho),
        "Kretschmann": str(sp.simplify(kretschmann)),
        "initial_slice_expansion": str(expansion),
        "all_normals_scope": "all normals to a constant-t FLRW slice are comoving; no other slices/backgrounds",
        "matter_era_flat_mode_negative_control": str(wrong_residual),
    }
