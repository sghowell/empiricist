# M24a: the pack boundary — `empiricist.packs`, the `ftfbqc` manifest, pack verifiers in the claim ledger

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Charter §5 made concrete as far as the cosmology port demands: a fixed pack namespace `empiricist.packs.<name>` whose manifest declares a domain's verifiers and golden suites; the claim ledger (`certify-verifier`, `promote`, `reverify`, `check`) resolves a verifier by name from a research repository's own declarations first and from installed packs second; `ftfbqc` is the first pack (a manifest over today's P3/P5 verifiers with v1 evidence adapters; the code is not physically moved yet). Two further packs, `cosmology` (M24b) and `zx` (M24c), are built against this API by parallel streams; a pack landing without touching core is the boundary's proof.

**Architecture:** `packs/__init__.py` holds the protocol and the registry: `PackVerifier` (`name`, `version`, `binary_hash`, `verify_bytes(payload) -> VerifierResult`, `run(evidence_rel)` reading the file from the repository, `golden_suite() -> list[GoldenCase]`), `PackManifest(name, version, verifiers={name: factory(repo)})`, `load_pack(name)` by import of `empiricist.packs.<name>` (a pack whose optional dependencies are missing loads as absent, never as an error), `resolve_pack_verifier(repo, name)`, `pack_identity(name)`, `certify_pack_verifier(repo, name)`. Core never imports a pack module statically; the CLI, config, roles, schemas and report carry no new domain names (the existing P3/P5 CLI verbs stay until the physical extraction, recorded as debt).

**Tech Stack:** Python 3.11+, pydantic 2 (registry), pytest; optional dependency groups per pack.

**Spec:** charter `docs/superpowers/specs/2026-09-04-empiricist-v1-charter.md` §5 (Registry and packs), §9 row 2026-10-02.

## Global Constraints

- Core imports no pack; a pack imports core freely. Pack discovery is by fixed name, no plugin system.
- Registry rule unchanged: a verifier produces evidence only under a PASS stamp for its exact (name, version, binary_hash) against the golden suite it was certified with.
- Verifier names are global across a repository's declarations and installed packs; a declaration shadows a pack verifier of the same name (the research repository is the authority on what it runs).
- Nothing rises above HEURISTIC without a PASS from a certified verifier; `check` runs no verifiers.
- No AI attribution in commit messages. Branch `feat/m24a-packs` off `main`.

---

### Task 1: `empiricist.packs` — protocol, manifest, registry, certification

**Files:**
- Create: `src/empiricist/packs/__init__.py`
- Modify: `src/empiricist/claims/registry.py` (`VerifierStamp.pack: str | None = None`)
- Test: `tests/test_packs.py`

**Interfaces (produced):**
```python
@dataclass(frozen=True)
class GoldenCase:
    label: str
    payload: bytes
    expected: Verdict

class PackVerifier(Protocol):
    name: str
    version: str
    @property
    def binary_hash(self) -> str: ...
    def verify_bytes(self, payload: bytes) -> VerifierResult: ...   # total: never raises
    def run(self, evidence_rel: str) -> VerifierResult: ...          # reads <repo>/<evidence_rel>
    def golden_suite(self) -> list[GoldenCase]: ...

@dataclass(frozen=True)
class PackManifest:
    name: str
    version: str
    verifiers: dict[str, Callable[[Path], PackVerifier]]   # factory takes the repository root
    problems: dict[str, str] = field(default_factory=dict)  # problem id -> frozen version

PACK_NAMES = ("ftfbqc", "cosmology", "zx")
class PackError(Exception)
def load_pack(name: str) -> PackManifest | None          # None: unknown name or missing optional deps
def installed_packs() -> dict[str, PackManifest]
def resolve_pack_verifier(repo, name) -> PackVerifier | None   # PackError on a name two packs declare
def pack_of(name) -> str | None
def pack_identity(name) -> tuple[str, str] | None         # (version, binary_hash) of the live pack verifier
def golden_suite_hash(cases: list[GoldenCase]) -> str      # sha256 over (label, sha256(payload), expected)
def certify_pack_verifier(repo, name, *, allow_downgrade=False) -> tuple[VerifierStamp | None, list[str]]
class BytesFileVerifier:  # helper base: run() = read file -> verify_bytes(); ERROR on unreadable
```

- [ ] **Step 1: failing tests** in `tests/test_packs.py` with a fake pack injected through `monkeypatch.setattr(packs, "installed_packs", lambda: {"toy": manifest})`: resolve by name; `pack_identity`; `certify_pack_verifier` stamps PASS iff every golden case matches (a must-FAIL case that PASSes certifies nothing; the stamp records `pack="toy"` and the suite hash); `load_pack("nope") is None`; a pack whose import raises `ImportError` loads as None; two packs declaring one name raise `PackError`.
- [ ] **Step 2: run → FAIL. Step 3: implement. Step 4: `uv run pytest tests/test_packs.py tests/test_claims_registry.py -p no:warnings`. Step 5: commit** `M24a: empiricist.packs — protocol, manifest, registry, certification`.

---

### Task 2: the claim ledger resolves pack verifiers

**Files:**
- Modify: `src/empiricist/claims/promote.py` (`_resolve_verifier`: declaration first, then `resolve_pack_verifier`; `_require_current_stamp` checks `golden_suite_hash(v.golden_suite())` for pack verifiers; `reverify` resolves the same way), `src/empiricist/claims/check.py` (`drifted_verifiers`: `identity_for(name)` = built-in, else pack), `src/empiricist/verifiers/builtin.py` (`identity_for`), `src/empiricist/cli.py` (`claims certify-verifier` dispatches declaration → command, else pack; new `claims packs` lists installed packs and their verifiers)
- Test: `tests/test_claims_promote.py` (promote + reverify a claim on a fake pack verifier; a declaration of the same name shadows it), `tests/test_claims_check.py` (pack drift → STALE), `tests/test_cli.py` (`claims packs`, `certify-verifier` on a pack verifier)

- [ ] Steps 1–5. Commit `M24a: certify-verifier, promote, reverify and check resolve pack verifiers`.

---

### Task 3: the `ftfbqc` pack manifest

**Files:**
- Create: `src/empiricist/packs/ftfbqc/__init__.py` (`MANIFEST`), `src/empiricist/packs/ftfbqc/adapters.py`
- Test: `tests/test_packs_ftfbqc.py`

**Verifiers (v1 evidence adapters over the existing v0 verifiers; identities = the v0 identities so registry stamps stay comparable):**
- `sos_certificate`: payload = canonical certificate JSON → `SOSCertificateVerifier.verify(certificate_from_json(...))`; goldens from `SOS_GOLDEN_SUITE`.
- `p3_exact_witness`: payload = `{"witness", "claimed_success", "require_all_identified"}` (the stored artifact form) → `P3ExactVerifier.verify(...)`; goldens from `P3_EXACT_GOLDEN_SUITE`.
- `stab_fusion`, `enum_fusion`, `verify_agreed`: payload = `ConstructionOut` JSON → the engines (agreement: both keys equal and both PASS); goldens from `P5_GOLDEN_SUITE`.
- `problems`: `{"P3": P3 versions, "P5": "p5-ghz3-v1"}`.

- [ ] Test: the manifest loads; each verifier's golden suite certifies PASS in a temp repository; `promote` of a formulated claim to CERTIFIED on `sos_certificate` with the k0 golden certificate as evidence and a human receipt; `check` green; `identity_for("sos_certificate")` equals the pack identity (and `verifiers/builtin.py`'s direct lookups are removed in favour of the pack). Commit `M24a: the ftfbqc pack manifest with v1 evidence adapters`.

