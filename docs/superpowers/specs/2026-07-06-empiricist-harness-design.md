# Empiricist v0 — Implementation Design Spec

**Status:** draft v2 (post-review) for user sign-off · **Date:** 2026-07-06 · **Author:** Sean Howell + Claude (Opus 4.8)
**Companions:** `docs/empiricist_harness.md` (harness design v0.1), `docs/open_problems_ftfbqc.md` (the ten problems)

This spec makes the harness design doc *implementation-ready* and records decisions from brainstorming, a 7-brief research sweep, and a 4-lens adversarial review (consistency, completeness, P5-domain correctness, Claude-Code transport — the last verified against the installed `claude` v2.1.201). Where this spec and the companion harness doc disagree, **this spec wins**.

---

## 0. Definition of done

Empiricist v0 succeeds when a single `empiricist` process — Fable-5 (via Claude Code) *proposing*, harness-executed verifiers *checking* — produces **ledger promotions backed by machine-checkable artifacts** for **Problem 5 (minimum-fusion synthesis of graph states, `F(G)`, GHZ₃ model)**, plus an auto-generated report a referee could audit without trusting a line of model output.

v0 exit criteria:

1. A **`VERIFIED_N` dataset** of exact `F(G)` for **all connected graphs up to n = 9 (exhaustive); n = 10 best-effort/sampled** in the GHZ₃ model — *past the published 8-qubit frontier*. Each value's **upper bound** (achievability) is witnessed by a construction that **both** independent verifiers (A: stim tableau, B: GF(2)) confirm reaches `LC(G)`; each value's **lower bound** (minimality) comes from an exhaustive BFS whose minima are **independently re-derived by a second search implementation** over the golden range and are consistent with the `F ≥ N−3` floor and the Löbl caterpillar lower bound.
2. At least **three surviving `CONJECTURED` closed forms** for natural families (path, cycle, tree, grid), each having passed a budgeted auto-`ATTACK`.
3. At least one **`PROVED_DRAFT`** lemma-DAG surviving an independent Critic pass — produced when a human opens the proof gate (not autonomously overnight).
4. A **`FORMALIZED` scaffold**: a real `lean` verifier + pinned mathlib project that builds sorry-free and passes the axiom audit on a generic connected-graph lemma (`|E| ≥ N−1`). *An actual formalized `F(G)` theorem is out of v0.*
5. A **report generated purely from the ledger**, and a **live overnight campaign** actually run against Fable-5 (the machine-only inner loop, unattended).

The success metric is **status promotions per token**.

---

