"""Tests for the `empiricist` CLI (`cli.py`, M7 T3): `run` (dry + --live via
the `_client_factory` injection seam), `resume`, `status`, `certify`,
`gates list|resolve`, `report`, exit codes, and the pyproject console-script
entry point. Offline throughout -- `--live` is exercised only against a
`FakeLLMClient` factory, never a real `claude` subprocess (that is M9's job).
"""

from __future__ import annotations

import importlib.metadata

import pytest

from empiricist.campaign.state import CampaignState
from empiricist.cli import _build_client, build_parser, main
from empiricist.ledger.db import UNKNOWN_BILLING_EXIT_CODE
from empiricist.ledger.models import Artifact, Run, Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.llm.openai_responses import OpenAIResponsesClient

FAST_FLAGS = ["--tier0-n", "5", "--tier1-n", "4", "--search-n", "5"]
PREFLIGHT_OK = {"ok": True}


def _tree_snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            "dir" if path.is_dir() else "file",
            None if path.is_dir() else path.read_bytes(),
        )
        for path in sorted(root.rglob("*"))
    }


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
    scripted = (
        [make_result(PREFLIGHT_OK)]
        + [make_result(None)] * 399
        + [make_result(TRUE_CONJECTURE)] * 20
    )

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


def test_run_live_without_budget_stop_condition_refuses_exit_2(tmp_path, capsys):
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


