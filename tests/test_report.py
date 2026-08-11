"""Tests for the M7 T3 auditable report (`report.py`): every content-contract
section (spec §12) present, per-role aggregates matching hand-inserted `runs`
rows, and the acceptance check -- every promoted (>=VERIFIED_N) claim's
provenance block names a CAS digest that actually exists in the store plus
at least one evidence row with a verifier+binary_hash. Offline, FakeLLMClient,
the same small (tier0_n=5, tier1_n=4) config test_campaign_moves.py uses.
"""

from __future__ import annotations

import asyncio
import re

import pytest

from empiricist import report
from empiricist.campaign.moves import conjecture_move, ensure_enumerate, search_move
from empiricist.campaign.state import CampaignState
from empiricist.config import RunConfig
from empiricist.ledger.models import (
    Artifact,
    Certification,
    Claim,
    EvidenceRow,
    Run,
    Status,
    Verdict,
)
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult

FAST_CFG = RunConfig(tier0_n=5, tier1_n=4, search_target_n=5, targets_per_gen=8)


def run(coro):
    return asyncio.run(coro)


def make_result(parsed: dict | None) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use" if parsed else "end_turn",
        is_error=False, input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


TRUE_CONJECTURE = {
    "family": "path", "closed_form": "N-3",
    "predicted_values": {"3": 0, "4": 1, "5": 2}, "confidence": 0.9,
}
FALSE_CONJECTURE = {
    "family": "path", "closed_form": "N-2",
    "predicted_values": {"5": 4}, "confidence": 0.5,
}


@pytest.fixture()
def campaign(tmp_path):
    """A small but non-trivial campaign: VERIFIED_N dataset, one CONJECTURED
    and one REFUTED statement artifact, one SEARCH generation event, a
    pending and a resolved gate, hand-inserted `runs` rows across two roles
    (FakeLLMClient never writes `runs` -- see llm/client.py), and a synthetic
    exact-upgrade + f3_alarm search_events row so the search summary section
    has real content to report."""
    state = CampaignState.load(tmp_path / "run")
    dataset = ensure_enumerate(state, FAST_CFG)

    true_client = FakeLLMClient([make_result(TRUE_CONJECTURE)])
    conjectured = run(conjecture_move(state, FAST_CFG, true_client))[0]
    false_client = FakeLLMClient([make_result(FALSE_CONJECTURE)])
    refuted = run(conjecture_move(state, FAST_CFG, false_client))[0]

    # One real SEARCH generation (all refusals -- exercises the loop's own
    # "generation" search_event without needing a real construction hit).
    run(search_move(state, FAST_CFG, FakeLLMClient([]), gen=1))

    # A second, synthetic generation event carrying an exact upgrade, in the
    # same shape SearchLoop.run_generation itself would log (dataclasses.
    # asdict(GenerationReport)) -- exercises the summary's exact_upgrades
    # count without needing to engineer a real construction hit.
    state.population.log_event(2, "generation", {
        "gen": 2, "sampled": 32, "no_artifact": 30, "screened_out": 0,
        "verify_fail": 0, "verify_error": 0, "inserted": 1, "duplicates": 1,
        "exact_upgrades": [["deadbeef" * 8, 5]], "screen_reasons": [],
    })
    state.population.log_event(2, "f3_alarm", {"disagreement": True})

    state.ledger.start_run(Run(run_id="s1", move="SAMPLE", role="searcher"))
    state.ledger.finish_run("s1", exit_code=0, wall_s=1.0,
                             tokens_in=1000, tokens_out=200, cost_usd=0.30)
    state.ledger.start_run(Run(run_id="s2", move="SAMPLE", role="searcher"))
    state.ledger.finish_run("s2", exit_code=0, wall_s=1.0,
                             tokens_in=500, tokens_out=100, cost_usd=0.10)
    state.ledger.start_run(Run(run_id="c1", move="SAMPLE", role="conjecturer"))
    state.ledger.finish_run("c1", exit_code=0, wall_s=1.0,
                             tokens_in=200, tokens_out=50, cost_usd=0.05)

    pending_gate = state.gates.open("PROOF_CAMPAIGN", artifact_id=conjectured.id, note="parked")
    resolved_gate = state.gates.open("RELEASE", artifact_id=dataset.id, note="ship it")
    state.gates.resolve(resolved_gate.id, approve=True, note="approved")

    yield state, FAST_CFG, {
        "dataset": dataset, "conjectured": conjectured, "refuted": refuted,
        "pending_gate": pending_gate, "resolved_gate": resolved_gate,
    }
    state.close()


