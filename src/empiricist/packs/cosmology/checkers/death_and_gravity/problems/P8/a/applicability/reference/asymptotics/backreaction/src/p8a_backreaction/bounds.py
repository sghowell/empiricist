"""Rational slab guards and a deliberately conditional actual-response bridge."""

from dataclasses import dataclass
from fractions import Fraction

from p8a_asymptotics.bounds import rational


@dataclass(frozen=True)
class Slab:
    """d is the resolved kappa*hbar/(46080*pi^2), in the declared clock units."""

    d: Fraction
    epsilon: Fraction
    t_minus: Fraction
    t_plus: Fraction
    z_max: Fraction = Fraction(1, 4)

    def __post_init__(self):
        for name in ("d", "epsilon", "t_minus", "t_plus", "z_max"):
            object.__setattr__(self, name, rational(getattr(self, name)))
        if self.d <= 0 or self.epsilon < 0:
            raise ValueError("Positive d and nonnegative epsilon are required")
        if self.t_minus <= 0 or self.t_plus <= self.t_minus:
            raise ValueError("A strictly ordered compact positive-time slab is required")
        if not 0 < self.z_max <= Fraction(1, 4):
            raise ValueError("This certified Taylor/defect domain requires 0<z_max<=1/4")
        if self.actual_z_max > self.z_max:
            raise ValueError("The slab exceeds the supplied certified z domain")

    @property
    def actual_z_max(self):
        return 4*self.epsilon*self.d/self.t_minus**2

    def preparation_check(self, past_time):
        past_time = rational(past_time)
        if not 0 < past_time < self.t_minus:
            raise ValueError("The common preparation time must precede the target slab")
        radicand = 1-4*self.epsilon*self.d/past_time**2
        if radicand <= 0:
            raise ValueError("Uniform positivity on the preparation interval is not certified")
        return {"past_time": str(past_time), "sufficient_radicand_lower_bound": str(radicand),
                "temporal_cutoff_is_one_on_target_slab": "required by the written construction"}


def frozen_bounds(slab):
    scale = slab.actual_z_max**2/slab.t_minus**2
    return {"density": Fraction(7, 3)*scale,
            "pressure": Fraction(35, 9)*scale, "EED": 7*scale}


def response_bridge(slab, *, density_response, pressure_response):
    """Bound kappa*|T_epsilon-T_ref|/epsilon, including any moved loop terms.

    No additional explicit curvature source may be omitted from these inputs.
    The response bounds themselves are supplied, not derived here.
    """
    density_response, pressure_response = map(rational, (density_response, pressure_response))
    if min(density_response, pressure_response) < 0:
        raise ValueError("Nonnegative supplied quantum-response bounds are required")
    frozen = frozen_bounds(slab)
    density = frozen["density"]+slab.epsilon**2*density_response
    pressure = frozen["pressure"]+slab.epsilon**2*pressure_response
    return {
        "actual_response_status": "CONDITIONAL_INPUT_NOT_DERIVED",
        "assumption": "kappa*abs(rho_epsilon-rho_ref)<=epsilon*M_rho and likewise pressure throughout the slab",
        "explicit_loop_curvature_terms": "absent, or their moved-to-source contribution (alpha*I+beta*J)/kappa is included in the supplied response bounds",
        "supplied_M_rho": str(density_response), "supplied_M_pressure": str(pressure_response),
        "conditional_actual_density_defect_bound": str(density),
        "conditional_actual_pressure_defect_bound": str(pressure),
        "conditional_actual_EED_defect_bound": str((density+3*pressure)/2),
        "numerical_actual_quantum_response_certified": False,
    }
