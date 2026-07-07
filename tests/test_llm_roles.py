"""Tests for the seven role definitions and their sampling policy (spec §5.4)."""

from empiricist.llm.models import Effort
from empiricist.llm.roles import ROLES, active_roles


def test_all_seven_roles_present():
    assert set(ROLES) == {
        "prospector", "toolwright", "searcher", "conjecturer",
        "prover", "critic", "formalizer",
    }


def test_roles_are_frozen():
    import dataclasses

    import pytest
    r = ROLES["searcher"]
    assert dataclasses.is_dataclass(r)
    with pytest.raises(AttributeError):
        r.k = 99  # type: ignore[misc]


def test_effort_matches_spec_table():
    assert ROLES["searcher"].effort is Effort.LOW
    assert ROLES["conjecturer"].effort is Effort.MEDIUM
    assert ROLES["prover"].effort is Effort.MAX
    assert ROLES["critic"].effort is Effort.MAX
    assert ROLES["formalizer"].effort is Effort.HIGH


def test_sampling_counts_match_spec():
    # max wave size; concurrency is clamped down by the client semaphore
    assert ROLES["searcher"].k >= 16
    assert ROLES["critic"].k == 2         # two independent critics
    assert ROLES["prover"].k == 1
    assert ROLES["conjecturer"].k >= 4


def test_active_roles_excludes_v0_stubs():
    """Prospector + Toolwright are deferred stubs in v0 (spec D11)."""
    names = {r.name for r in active_roles()}
    assert "prospector" not in names and "toolwright" not in names
    assert {"searcher", "conjecturer", "prover", "critic", "formalizer"} <= names


def test_every_role_has_a_nonempty_system_prompt():
    for r in ROLES.values():
        assert isinstance(r.system_prompt, str) and len(r.system_prompt) > 20


def test_role_has_model_default_fable5():
    assert ROLES["searcher"].model == "claude-fable-5"