def _extract_section(text: str, needle: str) -> str:
    """The '### ...' block containing `needle` in its heading line, up to
    (not including) the next '## ' or '### ' heading."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("### ") and needle in line)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("### "):
            end = i
            break
    return "\n".join(lines[start:end])


# -- header -----------------------------------------------------------------


def test_header_has_config_hash_env_and_total_spend(campaign):
    state, cfg, _arts = campaign
    text = report.generate(state, cfg)

    assert f"Config hash: `{cfg.config_hash()}`" in text
    assert "Environment: python" in text and "platform" in text
    spent = state.ledger.spent()
    assert f"${spent.cost_usd:.4f}" in text
    assert f"{spent.tokens_in} input tokens" in text
    assert f"{spent.tokens_out} output tokens" in text


def test_header_per_role_aggregates_match_runs_rows(campaign):
    state, cfg, _arts = campaign
    text = report.generate(state, cfg)

    aggs = {a.role: a for a in state.ledger.run_aggregates()}
    assert set(aggs) == {"searcher", "conjecturer"}
    for role, agg in aggs.items():
        row = (
            f"| {role} | {agg.run_count} | {agg.cost_usd:.4f} | "
            f"{agg.tokens_in} | {agg.tokens_out} |"
        )
        assert row in text
    # sanity on the actual numbers (hand-inserted in the fixture)
    assert aggs["searcher"].cost_usd == pytest.approx(0.40)
    assert aggs["searcher"].tokens_in == 1500
    assert aggs["conjecturer"].cost_usd == pytest.approx(0.05)


def test_generate_is_pure_and_deterministic_across_calls(campaign):
    """Same state, same cfg -> byte-identical report (a referee can
    regenerate it) -- generate() must not mutate the ledger/store."""
    state, cfg, _arts = campaign
    before = state.ledger.spent()
    first = report.generate(state, cfg)
    second = report.generate(state, cfg)
    assert first == second
    assert state.ledger.spent() == before


# -- claims table -------------------------------------------------------------


def test_claims_table_lists_every_artifact(campaign):
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    claims_section = text.split("## Claims")[1].split("## Provenance")[0]
    for art in arts["dataset"], arts["conjectured"], arts["refuted"]:
        assert art.id[:12] in claims_section

    dataset = state.ledger.get_artifact(arts["dataset"].id)
    assert (
        f"| `{dataset.id[:12]}` | P5 | p5-ghz3-v1 | dataset |"
        in claims_section
    )
    assert "VERIFIED_N" in claims_section
    assert str(dataset.status_n) in claims_section
    assert "exhaustive" in claims_section

    conjectured = state.ledger.get_artifact(arts["conjectured"].id)
    assert conjectured.status is Status.CONJECTURED
    refuted = state.ledger.get_artifact(arts["refuted"].id)
    assert refuted.status is Status.REFUTED


# -- provenance / acceptance check --------------------------------------------


def test_acceptance_every_promoted_claim_has_cas_digest_and_evidence(campaign):
    """The spec §12 acceptance check: every promoted (>=VERIFIED_N) claim's
    block names a CAS digest that exists in the store, plus at least one
    evidence row carrying a verifier + binary_hash."""
    state, cfg, _arts = campaign
    text = report.generate(state, cfg)

    promoted = [
        a for a in state.ledger.find_artifacts()
        if a.status.rank >= Status.VERIFIED_N.rank
    ]
    assert promoted  # the fixture's dataset artifact must be among them

    for art in promoted:
        section = _extract_section(text, art.id[:12])
        # CAS digest present AND actually resolvable in the store.
        assert art.content_path in section
        assert state.store.exists(art.content_path)
        # At least one evidence row: a "| verifier | version | `hash` | VERDICT | ..." line.
        evidence_rows = state.ledger.evidence_for(art.id)
        assert evidence_rows
        for ev in evidence_rows:
            assert ev.verifier in section
            assert ev.binary_hash[:12] in section


def test_provenance_section_lists_certifications_in_force(campaign):
    state, cfg, _arts = campaign
    text = report.generate(state, cfg)
    prov_section = text.split("## Provenance")[1]
    assert "stab_fusion" in prov_section
    assert "enum_fusion" in prov_section
    assert "PASS" in prov_section


def test_dataset_artifact_gets_a_provenance_block(campaign):
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    section = _extract_section(text, arts["dataset"].id[:12])
    assert "p5_tablebase_dataset_ingest" in section
    assert "PASS" in section


def test_no_provenance_blocks_for_sub_verified_n_artifacts(campaign):
    """CONJECTURED/REFUTED artifacts never get a '### statement: ...'
    provenance heading -- only >=VERIFIED_N claims do."""
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    prov_section = text.split("## Provenance")[1].split("## CONJECTURED")[0]
    assert arts["conjectured"].id[:12] not in prov_section
    assert arts["refuted"].id[:12] not in prov_section


def test_report_surfaces_canonical_claim_and_exact_evidence_links(tmp_path):
    state = CampaignState.load(tmp_path / "claim-bound")
    try:
        content = b"theorem checked : True := trivial"
        digest = state.store.put(content)
        artifact = Artifact(
            id=digest,
            kind="lean",
            problem="P5",
            problem_version="p5-ghz3-v1",
            title="Empiricist.checked",
            content_path=digest,
            status=Status.FORMALIZED,
            run_id="formalize-r1",
        )
        claim = Claim.create(
            artifact_id=artifact.id,
            problem=artifact.problem,
            problem_version=artifact.problem_version,
            statement="True",
            family="Empiricist.checked",
            metric="theorem",
            scope={"decl": "Empiricist.checked"},
        )
        state.ledger.start_run(
            Run(run_id="formalize-r1", move="SAMPLE", role="formalizer")
        )
        state.ledger.finish_run(
            "formalize-r1",
            exit_code=0,
            wall_s=1.0,
        )
        state.ledger.add_certification(Certification(
            verifier="lean",
            verifier_version="3.3",
            binary_hash="binary-current",
            golden_suite_hash="suite-current",
            verdict=Verdict.PASS,
        ))
        state.ledger.record_claimed_artifact(
            artifact,
            claim,
            EvidenceRow(
                artifact_id=artifact.id,
                claim_id=claim.id,
                run_id="formalize-r1",
                verifier="lean",
                verifier_version="3.3",
                binary_hash="binary-current",
                golden_suite_hash="suite-current",
                verdict=Verdict.PASS,
                details={"statement": "True"},
            ),
            expected_golden_suite_hash="suite-current",
        )

        text = report.generate(state, RunConfig())
        claims_section = text.split("## Claims")[1].split("## Provenance")[0]
        assert "### Canonical claim records" in claims_section
        assert claim.id[:12] in claims_section
        assert "p5-ghz3-v1" in claims_section
        assert "Empiricist.checked" in claims_section
        assert '{"decl":"Empiricist.checked"}' in claims_section

        provenance = _extract_section(text, artifact.id[:12])
        assert claim.id[:12] in provenance
        assert "formalize-r1"[:12] in provenance
        assert "suite-current"[:12] in provenance
        assert "| PASS | PASS |" in provenance
    finally:
        state.close()


# -- CONJECTURED / REFUTED -----------------------------------------------------


def test_conjectured_section_has_statement_and_falsification_effort(campaign):
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    section = text.split("## CONJECTURED")[1].split("## REFUTED")[0]
    assert arts["conjectured"].id[:12] in section
    assert '"family":"path"' in section or '"family": "path"' in section
    ev = state.ledger.evidence_for(arts["conjectured"].id)[0]
    checks = ev.details["checks"]
    assert f"{checks} check(s) survived" in section


def test_refuted_section_has_counterexample(campaign):
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    section = text.split("## REFUTED")[1].split("## Gates")[0]
    assert arts["refuted"].id[:12] in section
    ev = state.ledger.evidence_for(arts["refuted"].id)[0]
    counterexample = ev.details["counterexample"]
    assert counterexample in section


# -- gates --------------------------------------------------------------------


def test_gates_section_splits_pending_and_resolved(campaign):
    state, cfg, arts = campaign
    text = report.generate(state, cfg)
    gates_section = text.split("## Gates")[1].split("## Search summary")[0]
    pending_part, resolved_part = gates_section.split("### Resolved")

    assert arts["pending_gate"].id in pending_part
    assert "PROOF_CAMPAIGN" in pending_part

    assert arts["resolved_gate"].id in resolved_part
    assert "RELEASE" in resolved_part
    assert "approved" in resolved_part


# -- search summary -------------------------------------------------------------


def test_search_summary_counts_generations_population_upgrades_and_alarms(campaign):
    state, cfg, _arts = campaign
    text = report.generate(state, cfg)
    section = text.split("## Search summary")[1]

    events = state.population.events(trigger="generation")
    assert f"Generations run: {len(events)}" in section
    assert f"Population size: {state.population.count()}" in section
    assert "Exact upgrades: 1" in section
    assert re.search(r"f3_alarm: 1", section)


def test_empty_campaign_report_has_all_sections_and_no_crash(tmp_path):
    """A freshly-created (no ENUMERATE, no moves) run directory must still
    render every section -- generate() never assumes non-empty tables."""
    state = CampaignState.load(tmp_path / "empty")
    try:
        text = report.generate(state, RunConfig())
        for heading in (
            "# Empiricist Campaign Report", "## Claims", "## Provenance",
            "## CONJECTURED", "## REFUTED", "## Gates", "## Search summary",
        ):
            assert heading in text
    finally:
        state.close()
