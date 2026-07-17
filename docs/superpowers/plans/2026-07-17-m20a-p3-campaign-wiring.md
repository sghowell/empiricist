# M20a: P3 Campaign Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** The model-facing campaign layer for P3 — screen, ledger ingestion, an iterative
search loop, and the searcher role — so Fable can attack `p*(k)` questions through the
reviewed M19 verification stack.

**Architecture:** Mirrors the two proven patterns in this repo. The *screen* is P5's
`ScreenReject` gate: convert `BellSchemeOut` → `BellScheme` and enforce resource caps BEFORE
the verifier, so malformed or DoS-sized schemes never reach physics. The *loop* is M18's
`FormalizeLoop` shape: propose → gate → structured feedback → revise, with early stop on
target achievement. The *ingestion* is the P5 convention: verifiers write nothing; the
ingest helper content-hashes the scheme JSON into the CAS and records the `EvidenceRow`
(verifier identity = `P3SchemeVerifier`'s name/version/binary_hash) — PASS enters at
`VERIFIED_N` (two-engine agreement is machine evidence).

**Tech stack:** Python ≥3.11, existing harness modules only (no new dependencies).

**Design decisions (locked):**
1. **Caps** (the reviewed compute-DoS item): `n_modes ≤ 12`, total photons `k+2 ≤ 6`, mesh
   length ≤ 64 elements, ancilla superposition ≤ 32 terms. At those caps Engine A ≈ 1.5 s
   worst-case per Bell state — acceptable; anything bigger is `ScreenReject`, not FAIL.
2. **INVALID also screens.** The loop treats verifier verdict `INVALID` as a screen-class
   event (skip + feedback), never an alarm; `ERROR` aborts the loop immediately (F3).
3. **Ingestion status:** PASS → `VERIFIED_N` with the full success vector + leakage in the
   evidence details. Claims recorded verbatim (the declared budget is part of the claim).
   Artifact id = content hash of the canonical scheme JSON (dedup across rounds for free).
4. **The searcher iterates one scheme per round** (k=1, like the formalizer): structured
   feedback (achieved vector, leakage, verdict) beats blind resampling for interferometer
   design; wave-parallel search (k>8) is deferred until the loop is proven live.

**File structure:**
- Create: `src/empiricist/search/p3_screen.py` — caps + `screen_scheme` (ScreenReject gate)
  (search layer, NOT domain: the screen imports both llm schemas and domain conversion, and
  M19's layering rule is that domain never imports llm — same reason search/schemas.py owns
  to_construction)
- Create: `src/empiricist/domain/p3/ingest.py` — `ingest_scheme_artifact`
- Create: `src/empiricist/search/p3_loop.py` — `P3SearchTask`, `P3SearchReport`, `P3SearchLoop`
- Modify: `src/empiricist/llm/roles.py` — add `"p3_searcher"`
- Test: `tests/test_p3_screen.py`, `tests/test_p3_ingest.py`, `tests/test_p3_search_loop.py`

---

### Task 1: Screen (`screen.py`)

**Files:** Create `src/empiricist/search/p3_screen.py`; Test `tests/test_p3_screen.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_p3_screen.py
import numpy as np
import pytest

from empiricist.search.p3_screen import (
    MAX_ANCILLA_TERMS,
    MAX_MESH_ELEMENTS,
    MAX_MODES,
    MAX_PHOTONS,
    screen_scheme,
)
from empiricist.search.schemas import ScreenReject


def _bsm_dict(**overrides):
    d = {
        "n_modes": 4,
        "n_ancilla_photons": 0,
        "ancilla": [],
        "mesh": [
            {"kind": "bs", "i": 0, "j": 2, "theta": np.pi / 4, "phi": 0.0},
            {"kind": "bs", "i": 1, "j": 3, "theta": np.pi / 4, "phi": 0.0},
        ],
        "claimed_p_avg": 0.5,
    }
    d.update(overrides)
    return d


def test_screen_accepts_standard_bsm():
    scheme = screen_scheme(_bsm_dict())
    assert scheme.n_modes == 4


def test_screen_rejects_oversize_modes():
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=MAX_MODES + 1))


def test_screen_rejects_photon_dos():
    # a valid-looking but compute-DoS ancilla: photons over cap
    anc = [{"pattern": [MAX_PHOTONS + 1], "re": 1.0, "im": 0.0}]
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=5, n_ancilla_photons=MAX_PHOTONS + 1, ancilla=anc))


def test_screen_rejects_oversize_mesh():
    els = [{"kind": "phase", "i": 0, "j": 0, "theta": 0.1, "phi": 0.0}] * (MAX_MESH_ELEMENTS + 1)
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(mesh=els))


def test_screen_rejects_oversize_ancilla_terms():
    terms = [{"pattern": [1, 0], "re": 1.0, "im": 0.0}] * (MAX_ANCILLA_TERMS + 1)
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=6, n_ancilla_photons=1, ancilla=terms))


def test_screen_rejects_invalid_scheme_as_screenreject():
    # validation failures (here: schema-invalid extra field is NOT the screen's job,
    # but a converter-level ValueError IS): unnormalized ancilla
    anc = [{"pattern": [1, 0], "re": 0.5, "im": 0.0}]
    with pytest.raises(ScreenReject):
        screen_scheme(_bsm_dict(n_modes=6, n_ancilla_photons=1, ancilla=anc))
```

- [ ] **Step 2: Run, confirm fail** (module not found).
- [ ] **Step 3: Implement**

```python
# src/empiricist/search/p3_screen.py
"""The P3 screen: caps + conversion BEFORE the verifier (P5's ScreenReject discipline).

Model output is never trusted: a schema-valid `BellSchemeOut` can still be a
compute DoS (a valid 50-photon ancilla sends Ryser's permanent into 2^50
iterations) or a malformed scheme. The screen converts and caps FIRST, raising
`ScreenReject` so the campaign loop skips (never halts, never verifies).

Caps are sized so the worst case inside them stays ~1.5 s per Bell state on
Engine A (n_modes=12, 6 photons); everything outside is rejected unexamined.
"""

from __future__ import annotations

from empiricist.domain.p3.scheme import BellScheme, scheme_from_out
from empiricist.llm.schemas import BellSchemeOut
from empiricist.search.schemas import ScreenReject

MAX_MODES = 12
MAX_PHOTONS = 4          # ancilla photons k; total photons = k + 2 <= 6
MAX_MESH_ELEMENTS = 64
MAX_ANCILLA_TERMS = 32


def screen_scheme(raw: dict) -> BellScheme:
    """Parse, cap, and convert a raw model-emitted dict into a validated BellScheme.

    Raises ScreenReject on ANY defect: schema violation, cap violation, or
    conversion/validation failure. Never raises anything else.
    """
    try:
        out = BellSchemeOut.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError and friends
        raise ScreenReject(f"schema: {exc}") from exc
    if out.n_modes > MAX_MODES:
        raise ScreenReject(f"n_modes {out.n_modes} exceeds cap {MAX_MODES}")
    if out.n_ancilla_photons > MAX_PHOTONS:
        raise ScreenReject(
            f"n_ancilla_photons {out.n_ancilla_photons} exceeds cap {MAX_PHOTONS}"
        )
    if len(out.mesh) > MAX_MESH_ELEMENTS:
        raise ScreenReject(f"mesh length {len(out.mesh)} exceeds cap {MAX_MESH_ELEMENTS}")
    if len(out.ancilla) > MAX_ANCILLA_TERMS:
        raise ScreenReject(f"ancilla terms {len(out.ancilla)} exceed cap {MAX_ANCILLA_TERMS}")
    # belt-and-braces: pattern-level photon cap even if n_ancilla_photons lies
    for term in out.ancilla:
        if sum(term.pattern) > MAX_PHOTONS:
            raise ScreenReject("ancilla pattern photon count exceeds cap")
    try:
        return scheme_from_out(out)
    except (ValueError, TypeError) as exc:
        raise ScreenReject(f"invalid scheme: {exc}") from exc
```

NOTE: the search-layer placement is deliberate — `domain/` never imports `llm` (M19 rule;
`scheme_from_out` duck-types for exactly this reason). Mirror how `search/schemas.py`'s
`to_construction` is structured.

- [ ] **Step 4: Run tests + `uv run ruff check src tests`, pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): screen gate with resource caps"`

