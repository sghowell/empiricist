"""Tests for pydantic role-output schemas and their JSON-schema export."""

from math import pi, sqrt

import pytest
from pydantic import ValidationError

from empiricist.domain.p3.scheme import scheme_from_out
from empiricist.domain.p3.verify import verify_scheme_agreed
from empiricist.llm.schemas import (
    AncillaTerm,
    BellSchemeOut,
    ConjectureOut,
    CritiqueOut,
    MeshElement,
    json_schema_for,
)


def test_conjecture_out_validates_a_wellformed_object():
    obj = ConjectureOut(
        family="path", closed_form="N-3", predicted_values={"3": 0, "4": 1},
        confidence=0.7,
    )
    assert obj.family == "path" and obj.predicted_values["4"] == 1


def test_conjecture_out_rejects_missing_field():
    with pytest.raises(ValidationError):
        ConjectureOut(family="path", closed_form="N-3")  # missing predicted_values


def test_critique_out_gap_or_no_gap():
    gap = CritiqueOut(verdict="GAP", location="lemma 2, line 5",
                      detail="unjustified step", edges_checked=[])
    nogap = CritiqueOut(verdict="NO_GAP_FOUND", location=None, detail=None,
                        edges_checked=["l1->l2", "l2->l3"])
    assert gap.verdict == "GAP" and nogap.verdict == "NO_GAP_FOUND"


def test_critique_out_rejects_bad_verdict():
    with pytest.raises(ValidationError):
        CritiqueOut(verdict="MAYBE", location=None, detail=None, edges_checked=[])


def test_json_schema_for_produces_cli_ready_dict():
    schema = json_schema_for(ConjectureOut)
    assert schema["type"] == "object"
    assert "family" in schema["properties"]
    # additionalProperties must be false so the CLI enforces a closed shape.
    assert schema.get("additionalProperties") is False


def test_json_schema_is_json_serializable():
    import json
    json.dumps(json_schema_for(CritiqueOut))  # must not raise


# -- BellSchemeOut (P3): shape-only guarantee + converter round-trips ---------


def _bs_el(i: int, j: int) -> dict:
    return {"kind": "bs", "i": i, "j": j, "theta": pi / 4, "phi": 0.0}


def test_bell_scheme_out_round_trips_standard_bsm_to_pass():
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [_bs_el(0, 2), _bs_el(1, 3)],
        "claimed_p_avg": 0.5,
    }
    out = BellSchemeOut.model_validate(d)
    scheme = scheme_from_out(out)
    r = verify_scheme_agreed(scheme, claimed_p_avg=out.claimed_p_avg)
    assert r.verdict == "PASS"
    assert abs(r.report.p_avg - 0.5) < 1e-9


def test_scheme_from_out_rejects_unnormalized_ancilla():
    # A single ancilla term with re=0.5 (norm 0.25, not 1.0): schema-valid
    # SHAPE, physics-invalid content -- caught by BellScheme.validate(),
    # called by scheme_from_out before it returns.
    d = {
        "n_modes": 6,
        "n_ancilla_photons": 1,
        "ancilla": [{"pattern": [1, 0], "re": 0.5, "im": 0.0}],
        "mesh": [],
    }
    out = BellSchemeOut.model_validate(d)
    with pytest.raises(ValueError, match="not normalized"):
        scheme_from_out(out)


def test_bell_scheme_out_rejects_extra_fields():
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [],
        "bogus": 1,
    }
    with pytest.raises(ValidationError):
        BellSchemeOut.model_validate(d)


def test_mesh_element_and_ancilla_term_reject_extra_fields():
    with pytest.raises(ValidationError):
        MeshElement(kind="bs", i=0, j=1, theta=0.0, phi=0.0, bogus=1)
    with pytest.raises(ValidationError):
        AncillaTerm(pattern=[1, 0], re=1.0, im=0.0, bogus=1)


def test_bell_scheme_out_round_trips_grice_boosted_to_pass():
    # Grice PRA 84, 042331 (2011): 8 modes, k=2, ancilla dual-rail Bell pair
    # on modes 4-7, the 8-element mesh from known_schemes.grice_boosted_bsm.
    r2 = 1.0 / sqrt(2)
    d = {
        "n_modes": 8,
        "n_ancilla_photons": 2,
        "ancilla": [
            {"pattern": [1, 0, 1, 0], "re": r2, "im": 0.0},
            {"pattern": [0, 1, 0, 1], "re": r2, "im": 0.0},
        ],
        "mesh": [
            _bs_el(0, 2), _bs_el(1, 3),                        # input BSM
            _bs_el(4, 6), _bs_el(5, 7),                        # ancilla BSM
            _bs_el(0, 4), _bs_el(1, 5), _bs_el(2, 6), _bs_el(3, 7),  # rail coupling
        ],
        "claimed_p_avg": 0.75,
    }
    out = BellSchemeOut.model_validate(d)
    scheme = scheme_from_out(out)
    r = verify_scheme_agreed(scheme, claimed_p_avg=out.claimed_p_avg)
    assert r.verdict == "PASS"
    assert abs(r.report.p_avg - 0.75) < 1e-9
    assert abs(r.report.p_min - 0.5) < 1e-9
