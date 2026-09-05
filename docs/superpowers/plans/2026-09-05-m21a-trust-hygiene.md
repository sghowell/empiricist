# M21a: Trust Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three trust gaps the 2026-09-03 audit surfaced before any further P3
spend: (1) the 22 legacy FORMALIZED Lean artifacts in the P5 ledgers carry no evidence the
hardened gate can cross-check; (2) the CERTIFIED tier has never been populated — the exact
SOS checker has no ledger ingest path, so the k=0 ½ certificate lives only as a test golden;
(3) the P3 search loop discards every failed round's scheme (the k=1 all-four-identified
design was lost this way) and neither model loop recognises a rate-limited call.

**Architecture:** Three independent, additive changes. `reverify` re-runs the CURRENT
`LeanVerifier` over each FORMALIZED artifact's stored source and records a claim-bound
evidence row through the existing certification-gated transaction
(`record_claimed_artifact`), so the audit's `elevated_missing_certified_evidence` clears
only for artifacts that actually pass today's gate; a non-PASS is recorded as evidence
without demotion (the lattice cannot reduce rank, and REFUTED would be false). The
CERTIFIED path mirrors the Lean one exactly: a `Verifier` wrapping `check_certificate`
with its own mutation-resistant golden suite, `certify_with_suite` stamping, and a
`verify_and_ingest` transaction that re-derives the domain meaning (objective/constraint
polynomials) from `p3_targets` so a certificate can only certify the target it claims.
Loop robustness adds a per-round sink + log to the P3 loop and a shared throttle policy
(instant exit≠0 / 0 output tokens / <5 s wall ⇒ back off, retry, then abort the task)
to both model loops.

**Tech Stack:** Python ≥3.11, stdlib `fractions` (checker), blake3, pytest. No new
dependencies.

**Spec:** `docs/superpowers/specs/2026-07-06-empiricist-harness-design.md` §4.1 (status
lattice: CERTIFIED = general statement with a model-independent machine-checkable
certificate), §4.2 (statuses change only alongside evidence rows), §7 (verifier registry:
no evidence without a PASS certification stamp against the live golden suite), Appendix A
(`PRAGMA user_version=1`; v0 pilot ledgers migrate in place; read-only inspection leaves
them untouched).

## Global Constraints

- Nothing enters the ledger above HEURISTIC without machine evidence; REFUTED is terminal;
  status changes only alongside evidence rows (CLAUDE.md non-negotiables).
- Every elevated promotion routes through `record_claimed_artifact` (certification-gated)
  or `record_evidence(self_validating=True)` (self-validating) — `ledger/db.py`.
- `verifiers/lean.py` is NOT edited (its source is part of `LeanVerifier.binary_hash`;
  editing it invalidates every Lean certification stamp).
- `certificates/core.py` stays stdlib-only; no new imports there.
- The model never gets a shell; nothing in this plan calls a model.
- Commit messages: descriptive, no AI attribution. Branch `feat/m21a-trust-hygiene`,
  PR, squash-merge. Run `uv run ruff check src tests` and
  `uv run pytest -m "not slow and not slow_lean"` before every commit.

---

## File structure

| File | Responsibility |
|---|---|
| `src/empiricist/verifiers/reverify.py` (new) | `reverify_lean_artifacts`: re-verify FORMALIZED lean artifacts under the current gate; record claim-bound PASS evidence or evidence-only non-PASS. |
| `src/empiricist/cli.py` (modify) | `empiricist reverify --run-dir R [--dry-run] [--artifact ID…] [--timeout-s]` |
| `src/empiricist/certificates/goldens/p3_k0_standard_assignment.json` (moved from `tests/goldens/`) | The pinned k=0 exact certificate, now package data so the verifier's golden suite can load it. |
| `src/empiricist/certificates/verifier.py` (new) | `SOSCertificateVerifier` + `certificate_from_json` / `certificate_to_json`. |
| `src/empiricist/certificates/goldens.py` (new) | `SOS_GOLDEN_SUITE`, `sos_suite_hash()`, `certify_sos()`. |
| `src/empiricist/certificates/ingest.py` (new) | `P3_CERTIFICATE_TARGETS`, `verify_and_ingest_p3_certificate`, `ingest_p3_certificate` → CERTIFIED. |
| `src/empiricist/ledger/audit.py` (modify) | `_CERT_GATED_KINDS` gains `"certificate"`. |
| `src/empiricist/llm/throttle.py` (new) | `is_throttled_run`, `ThrottlePolicy`. |
| `src/empiricist/search/p3_loop.py` (modify) | `round_sink`, `rounds_log`, `throttled`, throttle retry. |
| `src/empiricist/formalize/loop.py` (modify) | throttle retry, `throttled` on the report. |
| `tests/test_reverify.py`, `tests/test_certificates_verifier.py`, `tests/test_certificates_ingest.py`, `tests/test_llm_throttle.py` (new); `tests/test_cli.py`, `tests/test_p3_search_loop.py`, `tests/test_formalize_loop.py`, `tests/test_p3_certificate_golden.py`, `tests/test_ledger_audit.py` (extend) | Tests. |

---

### Task 1: `reverify` — legacy FORMALIZED artifacts under the current gate

**Files:**
- Create: `src/empiricist/verifiers/reverify.py`
- Modify: `src/empiricist/cli.py` (parser at ~line 151, dispatch at ~line 567)
- Test: `tests/test_reverify.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `LeanVerifier` (`verifiers/lean.py`: `.name`, `.version`, `.binary_hash`,
  `.verify(source, *, decl, timeout_s)`), `_record_verified_lean_artifact` and
  `DEFAULT_LEAN_PROBLEM_VERSION` (`verifiers/lean.py`), `lean_suite_hash` / `certify_lean`
  (`verifiers/lean_goldens.py`), `Ledger.find_artifacts / get_certification /
  require_certification / record_evidence`, `Store.get`.
- Produces:
  ```python
  @dataclass(frozen=True)
  class ReverifyOutcome:
      artifact_id: str
      decl: str
      verdict: str    # "PASS" | "FAIL" | "ERROR" | "TIMEOUT" | "SKIPPED"
      detail: str

  @dataclass(frozen=True)
  class ReverifyReport:
      outcomes: tuple[ReverifyOutcome, ...]
      certified_now: bool   # True iff this pass issued a new certification stamp
      dry_run: bool
      @property
      def ok(self) -> bool  # every outcome is PASS (a dry run is never ok)

  def reverify_lean_artifacts(
      ledger: Ledger, store: Store, *, verifier=None, artifact_ids=None,
      dry_run: bool = False, certify: bool = True, timeout_s: float = 600.0,
  ) -> ReverifyReport
  ```

- [ ] **Step 1: Write the failing tests**

`tests/test_reverify.py`:

```python
"""Re-verification of legacy FORMALIZED Lean artifacts under the current gate."""
from __future__ import annotations

from blake3 import blake3
import pytest

from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import (
    Artifact, Certification, EvidenceRow, Status, Verdict,
)
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.lean_goldens import lean_suite_hash
from empiricist.verifiers.reverify import reverify_lean_artifacts