### Task 2: Ingestion (`ingest.py`)

**Files:** Create `src/empiricist/domain/p3/ingest.py`; Test `tests/test_p3_ingest.py`

MANDATORY FIRST STEP: read `src/empiricist/ledger/ingest.py` (ingest_artifact signature),
`src/empiricist/ledger/models.py` (EvidenceRow, Status, Verdict), and how
`src/empiricist/search/loop.py` records evidence for verified constructions (the
exact-upgrade path) — mirror that convention precisely.

- [ ] **Step 1: Write the failing tests** — use tmp_path ledger+store fixtures in the style
      of existing ledger tests (grep tests/ for `Ledger(` fixtures):

```python
# tests/test_p3_ingest.py  (adapt fixture style to the repo's existing ledger tests)
def test_ingest_pass_scheme_lands_verified_n(tmp_ledger, tmp_store):
    scheme_json = {...}  # the standard BSM dict from test_p3_screen, claimed_p_avg 0.5
    result = verify_scheme_agreed(screen_scheme(scheme_json), claimed_p_avg=0.5)
    assert result.verdict == "PASS"
    art = ingest_scheme_artifact(tmp_ledger, tmp_store, scheme_json=scheme_json,
                                 result=result, title="k=0 standard BSM at p_avg 1/2")
    stored = tmp_ledger.get_artifact(art.id)
    assert stored.status.value == "VERIFIED_N"
    # evidence row carries the verifier identity + the physics
    evs = tmp_ledger.get_evidence(art.id)          # adapt to the real API name
    assert any(e.verifier == "p3_scheme_agreed" for e in evs)


def test_ingest_refuses_non_pass(tmp_ledger, tmp_store):
    result = verify_scheme_agreed(screen_scheme(scheme_json), claimed_p_avg=0.99)
    assert result.verdict == "FAIL"
    with pytest.raises(ValueError):
        ingest_scheme_artifact(tmp_ledger, tmp_store, scheme_json=scheme_json,
                               result=result, title="nope")


def test_ingest_is_idempotent_on_same_scheme(tmp_ledger, tmp_store):
    # same canonical JSON -> same artifact id -> second ingest returns existing artifact
    a1 = ingest_scheme_artifact(...)
    a2 = ingest_scheme_artifact(...)
    assert a1.id == a2.id
```