## 1. Locked decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | **Resource model** | **GHZ₃** (unbounded \|GHZ₃⟩ = 3-star = triangle). Our **own forward search** is ground truth; the Löbl caterpillar table is a **lower-bound cross-check only** (`F_cat ≤ F_GHZ3`), never golden data. | Matches the P5 statement + the `F ≥ N−3` framing; avoids the 32 GB pkl and silent mis-certification. |
| D2 | **Model access** | **Claude Code headless** (`claude -p`) as default transport, behind an injectable `LLMClient`. Subscription auth. `FakeLLMClient` for tests; `AnthropicAPIClient` documented for high fan-out / Batch discount (metered). | User directive. **Caveat (review):** subscription concurrency is ~low-teens (RSS + rate limits), not 16–64; k auto-tuned by preflight; true high fan-out needs the API client. |
| D3 | **Repo** | **Private** (already private). | Release is a deliberate human gate. |
| D4 | **Live campaign** | **Full overnight, machine-only inner loop, unattended**; uncapped by default with a *configurable* cap, preflight, cost visibility, hard resumability. PROVE/FORMALIZE are human-gated (parked), not run autonomously. | User directive + the docs' two-loop design (inner unattended, outer human-gated at 4 points). |
| D5 | **Equivalence** | "Same graph state" = **LC-orbit equality**. The dedup key everywhere is the **LC-orbit canonical key** = min pynauty iso-certificate over the graph's LC-orbit. Raw iso-keys are used only *inside* the LC-orbit BFS. | `F` is LC-invariant; LC-equivalence is poly-time decidable; LC-equivalent graphs are generally not isomorphic, so a raw iso-key would fragment orbits. |
| D6 | **Fusion semantics** | Fusion = **destructive Bell-type measurement of the commuting pair `{X_A Z_B, Z_A X_B}`** (Löbl's canonical type-II convention) of one qubit from each of two components **or intra-component**, realized as a **stabilizer measurement on the tableau/GF(2) rep** (never a graph-rewrite shortcut). `F` = min **successful (postselected)** fusions. **No leaf-only restriction.** **Convention note (M5b implementation finding):** the P5 statement's literal `{X_A X_B, Z_A Z_B}` and this `{X_A Z_B, Z_A X_B}` differ by a Hadamard on one fusion qubit — a *free* single-qubit Clifford — so **`F(G)` is provably identical under either convention** (any schedule converts 1:1). The `{XZ, ZX}` form is used because it realizes the literature's graph rule (disjoint fusion = connect `N(A)×N(B)`, delete A,B; GHZ₃ chains → paths), matching Löbl arXiv:2412.04587 Thm 5 ("one fusion type suffices") and the ballistic-FBQC chain-building constructions. Verified on the stim tableau: `{XX,ZZ}` leaf-fusing two GHZ₃ stars yields the 4-star orbit; `{XZ,ZX}` yields P₄. | Matches the P5 problem's *quantity* exactly (F is convention-invariant); intra-component fusions are required to build cycles; postselection is WLOG (all outcomes LC-equivalent). |
| D7 | **Lean axioms** | Whitelist ⊆ `{propext, Classical.choice, Quot.sound}`; reject `sorryAx`, `native_decide`/`Lean.ofReduceBool`. | Load-bearing certified results must be in-kernel. |
| D8 | **Sandbox (v0)** | Built-in defense-in-depth: `sandbox-exec` (deny network + FS-confine), `psutil` RSS watchdog, CPU/FSIZE rlimits, `killpg`. Apple `container` microVM behind a flag for hostile tiers. | `RLIMIT_AS` is a no-op on macOS. Honest v0 safety = the model never gets a shell **and all v0 verifier code is harness-authored** (Toolwright is a deferred stub — see D11). |
| D9 | **Packaging** | `uv` + src-layout `pyproject.toml` + pinned lockfile; fresh venv. pynauty via conda-forge **or** Xcode-CLT source build; **nauty/`geng`** installed for enumeration. Versions embedded in every certificate. | Reproducibility. |
| D10 | **Dev discipline** | **Test-first** for ledger + verifiers (golden suites are the F3 mechanism); milestone branches → PR → squash-merge to `main`; **no AI attribution** in commits. | Verifier trust is the crux. |
| D11 | **Roles active in v0** | Active: Searcher, Conjecturer, Prover, Critic, Formalizer. **Deferred stubs:** Prospector (anti-scoped literature), **Toolwright** (model-authored verifier code — kept out of v0 so the sandbox trust argument holds). | Keeps the executed-code trust boundary clean for v0. |

---

## 2. Failure modes killed (F1–F5)

| # | Mode | Structural kill |
|---|---|---|
| F1 | Model as oracle | Nothing promotes above `HEURISTIC` without machine evidence. |
| F2 | Context rot | Fresh `--session-id` per attempt; the ledger, not a transcript, is memory; residual baseline context (global CLAUDE.md) is measured and pinned, not assumed zero. |
| F3 | Verifier gaming | Verifiers certified against golden suites before use; load-bearing verifiers (fusion A/B, and the minimality search) have **two independent implementations** whose agreement is required. |
| F4 | Proof by intimidation | Lemma-DAG proofs; independent bounty-framed Critic; past `PROVED_DRAFT` needs a certificate or Lean. |
| F5 | Unbounded burn | Per-move token/wall caps; stall detection; resumable-from-ledger; per-run cost recorded. |

---

## 3. Architecture

Single process, single repo. State = SQLite (WAL, **single-writer via one writer task**) + a blake3 CAS. Solvers/provers are subprocesses; the harness shells out and parses. The model proposes structured JSON; the harness executes everything.

```
empiricist/
  __init__.py          version embedded into certificates
  config.py            frozen RunConfig: version pins, per-role effort, feature flags,
                       resource_model="GHZ_3" (caterpillar only as optional lower-bound oracle),
                       sandbox tier, budget caps, and all numeric defaults (§ below)
  store.py             blake3 CAS: store/blake3/<hh>/<hh>/<hex64>

  ledger/
    schema.py          SQLite DDL + WAL/pragma bootstrap (Appendix A)
    db.py              single writer task + one-transaction-per-transition; workers post results to a queue
    models.py          Artifact, EpistemicLevel, Evidence, Edge, Run, Verdict, Claim, Gate, Certification, Budget
    frontier.py        Pareto frontier + monotone frontier_version (frontier-improvement ≠ status promotion)
    gates.py           persisted human-gate queue: park / list / resolve

  llm/
    client.py          LLMClient Protocol; ClaudeCodeClient (default), AnthropicAPIClient, FakeLLMClient
    roles.py           Role tuples: (system=[spec]+[role_card], effort, k, schema, transport)
    schemas.py         pydantic output/certificate schemas per role (incl. the Construction schema, Appendix E)
    parse.py           envelope → result → pydantic-validate (uses claude --json-schema); bounded retry on genuine failure
    preflight.py       model-resolves + auth-live + concurrency smoke test (auto-tunes k)

  executor/
    runner.py          create_subprocess_exec(start_new_session=True); env-scrub; emits a runs row
    sandbox.py         sandbox_wrap() seam: sandbox-exec profile | Apple container (flag)
    limits.py          darwin-safe rlimits (CPU/FSIZE/CORE=0/NOFILE); NOT RLIMIT_AS
    watchdog.py        psutil RSS watchdog: poll pgid, SIGKILL on breach, record peak RSS

  search/
    database.py        island + MAP-Elites population (LC-orbit-key PK, UPSERT hit_count, evicted-log)
    loop.py            synchronous generational loop: prompt→sample→screen→canonicalize→verify→insert
    attack.py          budgeted counterexample search; auto-ATTACK gate on HEURISTIC→CONJECTURED
    stall.py           two-signal stall → island reset / hard restart (logged)

  verifiers/
    base.py            Verifier Protocol; Verdict; Evidence(details) → CAS; Budget
    registry.py        registry keyed by (tool, version|git-SHA, binary-hash) + certification-stamp lookup
    stab_fusion.py     Verifier A: stim tableau — general destructive Bell fusion; canonical_stabilizers state-eq
    enum_fusion.py     Verifier B: GF(2) stabilizer rep (galois ref + bit-packed numpy) — independent of A
    graph.py           local complementation; LC-orbit BFS; rank-width/cut-rank profile pre-filter; pynauty; geng wrapper
    minsearch.py       exhaustive min-fusion search + an INDEPENDENT second implementation for cross-check
    lean.py            lake env lean --json parse + #print axioms audit → FORMALIZED cert
    lean_project/      pinned lake+mathlib project

  oracles/lobl_table.py   optional Löbl .pkl loader (flag); caterpillar lower-bound cross-check (soft warning)

  domain/p5/
    graphstate.py      graph ↔ GF(2) adjacency ↔ stabilizer generators (X_i Z_{N(i)})
    fusion.py          fusion semantics: GHZ_3 model, parity-pair convention, general fusion
    objectives.py      objective vector (v0: fusion count) + MAP-Elites descriptors (defaults below)
    construction.py    Construction dataclass (Appendix E) + apply()/target-check

  orchestrator.py      asyncio single loop: derive frontier, semaphore fan-out, wall-clock, resume, single writer
  scheduler.py         weighted round-robin over (problem, move); stall cooldown; budget accounting; skips parked gates
  report.py            ledger → Markdown/HTML report (content contract §12)
  cli.py               run / resume / status / verify-only / certify / gates / report

tests/                 pytest; golden suites; FakeLLMClient scripts
```

Modules tied to deferred problems ship as feature-flagged interface stubs (typed, `NotImplementedError` + `# v0.1`).

**Config defaults** (in `config.py`, so behavior is deterministic/testable): JSON-retry count = 2; MAP-Elites cells = `|V|` (exact) × `|E|`-bucket × diameter-class {1,2,3,4,≥5} × fusion-bucket (F−(N−3) ∈ {0,1,2,≥3}); stall no-improvement window = 8 generations; diversity floor = 0.30 distinct-key fraction over last 64 inserts; per-candidate verify timeout = 30 s; DP transient-size cap = n₀ + 4.

---

## 4. The epistemic ledger

### 4.1 Status lattice (per-claim epistemic strength, not a mandatory path)

```
        model proposal, screened            exact machine check, ≤ n
[*] ─────────────► HEURISTIC ──► CONJECTURED ─────────────► (datasets enter here directly)
                       │             │                         VERIFIED_N
                       │             │  general certificate           │
                       ▼             ▼                                ▼
                    REFUTED     PROVED_DRAFT                      CERTIFIED ──► FORMALIZED
```

The lattice is **per-claim epistemic strength**, not a conveyor belt. In particular, **dataset artifacts (the DP `F(G)` table) enter directly at `VERIFIED_N`** without passing through HEURISTIC/CONJECTURED; a closed-form *claim* becomes `CONJECTURED` only when it is consistent with an already-existing `VERIFIED_N` dataset and has survived `ATTACK`.

- **`HEURISTIC`** — screened model output. Never cited as fact.
- **`CONJECTURED`** — precise statement, survived a budgeted `ATTACK`, consistent with a `VERIFIED_N` dataset. Records falsification effort.
- **`PROVED_DRAFT`** (sub-status of `CONJECTURED`) — lemma-DAG proof, Critic returned no gap at a stated effort. Capped here; cert/human required to go higher. F4 dies here.
- **`VERIFIED_N`** — exactly machine-checked for all instances up to size `n`, with a **coverage** field (`exhaustive` | `sampled`). For P5: DP minima with two-verifier achievability + independent-search minimality.
- **`CERTIFIED`** — a **general** statement (not a bounded enumeration) with a machine-checkable certificate independent of the model. For P5 v0 this is a **per-family closed-form proof** whose steps carry independent certificates; the bounded DP table is `VERIFIED_N`, **not** `CERTIFIED`. (Later problems: DRAT UNSAT, rational SOS, exact ILP dual, interval tail.)
- **`FORMALIZED`** — Lean builds sorry-free vs pinned mathlib, axiom audit passes (D7).
- **`REFUTED`** — machine-verified counterexample. Terminal, kept.

### 4.2 Two rules with teeth

1. **Provenance is total.** Artifact IDs are blake3 hashes; evidence rows pin verifier + version + binary-hash + a `details_json`; `runs` rows pin argv, seed, versions, env fingerprint, wall time, peak RSS, tokens/cost; certification stamps are persisted (`certifications` table).
2. **External claims are quarantined.** Prospector output (deferred in v0) is tagged `EXTERNAL`, never a math dependency, parked at the human gate.

### 4.3 "Promotion" vs "frontier improvement" (disambiguated)

- A **status promotion** = an artifact's epistemic level rises up the lattice.
- A **frontier-improvement event** = the Pareto frontier strictly improved (a better construction). This is the Goodhart-resistant search score and is **not** a status change.
- **Stall** fires when a branch produces **neither** a status promotion **nor** a frontier-improvement within its budget.

### 4.4 Resume semantics (kill `-9` safe)

On `resume`: (a) **reconcile orphaned runs** — any `runs` row with `started` but no `ended` is marked `ERROR`/incomplete and its in-flight sample discarded; (b) **recompute spent budget** by summing `runs.cost_usd`/tokens (cap continues, never resets); (c) **reconstruct search state** (current generation, per-island MAP-Elites cells, stall counters) from `population` + `search_events`; (d) the **Pareto frontier is read** from the persisted `pareto_frontier` table and **recomputed from `population` as a consistency check** (they must match — divergence is a hard error). The single-writer discipline guarantees each transition is atomic, so there is never a half-applied promotion.

### 4.5 Reproducibility caveat

Fable-5 is stochastic (no seed); solvers may be non-deterministic. **`VERIFIED_N` rests on independently-checkable certificates, not bitwise output identity.** We force single-thread + logged seeds where possible; the trust argument is "a checkable certificate exists."

---

## 5. Model layer (Claude Code transport) — verified against `claude` v2.1.201

### 5.1 Injectable protocol

```python
class LLMClient(Protocol):
    def complete(self, role: Role, prompt: str, *, session_id: str) -> LLMResult: ...
    async def complete_many(self, role: Role, prompts: list[str]) -> list[LLMResult]: ...
```

`LLMResult`: `text` (mapped from the envelope's `result` field), `parsed` (schema-validated or `None`), `input_tokens`, `output_tokens`, `cache_read_tokens`, `cost_usd`, `duration_ms`, `session_id`, `stop_reason`. Implementations: **`ClaudeCodeClient`** (default), **`FakeLLMClient`** (tests), **`AnthropicAPIClient`** (documented alternative; Batch discount + real concurrency for large Searcher fan-out).

### 5.2 ClaudeCodeClient — the verified invocation

```
claude -p "<prompt>"
  --model claude-fable-5
  --system-prompt "<[frozen spec] + [role card]>"     # replaces default system prompt
  --effort <low|medium|high|xhigh|max>                 # first-class flag; maps 1:1 to role effort
  --tools ""                                           # fully disables tools — model returns text/JSON only
  --output-format json
  --json-schema '<role output schema>'                 # native schema enforcement (print mode); no prompt-hack
  --session-id <fresh uuid>                            # fresh context (F2); id → runs row
  --no-session-persistence                             # fire-and-forget; no session-dir accumulation
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' # no MCP autoload (empty {} CRASHES — needs mcpServers key)
  --permission-mode <non-interactive mode>
```

Verified true against v2.1.201: `--model claude-fable-5` resolves and reports `modelUsage['claude-fable-5']`; `--output-format json` returns `{result, stop_reason, session_id, duration_ms, usage.{input,output,cache_read,cache_creation}_tokens, total_cost_usd, modelUsage}`; `--tools ""` yields text/JSON only; `--effort` works headless; `--json-schema` enforces conformance in `-p` mode; fresh `--session-id` gives fresh context.

- **Structured output** — `parse.py` = take envelope `result` → pydantic-validate. With `--json-schema` the **success** envelope has `stop_reason ∈ {end_turn, tool_use}` — both are success. Hard artifact failure = `parsed is None` or `stop_reason ∈ {refusal, max_tokens}`; bounded retry only on genuine failure.
- **Context purity (F2)** — do **not** use `--bare` (it forces API-key auth and breaks subscription). Instead: `--system-prompt` (replaces default), a minimal `--setting-sources`, run the subprocess from a **clean cwd with no project `CLAUDE.md`**. The global `~/.claude/CLAUDE.md` may still inject (~2.6k tokens baseline observed); **Milestone 4 measures and pins the residual baseline**, recorded as fixed overhead in `runs` — the frozen prefix is *managed*, not assumed zero.
- **Concurrency (review-corrected)** — each `claude -p` ≈ **393 MB RSS + ~1.5 s startup**; the binding constraints are **RAM and subscription rate limits, not ncores**. `preflight.py` measures sustainable k (RSS budget ÷ ~450 MB, and a 429 ceiling) and the semaphore is bounded by that — expect **low-teens**, not 16–64. For large Searcher waves, `AnthropicAPIClient` is the honest path. **Milestone 4 reports sustained k before the overnight campaign relies on it.**
- **Usage** — the JSON envelope populates `runs` directly.
- **Auth/binary** — `claude` path configurable; uses the local binary's subscription auth.

### 5.3 Fable-5 constraints (transport-independent)

**No temperature/top-p/top-k** (all 400) → **SEARCH diversity comes from prompt/seed variation** (each Searcher prompt carries a distinct nonce + island context), never sampling. Thinking is always-on, adaptive, billed as output ($10 in / $50 out per MTok); depth set by `--effort`. 1M context, 128K output. (ZDR-400 is an **API-key-org** concern, not the subscription path — `preflight.py` targets model-resolves + auth-live + concurrency, and ZDR is checked only when `AnthropicAPIClient` is used.)

### 5.4 The seven roles

| Role | Effort | k | v0 | Output schema |
|---|---|---|---|---|
| Prospector | medium | 1 | **stub** | `external_claims.json` |
| Toolwright | high | 1–2 | **stub** (D11) | `code_artifact.json` |
| Searcher | low | auto (≤ sustained) | active | `construction.json` (Appendix E) |
| Conjecturer | medium | 4–8 | active | `conjecture.json` |
| Prover | max | 1 | active (human-gated) | `proof_dag.json` |
| Critic | max | 2 independent | active (human-gated) | `critic_report.json` |
| Formalizer | high | iterative | active (scaffold) | `lean_module.json` |

`k` lives on the Role tuple; the effective wave size is `min(role.k, preflight.sustained_k)`.

---

## 6. Executor & darwin sandbox

Every subprocess (verifier, enumerator, solver, `claude`) goes through `runner.py` → one `runs` row (argv, input hashes, env fingerprint, seed, exit, wall, peak RSS; tokens/cost for model calls). **Sandbox (`sandbox_wrap()`), v0:** `sandbox-exec` profile `(deny network*)` + write-confined `mkdtemp` cwd; `python -I -S` + env-scrub for any executed code; `preexec_fn` sets `RLIMIT_CPU/FSIZE/CORE=0/NOFILE` (**not** `RLIMIT_AS`); `start_new_session=True` + `os.killpg` on timeout; **`psutil` RSS watchdog** (the only working memory bound on macOS). Upgrade path (flag): Apple `container` microVM. Honest v0 safety: **the model never gets a shell and all v0 verifier code is harness-authored** (Toolwright deferred).

---

## 7. Verifier registry (the trust boundary)

`registry.py` keys entries by `(tool, version|git-SHA, binary-hash)`. A verifier **cannot emit evidence until a `certifications` row exists** for its `(name, version, binary_hash)` with `verdict=PASS` and the golden-suite hash. `empiricist certify <verifier>` runs the golden suite and upserts the stamp; `verify()` refuses without a matching stamp. **Load-bearing verifiers get two independent implementations** whose agreement is required (F3): fusion A/B, and the two min-fusion search implementations (`minsearch.py`).

P5 golden suites: identities (`F(path_N)=N−3`, the `F≥N−3` floor, `GHZ₃=K₃=star`), the Adcock LC-orbit counts (cumulative 587 through 9 qubits = 1+1+1+2+4+11+26+101+440) for the orbit machinery, the Löbl caterpillar **lower bound** as a soft cross-check, and (for `minsearch`) agreement between the two independent implementations over all connected orbits to n = 8. **Mutation-test** the suites.

---

## 8. P5 domain & science (where correctness lives)

### 8.1 The model (GHZ₃)

Unbounded \|GHZ₃⟩ (LC-equivalent to 3-star and triangle). Free: single-qubit Cliffords + Pauli-frame tracking. Costly: a **fusion** = destructive Bell measurement of one qubit from each of two components **or two qubits of the same component** (intra-component, needed to close cycles). `F(G) = min #successful fusions producing a state LC-equivalent to |G⟩`, connected `G`, `N ≥ 3`.

**Lower bound (folklore):** `g` GHZ₃'s give `3g` qubits; each fusion consumes 2; so `N = 3g − 2f`. If `f_m` fusions merge components and `f_i` are intra-component, connectivity gives `f_m ≥ g − 1`, whence **`F(G) ≥ N − 3`**, with equality iff every fusion merges two components (`f_i = 0`) and the result is LC-correct. Cyclic graphs need `f_i ≥ 1`, so their peak qubit count transiently exceeds `N` — the search must allow that.

### 8.2 Representations

- **Graph** (networkx / GF(2) adjacency); graph-state stabilizers `{X_v ∏_{u∈N(v)} Z_u}`.
- **Local complementation** `τ_a`: for all `b,c ∈ N(a)`, `A[b,c] ^= 1`. LC-equivalence ⟺ related by local complementations (Bouchet; poly-time). The **multiset of cut-ranks over bipartitions (rank-width profile) is LC-invariant**; a profile mismatch certifies non-equivalence (a cheap one-sided pre-filter feeding the full pynauty + LC-orbit check).

### 8.3 Two independent fusion verifiers (agreement = achievability certificate)

- **A — `stab_fusion` (stim):** build the graph state (`H^n` + `CZ`/edge); realize the fusion as a **native destructive Bell measurement** (measure `X_A X_B`, `Z_A Z_B`, postselect the success branch) — this handles **general** (leaf or internal, inter- or intra-component) fusions exactly and sidesteps the graph-rewrite rule; test **state equality** via `canonical_stabilizers()`.
- **B — `enum_fusion` (GF(2)):** stabilizer tableau over GF(2); the fusion is the **stabilizer-measurement update** of the commuting pair (not "add an edge"); `galois` reference + bit-packed `numpy.uint64` backend; **shares no code with A**.

`canonical_stabilizers()` tests **state** identity, not LC-equivalence; **LC-equivalence is decided by canonicalizing both sides to the LC-orbit canonical key** (D5) via `graph.py`. A construction's achievability requires **A and B to agree** on the resulting LC-orbit key.

### 8.4 Ground truth: exhaustive min-fusion search

`minsearch.py` computes exact `F(G)` (GHZ₃ model) by **BFS in fusion count over states = multisets of component LC-orbits**. Moves from a state: (i) **add a fresh GHZ₃** component; (ii) **apply one fusion** between any two qubits of the multiset — inter-component (merge) or intra-component (loop-close). Dedup states by the multiset of **LC-orbit canonical keys**. `F(orbit) =` the least fusion depth at which a *single* component equal to `G`'s LC-orbit first appears. Bounds that keep it exhaustive-yet-finite: transient component size ≤ `n₀ + transient_cap` (default +4), and fusion depth ≤ a known upper bound on `F` (from any achievable construction). Coverage (`exhaustive` | `sampled`) is recorded per `n`.

**Why the minima are trustworthy (the load-bearing claim):**
1. **Achievability (upper bound):** the search emits a witness Construction; verifiers **A ∧ B** confirm it reaches `LC(G)` → `F(G) ≤ f`.
2. **Minimality (lower bound):** the BFS is exhaustive over the correct move space → no fewer-fusion construction exists. This is made trustworthy by a **second, independent search implementation** (different state encoding — e.g. tableau-set vs GF(2)-multiset) that must reproduce the same minima over the golden range (n ≤ 8), plus consistency with the `F ≥ N−3` floor and the Löbl caterpillar lower bound.
3. The GHZ₃ `F` table is **novel** (there is no published GHZ₃ table — that is the contribution); it is validated by (1), (2), the known identities, and internal A/B + two-search agreement — **not** by a nonexistent external GHZ₃ oracle.

Löbl's caterpillar table is loaded (optionally) only as a **soft** lower-bound warning (`F_cat ≤ F_GHZ3`), never a hard gate.

### 8.5 The live model-driven chain (inner loop, autonomous overnight)

Deterministic `ENUMERATE` (search → `VERIFIED_N`) → **Conjecturer** mines the dataset → closed forms (`HEURISTIC`) → **auto-ATTACK** (counterexample search over the dataset + fresh `geng`-enumerated instances) gates → `CONJECTURED` (or `REFUTED`). **Searcher** proposes explicit Constructions (diversity from prompt/seed), scored by A∧B into the population/frontier. This whole chain runs unattended. **PROVE / CRITIQUE / FORMALIZE are human-gated** (§9): overnight they are *parked*, not run. When a human opens the proof gate for a chosen conjecture, Prover drafts a lemma-DAG and two independent Critics attack it → `PROVED_DRAFT`.

---

## 9. SEARCH / CONJECTURE / ATTACK machine

- **Population** (`search/database.py`): per-island **MAP-Elites** grid. Tables `population(lc_orbit_key PK, island, cell, objective_vec, cert_hash, hit_count)`, `evicted(key, reason, dominated_by, ts)`, `search_events(gen, trigger, detail, ts)`. **`lc_orbit_key` PK = anti-relabeling** (D5); **`evicted` log = no silent truncation**.
- **Loop** (`search/loop.py`): assemble `k` diverse prompts → sample (Searcher) → screen (schema) → canonicalize (LC-orbit key) → verify (A∧B) → insert. Straggler verifiers hit the per-candidate timeout → a distinct `unverified/timeout` rejection, never a barrier stall.
- **Pareto frontier** (`ledger/frontier.py`): explicit table + monotone `frontier_version`; insert iff not dominated, evict dominated in one transaction. **Frontier-improvement event** (§4.3), the only Goodhart-resistant score. v0 primary objective = fusion count, stored as `objective_vec`.
- **ATTACK** (`search/attack.py`): budgeted counterexample search against a precise statement; **mandatory auto-ATTACK gate before any `CONJECTURE` is accepted**; records `REFUTED` + counterexample in `Evidence.details`.
- **Stall** (`search/stall.py`): no-improvement counter (generations since a status **or** frontier event) + diversity floor (distinct-key fraction over a window + island-selection entropy). Frontier-stall → island reset; frontier-stall ∧ diversity-collapse → hard restart (effort bump, elite re-seed, prompt reframe). Every control move is a logged `search_event`.

---

## 10. Lean / FORMALIZE scaffold

One long-lived pinned `lake` + mathlib project (`lean-toolchain` byte-matching mathlib, `lake-manifest.json` pinned, oleans via `lake exe cache get`). `lean.py`: write a content-hash-named `.lean`; `lake env lean --json`; **fail on any `severity=="error"`**; then `#print axioms <target>` and enforce the whitelist ⊆ `{propext, Classical.choice, Quot.sound}` (reject `sorryAx`, `Lean.ofReduceBool`, `native_decide`). Certificate = `{toolchain, mathlib_commit, source_hash, sorted_axioms, json_transcript_hash}`. **Exit-code trap:** `sorry` is a warning and `lake build` exits 0 — the two-part JSON+axiom gate is the only sound check. v0 ships the verifier + pinned project + a generic `|E| ≥ N−1` lemma as a `FORMALIZED` **scaffold**; a real `F(G)` theorem is a separate spike.

---

## 11. Scheduling, budgets, live campaign

Weighted round-robin over `(problem, move)` (one problem in v0); **parked gates are skipped**; stalled branches cool down (weight halves). Authoritative budget table (referenced by §11 and Appendix C):

| Move/role | Token cap | Wall cap |
|---|---|---|
| Searcher wave | 200k | — |
| Conjecturer | 100k | — |
| Prover / lemma | 400k | — |
| Critic / review | 200k | — |
| Formalizer / lemma | 1M | — |
| verifier (screen tier) | — | 10 min |
| verifier (certificate tier) | — | 12 h |
| auto-ATTACK | 100k | 30 min |

**Live overnight campaign (D4):** the **machine-only inner loop** (ENUMERATE, SEARCH, CONJECTURE, ATTACK) runs unattended; PROVE/FORMALIZE park. Uncapped by default with configurable `budget.max_cost_usd`/`max_generations`; `preflight.py` verifies model-resolves + auth-live + sustainable-k; `runs` is the live cost dashboard; the ledger is the checkpoint so `empiricist resume` continues after any interruption; stall at 2M no-event tokens → cooldown.

---

## 12. CLI & reporting

```
empiricist run P5 [--live] [--max-cost N] [--max-gen N]
empiricist resume
empiricist status
empiricist verify-only <artifact>
empiricist certify <verifier>
empiricist gates [list|resolve <id> --approve|--reject]
empiricist report [--html]
```

**Report content contract** (makes exit-5 testable): a header (config hash, version pins, total cost, per-role token/cost); a claims table (each: `status`, `coverage`, `status_n`, the family/statement); for each `CERTIFIED`/`FORMALIZED`/`VERIFIED_N` claim a **provenance block** — evidence rows (`verifier`+`version`+`binary_hash`+`verdict`), the certification stamp used, the dependency chain (`edges`), CAS certificate links, and run costs; a `REFUTED` section with counterexamples; a `gates` section (pending/resolved). Acceptance check: every promoted claim links to a re-checkable CAS artifact and its verifier stamp.

---

## 13. Testing strategy

Test-first for ledger, CAS, executor, and every verifier. **Golden suites gate certification** (a verifier is uncertified until its suite passes; mutation-test the suites). **`FakeLLMClient`** drives all orchestrator/search/role tests deterministically and offline. **Cross-checks as tests:** fusion A vs B fuzzed on random small graphs; the GF(2) stabilizer-measurement update validated against the stim tableau; **the two `minsearch` implementations must agree on all connected orbits to n = 8** (this is what makes VERIFIED_N minimality defensible). The **live pilot** is the only token-spending run, gated behind `--live`.

---

## 14. Git / GitHub workflow

Remote `git@github.com:sghowell/empiricist.git` (SSH, private); push works now. **`gh` is not authenticated** → PR automation needs a one-time `! gh auth login` (else branches are pushed and PRs opened in the UI). One feature branch per milestone → squash-merge to `main`; **no AI attribution** in commits. `.gitignore` adds the SQLite DB, CAS blobs, venv, Lean build artifacts, `.DS_Store` (version only small text certificates).

---

## 15. Build plan (milestones = branches/PRs)

1. **Scaffold** — `uv`/pyproject/src-layout, pytest+ruff, package skeleton, `CLAUDE.md`, `.gitignore`, this spec.
2. **Ledger + CAS** (TDD) — schema (incl. certifications/gates/coverage), CAS, models, frontier, single-writer, resume.
3. **Executor + darwin sandbox** (TDD) — runner, sandbox seam, watchdog, runs rows.
4. **LLM layer** — `ClaudeCodeClient` + **empirical flag/k/baseline probe** (json-schema, effort, tools "", no-session-persistence, mcp fix, residual-token pin, sustained-k), `FakeLLMClient`, roles, parse, preflight.
5. **P5 verifiers** (TDD) — stim A, GF(2) B, graph/LC + rank-width profile, pynauty LC-orbit key, `geng` wrapper, `minsearch` ×2, golden suites + certification, Löbl cross-check.
6. **SEARCH/CONJECTURE/ATTACK** — population, loop, Pareto, ATTACK, stall.
7. **Orchestrator + scheduler + gates + report + CLI**.
8. **Lean verifier + pinned mathlib project scaffold**.
9. **Live P5 pilot** — overnight machine-only campaign + generated report.

Each milestone: branch → TDD → green → commit → push → (PR).

---

## 16. Risks & mitigations (top set)

| Risk | Mitigation |
|---|---|
| **DP misses cyclic graphs / mis-certifies** | Correct move space (intra-component fusions, transient sizes > n₀, depth bound); two independent searches agree to n=8; identities + Löbl lower bound. |
| **Leaf-only ≠ optimal** | Dropped; general fusion on the tableau is the definition (D6). |
| **VERIFIED_N minimality unverified** | Second independent `minsearch`; achievability by A∧B; identity goldens. |
| **`canonical_key` fragments LC-orbits** | One LC-orbit canonical key (min iso-key over the orbit) used as PK everywhere (D5). |
| macOS can't rlimit memory | psutil RSS watchdog day 1; Apple-container for hostile tiers. |
| Claude Code subscription k ≪ 16–64; startup/RSS/rate limits | preflight auto-tunes k (low-teens); API client for scale; Milestone 4 reports sustained k. |
| Global `~/.claude/CLAUDE.md` leaks into role context | clean cwd + `--system-prompt` + minimal setting-sources; measure/pin residual baseline. |
| Fable-5 refusal on FT-FBQC text | `stop_reason==refusal` detection → retry (API path: fallback to opus-4-8); per-role effort caps. |
| Lean exit-code trap | two-part JSON+axiom gate; reject `native_decide`/`Lean.ofReduceBool`/`sorryAx`. |
| Concurrent fan-out vs single-writer SQLite | all workers post to one writer task/queue; workers never write the DB. |
| Human-gate stalls an unattended run | gates parked in a table; scheduler skips; overnight runs machine-only moves. |
| pynauty no arm64 wheel; WL-hash ≠ certificate | conda-forge/Xcode-CLT build; pynauty certificate is the only certified dedup key. |
| SQLite WAL on synced FS; binary DB in git | DB+CAS on local disk; gitignore blobs; version only small text certificates. |

---

## 17. Anti-scope

No distributed execution, no vector DB, no fine-tuning/RL, no web UI beyond the report, no multi-agent architecture beyond Prover/Critic, no autonomous literature claims. Deferred (feature-flagged): Problems 1–4, 6–10; Toolwright + Prospector; all source-build cert tools (SAT/SMT/ILP/SDP/twee); python-flint; Apple-container; the 32 GB Löbl pkl; any actual `FORMALIZED` `F(G)` theorem.

---

## Appendix A. Ledger schema (SQLite, WAL)

```sql
PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,            -- blake3 of canonical content
  kind TEXT,                     -- statement|dataset|construction|certificate|proof_dag|lean|report
  problem TEXT, title TEXT, content_path TEXT,
  status TEXT,                   -- REFUTED|HEURISTIC|CONJECTURED|VERIFIED_N|CERTIFIED|FORMALIZED
  substatus TEXT,                -- PROVED_DRAFT | EXTERNAL | NULL
  status_n INTEGER,              -- iff VERIFIED_N
  coverage TEXT,                 -- 'exhaustive' | 'sampled' | NULL   (VERIFIED_N)
  created_at TEXT, run_id TEXT
);
CREATE TABLE evidence (
  artifact_id TEXT, verifier TEXT, verifier_version TEXT, binary_hash TEXT,
  verdict TEXT,                  -- PASS|FAIL|ERROR|TIMEOUT
  details_json TEXT,             -- counterexample, cert hash, counts, canonical key, ...
  log_path TEXT, wall_s REAL, created_at TEXT
);
CREATE TABLE certifications (    -- the trust-boundary stamp store
  verifier TEXT, verifier_version TEXT, binary_hash TEXT,
  golden_suite_hash TEXT, verdict TEXT, stamped_at TEXT, run_id TEXT,
  PRIMARY KEY (verifier, verifier_version, binary_hash)
);
CREATE TABLE edges (src TEXT, dst TEXT, rel TEXT);  -- depends_on|refutes|generalizes|formalizes|golden_for
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY, move TEXT, role TEXT, model TEXT,
  argv TEXT, seed INT, config_hash TEXT, env_fingerprint TEXT,
  tokens_in INT, tokens_out INT, cache_read INT, cost_usd REAL,
  peak_rss_mb REAL, exit_code INT, started TEXT, ended TEXT, wall_s REAL
);
CREATE TABLE claims (id TEXT PRIMARY KEY, artifact_id TEXT, statement TEXT, family TEXT);
CREATE TABLE gates (            -- persisted human-gate queue
  id TEXT PRIMARY KEY, kind TEXT,   -- REDUCE|PROOF_CAMPAIGN|ACCEPT_DRAFT|RELEASE
  artifact_id TEXT, state TEXT,     -- pending|approved|rejected
  opened_at TEXT, resolved_at TEXT, note TEXT
);
-- search subsystem
CREATE TABLE population (lc_orbit_key TEXT PRIMARY KEY, island INT, cell TEXT,
  objective_vec TEXT, cert_hash TEXT, hit_count INT);
CREATE TABLE evicted (lc_orbit_key TEXT, reason TEXT, dominated_by TEXT, ts TEXT);
CREATE TABLE search_events (gen INT, trigger TEXT, detail TEXT, ts TEXT);
CREATE TABLE pareto_frontier (lc_orbit_key TEXT PRIMARY KEY, objective_vec TEXT, frontier_version INT);
```

## Appendix B. Verifier protocol

```python
class Verdict(StrEnum):
    PASS="PASS"; FAIL="FAIL"; ERROR="ERROR"; TIMEOUT="TIMEOUT"

@dataclass(frozen=True)
class Budget:
    wall_s: float | None = None
    tokens: int | None = None
    rss_mb: float | None = None

@dataclass(frozen=True)
class Evidence:
    verdict: Verdict
    log_path: Path
    details: dict            # counterexample, certificate hash, counts, lc_orbit_key, ...

class Verifier(Protocol):
    name: str; version: str; binary_hash: str
    def applicable(self, artifact: Artifact) -> bool: ...
    def verify(self, artifact: Artifact, budget: Budget) -> Evidence: ...

# Registry rule: verify() runs only if a certifications row
# (name, version, binary_hash, golden_suite_hash, verdict=PASS) exists.
```

## Appendix C. P5 playbook (YAML)

```yaml
problem: P5
resource_model: GHZ_3
fusion: general        # destructive Bell {XX,ZZ}; inter- or intra-component; postselected
spec: artifacts/P5_statement
shared: [stab_fusion, enum_fusion, graph, minsearch, lean]
moves:
  - move: BUILD_TOOL              # v0: harness-authored (Toolwright deferred)
    targets: [stab_fusion, enum_fusion, graph, minsearch]
    golden: {identities: [F_path=N-3, F_ge_N-3, GHZ3=K3],
             orbit_counts: adcock_587_through_9,
             two_search_agreement: connected_to_n8,
             cross_check: lobl_caterpillar_lower_bound_soft}
  - move: ENUMERATE
    tool: minsearch
    range: {N_exhaustive: 9, N_besteffort: 10}
    emits: VERIFIED_N            # sets coverage=exhaustive|sampled
  - move: SEARCH                 # Searcher role, low effort, k-wave
    role: searcher
    scored_by: [stab_fusion, enum_fusion]   # A∧B agreement → population/frontier
    dedup: lc_orbit_key
  - move: CONJECTURE
    inputs: [dataset:F_table]
    families: [path, cycle, tree, grid]
    auto_attack: {budget_tokens: 100k, budget_wall: 30m, instances: geng}
  - move: PROVE                  # human-gated: parked overnight
    gate: human
    output: proof_dag
    then: CRITIQUE {samples: 2, fresh_context: true}
  - move: FORMALIZE              # human-gated
    target: scaffold_connected_edge_bound     # |E| >= N-1; F(G) theorem deferred
    lean: {mathlib: pinned, axiom_audit: true,
           reject: [native_decide, Lean.ofReduceBool, sorryAx]}
budgets:   # authoritative table is §11
  searcher_wave: 200k
  conjecturer: 100k
  prover_lemma: 400k
  critic_review: 200k
  formalizer_lemma: 1M
stall: {no_event_tokens: 2M, action: cooldown}   # "event" = status promotion OR frontier improvement
# Prospector: deferred (anti-scoped literature); no PROSPECT move in v0.
```

## Appendix D. Critic role card (skeleton)

```
You are the Critic. You receive a lemma DAG for a claimed proof.
You do not know who wrote it and you have no stake in it being correct.
Your only success condition is a concrete defect:
  - a lemma whose statement is false (give a counterexample), or
  - an inferential gap (name the lemma, the line, the missing step), or
  - a definition mismatch against the frozen problem statement.
"Looks correct" is a failure state unless you have checked every edge of the DAG;
then emit NO_GAP_FOUND with effort_level and the list of edges checked.
Never propose fixes. Never restate the proof. Output schema: critic_report.json.
```

## Appendix E. Construction / schedule artifact schema

The central search→verify artifact (`kind="construction"`), emitted by Searcher and consumed by verifiers A and B:

```python
@dataclass(frozen=True)
class FusionOp:
    a: QubitId       # (component_id, local_qubit) — one endpoint
    b: QubitId       # the other endpoint; a.component may equal b.component (intra)
    # measured pair is fixed by convention: {X_a X_b, Z_a Z_b}, success branch

@dataclass(frozen=True)
class LocalClifford:
    q: QubitId
    op: str          # e.g. "H", "S", "HS", ... (single-qubit Clifford)

@dataclass(frozen=True)
class Construction:
    resources: int               # number of GHZ_3 units consumed (each contributes 3 qubits)
    steps: list[FusionOp | LocalClifford]   # ordered; interleaved LC + fusion
    target: GraphSpec            # the claimed target graph G (canonical form)
    # F-claim = number of FusionOp steps; verifiers apply steps and check the
    # result's LC-orbit key equals target's LC-orbit key.
```

`applicable()` for A and B matches `kind=="construction"`. `apply()` (in `domain/p5/construction.py`) plays the steps on each verifier's own representation; achievability = both reach `target`'s LC-orbit key with the claimed fusion count.

---

*This spec is the source of truth for Empiricist v0. The correct amount of harness is the minimum that makes F1–F5 structurally impossible; resist adding more.*