class _StubLean:
    """LeanVerifier-shaped stub: PASS unless the source contains `sorry`."""
    name = "lean"
    version = "9.9"
    binary_hash = "ab" * 32

    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify(self, module_source: str, *, decl: str, timeout_s: float = 600.0):
        self.calls.append(decl)
        if "sorry" in module_source:
            return VerifierResult(verdict=Verdict.FAIL, details={"gate": "compile"})
        statement = f"stmt:{decl}"
        return VerifierResult(verdict=Verdict.PASS, details={
            "decl": decl, "axioms": ["propext"], "statement": statement,
            "statement_hash": blake3(statement.encode()).hexdigest(),
        })


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    yield lg, st
    lg.close()


def _stamp(lg: Ledger, v: _StubLean) -> None:
    lg.add_certification(Certification(
        verifier=v.name, verifier_version=v.version, binary_hash=v.binary_hash,
        golden_suite_hash=lean_suite_hash(), verdict=Verdict.PASS,
    ))


def _legacy_formalized(lg: Ledger, st: Store, source: str, decl: str) -> Artifact:
    """A pre-hardening FORMALIZED row: PASS evidence without a golden_suite_hash."""
    digest = st.put(source.encode())
    art = Artifact(id=digest, kind="lean", problem="P5", problem_version="legacy",
                   title=decl, content_path=digest, status=Status.FORMALIZED)
    lg.add_artifact(art)
    lg.record_evidence(EvidenceRow(
        artifact_id=art.id, verifier="lean", verifier_version="3.2",
        binary_hash="cd" * 32, verdict=Verdict.PASS, details={"decl": decl},
    ))
    return art


def _flagged(lg, st, artifact_id) -> bool:
    return any(
        i.code == "elevated_missing_certified_evidence" and i.artifact_id == artifact_id
        for i in audit_ledger(lg, st).issues
    )


def test_reverify_pass_clears_audit_flag_and_keeps_status(env):
    lg, st = env
    v = _StubLean(); _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    assert _flagged(lg, st, art.id)

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)

    assert rep.ok and [o.verdict for o in rep.outcomes] == ["PASS"]
    assert v.calls == ["Empiricist.foo"]
    assert not _flagged(lg, st, art.id)
    assert lg.get_artifact(art.id).status is Status.FORMALIZED
    rows = lg.evidence_for(art.id)
    assert len(rows) == 2
    new = [r for r in rows if r.golden_suite_hash == lean_suite_hash()]
    assert len(new) == 1 and new[0].claim_id is not None
    assert lg.claims_for(art.id)[0].statement == "stmt:Empiricist.foo"


def test_reverify_fail_records_evidence_without_demotion(env):
    lg, st = env
    v = _StubLean(); _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem bad : 1 = 2 := by sorry", "Empiricist.bad")

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False)

    assert not rep.ok and rep.outcomes[0].verdict == "FAIL"
    assert lg.get_artifact(art.id).status is Status.FORMALIZED   # never demoted
    assert _flagged(lg, st, art.id)                              # still honest
    fails = [r for r in lg.evidence_for(art.id) if r.verdict is Verdict.FAIL]
    assert len(fails) == 1
    assert fails[0].details["reverify"] is True
    assert fails[0].golden_suite_hash == lean_suite_hash()


def test_reverify_dry_run_writes_nothing(env):
    lg, st = env
    v = _StubLean(); _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False, dry_run=True)

    assert rep.dry_run and not rep.ok
    assert [o.verdict for o in rep.outcomes] == ["SKIPPED"]
    assert v.calls == []
    assert len(lg.evidence_for(art.id)) == 1


def test_reverify_refuses_without_current_certification(env):
    lg, st = env
    v = _StubLean()
    _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    with pytest.raises(PromotionIntegrityError):
        reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    assert v.calls == []


def test_reverify_filters_by_artifact_id_and_skips_non_lean(env):
    lg, st = env
    v = _StubLean(); _stamp(lg, v)
    a = _legacy_formalized(lg, st, "theorem a : 1 = 1 := rfl", "Empiricist.a")
    _legacy_formalized(lg, st, "theorem b : 2 = 2 := rfl", "Empiricist.b")
    other = st.put(b"not lean")
    lg.add_artifact(Artifact(id=other, kind="report", problem="P5", title="r",
                             content_path=other, status=Status.HEURISTIC))

    rep = reverify_lean_artifacts(lg, st, verifier=v, certify=False, artifact_ids=[a.id])

    assert [o.decl for o in rep.outcomes] == ["Empiricist.a"]
    assert v.calls == ["Empiricist.a"]


def test_reverify_is_idempotent(env):
    lg, st = env
    v = _StubLean(); _stamp(lg, v)
    art = _legacy_formalized(lg, st, "theorem foo : 1 = 1 := rfl", "Empiricist.foo")
    reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    reverify_lean_artifacts(lg, st, verifier=v, certify=False)
    # record_claimed_artifact dedups identical PASS rows: still exactly one new row.
    assert len(lg.evidence_for(art.id)) == 2