- [ ] **Step 2: Run, fail.** 
- [ ] **Step 3: Implement** `ingest_scheme_artifact(ledger, store, *, scheme_json: dict,
      result: AgreedResult, title: str, run_id: str | None = None) -> Artifact`:
      refuse (ValueError) unless `result.verdict == "PASS"`; canonicalize the scheme JSON
      (`json.dumps(..., sort_keys=True)`) as the CAS content; artifact kind `"construction"`,
      problem `"P3"`, status `VERIFIED_N`; artifact_id = the content hash convention used by
      `ingest_artifact` (let it derive; pass artifact_id only if the P5 dedup pattern
      requires); then `ledger.record_evidence(EvidenceRow(artifact_id=..., verifier=
      P3SchemeVerifier's name, verifier_version=its version, binary_hash=its binary_hash
      (instantiate `P3SchemeVerifier()` fresh), verdict=Verdict.PASS, details={success
      vector, p_min, p_avg, leakage, claims}), new_status=Status.VERIFIED_N)`. Handle the
      duplicate-ingest case the way `search/conjecture.py`'s submit() does (short-circuit
      return of the existing artifact, no second evidence row).
- [ ] **Step 4: Tests + ruff pass.**
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): scheme ingestion to VERIFIED_N"`

### Task 3: The search loop (`p3_loop.py`)

**Files:** Create `src/empiricist/search/p3_loop.py`; Test `tests/test_p3_search_loop.py`

MANDATORY FIRST STEP: read `src/empiricist/formalize/loop.py` in full (the shape to mirror:
constructor, run(), the complete() call contract, run_id naming, NO_ARTIFACT rounds,
history) and `tests/test_formalize_loop.py` (the fake-client test pattern — mirror it).

