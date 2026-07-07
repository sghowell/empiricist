"""Tests for the `empiricist` CLI (`cli.py`, M7 T3): `run` (dry + --live via
the `_client_factory` injection seam), `resume`, `status`, `certify`,
`gates list|resolve`, `report`, exit codes, and the pyproject console-script
entry point. Offline throughout -- `--live` is exercised only against a
`FakeLLMClient` factory, never a real `claude` subprocess (that is M9's job).
"""

from __future__ import annotations

import importlib.metadata

import pytest

from empiricist.cli import main
from empiricist.ledger.models import Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult

FAST_FLAGS = ["--tier0-n", "5", "--tier1-n", "4", "--search-n", "5"]


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


# -- console-script entry point -----------------------------------------------


def test_console_script_entry_point_resolves_and_is_callable():
    (ep,) = importlib.metadata.entry_points(group="console_scripts", name="empiricist")
    assert ep.value == "empiricist.cli:main"
    loaded = ep.load()
    assert loaded is main
    assert callable(loaded)


# -- run (dry, no --live) ------------------------------------------------------


def test_run_dry_runs_enumerate_and_writes_report_exit_0(tmp_path, capsys):
    run_dir = tmp_path / "run"
    rc = main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS])
    assert rc == 0

    out = capsys.readouterr().out
    assert "--live" in out  # the note that model moves need --live

    report_path = run_dir / "report.md"
    assert report_path.exists()
    text = report_path.read_text()
    assert "VERIFIED_N" in text
    assert "# Empiricist Campaign Report" in text


def test_run_dry_is_idempotent_second_call(tmp_path):
    run_dir = tmp_path / "run"
    assert main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS]) == 0
    assert main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS]) == 0

    from empiricist.campaign.state import CampaignState

    state = CampaignState.load(run_dir)
    try:
        datasets = state.ledger.find_artifacts(kind="dataset", status=Status.VERIFIED_N)
        assert len(datasets) == 1  # ensure_enumerate's idempotency held
    finally:
        state.close()


def test_run_rejects_unsupported_problem(tmp_path, capsys):
    run_dir = tmp_path / "run"
    rc = main(["run", "P9", "--run-dir", str(run_dir)])
    assert rc == 2
    assert "P9" in capsys.readouterr().err
    assert not run_dir.exists() or not (run_dir / "ledger.db").exists()


# -- resume ---------------------------------------------------------------------


def test_resume_is_an_alias_of_run_same_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    assert main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS]) == 0
    # resume takes no positional problem -- it defaults to P5 internally.
    rc = main(["resume", "--run-dir", str(run_dir), *FAST_FLAGS])
    assert rc == 0
    assert (run_dir / "report.md").exists()


# -- run --live (via the _client_factory seam) ---------------------------------


def test_run_live_uses_injected_client_and_writes_report(tmp_path):
    run_dir = tmp_path / "run"
    TRUE_CONJECTURE = {
        "family": "path", "closed_form": "N-3",
        "predicted_values": {"3": 0, "4": 1, "5": 2}, "confidence": 0.9,
    }
    # preflight's one call + a generous tail of scripted responses covering
    # whatever SEARCH/CONJECTURE waves the scheduler drives before the (tiny)
    # target set + patience exhaust it. --max-cost satisfies the fail-closed
    # budget guard without ever tripping (FakeLLMClient records no cost).
    scripted = [make_result(None)] * 400 + [make_result(TRUE_CONJECTURE)] * 20

    calls = []

    def factory():
        calls.append(1)
        return FakeLLMClient(scripted)

    rc = main(
        ["run", "P5", "--run-dir", str(run_dir), "--live", "--max-cost", "100", *FAST_FLAGS],
        _client_factory=factory,
    )
    assert rc == 0
    assert calls == [1]  # exactly one client built for the whole invocation
    assert (run_dir / "report.md").exists()
    text = (run_dir / "report.md").read_text()
    assert "# Empiricist Campaign Report" in text