---

### Task 4: docs, CI, PR

- [ ] Charter §5 status note (what is factored, what is deferred: the physical move of `domain/`, `certificates/`, `search/`, `campaign/` under `packs/ftfbqc/`, and the P3/P5 CLI verbs), `docs/science/...` not needed (no science); plan outcome; memory.
- [ ] `uv run pytest -m "not slow_lean" -p no:warnings`, ruff, `claims check --repo . --min-claims 1`; PR; squash-merge after CI.

## Parallel streams (start after Task 1 lands on the branch)

- **M24b `cosmology`** (`docs/superpowers/plans/2026-09-07-m24b-cosmology-pack.md`): port death_and_gravity's P8(a) checker family (sympy + python-flint ball arithmetic; seven replay checkers) into `packs/cosmology/` with golden suites from the pinned certificates and mutated FAIL fixtures; then the Taylor-model / Krawczyk (P4 `validated`) and conic-dual (P9) checkers as far as time allows; optional dependency group `cosmology`; a cosmology claim promoted with a pack verifier and a receipt in death_and_gravity.
- **M24c `zx`** (`docs/superpowers/plans/2026-09-07-m24c-zx-pack.md`): the P6 pack — ZX diagrams over π/4 phases, the Jeandel–Perdrix–Vilmart ruleset, a derivation-replay verifier, a small-size semantic oracle, a critical-pair joinability checker, a termination-certificate checker; golden suites; manifest. No science runs in this milestone.

## Outcome (2026-09-07)

Tasks 1–4 done on `feat/m24a-packs`. Fast suite 1142 passed; ruff clean; `claims check --repo . --min-claims 1` green (86 claims) with the registry's `sos_certificate`, `p3_exact_witness` identities now resolved through the `ftfbqc` pack; `claims packs` lists the pack's five verifiers. Deferred as recorded debt (charter §5 status): the physical move of `domain/`, `certificates/`, `search/`, `campaign/` under `packs/ftfbqc/` and the P3/P5 CLI verbs. The cosmology (M24b) and zx (M24c) packs are being built against this API by parallel streams.
