"""End-to-end FormalizeLoop test against the REAL LeanVerifier (M18),
`slow_lean`-marked and skipped when the pinned lake/lean toolchain isn't
available (mirrors `test_lean_verifier.py`'s gating). A `FakeLLMClient`
scripted with a canned, trivially-true module stands in for the model -- this
proves the full propose -> gate -> ingest chain (round 1 PASS -> FORMALIZED
artifact) without a real model call.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from empiricist.formalize.loop import FormalizeLoop, FormalizeTask
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Status
from empiricist.llm.client import FakeLLMClient
from empiricist.llm.models import LLMResult
from empiricist.store import Store
from empiricist.verifiers.lean import LeanVerifier

_PROJECT_DIR = Path(__file__).resolve().parents[1] / "lean" / "EmpiricistLean"

_lake_available = (
    shutil.which("lake") is not None
    and shutil.which("lean") is not None
    and (_PROJECT_DIR / "lake-manifest.json").exists()
)

slow_lean = pytest.mark.slow_lean
requires_lake = pytest.mark.skipif(
    not _lake_available, reason="lake/lean toolchain or the pinned project is not available"
)


# No import at all -- `True`/`trivial` are core Lean builtins. Mirrors
# `verifiers/lean_goldens.py`'s `_TRUE_STATEMENT_SOURCE` golden case
# deliberately: pulling in `import Mathlib` for a statement that doesn't need
# it would load the full pinned mathlib olean set, multiplying this smoke
# test's RSS footprint for no reason.
_CANNED_MODULE = (
    "namespace Empiricist\n"
    "theorem loop_smoke : True := trivial\n"
    "end Empiricist\n"
)
_CANNED_DECL = "Empiricist.loop_smoke"


@pytest.fixture(scope="session", autouse=True)
def _warm_lean_toolchain():
    """Build the `axiom_audit` driver ONCE per session, outside any per-case
    timeout (mirrors test_lean_verifier.py's fixture) -- a cold cache must not
    flake this single integration case."""
    if not _lake_available:
        yield
        return
    asyncio.run(LeanVerifier()._ensure_ready_async())
    yield


def make_result(parsed: dict) -> LLMResult:
    return LLMResult(
        text="", parsed=parsed, stop_reason="tool_use", is_error=False,
        input_tokens=1, output_tokens=1, cache_read_tokens=0,
        cache_creation_tokens=0, cost_usd=0.0, duration_ms=1,
        session_id="s", uuid="u", model="claude-fable-5",
    )


@slow_lean
@requires_lake
def test_real_verifier_end_to_end_pass_ingests_formalized(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    verifier = LeanVerifier()
    client = FakeLLMClient([
        make_result({"module_source": _CANNED_MODULE, "decl": _CANNED_DECL, "notes": "smoke"})
    ])
    loop = FormalizeLoop(client, lg, st, verifier, max_rounds=1)

    report = asyncio.run(
        loop.run(FormalizeTask(
            name="loop-smoke", goal="Prove True.", context="No dependencies needed.",
        ))
    )

    assert report.ok is True, report.history
    assert report.rounds == 1
    assert report.final_verdict == "PASS"
    assert report.recorded_statement == "True"
    assert report.artifact_id is not None

    art = lg.get_artifact(report.artifact_id)
    assert art.status == Status.FORMALIZED
    assert art.kind == "lean"

    evidence = lg.evidence_for(report.artifact_id)
    assert len(evidence) == 1
    assert evidence[0].verifier == "lean"
    lg.close()