def test_run_live_without_budget_ceiling_refuses_exit_2(tmp_path, capsys):
    """I1 fail-closed posture: --live with NEITHER --max-cost NOR --max-gen
    must refuse to start -- before building a client, before any preflight
    call, before touching the run directory's ledger."""
    run_dir = tmp_path / "run"

    def factory():
        raise AssertionError("client must never be constructed on refusal")

    rc = main(
        ["run", "P5", "--run-dir", str(run_dir), "--live", *FAST_FLAGS],
        _client_factory=factory,
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "--max-cost" in err and "--max-gen" in err
    assert not (run_dir / "ledger.db").exists()


@pytest.mark.parametrize("budget_flags", [["--max-cost", "100"], ["--max-gen", "1"]])
def test_run_live_with_either_budget_flag_proceeds(tmp_path, budget_flags):
    """Either ceiling alone satisfies the guard; the campaign runs and the
    report is written."""
    run_dir = tmp_path / "run"
    scripted = [make_result(None)] * 500  # preflight ok + all-refusal waves

    rc = main(
        ["run", "P5", "--run-dir", str(run_dir), "--live", *budget_flags, *FAST_FLAGS],
        _client_factory=lambda: FakeLLMClient(scripted),
    )
    assert rc == 0
    assert (run_dir / "report.md").exists()


def test_run_live_preflight_failure_returns_1(tmp_path, capsys):
    run_dir = tmp_path / "run"

    class RefusingClient:
        async def complete(self, *args, **kwargs):
            return None

        async def complete_many(self, *args, **kwargs):
            return []

    rc = main(
        ["run", "P5", "--run-dir", str(run_dir), "--live", "--max-gen", "3", *FAST_FLAGS],
        _client_factory=lambda: RefusingClient(),
    )
    assert rc == 1
    assert "preflight" in capsys.readouterr().err.lower()
    assert not (run_dir / "report.md").exists()


# -- status ---------------------------------------------------------------------


def test_status_reports_counts_spend_and_population(tmp_path, capsys):
    run_dir = tmp_path / "run"
    main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS])

    rc = main(["status", "--run-dir", str(run_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "VERIFIED_N: 1" in out
    assert "spend: $" in out
    assert "population size: 0" in out


def test_status_on_empty_run_dir_exits_0(tmp_path, capsys):
    run_dir = tmp_path / "empty"
    rc = main(["status", "--run-dir", str(run_dir)])
    assert rc == 0
    assert "(none)" in capsys.readouterr().out


# -- certify ----------------------------------------------------------------------


def test_certify_stamps_both_fusion_verifiers(tmp_path, capsys):
    run_dir = tmp_path / "run"
    rc = main(["certify", "--run-dir", str(run_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "stab_fusion" in out and "PASS" in out
    assert "enum_fusion" in out


# -- gates ------------------------------------------------------------------------


def test_gates_list_empty(tmp_path, capsys):
    run_dir = tmp_path / "run"
    rc = main(["gates", "--run-dir", str(run_dir), "list"])
    assert rc == 0
    assert "no gates" in capsys.readouterr().out


def test_gates_resolve_round_trip(tmp_path, capsys):
    run_dir = tmp_path / "run"
    from empiricist.campaign.state import CampaignState

    state = CampaignState.load(run_dir)
    gate = state.gates.open("PROOF_CAMPAIGN", artifact_id="a" * 64, note="test")
    state.close()

    rc_list = main(["gates", "--run-dir", str(run_dir), "list"])
    assert rc_list == 0
    out = capsys.readouterr().out
    assert gate.id in out and "PROOF_CAMPAIGN" in out

    rc_resolve = main(["gates", "--run-dir", str(run_dir), "resolve", gate.id, "--approve"])
    assert rc_resolve == 0
    out = capsys.readouterr().out
    assert f"{gate.id} -> approved" in out

    state2 = CampaignState.load(run_dir)
    try:
        resolved = state2.gates.list(state="approved")
        assert len(resolved) == 1 and resolved[0].id == gate.id
    finally:
        state2.close()


def test_gates_resolve_unknown_id_returns_1(tmp_path, capsys):
    run_dir = tmp_path / "run"
    rc = main(["gates", "--run-dir", str(run_dir), "resolve", "nope", "--approve"])
    assert rc == 1
    assert "no such gate" in capsys.readouterr().err


def test_gates_resolve_already_resolved_returns_1(tmp_path, capsys):
    run_dir = tmp_path / "run"
    from empiricist.campaign.state import CampaignState

    state = CampaignState.load(run_dir)
    gate = state.gates.open("RELEASE", artifact_id="b" * 64)
    state.close()

    assert main(["gates", "--run-dir", str(run_dir), "resolve", gate.id, "--reject"]) == 0
    rc = main(["gates", "--run-dir", str(run_dir), "resolve", gate.id, "--approve"])
    assert rc == 1
    assert "already" in capsys.readouterr().err.lower()


def test_gates_resolve_requires_approve_or_reject(tmp_path):
    run_dir = tmp_path / "run"
    with pytest.raises(SystemExit):
        main(["gates", "--run-dir", str(run_dir), "resolve", "some-id"])


# -- report -----------------------------------------------------------------------


def test_report_prints_to_stdout_by_default(tmp_path, capsys):
    run_dir = tmp_path / "run"
    main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS])

    rc = main(["report", "--run-dir", str(run_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# Empiricist Campaign Report" in out
    assert "VERIFIED_N" in out


def test_report_writes_to_out_file(tmp_path, capsys):
    run_dir = tmp_path / "run"
    main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS])

    out_file = tmp_path / "custom_report.md"
    rc = main(["report", "--run-dir", str(run_dir), "--out", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    assert "# Empiricist Campaign Report" in out_file.read_text()
    assert f"report written to {out_file}" in capsys.readouterr().out


# -- argparse-level usage errors (SystemExit(2), left to argparse) ---------------


def test_missing_run_dir_is_argparse_usage_error():
    with pytest.raises(SystemExit) as exc_info:
        main(["status"])
    assert exc_info.value.code == 2


def test_no_command_is_argparse_usage_error():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