- [ ] **Step 1: Write the failing tests** with a FakeClient (mirroring test_formalize_loop's):
      (a) a client that emits the standard-BSM dict claiming p_avg 0.5 on round 1 → loop
      returns ok=True in 1 round, artifact ingested at VERIFIED_N, report carries the
      achieved vector; (b) a client emitting a FAILing claim (0.99) then the good scheme →
      2 rounds, feedback string for round 2 contains the achieved p_avg and "FAIL";
      (c) a client emitting screen-rejected garbage (oversize modes) then the good scheme →
      screened round counted, loop continues; (d) a client whose scheme triggers verifier
      ERROR (monkeypatch verify to return ERROR) → loop ABORTS immediately with
      report.f3_alarm True; (e) NO_ARTIFACT (client returns None) rounds counted, loop
      continues to max_rounds then ok=False.
- [ ] **Step 2: Run, fail.**
- [ ] **Step 3: Implement:**

```python
# src/empiricist/search/p3_loop.py  (shape; mirror formalize/loop.py's conventions exactly)
@dataclass(frozen=True)
class P3SearchTask:
    name: str                 # run_id component; MUST be fresh per campaign run
    goal: str                 # the question, e.g. "find a k=0 scheme with p_min >= 1/2"
    context: str              # domain context block for the prompt
    target_p_min: float | None = None
    target_p_avg: float | None = None
    max_leakage: float = 0.0  # the declared budget the loop verifies claims against


@dataclass(frozen=True)
class P3SearchReport:
    ok: bool
    rounds: int
    artifact_id: str | None
    best: dict | None         # best scheme JSON seen (by target metric), even if not ok
    best_report: ... | None   # its SchemeReport-shaped summary (success vector etc.)
    f3_alarm: bool
    history: list[tuple[str, str]]   # (outcome, detail) per round: PASS/FAIL/INVALID/SCREENED/NO_ARTIFACT/ERROR


class P3SearchLoop:
    def __init__(self, client, ledger, store, *, max_rounds: int = 12): ...
    async def run(self, task: P3SearchTask) -> P3SearchReport:
        # per round: prompt = task.goal + task.context + feedback-so-far (+ best-so-far vector)
        # result = await self._client.complete(ROLES["p3_searcher"], prompt,
        #     schema=BellSchemeOut, ledger=self._ledger, run_id=f"p3search-{task.name}-r{n}")
        # None/unparsable -> NO_ARTIFACT round.
        # screen_scheme(raw) -> ScreenReject -> SCREENED round, feedback = the reject reason.
        # verify_scheme_agreed(scheme, claimed_p_min=task.target_p_min,
        #     claimed_p_avg=task.target_p_avg, claimed_max_leakage=task.max_leakage)
        #   PASS  -> ingest_scheme_artifact(...); return ok report.
        #   FAIL  -> feedback = achieved success vector + leakage + which claim missed;
        #            track best-so-far by the target metric.
        #   INVALID -> treat as SCREENED-class (skip + feedback).
        #   ERROR -> return immediately with f3_alarm=True (the caller stops the world).
```
      Feedback strings must be CONCRETE: the per-state success vector, p_min/p_avg achieved,
      leakage, and (on screen rejects) the reject reason — the model designs interferometers
      from this signal.
- [ ] **Step 4: Tests + ruff pass** (also rerun all p3 + formalize test files — no regression).
- [ ] **Step 5: Commit** — `git commit -m "feat(p3): iterative search loop (propose-screen-verify-ingest)"`

### Task 4: The searcher role

**Files:** Modify `src/empiricist/llm/roles.py`; extend `tests/test_p3_search_loop.py`

- [ ] **Step 1: Test** — `ROLES["p3_searcher"]` exists, active, k == 1; the loop uses it.
- [ ] **Step 2: Add the role** (mirroring the formalizer entry's style):

```python
    "p3_searcher": Role(
        name="p3_searcher",
        system_prompt=(
            "You are the P3 Searcher: you design ancilla-boosted linear-optical Bell "
            "measurements as beamsplitter meshes. You emit ONE scheme per round in the "
            "bell_scheme schema: n_modes, an ancilla Fock superposition on modes 4.., a "
            "mesh of bs(i, j, theta, phi) and phase(i, alpha) elements, and your claimed "
            "metrics. Dual-rail encoding: qubit A rails 0,1; qubit B rails 2,3. The "
            "harness verifies every claim with two independent engines and reports the "
            "achieved per-Bell-state success vector back to you; claims are checked "
            "exactly, so claim what you can defend, and declare a leakage budget only "
            "when you intend nonzero leakage. Design from interference physics, not "
            "random tweaking: reason about which detection patterns distinguish which "
            "Bell states before emitting. Iterate on the feedback."
        ),
        effort=Effort.HIGH, k=1, active=True,
    ),
```
- [ ] **Step 3: Tests + ruff; full fast-suite sanity** (`-m "not slow and not slow_lean"`).
- [ ] **Step 4: Commit** — `git commit -m "feat(p3): searcher role"`

---

## Acceptance for the milestone
1. Fast suite green (solo run), ruff clean.
2. The loop's fake-client tests demonstrate all six outcome paths (PASS/FAIL/SCREENED/
   INVALID/NO_ARTIFACT/ERROR-abort).
3. Grep-check: nothing outside the screen imports `BellSchemeOut` into the verify path —
   the loop's only path to a `BellScheme` is `screen_scheme`.
4. No change to `verifiers/lean.py`, no new subprocess call sites.

## Out of scope (M20b+)
- The live campaign scripts and spend posture (launched separately, with user sign-off).
- Wave-parallel search (k>1), population/elites, conjecture mining on p*(k) data.
- The SOS/SDP certificate pipeline and exact-arithmetic layer.