```

`tests/test_cli.py` (append):

```python
def test_reverify_dry_run_on_campaign_without_lean_artifacts(tmp_path, capsys):
    run_dir = tmp_path / "run"
    state = CampaignState.load(run_dir)
    state.close()
    rc = main(["reverify", "--run-dir", str(run_dir), "--dry-run"])
    assert rc == 0
    assert "reverify: 0 lean artifact" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_reverify.py tests/test_cli.py -k reverify -v`
Expected: FAIL / ImportError on `empiricist.verifiers.reverify`.

- [ ] **Step 3: Implement `verifiers/reverify.py`**

```python
"""Re-verify FORMALIZED Lean artifacts under the CURRENT gate.

Why this exists: artifacts recorded before golden-suite-hash tracking carry PASS
evidence the audit cannot cross-check against a certification
(`elevated_missing_certified_evidence`). The only honest way to clear that flag is
to run today's certified `LeanVerifier` over the exact stored source and record a
claim-bound evidence row through the certification-gated transaction. A non-PASS
is recorded as evidence WITHOUT a status change: the lattice never reduces rank,
and REFUTED (terminal) would assert the theorem is false, which a gate change does
not show. The audit keeps flagging such rows -- that is the correct outcome.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from empiricist.ledger.db import Ledger
from empiricist.ledger.models import EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.lean import (
    DEFAULT_LEAN_PROBLEM_VERSION,
    LeanVerifier,
    _record_verified_lean_artifact,
)
from empiricist.verifiers.lean_goldens import certify_lean, lean_suite_hash


@dataclass(frozen=True)
class ReverifyOutcome:
    artifact_id: str
    decl: str
    verdict: str   # "PASS" | "FAIL" | "ERROR" | "TIMEOUT" | "SKIPPED"
    detail: str


@dataclass(frozen=True)
class ReverifyReport:
    outcomes: tuple[ReverifyOutcome, ...]
    certified_now: bool
    dry_run: bool

    @property
    def ok(self) -> bool:
        return (not self.dry_run) and all(o.verdict == "PASS" for o in self.outcomes)


def _targets(ledger: Ledger, artifact_ids: Iterable[str] | None):
    wanted = None if artifact_ids is None else set(artifact_ids)
    return [
        a for a in ledger.find_artifacts(kind="lean", status=Status.FORMALIZED)
        if wanted is None or a.id in wanted
    ]


def reverify_lean_artifacts(
    ledger: Ledger,
    store: Store,
    *,
    verifier=None,
    artifact_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    certify: bool = True,
    timeout_s: float = 600.0,
) -> ReverifyReport:
    """Re-run the current Lean gate over every FORMALIZED lean artifact.

    PASS -> a claim-bound evidence row pinned to the live golden suite (via the
    same transaction `ingest_lean_artifact` uses; the artifact keeps its id,
    content, and status). Non-PASS -> an evidence-only row (`details["reverify"]`)
    with no status change. `dry_run` lists targets and touches nothing.
    """
    v = verifier if verifier is not None else LeanVerifier()
    suite_hash = lean_suite_hash()
    targets = _targets(ledger, artifact_ids)
    if dry_run:
        return ReverifyReport(
            outcomes=tuple(
                ReverifyOutcome(a.id, a.title, "SKIPPED", "dry run") for a in targets
            ),
            certified_now=False,
            dry_run=True,
        )
    certified_now = False
    if targets and certify:
        cert = ledger.get_certification(v.name, v.version, v.binary_hash)
        if (
            cert is None
            or cert.verdict is not Verdict.PASS
            or cert.golden_suite_hash != suite_hash
        ):
            stamp = certify_lean(ledger, v)
            certified_now = True
            if stamp.verdict is not Verdict.PASS:
                raise RuntimeError(
                    "the current LeanVerifier FAILED its golden suite; refusing to "
                    "re-verify anything against an uncertified gate"
                )
    if targets:
        # Fail closed (PromotionIntegrityError) before touching any artifact.
        ledger.require_certification(v.name, v.version, v.binary_hash, suite_hash)
    outcomes: list[ReverifyOutcome] = []
    for art in targets:
        source = store.get(art.content_path).decode("utf-8")
        decl = art.title
        result = v.verify(source, decl=decl, timeout_s=timeout_s)
        if result.verdict is Verdict.PASS:
            _record_verified_lean_artifact(
                ledger, store, source, decl, result,
                verifier=v, suite_hash=suite_hash, problem=art.problem,
                problem_version=DEFAULT_LEAN_PROBLEM_VERSION, run_id=None,
            )
            outcomes.append(ReverifyOutcome(art.id, decl, "PASS", "re-verified"))
            continue
        details = {"reverify": True, **result.details}
        ledger.record_evidence(EvidenceRow(
            artifact_id=art.id, verifier=v.name, verifier_version=v.version,
            binary_hash=v.binary_hash, golden_suite_hash=suite_hash,
            verdict=result.verdict, details=details,
        ))
        gate = result.details.get("gate") or result.details.get("error") or ""
        outcomes.append(ReverifyOutcome(art.id, decl, result.verdict.value, str(gate)))
    return ReverifyReport(tuple(outcomes), certified_now, False)
```

CLI (`cli.py`): parser

```python
    reverify_p = sub.add_parser(
        "reverify",
        help="re-verify FORMALIZED Lean artifacts under the current gate (migrates a v0 ledger in place)",
    )
    reverify_p.add_argument("--run-dir", required=True, type=Path)
    reverify_p.add_argument("--dry-run", action="store_true")
    reverify_p.add_argument("--artifact", action="append", default=None,
                            help="restrict to these artifact ids (repeatable)")
    reverify_p.add_argument("--timeout-s", type=float, default=600.0)
```

command:

```python
def _cmd_reverify(args: argparse.Namespace) -> int:
    ledger_path = args.run_dir / "ledger.db"
    if not ledger_path.is_file():
        print(f"error: campaign ledger does not exist: {ledger_path}", file=sys.stderr)
        return 1
    ledger = Ledger(ledger_path)          # write mode: v0 -> v1 migration in place
    store = Store(args.run_dir / "store")
    try:
        report = reverify_lean_artifacts(
            ledger, store, artifact_ids=args.artifact, dry_run=args.dry_run,
            timeout_s=args.timeout_s,
        )
    finally:
        ledger.close()
    print(f"reverify: {len(report.outcomes)} lean artifact(s)"
          + (" [dry run]" if report.dry_run else "")
          + (" [certified LeanVerifier in this pass]" if report.certified_now else ""))
    for o in report.outcomes:
        print(f"{o.verdict}: {o.decl} artifact={o.artifact_id} {o.detail}")
    return 0 if (report.ok or (report.dry_run)) else 1
```

Dispatch: `if args.command == "reverify": return _cmd_reverify(args)`. Import
`reverify_lean_artifacts` at the top of `cli.py`.

- [ ] **Step 4: Run the tests, lint**

Run: `uv run pytest tests/test_reverify.py tests/test_cli.py -q && uv run ruff check src tests`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/empiricist/verifiers/reverify.py src/empiricist/cli.py tests/test_reverify.py tests/test_cli.py
git commit -m "Add reverify: re-run the current Lean gate over legacy FORMALIZED artifacts"
```

---

### Task 2: The CERTIFIED tier — SOS certificate verifier, golden suite, ingest

**Files:**
- Move: `tests/goldens/p3_k0_standard_assignment.json` → `src/empiricist/certificates/goldens/p3_k0_standard_assignment.json`
- Create: `src/empiricist/certificates/verifier.py`, `src/empiricist/certificates/goldens.py`, `src/empiricist/certificates/ingest.py`
- Modify: `src/empiricist/ledger/audit.py` (`_CERT_GATED_KINDS`), `tests/test_p3_certificate_golden.py` (path + use `certificate_from_json`)
- Test: `tests/test_certificates_verifier.py`, `tests/test_certificates_ingest.py`, `tests/test_ledger_audit.py`

**Interfaces:**
- Consumes: `SOSCertificate`, `check_certificate`, `Poly`, `Monomial` (`certificates/core.py`);
  `standard_assignment_objective`, `unitarity_constraints`, `unambiguity_constraints`
  (`certificates/p3_targets.py`); `certify_with_suite` (`verifiers/registry.py`);
  `record_claimed_artifact`.
- Produces:
  ```python
  # certificates/verifier.py
  def certificate_from_json(data: dict) -> SOSCertificate   # raises ValueError on shape
  def certificate_to_json(cert: SOSCertificate) -> dict     # canonical, string rationals
  class SOSCertificateVerifier:
      name = "sos_certificate"; version = "1.0"
      binary_hash -> str   # blake3 over core.py + p3_targets.py + verifier.py, read fresh
      def verify(self, cert: SOSCertificate) -> VerifierResult   # never raises
  # certificates/goldens.py
  SOS_GOLDEN_SUITE: list[tuple[SOSCertificate, Verdict]]
  def load_k0_golden() -> SOSCertificate
  def sos_suite_hash() -> str
  def certify_sos(ledger, verifier) -> Certification
  # certificates/ingest.py
  P3_CERTIFICATE_PROBLEM_VERSION = "p3-sos-certificate-v1"
  @dataclass(frozen=True)
  class CertificateTarget: name, n_modes, k, objective(), constraints(), statement, metric
  P3_CERTIFICATE_TARGETS: dict[str, CertificateTarget]   # "k0_standard_assignment_p_avg"
  def verify_and_ingest_p3_certificate(ledger, store, *, certificate_json, target, title, run_id=None) -> tuple[VerifierResult, Artifact | None]
  def ingest_p3_certificate(...) -> Artifact   # raises ValueError on non-PASS / wrong target
  ```

- [ ] **Step 1: Move the golden and write the failing tests**

```bash
mkdir -p src/empiricist/certificates/goldens
git mv tests/goldens/p3_k0_standard_assignment.json src/empiricist/certificates/goldens/
```

Edit `tests/test_p3_certificate_golden.py`: replace `GOLDEN_PATH`, `_mono`, `_poly`,
`_load_certificate` with

```python
from empiricist.certificates.goldens import load_k0_golden as _load_certificate
```

(keep every existing assertion).

`tests/test_certificates_verifier.py`:

```python
"""SOSCertificateVerifier + its golden suite (the CERTIFIED tier's trust boundary)."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from empiricist.certificates.core import SOSCertificate
from empiricist.certificates.goldens import (
    SOS_GOLDEN_SUITE, certify_sos, load_k0_golden, sos_suite_hash,
)
from empiricist.certificates.verifier import (
    SOSCertificateVerifier, certificate_from_json, certificate_to_json,
)
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Verdict


def _tiny(bound="0", gram=((Fraction(1),),), objective=None) -> SOSCertificate:
    # -x0^2 <= 0 with Q = [[1]]:  0 - (-x0^2) = x0^2 = b^T Q b, b = (x0)
    return SOSCertificate(
        statement="tiny", variables=("x0",),
        objective={(0, 0): Fraction(-1)} if objective is None else objective,
        bound=Fraction(bound), constraints=(), multipliers=(),
        gram_basis=((0,),), gram=gram,
    )


def test_verifier_passes_the_k0_golden():
    r = SOSCertificateVerifier().verify(load_k0_golden())
    assert r.verdict is Verdict.PASS and r.details["failure"] == ""


def test_verifier_fails_identity_psd_and_shape_mutants():
    v = SOSCertificateVerifier()
    assert v.verify(_tiny()).verdict is Verdict.PASS
    assert v.verify(_tiny(bound="-1")).details["failure"] == "identity"
    # x0^2 <= 0 with Q = [[-1]]: identity holds, Gram is not PSD
    psd = _tiny(objective={(0, 0): Fraction(1)}, gram=((Fraction(-1),),))
    assert v.verify(psd).details["failure"] == "psd"
    assert v.verify(replace(_tiny(), gram=())).details["failure"] == "shape"
    assert v.verify(None).verdict is Verdict.FAIL   # never raises


def test_json_round_trip_is_exact():
    cert = load_k0_golden()
    assert certificate_from_json(certificate_to_json(cert)) == cert
    assert certificate_to_json(cert)["bound"] == "1/2"


def test_suite_has_teeth_and_stable_hash():
    verdicts = [e for _, e in SOS_GOLDEN_SUITE]
    assert Verdict.PASS in verdicts and Verdict.FAIL in verdicts
    assert len(sos_suite_hash()) == 64 and sos_suite_hash() == sos_suite_hash()


def test_certify_sos_stamps_pass(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    try:
        v = SOSCertificateVerifier()
        cert = certify_sos(lg, v)
        assert cert.verdict is Verdict.PASS
        assert lg.get_certification(v.name, v.version, v.binary_hash).golden_suite_hash == sos_suite_hash()
    finally:
        lg.close()
```

`tests/test_certificates_ingest.py`:

```python
"""Certificate -> CERTIFIED ingestion (the first real content in that tier)."""
from __future__ import annotations

import pytest

from empiricist.certificates.goldens import certify_sos, load_k0_golden, sos_suite_hash
from empiricist.certificates.ingest import (
    P3_CERTIFICATE_TARGETS, ingest_p3_certificate, verify_and_ingest_p3_certificate,
)
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
from empiricist.ledger.audit import audit_ledger
from empiricist.ledger.db import Ledger, PromotionIntegrityError
from empiricist.ledger.models import Status, Verdict
from empiricist.store import Store

TARGET = "k0_standard_assignment_p_avg"


@pytest.fixture()
def env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db")
    st = Store(tmp_path / "store")
    certify_sos(lg, SOSCertificateVerifier())
    yield lg, st
    lg.close()


def test_golden_ingests_at_certified_with_claim_and_clean_audit(env):
    lg, st = env
    art = ingest_p3_certificate(
        lg, st, certificate_json=certificate_to_json(load_k0_golden()),
        target=TARGET, title="k=0 standard assignment p_avg <= 1/2",
    )
    assert art.status is Status.CERTIFIED and art.kind == "certificate"
    claim = lg.claims_for(art.id)[0]
    assert "1/2" in claim.statement and claim.scope["target"] == TARGET
    rows = lg.evidence_for(art.id)
    assert len(rows) == 1 and rows[0].golden_suite_hash == sos_suite_hash()
    assert audit_ledger(lg, st).ok


def test_ingest_is_idempotent(env):
    lg, st = env
    kw = dict(certificate_json=certificate_to_json(load_k0_golden()), target=TARGET, title="t")
    a = ingest_p3_certificate(lg, st, **kw)
    b = ingest_p3_certificate(lg, st, **kw)
    assert a.id == b.id and len(lg.evidence_for(a.id)) == 1


def test_wrong_target_is_refused_before_verification(env):
    lg, st = env
    data = certificate_to_json(load_k0_golden())
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=data, target="no_such_target", title="t")
    data["objective"] = {"": "0"}
    with pytest.raises(ValueError, match="does not encode"):
        ingest_p3_certificate(lg, st, certificate_json=data, target=TARGET, title="t")
    assert lg.find_artifacts() == []


def test_mutated_certificate_records_nothing(env):
    lg, st = env
    data = certificate_to_json(load_k0_golden())
    data["bound"] = "49/100"
    result, art = verify_and_ingest_p3_certificate(
        lg, st, certificate_json=data, target=TARGET, title="t")
    assert result.verdict is Verdict.FAIL and art is None
    assert lg.find_artifacts() == []


def test_uncertified_verifier_fails_closed(tmp_path):
    lg = Ledger(tmp_path / "ledger.db"); st = Store(tmp_path / "store")
    try:
        with pytest.raises(PromotionIntegrityError):
            ingest_p3_certificate(
                lg, st, certificate_json=certificate_to_json(load_k0_golden()),
                target=TARGET, title="t")
    finally:
        lg.close()


def test_target_registry_names_the_k0_problem():
    t = P3_CERTIFICATE_TARGETS[TARGET]
    assert t.n_modes == 4 and t.k == 0 and "U(4)" in t.statement
```

`tests/test_ledger_audit.py` (append): a CERTIFIED `certificate`-kind artifact whose only
PASS evidence lacks `golden_suite_hash` must be flagged `elevated_missing_certified_evidence`
(mirror the existing lean-kind test in that file).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_certificates_verifier.py tests/test_certificates_ingest.py tests/test_p3_certificate_golden.py tests/test_ledger_audit.py -q`
Expected: ImportError on the new modules.

- [ ] **Step 3: Implement `certificates/verifier.py`**

```python
"""SOSCertificateVerifier: the `Verifier` wrapping `certificates.core.check_certificate`.

Same shape as `verifiers/p3_scheme.py` / `LeanVerifier`: a name/version/binary_hash
identity whose stamp dies the instant the checker's source changes, a total
`verify()` that never raises, and its own golden suite (`certificates/goldens.py`)
certified through `certify_with_suite`. The checker's arithmetic is the trust
boundary; this class only gives it a ledger identity.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from blake3 import blake3

from empiricist.certificates.core import Monomial, Poly, SOSCertificate, check_certificate
from empiricist.ledger.models import Verdict
from empiricist.verifiers.base import VerifierResult

_CERT_DIR = Path(__file__).resolve().parent
_HASHED_SOURCE_FILES = ("core.py", "p3_targets.py", "verifier.py")


def _mono_key(mono: Monomial) -> str:
    return ",".join(str(i) for i in mono)


def _mono_from_key(key: str) -> Monomial:
    return tuple(int(x) for x in key.split(",")) if key else ()


def _poly_to_json(p: Poly) -> dict[str, str]:
    return {_mono_key(m): str(c) for m, c in sorted(p.items())}


def _poly_from_json(d: Any) -> Poly:
    if not isinstance(d, dict):
        raise ValueError("polynomial must be a JSON object")
    return {_mono_from_key(k): Fraction(v) for k, v in d.items()}


def certificate_to_json(cert: SOSCertificate) -> dict:
    """Canonical JSON form (all rationals as strings; the golden file's format)."""
    return {
        "statement": cert.statement,
        "variables": list(cert.variables),
        "objective": _poly_to_json(cert.objective),
        "bound": str(cert.bound),
        "constraints": [_poly_to_json(c) for c in cert.constraints],
        "multipliers": [_poly_to_json(m) for m in cert.multipliers],
        "gram_basis": [list(m) for m in cert.gram_basis],
        "gram": [[str(v) for v in row] for row in cert.gram],
    }


def certificate_from_json(data: Any) -> SOSCertificate:
    """Inverse of `certificate_to_json`. Raises ValueError on any shape defect
    (the ingest path maps that to a refusal; the checker itself never sees it)."""
    try:
        return SOSCertificate(
            statement=str(data["statement"]),
            variables=tuple(str(v) for v in data["variables"]),
            objective=_poly_from_json(data["objective"]),
            bound=Fraction(data["bound"]),
            constraints=tuple(_poly_from_json(c) for c in data["constraints"]),
            multipliers=tuple(_poly_from_json(m) for m in data["multipliers"]),
            gram_basis=tuple(tuple(int(i) for i in m) for m in data["gram_basis"]),
            gram=tuple(tuple(Fraction(v) for v in row) for row in data["gram"]),
        )
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError(f"malformed certificate JSON: {type(exc).__name__}: {exc}") from exc


class SOSCertificateVerifier:
    name = "sos_certificate"
    version = "1.0"

    @property
    def binary_hash(self) -> str:
        h = blake3()
        for fname in _HASHED_SOURCE_FILES:
            h.update((_CERT_DIR / fname).read_bytes())
        return h.hexdigest()

    def applicable(self, kind: str) -> bool:
        return kind == "certificate"

    def verify(self, cert: Any) -> VerifierResult:
        """PASS iff the exact checker accepts `cert`. Total: `check_certificate`
        never raises and reports malformed input as failure="shape"."""
        res = check_certificate(cert)
        details = {"failure": res.failure, "detail": res.detail}
        if res.ok:
            details["bound"] = str(cert.bound)
            details["gram_dim"] = len(cert.gram_basis)
            details["n_constraints"] = len(cert.constraints)
            return VerifierResult(verdict=Verdict.PASS, details=details)
        return VerifierResult(verdict=Verdict.FAIL, details=details)
```

- [ ] **Step 4: Implement `certificates/goldens.py`**

```python
"""SOS_GOLDEN_SUITE: SOSCertificateVerifier's mutation-resistant certification suite.

Cases (certificate, expected verdict):
1. the pinned k=0 standard-assignment certificate (bound exactly 1/2) -> PASS
2. a tiny true certificate  (-x^2 <= 0, Q=[[1]])                      -> PASS
3. the k=0 golden with its bound lowered to 49/100 (identity breaks)  -> FAIL
4. x^2 <= 0 with Q=[[-1]] (identity holds, Gram not PSD)              -> FAIL
5. a shape-broken certificate (empty Gram for a 1-element basis)      -> FAIL
Cases 3-5 fail through three DIFFERENT checker branches (identity/psd/shape).
`sos_suite_hash()` pins every stamp to this exact suite content.
"""
from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from blake3 import blake3

from empiricist.certificates.core import SOSCertificate
from empiricist.certificates.verifier import (
    SOSCertificateVerifier, certificate_from_json, certificate_to_json,
)
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Certification, Verdict
from empiricist.verifiers.base import VerifierResult
from empiricist.verifiers.registry import certify_with_suite

_K0_GOLDEN_PATH = Path(__file__).resolve().parent / "goldens" / "p3_k0_standard_assignment.json"


def load_k0_golden() -> SOSCertificate:
    return certificate_from_json(json.loads(_K0_GOLDEN_PATH.read_text()))


def _tiny_true() -> SOSCertificate:
    return SOSCertificate(
        statement="-x0^2 <= 0", variables=("x0",), objective={(0, 0): Fraction(-1)},
        bound=Fraction(0), constraints=(), multipliers=(),
        gram_basis=((0,),), gram=((Fraction(1),),),
    )


def _not_psd() -> SOSCertificate:
    return replace(_tiny_true(), statement="x0^2 <= 0 (bogus)",
                   objective={(0, 0): Fraction(1)}, gram=((Fraction(-1),),))


_K0 = load_k0_golden()

SOS_GOLDEN_SUITE: list[tuple[SOSCertificate, Verdict]] = [
    (_K0, Verdict.PASS),
    (_tiny_true(), Verdict.PASS),
    (replace(_K0, bound=Fraction(49, 100)), Verdict.FAIL),
    (_not_psd(), Verdict.FAIL),
    (replace(_tiny_true(), gram=()), Verdict.FAIL),
]


def sos_suite_hash() -> str:
    payload = json.dumps(
        [[certificate_to_json(c), v.value] for c, v in SOS_GOLDEN_SUITE],
        sort_keys=True, separators=(",", ":"),
    )
    return blake3(payload.encode("utf-8")).hexdigest()


def certify_sos(ledger: Ledger, verifier: SOSCertificateVerifier) -> Certification:
    def run(v: SOSCertificateVerifier, cert: SOSCertificate) -> VerifierResult:
        return v.verify(cert)
    return certify_with_suite(ledger, verifier, SOS_GOLDEN_SUITE, run,
                              golden_suite_hash=sos_suite_hash())
```

- [ ] **Step 5: Implement `certificates/ingest.py`**

```python
"""Certificate -> CERTIFIED ingestion (spec 4.1: a GENERAL statement with a
model-independent machine-checkable certificate).

Two gates, in order: (1) DOMAIN MEANING -- the certificate's objective and
constraint polynomials must EQUAL the ones `p3_targets` derives for the declared
target (the checker verifies algebra only; this is where "these constraints are
unitarity, this objective is p_avg" is pinned); (2) the certified exact checker.
Only then is the artifact/claim/evidence transaction committed at CERTIFIED.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from blake3 import blake3

from empiricist.certificates.core import Poly, SOSCertificate
from empiricist.certificates.goldens import sos_suite_hash
from empiricist.certificates.p3_targets import (
    standard_assignment_objective, unambiguity_constraints, unitarity_constraints,
)
from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_from_json
from empiricist.ledger.db import Ledger
from empiricist.ledger.models import Artifact, Claim, EvidenceRow, Status, Verdict
from empiricist.store import Store
from empiricist.verifiers.base import VerifierResult

P3_CERTIFICATE_PROBLEM_VERSION = "p3-sos-certificate-v1"


@dataclass(frozen=True)
class CertificateTarget:
    name: str
    n_modes: int
    k: int
    objective: Callable[[], Poly]
    constraints: Callable[[], list[Poly]]
    statement: str      # format() with bound=<rational string>
    metric: str


P3_CERTIFICATE_TARGETS: dict[str, CertificateTarget] = {
    "k0_standard_assignment_p_avg": CertificateTarget(
        name="k0_standard_assignment_p_avg", n_modes=4, k=0,
        objective=lambda: standard_assignment_objective(4),
        constraints=lambda: unitarity_constraints(4) + unambiguity_constraints(4),
        statement=(
            "For every passive interferometer U in U(4) acting on the ancilla-free "
            "dual-rail Bell pair, the standard-assignment average Bell-identification "
            "probability p_avg is at most {bound} (exact SOS certificate on the "
            "unitarity variety)."
        ),
        metric="p_avg_upper_bound",
    ),
}


def _canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _check_target(cert: SOSCertificate, target: str) -> CertificateTarget:
    spec = P3_CERTIFICATE_TARGETS.get(target)
    if spec is None:
        raise ValueError(f"certificate does not encode a known target: {target!r}")
    if cert.objective != spec.objective() or list(cert.constraints) != spec.constraints():
        raise ValueError(
            f"certificate does not encode the declared target {target!r}: its objective "
            "or constraint polynomials differ from p3_targets' definitions"
        )
    return spec


def verify_and_ingest_p3_certificate(
    ledger: Ledger, store: Store, *, certificate_json: dict, target: str, title: str,
    run_id: str | None = None,
) -> tuple[VerifierResult, Artifact | None]:
    cert = certificate_from_json(certificate_json)     # ValueError on shape
    spec = _check_target(cert, target)                 # ValueError on meaning
    verifier = SOSCertificateVerifier()
    suite_hash = sos_suite_hash()
    ledger.require_certification(verifier.name, verifier.version, verifier.binary_hash, suite_hash)
    result = verifier.verify(cert)
    if result.verdict is not Verdict.PASS:
        return result, None
    content = _canonical_json(certificate_json)
    digest = store.put(content)
    evidence_run_id = run_id
    if evidence_run_id is not None:
        try:
            ledger.get_run(evidence_run_id)
        except KeyError:
            evidence_run_id = None
    art = Artifact(
        id=blake3(content).hexdigest(), kind="certificate", problem="P3",
        problem_version=P3_CERTIFICATE_PROBLEM_VERSION, title=title,
        content_path=digest, status=Status.CERTIFIED, run_id=evidence_run_id,
    )
    bound = str(cert.bound)
    claim = Claim.create(
        artifact_id=art.id, problem=art.problem, problem_version=art.problem_version,
        statement=spec.statement.format(bound=bound), family=spec.name, metric=spec.metric,
        scope={"target": spec.name, "bound": bound, "n_modes": spec.n_modes, "k": spec.k},
    )
    evidence = EvidenceRow(
        artifact_id=art.id, claim_id=claim.id, run_id=evidence_run_id,
        verifier=verifier.name, verifier_version=verifier.version,
        binary_hash=verifier.binary_hash, golden_suite_hash=suite_hash,
        verdict=Verdict.PASS, details={**result.details, "target": spec.name},
    )
    stored = ledger.record_claimed_artifact(art, claim, evidence, expected_golden_suite_hash=suite_hash)
    return result, stored


def ingest_p3_certificate(
    ledger: Ledger, store: Store, *, certificate_json: dict, target: str, title: str,
    run_id: str | None = None,
) -> Artifact:
    result, art = verify_and_ingest_p3_certificate(
        ledger, store, certificate_json=certificate_json, target=target, title=title, run_id=run_id,
    )
    if art is None:
        raise ValueError(
            f"refusing to ingest a non-PASS certificate ({result.details.get('failure')}: "
            f"{result.details.get('detail')})"
        )
    return art
```

`ledger/audit.py`: `_CERT_GATED_KINDS = frozenset({"lean", "certificate"})` and extend
the comment ("`certificate` = exact SOS certificates checked by `SOSCertificateVerifier`").

- [ ] **Step 6: Run tests + lint; commit**

Run: `uv run pytest tests/test_certificates_verifier.py tests/test_certificates_ingest.py tests/test_p3_certificate_golden.py tests/test_ledger_audit.py tests/test_certificates_core.py -q && uv run ruff check src tests`

```bash
git add -A src/empiricist/certificates src/empiricist/ledger/audit.py tests/
git commit -m "Wire the CERTIFIED tier: SOS certificate verifier, golden suite, and P3 certificate ingest"
```

---

### Task 3: Loop robustness — per-round persistence and throttle backoff

**Files:**
- Create: `src/empiricist/llm/throttle.py`
- Modify: `src/empiricist/search/p3_loop.py`, `src/empiricist/formalize/loop.py`
- Test: `tests/test_llm_throttle.py`, `tests/test_p3_search_loop.py`, `tests/test_formalize_loop.py`

**Interfaces:**
- Consumes: `Run` (`ledger/models.py`: `exit_code`, `tokens_out`, `wall_s`), `Ledger.get_run`.
- Produces:
  ```python
  # llm/throttle.py
  THROTTLE_MAX_WALL_S = 5.0
  def is_throttled_run(run: Run) -> bool
  @dataclass(frozen=True)
  class ThrottlePolicy:
      base_s: float = 60.0; max_s: float = 900.0; max_attempts: int = 5
      def delay(self, attempt: int) -> float      # attempt >= 1; base*2^(attempt-1) capped
  # search/p3_loop.py
  P3SearchLoop(client, ledger, store, *, max_rounds=12, role=None,
               throttle: ThrottlePolicy | None = ThrottlePolicy(),
               sleep=asyncio.sleep, round_sink: Callable[[dict], None] | None = None)
  P3SearchReport(..., throttled: bool = False, rounds_log: list[dict] = field(default_factory=list))
      # rounds_log entry: {"round", "attempt", "run_id", "outcome", "detail", "scheme", "summary"}
  # formalize/loop.py
  FormalizeLoop(client, ledger, store, verifier, *, max_rounds=12,
                throttle: ThrottlePolicy | None = ThrottlePolicy(), sleep=asyncio.sleep)
  FormalizeReport(..., throttled: bool = False)
  ```

- [ ] **Step 1: Write the failing tests**

`tests/test_llm_throttle.py`:

```python
from empiricist.ledger.models import Run
from empiricist.llm.throttle import ThrottlePolicy, is_throttled_run


def _run(**kw) -> Run:
    base = dict(run_id="r", move="SAMPLE", exit_code=1, tokens_out=0, wall_s=0.4)
    base.update(kw)
    return Run(**base)


def test_throttle_signature():
    assert is_throttled_run(_run())
    assert not is_throttled_run(_run(exit_code=0))
    assert not is_throttled_run(_run(tokens_out=12))
    assert not is_throttled_run(_run(wall_s=30.0))
    assert not is_throttled_run(_run(exit_code=None))
    assert not is_throttled_run(_run(wall_s=None))


def test_policy_backoff_doubles_and_caps():
    p = ThrottlePolicy(base_s=60.0, max_s=900.0, max_attempts=5)
    assert [p.delay(a) for a in (1, 2, 3, 4, 5)] == [60.0, 120.0, 240.0, 480.0, 900.0]
```

`tests/test_p3_search_loop.py` (append; reuse `env`-style fixture, `_STUB_ROLE`,
`_bsm_dict`, `make_result`, `run` already in the file):

```python
class ThrottlingFakeClient(FakeLLMClient):
    """First `n_throttled` calls: open+close a runs row with the rate-limit
    signature (exit 1, 0 output tokens, sub-second wall) and return None."""
    def __init__(self, scripted, *, n_throttled):
        super().__init__(scripted)
        self.n_throttled = n_throttled
        self.run_ids: list[str] = []

    async def complete(self, role, prompt, *, session_id=None, system_prompt=None,
                       schema=None, run_id=None, ledger=None):
        self.run_ids.append(run_id)
        if self.n_throttled > 0:
            self.n_throttled -= 1
            ledger.start_run(Run(run_id=run_id, move="SAMPLE", role=role.name))
            ledger.finish_run(run_id, exit_code=1, wall_s=0.3, tokens_out=0)
            return None
        ledger.start_run(Run(run_id=run_id, move="SAMPLE", role=role.name))
        ledger.finish_run(run_id, exit_code=0, wall_s=5.0, tokens_out=100)
        return await super().complete(role, prompt, schema=schema, run_id=run_id, ledger=ledger)


def _certified_env(tmp_path):
    lg = Ledger(tmp_path / "ledger.db"); st = Store(tmp_path / "store")
    certify_p3(lg, P3SchemeVerifier())
    return lg, st


def test_throttled_call_backs_off_then_retries_same_round(tmp_path):
    lg, st = _certified_env(tmp_path)
    slept: list[float] = []
    async def fake_sleep(s): slept.append(s)
    client = ThrottlingFakeClient([make_result(_bsm_dict(claimed_p_avg=0.5))], n_throttled=2)
    loop = P3SearchLoop(client, lg, st, max_rounds=3, role=_STUB_ROLE,
                        throttle=ThrottlePolicy(base_s=1.0, max_s=4.0, max_attempts=4),
                        sleep=fake_sleep)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert rep.ok and rep.rounds == 1 and not rep.throttled
    assert slept == [1.0, 2.0]
    assert [r.split("-")[-1] for r in client.run_ids] == ["r1", "r1a2", "r1a3"]
    assert [e["outcome"] for e in rep.rounds_log] == ["THROTTLED", "THROTTLED", "PASS"]
    lg.close()


def test_throttle_exhaustion_aborts_task_without_alarm(tmp_path):
    lg, st = _certified_env(tmp_path)
    async def fake_sleep(s): pass
    client = ThrottlingFakeClient([], n_throttled=99)
    loop = P3SearchLoop(client, lg, st, max_rounds=5, role=_STUB_ROLE,
                        throttle=ThrottlePolicy(base_s=1.0, max_s=1.0, max_attempts=3),
                        sleep=fake_sleep)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert not rep.ok and rep.throttled and not rep.f3_alarm
    assert rep.rounds == 1 and len(client.run_ids) == 3
    assert rep.history[-1][0] == "THROTTLED"
    lg.close()


def test_round_sink_receives_every_round_including_failed_schemes(tmp_path):
    lg, st = _certified_env(tmp_path)
    seen: list[dict] = []
    client = FakeLLMClient([make_result(_bsm_dict(claimed_p_avg=0.9)),
                            make_result(_bsm_dict(claimed_p_avg=0.5))])
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE, round_sink=seen.append)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert rep.ok
    assert [e["outcome"] for e in seen] == ["FAIL", "PASS"]
    assert seen[0]["scheme"]["mesh"] == _bsm_dict()["mesh"]     # the FAILED scheme survives
    assert seen[0]["summary"]["p_avg"] == pytest.approx(0.5)
    assert rep.rounds_log == seen
    lg.close()


def test_no_throttle_policy_keeps_legacy_no_artifact_behaviour(tmp_path):
    lg, st = _certified_env(tmp_path)
    client = ThrottlingFakeClient([], n_throttled=99)
    loop = P3SearchLoop(client, lg, st, max_rounds=2, role=_STUB_ROLE, throttle=None)
    rep = run(loop.run(P3SearchTask(name="t", goal="g", context="c", target_p_avg=0.5)))
    assert [h[0] for h in rep.history] == ["NO_ARTIFACT", "NO_ARTIFACT"] and not rep.throttled
    lg.close()
```

`tests/test_formalize_loop.py` (append, same `ThrottlingFakeClient` idea with
`LeanModuleOut`-shaped results and the file's `FakeVerifier`/`pass_result`): one test that
two throttled attempts precede a PASS with `slept == [1.0, 2.0]`, and one that exhaustion
yields `report.throttled is True`, `final_verdict == "THROTTLED"`, `ok is False`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_llm_throttle.py tests/test_p3_search_loop.py tests/test_formalize_loop.py -q`
Expected: ImportError / TypeError on the new keyword arguments.

- [ ] **Step 3: Implement `llm/throttle.py`**

```python
"""Rate-limit recognition for the model loops.

The documented signature of a throttled Claude Code call (M9/M20 operational
notes): the process exits non-zero almost instantly with zero output tokens.
Churning rounds against it wastes the round budget; the loops instead back off
and retry the SAME round, then abort the task (never an F3 alarm) once the
policy's attempts are exhausted.
"""
from __future__ import annotations

from dataclasses import dataclass

from empiricist.ledger.models import Run

THROTTLE_MAX_WALL_S = 5.0


def is_throttled_run(run: Run) -> bool:
    return (
        run.exit_code not in (0, None)
        and run.tokens_out == 0
        and run.wall_s is not None
        and run.wall_s < THROTTLE_MAX_WALL_S
    )


@dataclass(frozen=True)
class ThrottlePolicy:
    base_s: float = 60.0
    max_s: float = 900.0
    max_attempts: int = 5

    def delay(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt is 1-based")
        return min(self.max_s, self.base_s * (2 ** (attempt - 1)))
```

- [ ] **Step 4: Modify `search/p3_loop.py`**

Constructor: add `throttle: ThrottlePolicy | None = ThrottlePolicy()`,
`sleep: Callable[[float], Awaitable[None]] = asyncio.sleep`,
`round_sink: Callable[[dict], None] | None = None`; store them. Report: add
`throttled: bool = False` and `rounds_log: list[dict] = field(default_factory=list)`
(both with defaults so existing constructor calls keep working). In `run()` replace the
`for round_num ...` body's call section with an attempt loop:

```python
        rounds_log: list[dict] = []

        def _log(round_num, attempt, rid, outcome, detail, scheme=None, summary=None):
            entry = {"round": round_num, "attempt": attempt, "run_id": rid,
                     "outcome": outcome, "detail": detail, "scheme": scheme, "summary": summary}
            rounds_log.append(entry)
            if self._round_sink is not None:
                self._round_sink(entry)

        for round_num in range(1, self._max_rounds + 1):
            base_rid = f"p3search-{task.name}-{run_nonce}-r{round_num}"
            prompt = self.build_prompt(task, history, best_summary)
            attempt = 1
            while True:
                rid = base_rid if attempt == 1 else f"{base_rid}a{attempt}"
                result = await self._client.complete(
                    role, prompt, schema=BellSchemeOut, ledger=self._ledger, run_id=rid,
                )
                if result is not None and result.has_artifact:
                    break
                throttled = self._throttle is not None and self._is_throttled(rid)
                if not throttled:
                    history.append(_Round("NO_ARTIFACT", _NO_ARTIFACT_FEEDBACK))
                    _log(round_num, attempt, rid, "NO_ARTIFACT", _NO_ARTIFACT_FEEDBACK)
                    result = None
                    break
                _log(round_num, attempt, rid, "THROTTLED", "rate-limited call; backing off")
                if attempt >= self._throttle.max_attempts:
                    history.append(_Round("THROTTLED", "provider rate limit persisted; task aborted"))
                    return P3SearchReport(
                        ok=False, rounds=round_num, artifact_id=None, best=best,
                        best_summary=best_summary, f3_alarm=False,
                        history=[(rr.outcome, rr.detail) for rr in history],
                        throttled=True, rounds_log=rounds_log,
                    )
                await self._sleep(self._throttle.delay(attempt))
                attempt += 1
            if result is None:
                continue
            raw = result.parsed
            ...  # existing SCREENED / PASS / FAIL / INVALID / ERROR branches, each
                 # followed by _log(round_num, attempt, rid, <outcome>, <detail>, scheme=raw,
                 # summary=<dict or None>) and every returned report carrying
                 # rounds_log=rounds_log (throttled=False).
```

with the helper

```python
    def _is_throttled(self, rid: str) -> bool:
        try:
            run_row = self._ledger.get_run(rid)
        except KeyError:
            return False
        return is_throttled_run(run_row)
```

Summary dicts passed to `_log` on PASS/FAIL are the same
`{"success_by_state", "p_min", "p_avg", "leakage"}` shape as `best_summary`.

- [ ] **Step 5: Modify `formalize/loop.py`**

Same constructor additions (`throttle`, `sleep`), `throttled: bool = False` on
`FormalizeReport`, and the same attempt loop around `self._client.complete(...)` with
run ids `formalize-{task.name}-{run_nonce}-r{n}` / `...r{n}a{attempt}`; on exhaustion
append `_Round(verdict="THROTTLED", gate=None, feedback="provider rate limit persisted")`
and return `FormalizeReport(ok=False, rounds=round_num, artifact_id=None,
final_verdict="THROTTLED", final_gate=None, recorded_statement=None, recorded_axioms=None,
decl=last_decl, module_source=last_module_source, history=..., throttled=True)`.

- [ ] **Step 6: Run the full fast suite + lint; commit**

Run: `uv run pytest -m "not slow and not slow_lean" -q && uv run ruff check src tests`

```bash
git add src/empiricist/llm/throttle.py src/empiricist/search/p3_loop.py src/empiricist/formalize/loop.py tests/
git commit -m "Persist every P3 search round and back off on rate-limited model calls"
```

---

### Task 4: Campaign actions (after the PR merges; no code)

- [ ] **4.1** `uv run empiricist reverify --run-dir runs/p5-formalize` (migrates v0→v1 in
  place, certifies LeanVerifier v3.3 in that ledger, re-verifies 20 artifacts; expect
  ~30–60 min). Then the same for `runs/p5-live`. Record per-artifact outcomes in the
  science note; re-run `empiricist audit` on both and paste the tallies.
- [ ] **4.2** Ingest the k=0 certificate into `runs/p3-campaign`:
  ```bash
  uv run python -c "
  from pathlib import Path
  from empiricist.ledger.db import Ledger; from empiricist.store import Store
  from empiricist.certificates.goldens import certify_sos, load_k0_golden
  from empiricist.certificates.verifier import SOSCertificateVerifier, certificate_to_json
  from empiricist.certificates.ingest import ingest_p3_certificate
  lg = Ledger('runs/p3-campaign/ledger.db'); st = Store('runs/p3-campaign/store')
  certify_sos(lg, SOSCertificateVerifier())
  a = ingest_p3_certificate(lg, st, certificate_json=certificate_to_json(load_k0_golden()),
      target='k0_standard_assignment_p_avg',
      title='P3 k=0: standard-assignment p_avg <= 1/2 for all U in U(4) (exact SOS)')
  print(a.id, a.status); lg.close()"
  uv run empiricist status --run-dir runs/p3-campaign   # expect CERTIFIED: 1
  ```
- [ ] **4.3** Update `docs/science/` with a short hygiene note (outcomes, tallies) and the
  memory file; the M21b plan (deterministic tier + exact witnesses) follows.

## Self-review

- Spec coverage: §4.1 CERTIFIED (Task 2), §4.2 evidence-only rows for non-PASS (Task 1),
  §7 stamp-gated verify (Tasks 1–2 `require_certification`), Appendix A in-place
  migration (Task 1 CLI opens `Ledger` in write mode). Loop persistence/throttle is
  operational hardening called for in the M20b notes.
- Types: `ReverifyOutcome.verdict` is a `str` (`Verdict.value` or `"SKIPPED"`);
  `rounds_log` entries are plain dicts; `ThrottlePolicy.delay(attempt)` is 1-based in
  both loops.
- Placeholders: Task 3 Step 4 elides the unchanged PASS/FAIL/INVALID/ERROR branches on
  purpose (they exist in the file); each must gain a `_log` call and `rounds_log=`.