@pytest.mark.parametrize("value", ["0", "-1"])
def test_run_live_rejects_max_gen_below_one_before_client(tmp_path, capsys, value):
    run_dir = tmp_path / "run"

    def factory():
        raise AssertionError("client must never be constructed")

    rc = main(
        [
            "run", "P5", "--run-dir", str(run_dir), "--live",
            "--max-gen", value, *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 2
    assert "--max-gen must be at least 1" in capsys.readouterr().err
    assert not run_dir.exists()


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_run_live_rejects_invalid_max_cost_before_client(tmp_path, capsys, value):
    run_dir = tmp_path / "run"

    def factory():
        raise AssertionError("client must never be constructed")

    rc = main(
        [
            "run", "P5", "--run-dir", str(run_dir), "--live",
            "--max-cost", value, *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 2
    assert "--max-cost must be a finite number greater than 0" in capsys.readouterr().err
    assert not run_dir.exists()


@pytest.mark.parametrize("budget_flags", [["--max-cost", "100"], ["--max-gen", "1"]])
def test_run_live_with_either_budget_flag_proceeds(tmp_path, budget_flags):
    """Either stop condition alone satisfies the guard; the campaign runs and the
    report is written."""
    run_dir = tmp_path / "run"
    scripted = (
        [make_result(PREFLIGHT_OK)]
        + [make_result(None)] * 499
    )  # strict preflight canary + all-refusal waves

    rc = main(
        ["run", "P5", "--run-dir", str(run_dir), "--live", *budget_flags, *FAST_FLAGS],
        _client_factory=lambda: FakeLLMClient(scripted),
    )
    assert rc == 0
    assert (run_dir / "report.md").exists()


def test_resume_at_generation_limit_skips_client_and_paid_preflight(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.population.log_event(1, "generation", {"inserted": 0})
    state.close()

    def factory():
        raise AssertionError("client must never be constructed")

    rc = main(
        [
            "resume", "--run-dir", str(run_dir), "--live",
            "--max-gen", "1", *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "already at configured stop condition" in out
    assert "no preflight/model call" in out


def test_resume_at_cost_threshold_skips_client_and_paid_preflight(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.ledger.start_run(Run(run_id="prior", move="SAMPLE", role="searcher"))
    state.ledger.finish_run(
        "prior", exit_code=0, wall_s=1.0, tokens_in=1, tokens_out=1, cost_usd=2.0
    )
    state.close()

    def factory():
        raise AssertionError("client must never be constructed")

    rc = main(
        [
            "resume", "--run-dir", str(run_dir), "--live",
            "--max-cost", "2", *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 0
    assert "already at configured stop condition" in capsys.readouterr().out


def test_resume_blocks_unknown_billing_until_explicitly_acknowledged(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.ledger.start_run(
        Run(
            run_id="ambiguous-openai-call",
            move="SAMPLE",
            provider="openai",
            exit_code=UNKNOWN_BILLING_EXIT_CODE,
            ended="2026-07-24T00:00:00+00:00",
            cost_usd=2.0,
        )
    )
    state.close()

    def factory():
        raise AssertionError("client must never be constructed")

    base_args = [
        "resume", "--run-dir", str(run_dir), "--live",
        "--max-cost", "2", *FAST_FLAGS,
    ]
    assert main(base_args, _client_factory=factory) == 1
    err = capsys.readouterr().err
    assert "billing is unknown" in err
    assert "--acknowledge-unknown-billing" in err

    assert main(
        [*base_args, "--acknowledge-unknown-billing"],
        _client_factory=factory,
    ) == 0
    out = capsys.readouterr().out
    assert "acknowledged unresolved billing" in out
    assert "already at configured stop condition" in out


def test_resume_blocks_unreconciled_provider_orphan_before_preflight(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.ledger.start_run(
        Run(run_id="crashed-paid-call", move="SAMPLE", provider="openai")
    )
    state.close()

    def factory():
        raise AssertionError("client must never be constructed")

    rc = main(
        [
            "resume", "--run-dir", str(run_dir), "--live",
            "--max-gen", "1", *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 1
    assert "crashed-paid-call" in capsys.readouterr().err


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


def test_openai_provider_builds_gpt56_pro_client_without_reusing_codex_auth(tmp_path):
    args = build_parser().parse_args([
        "run",
        "P5",
        "--run-dir",
        str(tmp_path / "run"),
        "--provider",
        "openai",
        "--openai-model",
        "gpt-5.6-sol",
        "--openai-reasoning-mode",
        "pro",
    ])
    client = _build_client(args)
    assert isinstance(client, OpenAIResponsesClient)
    assert client.model == "gpt-5.6-sol"
    assert client.reasoning_mode == "pro"
    assert client.has_cost_accounting is False


def test_openai_max_cost_requires_explicit_pricing_before_client_construction(
    tmp_path, capsys
):
    run_dir = tmp_path / "run"

    def factory():
        raise AssertionError("client must not be built when accounting is unsafe")

    rc = main(
        [
            "run", "P5", "--run-dir", str(run_dir), "--live",
            "--provider", "openai", "--max-cost", "1", *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 2
    assert "explicit current pricing" in capsys.readouterr().err
    assert not run_dir.exists()


def test_openai_pricing_flags_are_all_or_nothing(tmp_path, capsys):
    rc = main(
        [
            "run", "P5", "--run-dir", str(tmp_path / "run"), "--live",
            "--provider", "openai", "--max-gen", "1",
            "--openai-input-usd-per-mtok", "1", *FAST_FLAGS,
        ],
        _client_factory=lambda: FakeLLMClient([]),
    )
    assert rc == 2
    assert "all-or-nothing" in capsys.readouterr().err


def test_openai_live_requires_cost_threshold_not_only_generation_limit(
    tmp_path, capsys
):
    def factory():
        raise AssertionError("client must not be built without a cost threshold")

    rc = main(
        [
            "run", "P5", "--run-dir", str(tmp_path / "run"), "--live",
            "--provider", "openai", "--max-gen", "1",
            "--openai-input-usd-per-mtok", "1",
            "--openai-cached-input-usd-per-mtok", "1",
            "--openai-output-usd-per-mtok", "1",
            *FAST_FLAGS,
        ],
        _client_factory=factory,
    )
    assert rc == 2
    assert "require --max-cost" in capsys.readouterr().err


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


def test_status_on_missing_run_dir_returns_1_without_creating(tmp_path, capsys):
    run_dir = tmp_path / "missing"
    rc = main(["status", "--run-dir", str(run_dir)])
    assert rc == 1
    assert "campaign ledger does not exist" in capsys.readouterr().err
    assert not run_dir.exists()


# -- audit ----------------------------------------------------------------------


def test_audit_reports_clean_campaign(tmp_path, capsys):
    run_dir = tmp_path / "run"
    main(["run", "P5", "--run-dir", str(run_dir), *FAST_FLAGS])

    rc = main(["audit", "--run-dir", str(run_dir)])
    assert rc == 0
    assert "audit OK" in capsys.readouterr().out


def test_audit_returns_1_for_missing_cas_blob(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.ledger.add_artifact(Artifact(
        id="a" * 64,
        kind="report",
        problem="P5",
        title="missing",
        content_path="b" * 64,
        status=Status.HEURISTIC,
    ))
    state.close()

    rc = main(["audit", "--run-dir", str(run_dir)])
    assert rc == 1
    assert "artifact_blob_missing" in capsys.readouterr().out


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
    state = CampaignState.load(run_dir)
    state.close()

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


def test_inspection_commands_do_not_mutate_campaign(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.close()
    before = _tree_snapshot(run_dir)

    commands = (
        ["status", "--run-dir", str(run_dir)],
        ["audit", "--run-dir", str(run_dir)],
        ["gates", "--run-dir", str(run_dir), "list"],
        ["report", "--run-dir", str(run_dir)],
    )
    for argv in commands:
        assert main(argv) == 0
        capsys.readouterr()

    assert _tree_snapshot(run_dir) == before


# -- argparse-level usage errors (SystemExit(2), left to argparse) ---------------


def test_missing_run_dir_is_argparse_usage_error():
    with pytest.raises(SystemExit) as exc_info:
        main(["status"])
    assert exc_info.value.code == 2


def test_no_command_is_argparse_usage_error():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


# -- reverify ---------------------------------------------------------------------


def test_reverify_dry_run_on_campaign_without_lean_artifacts(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.close()
    rc = main(["reverify", "--run-dir", str(run_dir), "--dry-run"])
    assert rc == 0
    assert "reverify: 0 lean artifact(s) [dry run]" in capsys.readouterr().out


def test_reverify_missing_ledger_is_an_error(tmp_path, capsys):
    rc = main(["reverify", "--run-dir", str(tmp_path / "nope")])
    assert rc == 1
    assert "does not exist" in capsys.readouterr().err


# -- p3-optimize ------------------------------------------------------------------


def test_p3_optimize_writes_results_and_ingests(tmp_path, capsys):
    run_dir = tmp_path / "run"
    out = tmp_path / "opt.json"
    rc = main(["p3-optimize", "--run-dir", str(run_dir), "--k", "0", "--m", "4",
               "--target", "p_avg", "--restarts", "2", "--max-iter", "120",
               "--out", str(out), "--ingest"])
    assert rc == 0
    text = capsys.readouterr().out
    assert "p3-optimize k=0 m=4 p_avg: best=0.5" in text
    assert "at HEURISTIC" in text and "at CERTIFIED" in text
    import json

    data = json.loads(out.read_text())
    assert data["results"][0]["exact"]["p_avg"] == "1/2"
    rc = main(["status", "--run-dir", str(run_dir)])
    assert rc == 0
    assert "CERTIFIED: 1" in capsys.readouterr().out


def test_p3_ingest_results_re_verifies_from_a_saved_file(tmp_path, capsys):
    run_dir = tmp_path / "run"
    out = tmp_path / "opt.json"
    assert main(["p3-optimize", "--run-dir", str(run_dir), "--k", "0", "--m", "4",
                 "--target", "p_avg", "--restarts", "2", "--max-iter", "120",
                 "--out", str(out)]) == 0
    capsys.readouterr()
    rc = main(["p3-ingest-results", "--run-dir", str(run_dir), "--results", str(out)])
    assert rc == 0
    text = capsys.readouterr().out
    assert "at HEURISTIC" in text and "at CERTIFIED" in text
    # idempotent: a second ingest adds no artifacts
    assert main(["p3-ingest-results", "--run-dir", str(run_dir), "--results", str(out)]) == 0
    main(["status", "--run-dir", str(run_dir)])
    status = capsys.readouterr().out
    assert "CERTIFIED: 1" in status and "HEURISTIC: 1" in status
